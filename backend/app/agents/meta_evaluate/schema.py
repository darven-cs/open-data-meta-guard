"""meta_evaluate 输出契约（EU MQA 405 分制 + 23 条规则）。"""
from typing import Literal

from pydantic import BaseModel, Field


# EU MQA 405 分制 = 5 维度 + 23 条规则
# rule_scores 必须用以下 23 个 indicator 名（agent 不得自创 key）：
EU_MQA_RULE_KEYS = [
    # Findability 4 条
    "keyword_usage", "categories", "geo_search", "time_based_search",
    # Accessibility 3 条
    "access_url_accessibility", "download_url", "download_url_accessibility",
    # Interoperability 6 条
    "format", "media_type", "format_vocabulary", "non_proprietary",
    "machine_readable", "dcat_ap_compliance",
    # Reusability 6 条
    "license_information", "license_vocabulary", "access_restrictions",
    "access_restrictions_vocabulary", "contact_point", "publisher",
    # Contextuality 4 条
    "rights", "file_size", "date_of_issue", "modification_date",
]


# EU MQA 23 条 indicator 各自满分（前端条形图 / 表格渲染需要）
EU_MQA_RULE_MAX = {
    # Findability
    "keyword_usage": 30,
    "categories": 30,
    "geo_search": 20,
    "time_based_search": 20,
    # Accessibility
    "access_url_accessibility": 50,
    "download_url": 20,
    "download_url_accessibility": 30,
    # Interoperability
    "format": 20,
    "media_type": 10,
    "format_vocabulary": 10,
    "non_proprietary": 20,
    "machine_readable": 20,
    "dcat_ap_compliance": 30,
    # Reusability
    "license_information": 20,
    "license_vocabulary": 10,
    "access_restrictions": 10,
    "access_restrictions_vocabulary": 5,
    "contact_point": 20,
    "publisher": 10,
    # Contextuality
    "rights": 5,
    "file_size": 5,
    "date_of_issue": 5,
    "modification_date": 5,
}


# 5 维满分（前端雷达图 / 报告用）
EU_MQA_DIMENSION_MAX = {
    "discover": 100,
    "access": 100,
    "interop": 110,
    "reuse": 75,
    "context": 20,
}


class MetaEvaluateResult(BaseModel):
    """meta_evaluate agent 输出契约（对齐欧盟 MQA 405 分制 + 23 条规则）。

    agent 按方法论 + 3 个 observation tool 算分 + 评级 + 建议。
    所有字段在 ToolStrategy 模式下都是必填。
    """

    # ---------- MQA 5 维分数 ----------
    score_total: int = Field(
        description="总分（0-405）= 5 维度分数之和",
        ge=0, le=405,
    )
    score_discover: int = Field(
        description="Findability 可发现性（0-100）：keyword_usage 30 + categories 30 + geo_search 20 + time_based_search 20",
        ge=0, le=100,
    )
    score_access: int = Field(
        description="Accessibility 可访问性（0-100）：access_url_accessibility 50 + download_url 20 + download_url_accessibility 30",
        ge=0, le=100,
    )
    score_interop: int = Field(
        description="Interoperability 互操作性（0-110）：format 20 + media_type 10 + format_vocabulary 10 + non_proprietary 20 + machine_readable 20 + dcat_ap_compliance 30",
        ge=0, le=110,
    )
    score_reuse: int = Field(
        description="Reusability 可重用性（0-75）：license_information 20 + license_vocabulary 10 + access_restrictions 10 + access_restrictions_vocabulary 5 + contact_point 20 + publisher 10",
        ge=0, le=75,
    )
    score_context: int = Field(
        description="Contextuality 上下文（0-20）：rights 5 + file_size 5 + date_of_issue 5 + modification_date 5",
        ge=0, le=20,
    )

    # ---------- 评级 ----------
    grade: Literal["Excellent", "Good", "Sufficient", "Bad"] = Field(
        description="质量评级：Excellent 351-405 / Good 221-350 / Sufficient 121-220 / Bad 0-120",
    )

    # ---------- 详细报告 ----------
    rule_scores: dict = Field(
        default_factory=dict,
        description=(
            "EU MQA 23 条 indicator 明细分，键名严格用 snake_case："
            "{"
            "keyword_usage, categories, geo_search, time_based_search, "
            "access_url_accessibility, download_url, download_url_accessibility, "
            "format, media_type, format_vocabulary, non_proprietary, "
            "machine_readable, dcat_ap_compliance, "
            "license_information, license_vocabulary, access_restrictions, "
            "access_restrictions_vocabulary, contact_point, publisher, "
            "rights, file_size, date_of_issue, modification_date"
            "}"
            "（23 条 rule key 必须全部填，缺则 0 分）"
        ),
    )

    llm_notes: dict = Field(
        default_factory=dict,
        description=(
            "LLM 软评估 + 改进建议，结构："
            "{soft_quality_title: 0-5, soft_quality_description: 0-5, "
            "improvement_suggestions: [str, ...]}"
        ),
    )

    summary: str = Field(
        default="",
        description="一句话结论（≤80 字）：元数据是否可投入二次开发",
    )

    evaluation_timestamp: str = Field(
        default="",
        description="评估时间戳（ISO 8601 UTC，DQV 标准需要；可由 service 层注入）",
    )