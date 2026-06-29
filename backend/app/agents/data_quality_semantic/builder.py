"""语义层数据质量评估 builder — 纯推理 LLM + with_structured_output。

使用 llm.with_structured_output() 而非 create_agent + ToolStrategy，
因为纯推理 agent 没有外部 tool，create_agent 无法处理空的 tools 列表
（会导致 "insufficient tool messages following tool_calls message" 错误）。
"""

from langchain_core.prompts import ChatPromptTemplate

from app.agents.data_quality_semantic.prompt import DATA_QUALITY_SEMANTIC_PROMPT
from app.agents.data_quality_semantic.schema import SemanticQualityOutput
from app.core.llm import _build_llm_unthinking


def build():
    """Build the semantic quality evaluation chain。

    使用 llm.with_structured_output() 强制结构化输出（不依赖 tool_choice）。
    纯推理，无外部 tool。
    """
    llm = _build_llm_unthinking()
    prompt = ChatPromptTemplate.from_messages([
        ("system", DATA_QUALITY_SEMANTIC_PROMPT),
        ("user", "{input}"),
    ])
    chain = prompt | llm.with_structured_output(SemanticQualityOutput)
    return chain
