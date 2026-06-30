"""知识图谱 DAO 层 — Neo4j Cypher 操作。

所有函数使用 neo4j.AsyncDriver 直接执行 Cypher。
"""
from typing import Any

from neo4j import AsyncDriver, AsyncManagedTransaction

from app.core.config import settings
from app.core.log import logger

# ───────── 图清理 ─────────


async def clear_graph(driver: AsyncDriver) -> dict:
    """清空整个图（DETACH DELETE 所有节点和关系）。

    Returns:
        {"ok": True} / {"ok": False, "error": "..."}
    """
    try:
        async with driver.session(database=settings.neo4j_database) as session:
            await session.run("MATCH (n) DETACH DELETE n")
        logger.info("[kg-dao] graph cleared")
        return {"ok": True}
    except Exception as e:
        logger.error("[kg-dao] clear_graph failed: {}", e)
        return {"ok": False, "error": str(e)}


# ───────── 批量写入 ─────────


async def merge_entities_batch(driver: AsyncDriver, entities: list[dict]) -> int:
    """批量 MERGE 实体节点。

    Args:
        entities: [{"type": "Publisher", "name": "...", "source_field": "..."}, ...]
                  注意 type 首字母大写（Neo4j Label 名）

    Returns:
        实际 upsert 数量
    """
    if not entities:
        return 0

    query = """
    UNWIND $entities AS e
    CALL apoc.merge.node([e.type], {name: e.name}, {source_field: e.source_field})
    YIELD node
    RETURN count(node) AS n
    """
    try:
        async with driver.session(database=settings.neo4j_database) as session:
            result = await session.run(query, {"entities": entities})
            record = await result.single()
            cnt = record["n"] if record else 0
            logger.debug("[kg-dao] merged {} entities", cnt)
            return cnt
    except Exception as e:
        # apoc 可能不可用，fallback 到逐条 MERGE
        logger.warning("[kg-dao] apoc merge failed, falling back to per-node MERGE: {}", e)
        return await _merge_entities_fallback(driver, entities)


async def _merge_entities_fallback(driver: AsyncDriver, entities: list[dict]) -> int:
    """不使用 apoc 的 fallback 批量 MERGE。"""
    count = 0
    async with driver.session(database=settings.neo4j_database) as session:
        for ent in entities:
            label = ent["type"]
            name = ent["name"]
            props = {k: v for k, v in ent.items() if k not in ("type", "name") and v}
            cypher = (
                f"MERGE (n:{label} {{name: $name}}) "
                f"SET n += $props "
                f"RETURN n.name AS name"
            )
            try:
                result = await session.run(cypher, {"name": name, "props": props})
                await result.single()
                count += 1
            except Exception as e:
                logger.warning("[kg-dao] merge entity failed: {} {} — {}", label, name, e)
    return count


async def create_relationships_batch(
    driver: AsyncDriver,
    rels: list[dict],
) -> int:
    """批量 CREATE 关系（Dataset 到实体）。

    Args:
        rels: [{"entity_type": "Publisher", "entity_name": "...",
                 "relation": "PUBLISHED_BY", "confidence": 1.0,
                 "dataset_id": "sha256hex"}]

    Returns:
        创建的关系数量
    """
    if not rels:
        return 0

    query = """
    UNWIND $rels AS r
    MATCH (e:{label} {name: r.entity_name})
    MERGE (d:Dataset {dataset_id: r.dataset_id})
    WITH d, e, r
    CALL apoc.create.relationship(d, r.relation, {confidence: r.confidence}, e) YIELD rel
    RETURN count(rel) AS n
    """

    # 按实体类型分组执行（UNWIND 中的 label 无法参数化）
    from collections import defaultdict
    grouped: dict[str, list[dict]] = defaultdict(list)
    for rel in rels:
        grouped[rel["entity_type"]].append(rel)

    total = 0
    async with driver.session(database=settings.neo4j_database) as session:
        for label, group in grouped.items():
            try:
                params = {"rels": group}
                result = await session.run(
                    query.replace("{label}", label),
                    params,
                )
                record = await result.single()
                total += record["n"] if record else 0
            except Exception as e:
                logger.warning("[kg-dao] apoc create rel failed, fallback: {}", e)
                total += await _create_relationships_fallback(session, group, label)

    logger.debug("[kg-dao] created {} relationships", total)
    return total


