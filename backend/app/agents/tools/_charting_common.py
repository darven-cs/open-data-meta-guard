"""图表与数据读取共享模块 — 数据故事 chatbot 用。

抽取自 data_analysis_tool.py，供 5 个工具复用：
- _safe_read_df：编码自动探测 + 采样限制
- _CHARTS_DIR：图表输出根目录
- save_fig_as_png：统一 PNG 保存入口（dataset_id 子目录 + 时间戳文件名）
- CJK 字体探测与 plt.rcParams 设置

设计要点：
- **matplotlib Agg backend + asyncio.to_thread()**：无显示器 + 不阻塞事件循环。
- **中文支持**：自动尝试多个中文字体。
- 文件名格式 `{chart_type}_{timestamp}.png` 与子目录结构与 v1 完全兼容。
"""
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # 必须在 import pyplot 之前设置

import matplotlib.pyplot as plt
import pandas as pd

from app.core.config import settings
from app.core.log import logger


# ───────── 中文支持 ─────────

# 按优先级尝试中文字体
_CN_FONT_CANDIDATES = [
    "Noto Sans CJK SC",
    "SimHei",
    "WenQuanYi Micro Hei",
    "WenQuanYi Zen Hei",
    "Noto Sans SC",
    "AR PL UMing CN",
    "DejaVu Sans",
]
_CN_FONT = None

for _f in _CN_FONT_CANDIDATES:
    try:
        from matplotlib.font_manager import FontProperties
        FontProperties(family=_f)
        _CN_FONT = _f
        break
    except Exception:
        continue

if _CN_FONT:
    plt.rcParams["font.sans-serif"] = [_CN_FONT, "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    logger.info("[_charting_common] using font: {}", _CN_FONT)
else:
    logger.warning("[_charting_common] no CJK font found, chart labels may render as tofu")


# ───────── 图表目录 ─────────

def _charts_dir() -> Path:
    base = Path(settings.download_dir).resolve()
    return base / "charts"


_CHARTS_DIR = _charts_dir()


# ───────── 守护函数 ─────────

# 中国政务数据文件常见编码(UTF-8 → GBK → GB18030 → latin-1 回退)
_CSV_ENCODINGS = ["utf-8", "gbk", "gb2312", "gb18030", "latin-1"]


def _safe_read_df(file_path: str, file_format: str) -> pd.DataFrame:
    """安全读取 CSV/XLSX,自动探测编码(中文政务数据常用 GBK)。"""
    fmt = file_format.lower()
    if fmt == "csv":
        last_err = None
        for enc in _CSV_ENCODINGS:
            try:
                return pd.read_csv(file_path, encoding=enc, nrows=settings.quality_sample_size)
            except (UnicodeDecodeError, UnicodeError) as e:
                last_err = e
                continue
        # 所有编码都失败,抛最后一种编码的错误
        raise ValueError(f"无法读取 CSV(已尝试编码 {_CSV_ENCODINGS}): {last_err}")
    elif fmt in ("xls", "xlsx"):
        return pd.read_excel(file_path, nrows=settings.quality_sample_size)
    elif fmt == "json":
        return pd.read_json(file_path)
    else:
        raise ValueError(f"unsupported file format: {fmt}")


# ───────── 通用 PNG 保存 ─────────

def save_fig_as_png(fig, dataset_id: str, chart_type: str) -> str | None:
    """通用 PNG 保存:基于 dataset_id 子目录 + 时间戳,返回相对路径。

    返回值格式: charts/<dataset_id>/<chart_type>_<timestamp>.png
    (与 _CHARTS_DIR.parent 的相对路径,供前端构造 URL 使用)
    """
    dataset_dir = _CHARTS_DIR / dataset_id
    dataset_dir.mkdir(parents=True, exist_ok=True)
    ts = int(time.time() * 1000)
    path = dataset_dir / f"{chart_type}_{ts}.png"
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return str(path.relative_to(_CHARTS_DIR.parent))


__all__ = [
    "_CN_FONT",
    "_CN_FONT_CANDIDATES",
    "_CHARTS_DIR",
    "_CSV_ENCODINGS",
    "_safe_read_df",
    "save_fig_as_png",
]