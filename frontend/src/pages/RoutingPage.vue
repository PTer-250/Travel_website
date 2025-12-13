<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import ErrorAlert from '../components/ui/ErrorAlert.vue'
import LoadingIndicator from '../components/ui/LoadingIndicator.vue'
import RouteMap from '../components/map/RouteMap.vue'
import AIChatPanel from '../components/chat/AIChatPanel.vue'
import KeywordSearchSelect from '../components/ui/KeywordSearchSelect.vue'
import {
  fetchRoutePlan,
  fetchMultiRoutePlan,
  fetchRegionMapData,
  searchRegionNodes,
  searchRegions,
  type RoutePlanQuery,
} from '../services/api'
import type {
  MapFeatureCollection,
  RegionNodeSummary,
  RegionSearchResult,
  RegionType,
  RoutePlanResponse,
  TransportMode,
  WeightStrategy,
} from '../types/api'
import {
  SAMPLE_ROUTING_COMBINATIONS,
  TRANSPORT_MODE_LABELS,
} from '../constants/demoOptions'
import {
  usePreferencesStore,
  createRoutingDefaults,
} from '../stores/preferences'
import { useApiRequest } from '../composables/useApiRequest'

interface RouteFormState {
  regionId: number
  startNodeId: number
  endNodeId: number
  strategy: WeightStrategy
  transportModes: TransportMode[]
}

type Option<TPayload> = {
  id: number | string
  label: string
  description?: string
  payload?: TPayload
}

type RegionOption = Option<RegionSearchResult>
type NodeOption = Option<RegionNodeSummary>

const regionTypeLabels: Record<RegionType, string> = {
  scenic: '景区',
  campus: '校园',
}

const toRegionOption = (item: RegionSearchResult): RegionOption => {
  const meta = [item.city ?? undefined, item.type ? regionTypeLabels[item.type] : undefined]
    .filter(Boolean)
    .join(' · ')
  return {
    id: item.id,
    label: item.name,
    description: item.description ?? (meta || undefined),
    payload: item,
  }
}

const toNodeOption = (item: RegionNodeSummary): NodeOption => {
  const description =
    item.description ??
    (item.code ? `编号 ${item.code}` : undefined) ??
    (Number.isFinite(item.latitude) && Number.isFinite(item.longitude)
      ? `(${item.latitude?.toFixed(4)}, ${item.longitude?.toFixed(4)})`
      : undefined)

  return {
    id: item.id,
    label: item.name ?? `节点 ${item.id}`,
    description: description ?? undefined,
    payload: item,
  }
}

const routeStrategyOptions: { label: string; value: WeightStrategy }[] = [
  { label: '⚡ 耗时最短', value: 'time' },
  { label: '📏 距离最短', value: 'distance' },
]

const transportModeOptions = computed(() =>
  Object.entries(TRANSPORT_MODE_LABELS).map(([value, label]) => ({
    value: value as TransportMode,
    label,
  }))
)

const preferencesStore = usePreferencesStore()
const { routing } = storeToRefs(preferencesStore)

const routeForm = reactive<RouteFormState>({ ...createRoutingDefaults(), transportModes: [] })

// 高级选项显示状态
const showAdvanced = ref(false)

const selectedRegion = ref<RegionOption | null>(null)
const selectedStartNode = ref<NodeOption | null>(null)
const selectedEndNode = ref<NodeOption | null>(null)
const waypoints = ref<NodeOption[]>([])

// 搜索函数
const searchRegionOptions = async (keyword: string): Promise<RegionOption[]> => {
  const trimmed = keyword.trim()
  if (!trimmed) return []
  try {
    const items = await searchRegions({ keyword: trimmed, limit: 12 })
    return items.map(toRegionOption)
  } catch (error) {
    console.warn('Failed to search regions:', error)
    return []
  }
}

