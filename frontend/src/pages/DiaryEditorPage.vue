<script setup lang="ts">
import { computed, onBeforeUnmount, reactive, ref } from 'vue'
import heic2any from 'heic2any'
import { storeToRefs } from 'pinia'
import { useRouter } from 'vue-router'
import type { Editor } from '@tiptap/core'
import { EditorContent, useEditor } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import Underline from '@tiptap/extension-underline'
import Link from '@tiptap/extension-link'
import Placeholder from '@tiptap/extension-placeholder'
import TextAlign from '@tiptap/extension-text-align'
import CharacterCount from '@tiptap/extension-character-count'

import PageSection from '../components/ui/PageSection.vue'
import KeywordSearchSelect, { type SearchOption } from '../components/ui/KeywordSearchSelect.vue'
import TagInput from '../components/ui/TagInput.vue'
import SuccessAlert from '../components/ui/SuccessAlert.vue'
import ErrorAlert from '../components/ui/ErrorAlert.vue'
import { useApiRequest } from '../composables/useApiRequest'
import { createDiary, fetchDiaryDetail, searchRegions } from '../services/api'
import DiaryMedia from '../components/editor/extensions/diaryMedia'
import { useAuthStore } from '../stores/auth'

import type {
  DiaryCreateRequest,
  DiaryCreateResponse,
  DiaryDetail,
  DiaryMediaType,
  DiaryMediaUpload,
  DiaryStatus,
  DiaryContentBlock,
} from '../types/diary'
import type { RegionSearchResult } from '../types/api'

interface EditorMediaItem {
  placeholder: string
  type: DiaryMediaType
  previewUrl: string
  upload: DiaryMediaUpload
}

const router = useRouter()
const authStore = useAuthStore()
const { isAuthenticated } = storeToRefs(authStore)

const characterLimit = 5000
const titleLimit = 40

const form = reactive({
  title: '',
  contentHtml: '',
  status: 'published' as DiaryStatus,
})

const selectedRegion = ref<SearchOption<RegionSearchResult> | null>(null)
const tags = ref<string[]>([])
const mediaUploads = ref<EditorMediaItem[]>([])
const fileInputRef = ref<HTMLInputElement | null>(null)

const tiptapEditor = useEditor({
  extensions: [
    StarterKit.configure({
      heading: { levels: [1, 2, 3] },
      bulletList: { keepMarks: true, keepAttributes: false },
      orderedList: { keepMarks: true, keepAttributes: false },
      link: false,
      underline: false,
    }),
    Underline,
    Link.configure({ openOnClick: false, autolink: true }),
    TextAlign.configure({ types: ['heading', 'paragraph'] }),
    Placeholder.configure({ placeholder: '输入正文' }),
    CharacterCount.configure({ limit: characterLimit }),
    DiaryMedia,
  ],
  content: '',
  onUpdate: ({ editor: instance }: { editor: Editor }) => {
    const html = instance.getHTML()
    form.contentHtml = html
    syncMediaUploadsWithContent(instance)
  },
})

const createdDiary = ref<DiaryCreateResponse | null>(null)
const createdDiaryDetail = ref<DiaryDetail | null>(null)
const mediaConvertError = ref<string | null>(null)
const submitted = ref(false)
const touched = reactive({
  title: false,
  region: false,
  content: false,
})

const statusOptions: Array<{ value: DiaryStatus; label: string; description: string }> = [
  { value: 'published', label: '立即发布', description: '创建后立即公开展示' },
  { value: 'draft', label: '保存草稿', description: '暂不公开，可稍后继续编辑' },
]

const {
  execute: submitDiary,
  loading: submitting,
  error: submitError,
} = useApiRequest(createDiary)


const handleRegionSearch = async (keyword: string) => {
  const results = await searchRegions({ keyword, limit: 8 })
  return results.map((region) => ({
    id: region.id,
    label: region.name,
    description: [region.city, region.type === 'scenic' ? '景区' : region.type === 'campus' ? '校园' : null]
      .filter(Boolean)
      .join(' · '),
    payload: region,
  })) as SearchOption<RegionSearchResult>[]
}

