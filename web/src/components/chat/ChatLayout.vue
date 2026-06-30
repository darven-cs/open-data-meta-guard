<template>
    <div class="chat-layout">
        <aside class="chat-layout__sidebar">
            <ConversationSidebar/>
        </aside>


        <main class="chat-layout__main">
            <!-- 不使用props传递,而是使用store -->
            <MessageList class="chat-layout__message" />
            <ChatInput
                class="chat-layout__input"
                :streaming="isStreaming"
                @send="handleSend"
                @stop="stop"
            />
        </main>
    </div>
</template>

<script setup lang="ts">
import {onMounted} from 'vue'
import ChatInput from './ChatInput.vue';
import MessageList from './MessageList.vue';
import ConversationSidebar from './ConversationSidebar.vue';
import {useChatStore} from '@/stores/chat'
import {useChat} from '@/composables/useChat'

const store=useChatStore()
const {send, stop, isStreaming}=useChat()

function handleSend(text:string){
    send(text)
}

onMounted(async () => {
    // 仅加载历史会话列表，不建空会话——等用户发第一条消息时再懒创建
    await store.loadConversationsFromServer()
  })


</script>

<style scoped>
.chat-layout {
    /* flex布局.默认是左右 */
    display: flex;
    /* 高度100%占满 */
    height: 100vh;
    /* 避免内部溢出导致滚条 */
    overflow: hidden;
}

.chat-layout__sidebar {
    /* 制定宽度（Swiss 风更紧凑） */
    width: 240px;
    /* 内边距 */
    padding: var(--sp-4);
    /* 右侧发丝分隔线，替代原隐式分隔 */
    border-right: 1px solid var(--hairline);
}

.chat-layout__main {
    /* 子元素自动填充满边框 */
    flex: 1;
    /* flex布局,使用上下布局 */
    display: flex;
    flex-direction: column;
    /* flex防止溢出 */
    min-width: 0;
}

.chat-layout__message {
    flex: 1;
    overflow-y: auto;
    min-height: 0;
}

.chat-layout__input {
    /* 0表示禁止被压缩,根据内部元素的大小制定 */
    flex-shrink: 0;
}
</style>
