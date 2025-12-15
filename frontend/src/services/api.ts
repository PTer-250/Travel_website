import apiClient from './apiClient'
import type {
  FacilityCategory,
  FacilityRouteResponse,
  MapFeatureCollection,
  RecommendationSort,
  RegionNodeSearchResponse,
  RegionNodeSummary,
  RegionRecommendationResponse,
  RegionSearchResponse,
  RegionSearchResult,
  RegionType,
  RoutePlanResponse,
  TransportMode,
  WeightStrategy,
} from '../types/api'

export interface RecommendationQuery {
  limit?: number
  sortBy?: RecommendationSort
  interests?: string[]
  interestsOnly?: boolean
  search?: string
  regionType?: RegionType | ''
}

export const fetchRegionRecommendations = async (
  params: RecommendationQuery = {}
): Promise<RegionRecommendationResponse> => {
  const queryParams = {
    limit: params.limit,
    sort_by: params.sortBy,
    interests: params.interests && params.interests.length > 0 ? params.interests : undefined,
    interests_only: params.interestsOnly,
    q: params.search || undefined,
    region_type: params.regionType || undefined,
  }

  const { data } = await apiClient.get<RegionRecommendationResponse>('/recommendations/regions', {
    params: queryParams,
  })

  return data
}

export interface RegionSearchQuery {
  keyword: string
  limit?: number
}

export const searchRegions = async (
  params: RegionSearchQuery
): Promise<RegionSearchResult[]> => {
  const queryParams = {
    q: params.keyword,
    limit: params.limit ?? 10,
  }

  const { data } = await apiClient.get<RegionSearchResponse>('/regions/search', {
    params: queryParams,
  })

  return data.items
}

export const fetchRegionDetail = async (regionId: number): Promise<RegionSearchResult> => {
  const { data } = await apiClient.get<RegionSearchResult>(`/regions/${regionId}`)
  return data
}

export interface RegionNodeSearchQuery {
  regionId: number
  keyword: string
  limit?: number
}

export const searchRegionNodes = async (
  params: RegionNodeSearchQuery
): Promise<RegionNodeSummary[]> => {
  const { regionId, keyword, limit } = params
  const { data } = await apiClient.get<RegionNodeSearchResponse>(
    `/regions/${regionId}/nodes/search`,
    {
      params: {
        q: keyword,
        limit: limit ?? 10,
      },
    }
  )

  return data.items
}

export const fetchRegionNodeDetail = async (
  regionId: number,
  nodeId: number
): Promise<RegionNodeSummary> => {
  const { data } = await apiClient.get<RegionNodeSummary>(
    `/regions/${regionId}/nodes/${nodeId}`
  )
  return data
}

export interface RoutePlanQuery {
  regionId: number
  startNodeId: number
  endNodeId: number
  strategy: WeightStrategy
  transportModes?: TransportMode[]
}

export const fetchRoutePlan = async (params: RoutePlanQuery): Promise<RoutePlanResponse> => {
  const queryParams = {
    region_id: params.regionId,
    start_node_id: params.startNodeId,
    end_node_id: params.endNodeId,
    strategy: params.strategy,
    transport_modes: params.transportModes && params.transportModes.length > 0 ? params.transportModes : undefined,
  }

  const { data } = await apiClient.get<RoutePlanResponse>('/routing/routes', {
    params: queryParams,
  })

  return data
}

export interface MultiRoutePlanQuery {
  regionId: number
  waypointNodeIds: number[]
  startNodeId?: number | null
  endNodeId?: number | null
  strategy: WeightStrategy
  transportModes?: TransportMode[]
}

export const fetchMultiRoutePlan = async (
  params: MultiRoutePlanQuery
): Promise<RoutePlanResponse> => {
  const body = {
    region_id: params.regionId,
    waypoint_node_ids: params.waypointNodeIds,
    start_node_id: params.startNodeId ?? null,
    end_node_id: params.endNodeId ?? null,
    strategy: params.strategy,
    transport_modes:
      params.transportModes && params.transportModes.length > 0
        ? params.transportModes
        : null,
  }

  const { data } = await apiClient.post<RoutePlanResponse>('/routing/multi-route', body)
  return data
}

