"""数据质量评估 builder — 包装 quality_tool.assess_quality()。

不依赖 LLM / langchain agent。纯 CPU 工具函数。
"""
from app.agents.tools.quality_tool import assess_quality


def build_quality_report(file_path: str, dataset_id: str) -> dict:
    """调 quality_tool 生成质量报告。

    Returns:
        {"summary": dict, "issues": list, "report_markdown": str}
    """
    return assess_quality(file_path, dataset_id)
