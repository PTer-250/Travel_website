<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'
import { useChatStore, type ToolActivityEntry, type ToolActivityStatus } from '../../stores/chat'
import type { AgentConversation, AgentMessage } from '../../types/agent'
import MarkdownIt from 'markdown-it'

const chatStore = useChatStore()
const newMessage = ref('')
const chatContainerRef = ref<HTMLElement | null>(null)
const showHistory = ref(false)

const conversations = computed(() => chatStore.conversations)
const messages = computed(() => chatStore.messages)
const activeConversationId = computed(() => chatStore.activeConversationId)
const loading = computed(() => chatStore.loading)
const sending = computed(() => chatStore.sending)

const md = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
})

const quickSuggestions = [
  '推荐热门景点',
  '规划最佳路线',
  '寻找当地美食',
  '小红书上有什么攻略',
  '推荐某个景点的路线',
]

onMounted(async () => {
  await chatStore.init()
  await nextTick(scrollToBottom)
})

const scrollToBottom = () => {
  const el = chatContainerRef.value
  if (!el) return
  el.scrollTop = el.scrollHeight
}

const renderTime = (message: AgentMessage) => {
  return new Date(message.created_at).toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
  })
}

const selectConversation = async (conversationId: number) => {
  await chatStore.loadMessages(conversationId)
  showHistory.value = false
  await nextTick(scrollToBottom)
}

const startNewConversation = () => {
  chatStore.startNewConversation()
  newMessage.value = ''
  showHistory.value = false
}

const toggleHistory = async () => {
  showHistory.value = !showHistory.value
  if (showHistory.value && !conversations.value.length) {
    await chatStore.refreshConversations()
  }
}

const sendMessage = async (content?: string) => {
  const text = (content ?? newMessage.value).trim()
  if (!text || sending.value) return
  newMessage.value = ''
  await chatStore.sendMessage(text)
  await chatStore.refreshConversations()
  await nextTick(scrollToBottom)
}

const activeConversation = computed<AgentConversation | null>(() => {
  return conversations.value.find((item) => item.id === activeConversationId.value) ?? null
})

const badgeForRole = (role: AgentMessage['role']) => {
  if (role === 'tool') return '工具'
  if (role === 'assistant') return 'AI'
  return '我'
}

const badgeForMessage = (message: AgentMessage) => {
  if (message.role === 'assistant' && message.tool_call_id) {
    return '工具'
  }
  return badgeForRole(message.role)
}

const toolActivityForMessage = (message: AgentMessage): ToolActivityEntry | null => {
  if (!message.tool_call_id) {
    return null
  }
  const conversationId = activeConversationId.value ?? message.conversation_id
  const map = chatStore.toolActivities[conversationId]
  return map?.[message.tool_call_id] ?? null
}

const renderAssistantMarkdown = (content: string) => {
  return md.render(content || '')
}

const toolStatusClass = (status: ToolActivityStatus) => {
  if (status === 'completed') return 'bg-emerald-50 text-emerald-700 border border-emerald-200'
  if (status === 'failed') return 'bg-rose-50 text-rose-700 border border-rose-200'
  if (status === 'running') return 'bg-amber-50 text-amber-800 border border-amber-200'
  return 'bg-slate-100 text-slate-600 border border-slate-200'
}

const formatToolArgs = (args?: Record<string, unknown> | null) => {
  if (!args || Object.keys(args).length === 0) {
    return '无参数'
  }
  return Object.entries(args)
    .map(([key, value]) => {
      if (typeof value === 'string') return `${key}: ${value}`
      try {
        return `${key}: ${JSON.stringify(value)}`
      } catch {
        return `${key}: ${String(value)}`
      }
    })
    .join('，')
}

const handleDeleteConversation = async (conversationId: number, event?: MouseEvent) => {
  event?.stopPropagation()
  const confirmed = window.confirm('确定删除该对话吗？')
  if (!confirmed) return
  try {
    await chatStore.deleteConversation(conversationId)
    await nextTick(scrollToBottom)
  } catch (error) {
    console.error(error)
  }
}
</script>