const titleLength = computed(() => form.title.trim().length)

const titleError = computed(() => {
  if (!touched.title && !submitted.value) return null
  if (titleLength.value === 0) return '请输入日记标题'
  if (titleLength.value > titleLimit) return `标题不能超过 ${titleLimit} 个字符`
  return null
})

const regionError = computed(() => {
  if (!touched.region && !submitted.value) return null
  if (!selectedRegion.value) return '请选择关联的地区'
  return null
})

const contentLength = computed(() => {
  const instance = tiptapEditor.value
  if (!instance) return 0
  return instance.storage.characterCount?.characters() ?? (instance.getText() || '').length
})

const DOM_PARSER = new DOMParser()

const releasePreviewUrl = (url: string | null | undefined) => {
  if (!url || !url.startsWith('blob:')) {
    return
  }
  URL.revokeObjectURL(url)
}

const decodeHtmlEntities = (input: string): string => {
  if (!input) return ''
  const textarea = document.createElement('textarea')
  textarea.innerHTML = input
  return textarea.value
}

const serializeContentForSubmission = (html: string): string => {
  if (!html) return ''

  let working = html

  working = working.replace(
    /<figure[^>]*data-placeholder="([^"]+)"[^>]*>[\s\S]*?<\/figure>/gi,
    (_match, placeholder) => `\n{{media:${placeholder}}}\n`
  )

  working = working
    .replace(/<br\s*\/?>(?=\s*\n?)/gi, '\n')
    .replace(/<li[^>]*>/gi, '- ')
    .replace(/<\/(p|div|section|article|h[1-6]|li)>/gi, '\n\n')

  working = working.replace(/<[^>]+>/g, '')
  working = decodeHtmlEntities(working)

  const normalized = working
    .replace(/\r/g, '')
    .replace(/[ \t]+\n/g, '\n')
    .replace(/\n{3,}/g, '\n\n')
    .split('\n')
    .map((line) => line.trimEnd())
    .join('\n')
    .trim()

  return normalized
}

const plainTextLength = computed(() => {
  if (!form.contentHtml) return 0
  const doc = DOM_PARSER.parseFromString(form.contentHtml, 'text/html')
  return (doc.body.textContent ?? '').replace(/\s+/g, ' ').trim().length
})

const contentError = computed(() => {
  if (!touched.content && !submitted.value) return null
  if (plainTextLength.value === 0) return '请输入日记正文内容'
  if (plainTextLength.value < 10) return '正文内容至少需要 10 个字符'
  return null
})

const canSubmit = computed(() => {
  return (
    isAuthenticated.value &&
    titleLength.value > 0 &&
    titleLength.value <= titleLimit &&
    !!selectedRegion.value &&
    plainTextLength.value >= 10
  )
})

function syncMediaUploadsWithContent(editor: Editor | null) {
  if (!editor) return

  const placeholders = new Set<string>()
  editor.state.doc.descendants((node) => {
    if (node.type.name === 'diaryMedia' && typeof node.attrs.placeholder === 'string') {
      placeholders.add(node.attrs.placeholder as string)
    }
  })

  mediaUploads.value = mediaUploads.value.filter((item) => {
    if (placeholders.has(item.placeholder)) {
      return true
    }
    releasePreviewUrl(item.previewUrl)
    return false
  })
}

const generatePlaceholder = (type: DiaryMediaType) =>
  `media-${type}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`

const triggerMediaUpload = () => {
  if (!isAuthenticated.value) {
    return
  }
  fileInputRef.value?.click()
}

const isHeicLike = (file: File): boolean => {
  const mime = (file.type || '').toLowerCase()
  if (mime === 'image/heic' || mime === 'image/heif' || mime === 'image/heic-sequence' || mime === 'image/heif-sequence') {
    return true
  }
  const name = (file.name || '').toLowerCase()
  return name.endsWith('.heic') || name.endsWith('.heif')
}

