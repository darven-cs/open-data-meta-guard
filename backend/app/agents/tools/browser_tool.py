"""
browser_tool.py — 5 个 Playwright 浏览器工具，给 web_scrap agent 用。

v2.0 调整：
- 路径从 `app/tools/browser_tool.py` 移到 `app/agents/tools/browser_tool.py`
- 删掉 web_scrap 用不到的 download 类工具（v2.0 砍掉数据下载阶段）：
  - browser_scan_downloads
  - browser_wait_for_download
  - browser_fill（保留，web_scrap 搜索场景可能用到）
- 保留 5 个：browser_start / browser_goto / browser_click / browser_fill / browser_close
"""
from urllib.parse import unquote

from langchain.tools import tool

from app.core.browser import PlaywrightBrowser
from app.core.log import logger

browser = PlaywrightBrowser()


@tool
async def browser_start() -> str:
    """
    显式启动浏览器进程。

    首次调用其他 browser_* 工具时会自动启动浏览器，所以一般不需要显式调。
    只有在「想提前预热，避免首次 goto 卡顿 1-2 秒」时才调它。

    Returns:
        "浏览器启动成功"
    """
    logger.info("[tool]>> browser_start")
    await browser.start()
    return "浏览器启动成功"


@tool
async def browser_goto(url: str) -> str:
    """
    打开指定网址，返回页面摘要。

    第一次调用会自动启动浏览器（无需先调 browser_start）。
    返回的内容用于后续判断页面结构、决定下一步点哪个元素。

    Args:
        url: 完整 http(s) 网址，例如 "https://example.com/path"

    Returns:
        页面摘要字符串，包含三段：
        - 当前页面标题
        - 当前 URL
        - 页面 HTML 片段（前 3000 字，从中可以提取关键字段或定位元素）
    """
    logger.info("[tool]>> browser_goto url={}", url)

    decoded = unquote(url)
    if "[object " in decoded or "<" in decoded or ">" in decoded:
        return (
            "URL 包含非法参数（疑似 DOM 对象被 toString 后拼进了 query），"
            "请去除非法参数后重试。原始 URL：" + url
        )

    return await browser.goto(url)


@tool
async def browser_click(locator_expression: str) -> str:
    """
    点击页面元素，返回点击后的页面摘要。

    Args:
        locator_expression: Playwright 语义定位器表达式。
            **不要写 `page.` 前缀**（函数内部会自动拼接）。
            支持的写法：
            - 角色定位（首选）：get_by_role("button", name="搜索")
            - 占位符定位：    get_by_placeholder("请输入关键词")
            - 文本定位：      get_by_text("登录")
            - CSS 定位：      locator("#submit-btn") / locator(".search-btn")

    Returns:
        点击成功时："点击成功，" + 新的页面摘要（title / url / html 片段）
        点击失败时："点击失败: <错误原因>"
    """
    logger.info("[tool]>> browser_click locator={}", locator_expression)
    return await browser.click_element(locator_expression)


@tool
async def browser_fill(locator_expression: str, content: str) -> str:
    """
    在输入框 / 文本域填入文本，返回填入后的页面摘要。

    Args:
        locator_expression: Playwright 语义定位器表达式。
            **不要写 `page.` 前缀**（同 browser_click 的写法）。
            常见用法：
            - get_by_placeholder("请输入关键词")
            - get_by_role("textbox", name="用户名")
            - locator("#search-input")
        content: 要输入的文字内容（短文本或长文本均可）。

    Returns:
        输入成功时："输入成功，" + 页面摘要
        输入失败时："输入失败: <错误原因>"
    """
    safe_content = content[:50] + "..." if len(content) > 50 else content
    logger.info("[tool]>> browser_fill locator={}, content={}", locator_expression, safe_content)
    return await browser.fill_input(locator_expression, content)


@tool
async def browser_close() -> str:
    """
    关闭浏览器进程，释放 Chromium 资源。

    调用场景：
    - 用户明确说「退出 / 结束 / 完成」
    - 任务彻底完成，后续不再访问网页

    不需要每次 goto 之间调用——浏览器对象会保留，多次 goto 共享同一个 session。

    Returns:
        "浏览器关闭"
    """
    logger.info("[tool]>> browser_close")
    await browser.close()
    return "浏览器关闭"


# ──────────────────────── 工具列表 ────────────────────────
# web_scrap agent 只用 5 个（删掉 v1.0 的 2 个 download 工具）
browser_tools = [
    browser_start,
    browser_goto,
    browser_click,
    browser_fill,
    browser_close,
]
