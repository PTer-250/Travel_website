<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import LoadingIndicator from '../components/ui/LoadingIndicator.vue'
import ErrorAlert from '../components/ui/ErrorAlert.vue'
import EmptyState from '../components/ui/EmptyState.vue'
import { useApiRequest } from '../composables/useApiRequest'
import { fetchDiaryDetail, rateDiary, fetchDiaryRatings, recordDiaryView } from '../services/api'
import type { DiaryRatingRequest, DiaryRatingListResponse } from '../types/diary'

const route = useRoute()
const router = useRouter()

// Get diary ID from route
const diaryId = ref<number>(parseInt(route.params.id as string))

// API request state
const {
  data: diary,
  error,
  loading,
  execute: loadDiary,
} = useApiRequest(fetchDiaryDetail)

// Rating state
const userRating = ref<number>(0)
const ratingComment = ref('')
const isSubmittingRating = ref(false)
const ratingData = ref<DiaryRatingListResponse | null>(null)
const ratingsPage = ref(1)
const ratingsPageSize = 5
const isLoadingRatings = ref(false)

const ratingItems = computed(() => ratingData.value?.items ?? [])
const averageScore = computed(() => ratingData.value?.average_score ?? 0)
const ratingDistribution = computed(() => {
  return [5, 4, 3, 2, 1].map((score) => {
    const count = ratingData.value?.score_distribution?.[score] ?? 0
    const total = ratingData.value?.total ?? 0
    const percentage = total > 0 ? Math.round((count / total) * 100) : 0
    return {
      score,
      count,
      percentage,
    }
  })
})
const ratingsTotal = computed(() => ratingData.value?.total ?? 0)
const commentsCount = computed(() => ratingData.value?.comments_count ?? 0)
const totalRatingPages = computed(() =>
  ratingData.value ? Math.max(1, Math.ceil(ratingData.value.total / ratingsPageSize)) : 1
)
const hasRatings = computed(() => ratingItems.value.length > 0)

// Load diary on mount
onMounted(async () => {
  if (diaryId.value) {
    try {
      await recordDiaryView(diaryId.value)
    } catch (error) {
      console.warn('Failed to record diary view:', error)
    }
    await loadDiary(diaryId.value)
    await loadRatings()
  }
})

const loadRatings = async (page: number = 1) => {
  if (!diaryId.value) return

  try {
    isLoadingRatings.value = true
    const data = await fetchDiaryRatings(diaryId.value, {
      page,
      page_size: ratingsPageSize,
    })

    ratingData.value = data
    ratingsPage.value = data.page

    if (data.current_user_rating) {
      userRating.value = data.current_user_rating.score
      ratingComment.value = data.current_user_rating.comment ?? ''
    } else {
      userRating.value = 0
      ratingComment.value = ''
    }
  } catch (error) {
    console.error('Failed to load ratings:', error)
  } finally {
    isLoadingRatings.value = false
  }
}

const goToRatingsPage = async (page: number) => {
  const totalPages = totalRatingPages.value
  const targetPage = Math.min(Math.max(page, 1), totalPages)
  if (targetPage === ratingsPage.value) return
  await loadRatings(targetPage)
}

// Handle rating submission
const submitRating = async () => {
  if (!diary.value || isSubmittingRating.value) return

  try {
    isSubmittingRating.value = true

    const ratingRequest: DiaryRatingRequest = {
      score: userRating.value,
      comment: ratingComment.value.trim() || undefined,
    }

    await rateDiary(diary.value.id, ratingRequest)

    // Refresh diary data to get updated ratings
    await loadDiary(diaryId.value)
    await loadRatings(1)
    ratingsPage.value = 1

    const currentRating = ratingData.value?.current_user_rating
    ratingComment.value = currentRating?.comment ?? ''

  } catch (error) {
    console.error('Failed to submit rating:', error)
  } finally {
    isSubmittingRating.value = false
  }
}

// 生成路线
const generateRoute = () => {
  router.push({
    name: 'routing',
    query: { 
      from_diary: diaryId.value,
      region: diary.value?.region.id 
    }
  })
}

// 返回上一页
const goBack = () => {
  router.go(-1)
}

// Format date
const formatDate = (dateStr: string): string => {
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
}

