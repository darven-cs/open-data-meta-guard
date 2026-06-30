<template>
    <div class="message-item" :class="`message-item--${message.role}`">
        <div class="message-item__bubble" :class="`message-item__bubble--${message.role}`">
            <!-- reasoning 折叠面板：独立 block 元素，宽度自然填满 bubble -->
            <div
                v-if="message.reasoning"
                class="message-item__reasoning"
            >
                <div
                    class="message-item__reasoning-header"
                    @click="isCollapsed = !isCollapsed"
                >
                    <span class="message-item__reasoning-title">
                        {{ reasoningTitle }}
                    </span>
                    <span class="message-item__reasoning-chevron">
                        {{ isCollapsed ? '▸' : '▾' }}
                    </span>
                </div>
                <div
                    v-show="!isCollapsed"
                    class="message-item__reasoning-body"
                >
                    {{ message.reasoning }}
                </div>
            </div>

            <!-- tool steps 进度条：只在 assistant 消息有 steps 时显示 -->
            <div
                v-if="message.role === 'assistant' && message.steps && message.steps.length > 0"
                class="message-item__steps"
            >
                <div
                    v-for="(step, idx) in message.steps"
                    :key="idx"
                    class="message-item__step"
                    :class="`message-item__step--${step.status}`"
                >
                    <span class="message-item__step-dot"></span>
                    <span class="message-item__step-name">{{ step.name }}</span>
                </div>
            </div>

            <!-- assistant：monogram + content 内层横向 row（避免被 reasoning 挤成竖条） -->
            <div v-if="message.role === 'assistant'" class="message-item__row">
                <span class="message-item__role">A</span>
                <div class="message-item__content">
                    <MarkdownView :content="message.content" :status="message.status" />
                </div>
            </div>

            <!-- user：白空间换行保留包一层({{ }} 插值天然 XSS-safe) -->
            <div v-else class="message-item__content">
                <div class="message-item__user-text">{{ message.content }}</div>
            </div>
        </div>
    </div>
</template>


<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import type { Message } from "@/types/chat"
import MarkdownView from './MarkdownView.vue';

const props = defineProps<{
    message: Message,
}>()

// 折叠状态：流式展开，完成自动折叠
const isCollapsed = ref(false)

// header 标题：流式中显示「思考中…」，其他显示「思考过程」
const reasoningTitle = computed(() => {
    return props.message.status === 'streaming' ? '思考中…' : '思考过程'
})

// status 变化时自动调整折叠状态
watch(
    () => props.message.status,
    (newStatus) => {
        if (newStatus === 'done') isCollapsed.value = true
        else if (newStatus === 'streaming') isCollapsed.value = false
    }
)
</script>

<style scoped>
.message-item {
    display: flex;
    margin-bottom: var(--sp-4);
}

.message-item--user {
    justify-content: flex-end;
}

.message-item--assistant {
    justify-content: flex-start;
}

/* —— 气泡基础 —— */
.message-item__bubble {
    max-width: 70%;
    padding: var(--sp-2) var(--sp-3);
    border-radius: var(--radius-md);
    word-break: break-word;
    min-width: 0;
    /* 长文本换行，配合父级 min-width:0 防溢出 */
}

/* —— user：油墨黑底 / 纸白字 / 方角 4px —— */
.message-item__bubble--user {
    background: var(--ink);
    color: var(--paper);
}

/* —— assistant：透明底，文档流文本（编辑感），block 布局避免 reasoning 挤窄 content —— */
.message-item__bubble--assistant {
    background: transparent;
    color: var(--ink);
    border-radius: 0;
    padding-left: 0;
    padding-right: 0;
    max-width: 100%;
    /* assistant 是文档流文本，bubble 退回 block；monogram+content 由内层 row 管理 flex */
}

/* —— assistant monogram + content 横向 row —— */
.message-item__row {
    display: flex;
    align-items: flex-start;
    gap: var(--sp-2);
    min-width: 0;
}

/* —— assistant monogram：Fraunces 斜体 + 朱红色（期刊感） —— */
.message-item__role {
    font-family: var(--font-display);
    font-style: italic;
    color: var(--accent);
    font-size: var(--text-md);
    line-height: 1.55;
    flex-shrink: 0;
}

/* —— reasoning：朱红竖线 + 透明底 + 斜体衬线（block 元素，自然填满 bubble 宽度） —— */
.message-item__reasoning {
    margin-bottom: var(--sp-2);
    border-left: 2px solid var(--accent);
    background: transparent;
    border-radius: 0;
    padding: 0 var(--sp-3);
    font-family: var(--font-display);
    font-style: italic;
    color: var(--ink-sub);
    min-width: 0;
    box-sizing: border-box;
}

/* —— tool steps 进度条 —— */
.message-item__steps {
    display: flex;
    flex-wrap: wrap;
    gap: var(--sp-1) var(--sp-2);
    margin-bottom: var(--sp-2);
    padding: var(--sp-1) 0;
    min-width: 0;
}

.message-item__step {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-family: var(--font-sans);
    font-size: var(--text-xs);
    padding: 2px 8px;
    border-radius: var(--radius-sm);
    background: var(--ink-dim);
    color: var(--ink-mute);
}

.message-item__step--running {
    background: var(--accent);
    color: var(--paper);
}

.message-item__step--done {
    background: var(--ink-dim);
    color: var(--ink-sub);
}

/* 小圆点 */
.message-item__step-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    flex-shrink: 0;
    background: currentColor;
    opacity: 0.6;
}

.message-item__step--running .message-item__step-dot {
    opacity: 1;
    animation: step-pulse 1.2s ease-in-out infinite;
}

@keyframes step-pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.3; }
}

.message-item__step-name {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 160px;
}

.message-item__reasoning-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    cursor: pointer;
    user-select: none;
    font-weight: 500;
    font-style: normal;
    font-family: var(--font-sans);
    font-size: var(--text-sm);
    color: var(--ink-mute);
}

.message-item__reasoning-title {
    color: var(--ink-mute);
}

.message-item__reasoning-chevron {
    font-size: 0.75em;
    opacity: 0.7;
}

.message-item__reasoning-body {
    margin-top: var(--sp-2);
    white-space: pre-wrap;
    word-break: break-word;
    min-width: 0;
    font-size: var(--text-sm);
}

.message-item__content {
    word-break: break-word;
    min-width: 0;
    /* assistant 模式下 flex 子项，需要 flex:1 防止挤爆 */
    flex: 1;
}

/* —— user 消息：保留换行 + tab 渲染 —— */
/* {{ }} 插值天然 XSS-safe，走 pre-wrap 比 markdown-it 渲染更稳 */
.message-item__user-text {
    white-space: pre-wrap;
    word-break: break-word;
    tab-size: 4;
}
</style>
