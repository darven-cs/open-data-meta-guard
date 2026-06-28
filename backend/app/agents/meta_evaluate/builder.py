"""创建元数据质量评估 agent（EU MQA 405 分制 + 3 个 observation tool）。"""
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy

from app.agents.meta_evaluate.prompt import META_EVALUATE_PROMPT
from app.agents.meta_evaluate.schema import MetaEvaluateResult
from app.agents.tools.meta_evaluate_tool import meta_evaluate_tools
from app.core.llm import _build_llm_unthinking


def build():
    """Build the meta_evaluate agent（EU MQA 405 分制 + 3 个 observation tool）。

    职责：
    - 输入：metadata（由 service 层传入，含 dataset_id）
    - 输出：完整 MetaEvaluateResult（5 维分 + grade + rule_scores + llm_notes + summary）

    工具职责边界（3 个 observation tool，**不是** LLM 印象给分）：
    - `http_head_check(url)` → 用于 A1 (50 分) + A3 (30 分)：必须调，不调就给 0
      返回 status_code + accessible；agent 根据 status_code < 400 判定给分
    - `dcat_ap_compliance_check(metadata_json)` → 用于 I6 (30 分)：必须调
      返回 missing 字段列表；agent 按 missing 数量扣分
    - `vocabulary_match(value, vocab_type)` → 用于 I3 (10) / I4 (20) / I5 (20) / R2 (10) / R4 (5)
      5 种 vocab_type，命中返回对应 EU 分数

    Schema：
    - response_format=ToolStrategy(MetaEvaluateResult)：
      强制 LLM 用 MetaEvaluateResult 工具返回结构化结果。
      必须用 _build_llm_unthinking()：ToolStrategy 会发 tool_choice="any"，
      deepseek thinking 模式不支持。
    """
    llm = _build_llm_unthinking()
    return create_agent(
        model=llm,
        tools=meta_evaluate_tools,
        system_prompt=META_EVALUATE_PROMPT,
        response_format=ToolStrategy(schema=MetaEvaluateResult),
    )