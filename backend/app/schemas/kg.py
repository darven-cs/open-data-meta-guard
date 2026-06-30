"""知识图谱 API Schema — `/kg/*` 请求/响应模型。"""
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class GraphNode(BaseModel):
    """图节点。"""
    id: str = Field(description="节点唯一标识")
    type: Literal["Dataset", "Publisher", "Theme", "Keyword", "Format"] = Field(description="节点类型")
    label: str = Field(description="显示标签")
    source_field: Optional[str] = Field(default=None, description="来源元数据字段")


class GraphEdge(BaseModel):
    """图边。"""
    source: str = Field(description="源节点 id")
    target: str = Field(description="目标节点 id")
    type: str = Field(description="关系类型")
    weight: float = Field(default=1.0, description="权重")


class GraphResponse(BaseModel):
    """图数据响应。"""
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class KgBuildResult(BaseModel):
    """图谱构建结果。"""
    datasets_processed: int = Field(description="处理的 datasets 数")
    entities_upserted: int = Field(description="upsert 的实体数")
    relationships_created: int = Field(description="创建的关系数")
    similar_edges: int = Field(description="Jaccard 相似边数")
    errors: list[str] = Field(default_factory=list, description="处理中的错误列表")


class EntityListItem(BaseModel):
    """实体列表项。"""
    id: str = Field(description="实体 ID（Label:name 格式）")
    type: str = Field(description="实体类型")
    name: str = Field(description="实体名称")
    dataset_count: int = Field(description="关联数据集数量")


class EntityListResponse(BaseModel):
    """实体列表响应。"""
    items: list[EntityListItem]
    page: int
    size: int
    count: int


class EntityDetail(BaseModel):
    """实体详情。"""
    id: str
    type: str
    name: str
    related_datasets: list[dict[str, Any]] = Field(
        default_factory=list,
        description="关联数据集列表",
    )
