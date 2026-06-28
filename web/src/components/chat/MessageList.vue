<template>
    <div ref="scrollerRef" class="message-list chat-layout__message--fade">
        <!-- 空状态占位（Fraunces 标题，期刊编辑感） -->
        <div v-if="currentMessages.length === 0" class="message-list__empty">
            <h1 class="message-list__title">Open Data Meta Guard</h1>
            <p class="message-list__hint">提问以开始一次数据探查。</p>
        </div>
        <!-- 内层 contentRef 容器：ResizeObserver 监听它的尺寸变化来驱动粘底滚动 -->
        <div ref="contentRef">
            <MessageItem v-for="msg in currentMessages" :key="msg.id" :message="msg" />
        </div>
        <!-- FAB：未粘底 + 离底距离 > 阈值时显示，点击平滑滚到底部 -->
        <button
            v-if="showJumpToBottom"
            type="button"
            class="chat-scroll-fab"
            aria-label="跳到底部"
            title="跳到底部"
            @click="scrollToBottom(true)"
        >↓</button>
    </div>
</template>


<script setup lang="ts">
import { useTemplateRef } from 'vue'
import MessageItem from "./MessageItem.vue";
import {useChatStore} from '@/stores/chat'
import {storeToRefs} from 'pinia'
import { useChatScroll } from '@/composables/useChatScroll'

// 传递信息
const store=useChatStore()
const {currentMessages} =storeToRefs(store)

// 滚动容器 ref + 内容容器 ref —— useChatScroll 需要两根 ref
const scrollerRef = useTemplateRef<HTMLElement>('scrollerRef')
const contentRef = useTemplateRef<HTMLElement>('contentRef')

// 智能粘底：用户在底部跟随；向上翻暂停；滚回底部恢复；FAB 显隐
const { showJumpToBottom, scrollToBottom } = useChatScroll(scrollerRef, contentRef)
</script>

<style scoped>
.message-list {
    padding: var(--sp-4);
    /* FAB 绝对定位的参考系（.chat-layout__message 在 base.css 加 position: relative） */
    position: relative;
}

/* 空状态：Fraunces 衬线大标题 + 三级灰提示 */
.message-list__empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    min-height: 60vh;
}

.message-list__title {
    font-family: var(--font-display);
    font-size: var(--text-xl);
    font-weight: 400;
    letter-spacing: -0.02em;
    margin-bottom: var(--sp-2);
    color: var(--ink);
}

.message-list__hint {
    color: var(--ink-mute);
    font-size: var(--text-sm);
}
</style>
