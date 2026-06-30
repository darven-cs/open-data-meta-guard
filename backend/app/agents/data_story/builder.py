"""数据故事 Agent 构建器。

不用 create_agent + ToolStrategy（会强制 tool_choice="any" 导致无法流式输出 token），
改为手动 llm.bind_tools + 路由层手动 tool-calling 循环。
"""
from langchain_core.messages import SystemMessage
from app.agents.data_story.prompt import DATA_STORY_PROMPT
from app.agents.tools.kg_query_tool import kg_query
from app.agents.tools.data_analysis_tool import analyze_and_chart
from app.core.llm import _build_llm
from app.core.log import logger


def build():
    """返回 (llm_with_tools, tools)。

    由路由层负责流式编排（astream + 手动工具循环）。
    """
    llm = _build_llm()  # 保留 thinking 模式（用于叙述性输出）
    if llm is None:
        logger.error("[data_story] LLM build failed — check LLM_* env vars")
        return None, []

    tools = [kg_query, analyze_and_chart]
    llm_with_tools = llm.bind_tools(tools)
    return llm_with_tools, tools
