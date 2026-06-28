"""
Alembic 异步环境（async template + 项目 DSN 注入）。

要点
----
1. **DSN 来源**：`app.core.config.settings.postgres_dsn`，从 .env 读
2. **load_dotenv 兜底**：`alembic` 是独立进程，`app/api/app.py` 的
   `load_dotenv()` 不会自动跑。这里手动调一次，行为与 FastAPI 启动一致
3. **target_metadata**：从 `app.core.db.Base.metadata` 拿；下面 `from app.model import *`
   显式 import 是关键——不 import 模型类，metadata 是空的，autogenerate 写出来是空文件
4. **render_as_batch=False**：PostgreSQL 不需要 SQLite 的 batch 模式
5. **compare_type=True / compare_server_default=True**：autogenerate 能识别列类型/默认值变更

v2.0 调整：
   - `app.models` → `app.model`（v2.0 单数命名）
   - 各 Phase 的模型在对应 alembic 迁移文件生成时才 import
"""
import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# ---------- 加载 .env + 项目依赖 ----------
from dotenv import load_dotenv
load_dotenv()  # noqa: E402

from app.core.db import Base  # noqa: E402
from app.core.config import settings  # noqa: E402

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 注入 DSN：让 alembic.ini 里的 sqlalchemy.url 失效，env.py 接管
config.set_main_option("sqlalchemy.url", settings.postgres_dsn)

# ---------- 目标 metadata ----------
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """offline 模式只生成 SQL 脚本不实际连库；不创建 Engine、不需要 DBAPI。"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """在线模式：async engine + 走 connection.run_sync 同步执行 migration。"""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """在线模式入口。"""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