export interface FacilityQuery {
  regionId: number
  originNodeId: number
  radiusMeters?: number | null
  limit?: number
  strategy: WeightStrategy
  categories?: FacilityCategory[]
  transportModes?: TransportMode[]
}

export const fetchNearbyFacilities = async (
  params: FacilityQuery
): Promise<FacilityRouteResponse> => {
  const queryParams = {
    region_id: params.regionId,
    origin_node_id: params.originNodeId,
    radius_meters: params.radiusMeters ?? undefined,
    limit: params.limit,
    strategy: params.strategy,
    category:
      params.categories && params.categories.length > 0
        ? params.categories
        : undefined,
    transport_modes:
      params.transportModes && params.transportModes.length > 0
        ? params.transportModes
        : undefined,
  }

  const { data } = await apiClient.get<FacilityRouteResponse>('/facilities/nearby', {
    params: queryParams,
  })

  return data
}

export const fetchRegionMapData = async (
  regionId: number,
  includeRoads: boolean = false
): Promise<MapFeatureCollection> => {
  const { data } = await apiClient.get<MapFeatureCollection>(`/map-data/${regionId}`, {
    params: {
      include_roads: includeRoads,
    },
  })
  return data
}

// ===== Diary API Functions =====

import type {
  DiarySortBy,
  DiaryListResponse,
  DiaryRecommendationParams,
  DiaryRecommendationResponse,
  DiaryCreateRequest,
  DiaryCreateResponse,
  DiaryUpdateRequest,
  DiaryDetail,
  DiaryRatingRequest,
  DiaryRatingResponse,
  DiaryRatingListResponse,
  AnimationGenerateRequest,
  DiaryAnimation,
  DiaryMediaUpload,
} from '../types/diary'
import type {
  AgentChatResponse,
  AgentConversation,
  AgentMessage,
  AgentStreamStatus,
} from '../types/agent'

/**
 * Get personalized diary recommendations
 */
export const fetchDiaryRecommendations = async (
  params: DiaryRecommendationParams = {}
): Promise<DiaryRecommendationResponse> => {
  const queryParams = {
    limit: params.limit ?? 10,
    sort_by: params.sort_by ?? 'hybrid',
    interests: params.interests && params.interests.length > 0 ? params.interests : undefined,
    region_id: params.region_id ?? undefined,
  }

  const { data } = await apiClient.get<DiaryRecommendationResponse>(
    '/diaries/recommendations',
    { params: queryParams }
  )

  return data
}

/**
 * Search diaries using full-text search
 */
export const searchDiaries = async (
  query: string,
  params: {
    limit?: number
    sort_by?: DiarySortBy
    interests?: string[]
    region_id?: number
  } = {}
): Promise<DiaryListResponse> => {
  const queryParams = {
    q: query,
    limit: params.limit ?? 20,
    sort_by: params.sort_by ?? 'hybrid',
    interests: params.interests && params.interests.length > 0 ? params.interests : undefined,
    region_id: params.region_id ?? undefined,
  }

  const { data } = await apiClient.get<DiaryListResponse>('/diaries/search', {
    params: queryParams,
  })

  return data
}

/**
 * Get diary detail by ID
 */
export const fetchDiaryDetail = async (diaryId: number): Promise<DiaryDetail> => {
  const { data } = await apiClient.get<DiaryDetail>(`/diaries/${diaryId}`)
  return data
}

/**
 * Create a new diary
 */
