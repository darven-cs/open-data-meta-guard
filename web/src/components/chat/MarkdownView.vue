<template>
    <div ref="root" class="markdown-wrap">
        <div class="markdown" v-html="renderedHtml"></div>
        <span
            v-if="props.status === 'streaming'"
            class="markdown__cursor"
            aria-hidden="true"
        ></span>
    </div>
</template>

<script setup lang="ts">
import { ref, watch, onUnmounted, onMounted, onUpdated, nextTick, useTemplateRef } from 'vue'
import { md, createStreamingPreprocessor, sanitizeHtml } from '@/utils/markdown'
import type { MessageStatus } from '@/types/chat'

const props = defineProps<{
    content: string
    status?: MessageStatus
}>()

const renderedHtml = ref('')
const root = useTemplateRef<HTMLElement>('root')
let rafId: number | null = null
// 每实例独立的增量 preprocessor(状态 lastLen/lastSuffix/fenceChar/fenceLength 闭包内)
// 多 MarkdownView 实例并存时(切会话/同屏多条)不串台
const preprocessor = createStreamingPreprocessor()
// 守包含补 fence 后的内容:流式末尾补的 ``` 不变时跳过重渲染(rAF 帧内多次 watch 触发)
let lastSanitizedInput = ''

function scheduleRender() {
    if (rafId !== null) return  // 已排队 → 跳过,让已排队的 rAF 处理最新 content
    rafId = requestAnimationFrame(() => {
        rafId = null
        const raw = props.content ?? ''
        const { processed } = preprocessor.process(raw)
        // 增量:processed 不变就跳过(避免流式稳定期每帧都 parse)
        if (processed === lastSanitizedInput) return
        lastSanitizedInput = processed
        // XSS 第二道防线:DOMPurify 洗一遍 markdown-it 输出
        renderedHtml.value = sanitizeHtml(md.render(processed))
    })
}

// immediate: 首次挂载也要渲染(切会话加载历史消息时,content 不会变)
watch(() => props.content, scheduleRender, { immediate: true })

// 简单 HTML escape,用于拼 Copy 按钮 innerHTML 时防 language 标签 XSS
function escapeHtml(s: string) {
    return s.replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]!))
}

/**
 * 给所有 <pre.markdown-pre> 补顶栏 bar(语言标签 + Copy 按钮)
 *
 * 为什么用 onUpdated + 直接 DOM 操作,不用 v-for 模板:
 * 1. v-html 注入的子元素无 Vue 响应性,挂不上 @click
 * 2. 包一个 <MarkdownPreBlock> 子组件需要在 markdown 解析前拦截,改动面太大
 * 3. 幂等去重:bar 存在就跳过,反复调用安全
 *
 * 性能:onUpdated 触发频率 = watch 触发频率,流式时每帧 ~5ms,可接受
 */
function attachCopyButtons(container: HTMLElement) {
    container.querySelectorAll<HTMLPreElement>('pre.markdown-pre').forEach((pre) => {
        // 幂等:已挂过跳过
        if (pre.querySelector('.markdown-pre__bar')) return
        pre.style.position = 'relative'

        const lang = pre.dataset.language ?? ''
        const bar = document.createElement('div')
        bar.className = 'markdown-pre__bar'
        // innerHTML 拼字符串:语言标签已 escapeHtml 兜底,Copy 按钮是固定文本无注入面
        bar.innerHTML =
            `<span class="markdown-pre__lang">${escapeHtml(lang)}</span>` +
            `<button type="button" class="markdown-pre__copy" aria-label="Copy code">` +
            `<span class="markdown-pre__copy-text">Copy</span></button>`
        pre.prepend(bar)

        const copyBtn = bar.querySelector<HTMLButtonElement>('.markdown-pre__copy')
        copyBtn?.addEventListener('click', () => {
            const code = pre.querySelector('code')?.textContent ?? ''
            navigator.clipboard.writeText(code).then(() => {
                const txt = copyBtn.querySelector('.markdown-pre__copy-text')!
                const old = txt.textContent
                txt.textContent = 'Copied'
                setTimeout(() => { txt.textContent = old }, 1200)
            })
        })
    })
}

onMounted(() => {
    nextTick(() => root.value && attachCopyButtons(root.value))
})

onUpdated(() => {
    // v-html 更新后等下一 tick(DOM 写入完成)再挂 Copy 按钮
    nextTick(() => root.value && attachCopyButtons(root.value))
})

// 组件卸载时清理 rAF,避免内存泄漏 + 对已卸载组件赋值
onUnmounted(() => {
    if (rafId !== null) cancelAnimationFrame(rafId)
})
</script>

<style scoped>
/* 容器只控制布局,token 颜色用全局 .markdown 样式(base.css) */
.markdown-wrap {
    min-width: 0;
    word-break: break-word;
    /* block(默认)让内部 <h1>/<p>/<pre> 正常堆叠,光标 <span> 是 inline 自然跟在末元素后 */
}
.markdown {
    min-width: 0;
    word-break: break-word;
}
</style>