const createNodeSearchProvider = (getRegionId: () => number) =>
  async (keyword: string): Promise<NodeOption[]> => {
    const trimmed = keyword.trim()
    const regionId = getRegionId()
    if (!trimmed || !regionId) return []
    try {
      const items = await searchRegionNodes({ regionId, keyword: trimmed, limit: 15 })
      return items.map(toNodeOption)
    } catch (error) {
      console.warn('Failed to search nodes:', error)
      return []
    }
  }

const searchStartNodeOptions = createNodeSearchProvider(() => routeForm.regionId)
const searchEndNodeOptions = createNodeSearchProvider(() => routeForm.regionId)

// 选择处理
const handleRegionSelect = (option: any) => {
  const payload = option.payload as RegionSearchResult | undefined
  if (!payload) return
  selectedRegion.value = {
    id: option.id,
    label: option.label,
    description: option.description,
    payload,
  }
  const regionId = payload.id
  if (routeForm.regionId !== regionId) {
    routeForm.regionId = regionId
    selectedStartNode.value = null
    selectedEndNode.value = null
    waypoints.value = []
    routeForm.startNodeId = 0
    routeForm.endNodeId = 0
  }
}

const handleRegionClear = () => {
  selectedRegion.value = null
  routeForm.regionId = 0
  routeForm.startNodeId = 0
  routeForm.endNodeId = 0
  selectedStartNode.value = null
  selectedEndNode.value = null
  waypoints.value = []
}

const handleStartNodeSelect = (option: any) => {
  const payload = option.payload as RegionNodeSummary | undefined
  if (!payload) return
  selectedStartNode.value = {
    id: option.id,
    label: option.label,
    description: option.description,
    payload,
  }
  routeForm.startNodeId = payload.id
}

const handleStartNodeClear = () => {
  selectedStartNode.value = null
  routeForm.startNodeId = 0
}

const handleEndNodeSelect = (option: any) => {
  const payload = option.payload as RegionNodeSummary | undefined
  if (!payload) return
  selectedEndNode.value = {
    id: option.id,
    label: option.label,
    description: option.description,
    payload,
  }
  routeForm.endNodeId = payload.id
}

const handleEndNodeClear = () => {
  selectedEndNode.value = null
  routeForm.endNodeId = 0
}

// 状态管理
const hydrateRouteForm = (prefs = routing.value) => {
  routeForm.regionId = prefs.regionId
  routeForm.startNodeId = prefs.startNodeId
  routeForm.endNodeId = prefs.endNodeId
  routeForm.strategy = prefs.strategy
  routeForm.transportModes = [...prefs.transportModes]
}

watch(routing, (value) => {
  hydrateRouteForm(value)
}, { immediate: true })

// API 请求
const {
  data: routeData,
  error: routeError,
  loading: routeLoading,
  execute: executeRoute,
  reset: resetRouteRequest,
} = useApiRequest(fetchRoutePlan)

const plan = computed<RoutePlanResponse | null>(() => routeData.value ?? null)
const allowedModes = computed(() => plan.value?.allowed_transport_modes ?? [])

// 地图数据
const mapTile = ref<MapFeatureCollection | null>(null)
const mapRegionId = ref<number | null>(null)
const mapLoading = ref(false)
const mapError = ref<string | null>(null)

const ensureMapData = async (regionId: number | null | undefined) => {
  if (!regionId || mapRegionId.value === regionId) return
  mapLoading.value = true
  mapError.value = null
  try {
    mapTile.value = await fetchRegionMapData(regionId)
    mapRegionId.value = regionId
  } catch (error) {
    mapTile.value = null
    mapRegionId.value = null
    mapError.value = error instanceof Error ? error.message : '地图数据加载失败'
  } finally {
    mapLoading.value = false
  }
}

watch(plan, (value) => {
  if (value) {
    void ensureMapData(value.region_id)
  }
})

