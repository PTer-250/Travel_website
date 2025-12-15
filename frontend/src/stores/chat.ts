import { defineStore } from 'pinia'
import {
  deleteAgentConversation,
  fetchAgentConversations,
  fetchAgentMessages,
  streamAgentMessage,
} from '../services/api'
import type { AgentConversation, AgentMessage, AgentStreamStatus } from '../types/agent'
import { useAuthStore } from './auth'

export type ToolActivityStatus = 'pending' | 'running' | 'completed' | 'failed'

export interface ToolActivityEntry {
  toolCallId: string
  conversationId: number
  toolName: string | null
  label: string
  status: ToolActivityStatus
  toolArgs?: Record<string, unknown> | null
  toolOutputPreview?: string | null
  message?: string | null
  startedAt: string
  updatedAt: string
}

interface ChatState {
  conversations: AgentConversation[]
  messages: AgentMessage[]
  activeConversationId: number | null
  loading: boolean
  sending: boolean
  error: string | null
  toolActivities: Record<number, Record<string, ToolActivityEntry>>
}

export const useChatStore = defineStore('chat', {
  state: (): ChatState => ({
    conversations: [],
    messages: [],
    activeConversationId: null,
    loading: false,
    sending: false,
    error: null,
    toolActivities: {},
  }),

  actions: {
    startNewConversation() {
      this.activeConversationId = null
      this.messages = []
    },

    async init() {
      await this.refreshConversations()
      if (this.conversations.length > 0) {
        const first = this.conversations[0]
        if (!first) return
        await this.loadMessages(first.id)
      }
    },

    async refreshConversations() {
      try {
        this.loading = true
        this.conversations = await fetchAgentConversations()
      } catch (error) {
        this.error = error instanceof Error ? error.message : '加载会话失败'
      } finally {
        this.loading = false
      }
    },

    async loadMessages(conversationId: number) {
      try {
        this.loading = true
        this.activeConversationId = conversationId
        const rawMessages = await fetchAgentMessages(conversationId)
        this.rebuildToolActivities(conversationId, rawMessages)
        this.messages = rawMessages.filter((message) => this.shouldDisplayMessage(message))
      } catch (error) {
        this.error = error instanceof Error ? error.message : '加载消息失败'
      } finally {
        this.loading = false
      }
    },

    async sendMessage(content: string) {
      const text = content.trim()
      if (!text) {
        return
      }

      const authStore = useAuthStore()
      this.error = null
      this.sending = true

      let streamingAssistant: AgentMessage | null = null
      let streamingAssistantIndex = -1
      let streamingAssistantTempId: number | null = null
      let currentConversationId = this.activeConversationId

      const replacePlaceholder = (incoming: AgentMessage): boolean => {
        if (
          streamingAssistant &&
          streamingAssistantIndex >= 0 &&
          streamingAssistantTempId !== null &&
          this.messages[streamingAssistantIndex]?.id === streamingAssistantTempId &&
          incoming.role === 'assistant'
        ) {
          this.messages.splice(streamingAssistantIndex, 1, incoming)
          streamingAssistant = null
          streamingAssistantIndex = -1
          streamingAssistantTempId = null
          return true
        }
        return false
      }

      const handleDelta = (delta: string) => {
        if (!delta) {
          return
        }
        const convId = currentConversationId ?? this.activeConversationId ?? 0
        const timestamp = new Date().toISOString()
        if (!streamingAssistant) {
          streamingAssistantTempId = -Date.now()
          streamingAssistant = {
            id: streamingAssistantTempId,
            conversation_id: convId,
            role: 'assistant',
            content: delta,
            created_at: timestamp,
          } as AgentMessage
          streamingAssistantIndex = this.messages.length
          this.messages.push(streamingAssistant)
        } else {
          streamingAssistant = {
            ...streamingAssistant,
            conversation_id: convId,
            content: streamingAssistant.content + delta,
          }
          if (streamingAssistantIndex >= 0) {
            this.messages.splice(streamingAssistantIndex, 1, streamingAssistant)
          } else {
            streamingAssistantIndex = this.messages.length
            this.messages.push(streamingAssistant)
          }
        }
        if (convId) {
          this.ensureConversationSummary(convId, streamingAssistant.content)
        }
      }

      try {
        await streamAgentMessage(
          text,
          currentConversationId,
          {
            onConversation: (conversationId) => {
              currentConversationId = conversationId
              this.activeConversationId = conversationId
              if (streamingAssistant) {
                streamingAssistant = {
                  ...streamingAssistant,
                  conversation_id: conversationId,
                }
                if (streamingAssistantIndex >= 0) {
                  this.messages.splice(streamingAssistantIndex, 1, streamingAssistant)
                }
              }
              this.ensureConversationSummary(conversationId, text)
            },
            onMessage: (message) => {
              if (
                currentConversationId !== null &&
                message.conversation_id !== currentConversationId
              ) {
                return
              }
              if (message.role === 'tool') {
                this.captureToolCompletion(currentConversationId, message)
              } else if (message.role === 'assistant' && message.tool_call_id) {
                this.captureAssistantToolCall(currentConversationId, message)
              }
              if (!this.shouldDisplayMessage(message)) {
                return
              }
              const replaced = replacePlaceholder(message)
              if (!replaced) {
                this.upsertMessage(message)
              }
              if (message.role !== 'tool') {
                this.ensureConversationSummary(message.conversation_id, message.content)
              }
            },
            onDelta: handleDelta,
            onStatus: (statusPayload) => {
              this.handleStatusPayload(currentConversationId, statusPayload)
            },
            onDone: () => {
              if (streamingAssistant && streamingAssistantIndex >= 0) {
                this.messages.splice(streamingAssistantIndex, 1)
              }
              streamingAssistant = null
              streamingAssistantIndex = -1
              streamingAssistantTempId = null
            },
            onError: (err) => {
              this.error = err.message
            },
          },
          authStore.accessToken ?? null
        )
      } catch (error) {
        if (streamingAssistant && streamingAssistantIndex >= 0) {
          this.messages.splice(streamingAssistantIndex, 1)
        }
        const message = error instanceof Error ? error.message : '发送消息失败'
        this.error = message
        throw error
      } finally {
        this.sending = false
        streamingAssistant = null
        streamingAssistantIndex = -1
        streamingAssistantTempId = null
      }
    },

    async deleteConversation(conversationId: number) {
      try {
        await deleteAgentConversation(conversationId)
        this.conversations = this.conversations.filter((item) => item.id !== conversationId)
        delete this.toolActivities[conversationId]
        if (this.activeConversationId === conversationId) {
          this.startNewConversation()
        }
        await this.refreshConversations()
        if (this.activeConversationId === null && this.conversations.length > 0) {
          const first = this.conversations[0]
          if (first) {
            await this.loadMessages(first.id)
          }
        }
      } catch (error) {
        const message = error instanceof Error ? error.message : '删除会话失败'
        this.error = message
        throw error
      }
    },

    upsertMessage(message: AgentMessage) {
      if (!this.shouldDisplayMessage(message)) {
        return
      }
      if (this.activeConversationId !== null && message.conversation_id !== this.activeConversationId) {
        return
      }
      const idx = this.messages.findIndex((item) => item.id === message.id)
      if (idx >= 0) {
        this.messages[idx] = message
      } else {
        this.messages.push(message)
      }
    },

    ensureConversationSummary(conversationId: number, preview?: string) {
      const now = new Date().toISOString()
      const previewText = preview ? preview.slice(0, 60) : undefined
      const idx = this.conversations.findIndex((item) => item.id === conversationId)
      if (idx >= 0) {
        const existing = this.conversations[idx]
        if (!existing) return
        existing.updated_at = now
        if (previewText) {
          existing.last_message_preview = previewText
        }
        if (idx > 0) {
          this.conversations.splice(idx, 1)
          this.conversations.unshift(existing)
        }
        return
      }
      this.conversations.unshift({
        id: conversationId,
        title: (preview ?? '新对话').slice(0, 30) || '新对话',
        summary: null,
        created_at: now,
        updated_at: now,
        last_message_preview: previewText ?? null,
      })
    },

    shouldDisplayMessage(message: AgentMessage): boolean {
      if (message.role === 'tool') {
        return false
      }
      // Display assistant tool-call placeholders inline in the chat timeline.
      // Tool-role messages remain hidden; their outputs are surfaced via toolActivities.
      return true
    },

    rebuildToolActivities(conversationId: number, rawMessages: AgentMessage[]) {
      const snapshot: Record<string, ToolActivityEntry> = {}
      const ensureSnapshotEntry = (toolCallId: string): ToolActivityEntry => {
        if (!snapshot[toolCallId]) {
          snapshot[toolCallId] = this.createToolActivityEntry(conversationId, toolCallId)
        }
        return snapshot[toolCallId]
      }
      for (const message of rawMessages) {
        if (!message.tool_call_id) {
          continue
        }
        const entry = ensureSnapshotEntry(message.tool_call_id)
        entry.toolName = message.tool_name ?? entry.toolName
        entry.toolArgs = message.tool_args ?? entry.toolArgs
        entry.updatedAt = message.created_at
        if (message.role === 'assistant') {
          entry.status = 'running'
          entry.label = `${entry.toolName || '工具'} 调用中`
          if (!entry.startedAt) {
            entry.startedAt = message.created_at
          }
        }
        if (message.role === 'tool') {
          entry.status = 'completed'
          entry.label = `${entry.toolName || '工具'} 完成`
          if (!entry.startedAt) {
            entry.startedAt = message.created_at
          }
          entry.toolOutputPreview = entry.toolOutputPreview ?? this.stringifyToolPreview(message.tool_output ?? message.content)
        }
      }
      this.toolActivities[conversationId] = snapshot
    },

    createToolActivityEntry(conversationId: number, toolCallId: string): ToolActivityEntry {
      const now = new Date().toISOString()
      return {
        toolCallId,
        conversationId,
        toolName: null,
        label: '工具调用中',
        status: 'pending',
        toolArgs: null,
        toolOutputPreview: null,
        message: null,
        startedAt: now,
        updatedAt: now,
      }
    },

    ensureToolActivityEntry(
      conversationId: number | null,
      toolCallId: string | null | undefined
    ): ToolActivityEntry | null {
      if (!conversationId || !toolCallId) {
        return null
      }
      if (!this.toolActivities[conversationId]) {
        this.toolActivities[conversationId] = {}
      }
      if (!this.toolActivities[conversationId][toolCallId]) {
        this.toolActivities[conversationId][toolCallId] = this.createToolActivityEntry(
          conversationId,
          toolCallId
        )
      }
      return this.toolActivities[conversationId][toolCallId]
    },

    captureAssistantToolCall(conversationId: number | null, message: AgentMessage) {
      if (message.role !== 'assistant') {
        return
      }
      const entry = this.ensureToolActivityEntry(
        conversationId ?? message.conversation_id,
        message.tool_call_id
      )
      if (!entry) {
        return
      }
      entry.toolName = message.tool_name ?? entry.toolName
      entry.toolArgs = message.tool_args ?? entry.toolArgs
      entry.status = 'running'
      entry.label = `${entry.toolName || '工具'} 调用中`
      entry.updatedAt = message.created_at
      if (!entry.startedAt) {
        entry.startedAt = message.created_at
      }
    },

    captureToolCompletion(conversationId: number | null, message: AgentMessage) {
      if (message.role !== 'tool') {
        return
      }
      const entry = this.ensureToolActivityEntry(
        conversationId ?? message.conversation_id,
        message.tool_call_id
      )
      if (!entry) {
        return
      }
      entry.toolName = message.tool_name ?? entry.toolName
      entry.toolArgs = message.tool_args ?? entry.toolArgs
      if (entry.status !== 'failed') {
        entry.status = 'completed'
        entry.label = `${entry.toolName || '工具'} 完成`
      }
      entry.toolOutputPreview = this.stringifyToolPreview(message.tool_output ?? message.content)
      entry.updatedAt = message.created_at
      if (!entry.startedAt) {
        entry.startedAt = message.created_at
      }
    },

    handleStatusPayload(conversationId: number | null, payload: AgentStreamStatus) {
      const targetConversationId = payload.conversation_id ?? conversationId ?? this.activeConversationId
      const entry = this.ensureToolActivityEntry(targetConversationId, payload.tool_call_id)
      if (!entry) {
        return
      }
      if (payload.tool_name) {
        entry.toolName = payload.tool_name
      }
      if (payload.tool_args) {
        entry.toolArgs = payload.tool_args
      }
      if (payload.label) {
        entry.label = payload.label
      }
      entry.status = this.mapStatus(payload.status)
      entry.updatedAt = new Date().toISOString()
      if (payload.tool_output_preview) {
        entry.toolOutputPreview = payload.tool_output_preview
      }
      if (payload.message) {
        entry.message = payload.message
      }
    },

    mapStatus(status?: string | null): ToolActivityStatus {
      switch (status) {
        case 'tool_call_completed':
          return 'completed'
        case 'tool_call_failed':
          return 'failed'
        case 'tool_call_started':
          return 'running'
        default:
          return 'pending'
      }
    },

    stringifyToolPreview(payload: unknown): string | null {
      if (payload === null || payload === undefined) {
        return null
      }
      if (typeof payload === 'string') {
        const text = payload.trim()
        return text ? text.slice(0, 160) : null
      }
      try {
        const text = JSON.stringify(payload)
        return text ? text.slice(0, 160) : null
      } catch {
        return null
      }
    },

    getToolActivities(conversationId: number | null): ToolActivityEntry[] {
      if (!conversationId) {
        return []
      }
      const map = this.toolActivities[conversationId]
      if (!map) {
        return []
      }
      return Object.values(map).sort((a, b) => a.startedAt.localeCompare(b.startedAt))
    },
  },
})
