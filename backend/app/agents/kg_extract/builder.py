"""知识图谱实体抽取 Agent 构建器。

使用 ChatPromptTemplate + llm.with_structured_output() 实现
结构化实体抽取，不依赖 LangChain Agent 框架。
"""
from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate

from app.agents.kg_extract.prompt import KG_EXTRACT_PROMPT
from app.agents.kg_extract.schema import KgExtractResult
from app.core.llm import _build_llm_unthinking


def build():
    """构建 KG 实体抽取 chain。

    Returns:
        callable: 接受 metadata dict，返回 KgExtractResult 的 chain
        None: LLM 配置缺失时返回 None
    """
    llm = _build_llm_unthinking()
    if llm is None:
        return None

    # 注意：SystemMessage 不走 template parser，避免 prompt 中的 {…} 被误解析
    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=KG_EXTRACT_PROMPT),
        HumanMessagePromptTemplate.from_template(
            "以下数据集元数据，请抽取实体和关系：\n\n{input}",
        ),
    ])

    chain = prompt | llm.with_structured_output(KgExtractResult)
    return chain
