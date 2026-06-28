export type MessageRole = 'user' | 'assistant'

export type MessageStatus = 'pending' | 'streaming' | 'done' | 'error'

export interface ToolStep {
    name: string                 // 如 'web_scrap_tool' / 'data_story_tool'
    status: 'running' | 'done'   // tool_start→running, tool_end→done
}

export interface Message {
    id: string
    role: MessageRole
    content: string
    reasoning?: string
    steps?: ToolStep[]
    createdAt: number
    status?: MessageStatus
}

export interface Conversation{
    id:string,
    title:string,
    messages:Message[],
    createdAt:number
}
