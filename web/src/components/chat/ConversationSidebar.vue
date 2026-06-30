<template>
    <div class="conversation-sidebar">
        <!-- 新建会话按钮 -->
        <button class="conversation-sidebar__new" @click="handleNew">
            + 新建会话
        </button>

        <!-- 会话列表 -->
        <ul class="conversation-sidebar__list">
            <li v-for="conv in conversations" :key="conv.id" class="conversation-sidebar__item"
                :class="{ 'conversation-sidebar__item--active': conv.id === currentId }"
                @click="handleSwitch(conv.id)">
                <span class="conversation-sidebar__title">{{ conv.title }}</span>
                <button
                    class="conversation-sidebar__delete"
                    @click.stop="handleDelete(conv.id)"
                    title="删除会话"
                >
                    &times;
                </button>
            </li>
        </ul>
    </div>
</template>


<script setup lang="ts">
import { useChatStore } from '@/stores/chat'
import { storeToRefs } from 'pinia'
const store = useChatStore()
const { conversations, currentId } = storeToRefs(store)

async function handleNew() {
    await store.createConversation()
}

async function handleSwitch(id: string) {
    await store.switchConversation(id)
}

async function handleDelete(id: string) {
    await store.deleteRemoteConversation(id)
}
</script>

<style scoped>
.conversation-sidebar {
    height: 100%;
    display: flex;
    flex-direction: column;
    gap: var(--sp-3);
}

/* 新建按钮：发丝框 + 油墨字 + 朱红 hover 下划线（Swiss 风） */
.conversation-sidebar__new {
    padding: var(--sp-2) var(--sp-3);
    border: 1px solid var(--hairline);
    border-radius: var(--radius-sm);
    background: transparent;
    color: var(--ink);
    font-family: var(--font-sans);
    font-size: var(--text-sm);
    letter-spacing: 0.02em;
    cursor: pointer;
    transition: border-color 0.15s;
}

.conversation-sidebar__new:hover {
    border-color: var(--ink);
    text-decoration: underline;
    text-decoration-color: var(--accent);
    text-underline-offset: 4px;
}

.conversation-sidebar__list {
    list-style: none;
    margin: 0;
    padding: 0;
    flex: 1;
    overflow-y: auto;
    /* 会话多了自己滚 */
}

.conversation-sidebar__item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: var(--sp-2) var(--sp-3);
    border-left: 2px solid transparent;
    cursor: pointer;
    color: var(--ink-sub);
    transition: background 0.12s;
}

.conversation-sidebar__item:hover {
    background: var(--paper-sub);
}

/* active：透明底 + 朱红左竖线 + 油墨字加粗（Swiss 风不用色块） */
.conversation-sidebar__item--active {
    background: transparent;
    color: var(--ink);
    font-weight: 600;
    border-left-color: var(--accent);
}

.conversation-sidebar__title {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    flex: 1;
    min-width: 0;
}

.conversation-sidebar__delete {
    flex-shrink: 0;
    margin-left: var(--sp-2);
    padding: 0 4px;
    border: none;
    background: transparent;
    color: var(--ink-sub);
    font-size: 16px;
    line-height: 1;
    cursor: pointer;
    opacity: 0;
    transition: opacity 0.12s, color 0.12s;
}

.conversation-sidebar__item:hover .conversation-sidebar__delete {
    opacity: 1;
}

.conversation-sidebar__delete:hover {
    color: var(--accent);
}
</style>
