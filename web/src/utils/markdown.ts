import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js/lib/common'
import DOMPurify from 'dompurify'

export const md: MarkdownIt = new MarkdownIt({
    html: false,        // ← XSS 第一道防线:禁止原始 HTML 注入(默认 false,显式写更清晰)
    linkify: true,      // 自动识别裸 URL 为 <a>
    breaks: false,      // 不把单换行转 <br>(CommonMark 标准,只认两个换行+成段)
    typographer: false, // 不做智能引号(中文场景反而干扰)
    highlight(str, lang) {
        // highlight() 输出 pre.markdown-pre data-language
        // 这样 onUpdated 钩能 querySelectorAll('pre.markdown-pre') 挂 Copy 按钮,
        // data-language 给顶栏显示「python」「js」等语言标签
        const safeLang = (lang || 'text').toLowerCase()
        const langAttr = ` data-language="${md.utils.escapeHtml(safeLang)}"`
        const codeClass = `hljs language-${md.utils.escapeHtml(safeLang)}`

        // 优先用指定语言高亮,fallback 到自动检测,fallback 失败就 escape 原文
        if (lang && hljs.getLanguage(lang)) {
            try {
                return `<pre class="hljs markdown-pre"${langAttr}><code class="${codeClass}">${hljs.highlight(str, { language: lang, ignoreIllegals: true }).value}</code></pre>`
            } catch {
                // fall through
            }
        }
        try {
            return `<pre class="hljs markdown-pre"${langAttr}><code class="${codeClass}">${hljs.highlightAuto(str).value}</code></pre>`
        } catch {
            return `<pre class="hljs markdown-pre"${langAttr}><code class="${codeClass}">${md.utils.escapeHtml(str)}</code></pre>`
        }
    },
})

// 安全加固:所有 <a> 强制 target=_blank + rel=noopener(防 reverse tabnabbing)
// 记住:默认 target=_self,LLM 输出链接会把当前页覆盖掉,体验差且不安全
const defaultLinkOpen = md.renderer.rules.link_open || function (tokens, idx, options, _env, self) {
    return self.renderToken(tokens, idx, options)
}
md.renderer.rules.link_open = function (tokens, idx, options, env, self) {
    const aIndex = tokens[idx].attrIndex('target')
    if (aIndex < 0) {
        tokens[idx].attrPush(['target', '_blank'])
        tokens[idx].attrPush(['rel', 'noopener noreferrer'])
    } else {
        tokens[idx].attrs![aIndex][1] = '_blank'
    }
    return defaultLinkOpen(tokens, idx, options, env, self)
}

// 表格横滚:在 <table> 外包 <div class="markdown-table-wrap">,CSS 给 overflow-x:auto
// 这样宽表不撑破布局,容器出横向滚动条
// DOMPurify 不会重组 <div><table> 标准嵌套,可以安全 sanitize
md.renderer.rules.table_open = function () {
    return '<div class="markdown-table-wrap">\n<table>'
}
md.renderer.rules.table_close = function () {
    return '</table>\n</div>'
}

/**
 * DOMPurify sanitize 配置 —— XSS 第二道防线
 *
 * 第一道防线:md 实例 html:false(禁原始 HTML)
 * 第二道防线:即使第一道被绕过,DOMPurify 也会洗掉危险标签/属性
 * - USE_PROFILES: { html: true }:标准 HTML profile,默认放行 class / data-* / a[href]
 *   这样 hljs 的 class (hljs-keyword / hljs-string / ...) 不会被洗掉
 * - ADD_ATTR: ['target', 'rel']:link_open rule 注入的 target/rel 在 markdown 渲染后保留
 *   (DOMPurify 默认会过滤非白名单 attr,这里显式允许)
 * - FORBID_TAGS:button/input/form/iframe/script/style/object/embed —— 防交互注入
 *   (我们的 Copy 按钮是 JS 后挂的,不走 sanitize,这里禁 button 标签不影响功能)
 * - FORBID_ATTR:onerror/onload/onclick 等事件属性 + style —— 防伪协议 + 行内样式注入
 * - RETURN_TRUSTED_TYPE: false:关闭 TrustedHTML 输出,直接返回 string(避免 TS 类型不匹配)
 *
 * 类型技巧:@types/dompurify 用 `export = DOMPurify` + `export as namespace DOMPurify`,
 * TS 6.0 解析不到 DOMPurify.Config namespace 成员。用 Parameters 推断 config 参数类型
 * 既保住类型推断,又避开 namespace 限制。
 */
