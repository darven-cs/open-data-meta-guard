"""
集中读 .env 配置（pydantic-settings v2）。

v2.0 调整：
  - 删除 neo4j_uri / neo4j_user / neo4j_password / neo4j_database 配置项
  - 端口默认值改 10020（v2.0 独立占用，避免与 v1.0 的 10010 冲突）
"""
from functools import lru_cache

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        case_sensitive=False,
        extra="ignore",
    )

    # ---------- PostgreSQL ----------
    # v2.0 独立占用 10020（v1.0 仍占 10010，两套环境可并存）
    postgres_host: str = Field(default="localhost")
    postgres_port: int = Field(default=10020)
    postgres_db: str = Field(default="open_data_meta_guard")
    postgres_user: str = Field(default="postgres")
    postgres_password: str = Field(default="change_me")

    # SQLAlchemy 连接池
    pg_pool_size: int = Field(default=10)
    pg_max_overflow: int = Field(default=20)
    pg_pool_timeout: int = Field(default=30)
    pg_echo: bool = Field(default=False)

    # ---------- 数据下载 ----------
    download_dir: str = Field(default="./data")
    download_timeout: int = Field(default=60)
    download_max_file_size_mb: int = Field(default=500)

    # ---------- 质量评估 ----------
    quality_sample_size: int = Field(default=100_000)
    quality_minimal_mode: bool = Field(default=True)

    # ---------- meta_evaluate 异步 worker ----------
    # 单次 agent.ainvoke 硬超时（秒）
    meta_evaluate_timeout_sec: int = Field(default=180)
    # worker 主循环 tick 间隔（秒），claim 周期
    meta_evaluate_worker_tick_sec: float = Field(default=1.0)
    # 启动时重置 stale running job 的阈值（秒）
    meta_evaluate_stale_threshold_sec: int = Field(default=300)
    # reason_content / tool_calls 日志截断阈值（字节）
    meta_evaluate_log_truncate_bytes: int = Field(default=16 * 1024)

    # ---------- 计算属性 ----------
    @computed_field  # type: ignore[prop-decorator]
    @property
    def postgres_dsn(self) -> str:
        """SQLAlchemy async DSN（用 asyncpg 驱动）"""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def postgres_sync_dsn(self) -> str:
        """同步 DSN：alembic 迁移 / 临时 psql 用，注意驱动是 psycopg2 不是 asyncpg"""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache(maxsize=1)
def _get_settings() -> Settings:
    """lru_cache 实现单例，避免每次 import 都重新读 env"""
    return Settings()


# 模块级单例（其他模块直接 `from app.core.config import settings`）
settings: Settings = _get_settings()


__all__ = ["Settings", "settings"]
