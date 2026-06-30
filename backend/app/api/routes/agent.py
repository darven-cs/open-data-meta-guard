"""数据故事 Chatbot SSE 流式路由。

SSE 端点: POST /agent/stream
支持 6 种事件: token / reasoning / tool_start / tool_end / done / error

流式编排：手动 tool-calling 循环（不用 create_agent + ToolStrategy）。
原因：create_agent 强制 tool_choice="any"，最终答案打包在 tool_call 里，
无法流式输出故事 token。改用手动工具编排，LLM 可以边思考边输出 token。

多工具并发：kg_query 和 analyze_and_chart 互不依赖 → asyncio.gather() 并发执行。
最大循环数：MAX_TOOL_ROUNDS=5，防止死循环。
"""
import asyncio
import json
import traceback

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, SystemMessage, ToolMessage

from app.agents.data_story.builder import build
from app.agents.data_story.prompt import DATA_STORY_PROMPT
from app.core.db import AsyncSessionLocal
from app.core.llm import _build_llm, _build_llm_unthinking
from app.core.log import logger
from app.dao import chat as chat_dao
from app.schemas.chat import ConversationCreate

router = APIRouter(prefix="/agent", tags=["agent"])

# 最大工具调用轮次（纯安全网，LLM 无 tool_calls 时会自动 break）
MAX_TOOL_ROUNDS = 15

# ───────── SSE helpers ─────────


def _sse(event: str, data: dict | None = None) -> str:
    """构建一条 SSE 消息。"""
    payload = json.dumps(data or {}, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


def _sse_error(msg: str) -> str:
    """构建 SSE error 消息。"""
    return _sse("error", {"msg": msg})


def _sse_done() -> str:
    return _sse("done")


# ───────── 工具名称映射 ─────────

_TOOL_NAME_MAP = {
    "kg_query": "kg_query",
    "analyze_and_chart": "analyze_and_chart",
}


def _get_tool_name(tc: dict) -> str:
    """从 tool_call dict 提取工具名。"""
    return _TOOL_NAME_MAP.get(tc.get("name", ""), tc.get("name", "unknown"))


# ───────── 主流式端点 ─────────


@router.post("/stream")
async def stream(request: Request):
    """SSE 流式对话端点。

    POST body: {message: str, conversation_id?: str}
    """

    # ── 解析请求体 ──
    try:
        body = await request.json()
        user_msg = body.get("message", "").strip()
        conv_id = body.get("conversation_id") or None
    except Exception:
        return StreamingResponse(
            iter([_sse_error("invalid JSON body")]),
            media_type="text/event-stream",
        )

    if not user_msg:
        return StreamingResponse(
            iter([_sse_error("message is required")]),
            media_type="text/event-stream",
        )

    # ── 构建 agent ──
    llm_with_tools, tools = build()
    if llm_with_tools is None or not tools:
        return StreamingResponse(
            iter([_sse_error("LLM 配置异常，请检查环境变量")]),
            media_type="text/event-stream",
        )

    # ── 定义异步生成器 ──
    async def event_stream():
        # 收集的 chart_paths 和 kg_context（用于持久化）
        collected_charts: list[dict] = []
        collected_kg_context: dict = {}
        collected_tool_steps: list[dict] = []

        # 客户端连接状态 + 文本内容累加器
        assistant_content_parts: list[str] = []
        _client_connected = True

        try:
            # 构建初始消息
            messages = [
                SystemMessage(content=DATA_STORY_PROMPT),
                HumanMessage(content=user_msg),
            ]

            # ── 手动 tool-calling 循环 ──
            for round_num in range(1, MAX_TOOL_ROUNDS + 1):
                if await request.is_disconnected():
                    if _client_connected:
                        logger.info("[agent] client disconnected during loop round {}", round_num)
                        _client_connected = False

                # ── astream → yield token/reasoning events ──
                full_chunks: list[AIMessageChunk] = []

                async for chunk in llm_with_tools.astream(messages):
                    if await request.is_disconnected():
                        if _client_connected:
                            logger.info("[agent] client disconnected during streaming")
                            _client_connected = False

                    full_chunks.append(chunk)

                    # reasoning（DeepSeek thinking）
                    reasoning = (
                        chunk.additional_kwargs.get("reasoning_content", "")
                        if isinstance(chunk.additional_kwargs, dict)
                        else ""
                    )
                    if reasoning and isinstance(reasoning, str):
                        if _client_connected:
                            yield _sse("reasoning", {"content": reasoning})
                        continue

                    # 如果有 tool_call_chunks → 跳过 content（content 可能是工具参数的 JSON 片段）
                    has_tool_chunks = (
                        hasattr(chunk, "tool_call_chunks")
                        and chunk.tool_call_chunks
                    )

                    # 输出文本 token
                    content = chunk.content
                    if content and isinstance(content, str) and not has_tool_chunks:
                        if _client_connected:
                            yield _sse("token", {"content": content})
                        assistant_content_parts.append(content)

                # ── 合并所有 chunks 为一条完整消息 ──
                if not full_chunks:
                    break

                # AIMessageChunk 支持 + 运算合并
                full_message: AIMessage = full_chunks[0]
                for c in full_chunks[1:]:
                    full_message = full_message + c

                # ── 检查是否有 tool_calls ──
                if not full_message.tool_calls:
                    # 无工具调用 → LLM 已给出最终回答 → 结束
                    break

                # ── 执行工具（并发） ──
                tool_calls = full_message.tool_calls

                # 发送 tool_start 事件
                for tc in tool_calls:
                    name = _get_tool_name(tc)
                    if _client_connected:
                        yield _sse("tool_start", {"tool": name})
                    collected_tool_steps.append({"tool": name, "status": "running"})

                tool_results = await _execute_tools_concurrent(tools, tool_calls)

                # 发送 tool_end 事件
                for tc in tool_calls:
                    name = _get_tool_name(tc)
                    if _client_connected:
                        yield _sse("tool_end", {"tool": name})
                    # 更新 tool_steps
                    for s in collected_tool_steps:
                        if s["tool"] == name and s["status"] == "running":
                            s["status"] = "done"
                            break

                # 收集 kg_context 和 chart_paths
                for tc, result in zip(tool_calls, tool_results):
                    name = _get_tool_name(tc)
                    if name == "kg_query":
                        try:
                            collected_kg_context = json.loads(result)
                        except (json.JSONDecodeError, TypeError):
                            pass
                    elif name == "analyze_and_chart":
                        try:
                            ar = json.loads(result)
                            if ar.get("chart_path"):
                                collected_charts.append({
                                    "chart_type": tc.get("args", {}).get("analysis_type", "unknown"),
                                    "file_path": ar["chart_path"],
                                    "title": tc.get("args", {}).get("chart_title", ""),
                                })
                        except (json.JSONDecodeError, TypeError):
                            pass

                # 把 tool 调用加入 messages（注意顺序保持一致）
                messages.append(full_message)
                for tc, result in zip(tool_calls, tool_results):
                    messages.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))

                logger.info(
                    "[agent] round {}: executed {} tools, total tokens emitted",
                    round_num,
                    len(tool_calls),
                )

            # ── 流结束 ──
            assistant_content = "".join(assistant_content_parts)
            if _client_connected:
                yield _sse_done()

            # ── 持久化到 DB ──
            await _persist_conversation(
                conv_id=conv_id,
                user_msg=user_msg,
                assistant_content=assistant_content,
                chart_paths=collected_charts,
                kg_context=collected_kg_context,
                tool_steps=collected_tool_steps,
            )

        except Exception as e:
            logger.error("[agent] stream error: {}\n{}", e, traceback.format_exc())
            if _client_connected:
                yield _sse_error(str(e))

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ───────── 工具并发执行 ─────────


