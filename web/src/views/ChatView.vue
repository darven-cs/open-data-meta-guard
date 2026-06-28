<!--
  ChatView: 数据小D（Phase 0 骨架就绪）
  - ChatLayout 自身带 height:100vh,容器占满即可
  - Phase 5 在 ChatLayout 接入 chat agent 与 SSE 流式
-->
<template>
  <div class="chat-view">
    <ChatLayout />
  </div>
</template>

<script setup lang="ts">
import ChatLayout from '@/components/chat/ChatLayout.vue'
</script>

<style scoped>
.chat-view {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100vh;
}
</style>
