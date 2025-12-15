<template>
  <div
    class="group relative overflow-hidden rounded-2xl bg-white shadow-sm transition-all duration-300 hover:shadow-xl hover:-translate-y-1 cursor-pointer border border-slate-100"
    @click="handleClick"
  >
    <!-- 封面图片 -->
    <div
      v-if="coverUrl"
      class="relative aspect-[4/5] w-full overflow-hidden bg-slate-100"
    >
      <img
        :src="coverUrl"
        :alt="diary.title"
        class="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
        loading="lazy"
      />
      
      <!-- 状态徽章 -->
      <div class="absolute right-3 top-3 flex flex-col gap-2">
        <!-- 草稿状态 -->
        <div
          v-if="diary.status === 'draft'"
          class="rounded-full bg-yellow-500/90 backdrop-blur-sm px-3 py-1 text-xs font-medium text-white shadow-lg"
        >
          草稿
        </div>
        <!-- 推荐分数 -->
        <div
          v-if="recommendationScore !== undefined"
          class="rounded-full bg-gradient-to-r from-pink-500/90 to-red-500/90 backdrop-blur-sm px-3 py-1 text-xs font-bold text-white shadow-lg"
        >
          🎯 {{ recommendationScore.toFixed(1) }}
        </div>
        <!-- 压缩状态 -->
        <div
          v-if="showCompressionStatus && (diary as any).is_compressed"
          class="rounded-full bg-green-500/90 backdrop-blur-sm px-3 py-1 text-xs font-medium text-white shadow-lg"
        >
          ✓ 已压缩
        </div>
      </div>

      <!-- 动画预览 -->
      <div
        v-if="animationThumbnail"
        class="absolute bottom-3 right-3 rounded-lg bg-black/60 backdrop-blur-sm p-2"
      >
        <div class="flex items-center gap-1 text-xs text-white">
          <span>🎬</span>
          <span>动画</span>
        </div>
      </div>

      <!-- 图片下方渐变遮罩 -->
      <div class="absolute bottom-0 left-0 right-0 h-20 bg-gradient-to-t from-black/60 to-transparent"></div>
    </div>

    <!-- 内容区域 -->
    <div class="p-4">
      <!-- 标题 -->
      <h3 class="mb-3 line-clamp-2 text-lg font-semibold text-slate-800 group-hover:text-pink-600 transition-colors leading-tight">
        {{ diary.title }}
      </h3>

      <!-- 内容预览 -->
      <p v-if="contentPreview" class="mb-4 line-clamp-3 text-sm text-slate-600 leading-relaxed">
        {{ contentPreview }}
      </p>

      <!-- 作者和地点信息 -->
      <div class="mb-4 flex items-center justify-between">
        <div class="flex items-center gap-2">
          <div class="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-pink-400 to-red-500 text-white text-sm font-bold">
            {{ diary.author.username.charAt(0).toUpperCase() }}
          </div>
          <div>
            <div class="text-sm font-medium text-slate-700">{{ diary.author.username }}</div>
            <div class="text-xs text-slate-500">旅游达人</div>
          </div>
        </div>
        <div class="flex items-center gap-1 text-xs text-slate-500">
          <span>📍</span>
          <span>{{ diary.region.name || '神秘地点' }}</span>
        </div>
      </div>

      <!-- 标签 -->
      <div v-if="diary.tags && diary.tags.length > 0" class="mb-4 flex flex-wrap gap-2">
        <span
          v-for="tag in diary.tags.slice(0, 3)"
          :key="tag"
          class="rounded-full bg-gradient-to-r from-pink-100 to-red-100 px-3 py-1 text-xs font-medium text-pink-700 border border-pink-200"
        >
          #{{ tag }}
        </span>
        <span
          v-if="diary.tags.length > 3"
          class="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-500"
        >
          +{{ diary.tags.length - 3 }}
        </span>
      </div>

      <!-- 互动数据 -->
      <div class="mb-3 flex items-center justify-between text-sm">
        <div class="flex items-center gap-4">
          <!-- 观看数 -->
          <div class="flex items-center gap-1 text-slate-500">
            <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
            </svg>
            <span>{{ formatNumber(diary.popularity) }}</span>
          </div>
          <!-- 评分 -->
          <div class="flex items-center gap-1">
            <div class="flex text-yellow-400">
              <svg v-for="star in 5" :key="star" class="h-4 w-4" :fill="star <= Math.floor(diary.rating) ? 'currentColor' : 'none'" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
              </svg>
            </div>
            <span class="text-sm font-medium text-slate-700">{{ diary.rating.toFixed(1) }}</span>
            <span class="text-xs text-slate-400">({{ diary.ratings_count }})</span>
          </div>
          <!-- 评论数 -->
          <div v-if="diary.comments_count > 0" class="flex items-center gap-1 text-slate-500">
            <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
            <span>{{ diary.comments_count }}</span>
          </div>
        </div>
      </div>

      <!-- 发布时间 -->
      <div class="flex items-center justify-between">
        <div class="text-xs text-slate-400">
          {{ formatDate(diary.created_at) }}
        </div>
        <!-- 快速操作按钮 -->
        <div class="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
          <button 
            @click.stop
            class="p-2 rounded-full hover:bg-slate-100 text-slate-400 hover:text-pink-500 transition-colors"
            title="点赞"
          >
            <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
            </svg>
          </button>
          <button 
            @click.stop
            class="p-2 rounded-full hover:bg-slate-100 text-slate-400 hover:text-blue-500 transition-colors"
            title="收藏"
          >
            <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
            </svg>
          </button>
          <button 
            @click.stop
            class="p-2 rounded-full hover:bg-slate-100 text-slate-400 hover:text-green-500 transition-colors"
            title="分享"
          >
            <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.367 2.684 3 3 0 00-5.367-2.684z" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { DiaryListItem } from '../../types/diary'

