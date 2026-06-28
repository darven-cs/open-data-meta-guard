<template>
    <div class="chat-input">
        <textarea
            ref="textareaRef"
            class="chat-input__field"
            v-model="text"
            :rows="1"
            :placeholder="placeholder"
            @keydown.enter="onEnter"
            @input="autoResize"
        />

        <div class="chat-input__hint-row">
            <span class="chat-input__hint-left">回车发送 · Shift+回车换行</span>
            <span
                class="chat-input__counter"
                :class="{ 'chat-input__counter--over': isOverLimit }"
            >
                {{ text.length }} / {{ MAX_LEN }}
            </span>
        </div>

        <div class="chat-input__actions">
            <span class="chat-input__shortcut">⇧⏎ 换行</span>

            <button
                v-if="!streaming"
                class="chat-input__send"
                :disabled="!canSend"
                @click="send"
            >
                发送
            </button>
            <button
                v-else
                class="chat-input__stop"
                @click="emit('stop')"
                aria-label="停止生成"
            >
                <span class="chat-input__stop-icon"></span>
                停止
            </button>
        </div>
    </div>
</template>


<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue"

const props = defineProps<{ streaming: boolean }>()
const emit = defineEmits<{
    (e: 'send', text: string): void
    (e: 'stop'): void
}>()

const text = ref('')
const textareaRef = ref<HTMLTextAreaElement | null>(null)
const MAX_LEN = 4000

const placeholder = '说点什么……'

const canSend = computed(
    () =>
        !props.streaming &&
        text.value.trim().length > 0 &&
        text.value.length <= MAX_LEN
)
const isOverLimit = computed(() => text.value.length > MAX_LEN)

function autoResize() {
    const el = textareaRef.value
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 200) + 'px'
}
watch(text, () => nextTick(autoResize))

function send() {
    if (!canSend.value) return
    emit('send', text.value.trim())
    text.value = ''
    nextTick(() => textareaRef.value?.focus())
}

function onEnter(e: KeyboardEvent) {
    // IME 组合态守卫：拼音/中文输入法按回车确认时不让其触发发送
    if (e.isComposing || e.keyCode === 229) return
    if (e.shiftKey) return                            // 显式换行
    e.preventDefault()
    send()
}
</script>

<style scoped>
.chat-input {
    display: flex;
    flex-direction: column;
    gap: var(--sp-2);
    padding: var(--sp-4);
    border-top: 1px solid var(--hairline);
    background: var(--paper);
    position: relative;
}

/* 顶部纸面分层渐变：让 ChatInput 与消息区有「分层」感 */
.chat-input::before {
    content: '';
    position: absolute;
    inset: -4px 0 auto 0;
    height: 4px;
    background: linear-gradient(to bottom, var(--paper-sub), transparent);
    pointer-events: none;
}

/* textarea:撑高的核心 */
.chat-input__field {
    width: 100%;
    min-height: 32px;
    max-height: 200px;
    resize: none;
    box-sizing: border-box;
    padding: var(--sp-3);
    border: 1px solid var(--hairline);
    border-radius: var(--radius-md);
    font: inherit;
    color: var(--ink);
    background: var(--paper);
    outline: none;
    box-shadow: inset 0 1px 2px rgba(10, 10, 10, 0.04);
    transition: border-color 0.15s ease, box-shadow 0.15s ease;
    font-family: var(--font-sans);
    line-height: 1.5;
}

/* placeholder:Fraunces 斜体,与正文形成 editorial 对比 */
.chat-input__field::placeholder {
    font-family: var(--font-display);
    font-style: italic;
    color: var(--ink-mute);
}

.chat-input__field:focus {
    border-color: var(--hairline-strong);
}

/* 提示行(快捷键 + 字符计数) */
.chat-input__hint-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-family: var(--font-sans);
    font-size: var(--text-xs);
    color: var(--ink-mute);
    text-transform: uppercase;
    letter-spacing: 0.04em;
    padding: 0 var(--sp-1);
    min-height: 14px;
}

.chat-input__hint-left { color: var(--ink-mute); }

.chat-input__counter--over {
    color: var(--accent);
    font-weight: 600;
}

/* 底栏:左快捷键提示 + 右按钮 */
.chat-input__actions {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--sp-3);
}

.chat-input__shortcut {
    font-family: var(--font-sans);
    font-size: var(--text-xs);
    color: var(--ink-mute);
    text-transform: uppercase;
    letter-spacing: 0.04em;
}

/* 发送按钮:油墨实色 Swiss CTA */
.chat-input__send {
    flex-shrink: 0;
    padding: var(--sp-2) var(--sp-5);
    border: none;
    border-radius: var(--radius-md);
    background: var(--ink);
    color: var(--paper);
    font-family: var(--font-sans);
    font-size: var(--text-sm);
    letter-spacing: 0.02em;
    cursor: pointer;
    transition: background 0.15s ease, transform 0.08s ease, box-shadow 0.15s ease;
    box-shadow: 0 1px 0 rgba(10, 10, 10, 0.06);
}

.chat-input__send:hover:not(:disabled) {
    background: var(--ink-sub);
}

.chat-input__send:active:not(:disabled) {
    transform: translateY(1px);
    box-shadow: none;
}

.chat-input__send:disabled {
    opacity: 0.4;
    cursor: not-allowed;
}

/* 停止按钮:朱红边框 + 朱红字 + 透明底,hover 时朱红底纸白字 */
.chat-input__stop {
    flex-shrink: 0;
    display: inline-flex;
    align-items: center;
    gap: var(--sp-2);
    padding: var(--sp-2) var(--sp-4);
    border: 1px solid var(--accent);
    border-radius: var(--radius-md);
    background: transparent;
    color: var(--accent);
    font-family: var(--font-sans);
    font-size: var(--text-sm);
    letter-spacing: 0.02em;
    cursor: pointer;
    transition: background 0.15s ease, color 0.15s ease;
}

.chat-input__stop:hover {
    background: var(--accent);
    color: var(--paper);
}

/* 停止方块:1.6s 呼吸动画,呼应 MessageList 流式光标但更克制 */
.chat-input__stop-icon {
    display: inline-block;
    width: 8px;
    height: 8px;
    background: currentColor;
    border-radius: 1px;
    animation: stop-pulse 1.6s ease-in-out infinite;
}

@keyframes stop-pulse {
    0%, 100% { opacity: 0.6; }
    50%      { opacity: 1; }
}

@media (prefers-reduced-motion: reduce) {
    .chat-input__stop-icon { animation: none; }
}
</style>