async def _execute_tools_concurrent(tools, tool_calls: list[dict]) -> list:
    """并发执行多个工具调用。

    所有工具调用互不依赖 → asyncio.gather() 并发执行。
    """
    async def _run_one(tc: dict):
        name = tc.get("name", "")
        args = tc.get("args", {})
        # 找到对应工具
        for t in tools:
            if t.name == name:
                try:
                    result = await t.ainvoke(args)
                    return str(result) if result is not None else ""
                except Exception as e:
                    logger.error("[agent] tool {} failed: {}", name, e)
                    return json.dumps({"error": str(e)}, ensure_ascii=False)
        return json.dumps({"error": f"unknown tool: {name}"}, ensure_ascii=False)

    return await asyncio.gather(*[_run_one(tc) for tc in tool_calls])


# ───────── 持久化 ─────────


async def _persist_conversation(
    conv_id: str | None,
    user_msg: str,
    assistant_content: str,
    chart_paths: list[dict],
    kg_context: dict,
    tool_steps: list[dict],
) -> None:
    """持久化对话到 PG（可选，失败不阻塞）。"""
    try:
        async with AsyncSessionLocal() as session:
            is_new = False
            # 创建或复用会话
            if not conv_id:
                conv_res = await chat_dao.create_conversation(session, title="新会话")
                if conv_res.get("ok"):
                    conv_id = conv_res["conversation"]["id"]
                    is_new = True
                else:
                    logger.warning("[agent] failed to create conversation")
                    return

            # 保存用户消息
            await chat_dao.add_message(
                session, conv_id, "user", content=user_msg,
            )

            # 保存助手消息
            await chat_dao.add_message(
                session,
                conv_id,
                "assistant",
                content=assistant_content,
                chart_paths=chart_paths,
                kg_context=kg_context,
                tool_steps=tool_steps,
            )

            # 新会话首次对话结束后，用 LLM 生成标题
            if is_new:
                await _auto_generate_title(session, conv_id, user_msg)
        logger.info("[agent] persisted conversation {} to DB", conv_id)
    except Exception as e:
        logger.warning("[agent] persist failed (non-blocking): {}", e)


