"""创建网页元数据抓取 agent（v2：用 ToolStrategy 强制结构化输出）。

v2.0 调整：原样搬自 v1.0（tools 已从 app.tools 移到 app.agents.tools）。
"""
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy

from app.agents.web_scrap.prompt import WEB_SCRAP_PROMPT
from app.agents.web_scrap.schema import ScrapResult
from app.agents.tools.browser_tool import browser_tools
from app.core.llm import _build_llm_unthinking


def build():
    """Build web_scrap agent（每次调用都新建一个，避免 state 污染）。"""
    llm = _build_llm_unthinking()
    return create_agent(
        model=llm,
        tools=list(browser_tools),
        system_prompt=WEB_SCRAP_PROMPT,
        response_format=ToolStrategy(schema=ScrapResult),  # 适配 deepseek 的工具调用
    )