const convertHeicToJpeg = async (file: File): Promise<File> => {
  const blob = (await heic2any({ blob: file, toType: 'image/jpeg', quality: 0.92 })) as Blob
  const base = (file.name || 'upload').replace(/\.[^/.]+$/, '')
  return new File([blob], `${base}.jpg`, { type: 'image/jpeg', lastModified: Date.now() })
}

const handleMediaFilesSelected = async (event: Event) => {
  const input = event.target as HTMLInputElement
  const instance = tiptapEditor.value
  if (!input.files || !instance) return

  mediaConvertError.value = null

  const files = Array.from(input.files)
  for (const originalFile of files) {
    let file = originalFile
    try {
      if (isHeicLike(file)) {
        file = await convertHeicToJpeg(file)
      }
    } catch (e) {
      console.error('HEIC conversion failed', e)
      mediaConvertError.value = 'HEIC/HEIF 图片当前浏览器无法直接预览，且转换失败。请将照片导出为 JPG/PNG 后再上传。'
      // 转换失败时跳过该文件，避免插入灰块占位
      continue
    }

    const mediaType: DiaryMediaType = file.type.startsWith('video') ? 'video' : 'image'
    const placeholder = generatePlaceholder(mediaType)
    // 生成与占位符绑定的安全文件名，避免泄露用户本地文件名
    const getSafeFilename = (
      f: File,
      ph: string,
      type: DiaryMediaType
    ): string => {
      // 优先依据 MIME 推断扩展名
      const mime = (f.type || '').toLowerCase()
      const mimeExtMap: Record<string, string> = {
        'image/jpeg': 'jpg',
        'image/jpg': 'jpg',
        'image/png': 'png',
        'image/gif': 'gif',
        'image/webp': 'webp',
        'image/avif': 'avif',
        'video/mp4': 'mp4',
        'video/webm': 'webm',
        'video/ogg': 'ogg',
        'video/quicktime': 'mov',
      }
      let ext = mimeExtMap[mime]
      if (!ext) {
        // 回退：仅提取原名中的扩展名，不保留文件名主体
        const name = f.name || ''
        const dot = name.lastIndexOf('.')
        const rawExt = dot >= 0 ? name.slice(dot + 1).toLowerCase() : ''
        // 白名单中的常见扩展，否则给出缺省
        const allowed = new Set(['jpg', 'jpeg', 'png', 'gif', 'webp', 'avif', 'mp4', 'webm', 'ogg', 'mov'])
        ext = allowed.has(rawExt) ? rawExt : (type === 'video' ? 'mp4' : 'jpg')
      }
      return `${ph}.${ext}`
    }
    const safeFilename = getSafeFilename(file, placeholder, mediaType)
    const upload: DiaryMediaUpload = {
      placeholder,
      media_type: mediaType,
      // 使用安全文件名，杜绝原始文件名外泄
      filename: safeFilename,
      content_type: file.type || undefined,
      file,
    }
    const previewUrl = URL.createObjectURL(file)

    mediaUploads.value.push({ placeholder, type: mediaType, previewUrl, upload })

    instance
      .chain()
      .focus()
      .insertDiaryMedia({
        placeholder,
        type: mediaType,
        src: previewUrl,
        // 仅用于内部数据，不进行可视化渲染
        filename: upload.filename,
      })
      .run()
  }

  form.contentHtml = instance.getHTML()
  syncMediaUploadsWithContent(instance)

  input.value = ''
}

const clearMediaUploads = () => {
  mediaUploads.value.forEach((item) => releasePreviewUrl(item.previewUrl))
  mediaUploads.value = []
}

const resetForm = () => {
  form.title = ''
  form.contentHtml = ''
  form.status = 'published'
  selectedRegion.value = null
  tags.value = []
  createdDiary.value = null
  createdDiaryDetail.value = null
  submitted.value = false
  touched.title = false
  touched.region = false
  touched.content = false
  clearMediaUploads()
  tiptapEditor.value?.commands.clearContent()
}