async def _auto_generate_title(
    session, conv_id: str, user_msg: str
) -> None:
    """用 LLM 根据第一条用户消息生成 ≤12 字标题（失败不阻塞）。"""
    try:
        llm = _build_llm_unthinking()
        if llm is None:
            llm = _build_llm()
        if llm is None:
            logger.warning("[agent] no LLM available for title generation")
            return

        prompt = (
            "用不超过12个字总结以下对话的主题，只输出标题：\n"
            f"{user_msg[:200]}"
        )
        resp = await llm.ainvoke([HumanMessage(content=prompt)])
        title = resp.content.strip()[:12] if resp.content else "新会话"
        if not title:
            title = "新会话"

        await chat_dao.update_conversation_title(session, conv_id, title)
        logger.info("[agent] auto-generated title '{}' for conv {}", title, conv_id)
    except Exception as e:
        logger.warning("[agent] title generation failed (non-blocking): {}", e)


# ───────── 会话管理端点（可选，后续迭代）─────────


@router.get("/conversations")
async def list_conversations():
    """列出所有会话。"""
    try:
        async with AsyncSessionLocal() as session:
            result = await chat_dao.list_conversations(session)
            if not result.get("ok"):
                return {"code": 500, "data": None, "msg": result.get("error", "")}
            return {
                "code": 200,
                "data": result["conversations"],
                "msg": "success",
            }
    except Exception as e:
        logger.error("[agent] list_conversations failed: {}", e)
        return {"code": 500, "data": None, "msg": str(e)}


@router.delete("/conversations/{conv_id}")
async def delete_conversation(conv_id: str):
    """删除指定会话及其所有消息。"""
    try:
        async with AsyncSessionLocal() as session:
            result = await chat_dao.delete_conversation(session, conv_id)
            if not result.get("ok"):
                return {"code": 404, "data": None, "msg": result.get("error", "")}
            return {"code": 200, "data": None, "msg": "success"}
    except Exception as e:
        logger.error("[agent] delete_conversation failed: {}", e)
        return {"code": 500, "data": None, "msg": str(e)}


@router.post("/conversations")
async def create_conversation(body: ConversationCreate):
    """显式创建会话，返回服务端 UUID。"""
    try:
        async with AsyncSessionLocal() as session:
            result = await chat_dao.create_conversation(session, title=body.title)
            if not result.get("ok"):
                return {"code": 500, "data": None, "msg": result.get("error", "")}
            return {
                "code": 200,
                "data": result["conversation"],
                "msg": "success",
            }
    except Exception as e:
        logger.error("[agent] create_conversation failed: {}", e)
        return {"code": 500, "data": None, "msg": str(e)}


@router.get("/conversations/{conv_id}/messages")
async def get_messages(conv_id: str):
    """获取会话历史消息。"""
    try:
        async with AsyncSessionLocal() as session:
            result = await chat_dao.get_messages(session, conv_id)
            if not result.get("ok"):
                return {"code": 404, "data": None, "msg": result.get("error", "")}
            return {
                "code": 200,
                "data": result["messages"],
                "msg": "success",
            }
    except Exception as e:
        logger.error("[agent] get_messages failed: {}", e)
        return {"code": 500, "data": None, "msg": str(e)}


@router.patch("/conversations/{conv_id}/title")
async def update_title(conv_id: str, body: dict):
    """更新会话标题。"""
    title = body.get("title", "").strip()
    if not title:
        return {"code": 400, "data": None, "msg": "title is required"}
    try:
        async with AsyncSessionLocal() as session:
            result = await chat_dao.update_conversation_title(session, conv_id, title)
            if not result.get("ok"):
                return {"code": 404, "data": None, "msg": result.get("error", "")}
            return {
                "code": 200,
                "data": result["conversation"],
                "msg": "success",
            }
    except Exception as e:
        logger.error("[agent] update_title failed: {}", e)
        return {"code": 500, "data": None, "msg": str(e)}


__all__ = ["router"]
