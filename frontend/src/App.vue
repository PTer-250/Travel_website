<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'

import { useAuthStore } from './stores/auth'

const navLinks = [
  { to: '/', label: '日记推荐' },
  { to: '/routing', label: '地图路线' },
  { to: '/facilities', label: '场所查询' },
]

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const { isAuthenticated, user } = storeToRefs(authStore)

const activePath = computed(() => route.path)
const displayName = computed(
  () => user.value?.username ?? '我的账户'
)

const showUserMenu = ref(false)

const toggleUserMenu = () => {
  showUserMenu.value = !showUserMenu.value
}

const closeUserMenu = () => {
  showUserMenu.value = false
}

const handleLogout = async () => {
  closeUserMenu()
  await authStore.logout()
  await router.push({ name: 'home' })
}

const goToProfile = async () => {
  closeUserMenu()
  await router.push({ name: 'profile' })
}

watch(
  () => route.fullPath,
  () => {
    closeUserMenu()
  }
)

void authStore.ensureProfile()
</script>

<template>
  <div class="flex min-h-screen flex-col bg-gradient-to-br from-slate-50 via-pink-50 to-blue-50 text-slate-900">
    <header class="sticky top-0 z-50 border-b border-slate-200/60 bg-white/90 shadow-sm backdrop-blur-xl">
      <div class="mx-auto flex max-w-7xl items-center justify-between px-4 py-4">
        <RouterLink to="/" class="flex items-center gap-3 text-xl font-bold text-primary transition hover:text-primary/80 group">
          <span class="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-pink-500 via-red-500 to-yellow-500 text-lg font-black text-white shadow-xl group-hover:scale-105 transition-transform">
            旅
          </span>
          <span class="hidden sm:inline bg-gradient-to-r from-pink-600 to-red-600 bg-clip-text text-transparent font-bold">
            智能旅游平台
          </span>
        </RouterLink>
        
        <div class="flex items-center gap-4">
          <nav class="hidden md:flex items-center gap-1 text-sm font-medium">
            <RouterLink
              v-for="link in navLinks"
              :key="link.to"
              :to="link.to"
              class="rounded-full px-4 py-2.5 transition-all duration-200 relative overflow-hidden"
              :class="activePath === link.to
                ? 'bg-gradient-to-r from-pink-500 to-red-500 text-white shadow-lg shadow-pink-500/30'
                : 'text-slate-600 hover:text-pink-600 hover:bg-pink-50'"
            >
              <span class="relative z-10">{{ link.label }}</span>
              <div
                v-if="activePath === link.to"
                class="absolute inset-0 bg-gradient-to-r from-pink-400 to-red-400 opacity-80"
              ></div>
            </RouterLink>
          </nav>

          <!-- 移动端菜单 -->
          <div class="md:hidden">
            <button
              class="p-2 rounded-lg text-slate-600 hover:bg-slate-100 transition-colors"
            >
              <svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
          </div>

          <div v-if="isAuthenticated" class="relative">
            <button
              class="flex items-center gap-3 rounded-full border-2 border-slate-200 bg-white/80 backdrop-blur-sm px-4 py-2.5 text-sm font-medium text-slate-700 shadow-sm transition hover:border-pink-300 hover:text-pink-600 hover:bg-white/95"
              @click="toggleUserMenu"
            >
              <span class="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-pink-400 to-red-500 text-white font-bold">
                {{ displayName.charAt(0).toUpperCase() }}
              </span>
              <span class="hidden sm:inline">{{ displayName }}</span>
              <svg
                class="h-4 w-4 text-slate-400 transition-transform duration-200"
                :class="showUserMenu ? 'rotate-180' : ''"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
              </svg>
            </button>

            <transition name="fade" mode="out-in">
              <div
                v-if="showUserMenu"
                class="absolute right-0 mt-3 w-48 rounded-2xl border border-slate-200 bg-white/95 backdrop-blur-xl p-2 text-sm shadow-2xl"
              >
                <button
                  class="w-full rounded-xl px-4 py-3 text-left text-slate-700 hover:bg-pink-50 hover:text-pink-600 transition-colors"
                  @click="goToProfile"
                >
                  <div class="flex items-center gap-3">
                    <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                    </svg>
                    个人中心
                  </div>
                </button>
                <button
                  class="w-full rounded-xl px-4 py-3 text-left text-red-500 hover:bg-red-50 transition-colors"
                  @click="handleLogout"
                >
                  <div class="flex items-center gap-3">
                    <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                    </svg>
                    退出登录
                  </div>
                </button>
              </div>
            </transition>
          </div>

          <RouterLink
            v-else
            to="/login"
            class="hidden sm:flex items-center gap-2 rounded-full bg-gradient-to-r from-pink-500 to-red-500 px-6 py-3 text-sm font-semibold text-white shadow-lg hover:shadow-xl transition-all hover:scale-105"
          >
            <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
            登录 / 注册
          </RouterLink>
        </div>
      </div>
    </header>

    <main class="flex-1 bg-gradient-to-br from-slate-50 via-pink-25 to-blue-25">
      <div class="mx-auto max-w-7xl px-4 py-6">
        <RouterView />
      </div>
    </main>

    <footer class="border-t border-slate-200/60 bg-white/80 backdrop-blur-xl py-8">
      <div class="mx-auto max-w-7xl px-4">
        <div class="flex flex-col items-center justify-between gap-6 md:flex-row">
          <div class="flex items-center gap-4">
            <div class="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-pink-500 to-red-500 text-white font-bold">
              旅
            </div>
            <div>
              <div class="font-bold text-slate-800">© {{ new Date().getFullYear() }} 智能旅游平台</div>
              <div class="text-xs text-slate-500">发现世界，分享美好</div>
            </div>
          </div>
          
          <div class="flex flex-col items-center gap-4 md:flex-row">
            <div class="flex items-center gap-3">
              <span class="rounded-full bg-gradient-to-r from-blue-100 to-purple-100 px-4 py-2 text-xs font-semibold text-blue-700 shadow-sm">
                FastAPI
              </span>
              <span class="rounded-full bg-gradient-to-r from-green-100 to-emerald-100 px-4 py-2 text-xs font-semibold text-green-700 shadow-sm">
                Vue 3
              </span>
              <span class="rounded-full bg-gradient-to-r from-pink-100 to-red-100 px-4 py-2 text-xs font-semibold text-pink-700 shadow-sm">
                Tailwind CSS
              </span>
            </div>
            <div class="text-xs text-slate-400">
              由 AI 驱动的智能旅游平台
            </div>
          </div>
        </div>
      </div>
    </footer>
  </div>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