async def _create_relationships_fallback(
    session, rels: list[dict], label: str,
) -> int:
    """不使用 apoc 的 fallback 逐条 CREATE 关系。"""
    count = 0
    for rel in rels:
        cypher = (
            f"MATCH (e:{label} {{name: $entity_name}}) "
            f"MERGE (d:Dataset {{dataset_id: $dataset_id}}) "
            f"CREATE (d)-[r:{rel['relation']} {{confidence: $confidence}}]->(e) "
            f"RETURN count(r) AS n"
        )
        try:
            result = await session.run(cypher, {
                "entity_name": rel["entity_name"],
                "dataset_id": rel["dataset_id"],
                "confidence": rel.get("confidence", 1.0),
            })
            await result.single()
            count += 1
        except Exception as e:
            logger.warning("[kg-dao] create rel fallback failed: {}", e)
    return count


# ───────── 图查询 ─────────


async def get_graph(
    driver: AsyncDriver,
    entity_types: list[str] | None = None,
) -> dict:
    """获取图数据（节点 + 关系），支持实体类型过滤。

    Args:
        entity_types: None 或空列表表示全部；否则只匹配指定实体类型

    Returns:
        {"ok": True, "nodes": [...], "edges": [...]}
    """
    nodes: list[dict] = []
    edges: list[dict] = []
    seen_node_keys: set[str] = set()

    type_filter = _build_type_filter(entity_types)
    cypher = f"""
    MATCH (d:Dataset)-[r]->(e)
    WHERE d.dataset_id IS NOT NULL AND {type_filter}
    RETURN
      d.dataset_id AS dataset_id,
      labels(e) AS e_labels,
      e.name AS e_name,
      e.source_field AS e_source_field,
      type(r) AS rel_type,
      r.confidence AS confidence
    """

    try:
        async with driver.session(database=settings.neo4j_database) as session:
            result = await session.run(cypher)
            async for record in result:
                dataset_id = record.get("dataset_id")
                e_labels = record.get("e_labels")
                e_name = record.get("e_name")
                e_source = record.get("e_source_field", "") or ""
                rel_type = record.get("rel_type")
                confidence = record.get("confidence", 1.0) or 1.0

                # 防御：跳过 null/空值记录
                if not dataset_id or not e_name or not rel_type:
                    continue
                if not e_labels:
                    continue

                # Dataset 节点（去重）
                d_key = f"Dataset:{dataset_id}"
                if d_key not in seen_node_keys:
                    seen_node_keys.add(d_key)
                    nodes.append({
                        "id": dataset_id,
                        "type": "Dataset",
                        "label": dataset_id[:12] + "…",
                    })

                # 实体节点（去重）
                for lbl in e_labels:
                    if lbl == "Dataset":
                        continue
                    e_key = f"{lbl}:{e_name}"
                    if e_key not in seen_node_keys:
                        seen_node_keys.add(e_key)
                        node_id = f"{lbl}:{e_name}"
                        nodes.append({
                            "id": node_id,
                            "type": lbl,
                            "label": e_name,
                            "source_field": e_source,
                        })

                    # 边
                    edges.append({
                        "source": dataset_id,
                        "target": e_key,
                        "type": rel_type,
                        "weight": float(confidence),
                    })

        return {"ok": True, "nodes": nodes, "edges": edges}
    except Exception as e:
        logger.error("[kg-dao] get_graph failed: {}", e)
        return {"ok": False, "error": str(e)}


def _build_type_filter(entity_types: list[str] | None) -> str:
    """构建 Cypher WHERE 子句过滤实体类型。"""
    if not entity_types:
        return "e IS NOT NULL"

    labels_upper = [t.capitalize() for t in entity_types]
    conds = " OR ".join(f"'{lbl}' IN labels(e)" for lbl in labels_upper)
    return f"({conds})"


