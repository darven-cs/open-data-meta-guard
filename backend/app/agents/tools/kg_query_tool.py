"""知识图谱查询工具 — 数据故事 chatbot 用。

供 LLM 通过 @tool 调用，在 Neo4j 知识图谱中搜索实体和数据集。
返回结果会标注哪些数据集已有数据文件（可直接分析），
避免 LLM 在无数据文件的数据集上浪费分析轮次。
"""
import json

from langchain.tools import tool
from sqlalchemy import select, func

from app.core.db import AsyncSessionLocal, get_neo4j_driver
from app.core.log import logger
from app.dao import kg as kg_dao
from app.model.data_download import DataDownload


@tool
async def kg_query(keywords: str) -> str:
    """在知识图谱中搜索与关键词相关的实体和数据集。

    先通过模糊匹配找到相关实体，再查每个实体关联的数据集，
    最后按数据集聚合返回有数据文件（已上传）的结果。

    Args:
        keywords: 搜索关键词（支持中英文），多个关键词用空格分隔，如 "财政 经济 交通"

    Returns:
        JSON 字符串：{entities: [...], datasets: [...], similar_groups: [...]}
    """
    if not keywords or not keywords.strip():
        return json.dumps({"entities": [], "datasets": [], "similar_groups": []}, ensure_ascii=False)

    try:
        driver = get_neo4j_driver()
    except RuntimeError as e:
        logger.error("[kg_query] Neo4j driver not available: {}", e)
        return json.dumps({
            "entities": [],
            "datasets": [],
            "error": "知识图谱不可用，请先构建图谱",
        }, ensure_ascii=False)

    # 1. 按关键词搜索实体
    keywords_list = [kw.strip() for kw in keywords.split() if kw.strip()]
    all_entities: dict[str, dict] = {}

    for kw in keywords_list:
        result = await kg_dao.search_entities_by_keyword(driver, kw, limit=10)
        if result.get("ok") and result.get("entities"):
            for ent in result["entities"]:
                key = ent["id"]
                if key not in all_entities:
                    all_entities[key] = ent

    if not all_entities:
        return json.dumps({
            "entities": [],
            "datasets": [],
            "similar_groups": [],
        }, ensure_ascii=False)

    # 2. 对有数据集关联的实体，查详细 dataset 列表
    entities_with_datasets: list[dict] = []
    all_dataset_ids: set[str] = set()

    for ent in list(all_entities.values()):
        if ent["dataset_count"] > 0:
            ds_result = await kg_dao.get_datasets_by_entity(
                driver, ent["name"], ent["type"]
            )
            if ds_result.get("ok") and ds_result.get("datasets"):
                ent_copy = dict(ent)
                ent_copy["datasets"] = ds_result["datasets"]
                entities_with_datasets.append(ent_copy)
                for ds in ds_result["datasets"]:
                    all_dataset_ids.add(ds["dataset_id"])

    # 3. 交叉查 PG：标记哪些数据集已有数据文件（可直接分析）
    datasets_with_files: set[str] = set()
    if all_dataset_ids:
        try:
            async with AsyncSessionLocal() as session:
                stmt = (
                    select(DataDownload.dataset_id)
                    .where(DataDownload.dataset_id.in_(list(all_dataset_ids)))
                    .distinct()
                )
                result = await session.execute(stmt)
                datasets_with_files = {row[0] for row in result.fetchall()}
        except Exception as e:
            logger.warning("[kg_query] failed to check data_downloads: {}", e)

    # 标记 entities 中哪些有数据文件
    for ent in entities_with_datasets:
        ent["has_data_files"] = any(
            d["dataset_id"] in datasets_with_files for d in ent.get("datasets", [])
        )

    # 4. 返回聚合结果
    return json.dumps({
        "entities": entities_with_datasets,
        "datasets": sorted(list(all_dataset_ids)),
        "datasets_with_files": sorted(list(datasets_with_files)),
        "similar_groups": [],  # 预留
    }, ensure_ascii=False)


__all__ = ["kg_query"]
