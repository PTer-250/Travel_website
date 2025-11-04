<template>
  <div class="diary-filters">
    <div class="grid grid-cols-1 gap-4 md:grid-cols-12 md:items-end">
      <!-- Full-text Search -->
      <div class="md:col-span-5">
        <label class="mb-2 block text-sm font-medium text-slate-700">全文搜索</label>
        <div class="relative">
          <input
            v-model="fullTextSearch"
            type="text"
            placeholder="搜索日记内容或标题..."
            class="h-11 w-full rounded-md border border-slate-300 px-3 pl-9 text-sm placeholder-slate-400 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
            @input="handleFullTextSearchInput"
          />
          <div class="absolute inset-y-0 left-0 flex items-center pl-3">
            <svg class="h-4 w-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
        </div>
      </div>

      <!-- Sort By -->
      <div class="md:col-span-2">
        <label class="mb-2 block text-sm font-medium text-slate-700">排序方式</label>
        <select
          v-model="sortBy"
          class="h-11 w-full rounded-md border border-slate-300 px-3 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
          @change="handleSortChange"
        >
          <option value="hybrid">综合推荐</option>
          <option value="popularity">热度优先</option>
          <option value="rating">评分优先</option>
          <option value="latest">最新发布</option>
        </select>
      </div>

      <!-- Region Filter -->
      <div class="md:col-span-3">
        <label class="mb-2 block text-sm font-medium text-slate-700">旅游目的地</label>
        <input
          v-model="regionSearch"
          type="text"
          placeholder="输入目的地名称（可选）"
          class="h-11 w-full rounded-md border border-slate-300 px-3 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
          @input="handleRegionSearchInput"
        />
      </div>

      <!-- Create Diary Button (aligned with search) -->
      <div class="md:col-span-2">
        <label class="mb-2 block text-sm font-medium text-transparent select-none">占位</label>
        <button
          class="inline-flex h-11 w-full items-center justify-center rounded-md bg-primary px-4 text-sm font-medium text-white hover:bg-primary/90"
          @click="emit('create')"
        >
          ✏️ 撰写日记
        </button>
      </div>
    </div>

    <!-- Reset Button -->
    <div class="mt-4">
      <button
        v-if="hasActiveFilters"
        class="w-full rounded-md bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-200"
        @click="handleReset"
      >
        重置筛选
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { DiarySortBy } from '../../types/diary'

interface Emits {
  (e: 'update:sortBy', value: DiarySortBy): void
  (e: 'update:regionId', value: number | null): void
  (e: 'update:search', value: string): void
  (e: 'update:fullTextSearch', value: string): void
  (e: 'filtersChanged'): void
  (e: 'create'): void
}

const emit = defineEmits<Emits>()

// Local state
const fullTextSearch = ref('')
const searchQuery = ref('')
const sortBy = ref<DiarySortBy>('hybrid')
const regionSearch = ref('')

// Computed
const hasActiveFilters = computed(() => {
  return (
    fullTextSearch.value !== '' ||
    searchQuery.value !== '' ||
    regionSearch.value !== ''
  )
})

// Full-text search input handler with debounce
let fullTextTimeout: number | undefined
const handleFullTextSearchInput = () => {
  if (fullTextTimeout) clearTimeout(fullTextTimeout)
  fullTextTimeout = window.setTimeout(() => {
    emit('update:fullTextSearch', fullTextSearch.value)
    emit('filtersChanged')
  }, 300)
}

// Region search input handler
let regionTimeout: number | undefined
const handleRegionSearchInput = () => {
  if (regionTimeout) clearTimeout(regionTimeout)
  regionTimeout = window.setTimeout(() => {
    // For now, we'll just emit null since we don't have region ID
    // In a real app, you'd search for regions and get the ID
    emit('update:regionId', null)
    emit('filtersChanged')
  }, 300)
}

const handleSortChange = () => {
  emit('update:sortBy', sortBy.value)
  emit('filtersChanged')
}

const handleReset = () => {
  fullTextSearch.value = ''
  searchQuery.value = ''
  sortBy.value = 'hybrid'
  regionSearch.value = ''
  
  emit('update:fullTextSearch', '')
  emit('update:search', '')
  emit('update:sortBy', 'hybrid')
  emit('update:regionId', null)
  emit('filtersChanged')
}
</script>
