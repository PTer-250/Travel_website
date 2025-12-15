export interface AgentConversation {
  id: number
  title: string
  summary?: string | null
  created_at: string
  updated_at: string
  last_message_preview?: string | null
}

export type AgentRole = 'user' | 'assistant' | 'tool'

export interface AgentMessage {
  id: number
  conversation_id: number
  role: AgentRole
  content: string
  tool_name?: string | null
  tool_call_id?: string | null
  tool_args?: Record<string, unknown> | null
  tool_output?: Record<string, unknown> | null
  created_at: string
}

export interface AgentChatResponse {
  conversation_id: number
  messages: AgentMessage[]
}

export interface AgentStreamStatus {
  status: string
  conversation_id?: number | null
  tool_name?: string | null
  tool_call_id?: string | null
  tool_args?: Record<string, unknown> | null
  label?: string | null
  message?: string | null
  tool_output_preview?: string | null
}
