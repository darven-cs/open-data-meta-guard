"""
SQLAlchemy 2.x async 数据库层 + Neo4j 异步驱动管理。

公开接口
--------
- `engine`            : AsyncEngine 单例（连接池）
- `AsyncSessionLocal` : async_sessionmaker，业务侧 `async with AsyncSessionLocal() as s`
- `Base`              : DeclarativeBase，所有 ORM 模型继承
- `get_db()`          : FastAPI dependency
- `ping()`            : 探活，lifespan / /health 用
- `get_neo4j_driver()`: Neo4j AsyncDriver 单例
- `init_neo4j_driver()`: 初始化 Neo4j 驱动（lifespan 启动时调）
- `close_neo4j_driver()`: 关闭 Neo4j 驱动（lifespan 关闭时调）

v2.0 调整：Phase 5 新增 Neo4j 异步驱动管理。
"""
from typing import AsyncGenerator, Optional

from neo4j import AsyncDriver, AsyncGraphDatabase
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


# ═══════════════════════════════════════════════════════════════════
# Neo4j 异步驱动（Phase 5 知识图谱）
# ═══════════════════════════════════════════════════════════════════

_neo4j_driver: Optional[AsyncDriver] = None


def get_neo4j_driver() -> AsyncDriver:
    """获取 Neo4j AsyncDriver 单例。

    Raises:
        RuntimeError: 驱动未初始化（lifespan 启动前或关闭后调用）
    """
    if _neo4j_driver is None:
        raise RuntimeError("Neo4j driver not initialized. Call init_neo4j_driver() first.")
    return _neo4j_driver


async def init_neo4j_driver() -> None:
    """初始化 Neo4j 异步驱动（lifespan 启动阶段调用）。"""
    global _neo4j_driver
    try:
        driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
        # 验证连接
        async with driver.session(database=settings.neo4j_database) as session:
            await session.run("RETURN 1")
        _neo4j_driver = driver
        logger.info("[neo4j] driver initialized: uri={}", settings.neo4j_uri)
    except Exception as e:
        logger.error("[neo4j] driver init failed: {}", e)
        raise


async def close_neo4j_driver() -> None:
    """优雅关闭 Neo4j 驱动（lifespan 关闭阶段调用）。"""
    global _neo4j_driver
    if _neo4j_driver is None:
        return
    try:
        await _neo4j_driver.close()
        logger.info("[neo4j] driver closed")
    except Exception as e:
        logger.warning("[neo4j] driver close error: {}", e)
    finally:
        _neo4j_driver = None


async def ping_neo4j() -> tuple[bool, str | None]:
    """Neo4j 探活。"""
    try:
        driver = get_neo4j_driver()
        async with driver.session(database=settings.neo4j_database) as session:
            await session.run("RETURN 1")
        return True, None
    except Exception as e:
        logger.error("[neo4j] ping failed: {}", e)
        return False, str(e)


__all__ = [
    "engine",
    "AsyncSessionLocal",
    "Base",
    "get_db",
    "ping",
    "dispose",
    "get_neo4j_driver",
    "init_neo4j_driver",
    "close_neo4j_driver",
    "ping_neo4j",
]
