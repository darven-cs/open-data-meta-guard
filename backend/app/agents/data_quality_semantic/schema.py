"""语义层数据质量评估输出契约（Zhai Jun 29 类脏数据类型 + 8 维度）。"""

from typing import Literal

from pydantic import BaseModel, Field


class SemanticIssue(BaseModel):
    """单条语义层脏数据问题。"""

    category: str = Field(
        description='脏数据类型编号，如 "D8" "D9" … "D29"',
    )
    severity: Literal["error", "warning", "info"] = Field(
        description="严重程度：error 数据不可用 / warning 需关注 / info 建议优化",
    )
    dimension: str = Field(
        description="所属评估维度：Completeness / Consistency / Accuracy / Timeliness / Uniqueness / Normativity / Openness / Security",
    )
    field: str | None = Field(
        default=None,
        description="涉及的具体字段名（可为空，如 D21 过时数据针对全表）",
    )
    description: str = Field(
        description="问题描述（中文，200 字以内，含具体行/列定位）",
    )
    suggestion: str = Field(
        description="修复建议（中文，100 字以内）",
    )


class DimensionScores(BaseModel):
    """8 个评估维度评分（1-100，越高越好）。"""

    completeness: int = Field(description="完整性", ge=1, le=100, default=100)
    consistency: int = Field(description="一致性", ge=1, le=100, default=100)
    accuracy: int = Field(description="准确性", ge=1, le=100, default=100)
    timeliness: int = Field(description="时效性", ge=1, le=100, default=100)
    uniqueness: int = Field(description="唯一性", ge=1, le=100, default=100)
    normativity: int = Field(description="规范性", ge=1, le=100, default=100)
    openness: int = Field(description="开放性", ge=1, le=100, default=100)
    security: int = Field(description="安全性/隐私性", ge=1, le=100, default=100)


class SemanticQualityOutput(BaseModel):
    """语义层数据质量评估输出。

    Agent 必须按此 schema 返回结构化结果，不得编造不存在的数据。
    """

    dimension_scores: DimensionScores = Field(
        description="8 维度评分（每个维度 1-100）",
    )
    issues: list[SemanticIssue] = Field(
        description="检出的语义层脏数据问题列表",
    )
    summary: str = Field(
        description="语义评估结论（中文，200 字以内，含总体质量判断和修复优先级）",
    )
    overall_score: int = Field(
        description="综合语义质量评分（1-100）",
        ge=1, le=100,
    )
