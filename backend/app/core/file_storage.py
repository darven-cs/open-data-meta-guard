"""
文件存储工具：路径净化 + 数据目录初始化。

v2.0 调整：原样搬自 v1.0（v2.0 仍会用到 safe_path / safe_dataset_id 做路径防御）。
"""
import re
from pathlib import Path

from app.core.config import settings
from app.core.log import logger


# 仅允许：字母 / 数字 / 下划线 / 短横线 / 点（点禁止开头，防 .env / .. 之类）
_VALID_PART = re.compile(r"^[A-Za-z0-9_\-][A-Za-z0-9_\-.]*$")


def safe_dataset_id(raw: str) -> str:
    """把任意字符串净化成可作为文件名/路径段使用的形式。

    sha256 输出本就只有十六进制 [0-9a-f]，这里是兜底防御。
    """
    sanitized = re.sub(r"[^A-Za-z0-9_\-]", "_", raw)
    # 截断过长（防文件系统 NAMETOO_LONG）
    return sanitized[:128] or "unknown"


def safe_path(base: str | Path, *parts: str) -> Path:
    """安全拼路径，确保最终路径在 base 之内（防 `..` 穿越）。

    Args:
        base: 基础目录（settings.download_dir 之类）
        *parts: 后续路径段，会逐段净化

    Returns:
        绝对路径 Path

    Raises:
        ValueError: 任何段含非法字符，或最终路径逃出 base
    """
    base_p = Path(base).resolve()
    for p in parts:
        if not p or not _VALID_PART.match(p):
            raise ValueError(f"[safe_path] illegal path segment: {p!r}")

    final = base_p.joinpath(*parts).resolve()
    # 必须仍在 base 之下
    try:
        final.relative_to(base_p)
    except ValueError as e:
        raise ValueError(
            f"[safe_path] path escapes base: base={base_p} final={final}"
        ) from e
    return final


def ensure_data_dirs() -> None:
    """lifespan 启动时建好所有数据子目录（幂等）。"""
    base = Path(settings.download_dir).resolve()
    sub_dirs = [
        base / "raw",
        base / "cleaned",
        base / "uploads",
        base / "charts",
        base / "reports" / "meta_evaluate",
        base / "reports" / "quality",
    ]
    for d in sub_dirs:
        d.mkdir(parents=True, exist_ok=True)
    logger.info("[storage] data dirs ready under {}", base)


__all__ = ["safe_dataset_id", "safe_path", "ensure_data_dirs"]