async def get_entity_detail(
    driver: AsyncDriver,
    entity_id: str,
) -> dict:
    """实体详情（基本信息 + 关联数据集列表）。

    Args:
        entity_id: "{Label}:{name}" 格式，如 "Publisher:中华人民共和国财政部"

    Returns:
        {"ok": True, "entity": {...}} / {"ok": False, "error": "..."}
    """
    if ":" not in entity_id:
        return {"ok": False, "error": "invalid entity_id format, expected Label:name"}

    label, name = entity_id.split(":", 1)
    cypher = f"""
    MATCH (e:{label} {{name: $name}})<-[r]-(d:Dataset)
    RETURN e.name AS name, labels(e) AS labels,
           collect({{dataset_id: d.dataset_id, rel_type: type(r), confidence: r.confidence}}) AS datasets
    """

    try:
        async with driver.session(database=settings.neo4j_database) as session:
            result = await session.run(cypher, {"name": name})
            record = await result.single()
            if not record:
                return {"ok": False, "error": f"entity not found: {entity_id}"}

            for lbl in record["labels"]:
                if lbl != "Dataset":
                    label = lbl
                    break

            return {
                "ok": True,
                "entity": {
                    "id": entity_id,
                    "type": label,
                    "name": record["name"],
                    "related_datasets": record["datasets"] or [],
                },
            }
    except Exception as e:
        logger.error("[kg-dao] get_entity_detail failed: {}", e)
        return {"ok": False, "error": str(e)}


async def list_entities(
    driver: AsyncDriver,
    entity_type: str | None = None,
    page: int = 1,
    size: int = 20,
) -> dict:
    """分页实体列表，支持按类型过滤。

    Returns:
        {"ok": True, "items": [...], "page": int, "size": int, "count": int}
    """
    if page < 1:
        page = 1
    if size < 1 or size > 100:
        size = 20

    labels = [entity_type.capitalize()] if entity_type else ["Publisher", "Theme", "Keyword", "Format"]

    all_items: list[dict] = []
    for label in labels:
        cypher = (
            f"MATCH (e:{label}) "
            f"OPTIONAL MATCH (d:Dataset)-[:{_rel_for_label(label)}]->(e) "
            f"RETURN e.name AS name, '{label}' AS type, count(d) AS dataset_count "
            f"ORDER BY dataset_count DESC"
        )
        try:
            async with driver.session(database=settings.neo4j_database) as session:
                result = await session.run(cypher)
                async for record in result:
                    eid = f"{record['type']}:{record['name']}"
                    all_items.append({
                        "id": eid,
                        "type": record["type"],
                        "name": record["name"],
                        "dataset_count": record["dataset_count"],
                    })
        except Exception as e:
            logger.warning("[kg-dao] list_entities failed for {}: {}", label, e)

    # 分页
    offset = (page - 1) * size
    page_items = all_items[offset:offset + size]

    return {
        "ok": True,
        "items": page_items,
        "page": page,
        "size": size,
        "count": len(all_items),
    }


def _rel_for_label(label: str) -> str:
    mapping = {
        "Publisher": "PUBLISHED_BY",
        "Theme": "HAS_THEME",
        "Keyword": "HAS_KEYWORD",
        "Format": "HAS_FORMAT",
    }
    return mapping.get(label, "RELATED_TO")


