import {ref, computed} from 'vue'
import {defineStore} from 'pinia'
import type {Conversation, Message, MessageStatus} from '@/types/chat'
import {
  createConversationApi,
  fetchConversationsApi,
  fetchMessagesApi,
  deleteConversationApi,
} from '@/api/chat'


export const useChatStore = defineStore('chat', () => {
    const conversations = ref<Conversation[]>([])
    const currentId = ref<string | null>(null)

    const currentConversation = computed(() =>
      conversations.value.find(c => c.id === currentId.value)
    )
    const currentMessages = computed(() =>
      currentConversation.value?.messages ?? []      // 没有当前会话就返回空数组
    )

    // ── 本地辅助 ──

    // ── 会话 CRUD ──

    async function createConversation(): Promise<string> {
      const server = await createConversationApi('新会话')
      const conv: Conversation = {
        id: server.id,
        title: server.title,
        messages: [],
        createdAt: server.created_at ? Date.parse(server.created_at) : Date.now(),
      }
      conversations.value.push(conv)
      currentId.value = conv.id
      return conv.id
    }

    async function ensureActiveConversation(): Promise<string> {
      if (currentId.value) return currentId.value
      return await createConversation()
    }

    function selectConversation(id: string) {
      currentId.value = id
    }

    // ── 远程同步 ──

    async function loadConversationsFromServer() {
      try {
        const list = await fetchConversationsApi()
        for (const s of list) {
          const exists = conversations.value.find(c => c.id === s.id)
          if (!exists) {
            conversations.value.push({
              id: s.id,
              title: s.title,
              messages: [],
              createdAt: s.created_at ? Date.parse(s.created_at) : Date.now(),
            })
          } else {
            // 同步标题（LLM 可能在后台更新了标题）
            exists.title = s.title
          }
        }
      } catch (e) {
        console.warn('[chat store] loadConversationsFromServer failed:', e)
      }
    }

    async function loadMessages(convId: string) {
      const conv = conversations.value.find(c => c.id === convId)
      if (!conv) return
      // 已有消息 → 跳过（本地已有则不再重复加载）
      if (conv.messages.length > 0) return
      try {
        const list = await fetchMessagesApi(convId)
        conv.messages = list.map(m => ({
          id: m.id,
          role: m.role as 'user' | 'assistant',
          content: m.content,
          steps: m.tool_steps?.map(s => ({ name: s.tool, status: s.status as 'running' | 'done' })) ?? [],
          createdAt: m.created_at ? Date.parse(m.created_at) : Date.now(),
          status: 'done' as MessageStatus,
        }))
      } catch (e) {
        console.warn('[chat store] loadMessages failed:', e)
      }
    }

    async function switchConversation(convId: string) {
      selectConversation(convId)
      await loadMessages(convId)
    }

    async function deleteRemoteConversation(convId: string) {
      try {
        await deleteConversationApi(convId)
      } catch (e) {
        console.warn('[chat store] deleteRemoteConversation failed:', e)
      }
      // 无论远程是否成功，都从本地移除
      const idx = conversations.value.findIndex(c => c.id === convId)
      if (idx !== -1) conversations.value.splice(idx, 1)
      if (currentId.value === convId) {
        currentId.value = conversations.value[0]?.id ?? null
      }
    }

    // ── 消息操作 ──

    function addMessage(message: Message) {
      currentConversation.value?.messages.push(message)
    }

    function sendUserMessage(text: string) {
        addMessage({
            id: crypto.randomUUID(),
            role: 'user',
            content: text,
            createdAt: Date.now(),
        })
    }

    // ===== SSE 流式消息更新（Step 5）=====
    // 一条 assistant 消息 = 一整轮 SSE 事件聚合，下面 6 个 action 各对应一种事件

    // 在所有会话里按 id 找消息（流式过程中用户切会话也能继续更新这条消息）
    function findMessage(messageId: string): Message | undefined {
      for (const conv of conversations.value) {
        const msg = conv.messages.find(m => m.id === messageId)
        if (msg) return msg
      }
      return undefined
    }

    // 创建空的 assistant 消息作为流式容器，返回 id 给 useChat 持有
    function startAssistantMessage(): string {
      const id = crypto.randomUUID()
      addMessage({
        id,
        role: 'assistant',
        content: '',
        reasoning: '',
        steps: [],
        createdAt: Date.now(),
        status: 'streaming',
      })
      return id
    }

    function appendContent(messageId: string, chunk: string) {
      const msg = findMessage(messageId)
      if (msg) msg.content += chunk
    }

    function appendReasoning(messageId: string, chunk: string) {
      const msg = findMessage(messageId)
      if (msg) msg.reasoning = (msg.reasoning ?? '') + chunk
    }

    function addToolStep(messageId: string, tool: string) {
      const msg = findMessage(messageId)
      if (msg) {
        if (!msg.steps) msg.steps = []
        msg.steps.push({ name: tool, status: 'running' })
      }
    }

    // 倒序找最后一个同名 running 改 done（同名工具在一次对话里可能被多次调用）
    function finishToolStep(messageId: string, tool: string) {
      const msg = findMessage(messageId)
      if (msg?.steps) {
        for (let i = msg.steps.length - 1; i >= 0; i--) {
          if (msg.steps[i].name === tool && msg.steps[i].status === 'running') {
            msg.steps[i].status = 'done'
            break
          }
        }
      }
    }

    function setMessageStatus(messageId: string, status: MessageStatus) {
      const msg = findMessage(messageId)
      if (msg) msg.status = status
    }

     return {
      // 暴露给组件用的：state + getters + actions
      conversations,
      currentId,
      currentConversation,
      currentMessages,
      createConversation,
      ensureActiveConversation,
      selectConversation,
      addMessage,
      sendUserMessage,
      // 远程同步
      loadConversationsFromServer,
      loadMessages,
      switchConversation,
      deleteRemoteConversation,
      // SSE 流式相关
      startAssistantMessage,
      appendContent,
      appendReasoning,
      addToolStep,
      finishToolStep,
      setMessageStatus,
    }

})