const prepareSubmissionContent = () => {
  if (!tiptapEditor.value) {
    return { html: '', serialized: '', blocks: [] as DiaryContentBlock[] }
  }

  const html = tiptapEditor.value.getHTML()
  form.contentHtml = html
  syncMediaUploadsWithContent(tiptapEditor.value)

  const serialized = serializeContentForSubmission(html)
  // Build content blocks from serialized string to preserve exact order
  const blocks: DiaryContentBlock[] = []
  const regex = /\{\{media:([a-zA-Z0-9_.-]+)\}\}/g
  let lastIndex = 0
  let m: RegExpExecArray | null
  const pushText = (text: string) => {
    if (text.length > 0) {
      blocks.push({ type: 'text', text })
    }
  }
  while ((m = regex.exec(serialized)) !== null) {
    const start = m.index
    if (start > lastIndex) {
      pushText(serialized.slice(lastIndex, start))
    }
  const ph = (m[1] ?? '') as string
    // Find media type from mediaUploads map
    const item = mediaUploads.value.find((it) => it.placeholder === ph)
    const mediaType: DiaryMediaType = item?.type ?? 'image'
    blocks.push({ type: 'media', placeholder: ph, media_type: mediaType })
    lastIndex = regex.lastIndex
  }
  if (lastIndex < serialized.length) {
    pushText(serialized.slice(lastIndex))
  }

  return { html, serialized, blocks }
}

const handleSubmit = async () => {
  submitted.value = true
  touched.title = true
  touched.region = true
  touched.content = true

  if (
    !canSubmit.value ||
    submitting.value ||
    !selectedRegion.value ||
    !tiptapEditor.value ||
    !isAuthenticated.value
  ) {
    return
  }

  const { serialized, blocks } = prepareSubmissionContent()
  if (plainTextLength.value < 10 || serialized.length < 10) {
    return
  }

  const mediaPlaceholders = mediaUploads.value.map((item) => ({
    placeholder: item.placeholder,
    media_type: item.type,
    filename: item.upload.filename,
    content_type: item.upload.content_type,
  }))

  const payload: DiaryCreateRequest = {
    title: form.title.trim(),
    content: serialized,
    region_id: Number(selectedRegion.value.id),
    tags: tags.value,
    media_placeholders: mediaPlaceholders,
    status: form.status,
    content_blocks: blocks,
  }

  try {
    const response = await submitDiary(
      payload,
      mediaUploads.value.map((item) => item.upload)
    )
    createdDiary.value = response
    try {
      createdDiaryDetail.value = await fetchDiaryDetail(response.id)
    } catch (e) {
      // 如果详情拉取失败，仍然视为创建成功（用户可通过“查看详情”进入）
      createdDiaryDetail.value = null
      console.warn('Failed to fetch created diary detail', e)
    }
  } catch (error) {
    console.error('Failed to create diary', error)
    createdDiary.value = null
    createdDiaryDetail.value = null
  }
}

const goToDiaryDetail = () => {
  if (!createdDiary.value) return
  void router.push({ name: 'diary-detail', params: { id: createdDiary.value.id } })
}

const handleFocus = (field: 'title' | 'region' | 'content') => {
  touched[field] = true
}

const toggleBold = () => tiptapEditor.value?.chain().focus().toggleBold().run()
const toggleStrike = () => tiptapEditor.value?.chain().focus().toggleStrike().run()
const toggleItalic = () => tiptapEditor.value?.chain().focus().toggleItalic().run()
const toggleUnderline = () => tiptapEditor.value?.chain().focus().toggleUnderline().run()
const setParagraph = () => tiptapEditor.value?.chain().focus().setParagraph().run()
const toggleBlockquote = () => tiptapEditor.value?.chain().focus().toggleBlockquote().run()
const toggleBulletList = () => tiptapEditor.value?.chain().focus().toggleBulletList().run()
const toggleOrderedList = () => tiptapEditor.value?.chain().focus().toggleOrderedList().run()
const setTextAlign = (align: 'left' | 'center' | 'right') =>
  tiptapEditor.value?.chain().focus().setTextAlign(align).run()
const insertHorizontalRule = () => tiptapEditor.value?.chain().focus().setHorizontalRule().run()