async def get_dataset_relations(
    driver: AsyncDriver,
    dataset_id: str,
) -> dict:
    """查询数据集的所有关系。

    Returns:
        {"ok": True, "nodes": [...], "edges": [...]}
    """
    cypher = """
    MATCH (d:Dataset {dataset_id: $dataset_id})-[r]->(e)
    RETURN
      d.dataset_id AS dataset_id,
      labels(e) AS e_labels, e.name AS e_name,
      type(r) AS rel_type, r.confidence AS confidence
    """

    nodes: list[dict] = []
    edges: list[dict] = []
    seen_nodes: set[str] = set()

    try:
        async with driver.session(database=settings.neo4j_database) as session:
            result = await session.run(cypher, {"dataset_id": dataset_id})
            async for record in result:
                e_labels = record.get("e_labels")
                e_name = record.get("e_name")
                rel_type = record.get("rel_type")
                confidence = record.get("confidence", 1.0) or 1.0

                if not e_name or not rel_type or not e_labels:
                    continue

                for lbl in e_labels:
                    if lbl == "Dataset":
                        continue
                    e_key = f"{lbl}:{e_name}"
                    if e_key not in seen_nodes:
                        seen_nodes.add(e_key)
                        nodes.append({
                            "id": e_key,
                            "type": lbl,
                            "label": e_name,
                        })
                    edges.append({
                        "source": dataset_id,
                        "target": e_key,
                        "type": rel_type,
                        "weight": float(confidence),
                    })

        # 添加 Dataset 自身节点
        if seen_nodes:
            nodes.insert(0, {
                "id": dataset_id,
                "type": "Dataset",
                "label": dataset_id[:12] + "…",
            })

        return {"ok": True, "nodes": nodes, "edges": edges}
    except Exception as e:
        logger.error("[kg-dao] get_dataset_relations failed: {}", e)
        return {"ok": False, "error": str(e)}


# ───────── Jaccard 相似度 ─────────


# ───────── 关键词搜索（Phase 6 数据故事 chatbot）─────────


async def search_entities_by_keyword(
    driver: AsyncDriver,
    keyword: str,
    entity_types: list[str] | None = None,
    limit: int = 10,
) -> dict:
    """关键词搜索实体（模糊匹配实体名）。

    Args:
        keyword: 搜索关键词
        entity_types: None 或空列表表示全部类型；否则只匹配指定类型
        limit: 最大返回条数

    Returns:
        {"ok": True, "entities": [...]} / {"ok": False, "error": "..."}
    """
    if not keyword or not keyword.strip():
        return {"ok": True, "entities": []}

    labels = (
        [t.capitalize() for t in entity_types]
        if entity_types
        else ["Publisher", "Theme", "Keyword", "Format"]
    )

    all_entities: list[dict] = []
    seen: set[str] = set()

    async with driver.session(database=settings.neo4j_database) as session:
        for label in labels:
            cypher = f"""
            MATCH (e:{label})
            WHERE e.name CONTAINS $keyword
            OPTIONAL MATCH (d:Dataset)-[:{_rel_for_label(label)}]->(e)
            OPTIONAL MATCH (e)-[r]-(d2:Dataset)
            RETURN e.name AS name, '{label}' AS type, count(DISTINCT d2) AS dataset_count
            ORDER BY dataset_count DESC
            LIMIT $limit
            """
            try:
                result = await session.run(
                    cypher, {"keyword": keyword.strip(), "limit": limit}
                )
                async for record in result:
                    key = f"{record['type']}:{record['name']}"
                    if key not in seen:
                        seen.add(key)
                        all_entities.append({
                            "id": key,
                            "type": record["type"],
                            "name": record["name"],
                            "dataset_count": record["dataset_count"],
                        })
            except Exception as e:
                logger.warning(
                    "[kg-dao] search_entities_by_keyword failed for {}: {}", label, e
                )

    # 按关联数据集数量降序, 截断 limit
    all_entities.sort(key=lambda x: x["dataset_count"], reverse=True)
    return {"ok": True, "entities": all_entities[:limit]}


