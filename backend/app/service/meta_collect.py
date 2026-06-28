"""
元数据采集 service 层（v2.0 同步实现）。

设计要点：
- 同步遍历 urls，逐个调 web_scrap agent + 落库（不走后台，不走 SSE）
- 单 URL 异常被 try/except 捕获，不会中断其它 URL
- session 由调用方（路由层 Depends(get_db)）注入并负责 commit 边界

v2.0 简化（对照 v1.0 meta_collect.py）：
- 没有 collect_tasks 表（v2.0 砍掉任务流水）
- 没有 meta_evaluate 第二步（Phase 2 才加）
- 没有 SSE 事件（同步阻塞，前端一次性收结果）
- 用 dict 消息格式 `{"role": "user", "content": url}`（与 v1.0 一致，
  避免引入 langchain_core.messages 单独依赖）
"""
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.log import logger
from app.dao import dataset as dataset_dao


async def ingest_urls(
    session: AsyncSession,
    urls: list[str],
) -> dict[str, Any]:
    """同步遍历 URL 列表，逐个调 web_scrap agent + upsert。

    Args:
        session: 由 Depends(get_db) 注入的 AsyncSession
        urls: 已校验 + 去重 + http/https 的 URL 列表

    Returns:
        {
            "ok": True,
            "items": [{"url", "dataset_id", "status", "error_message?"}, ...],
            "success_count": int,
            "failed_count": int,
        }
    """
    # 延迟 import：避免 service 模块 import 时触发 agent 链路（LLM 初始化）
    from app.agents.web_scrap.builder import build as build_web_scrap_agent

    items: list[dict[str, Any]] = []
    success_count = 0
    failed_count = 0

    for url in urls:
        dataset_id = dataset_dao.compute_dataset_id(url)
        try:
            agent = build_web_scrap_agent()
            result = await agent.ainvoke(
                {"messages": [{"role": "user", "content": url}]}
            )
            scrap = result.get("structured_response")

            if scrap is None:
                raise RuntimeError("agent returned no structured_response")

            if scrap.scrape_status == "success":
                metadata = scrap.metadata or {}
                status = "scraped"
                error_message = None
            else:
                metadata = {"reason": scrap.reason or "unknown"}
                status = "failed"
                error_message = scrap.reason or "scrap failed"

            upsert_res = await dataset_dao.upsert_dataset(
                session=session,
                dataset_id=dataset_id,
                url=url,
                metadata=metadata,
                status=status,
            )
            if not upsert_res.get("ok"):
                raise RuntimeError(
                    upsert_res.get("error", "upsert_dataset failed")
                )

            items.append(
                {
                    "url": url,
                    "dataset_id": dataset_id,
                    "status": status,
                    "error_message": error_message,
                }
            )
            if status == "scraped":
                success_count += 1
            else:
                failed_count += 1

        except Exception as e:
            logger.exception("[meta-collect] ingest failed url={}: {}", url, e)
            items.append(
                {
                    "url": url,
                    "dataset_id": dataset_id,
                    "status": "failed",
                    "error_message": str(e),
                }
            )
            failed_count += 1

    return {
        "ok": True,
        "items": items,
        "success_count": success_count,
        "failed_count": failed_count,
    }