export const createDiary = async (
  request: DiaryCreateRequest,
  mediaUploads: DiaryMediaUpload[] = []
): Promise<DiaryCreateResponse> => {
  const formData = new FormData()
  formData.append('title', request.title)
  formData.append('content', request.content)
  formData.append('region_id', request.region_id.toString())
  formData.append('status_value', (request.status ?? 'published') as string)

  const tags = request.tags ?? []
  formData.append('tags', JSON.stringify(tags))

  const manifest = mediaUploads.map((item) => ({
    placeholder: item.placeholder,
    media_type: item.media_type,
    filename: item.filename,
    content_type: item.content_type,
  }))

  if (manifest.length > 0) {
    formData.append('media_manifest', JSON.stringify(manifest))
  }

  if (request.content_blocks && request.content_blocks.length > 0) {
    formData.append('content_blocks', JSON.stringify(request.content_blocks))
  }

  for (const media of mediaUploads) {
    formData.append('media_files', media.file, media.filename)
  }

  const { data } = await apiClient.post<DiaryCreateResponse>('/diaries', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })

  return data
}

/**
 * Update an existing diary
 */
export const updateDiary = async (
  diaryId: number,
  request: DiaryUpdateRequest
): Promise<DiaryDetail> => {
  const { data } = await apiClient.put<DiaryDetail>(`/diaries/${diaryId}`, request)
  return data
}

/**
 * Delete a diary
 */
export const deleteDiary = async (diaryId: number): Promise<void> => {
  await apiClient.delete(`/diaries/${diaryId}`)
}

/**
 * Record a diary view
 */
export const recordDiaryView = async (diaryId: number): Promise<void> => {
  await apiClient.post(`/diaries/${diaryId}/view`)
}

/**
 * Rate a diary
 */
export const rateDiary = async (
  diaryId: number,
  request: DiaryRatingRequest
): Promise<DiaryRatingResponse> => {
  const { data } = await apiClient.post<DiaryRatingResponse>(
    `/diaries/${diaryId}/rate`,
    request
  )
  return data
}

/**
 * Fetch diary ratings with pagination
 */
export const fetchDiaryRatings = async (
  diaryId: number,
  params: { page?: number; page_size?: number } = {}
): Promise<DiaryRatingListResponse> => {
  const query = {
    page: params.page ?? 1,
    page_size: params.page_size ?? 10,
  }

  const { data } = await apiClient.get<DiaryRatingListResponse>(
    `/diaries/${diaryId}/ratings`,
    { params: query }
  )

  return data
}

/**
 * Generate animation for a diary using AIGC
 */
export const generateDiaryAnimation = async (
  diaryId: number,
  request: AnimationGenerateRequest = {}
): Promise<DiaryAnimation> => {
  const { data } = await apiClient.post<DiaryAnimation>(
    `/diaries/${diaryId}/generate-animation`,
    request
  )
  return data
}

/**
 * Get all animations for a diary
 */
export const fetchDiaryAnimations = async (diaryId: number): Promise<DiaryAnimation[]> => {
  const { data } = await apiClient.get<DiaryAnimation[]>(`/diaries/${diaryId}/animations`)
  return data
}

/**
 * Get user's diaries
 */
export const fetchUserDiaries = async (
  userId: string,
  params: { page?: number; page_size?: number; status?: string } = {}
): Promise<DiaryListResponse> => {
  const queryParams = {
    page: params.page ?? 1,
    page_size: params.page_size ?? 10,
    status: params.status ?? undefined,
  }

  const { data } = await apiClient.get<DiaryListResponse>(`/diaries/users/${userId}/diaries`, {
    params: queryParams,
  })

  return data
}

// ===== Agent Chat API =====

export interface AgentStreamHandlers {
  onConversation?(conversationId: number): void
  onMessage?(message: AgentMessage): void
  onDelta?(delta: string): void
  onStatus?(payload: AgentStreamStatus): void
  onDone?(): void
  onError?(error: Error): void
}

const parseSseEvent = (rawEvent: string): { event?: string; data?: string } => {
  const lines = rawEvent.split(/\r?\n/)
  let eventName: string | undefined
  const dataLines: string[] = []

  for (const line of lines) {
    if (line.startsWith('event:')) {
      eventName = line.slice(6).trim()
    } else if (line.startsWith('data:')) {
      let value = line.slice(5)
      if (value.startsWith(' ')) {
        value = value.slice(1)
      }
      if (value.endsWith('\r')) {
        value = value.slice(0, -1)
      }
      dataLines.push(value)
    }
  }

  return {
    event: eventName,
    data: dataLines.join('\n'),
  }
}

