import { fetchEventSource } from '@microsoft/fetch-event-source'

// ───────── 服务端数据类型 ─────────

export interface ServerConversation {
    id: string
    title: string
    created_at?: string
    updated_at?: string
}

export interface ServerMessage {
    id: string
    conversation_id: string
    role: string
    content: string
    chart_paths: { chart_type: string; file_path: string; title: string }[]
    kg_context: Record<string, unknown>
    tool_steps: { tool: string; status: string }[]
    created_at?: string
}

// ───────── SSE 回调 ─────────

// 6 种 SSE 事件对应的回调（和后端 app/api/routes/agent.py 的 event 一一对应）
export interface SSECallbacks {
    onToken: (content: string) => void      // event: token
    onReasoning: (content: string) => void  // event: reasoning
    onToolStart: (tool: string) => void     // event: tool_start
    onToolEnd: (tool: string) => void       // event: tool_end
    onDone: () => void                       // event: done
    onError: (err: unknown) => void         // event: error 或网络错误
}

// ───────── SSE 流式请求 ─────────

export async function streamChat(
    message: string,
    conversationId: string | null,
    callbacks: SSECallbacks,
    signal?: AbortSignal,
) {
    try {
        await fetchEventSource('/api/agent/stream', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message,
                conversation_id: conversationId,
            }),
            signal,

            // 连接打开：检查 HTTP 状态
            async onopen(res) {
                if (!res.ok) throw new Error(`HTTP ${res.status}`)
            },

            // 收到一个事件（所有事件都走这里，靠 ev.event 分流）
            onmessage(ev) {
                // ev.data 是字符串，后端发的是 JSON 字符串，要 parse
                const data = ev.data ? JSON.parse(ev.data) : {}
                switch (ev.event) {
                    case 'token': callbacks.onToken(data.content); break
                    case 'reasoning': callbacks.onReasoning(data.content); break
                    case 'tool_start': callbacks.onToolStart(data.tool); break
                    case 'tool_end': callbacks.onToolEnd(data.tool); break
                    case 'done': callbacks.onDone(); break
                    case 'error': callbacks.onError(data); break
                }
            },

            // 网络错误
            onerror(err) {
                callbacks.onError(err)
                throw err   // 必须抛出！否则 fetch-event-source 默认会自动重连（指数退避），
                // AI 聊天场景重连会导致重复消息，所以要 throw 停止重连
            },
        })
    } catch (err) {
        callbacks.onError(err)
    }
}

// ───────── HTTP 会话/消息 API ─────────

export async function createConversationApi(title = '新会话'): Promise<ServerConversation> {
    const res = await fetch('/api/agent/conversations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title }),
    })
    const json = await res.json()
    if (json.code !== 200) throw new Error(json.msg || 'create conversation failed')
    return json.data as ServerConversation
}

export async function fetchConversationsApi(): Promise<ServerConversation[]> {
    const res = await fetch('/api/agent/conversations')
    const json = await res.json()
    if (json.code !== 200) throw new Error(json.msg || 'fetch conversations failed')
    return json.data as ServerConversation[]
}

export async function fetchMessagesApi(convId: string): Promise<ServerMessage[]> {
    const res = await fetch(`/api/agent/conversations/${convId}/messages`)
    const json = await res.json()
    if (json.code !== 200) throw new Error(json.msg || 'fetch messages failed')
    return json.data as ServerMessage[]
}

export async function deleteConversationApi(convId: string): Promise<void> {
    const res = await fetch(`/api/agent/conversations/${convId}`, { method: 'DELETE' })
    const json = await res.json()
    if (json.code !== 200) throw new Error(json.msg || 'delete conversation failed')
}