const formatDateTime = (dateStr: string): string => {
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

// Format rating stars
const formatRating = (rating: number): string => {
  return '⭐'.repeat(Math.floor(rating)) + (rating % 1 >= 0.5 ? '⭐' : '')
}

const renderStars = (score: number): string => {
  const filled = '★'.repeat(score)
  const empty = '☆'.repeat(Math.max(0, 5 - score))
  return `${filled}${empty}`
}

// 将纯文本 + 媒体占位符渲染为 HTML，或对来自后端的 HTML 进行轻度清洗
const renderedContent = computed(() => {
  const raw = diary.value?.content ?? ''
  if (!raw) return ''

  const containsHtml = /<(img|video|figure)[\s>]/i.test(raw)

  // 情况一：后端已返回 HTML，做最小清洗（去除文件名等无关信息）
  if (containsHtml) {
    try {
      const parser = new DOMParser()
      const doc = parser.parseFromString(raw, 'text/html')
      doc.querySelectorAll('figcaption').forEach((el) => el.remove())
      doc.querySelectorAll('[data-filename]').forEach((el) => el.removeAttribute('data-filename'))
      return doc.body.innerHTML
    } catch {
      return raw.replace(/<figcaption[\s\S]*?<\/figcaption>/gi, '')
    }
  }

  // 情况二：内容为纯文本 + {{media:placeholder}} 占位符，需要在原位插入媒体
  const items = (diary.value as any)?.media_items as Array<{
    placeholder: string
    url: string
    media_type: 'image' | 'video'
  }> | undefined
  const map = new Map<string, { url: string; type: 'image' | 'video' }>()
  if (items && Array.isArray(items)) {
    for (const it of items) {
      if (it?.placeholder && it?.url) {
        map.set(it.placeholder, { url: it.url, type: (it.media_type as any) || 'image' })
      }
    }
  }

  // 简单的 HTML 转义
  const escapeHtml = (s: string) =>
    s
      .replace(/&/g, '&')
      .replace(/</g, '<')
      .replace(/>/g, '>')
      .replace(/"/g, '"')
      .replace(/'/g, '"')

  // 将文本段落转换为 <p>，保留换行
  const textToHtml = (text: string) => {
    const paragraphs = text.replace(/\r/g, '').split(/\n{2,}/)
    return paragraphs
      .map((p) => `<p>${escapeHtml(p).replace(/\n/g, '<br/>')}</p>`) // 单换行 -> <br/>
      .join('')
  }

  const tokens: string[] = []
  const regex = /\{\{media:([a-zA-Z0-9_-]+)\}\}/g
  let lastIndex = 0
  let m: RegExpExecArray | null
  while ((m = regex.exec(raw)) !== null) {
    const start = m.index
    if (start > lastIndex) {
      tokens.push(textToHtml(raw.slice(lastIndex, start)))
    }
  const ph = m[1] as string
    const media = map.get(ph)
    if (media) {
      if (media.type === 'video') {
        tokens.push(
          `<figure class="editor-media-block" data-media-type="video" data-placeholder="${ph}">` +
            `<video src="${media.url}" controls preload="metadata"></video>` +
          `</figure>`
        )
      } else {
        tokens.push(
          `<figure class="editor-media-block" data-media-type="image" data-placeholder="${ph}">` +
            `<img src="${media.url}" alt=""/>` +
          `</figure>`
        )
      }
    } else {
      // 未找到媒体，保留原文本以便排查
      tokens.push(`<p>${escapeHtml(m[0])}</p>`) 
    }
    lastIndex = regex.lastIndex
  }
  if (lastIndex < raw.length) {
    tokens.push(textToHtml(raw.slice(lastIndex)))
  }

  return tokens.join('')
})
</script>

<template>
  <div class="min-h-screen bg-gradient-to-br from-slate-50 to-pink-50">
    <LoadingIndicator v-if="loading" message="加载日记详情..." />
    <ErrorAlert v-else-if="error" :message="error.message" />
    <EmptyState
      v-else-if="!diary"
      icon="📝"
      title="日记不存在"
      message="找不到这篇日记，可能已被删除或不存在。"
    />

    <div v-else class="max-w-7xl mx-auto px-4 py-6">
      <!-- 头部导航 -->
      <div class="flex items-center justify-between mb-6">
        <button 
          @click="goBack"
          class="flex items-center gap-2 px-4 py-2 rounded-lg text-slate-600 hover:bg-white hover:text-slate-800 transition-colors"
        >
          <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
          </svg>
          返回
        </button>
        
        <div class="flex items-center gap-3">
          <!-- 生成路线按钮 -->
          <button
            @click="generateRoute"
            class="flex items-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 text-white font-semibold shadow-lg hover:shadow-xl transition-all"
          >
            <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
            </svg>
            生成路线
          </button>
          
          <!-- 点赞按钮 -->
          <button class="p-3 rounded-full bg-white hover:bg-pink-50 text-slate-600 hover:text-pink-500 transition-colors shadow-sm">
            <svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
            </svg>
          </button>
          
          <!-- 收藏按钮 -->
          <button class="p-3 rounded-full bg-white hover:bg-blue-50 text-slate-600 hover:text-blue-500 transition-colors shadow-sm">
            <svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
            </svg>
          </button>
          
          <!-- 分享按钮 -->
          <button class="p-3 rounded-full bg-white hover:bg-green-50 text-slate-600 hover:text-green-500 transition-colors shadow-sm">
            <svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.367 2.684 3 3 0 00-5.367-2.684z" />
            </svg>
          </button>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <!-- 主内容区域 -->
        <div class="lg:col-span-2 space-y-6">
          <!-- 日记头部信息 -->
          <div class="bg-white rounded-3xl shadow-xl border border-slate-200 overflow-hidden">
            <!-- 封面图片 -->
            <div v-if="diary.cover_image" class="aspect-[16/9] w-full overflow-hidden">
              <img
                :src="diary.cover_image"
                :alt="diary.title"
                class="h-full w-full object-cover"
              />
            </div>
            
            <!-- 内容头部 -->
            <div class="p-8">
              <div class="flex items-start justify-between mb-6">
                <div class="flex-1">
                  <h1 class="text-3xl font-bold text-slate-900 mb-3 leading-tight">{{ diary.title }}</h1>
                  <div class="flex items-center gap-4 text-sm text-slate-600">
                    <div class="flex items-center gap-1">
                      <span>📍</span>
                      <span>{{ diary.region.name }}</span>
                    </div>
                    <div class="flex items-center gap-1">
                      <span>👁️</span>
                      <span>{{ diary.popularity }}</span>
                    </div>
                    <div class="flex items-center gap-1">
                      <span>{{ formatRating(diary.rating) }}</span>
                      <span>{{ diary.rating.toFixed(1) }} ({{ diary.ratings_count }}人评价)</span>
                    </div>
                    <div class="flex items-center gap-1">
                      <span>📅</span>
                      <span>{{ formatDate(diary.created_at) }}</span>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 作者信息 -->
              <div class="flex items-center gap-4 p-4 bg-gradient-to-r from-pink-50 to-red-50 rounded-2xl mb-6">
                <div class="flex h-12 w-12 items-center justify-center rounded-full bg-gradient-to-br from-pink-400 to-red-500 text-white text-lg font-bold">
                  {{ diary.author.username.charAt(0).toUpperCase() }}
                </div>
                <div>
                  <div class="font-semibold text-slate-800">{{ diary.author.username }}</div>
                  <div class="text-sm text-slate-600">旅游达人</div>
                </div>
                <div class="ml-auto">
                  <button class="px-4 py-2 bg-gradient-to-r from-pink-500 to-red-500 text-white rounded-full text-sm font-medium hover:shadow-lg transition-all">
                    关注
                  </button>
                </div>
              </div>

              <!-- 标签 -->
              <div v-if="diary.tags && diary.tags.length > 0" class="mb-6">
                <div class="flex flex-wrap gap-2">
                  <span
                    v-for="tag in diary.tags"
                    :key="tag"
                    class="inline-flex items-center rounded-full bg-gradient-to-r from-pink-100 to-red-100 px-4 py-2 text-sm font-medium text-pink-700 border border-pink-200"
                  >
                    #{{ tag }}
                  </span>
                </div>
              </div>
            </div>
          </div>

          <!-- 日记内容 -->
          <div class="bg-white rounded-3xl shadow-xl border border-slate-200 p-8">
            <div class="prose prose-slate prose-lg max-w-none">
              <div
                class="diary-content text-slate-700 leading-relaxed"
                v-html="renderedContent"
              ></div>
            </div>
          </div>
        </div>

        <!-- 右侧评价栏 -->
        <div class="space-y-6">
          <!-- 评价总览 -->
          <div class="bg-white rounded-3xl shadow-xl border border-slate-200 p-6">
            <h3 class="text-xl font-bold text-slate-800 mb-6 flex items-center gap-2">
              <span>💬</span>
              旅友评价
            </h3>
            
            <!-- 平均分 -->
            <div class="text-center mb-6">
              <div class="text-5xl font-bold text-slate-800 mb-2">
                {{ averageScore.toFixed(1) }}
              </div>
              <div class="flex justify-center mb-2">
                <div class="text-2xl text-yellow-400">
                  {{ averageScore > 0 ? formatRating(averageScore) : '暂无评分' }}
                </div>
              </div>
              <div class="text-sm text-slate-500">
                基于 {{ ratingsTotal }} 条评分 · {{ commentsCount }} 条评论
              </div>
            </div>

            <!-- 评分分布 -->
            <div class="space-y-3 mb-6">
              <div
                v-for="item in ratingDistribution"
                :key="item.score"
              >
                <div class="flex items-center justify-between text-sm text-slate-500 mb-1">
                  <span>{{ item.score }} 星</span>
                  <span>{{ item.count }}</span>
                </div>
                <div class="h-2 w-full rounded-full bg-slate-200">
                  <div
                    class="h-full rounded-full bg-gradient-to-r from-yellow-400 to-orange-400 transition-all"
                    :style="{ width: `${item.percentage}%` }"
                  ></div>
                </div>
              </div>
            </div>
          </div>

          <!-- 评价列表 -->
          <div class="bg-white rounded-3xl shadow-xl border border-slate-200 p-6">
            <LoadingIndicator v-if="isLoadingRatings" message="加载评价..." />

            <div v-else class="space-y-4">
              <template v-if="hasRatings">
                <div
                  v-for="rating in ratingItems"
                  :key="rating.id"
                  class="border-b border-slate-100 last:border-b-0 pb-4 last:pb-0"
                >
                  <div class="flex items-start gap-3">
                    <div class="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-blue-400 to-purple-500 text-white text-sm font-bold">
                      {{ rating.user.username.charAt(0).toUpperCase() }}
                    </div>
                    <div class="flex-1">
                      <div class="flex items-center justify-between mb-2">
                        <div>
                          <div class="text-sm font-semibold text-slate-700">
                            {{ rating.user.username }}
                          </div>
                          <div class="text-xs text-slate-500">
                            {{ formatDateTime(rating.created_at) }}
                          </div>
                        </div>
                        <div class="text-lg text-yellow-400">
                          {{ renderStars(rating.score) }}
                        </div>
                      </div>
                      <p v-if="rating.comment" class="text-sm text-slate-700 leading-relaxed">
                        {{ rating.comment }}
                      </p>
                    </div>
                  </div>
                </div>
              </template>
              <EmptyState
                v-else
                icon="💬"
                title="暂无评价"
                message="快来留下你的第一条评论吧。"
              />

              <!-- 分页 -->
              <div
                v-if="totalRatingPages > 1"
                class="flex items-center justify-between mt-6 pt-4 border-t border-slate-100"
              >
                <button
                  class="px-3 py-1.5 text-sm rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 disabled:opacity-50"
                  :disabled="ratingsPage === 1"
                  @click="goToRatingsPage(ratingsPage - 1)"
                >
                  上一页
                </button>
                <span class="text-sm text-slate-500">
                  {{ ratingsPage }} / {{ totalRatingPages }}
                </span>
                <button
                  class="px-3 py-1.5 text-sm rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 disabled:opacity-50"
                  :disabled="ratingsPage === totalRatingPages"
                  @click="goToRatingsPage(ratingsPage + 1)"
                >
                  下一页
                </button>
              </div>
            </div>
          </div>

          <!-- 评价输入框 -->
          <div class="bg-white rounded-3xl shadow-xl border border-slate-200 p-6 sticky bottom-6">
            <h4 class="font-semibold text-slate-800 mb-4">写下你的评价</h4>
            <div class="space-y-4">
              <textarea
                v-model="ratingComment"
                rows="3"
                placeholder="分享你的旅游体验..."
                class="w-full px-4 py-3 border border-slate-300 rounded-xl focus:border-pink-500 focus:ring-2 focus:ring-pink-500/20 outline-none transition resize-none"
              ></textarea>
              
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-1">
                  <button
                    v-for="star in 5"
                    :key="star"
                    :class="[
                      'text-2xl transition-colors',
                      star <= userRating ? 'text-yellow-400' : 'text-slate-300'
                    ]"
                    @click="userRating = star"
                  >
                    ★
                  </button>
                </div>
                <button
                  class="px-6 py-2 bg-gradient-to-r from-pink-500 to-red-500 text-white rounded-xl font-medium hover:shadow-lg transition-all disabled:opacity-50"
                  :disabled="userRating === 0 || isSubmittingRating"
                  @click="submitRating"
                >
                  {{ isSubmittingRating ? '提交中...' : '发布评价' }}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.diary-content {
  line-height: 1.8;
}

.diary-content h1,
.diary-content h2,
.diary-content h3 {
  color: #1e293b;
  margin-top: 2em;
  margin-bottom: 0.5em;
}

.diary-content p {
  margin-bottom: 1.5em;
}

.diary-content img {
  max-width: 100%;
  height: auto;
  border-radius: 1rem;
  margin: 2rem 0;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
}

.diary-content .diary-media {
  margin: 2rem 0;
  text-align: center;
}

.diary-content .diary-media img,
.diary-content .diary-media video {
  max-width: 100%;
  border-radius: 1.5rem;
  box-shadow: 0 20px 40px rgba(15, 23, 42, 0.15);
}

.diary-content .diary-media figcaption,
.diary-content figcaption {
  display: none;
}

.diary-content .editor-media-block {
  margin: 2rem 0;
  text-align: center;
}

.diary-content .editor-media-block img,
.diary-content .editor-media-block video {
  max-width: 100%;
  border-radius: 1.5rem;
  box-shadow: 0 20px 40px rgba(15, 23, 42, 0.15);
}
</style>