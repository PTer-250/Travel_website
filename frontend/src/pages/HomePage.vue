<script setup lang="ts">
import { onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import LoadingIndicator from '../components/ui/LoadingIndicator.vue'
import ErrorAlert from '../components/ui/ErrorAlert.vue'
import EmptyState from '../components/ui/EmptyState.vue'
import DiaryCard from '../components/diary/DiaryCard.vue'
import { useApiRequest } from '../composables/useApiRequest'
import { fetchDiaryRecommendations } from '../services/api'
import { useDiariesStore } from '../stores/diaries'
import type { DiaryListItem } from '../types/diary'

const diariesStore = useDiariesStore()
const router = useRouter()

// 筛选选项
const filters = [
  { key: 'hybrid', label: '✨ 智能推荐' },
  { key: 'popularity', label: '🔥 热门优先' },
  { key: 'rating', label: '⭐ 评分最高' },
  { key: 'latest', label: '🕒 最新发布' },
]

// 防抖搜索
let searchTimeout: number | null = null
const debouncedSearch = () => {
  if (searchTimeout) {
    clearTimeout(searchTimeout)
  }
  searchTimeout = setTimeout(() => {
    handleFiltersChanged()
  }, 300)
}

// API request state for recommendations
const {
  data: recommendationsData,
  error: recommendationsError,
  loading: recommendationsLoading,
  execute: loadRecommendations,
} = useApiRequest(fetchDiaryRecommendations)

// Computed properties for current data
const currentData = computed(() => {
  // For recommendations, create a unified interface
  const recData = recommendationsData.value
  if (recData) {
    return {
      ...recData,
      total: recData.total_candidates, // Use total_candidates as total for consistency
    }
  }
  return null
})

const error = computed(() => recommendationsError.value)
const loading = computed(() => recommendationsLoading.value)

// Unified diary items for template
const diaryItems = computed(() => {
  if (!currentData.value) return []
  return currentData.value.items.map((item: any) => {
    return {
      diary: item.diary as DiaryListItem,
      recommendationScore: item.score,
      showCompressionStatus: false,
      animationThumbnail: undefined,
    }
  })
})

// Load initial data
onMounted(async () => {
  await handleFiltersChanged()
})

// Handle filter changes
const handleFiltersChanged = async () => {
  await loadRecommendations({
    limit: 20,
    sort_by: diariesStore.filters.sortBy,
    region_id: diariesStore.filters.regionId || undefined,
  })
}

// Load more function
const loadMore = async () => {
  // 实现加载更多功能
  await handleFiltersChanged()
}

// Handle diary card click
const handleDiaryClick = (diary: DiaryListItem) => {
  void router.push({ name: 'diary-detail', params: { id: diary.id } })
}

// Handle create diary button
const handleCreateDiary = () => {
  void router.push({ name: 'diary-create' })
}
</script>

<template>
  <div class="space-y-6">
    <!-- 页面标题区域 -->
    <div class="relative overflow-hidden rounded-3xl bg-gradient-to-r from-pink-500 via-red-500 to-yellow-500 p-8 text-white">
      <div class="relative z-10">
        <h1 class="text-3xl font-bold mb-2">发现精彩旅程</h1>
        <p class="text-pink-100 text-lg">探索全球旅游日记，找到你的下一个目的地</p>
      </div>
      <!-- 背景装饰 -->
      <div class="absolute right-0 top-0 h-32 w-32 -translate-y-8 translate-x-8 rounded-full bg-white/10 blur-3xl"></div>
      <div class="absolute bottom-0 right-0 h-24 w-24 translate-y-8 translate-x-8 rounded-full bg-white/5 blur-2xl"></div>
    </div>

    <!-- 搜索和筛选栏 -->
    <div class="sticky top-20 z-40 -mx-4 bg-white/80 px-4 pb-4 pt-4 backdrop-blur-lg">
      <div class="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <!-- 搜索栏 -->
        <div class="relative flex-1 max-w-md">
          <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <svg class="h-5 w-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
          <input
            v-model="diariesStore.filters.fullTextSearch"
            type="text"
            placeholder="搜索日记、地点、标签..."
            class="block w-full pl-10 pr-4 py-3 border border-slate-200 rounded-xl bg-white/90 backdrop-blur-sm focus:border-pink-500 focus:ring-2 focus:ring-pink-500/20 transition"
            @input="debouncedSearch"
          />
        </div>

        <!-- 筛选按钮组 -->
        <div class="flex flex-wrap gap-2">
          <button
            v-for="filter in filters"
            :key="filter.key"
            @click="diariesStore.setSortBy(filter.key as any)"
            class="px-4 py-2 rounded-full text-sm font-medium transition-all"
            :class="diariesStore.filters.sortBy === filter.key
              ? 'bg-gradient-to-r from-pink-500 to-red-500 text-white shadow-lg'
              : 'bg-slate-100 text-slate-600 hover:bg-slate-200'"
          >
            {{ filter.label }}
          </button>
        </div>

        <!-- 发布日记按钮 -->
        <button
          @click="handleCreateDiary"
          class="flex items-center gap-2 rounded-full bg-gradient-to-r from-pink-500 to-red-500 px-6 py-3 text-white font-medium shadow-lg hover:shadow-xl transition-all"
        >
          <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
          </svg>
          发布日记
        </button>
      </div>
    </div>

    <!-- 统计信息 -->
    <div class="flex items-center justify-between text-sm text-slate-600 mb-4">
      <div class="flex items-center gap-4">
        <span class="font-medium">找到 {{ currentData?.total || 0 }} 篇精彩日记</span>
      </div>
      <div class="text-slate-400">
        {{ {
          hybrid: '✨ 智能推荐',
          popularity: '🔥 热门优先',
          rating: '⭐ 评分最高',
          latest: '🕒 最新发布'
        }[diariesStore.filters.sortBy] }}
      </div>
    </div>

    <!-- Loading State -->
    <LoadingIndicator v-if="loading" message="正在加载精彩内容..." />

    <!-- Error State -->
    <ErrorAlert v-else-if="error" :message="error.message" />

    <!-- Empty State -->
    <EmptyState
      v-else-if="!currentData || currentData.items.length === 0"
      icon="🌟"
      title="还没有精彩日记"
      message="成为第一个分享精彩旅程的人吧！"
    />

    <!-- Diary Grid -->
    <div v-else class="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      <DiaryCard
        v-for="item in diaryItems"
        :key="item.diary.id"
        :diary="item.diary"
        :show-compression-status="item.showCompressionStatus"
        :recommendation-score="item.recommendationScore"
        :animation-thumbnail="item.animationThumbnail"
        @click="handleDiaryClick"
      />
    </div>

    <!-- 加载更多 -->
    <div v-if="currentData && currentData.items.length > 0" class="flex justify-center pt-8">
      <button
        class="rounded-full border-2 border-pink-200 px-8 py-3 text-pink-600 font-medium hover:bg-pink-50 transition-colors"
        @click="loadMore"
        :disabled="loading"
      >
        {{ loading ? '加载中...' : '加载更多' }}
      </button>
    </div>
  </div>
</template>
