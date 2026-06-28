"""FastAPI lifespan：基础设施启动 / 收尾。

启动顺序（按依赖关系）：
1. 数据目录建好（不依赖任何外部服务）
2. PostgreSQL 探活（严格模式：失败直接抛，应用启动失败）
3. meta_evaluate worker 启动（lifespan 自带 reset stale running）

收尾顺序（反向）：
1. meta_evaluate worker 停止（取消所有 running task）
2. SQLAlchemy engine dispose（关闭连接池）

为什么严格模式？
- DB 不可用时让 systemd / docker 立刻看到失败
- 调试期想绕过：临时 `docker compose up -d postgres` 起好就行
"""
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from app.core.db import dispose as dispose_db, ping as ping_db
from app.core.file_storage import ensure_data_dirs
from app.core.log import logger
from app.workers import worker as meta_evaluate_worker


@asynccontextmanager
async def app_lifespan(app: FastAPI) -> AsyncIterator[None]:
    """FastAPI 生命周期管理。"""

    # ============== 启动 ==============
    logger.info("=" * 60)
    logger.info("[lifespan] starting application infrastructure...")
    logger.info("=" * 60)

    # 1. 数据目录
    ensure_data_dirs()

    # 2. PostgreSQL 探活（严格：失败直接 raise）
    ok, err = await ping_db()
    if not ok:
        logger.error("[lifespan] PostgreSQL 探活失败，应用启动中止：{}", err)
        raise RuntimeError(f"PostgreSQL unavailable: {err}")
    logger.info("[lifespan] PostgreSQL OK")

    # 3. meta_evaluate worker 启动（内部会 reset stale running）
    await meta_evaluate_worker.start()

    logger.info("[lifespan] infrastructure ready, FastAPI app starting")
    logger.info("=" * 60)

    # ============== 运行期 ==============
    yield

    # ============== 收尾 ==============
    logger.info("=" * 60)
    logger.info("[lifespan] shutting down infrastructure...")
    logger.info("=" * 60)

    # 1. worker 停
    await meta_evaluate_worker.stop()

    # 2. DB dispose
    await dispose_db()

    logger.info("[lifespan] shutdown complete")


__all__ = ["app_lifespan"]