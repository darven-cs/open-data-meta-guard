import asyncio
import base64
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional, Dict, Any
from urllib.parse import urlparse

from playwright.async_api import (
    Download,
    Page,
    Browser,
    BrowserContext,
    async_playwright,
    Locator,
)

from app.core.log import logger


class PlaywrightBrowser:
    def __init__(self, max_contexts: int = 3):
        """多 context 浏览器池（2026-06-26 batch 化重构）。

        Args:
            max_contexts: 同时存在的 context 数（默认 3，对应默认批次并发度）；
                          每个 context 独立 page + 下载队列，互不干扰。

        兼容性：
            - 保留 self.page 属性指向 contexts[0].page，让现有 web_scrap / download
              agent 直接用 browser.page 不破坏；
            - 新代码（batch 路由）用 `async with browser.acquire_page() as page` 借/还。
        """
        self.max_contexts: int = max_contexts
        self.pw: Optional[async_playwright] = None
        self.browser: Optional[Browser] = None
        # v3（2026-06-26）：单 ctx 变 N ctx 池
        self.contexts: list[BrowserContext] = []
        self.pages: list[Page] = []
        # 兼容旧引用：指向 contexts[0] 的 page，让 browser.page / ctx 还能用
        self.ctx: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.headless = False  # 有头模式
        self.launch_args = [
            "--no-sandbox",
            "--disable-blink-features=AutomationControlled",
        ]
        # ─── 下载捕获机制（v2 — 2026-06-24 修竞态）───
        # 旧版用 page.once + Future 有竞态：click 触发 download 时 future 可能不存在 → 事件被丢弃。
        # 新版用 page.on（持久监听器）+ asyncio.Queue 缓冲：
        # - click 触发 download → put_nowait 入队（即便没人在 wait）
        # - wait_for_next_download 优先检查队列、再 get 阻塞
        # - 任意顺序 click/wait 都能正确工作
        # 详见 memory/bugs/playwright_download_race_condition.md
        self._download_queue: asyncio.Queue = asyncio.Queue()
        self._download_listeners_installed: bool = False
        # 并发控制：N 个 context 上限 → 同一时刻最多 N 个 task 拿到 page
        self._sem: Optional[asyncio.Semaphore] = None

    async def start(self):
        """启动浏览器 + 创建 max_contexts 个 context（v3 — 2026-06-26）。

        关键参数（参考 v1_flet_ui/scraper/browser.py 实测）：
        - channel="chrome"：系统真实 Chrome，过阿里云 WAF
        - --no-sandbox：WAF 站点对完整 Chrome 指纹要求，sandbox 关掉避免环境差异
        - locale=zh-CN + viewport 1920x1080：避免 viewport=None 被指纹识别
        """
        if self.browser and self.browser.is_connected():
            return
        # 引用还活着但 is_connected=False（disconnected 事件漏挂的极端情况），
        # 先清理脏引用，避免下面 self.pw=... 覆盖后旧的 ctx/page 悬空泄漏
        if self.browser or self.contexts or self.pages or self.pw:
            await self.close()

        self.pw = await async_playwright().start()
        self.browser = await self.pw.chromium.launch(
            channel="chrome",
            headless=self.headless,
            args=self.launch_args,
        )

        # 创建 N 个独立 context + page（互不共享 cookie/storage）
        self.contexts = []
        self.pages = []
        for _ in range(self.max_contexts):
            ctx = await self.browser.new_context(
                locale="zh-CN",
                viewport={"width": 1920, "height": 1080},
            )
            page = await ctx.new_page()
            self.contexts.append(ctx)
            self.pages.append(page)

        # 兼容老引用：单 page → contexts[0].page；老 agent 用 browser.page 不破坏
        self.ctx = self.contexts[0]
        self.page = self.pages[0]

        # 并发控制信号量
        self._sem = asyncio.Semaphore(self.max_contexts)

        self.browser.on("disconnected", self._invalidate)
        self._install_download_listener()
        print(f">> 有头浏览器启动完成（{self.max_contexts} contexts）")

    @asynccontextmanager
    async def acquire_page(self) -> AsyncIterator[Page]:
        """借一个空闲 page，用完自动归还。

        用法：
            async with browser.acquire_page() as page:
                await page.goto(url)
                ...

        实现：asyncio.Semaphore 控制并发上限；内部用一个简单 round-robin
        索引分发（contexts 数量少，1..3 个轮转足够）。

        必须 start() 后才能用，否则 raise。
        """
        if self._sem is None or not self.pages:
            raise RuntimeError("browser not started; call start() first")

        await self._sem.acquire()
        # round-robin：取 _sem 释放前的 value（已 acquire 后少 1）作为索引
        # 实际更可靠的：用当前 in_use 计数；这里简化用 value 模 len
        idx = (self.max_contexts - self._sem._value - 1) % len(self.pages)
        try:
            yield self.pages[idx]
        finally:
            self._sem.release()

    def _invalidate(self, _browser=None):
        """disconnected 事件回调（必须是 sync 函数，Playwright 同步派发）。

        Chromium 进程死掉时由 Playwright 触发，把所有引用清空，
        让下次 start() 重新拉起浏览器。不在 handler 里重启——
        重启是 async 操作，交给业务侧 start() 处理。

        同时清理下载队列，避免 wait_for_next_download 永久挂起
        导致后续请求全部卡死。
        """
        # 清空 queue（无 close 方法，置 None 强引用断开）
        while not self._download_queue.empty():
            try:
                self._download_queue.get_nowait()
            except Exception:
                break
        self._download_listeners_installed = False
        # v3：清空多 context 引用
        self.pages = []
        self.contexts = []
        self.page = None
        self.ctx = None
        self.browser = None
        self.pw = None
        self._sem = None
        logger.warning("浏览器被外部关闭（用户关窗口/Chromium 崩溃），下次调用会自动重启")

    async def close(self):
        # 二次关闭时 Playwright 会抛 TargetClosedError，套通用 Exception 捕掉
        # 因为 close() 可能在「浏览器已被外部关闭」之后再次调用（比如 main.py finally）
        # v3：关闭所有 context + 全部 page
        for page in list(self.pages):
            try:
                await page.close()
            except Exception:
                pass
        self.pages = []
        for ctx in list(self.contexts):
            try:
                await ctx.close()
            except Exception:
                pass
        self.contexts = []
        self.page = None
        self.ctx = None
        if self.browser:
            try:
                await self.browser.close()
            except Exception:
                pass
            self.browser = None
        if self.pw:
            try:
                await self.pw.stop()
            except Exception:
                pass
            self.pw = None
        self._sem = None
        print(">> 浏览器关闭")

    # ──────────────────────── 下载事件捕获（v2 队列 + 持久监听）────────────────────────
    def _install_download_listener(self):
        """挂一个 page.on("download", ...) 持久监听器，把事件塞进 asyncio.Queue。

        为什么要用 queue + 持久监听器？
        旧版用 page.once + Future 有竞态：click 触发的 download 事件可能在 wait 之前到达，
        此时 Future 不存在 → 事件被丢弃 → wait 永远超时。LLM agent 的"click 后 wait"是
        自然语序，但 download 事件在 click 同步阶段就触发了，wait 调用要等下一次 agent 循环。

        新版：download 事件永远入队，wait_for_next_download 优先查队列再 get 阻塞。
        - click 先于 wait：事件入队 → wait 立刻返回
        - wait 先于 click：wait 阻塞 → click 触发 → 入队 → wait 拿到
        - 多次 click：每次都入队，按序消费

        触发时机：start() 末尾挂一次（持久）；disconnected 时清空。
        """
        if not self.page or self._download_listeners_installed:
            return

        def _on_download(download: Download):
            # listener 同步派发，put_nowait 是非阻塞的
            try:
                self._download_queue.put_nowait(download)
                logger.info(
                    "[browser] download 事件入队 suggested_filename={!r} url={}",
                    download.suggested_filename, download.url[:100],
                )
            except Exception as e:
                logger.warning("[browser] download 事件入队失败: {}", e)

        # page.on（持久监听，多次 download 多次触发），不再用 page.once
        self.page.on("download", _on_download)
        self._download_listeners_installed = True
        logger.debug("[browser] download listener 已挂载（持久 + queue）")

    async def wait_for_next_download(self, timeout: float = 30.0) -> Optional[Download]:
        """等待并返回下一个 download 事件。

        与 page.expect_download() 的区别：
        后者是 context manager，强制包住 click —— 想 click 与下载捕获分离就不行。
        本方法用 page.on（持久）+ asyncio.Queue 拆分两者，让 LLM 可以先 click 后等，
        也可以先等后 click。竞态由 queue 缓冲解决。

        Args:
            timeout: 最长等待秒数（仅当队列为空时生效）

        Returns:
            Download 对象 或 None（队列空 + 超时）
        """
        await self.start()

        # 优先检查队列：之前 click 已经触发的 download 可能还在等
        try:
            download = self._download_queue.get_nowait()
            logger.info(
                "[browser] 命中队列里的 download suggested_filename={!r}",
                download.suggested_filename,
            )
            return download
        except asyncio.QueueEmpty:
            pass

        # 队列空：阻塞等下一次 download
        try:
            download = await asyncio.wait_for(
                self._download_queue.get(), timeout=timeout,
            )
            logger.info(
                "[browser] 等待到 download suggested_filename={!r}",
                download.suggested_filename,
            )
            return download
        except asyncio.TimeoutError:
            logger.warning("[browser] wait_for_next_download 超时（{}s）", timeout)
            return None

    async def goto(self, url: str) -> str:
        """访问网址，返回页面摘要信息。

        WAF + SPA 双层等待策略：
        1. domcontentloaded 让原始 HTML 解析完
        2. wait_for_function 等 innerText 出现可读内容（最多 15s）
           —— 覆盖 WAF challenge JS 跑完（首次访问约需 5-15s）+ SPA 数据渲染
        3. 兜底 +3s 让 SPA 稳定

        详见 memory/bugs/playwright_spa_inner_text.md
        + memory/bugs/waf_challenge_wait.md
        """
        await self.start()
        await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)

        # 智能等待：innerText 出现 > 50 字符说明 WAF + SPA 都跑完了
        try:
            await self.page.wait_for_function(
                "() => document.body && (document.body.innerText || '').trim().length > 50",
                timeout=15000,
            )
        except Exception:
            # 超时还没内容：可能真空白页 / SPA 慢 / WAF 拦死了
            # 多给 3s 兜底，最终结果由 get_page_summary 报告
            logger.warning("WAF/SPA 等待超时（15s innerText 仍 < 50 字符），再多等 3s 兜底 url={}", url)
            await self.page.wait_for_timeout(3000)

        # 再多 1s 让 SPA 路由切换 / title 更新稳定（避免拿到中间态）
        await self.page.wait_for_timeout(1000)

        return await self.get_page_summary()

    async def click_element(self, locator_str: str) -> str:
        """
        locator_str 示例：
        get_by_role("button", name="登录")
        locator("#su")
        """
        await self.start()
        try:
            loc: Locator = eval(f"self.page.{locator_str}")
            await loc.wait_for(timeout=6000)
            await loc.click()
            await self.page.wait_for_timeout(1000)
            return f"点击成功，{await self.get_page_summary()}"
        except Exception as e:
            return f"点击失败: {str(e)}"

    async def fill_input(self, locator_str: str, text: str) -> str:
        await self.start()
        try:
            loc: Locator = eval(f"self.page.{locator_str}")
            await loc.wait_for(timeout=6000)
            await loc.fill(text)
            return f"输入成功，{await self.get_page_summary()}"
        except Exception as e:
            return f"输入失败: {str(e)}"

    async def get_page_summary(self) -> str:
        try:
            await self.page.wait_for_load_state("domcontentloaded", timeout=5000)
        except Exception:
            pass  # SPA 重定向中偶尔失败，跳过别 raise

        title = await self.page.title()
        current_url = self.page.url

        # 重试
        for attempt in range(5):
            try:
                body_text = await self.page.evaluate("() => document.body.innerText")  # 读渲染后文本
                break
            except Exception as e:
                if "navigating" in str(e) and attempt < 4:
                    await asyncio.sleep(0.3)
                    continue
                raise

        snippet = body_text[:3000]
        logger.info(
            "页面摘要 title='{}' innerText_len={} url={}",
            title, len(body_text), current_url,
        )
        return f"""
        当前页面标题：{title}
        当前URL：{current_url}
        页面正文片段：{snippet}
        """

    async def scan_download_candidates(self) -> dict:
        """扫描当前页面，提取可下载文件候选的结构化清单。

        返回 dict（会被外层 @tool 序列化成 JSON）：
            csv_count / xlsx_count / json_count / xml_count: 各扩展名候选数
            has_download_all: bool, 是否有「下载所有」批量按钮
            sample_filenames: list[str], 前 5 个文件名样本
            suggested_action: "use_zip_fallback" (count>5 或只有批量按钮)
                              | "click_individual" (count<=5)
                              | "no_candidates" (一个都没有)
            best_locator: str, 推荐下一步 click 用的 locator 表达式

        设计动机（v6 — 2026-06-24）：
            v5 prompt 让 LLM 用 `get_by_role(...).count()` 判定文件数，
            但 LLM 没有「返回 count」的工具，page summary 又被截到 3000 字符，
            导致 agent 反复 goto 刷页面陷入死循环（典型：data.sh.gov.cn 703 月度文件）。
            本工具一次性返回结构化清单 + 决策建议 + 推荐 locator，
            LLM 拿到后可直接走对应路径，不用再读冗长 innerText。

        实现细节：
            - 优先用 class selector `.filebase.{ext}`（data.sh.gov.cn 等站点专用）
            - class 不命中时退化到 text 匹配（`a/button[onclick]` 内文字含 ext）
            - 中文文件名按 `el.innerText.trim()` 提取，前 5 个去重
            - 「下载所有」按钮用精确文本匹配 "下载所有" / "全部下载"
        """
        await self.start()
        try:
            await self.page.wait_for_load_state("domcontentloaded", timeout=5000)
        except Exception:
            pass

        # 让前端的 Vue/React 有时间渲染出文件列表
        await self.page.wait_for_timeout(500)

        scan_js = r"""
        () => {
            const exts = ['csv', 'xlsx', 'json', 'xml'];
            const counts = {csv: 0, xlsx: 0, json: 0, xml: 0};
            const samples = [];

            // 方法1: class selector .filebase.{ext}（data.sh.gov.cn 等结构）
            for (const ext of exts) {
                const sel = `.filebase.${ext}`;
                const elements = document.querySelectorAll(sel);
                counts[ext] = elements.length;
                for (let i = 0; i < Math.min(5, elements.length); i++) {
                    const el = elements[i];
                    const txt = (el.innerText || el.textContent || '').trim();
                    if (txt && !samples.includes(txt)) {
                        samples.push(txt);
                    }
                }
            }

            // 方法2: 通用 a/button 文本匹配（class 不命中时退化）
            const totalByClass = Object.values(counts).reduce((a, b) => a + b, 0);
            if (totalByClass === 0) {
                const candidates = document.querySelectorAll(
                    'a, button, [onclick], [role="button"]'
                );
                for (const ext of exts) {
                    const matched = Array.from(candidates).filter(el => {
                        const t = (el.innerText || el.textContent || '').toLowerCase().trim();
                        // 短文本 + 含 ext 关键字（排除段落/标题等长文本）
                        return t.length > 0 && t.length < 100 && t.includes(ext);
                    });
                    counts[ext] = matched.length;
                    for (let i = 0; i < Math.min(5, matched.length); i++) {
                        const txt = (matched[i].innerText || matched[i].textContent || '').trim();
                        if (txt && !samples.includes(txt)) {
                            samples.push(txt);
                        }
                    }
                }
            }

            // 检查「下载所有」批量按钮
            const allButtons = document.querySelectorAll('a, button, [role="button"]');
            const hasDownloadAll = Array.from(allButtons).some(el => {
                const t = (el.innerText || el.textContent || '').trim();
                return t === '下载所有' || t === '全部下载' || t.includes('下载所有');
            });

            return {
                counts: counts,
                samples: samples.slice(0, 5),
                has_download_all: hasDownloadAll,
            };
        }
        """
        result = await self.page.evaluate(scan_js)
        counts = result.get("counts", {})
        samples = result.get("samples", [])
        has_download_all = bool(result.get("has_download_all", False))

        # 选优先级最高的 type (csv > xlsx > json > xml)
        priority = {"csv": 0, "xlsx": 1, "json": 2, "xml": 3}
        chosen_type = ""
        chosen_count = 0
        for ext in ["csv", "xlsx", "json", "xml"]:
            c = counts.get(ext, 0)
            if c > 0 and (chosen_type == "" or priority[ext] < priority[chosen_type]):
                chosen_type = ext
                chosen_count = c

        # 决策
        if chosen_count == 0 and not has_download_all:
            suggested = "no_candidates"
            best_locator = ""
        elif chosen_count > 5 or (chosen_count <= 5 and chosen_count == 0 and has_download_all):
            suggested = "use_zip_fallback"
            best_locator = (
                'get_by_role("button", name="下载所有").first'
                if has_download_all
                else f'get_by_role("link", name="{chosen_type}").first'
            )
        else:
            suggested = "click_individual"
            best_locator = f'get_by_role("link", name="{chosen_type}").first'

        out = {
            "csv_count": counts.get("csv", 0),
            "xlsx_count": counts.get("xlsx", 0),
            "json_count": counts.get("json", 0),
            "xml_count": counts.get("xml", 0),
            "has_download_all": has_download_all,
            "sample_filenames": samples,
            "chosen_type": chosen_type,
            "chosen_count": chosen_count,
            "suggested_action": suggested,
            "best_locator": best_locator,
        }
        logger.info(
            "[browser] scan_download_candidates: counts={} has_dl_all={} chosen={}({}) action={}",
            counts, has_download_all, chosen_type, chosen_count, suggested,
        )
        return out
