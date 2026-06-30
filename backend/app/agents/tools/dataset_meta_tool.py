"""数据集元数据查询工具 — 数据故事 chatbot 用。

读取 PG 中 datasets.metadata_ JSONB + data_downloads 联合查询，
返回数据故事的「数据来源 + 局限性」所需元信息。

不对数据文件做分析/渲染图表，仅返回结构化 JSON。
"""
import json
from typing import Any

from langchain.tools import tool
from sqlalchemy import select

from app.core.db import AsyncSessionLocal
from app.core.log import logger
from app.dao import data_download as download_dao
from app.model.data_download import DataDownload
from app.model.dataset import Dataset


# ───────── 字段提取 ─────────

# metadata_ JSONB 常见键名（不同数据源键名差异，做宽口径读取）
_METADATA_KEYS_TITLE = ["title", "标题", "数据集名称", "name", "dataset_name", "数据集标题"]
_METADATA_KEYS_PUBLISHER = ["publisher", "发布机构", "提供方", "来源", "organization", "org"]
_METADATA_KEYS_ISSUED = ["issued", "发布日期", "创建日期", "created", "发布日期", "release_date", "publish_date"]
_METADATA_KEYS_UPDATE_FREQ = ["update_frequency", "更新频率", "更新周期", "frequency"]
_METADATA_KEYS_TEMPORAL = ["temporal_coverage", "时间范围", "时间覆盖", "时间跨度", "temporal", "date_range"]
_METADATA_KEYS_SPATIAL = ["spatial_coverage", "空间范围", "地理范围", "空间覆盖", "spatial", "region"]
_METADATA_KEYS_CATEGORY = ["category", "分类", "主题", "subject", "tag"]
_METADATA_KEYS_LANGUAGE = ["language", "语言", "lang"]
_METADATA_KEYS_DESCRIPTION = [
    "description", "描述", "简介", "abstract", "summary", "说明",
]


def _first_match(meta: dict, keys: list[str]) -> str:
    """从 metadata_ JSONB 中按候选键顺序取第一个存在的值。"""
    if not isinstance(meta, dict):
        return ""
    for k in keys:
        if k in meta and meta[k] not in (None, "", []):
            v = meta[k]
            return str(v).strip() if not isinstance(v, (dict, list)) else json.dumps(v, ensure_ascii=False)
    return ""


def _extract_columns_from_meta(meta: dict) -> list[str]:
    """尝试从 metadata_ 中提取列名（schema / columns / fields 等键）。"""
    if not isinstance(meta, dict):
        return []
    for k in ("schema_columns", "columns", "schema", "fields", "字段", "列名"):
        v = meta.get(k)
        if isinstance(v, list):
            return [str(x) for x in v[:50]]
        if isinstance(v, dict):
            return [str(x) for x in list(v.keys())[:50]]
    return []


def _build_limitations(meta: dict, files: list[dict]) -> str:
    """从 metadata_ 推导数据局限性说明。

    优先级：
    1. metadata_["limitations"] / 局限性 / 限制（若有显式字段）
    2. description 截取前 100 字
    3. 否则返回「未提供数据局限性说明」
    """
    if not isinstance(meta, dict):
        return "未提供数据局限性说明"

    for k in ("limitations", "局限性", "限制", "data_limitations", "caveats"):
        v = meta.get(k)
        if v and isinstance(v, str) and v.strip():
            return v.strip()

    desc = _first_match(meta, _METADATA_KEYS_DESCRIPTION)
    if desc:
        return desc[:100] + ("…" if len(desc) > 100 else "")

    if not files:
        return "未提供数据局限性说明"
    return "未提供数据局限性说明"


# ───────── Tool 定义 ─────────


@tool
async def dataset_meta_query(dataset_id: str) -> str:
    """读取数据集的官方元数据（发布机构、覆盖范围、数据局限）。

    用途：
    1. 数据故事开篇的背景信息
    2. 文末数据来源附录
    3. 数据局限性说明

    Args:
        dataset_id: 数据集 ID（来自 kg_query 返回的 dataset_id）

    Returns:
        JSON 字符串，包含：
        - dataset_id
        - title / publisher / issued / update_frequency
        - temporal_coverage / spatial / category / language
        - description / limitations
        - data_files: [{format, size_bytes, uploaded_at}, ...]
        - schema_columns: [...]（若 metadata 中提供）
    """
    if not dataset_id:
        return json.dumps({"error": "dataset_id is required"}, ensure_ascii=False)

    try:
        async with AsyncSessionLocal() as session:
            # 1. 查 datasets 表拿 metadata_
            ds = await session.get(Dataset, dataset_id)
            if ds is None:
                return json.dumps({
                    "error": f"dataset not found: {dataset_id}",
                    "dataset_id": dataset_id,
                }, ensure_ascii=False)
            meta = ds.metadata_ or {}

            # 2. 查 data_downloads 拿文件信息
            dl_result = await download_dao.list_by_dataset(session, dataset_id, page=1, size=10)
            files: list[dict[str, Any]] = []
            if dl_result.get("ok") and dl_result.get("items"):
                for it in dl_result["items"]:
                    files.append({
                        "format": it.get("file_format"),
                        "size_bytes": it.get("file_size"),
                        "uploaded_at": it.get("created_at"),
                        "file_name": it.get("file_name"),
                    })

            # 3. 组装 payload
            payload = {
                "dataset_id": dataset_id,
                "title": _first_match(meta, _METADATA_KEYS_TITLE),
                "publisher": _first_match(meta, _METADATA_KEYS_PUBLISHER),
                "issued": _first_match(meta, _METADATA_KEYS_ISSUED),
                "update_frequency": _first_match(meta, _METADATA_KEYS_UPDATE_FREQ),
                "temporal_coverage": _first_match(meta, _METADATA_KEYS_TEMPORAL),
                "spatial": _first_match(meta, _METADATA_KEYS_SPATIAL),
                "category": _first_match(meta, _METADATA_KEYS_CATEGORY),
                "language": _first_match(meta, _METADATA_KEYS_LANGUAGE) or "zh",
                "description": _first_match(meta, _METADATA_KEYS_DESCRIPTION),
                "limitations": _build_limitations(meta, files),
                "data_files": files,
                "schema_columns": _extract_columns_from_meta(meta),
                "source_url": ds.url,
                "status": ds.status,
                "has_uploaded": bool(ds.has_uploaded),
            }
            return json.dumps(payload, ensure_ascii=False)

    except Exception as e:
        logger.error("[dataset_meta_query] failed for {}: {}", dataset_id, e)
        return json.dumps({
            "error": str(e),
            "dataset_id": dataset_id,
        }, ensure_ascii=False)


__all__ = ["dataset_meta_query"]