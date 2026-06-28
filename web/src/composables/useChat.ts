import { computed, ref } from 'vue'
import { streamChat } from '@/api/chat'
import { useChatStore } from '@/stores/chat'

// 模块级 AbortController：跨 useChat() 多次调用共享，
// 用户在流式中切会话也能命中同一个 controller 触发停止
let controller: AbortController | null = null
// 暴露给 UI 的响应式流式状态（只读语义）
const isStreaming = ref(false)

// 高层封装：把"发消息"这件事编排出完整流程
// UI 组件只调 useChat().send(text)，不直接碰 store / api 细节
export function useChat() {
  const store = useChatStore()

  async function send(text: string) {
    // 防御：已有流在跑直接拒收（UI 已禁用按钮，但双保险）
    if (controller) return

    // 1. 没会话先建（addMessage 依赖 currentConversation 非空，currentId=null 时 ?. 短路）
    if (!store.currentId) {
      store.createConversation()
    }

    // 2. user 消息进 store
    store.sendUserMessage(text)

    // 3. 占位 assistant 消息——整轮 SSE 流的事件都聚合到这一条
    const assistantId = store.startAssistantMessage()

    // 4. 启 controller,流式态置 true
    controller = new AbortController()
    isStreaming.value = true

    try {
      // 5. 6 种 SSE 事件 → store action 一一映射
      await streamChat(text, {
        onToken: (c) => store.appendContent(assistantId, c),
        onReasoning: (c) => store.appendReasoning(assistantId, c),
        onToolStart: (t) => store.addToolStep(assistantId, t),
        onToolEnd: (t) => store.finishToolStep(assistantId, t),
        onDone: () => store.setMessageStatus(assistantId, 'done'),
        onError: () => store.setMessageStatus(assistantId, 'error'),
      }, controller.signal)
    } finally {
      // 无论正常完成 / 出错 / 被 abort,都清 controller,让 UI 退出流式态
      controller = null
      isStreaming.value = false
    }
  }

  function stop() {
    if (!controller) return
    controller.abort()    // 触发 fetchEventSource onerror → onError 回调 → setMessageStatus('error')
    // controller = null / isStreaming = false 会在 send 的 finally 里完成
  }

  return { send, stop, isStreaming: computed(() => isStreaming.value) }
}
