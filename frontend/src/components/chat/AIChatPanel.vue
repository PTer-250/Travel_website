<script setup lang="ts">
import { ref, computed, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'

interface ChatMessage {
  id: string
  type: 'user' | 'assistant'
  content: string
  timestamp: Date
  suggestions?: string[]
}

interface Props {
  currentRegion?: string
  currentDiaryId?: number
  contextData?: any
}

const props = defineProps<Props>()

const route = useRoute()
const router = useRouter()

// 聊天相关状态
const messages = ref<ChatMessage[]>([
  {
    id: '1',
    type: 'assistant',
    content: '你好！我是你的智能旅游助手。我可以帮你：\n\n🎯 推荐旅游目的地\n📝 参考他人日记\n🗺️ 规划游览路线\n🎪 寻找特色活动\n\n请告诉我你想去哪里玩，或者有什么具体的需求吧！',
    timestamp: new Date(),
    suggestions: [
      '推荐一个适合周末的短途旅行目的地',
      '我想去故宫，有什么游览建议吗？',
      '帮我根据这篇日记规划路线',
      '寻找美食推荐'
    ]
  }
])

const newMessage = ref('')
const isLoading = ref(false)

// 快速回复建议
const quickSuggestions = [
  '推荐热门景点',
  '规划最佳路线',
  '寻找当地美食',
  '了解交通方式',
  '查看天气情况',
  '获取门票信息'
]

// 发送消息
const sendMessage = async (content?: string) => {
  const messageContent = content || newMessage.value.trim()
  if (!messageContent) return

  // 添加用户消息
  const userMessage: ChatMessage = {
    id: Date.now().toString(),
    type: 'user',
    content: messageContent,
    timestamp: new Date()
  }
  messages.value.push(userMessage)
  newMessage.value = ''
  isLoading.value = true

  // 模拟AI回复
  await new Promise(resolve => setTimeout(resolve, 1000))
  
  const assistantMessage: ChatMessage = {
    id: (Date.now() + 1).toString(),
    type: 'assistant',
    content: generateAIResponse(messageContent),
    timestamp: new Date(),
    suggestions: generateSuggestions(messageContent)
  }
  messages.value.push(assistantMessage)
  isLoading.value = false

  // 滚动到底部
  nextTick(() => {
    const chatContainer = document.getElementById('chat-messages')
    if (chatContainer) {
      chatContainer.scrollTop = chatContainer.scrollHeight
    }
  })
}

// 生成AI回复内容
const generateAIResponse = (userMessage: string): string => {
  const lowerMessage = userMessage.toLowerCase()
  
  if (lowerMessage.includes('推荐') || lowerMessage.includes('去哪')) {
    return `根据你的需求，我为你推荐几个热门目的地：

🏔️ **黄山** - 奇松怪石，云海日出，绝美风光
🏛️ **故宫** - 千年古都，历史文化浓厚
🌸 **杭州西湖** - 诗意江南，风景如画
🏔️ **张家界** - 奇峰异石，电影取景地

你想了解哪个目的地的详细信息呢？`
  } else if (lowerMessage.includes('路线') || lowerMessage.includes('规划')) {
    return `我来帮你规划最佳游览路线！🗺️

根据当前选定的区域，我建议：

📍 **经典路线**（1-2天）：
主要景点 → 最佳观景点 → 特色体验地 → 美食街区

🚶‍♂️ **深度路线**（3-5天）：
经典景点 → 周边探索 → 文化体验 → 休闲购物

你想规划几天的行程呢？我可以根据你的时间和兴趣定制专属路线！`
  } else if (lowerMessage.includes('美食') || lowerMessage.includes('吃')) {
    return `美食推荐来啦！🍜

🥘 **特色菜系**：
- 本帮菜：红烧肉、白切鸡、糖醋排骨
- 小吃：生煎包、小笼包、锅贴
- 甜品：绿豆汤、酒酿圆子

📍 **推荐餐厅**：
- 老字号：本帮菜传承
- 网红店：创意融合菜
- 街头巷尾：地道小食

你比较喜欢什么口味呢？我可以推荐具体的餐厅地址！`
  } else {
    return `我理解你想了解"${userMessage}"。

作为你的旅游助手，我可以帮你：

🎯 **目的地推荐** - 根据季节和兴趣推荐
🗺️ **路线规划** - 定制专属行程  
📝 **日记参考** - 看看其他游客的体验
🎪 **活动推荐** - 当地特色活动
🚗 **交通指南** - 怎么去最方便
🏨 **住宿建议** - 住哪里最合适

请告诉我更多具体信息，我会给出更精准的建议！`
  }
}

// 生成快速回复建议
const generateSuggestions = (userMessage: string): string[] => {
  const lowerMessage = userMessage.toLowerCase()
  
  if (lowerMessage.includes('推荐')) {
    return ['推荐热门景点', '推荐当地美食', '推荐住宿', '推荐交通方式']
  } else if (lowerMessage.includes('路线')) {
    return ['经典1日游', '深度2-3日游', '亲子游路线', '情侣游路线']
  } else {
    return ['查看地图位置', '了解开放时间', '获取门票信息', '联系客服']
  }
}

// 跳转到搜索相关页面
const searchDestination = (destination: string) => {
  router.push({
    name: 'diaries',
    query: { search: destination }
  })
}

// 生成路线规划
const generateRoute = () => {
  if (props.currentDiaryId) {
    router.push({
      name: 'routing',
      query: { from_diary: props.currentDiaryId }
    })
  } else {
    router.push({ name: 'routing' })
  }
}

// 清空聊天记录
const clearChat = () => {
  messages.value = [
    {
      id: '1',
      type: 'assistant',
      content: '聊天记录已清空。我是你的智能旅游助手，有什么可以帮助你的吗？',
      timestamp: new Date()
    }
  ]
}
</script>

<template>
  <div class="flex flex-col h-full bg-white rounded-2xl shadow-lg border border-slate-200">
    <!-- 聊天头部 -->
    <div class="flex items-center justify-between p-4 border-b border-slate-200 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-t-2xl">
      <div class="flex items-center gap-3">
        <div class="flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 text-white text-lg font-bold">
          AI
        </div>
        <div>
          <h3 class="font-semibold text-slate-800">智能旅游助手</h3>
          <p class="text-xs text-slate-500">在线 • 随时为您服务</p>
        </div>
      </div>
      <div class="flex items-center gap-2">
        <button
          @click="generateRoute"
          class="p-2 rounded-lg hover:bg-white/50 text-slate-600 hover:text-blue-600 transition-colors"
          title="生成路线"
        >
          <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
          </svg>
        </button>
        <button
          @click="clearChat"
          class="p-2 rounded-lg hover:bg-white/50 text-slate-600 hover:text-red-500 transition-colors"
          title="清空聊天"
        >
          <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
          </svg>
        </button>
      </div>
    </div>

    <!-- 聊天消息区域 -->
    <div id="chat-messages" class="flex-1 overflow-y-auto p-4 space-y-4">
      <div
        v-for="message in messages"
        :key="message.id"
        class="flex"
        :class="message.type === 'user' ? 'justify-end' : 'justify-start'"
      >
        <div
          class="max-w-[80%] rounded-2xl px-4 py-3"
          :class="message.type === 'user'
            ? 'bg-gradient-to-r from-blue-500 to-indigo-600 text-white'
            : 'bg-slate-100 text-slate-800'"
        >
          <div class="whitespace-pre-wrap">{{ message.content }}</div>
          <div
            class="text-xs mt-2 opacity-70"
            :class="message.type === 'user' ? 'text-blue-100' : 'text-slate-500'"
          >
            {{ message.timestamp.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) }}
          </div>
          
          <!-- 建议回复 -->
          <div v-if="message.suggestions && message.type === 'assistant'" class="mt-3 flex flex-wrap gap-2">
            <button
              v-for="suggestion in message.suggestions"
              :key="suggestion"
              @click="sendMessage(suggestion)"
              class="px-3 py-1.5 text-xs font-medium rounded-full bg-white/80 hover:bg-white text-slate-700 hover:text-blue-600 transition-colors border border-slate-200"
            >
              {{ suggestion }}
            </button>
          </div>
        </div>
      </div>
      
      <!-- 加载指示器 -->
      <div v-if="isLoading" class="flex justify-start">
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

    <!-- 快速建议 -->
    <div v-if="messages.length <= 2" class="px-4 py-3 border-t border-slate-200 bg-slate-50">
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

    <!-- 输入区域 -->
    <div class="p-4 border-t border-slate-200 bg-white rounded-b-2xl">
      <div class="flex gap-2">
        <input
          v-model="newMessage"
          type="text"
          placeholder="输入你想咨询的问题..."
          class="flex-1 px-4 py-2 border border-slate-300 rounded-xl focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 outline-none transition"
          @keyup.enter="sendMessage()"
          :disabled="isLoading"
        />
        <button
          @click="sendMessage()"
          :disabled="isLoading || !newMessage.trim()"
          class="px-4 py-2 bg-gradient-to-r from-blue-500 to-indigo-600 text-white rounded-xl hover:from-blue-600 hover:to-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
        >
          <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 自定义滚动条 */
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