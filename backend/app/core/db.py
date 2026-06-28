"""
SQLAlchemy 2.x async 数据库层。

公开接口
--------
- `engine`            : AsyncEngine 单例（连接池）
- `AsyncSessionLocal` : async_sessionmaker，业务侧 `async with AsyncSessionLocal() as s`
- `Base`              : DeclarativeBase，所有 ORM 模型继承
- `get_db()`          : FastAPI dependency
- `ping()`            : 探活，lifespan / /health 用

v2.0 调整：原样搬自 v1.0（v1.0 没有 neo4j 相关代码，纯 PG 层）。
"""
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text

from app.core.config import settings
from app.core.log import logger


# ---------- 引擎 ----------
engine: AsyncEngine = create_async_engine(
    settings.postgres_dsn,
    pool_size=settings.pg_pool_size,
    max_overflow=settings.pg_max_overflow,
    pool_timeout=settings.pg_pool_timeout,
    pool_pre_ping=True,
    echo=settings.pg_echo,
    future=True,
)


# ---------- Session 工厂 ----------
AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


# ---------- ORM 基类 ----------
class Base(DeclarativeBase):
    """所有模型的基类。Phase 1+ 的 model/*.py 继承它定义表。"""
    pass


# ---------- FastAPI dependency ----------
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """请求级 session：进路由时拿一个，出路由时自动关闭/回滚未提交事务。

    用法：
        @router.get("/datasets")
        async def list_datasets(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Dataset))
            return result.scalars().all()
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        # 不在这里 commit：业务路由显式 commit，避免误吞 ROLLBACK


# ---------- 探活 ----------
async def ping() -> tuple[bool, str | None]:
    """探活：lifespan 启动期校验 + /health 端点用。

    Returns:
        (True,  None)            连接成功
        (False, "error message") 连接失败
    """
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True, None
    except Exception as e:
        logger.error("[db] PostgreSQL ping failed: {}", e)
        return False, str(e)


async def dispose() -> None:
    """优雅关闭连接池。lifespan 关闭阶段调用。"""
    try:
        await engine.dispose()
        logger.info("[db] engine disposed")
    except Exception as e:
        logger.warning("[db] dispose error: {}", e)


__all__ = [
    "engine",
    "AsyncSessionLocal",
    "Base",
    "get_db",
    "ping",
    "dispose",
]