// 提交路线规划
const submitRoute = async () => {
  if (!routeForm.regionId) return
  const hasWaypoints = waypoints.value.length > 0
  const hasStartEnd = !!routeForm.startNodeId && !!routeForm.endNodeId
  try {
    let result: RoutePlanResponse
    if (hasWaypoints) {
      const wpIds = waypoints.value
        .map((w) => w.payload?.id)
        .filter((id): id is number => typeof id === 'number')
      const params = {
        regionId: routeForm.regionId,
        waypointNodeIds: wpIds,
        startNodeId: routeForm.startNodeId || undefined,
        endNodeId: routeForm.endNodeId || undefined,
        strategy: routeForm.strategy,
        transportModes: routeForm.transportModes,
      }
      result = await fetchMultiRoutePlan(params)
      // 写入到当前计划数据
      // 直接更新响应数据以驱动界面刷新
      ;(routeData as any).value = result
    } else if (hasStartEnd) {
      const payload: RoutePlanQuery = {
        regionId: routeForm.regionId,
        startNodeId: routeForm.startNodeId,
        endNodeId: routeForm.endNodeId,
        strategy: routeForm.strategy,
        transportModes: routeForm.transportModes,
      }
      result = await executeRoute(payload)
      preferencesStore.updateRouting({
        regionId: payload.regionId,
        startNodeId: payload.startNodeId,
        endNodeId: payload.endNodeId,
        strategy: payload.strategy,
        transportModes: [...(payload.transportModes ?? [])],
      })
    } else {
      return
    }
    await ensureMapData(result.region_id)
  } catch {
    // 错误由 useApiRequest 处理
  }
}

// 辅助功能
const swapRouteNodes = () => {
  const { startNodeId, endNodeId } = routeForm
  routeForm.startNodeId = endNodeId
  routeForm.endNodeId = startNodeId
  const temp = selectedStartNode.value
  selectedStartNode.value = selectedEndNode.value
  selectedEndNode.value = temp
}

// 多点路线：增删改处理
const addWaypoint = () => {
  waypoints.value.push({ id: Date.now(), label: '', description: '', payload: undefined })
}

const removeWaypoint = (index: number) => {
  waypoints.value.splice(index, 1)
}

const handleWaypointSelect = (index: number, option: any) => {
  const payload = option.payload as RegionNodeSummary | undefined
  if (!payload) return
  waypoints.value[index] = {
    id: option.id,
    label: option.label,
    description: option.description,
    payload,
  }
}

const handleWaypointClear = (index: number) => {
  waypoints.value[index] = { id: Date.now(), label: '', description: '', payload: undefined }
}

const moveWaypointUp = (index: number) => {
  if (index <= 0) return
  const tmp = waypoints.value[index - 1]
  waypoints.value[index - 1] = waypoints.value[index]
  waypoints.value[index] = tmp
}

const moveWaypointDown = (index: number) => {
  if (index >= waypoints.value.length - 1) return
  const tmp = waypoints.value[index + 1]
  waypoints.value[index + 1] = waypoints.value[index]
  waypoints.value[index] = tmp
}

// 拖拽排序
const dragState = ref<{ from: number | null }>({ from: null })
const dragHoverIndex = ref<number | null>(null)
const onWaypointDragStart = (index: number, e: DragEvent) => {
  dragState.value.from = index
  e.dataTransfer?.setData('text/plain', String(index))
  e.dataTransfer?.setDragImage(new Image(), 0, 0)
}
const onWaypointDragEnter = (index: number) => {
  dragHoverIndex.value = index
}
const onWaypointDragLeave = (index: number) => {
  if (dragHoverIndex.value === index) dragHoverIndex.value = null
}
const onWaypointDrop = (index: number, e: DragEvent) => {
  const fromStr = e.dataTransfer?.getData('text/plain')
  const from = dragState.value.from ?? (fromStr ? parseInt(fromStr) : null)
  dragState.value.from = null
  dragHoverIndex.value = null
  if (from === null || from === index) return
  const item = waypoints.value[from]
  waypoints.value.splice(from, 1)
  waypoints.value.splice(index, 0, item)
}