const promptLink = () => {
  if (!tiptapEditor.value) return
  const currentUrl = tiptapEditor.value.getAttributes('link').href as string | undefined
  const url = window.prompt('输入链接地址', currentUrl || 'https://')

  if (url === null) {
    return
  }

  if (url === '') {
    tiptapEditor.value.chain().focus().extendMarkRange('link').unsetLink().run()
    return
  }

  tiptapEditor.value
    .chain()
    .focus()
    .extendMarkRange('link')
    .setLink({ href: url, target: '_blank', rel: 'noopener noreferrer' })
    .run()
}

const isActive = (name: string, attrs?: Record<string, unknown>) => {
  if (!tiptapEditor.value) return false
  return tiptapEditor.value.isActive(name as any, attrs)
}

const alignmentIsActive = (align: 'left' | 'center' | 'right') => {
  if (!tiptapEditor.value) return align === 'left'
  return tiptapEditor.value.isActive({ textAlign: align })
}

onBeforeUnmount(() => {
  clearMediaUploads()
  tiptapEditor.value?.destroy()
})
</script>

<template>
  <div class="space-y-6">
    <PageSection
      title="撰写旅行日记"
      description="记录旅途中的精彩瞬间，分享你的独特体验"
    >
      <div class="mx-auto max-w-4xl space-y-6">
        <SuccessAlert
          v-if="createdDiary"
          :message="`日记《${createdDiary.title}》创建成功！`"
        />

        <ErrorAlert
          v-else-if="submitError"
          :message="submitError.message || '创建日记失败，请稍后再试。'"
        />

        <form class="space-y-6" @submit.prevent="handleSubmit">
          <div class="space-y-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <div class="space-y-2">
              <div class="flex items-center justify-between text-sm text-slate-400">
                <span>请输入标题（建议30字以内）</span>
                <span>{{ titleLength }} / {{ titleLimit }}</span>
              </div>
              <input
                v-model="form.title"
                type="text"
                class="title-input"
                :maxlength="titleLimit"
                placeholder="输入标题"
                @focus="handleFocus('title')"
              />
              <p v-if="titleError" class="text-xs text-red-500">{{ titleError }}</p>
            </div>

            <div class="grid gap-4 md:grid-cols-2">
              <div class="space-y-2">
                <label class="block text-sm font-medium text-slate-700">关联地区 *</label>
                <KeywordSearchSelect
                  v-model="selectedRegion"
                  :search="handleRegionSearch"
                  placeholder="搜索景区或园区"
                  @select="() => (touched.region = true)"
                  @clear="() => (touched.region = true)"
                />
                <p v-if="regionError" class="text-xs text-red-500">{{ regionError }}</p>
              </div>

              <div class="space-y-2">
                <label class="block text-sm font-medium text-slate-700">标签</label>
                <TagInput v-model="tags" :max-tags="10" placeholder="添加标签，回车确认" />
                <p class="text-xs text-slate-400">示例：美食、自然、亲子、夜景</p>
              </div>
            </div>

            <div class="space-y-3">
              <div class="editor-toolbar">
                <button type="button" :class="{ active: isActive('paragraph') }" @click="setParagraph">T</button>
                <button type="button" :class="{ active: isActive('bold') }" @click="toggleBold">B</button>
                <button type="button" :class="{ active: isActive('strike') }" @click="toggleStrike">S</button>
                <button type="button" :class="{ active: isActive('italic') }" @click="toggleItalic">I</button>
                <button type="button" :class="{ active: isActive('underline') }" @click="toggleUnderline">A</button>
                <div class="toolbar-divider"></div>
                <button type="button" :class="{ active: isActive('blockquote') }" @click="toggleBlockquote">“</button>
                <div class="toolbar-divider"></div>
                <button type="button" :class="{ active: alignmentIsActive('left') }" @click="() => setTextAlign('left')">⟸</button>
                <button type="button" :class="{ active: alignmentIsActive('center') }" @click="() => setTextAlign('center')">⇔</button>
                <button type="button" :class="{ active: alignmentIsActive('right') }" @click="() => setTextAlign('right')">⟹</button>
                <div class="toolbar-divider"></div>
                <button type="button" :class="{ active: isActive('bulletList') }" @click="toggleBulletList">•</button>
                <button type="button" :class="{ active: isActive('orderedList') }" @click="toggleOrderedList">1.</button>
                <div class="toolbar-divider"></div>
                <button type="button" @click="promptLink">🔗</button>
                <button type="button" @click="triggerMediaUpload">🖼️</button>
                <button type="button" @click="insertHorizontalRule">＋</button>
              </div>

              <input
                ref="fileInputRef"
                type="file"
                accept="image/*,video/*,.heic,.heif"
                multiple
                class="hidden"
                @change="handleMediaFilesSelected"
              />

              <ErrorAlert v-if="mediaConvertError" class="mb-3" :message="mediaConvertError" />

              <div v-if="mediaUploads.length > 0" class="rounded-xl border border-slate-200 bg-slate-50 p-4">
                <div class="flex items-center justify-between">
                  <div class="text-sm font-medium text-slate-700">已选择媒体（{{ mediaUploads.length }}）</div>
                  <div class="text-xs text-slate-400">发布成功后将自动上传</div>
                </div>
                <div class="mt-3 grid grid-cols-2 gap-3 md:grid-cols-4">
                  <div
                    v-for="item in mediaUploads"
                    :key="item.placeholder"
                    class="overflow-hidden rounded-lg bg-slate-200"
                  >
                    <img
                      v-if="item.type === 'image'"
                      :src="item.previewUrl"
                      alt=""
                      class="h-28 w-full object-cover"
                    />
                    <video
                      v-else
                      :src="item.previewUrl"
                      class="h-28 w-full object-cover"
                      muted
                      playsinline
                      preload="metadata"
                      controls
                    />
                  </div>
                </div>
              </div>

              <div v-if="createdDiary" class="rounded-xl border border-emerald-200 bg-emerald-50 p-4">
                <div class="text-sm font-medium text-emerald-800">发布成功</div>
                <div class="mt-1 text-xs text-emerald-700">
                  {{ createdDiaryDetail?.media_items?.length ? `已上传媒体：${createdDiaryDetail.media_items.length}` : '媒体上传状态：可点击“查看详情”确认' }}
                </div>
                <div v-if="createdDiaryDetail?.cover_image" class="mt-3 overflow-hidden rounded-lg bg-slate-200">
                  <img :src="createdDiaryDetail.cover_image" alt="" class="w-full max-h-56 object-cover" />
                </div>
              </div>

              <div class="editor-shell" @focus="handleFocus('content')">
                <EditorContent :editor="tiptapEditor || undefined" />
              </div>

              <div class="flex items-center justify-between text-xs text-slate-400">
                <span>内容不少于 10 字</span>
                <span>{{ contentLength }} / {{ characterLimit }}</span>
              </div>
              <p v-if="contentError" class="text-xs text-red-500">{{ contentError }}</p>
            </div>

            <div>
              <label class="block text-sm font-medium text-slate-700">发布设置</label>
              <div class="mt-3 grid gap-3 md:grid-cols-2">
                <label
                  v-for="option in statusOptions"
                  :key="option.value"
                  class="flex cursor-pointer items-start gap-3 rounded-xl border border-slate-200 bg-slate-50 p-4 transition-colors hover:border-primary/70"
                >
                  <input
                    v-model="form.status"
                    type="radio"
                    name="diary-status"
                    :value="option.value"
                    class="mt-1 h-4 w-4 border-primary text-primary focus:ring-primary"
                  />
                  <div>
                    <div class="text-sm font-medium text-slate-700">{{ option.label }}</div>
                    <div class="mt-1 text-xs text-slate-500">{{ option.description }}</div>
                  </div>
                </label>
              </div>
            </div>
          </div>

          <div class="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div class="text-xs text-slate-400">带 * 为必填项</div>
            <div class="flex items-center gap-3">
              <button
                type="submit"
                class="rounded-full bg-primary px-6 py-2 text-sm font-medium text-white shadow-md transition hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
                :disabled="submitting || !canSubmit"
              >
                {{ submitting ? '保存中…' : form.status === 'draft' ? '保存草稿' : '发布日记' }}
              </button>
              <button
                v-if="createdDiary"
                type="button"
                class="rounded-full border border-primary px-6 py-2 text-sm font-medium text-primary transition hover:bg-primary/10"
                @click="goToDiaryDetail"
              >
                查看详情
              </button>
              <button
                v-if="createdDiary"
                type="button"
                class="rounded-full border border-slate-300 px-6 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-100"
                @click="resetForm"
              >
                继续撰写
              </button>
            </div>
          </div>
        </form>
      </div>
    </PageSection>
  </div>