const PURIFY_CONFIG = {
    USE_PROFILES: { html: true },
    ADD_ATTR: ['target', 'rel'],
    FORBID_TAGS: ['style', 'script', 'iframe', 'form', 'input', 'button', 'object', 'embed'],
    FORBID_ATTR: ['onerror', 'onload', 'onclick', 'onmouseover', 'onfocus', 'onblur', 'style'],
    RETURN_TRUSTED_TYPE: false,
} as Parameters<typeof DOMPurify.sanitize>[1]

/**
 * 把 markdown-it 输出的 HTML 字符串过一遍 DOMPurify,移除 XSS 风险
 * @param dirty markdown-it 渲染产物(可能含 hljs span、属性注入尝试等)
 * @returns sanitize 后的安全 HTML
 */
export function sanitizeHtml(dirty: string): string {
    return DOMPurify.sanitize(dirty, PURIFY_CONFIG) as string
}

/**
 * 流式渲染预处理:工厂函数,每个 MarkdownView 实例持有一个
 *
 * 原理:markdown-it 严格遵守 CommonMark,fence 必须配对才结束。
 * 流式中 LLM 写完 ```json 但还没写 ``` 时,后续所有文字会被当成代码块内容
 * (实测现象:```json 后面接 ## 二级标题、表格、列表,全部被吞进 <pre>)
 *
 * 这里手动扫描行首 fence 状态,发现未闭合就在末尾补一个匹配长度的 fence。
 * CommonMark fence 规则:开头最多 3 个空格缩进,然后 3+ 个 ` 或 ~,闭合 fence 长度需 >= 开启。
 *
 * 性能:相比每次全量 split('\n'),增量扫描从上一个换行后开始(state.lastLen 记录),
 * 5KB 长内容每帧节省 ~70% 解析开销。
 *
 * 边界 case:代码块内部如果出现行首的 ```(比如代码示例),会被误判关闭。
 * 但实际场景代码块内的 ``` 一般有 4 空格缩进,正则 ^{0,3} 不匹配 → 留在 fence 内,正确。
 *
 * @returns factory 闭包,持 state
 */
export function createStreamingPreprocessor() {
    let lastLen = 0
    let lastSuffix: 'closed' | 'open' = 'closed'
    let fenceChar = ''
    let fenceLength = 0

    return {
        /**
         * 处理一帧 content
         * @param raw 当前 content(props.content)
         * @returns {processed} 预处理后的 content(可能末尾补了闭合符)
         */
        process(raw: string): { processed: string } {
            // reset 条件:长度回退(SSE 不应发生,但切会话/重发可能)
            if (raw.length < lastLen) {
                lastLen = 0
                lastSuffix = 'closed'
                fenceChar = ''
                fenceLength = 0
            }

            // 长度未变:心跳空帧,直接返回缓存结果
            if (raw.length === lastLen) {
                return {
                    processed: lastSuffix === 'open'
                        ? raw + '\n' + fenceChar.repeat(fenceLength)
                        : raw,
                }
            }

            // 增量扫描:从 lastLen 位置之前最后一个换行 + 1 开始,避免跨 chunk 漏扫描
            // (例:上次到 "...```py" 末尾,这次新 chunk 是 "\nprint(1)\n",从 py 所在行重新扫)
            const lastNewlineBefore = raw.lastIndexOf('\n', lastLen)
            const scanStart = lastNewlineBefore + 1
            const lines = raw.slice(scanStart).split('\n')

            let inFence = lastSuffix === 'open'
            let c = fenceChar
            let l = fenceLength

            for (const line of lines) {
                // CommonMark fence 规则:开头最多 3 个空格缩进,然后 3+ 个 ` 或 ~
                const m = line.match(/^( {0,3})(`{3,}|~{3,})(.*)$/)
                if (!m) continue

                const marker = m[2]
                const char = marker[0]
                const len = marker.length

                if (!inFence) {
                    // 开启 fence
                    inFence = true
                    c = char
                    l = len
                } else if (char === c && len >= l) {
                    // 关闭 fence(同类型 + 长度 >= 开启长度)
                    inFence = false
                }
                // 其他情况(代码块内行首出现的 fence 字符串):忽略,继续留在 fence 内
            }

            lastLen = raw.length
            lastSuffix = inFence ? 'open' : 'closed'
            fenceChar = c
            fenceLength = l

            return {
                processed: inFence ? raw + '\n' + c.repeat(l) : raw,
            }
        },
    }
}