<template>
  <div class="flex flex-col h-full gap-3">
    <div class="relative bg-white rounded-2xl border border-slate-200 shadow-sm px-4 py-3 flex items-center justify-between">
      <div class="flex items-center gap-3">
        <button
          class="inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-slate-200 bg-slate-50 hover:bg-blue-50 text-slate-700 hover:text-blue-700 transition"
          @click="toggleHistory"
          title="历史对话"
        >
          <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 2m6-2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span class="text-sm font-medium">历史对话</span>
        </button>
        <span class="text-xs text-slate-500">点击查看历史记录</span>
      </div>
      <button
        class="px-3 py-2 text-xs rounded-lg bg-blue-500 text-white hover:bg-blue-600 transition"
        @click="startNewConversation"
      >
        新对话
      </button>

      <div
        v-if="showHistory"
        class="absolute left-4 right-4 top-14 z-10 bg-white border border-slate-200 shadow-xl rounded-xl max-h-80 overflow-y-auto"
      >
        <div
          v-for="conversation in conversations"
          :key="conversation.id"
          class="px-4 py-3 hover:bg-blue-50 cursor-pointer flex items-start gap-3"
          :class="conversation.id === activeConversationId ? 'bg-blue-50' : ''"
          @click="selectConversation(conversation.id)"
        >
          <div class="mt-1 text-slate-400">
            <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 2m6-2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div class="flex-1 min-w-0">
            <div class="flex items-center justify-between gap-2">
              <span class="font-medium text-slate-800 truncate">{{ conversation.title || '新对话' }}</span>
              <span class="text-[11px] text-slate-500">{{ new Date(conversation.updated_at).toLocaleDateString('zh-CN', { month: 'numeric', day: 'numeric' }) }}</span>
            </div>
            <p class="text-sm text-slate-500 line-clamp-2">{{ conversation.last_message_preview || '暂无内容' }}</p>
          </div>
          <button
            class="text-xs text-rose-500 hover:text-rose-600 px-2 py-1 rounded-lg"
            @click="handleDeleteConversation(conversation.id, $event)"
          >
            删除
          </button>
        </div>
        <div v-if="!conversations.length" class="px-4 py-3 text-sm text-slate-500">暂无历史对话</div>
      </div>
    </div>

    <div class="flex-1 flex flex-col h-full bg-white rounded-2xl shadow-lg border border-slate-200">
      <div class="flex items-center justify-between p-4 border-b border-slate-200 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-t-2xl">
        <div class="flex items-center gap-3">
          <div class="flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 text-white text-lg font-bold">
            AI
          </div>
          <div>
            <h3 class="font-semibold text-slate-800">智能旅游助手</h3>
            <p class="text-xs text-slate-500">
              {{ activeConversation ? '正在对话' : '新对话' }}
            </p>
          </div>
        </div>
        <div class="flex items-center gap-2 text-xs text-slate-500">
          <span v-if="loading">加载中...</span>
          <span v-else-if="sending">发送中...</span>
        </div>
      </div>

      <div ref="chatContainerRef" class="flex-1 overflow-y-auto p-4 space-y-4" id="chat-messages">
        <div v-if="!messages.length" class="text-sm text-slate-500 bg-slate-50 border border-dashed border-slate-200 rounded-xl p-4">
          开始与智能助手对话，历史会话会在这里出现。
        </div>
        <div
          v-for="message in messages"
          :key="message.id"
          class="flex"
          :class="message.role === 'user' ? 'justify-end' : 'justify-start'"
        >
          <div
            class="max-w-[80%] rounded-2xl px-4 py-3 space-y-2"
            :class="message.role === 'user'
              ? 'bg-gradient-to-r from-blue-500 to-indigo-600 text-white'
              : message.role === 'tool'
                ? 'bg-amber-50 text-amber-900 border border-amber-200'
                : (message.role === 'assistant' && message.tool_call_id)
                  ? 'bg-slate-50 text-slate-800 border border-slate-200'
                  : 'bg-slate-100 text-slate-800'"
          >
            <div class="flex items-center gap-2 text-xs opacity-80">
              <span class="inline-flex items-center px-2 py-0.5 rounded-full border border-white/40 text-[11px]"
                :class="message.role === 'tool' ? 'bg-white/70 text-amber-800 border-amber-200' : 'bg-white/30 text-white'"
              >
                {{ badgeForMessage(message) }}
              </span>
              <span :class="message.role === 'user' ? 'text-blue-100' : 'text-slate-500'">{{ renderTime(message) }}</span>
            </div>

            <template v-if="message.role === 'assistant' && message.tool_call_id">
              <div class="space-y-1">
                <div class="flex items-center justify-between gap-3">
                  <span class="font-medium text-slate-800 truncate">
                    {{ toolActivityForMessage(message)?.toolName || message.tool_name || '工具调用' }}
                  </span>
                  <span
                    class="text-[11px] px-2 py-0.5 rounded-full"
                    :class="toolStatusClass(toolActivityForMessage(message)?.status || 'pending')"
                  >
                    {{ toolActivityForMessage(message)?.label || '工具调用中' }}
                  </span>
                </div>
                <p class="text-xs text-slate-500">
                  参数：{{ formatToolArgs(toolActivityForMessage(message)?.toolArgs || message.tool_args) }}
                </p>
                <p v-if="toolActivityForMessage(message)?.toolOutputPreview" class="text-xs text-slate-600 line-clamp-2">
                  结果：{{ toolActivityForMessage(message)?.toolOutputPreview }}
                </p>
                <p v-else-if="toolActivityForMessage(message)?.message" class="text-xs text-rose-600">
                  异常：{{ toolActivityForMessage(message)?.message }}
                </p>
              </div>
            </template>
            <template v-else-if="message.role === 'assistant'">
              <div class="leading-relaxed text-sm chat-markdown" v-html="renderAssistantMarkdown(message.content)"></div>
            </template>
            <template v-else>
              <div class="whitespace-pre-wrap leading-relaxed text-sm">{{ message.content }}</div>
            </template>
          </div>
        </div>

        <div v-if="sending" class="flex justify-start">
          <div class="bg-slate-100 rounded-2xl px-4 py-3">
            <div class="flex items-center gap-2">
              <div class="flex gap-1">
                <div class="w-2 h-2 bg-slate-400 rounded-full animate-bounce"></div>
                <div class="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style="animation-delay: 0.1s"></div>
                <div class="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style="animation-delay: 0.2s"></div>
              </div>
              <span class="text-sm text-slate-500">正在思考...</span>
            </div>
          </div>
        </div>
      </div>

      <div v-if="messages.length <= 1" class="px-4 py-3 border-t border-slate-200 bg-slate-50">
        <div class="text-xs font-medium text-slate-600 mb-2">💡 快速开始</div>
        <div class="flex flex-wrap gap-2">
          <button
            v-for="suggestion in quickSuggestions"
            :key="suggestion"
            @click="sendMessage(suggestion)"
            class="px-3 py-1.5 text-xs font-medium rounded-full bg-white hover:bg-blue-50 text-slate-600 hover:text-blue-600 transition-colors border border-slate-200"
          >
            {{ suggestion }}
          </button>
        </div>
      </div>

      <div class="p-4 border-t border-slate-200 bg-white rounded-b-2xl">
        <div class="flex gap-2">
          <input
            v-model="newMessage"
            type="text"
            placeholder="输入你想咨询的问题..."
            class="flex-1 px-4 py-2 border border-slate-300 rounded-xl focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 outline-none transition"
            @keyup.enter="sendMessage()"
            :disabled="sending"
          />
          <button
            @click="sendMessage()"
            :disabled="sending || !newMessage.trim()"
            class="px-4 py-2 bg-gradient-to-r from-blue-500 to-indigo-600 text-white rounded-xl hover:from-blue-600 hover:to-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          >
            <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
#chat-messages::-webkit-scrollbar {
  width: 4px;
}

#chat-messages::-webkit-scrollbar-track {
  background: transparent;
}

#chat-messages::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 2px;
}

#chat-messages::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}
</style>

<style scoped>
.chat-markdown :deep(p) {
  margin: 0.25rem 0;
}

.chat-markdown :deep(ul),
.chat-markdown :deep(ol) {
  padding-left: 1.25rem;
  margin: 0.25rem 0;
}

.chat-markdown :deep(pre) {
  overflow-x: auto;
}

.chat-markdown :deep(a) {
  text-decoration: underline;
}
</style>