</template>

<style scoped>
.title-input {
  width: 100%;
  border-radius: 1rem;
  border: 1px solid rgba(148, 163, 184, 0.6);
  padding: 0.75rem 1.25rem;
  font-size: 1.125rem;
  font-weight: 600;
  color: #1f2937;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.title-input:focus {
  outline: none;
  border-color: rgba(59, 130, 246, 0.8);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
}

.editor-toolbar {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  border: 1px solid rgba(148, 163, 184, 0.4);
  border-radius: 9999px;
  padding: 0.5rem 0.75rem;
  background: #f8fafc;
  flex-wrap: wrap;
}

.editor-toolbar button {
  border: none;
  background: transparent;
  padding: 0.35rem 0.65rem;
  border-radius: 9999px;
  font-size: 0.875rem;
  color: #475569;
  cursor: pointer;
  transition: background 0.2s ease, color 0.2s ease;
}

.editor-toolbar button:hover {
  background: rgba(59, 130, 246, 0.12);
  color: #1d4ed8;
}

.editor-toolbar button.active {
  background: rgba(59, 130, 246, 0.18);
  color: #1d4ed8;
  font-weight: 600;
}

.toolbar-divider {
  width: 1px;
  height: 1.5rem;
  background: rgba(148, 163, 184, 0.5);
}

