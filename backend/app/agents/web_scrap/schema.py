"""
scrap_schema.py — web_scrap agent v2 输出契约（单 schema）。

成功 / 失败共用一个 Pydantic 类，所有条件字段都是 Optional，
让 LLM 根据 prompt 自己判断填哪个字段。

为什么不用 Union：
- ProviderStrategy 不支持 Union 类型（不调 _iter_variants，会报 Unsupported schema type）
- 单 schema + Optional 字段 + prompt 强约束 = 简单可靠

v2.0 调整：原样搬自 v1.0。
"""
from typing import Literal, Optional

from pydantic import BaseModel, Field


class ScrapResult(BaseModel):
    """v2 输出契约。"""

    url: str = Field(
        description="用户传入的原始 URL",
    )

    scrape_status: Literal["success", "failed"] = Field(
        description=(
            "抓取结果状态。"
            "成功填 'success'；失败填 'failed'。"
            "这个字段决定其它字段的填法（见 prompt）。"
        ),
    )

    metadata: Optional[dict] = Field(
        default=None,
        description=(
            "页面原始元数据字典。"
            "成功时必填（中文键字典）；失败时填 null。"
        ),
    )

    raw_excerpt: Optional[str] = Field(
        default=None,
        description=(
            "页面 innerText 前 800 字原文快照，用于溯源校验。"
            "成功时必填；失败时填 null。"
        ),
    )

    reason: Optional[str] = Field(
        default=None,
        description=(
            "失败原因简述。"
            "仅 scrape_status='failed' 时填。"
            "成功时填 null。"
        ),
    )