async def get_datasets_by_entity(
    driver: AsyncDriver,
    entity_name: str,
    entity_type: str,
) -> dict:
    """获取关联到某实体的所有 dataset 信息。

    Args:
        entity_name: 实体名称
        entity_type: 实体类型（如 Publisher / Theme / Keyword / Format）

    Returns:
        {"ok": True, "datasets": [...]} / {"ok": False, "error": "..."}
    """
    if not entity_name or not entity_type:
        return {"ok": False, "error": "entity_name and entity_type are required"}

    label = entity_type.capitalize()
    rel = _rel_for_label(label)
    cypher = f"""
    MATCH (e:{label} {{name: $name}})<-[r]-(d:Dataset)
    RETURN d.dataset_id AS dataset_id, type(r) AS rel_type, r.confidence AS confidence
    ORDER BY r.confidence DESC
    LIMIT 50
    """

    try:
        async with driver.session(database=settings.neo4j_database) as session:
            result = await session.run(cypher, {"name": entity_name})
            datasets: list[dict] = []
            async for record in result:
                datasets.append({
                    "dataset_id": record["dataset_id"],
                    "rel_type": record["rel_type"],
                    "confidence": record["confidence"] or 1.0,
                })
        return {"ok": True, "datasets": datasets}
    except Exception as e:
        logger.error("[kg-dao] get_datasets_by_entity failed: {}", e)
        return {"ok": False, "error": str(e)}


async def compute_similarity(driver: AsyncDriver) -> int:
    """计算 Dataset-Dataset Jaccard 相似度 → [:SIMILAR_TO] 边。

    阈值：Jaccard >= 0.3（避免全连接图）。
    每个方向只保留一条边（无向），去重。

    Returns:
        创建的 SIMILAR_TO 边数量
    """
    cypher = """
    MATCH (d1:Dataset)
    MATCH (d2:Dataset)
    WHERE id(d1) < id(d2)
      AND d1.dataset_id <> d2.dataset_id
    OPTIONAL MATCH (d1)-[r1]->(e)
    OPTIONAL MATCH (d2)-[r2]->(e)
    WITH d1, d2, count(DISTINCT e) AS shared,
         d1_neighbors, d2_neighbors
    """
    # 简化实现：用 Python 端计算，避免复杂 Cypher
    return await _compute_similarity_python(driver)


async def _compute_similarity_python(driver: AsyncDriver) -> int:
    """Python 端计算 Jaccard 相似度。"""
    # 1. 获取所有 Dataset 及其关联实体
    query = """
    MATCH (d:Dataset)-[r]->(e)
    RETURN d.dataset_id AS dataset_id, collect(DISTINCT {label: head(labels(e)), name: e.name}) AS entities
    """
    dataset_entities: dict[str, set[tuple[str, str]]] = {}

    try:
        async with driver.session(database=settings.neo4j_database) as session:
            result = await session.run(query)
            async for record in result:
                ds_id = record["dataset_id"]
                ents = set()
                for ent in record["entities"]:
                    ents.add((ent["label"], ent["name"]))
                dataset_entities[ds_id] = ents
    except Exception as e:
        logger.error("[kg-dao] compute_similarity fetch failed: {}", e)
        return 0

    # 2. 计算 Jaccard 并写入
    created = 0
    ds_ids = list(dataset_entities.keys())
    edge_cypher = """
    MATCH (d1:Dataset {dataset_id: $id1})
    MATCH (d2:Dataset {dataset_id: $id2})
    MERGE (d1)-[r:SIMILAR_TO {jaccard: $jaccard}]-(d2)
    RETURN count(r) AS n
    """

    async with driver.session(database=settings.neo4j_database) as session:
        for i in range(len(ds_ids)):
            for j in range(i + 1, len(ds_ids)):
                id1, id2 = ds_ids[i], ds_ids[j]
                set1, set2 = dataset_entities[id1], dataset_entities[id2]

                if not set1 or not set2:
                    continue

                intersection = len(set1 & set2)
                union = len(set1 | set2)
                if union == 0:
                    continue

                jaccard = intersection / union
                if jaccard < 0.3:
                    continue

                try:
                    result = await session.run(edge_cypher, {
                        "id1": id1,
                        "id2": id2,
                        "jaccard": round(jaccard, 4),
                    })
                    record = await result.single()
                    created += record["n"] if record else 0
                except Exception as e:
                    logger.warning("[kg-dao] similarity edge failed: {}~{} — {}", id1[:8], id2[:8], e)

    logger.info("[kg-dao] created {} SIMILAR_TO edges", created)
    return created