.editor-shell {
  border: 1px solid rgba(148, 163, 184, 0.4);
  border-radius: 1rem;
  min-height: 360px;
  padding: 1.25rem;
  background: #fff;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.editor-shell:focus-within {
  border-color: rgba(59, 130, 246, 0.8);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.18);
}

.editor-shell :deep(.ProseMirror) {
  outline: none;
  min-height: 320px;
  white-space: pre-wrap;
}

.editor-shell :deep(.ProseMirror p) {
  margin: 0 0 1rem;
  line-height: 1.8;
  color: #1f2937;
}

.editor-shell :deep(.editor-media-block) {
  display: block; /* 避免与段落内联导致换行异常 */
  width: 100%;
  box-sizing: border-box;
  gap: 0.5rem;
  padding: 0.75rem;
  border-radius: 1rem;
  border: 1px dashed rgba(148, 163, 184, 0.6);
  background: rgba(241, 245, 249, 0.7);
  margin: 0.75rem 0;
}

.editor-shell :deep(.editor-media-block img),
.editor-shell :deep(.editor-media-block video) {
  max-width: 100%;
  height: auto;
  border-radius: 0.75rem;
  background: #0f172a;
}

.editor-shell :deep(.editor-media-block figcaption) {
  font-size: 0.75rem;
  color: #475569;
}

.editor-shell :deep(figcaption:empty) {
  display: none;
}

.editor-shell :deep(blockquote) {
  border-left: 4px solid rgba(59, 130, 246, 0.45);
  margin: 1rem 0;
  padding: 0.75rem 1rem;
  background: rgba(59, 130, 246, 0.08);
  color: #1e293b;
}

.editor-shell :deep(ul),
.editor-shell :deep(ol) {
  padding-left: 1.5rem;
  margin-bottom: 1rem;
}

.editor-shell :deep(hr) {
  border: none;
  border-top: 1px dashed rgba(148, 163, 184, 0.5);
  margin: 1.5rem 0;
}
</style>
