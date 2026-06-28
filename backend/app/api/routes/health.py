"""
/health 端点：API 自身 + PostgreSQL 两层探活。

v2.0 调整：
  - 删除 neo4j 探活（v2.0 不再上 Neo4j）
  - 返回示例（全部健康）：
        {
            "status": "ok",
            "components": {
                "api":      {"status": "ok"},
                "postgres": {"status": "ok"}
            }
        }

任一组件失败时，整体 status="degraded"，HTTP 仍返 200。
"""
from fastapi import APIRouter

from app.core.db import ping as ping_db

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    components: dict[str, dict] = {"api": {"status": "ok"}}

    pg_ok, pg_err = await ping_db()
    components["postgres"] = {"status": "ok"} if pg_ok else {"status": "error", "error": pg_err}

    overall = "ok" if pg_ok else "degraded"
    return {"status": overall, "components": components}
