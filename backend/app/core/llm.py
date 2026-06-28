"""
创建 LLM。用 `ChatDeepSeek`（langchain-deepseek）而非 `ChatOpenAI`。

为什么不用 `ChatOpenAI`？
- `langchain-openai` 官方声明（base.py 第 1-12 行）：只针对 OpenAI 官方 API spec，
  第三方 provider 的非标字段（如 DeepSeek 的 `reasoning_content`）**不会被提取也不会保留**。
- DeepSeek V4 默认 Thinking 模式，思考阶段 `chunk.content` 是空字符串，
  导致前端看到一堆空 token（agent 看似 hang 住）。

`ChatDeepSeek` 解决方案：
- 把 `reasoning_content` 放进 `chunk.additional_kwargs['reasoning_content']`
- 上游可区分「思考过程」和「正式回答」（在 routes/agent.py 里分发为两个 SSE 事件）

v2.0 调整：原样搬自 v1.0（v2.0 仍用 DeepSeek 双工厂函数，
  web_scrap / meta_evaluate / quality_assess agent 在 Phase 1-4 才会用到）。
"""
import os

from langchain_deepseek import ChatDeepSeek

from app.core.log import logger


def _build_llm():
    # 1. 读取环境变量并校验
    base_url = os.getenv("LLM_BASE_URL")
    model_name = os.getenv("LLM_MODEL")
    api_key = os.getenv("LLM_API_KEY")
    timeout_str = os.getenv("LLM_TIMEOUT")

    missing_items = []
    if not base_url:
        missing_items.append("LLM_BASE_URL")
    if not model_name:
        missing_items.append("LLM_MODEL")
    if not api_key:
        missing_items.append("LLM_API_KEY")
    if not timeout_str:
        missing_items.append("LLM_TIMEOUT")

    if missing_items:
        logger.error("[LLM] 缺少环境变量配置: {}", ", ".join(missing_items))
        return None

    try:
        timeout = float(timeout_str)
    except ValueError as e:
        logger.error("[LLM] LLM_TIMEOUT 格式非法，必须是数字: {}", e)
        return None

    try:
        llm = ChatDeepSeek(
            base_url=base_url,
            model=model_name,
            api_key=api_key,
            timeout=timeout,
        )
        logger.info(f"[LLM] 初始化成功, model={model_name}, base_url={base_url}")
        return llm
    except Exception as e:
        logger.exception("[LLM] 创建 ChatDeepSeek 实例异常")
        return None


def _build_llm_unthinking():
    """创建「关掉 thinking 模式」的 ChatDeepSeek 实例。

    适用场景：使用 ToolStrategy 强制 tool_choice="any" 的 agent
    （如 web_scrap v2 / orchestrator 等需要结构化输出的场景）。

    为什么单独搞一个？
    - deepseek-v4-flash 默认 thinking 模式
    - thinking 模式下，DeepSeek API 不支持 tool_choice="any"
      （会 400 报错："Thinking mode does not support this tool_choice"）
    - LangChain 的 ToolStrategy 必须配 tool_choice="any" 才能强制结构化输出
    - 所以这一类 agent 必须用"关 thinking"的模型实例
    """
    base_url = os.getenv("LLM_BASE_URL")
    model_name = os.getenv("LLM_MODEL")
    api_key = os.getenv("LLM_API_KEY")
    timeout_str = os.getenv("LLM_TIMEOUT")

    missing_items = []
    if not base_url:
        missing_items.append("LLM_BASE_URL")
    if not model_name:
        missing_items.append("LLM_MODEL")
    if not api_key:
        missing_items.append("LLM_API_KEY")
    if not timeout_str:
        missing_items.append("LLM_TIMEOUT")

    if missing_items:
        logger.error(
            "[LLM unthinking] 缺少环境变量配置: {}", ", ".join(missing_items)
        )
        return None

    try:
        timeout = float(timeout_str)
    except ValueError as e:
        logger.error("[LLM unthinking] LLM_TIMEOUT 格式非法，必须是数字: {}", e)
        return None

    try:
        llm = ChatDeepSeek(
            base_url=base_url,
            model=model_name,
            api_key=api_key,
            timeout=timeout,
            extra_body={"thinking": {"type": "disabled"}},
        )
        logger.info(
            f"[LLM unthinking] 初始化成功, model={model_name}, base_url={base_url}"
        )
        return llm
    except Exception as e:
        logger.exception("[LLM unthinking] 创建 ChatDeepSeek 实例异常")
        return None
