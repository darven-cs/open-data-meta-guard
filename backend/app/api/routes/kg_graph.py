"""知识图谱 API 路由（Phase 5）。

路由（prefix=`/kg`）：
    POST   /kg/build              全量重建图谱
    GET    /kg/graph              获取图数据（支持 entity_types 过滤）
    GET    /kg/entities           分页实体列表（支持 type 过滤）
    GET    /kg/entities/{id}      实体详情 + 关联数据集
    GET    /kg/datasets/{id}/relations  数据集的所有关系
"""
from fastapi import APIRouter, Depends, Query
from neo4j import AsyncDriver
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.resp import ResponseModel
from app.core.db import get_db, get_neo4j_driver
from app.dao import kg as kg_dao
from app.schemas.kg import (
    EntityDetail,
    EntityListItem,
    EntityListResponse,
    GraphNode,
    GraphEdge,
    GraphResponse,
    KgBuildResult,
)
from app.service import kg as kg_service

router = APIRouter(prefix="/kg", tags=["kg"])


@router.post("/build", response_model=ResponseModel)
async def build_graph(
    pg_session: AsyncSession = Depends(get_db),
):
    """全量重建知识图谱：清空旧图 → 重新抽取 → 写入 → 计算相似度。"""
    try:
        driver = get_neo4j_driver()
    except RuntimeError as e:
        return ResponseModel.fail(code=503, msg=str(e))

    result = await kg_service.build_knowledge_graph(
        driver=driver,
        pg_session=pg_session,
    )
    if not result.get("ok"):
        return ResponseModel.fail(code=500, msg=result.get("error", "build failed"))

    payload = KgBuildResult(
        datasets_processed=result["datasets_processed"],
        entities_upserted=result["entities_upserted"],
        relationships_created=result["relationships_created"],
        similar_edges=result["similar_edges"],
        errors=result.get("errors", []),
    )
    return ResponseModel.success(payload.model_dump(), msg="知识图谱构建完成")


@router.get("/graph", response_model=ResponseModel)
async def get_graph(
    entity_types: str = Query(
        default="",
        description="逗号分隔的实体类型，如 Publisher,Theme,Keyword；空=全部",
    ),
):
    """获取知识图谱图数据（节点 + 边）。"""
    try:
        driver = get_neo4j_driver()
    except RuntimeError as e:
        return ResponseModel.fail(code=503, msg=str(e))

    types = [t.strip() for t in entity_types.split(",") if t.strip()] or None
    result = await kg_dao.get_graph(driver, entity_types=types)
    if not result.get("ok"):
        return ResponseModel.fail(code=500, msg=result.get("error", "query failed"))

    payload = GraphResponse(
        nodes=[GraphNode(**n) for n in result["nodes"]],
        edges=[GraphEdge(**e) for e in result["edges"]],
    )
    return ResponseModel.success(payload.model_dump())


@router.get("/entities", response_model=ResponseModel)
async def list_entities(
    type: str = Query(default="", description="实体类型过滤：Publisher / Theme / Keyword / Format"),
    page: int = Query(1, ge=1, description="页码（1-based）"),
    size: int = Query(20, ge=1, le=100, description="每页条数"),
):
    """分页实体列表。"""
    try:
        driver = get_neo4j_driver()
    except RuntimeError as e:
        return ResponseModel.fail(code=503, msg=str(e))

    entity_type = type.strip() or None
    result = await kg_dao.list_entities(
        driver=driver,
        entity_type=entity_type,
        page=page,
        size=size,
    )
    if not result.get("ok"):
        return ResponseModel.fail(code=500, msg=result.get("error", "query failed"))

    payload = EntityListResponse(
        items=[EntityListItem(**it) for it in result["items"]],
        page=result["page"],
        size=result["size"],
        count=result["count"],
    )
    return ResponseModel.success(payload.model_dump())


@router.get("/entities/{entity_id}", response_model=ResponseModel)
async def get_entity_detail(entity_id: str):
    """实体详情 + 关联数据集列表。"""
    try:
        driver = get_neo4j_driver()
    except RuntimeError as e:
        return ResponseModel.fail(code=503, msg=str(e))

    result = await kg_dao.get_entity_detail(driver, entity_id)
    if not result.get("ok"):
        return ResponseModel.fail(
            code=404,
            msg=result.get("error", "entity not found"),
        )

    ent = result["entity"]
    payload = EntityDetail(
        id=ent["id"],
        type=ent["type"],
        name=ent["name"],
        related_datasets=ent.get("related_datasets", []),
    )
    return ResponseModel.success(payload.model_dump())


@router.get("/datasets/{dataset_id}/relations", response_model=ResponseModel)
async def get_dataset_relations(dataset_id: str):
    """数据集的所有关系。"""
    try:
        driver = get_neo4j_driver()
    except RuntimeError as e:
        return ResponseModel.fail(code=503, msg=str(e))

    result = await kg_dao.get_dataset_relations(driver, dataset_id)
    if not result.get("ok"):
        return ResponseModel.fail(code=500, msg=result.get("error", "query failed"))

    payload = GraphResponse(
        nodes=[GraphNode(**n) for n in result["nodes"]],
        edges=[GraphEdge(**e) for e in result["edges"]],
    )
    return ResponseModel.success(payload.model_dump())
