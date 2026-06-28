import {ref,computed} from 'vue'
import {defineStore} from 'pinia'
import type {Conversation,Message,MessageStatus} from '@/types/chat'


export const useChatStore=defineStore('chat',()=>{
    const conversations=ref<Conversation[]>([])
    const currentId=ref<string|null>(null)

    const currentConversation = computed(() =>
      conversations.value.find(c => c.id === currentId.value)
    )
    const currentMessages = computed(() =>
      currentConversation.value?.messages ?? []      // 没有当前会话就返回空数组
    )

    function createConversation(): string {
      const id = crypto.randomUUID()
      conversations.value.push({
        id,
        title: '新会话',
        messages: [],
        createdAt: Date.now(),
      })
      currentId.value = id          // 新建后自动切到它
      return id
    }

    function selectConversation(id: string) {
      currentId.value = id
    }

    function addMessage(message: Message) {
      currentConversation.value?.messages.push(message)
    }

    function sendUserMessage(text:string){
        addMessage({
            id:crypto.randomUUID(),
            role:'user',
            content:text,
            createdAt:Date.now(),
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
      selectConversation,
      addMessage,
      sendUserMessage,
      // SSE 流式相关
      startAssistantMessage,
      appendContent,
      appendReasoning,
      addToolStep,
      finishToolStep,
      setMessageStatus,
    }

})


