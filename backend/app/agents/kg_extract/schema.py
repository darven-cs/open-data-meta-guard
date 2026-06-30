"""知识图谱实体抽取 Pydantic 输出契约。

实体类型和关系类型对齐 Neo4j Labeled Property Graph Schema。
"""
from typing import Literal

from pydantic import BaseModel, Field


# ───────── 实体类型 ─────────
EntityType = Literal["publisher", "theme", "keyword", "format"]
RelationType = Literal["PUBLISHED_BY", "HAS_THEME", "HAS_KEYWORD", "HAS_FORMAT"]


class ExtractedEntity(BaseModel):
    """单个实体。"""

    type: EntityType = Field(description="实体类型：publisher / theme / keyword / format")
    name: str = Field(description="实体标准化名称（去重用），如「中华人民共和国财政部」")
    source_field: str = Field(default="", description="来源元数据字段名，如 publisher / theme / keyword / format")


class ExtractedRelationship(BaseModel):
    """实体与 Dataset 之间的关系（由 LLM 推断置信度）。"""

    entity_type: EntityType = Field(description="关联的实体类型")
    entity_name: str = Field(description="关联的实体名称（与 ExtractedEntity.name 一致）")
    relation: RelationType = Field(description="关系类型：PUBLISHED_BY / HAS_THEME / HAS_KEYWORD / HAS_FORMAT")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="LLM 推断置信度")


class KgExtractResult(BaseModel):
    """LLM 从单条 metadata dict 中抽取的实体和关系。"""

    entities: list[ExtractedEntity] = Field(
        description="从 metadata 中识别到的实体列表",
    )
    relationships: list[ExtractedRelationship] = Field(
        description="数据集与实体之间的关系列表",
    )
