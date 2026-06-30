"""知识图谱构建 service 层。

build_knowledge_graph(driver, pg_session):
    1. 从 PostgreSQL 读取所有 status='scraped' 的 datasets
    2. 分批（5 个一批）调 LLM 抽取实体和关系
    3. 批量写入 Neo4j（MERGE 节点 + CREATE 关系）
    4. 计算 Dataset-Dataset Jaccard 相似度 → [:SIMILAR_TO] 边
    5. 返回构建统计
"""
from neo4j import AsyncDriver
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.kg_extract import build as build_extractor, KgExtractResult
from app.core.log import logger
from app.dao import dataset as dataset_dao
from app.dao import kg as kg_dao


BATCH_SIZE = 5


async def build_knowledge_graph(
    driver: AsyncDriver,
    pg_session: AsyncSession,
) -> dict:
    """全量重建知识图谱。

    Args:
        driver: Neo4j AsyncDriver 实例
        pg_session: PostgreSQL AsyncSession

    Returns:
        {"ok": True, **KgBuildResult}
        {"ok": False, "error": "..."}
    """
    extractor = build_extractor()
    if extractor is None:
        return {"ok": False, "error": "LLM not configured (check LLM_BASE_URL / LLM_MODEL / LLM_API_KEY)"}

    # 1) 清空旧图
    clear_res = await kg_dao.clear_graph(driver)
    if not clear_res.get("ok"):
        return {"ok": False, "error": f"clear graph failed: {clear_res.get('error')}"}

    # 2) 读所有 scraped datasets
    list_res = await dataset_dao.list_datasets(
        session=pg_session,
        page=1,
        size=10000,
        status="scraped",
    )
    if not list_res.get("ok"):
        return {"ok": False, "error": f"list datasets failed: {list_res.get('error')}"}

    datasets = list_res["items"]
    if not datasets:
        return {
            "ok": True,
            "datasets_processed": 0,
            "entities_upserted": 0,
            "relationships_created": 0,
            "similar_edges": 0,
            "errors": [],
        }

    logger.info("[kg-service] building knowledge graph from {} datasets", len(datasets))

    all_entities: list[dict] = []
    all_relationships: list[dict] = []
    errors: list[str] = []

    # 3) 分批调 LLM 抽取
    for i in range(0, len(datasets), BATCH_SIZE):
        batch = datasets[i:i + BATCH_SIZE]
        for ds in batch:
            ds_id = ds["id"]
            metadata = ds.get("metadata", {})
            if not metadata:
                continue

            try:
                payload = f"dataset_id: {ds_id}\nmetadata: {metadata}"
                result: KgExtractResult = await extractor.ainvoke({"input": payload})

                # 收集实体
                for ent in result.entities:
                    all_entities.append({
                        "type": ent.type.capitalize(),
                        "name": ent.name,
                        "source_field": ent.source_field,
                    })

                # 收集关系
                for rel in result.relationships:
                    all_relationships.append({
                        "entity_type": rel.entity_type.capitalize(),
                        "entity_name": rel.entity_name,
                        "relation": rel.relation,
                        "confidence": rel.confidence,
                        "dataset_id": ds_id,
                    })

                logger.debug(
                    "[kg-service] extracted {} entities, {} rels from {}",
                    len(result.entities),
                    len(result.relationships),
                    ds_id[:12],
                )
            except Exception as e:
                err_msg = f"extract failed for {ds_id[:16]}: {e}"
                logger.warning("[kg-service] {}", err_msg)
                errors.append(err_msg)

    # 4) 批量写入 Neo4j
    # 去重实体
    seen_entities: set[tuple[str, str]] = set()
    deduped_entities: list[dict] = []
    for ent in all_entities:
        key = (ent["type"], ent["name"])
        if key not in seen_entities:
            seen_entities.add(key)
            deduped_entities.append(ent)

    entities_upserted = await kg_dao.merge_entities_batch(driver, deduped_entities)
    rels_created = await kg_dao.create_relationships_batch(driver, all_relationships)

    # 5) Jaccard 相似度
    try:
        similar_edges = await kg_dao.compute_similarity(driver)
    except Exception as e:
        logger.warning("[kg-service] similarity computation failed: {}", e)
        similar_edges = 0
        errors.append(f"similarity computation: {e}")

    logger.info(
        "[kg-service] build complete: {} datasets, {} entities, {} rels, {} similar",
        len(datasets), entities_upserted, rels_created, similar_edges,
    )

    return {
        "ok": True,
        "datasets_processed": len(datasets),
        "entities_upserted": entities_upserted,
        "relationships_created": rels_created,
        "similar_edges": similar_edges,
        "errors": errors,
    }