interface Props {
  diary: DiaryListItem
  showCompressionStatus?: boolean
  recommendationScore?: number
  animationThumbnail?: string
}

interface Emits {
  (e: 'click', diary: DiaryListItem): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const contentPreview = computed(() => props.diary.content_preview?.trim() ?? '')

const coverUrl = computed(() => {
  const diaryAny = props.diary as any
  const direct = (props.diary.cover_image || diaryAny.coverImage || diaryAny.cover) as string | undefined
  if (direct && typeof direct === 'string' && direct.trim().length > 0) {
    return direct
  }

  const mediaUrls = diaryAny.media_urls as unknown
  if (Array.isArray(mediaUrls) && typeof mediaUrls[0] === 'string' && mediaUrls[0].trim().length > 0) {
    return mediaUrls[0]
  }

  const mediaItems = diaryAny.media_items as unknown
  if (Array.isArray(mediaItems)) {
    const firstImage = mediaItems.find(
      (it: any) => (it?.media_type === 'image' || it?.media_type === 'IMAGE') && typeof it?.url === 'string'
    )
    if (firstImage?.url) {
      return firstImage.url as string
    }
  }

  return ''
})

const handleClick = () => {
  emit('click', props.diary)
}

const formatNumber = (num: number): string => {
  if (num >= 10000) {
    return (num / 10000).toFixed(1) + 'w'
  } else if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'k'
  }
  return num.toString()
}

const formatDate = (dateStr: string): string => {
  const date = new Date(dateStr)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const days = Math.floor(diff / (1000 * 60 * 60 * 24))

  if (days === 0) {
    return '今天'
  } else if (days === 1) {
    return '昨天'
  } else if (days < 7) {
    return `${days}天前`
  } else if (days < 30) {
    return `${Math.floor(days / 7)}周前`
  } else if (days < 365) {
    return `${Math.floor(days / 30)}个月前`
  } else {
    return date.toLocaleDateString('zh-CN')
  }
}
</script>

<style scoped>
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  line-clamp: 2;
  overflow: hidden;
}

.line-clamp-3 {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  line-clamp: 3;
  overflow: hidden;
}
</style>