export const fetchAgentConversations = async (): Promise<AgentConversation[]> => {
  const { data } = await apiClient.get<{ items: AgentConversation[] }>('/agent/conversations')
  return data.items
}

export const fetchAgentMessages = async (
  conversationId: number
): Promise<AgentMessage[]> => {
  const { data } = await apiClient.get<{ items: AgentMessage[] }>(
    `/agent/conversations/${conversationId}/messages`
  )
  return data.items
}

export const deleteAgentConversation = async (conversationId: number): Promise<void> => {
  await apiClient.delete(`/agent/conversations/${conversationId}`)
}

export const sendAgentMessage = async (
  content: string,
  conversationId?: number | null
): Promise<AgentChatResponse> => {
  const payload = {
    content,
    conversation_id: conversationId ?? undefined,
  }
  const { data } = await apiClient.post<AgentChatResponse>('/agent/chat', payload)
  return data
}

export const streamAgentMessage = async (
  content: string,
  conversationId: number | null | undefined,
  handlers: AgentStreamHandlers,
  accessToken?: string | null
): Promise<void> => {
  const payload = {
    content,
    conversation_id: conversationId ?? undefined,
  }
  const controller = new AbortController()
  const baseURL = apiClient.defaults.baseURL ?? ''
  const url = `${baseURL.replace(/\/$/, '')}/agent/chat/stream`
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    Accept: 'text/event-stream',
  }
  if (accessToken) {
    headers.Authorization = `Bearer ${accessToken}`
  }

  const dispatchPayload = (rawEvent: string): boolean => {
    const { data } = parseSseEvent(rawEvent)
    if (!data) {
      return true
    }
    let parsed: any
    try {
      parsed = JSON.parse(data)
    } catch (error) {
      console.warn('Failed to parse SSE payload', error, data)
      return true
    }

    switch (parsed.type) {
      case 'conversation':
        handlers.onConversation?.(parsed.conversation_id)
        return true
      case 'message':
        handlers.onMessage?.(parsed.message as AgentMessage)
        return true
      case 'delta':
        handlers.onDelta?.(parsed.delta ?? '')
        return true
      case 'status':
        handlers.onStatus?.(parsed as AgentStreamStatus)
        return true
      case 'done':
        handlers.onDone?.()
        return false
      case 'error': {
        const err = new Error(parsed.message ?? 'AI 对话失败')
        handlers.onError?.(err)
        throw err
      }
      default:
        return true
    }
  }

  const flushBuffer = (bufferRef: { current: string }): boolean => {
    while (true) {
      const boundary = bufferRef.current.indexOf('\n\n')
      if (boundary === -1) {
        return true
      }
      const rawEvent = bufferRef.current.slice(0, boundary)
      bufferRef.current = bufferRef.current.slice(boundary + 2)
      if (!rawEvent.trim()) {
        continue
      }
      const shouldContinue = dispatchPayload(rawEvent)
      if (!shouldContinue) {
        return false
      }
    }
  }

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers,
      body: JSON.stringify(payload),
      signal: controller.signal,
      credentials: 'include',
    })

    if (!response.ok) {
      const errorText = await response.text().catch(() => '')
      throw new Error(errorText || '无法建立流式对话连接')
    }

    if (!response.body) {
      throw new Error('当前浏览器不支持流式响应')
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder('utf-8')
    const bufferRef = { current: '' }
    let continueStreaming = true

    while (continueStreaming) {
      const { value, done } = await reader.read()
      if (done) {
        break
      }
      bufferRef.current += decoder.decode(value, { stream: true })
      continueStreaming = flushBuffer(bufferRef)
    }

    if (continueStreaming) {
      bufferRef.current += decoder.decode()
      continueStreaming = flushBuffer(bufferRef)
      if (continueStreaming) {
        handlers.onDone?.()
      }
    }
  } catch (error) {
    if (error instanceof Error) {
      handlers.onError?.(error)
    }
    throw error
  } finally {
    controller.abort()
  }
}