// 当途经点顺序或内容变化时，自动重新规划（加防抖）
let waypointPlanTimer: number | null = null
watch(
  waypoints,
  () => {
    if (waypointPlanTimer) {
      clearTimeout(waypointPlanTimer)
      waypointPlanTimer = null
    }
    // 仅在存在有效途经点时触发
    const hasValidWaypoints = waypoints.value.some((w) => typeof w.payload?.id === 'number')
    if (!hasValidWaypoints || !routeForm.regionId) return
    waypointPlanTimer = window.setTimeout(() => {
      void submitRoute()
    }, 300)
  },
  { deep: true }
)

// 起点/终点/策略/交通方式变化时自动重算（300ms 防抖）
let routeAutoTimer: number | null = null
watch(
  () => [routeForm.startNodeId, routeForm.endNodeId, routeForm.strategy, routeForm.transportModes.slice()],
  () => {
    if (routeAutoTimer) {
      clearTimeout(routeAutoTimer)
      routeAutoTimer = null
    }
    if (!routeForm.regionId) return
    const hasWaypoints = waypoints.value.some((w) => typeof w.payload?.id === 'number')
    const hasStartEnd = !!routeForm.startNodeId && !!routeForm.endNodeId
    if (!hasWaypoints && !hasStartEnd) return
    routeAutoTimer = window.setTimeout(() => {
      void submitRoute()
    }, 300)
  },
  { deep: true }
)

const resetRouteForm = () => {
  const defaults = createRoutingDefaults()
  hydrateRouteForm(defaults)
  preferencesStore.updateRouting(defaults)
  resetRouteRequest()
  selectedRegion.value = null
  selectedStartNode.value = null
  selectedEndNode.value = null
  waypoints.value = []
}

const applySample = (index: number) => {
  const sample = SAMPLE_ROUTING_COMBINATIONS[index]
  if (!sample) return
  routeForm.regionId = sample.regionId
  routeForm.startNodeId = sample.startNodeId
  routeForm.endNodeId = sample.endNodeId
  selectedRegion.value = null
  selectedStartNode.value = null
  selectedEndNode.value = null
  waypoints.value = []
}
</script>

<template>
  <div class="h-[calc(100vh-8rem)] flex gap-4">
    <!-- 主要地图区域 -->
    <div class="flex-1 flex flex-col space-y-4">
      <!-- 一行式搜索和规划区域 -->
      <div class="bg-white rounded-xl shadow-lg border border-slate-200 p-4">
        <div class="flex items-center gap-3 overflow-x-auto">
          <!-- 景区搜索 -->
          <div class="flex-shrink-0 w-48">
            <KeywordSearchSelect
              v-model="selectedRegion"
              :search="searchRegionOptions"
              placeholder="搜索景区..."
              @select="handleRegionSelect"
              @clear="handleRegionClear"
            />
          </div>

          <!-- 起点 -->
          <div class="flex-shrink-0 w-32">
            <KeywordSearchSelect
              v-model="selectedStartNode"
              :search="searchStartNodeOptions"
              placeholder="起点"
              :disabled="!routeForm.regionId"
              @select="handleStartNodeSelect"
              @clear="handleStartNodeClear"
            />
          </div>

          <!-- 交换按钮 -->
          <div class="flex-shrink-0">
            <button
              type="button"
              @click="swapRouteNodes"
              :disabled="!routeForm.startNodeId || !routeForm.endNodeId"
              class="flex items-center gap-1 rounded-lg border-2 border-slate-300 bg-white px-2 py-2 text-xs font-medium text-slate-600 transition hover:border-emerald-500 hover:text-emerald-600 disabled:opacity-50"
            >
              🔄
            </button>
          </div>

          <!-- 终点 -->
          <div class="flex-shrink-0 w-32">
            <KeywordSearchSelect
              v-model="selectedEndNode"
              :search="searchEndNodeOptions"
              placeholder="终点"
              :disabled="!routeForm.regionId"
              @select="handleEndNodeSelect"
              @clear="handleEndNodeClear"
            />
          </div>

          <!-- 生成路线按钮 -->
          <div class="flex-shrink-0">
            <button
              type="button"
              @click="submitRoute"
              :disabled="routeLoading || !routeForm.regionId || (!routeForm.startNodeId && !routeForm.endNodeId && waypoints.length === 0)"
              class="flex items-center gap-2 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 px-4 py-2.5 text-white font-semibold shadow-lg transition hover:shadow-xl hover:from-emerald-600 hover:to-teal-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {{ routeLoading ? '🔄 规划中…' : '🗺️ 生成路线' }}
            </button>
          </div>

          <!-- 高级选项切换 -->
          <div class="flex-shrink-0">
            <button
              type="button"
              @click="showAdvanced = !showAdvanced"
              class="flex items-center gap-2 rounded-lg border-2 border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-600 transition hover:border-blue-500 hover:text-blue-600"
            >
              <svg class="h-4 w-4 transition-transform duration-200" :class="showAdvanced ? 'rotate-180' : ''" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
              </svg>
              高级
            </button>
          </div>
        </div>

        <!-- 高级选项区域 -->
        <div v-if="showAdvanced" class="mt-4 space-y-4 border-t border-slate-200 pt-4">
          <!-- 策略和交通方式 -->
          <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <div>
              <label class="block text-xs font-medium text-slate-700 mb-2">🎯 优化策略</label>
              <select v-model="routeForm.strategy" class="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20">
                <option v-for="option in routeStrategyOptions" :key="option.value" :value="option.value">
                  {{ option.label }}
                </option>
              </select>
            </div>

            <div class="lg:col-span-2">
              <label class="block text-xs font-medium text-slate-700 mb-2">🚗 交通方式</label>
              <div class="flex flex-wrap gap-1">
                <label
                  v-for="option in transportModeOptions"
                  :key="option.value"
                  class="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-slate-50 px-2 py-1.5 text-xs font-medium text-slate-700 transition hover:border-emerald-500 hover:bg-emerald-50"
                >
                  <input v-model="routeForm.transportModes" type="checkbox" :value="option.value" class="h-3 w-3 rounded border-slate-300 text-emerald-600" />
                  {{ option.label }}
                </label>
              </div>
            </div>
          </div>

          <!-- 多点路线 -->
          <div class="rounded-lg bg-slate-50 p-3 space-y-3">
            <div class="flex items-center justify-between">
              <span class="text-xs font-semibold text-slate-600">➕ 多点路线</span>
              <button
                type="button"
                class="rounded-md border border-slate-300 bg-white px-2 py-1 text-xs text-slate-700 hover:border-emerald-500 hover:text-emerald-600"
                :disabled="!routeForm.regionId"
                @click="addWaypoint"
              >+ 添加地点</button>
            </div>
            <div class="space-y-2">
              <div
                v-for="(wp, idx) in waypoints"
                :key="idx"
                class="flex items-center gap-2"
                :class="{ 'ring-2 ring-emerald-400 rounded-md bg-emerald-50': dragHoverIndex === idx, 'opacity-70': dragState.from === idx }"
                draggable="true"
                @dragstart="onWaypointDragStart(idx, $event)"
                @dragover.prevent
                @dragenter.prevent="onWaypointDragEnter(idx)"
                @dragleave.prevent="onWaypointDragLeave(idx)"
                @drop="onWaypointDrop(idx, $event)"
              >
                <div class="w-6 text-xs font-semibold text-slate-600 text-center">{{ idx + 1 }}</div>
                <div class="flex-1">
                  <KeywordSearchSelect
                    v-model="waypoints[idx]"
                    :search="searchStartNodeOptions"
                    placeholder="选择途经点"
                    :disabled="!routeForm.regionId"
                    @select="(opt) => handleWaypointSelect(idx, opt)"
                    @clear="() => handleWaypointClear(idx)"
                  />
                </div>
                <button
                  type="button"
                  class="rounded-md border border-slate-300 bg-white px-2 py-1 text-xs text-slate-700 hover:border-rose-500 hover:text-rose-600"
                  @click="removeWaypoint(idx)"
                >移除</button>
                <div class="flex items-center gap-1">
                  <button
                    type="button"
                    class="rounded-md border border-slate-300 bg-white px-2 py-1 text-xs text-slate-700 hover:border-slate-500"
                    :disabled="idx === 0"
                    @click="moveWaypointUp(idx)"
                  >↑</button>
                  <button
                    type="button"
                    class="rounded-md border border-slate-300 bg-white px-2 py-1 text-xs text-slate-700 hover:border-slate-500"
                    :disabled="idx === waypoints.length - 1"
                    @click="moveWaypointDown(idx)"
                  >↓</button>
                </div>
              </div>
            </div>
          </div>

          <!-- 快速示例 -->
          <div class="rounded-lg bg-slate-50 p-3">
            <span class="text-xs font-semibold text-slate-600">⚡ 快速示例</span>
            <div class="mt-2 flex flex-wrap gap-1">
              <button
                v-for="(sample, index) in SAMPLE_ROUTING_COMBINATIONS"
                :key="sample.label"
                type="button"
                class="rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-xs font-medium text-slate-600 shadow-sm transition hover:border-emerald-500 hover:text-emerald-600"
                @click="applySample(index)"
              >
                {{ sample.label }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- 地图显示区域 -->
      <div class="flex-1 bg-white rounded-xl shadow-lg border border-slate-200 min-h-96">
        <div class="h-full relative">
          <ErrorAlert v-if="mapError" :message="mapError" />
          <RouteMap
            :plan="plan"
            :tile="mapTile"
            :loading="mapLoading || routeLoading"
            :waypoint-node-ids="waypoints.map(w => w.payload?.id).filter(id => typeof id === 'number')"
            :waypoint-order="waypoints.map((_, i) => i + 1)"
          />
        </div>
      </div>

      <!-- 路线详情 -->
      <div class="bg-white rounded-xl shadow-lg border border-slate-200 p-4">
        <template v-if="routeError">
          <ErrorAlert :message="routeError.message" />
        </template>
        <template v-else-if="routeLoading">
          <LoadingIndicator label="正在计算最优路线，请稍候…" />
        </template>
        <template v-else-if="plan">
          <div class="grid gap-4 sm:grid-cols-3">
            <div class="rounded-xl bg-gradient-to-br from-blue-50 to-blue-100 p-4 text-center">
              <p class="mb-1 text-xs font-semibold text-blue-600">📏 距离</p>
              <p class="text-lg font-bold text-blue-900">
                {{ plan.total_distance.toFixed(1) }}km
              </p>
            </div>
            <div class="rounded-xl bg-gradient-to-br from-emerald-50 to-emerald-100 p-4 text-center">
              <p class="mb-1 text-xs font-semibold text-emerald-600">⏱️ 耗时</p>
              <p class="text-lg font-bold text-emerald-900">
                {{ Math.round(plan.total_time) }}min
              </p>
            </div>
            <div class="rounded-xl bg-gradient-to-br from-purple-50 to-purple-100 p-4 text-center">
              <p class="mb-1 text-xs font-semibold text-purple-600">🏛️ 区域</p>
              <p class="text-sm font-bold text-purple-900 truncate">
                {{ selectedRegion?.label ?? `区域 ${plan.region_id}` }}
              </p>
            </div>
          </div>
        </template>
        <template v-else>
          <div class="text-center py-8">
            <div class="text-4xl mb-2">🗺️</div>
            <p class="text-sm text-slate-600">搜索景点，设置起终点，让AI为你规划最佳路线</p>
          </div>
        </template>
      </div>
    </div>

    <!-- 右侧智能体聊天面板 - 缩窄宽度 -->
    <div class="w-80 min-w-[280px] max-w-[320px]">
      <AIChatPanel 
        :current-region="selectedRegion?.label"
        :context-data="{
          region: selectedRegion?.payload,
          startNode: selectedStartNode?.payload,
          endNode: selectedEndNode?.payload,
          routePlan: plan
        }"
      />
    </div>
  </div>
</template>
