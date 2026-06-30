<!--
  DataCollectView: 数据采集 - 按 dataset 维度列表展示，行级 state-aware 按钮

  列表直接展示所有 datasets，每行按 has_uploaded 状态切换操作：
    - status='pending'          → 「采集中…」禁用
    - status='failed'           → 「采集失败」禁用
    - uploadingIds.has(id)      → 「上传中…」禁用
    - has_uploaded === false    → 「上传」按钮 → 打开 UploadDrawer
    - has_uploaded === true     → 「查看文件」→ FileManageModal + 「继续上传」→ UploadDrawer
-->
<template>
  <div class="data-collect-view">
    <header class="data-collect-view__head">
      <p class="data-collect-view__eyebrow">
        <span class="data-collect-view__eyebrow-tag">Phase 3</span>
        <span class="data-collect-view__eyebrow-sep">/</span>
        <span class="data-collect-view__eyebrow-mute">Data Upload</span>
      </p>
      <h1 class="data-collect-view__title">数据采集</h1>
    </header>

    <hr class="data-collect-view__rule" />

    <!-- 工具栏 -->
    <div class="data-collect-view__toolbar">
      <button
        type="button"
        class="data-collect-view__btn"
        :disabled="loading"
        @click="refresh"
      >
        {{ loading ? '刷新中…' : '刷新' }}
      </button>
    </div>

    <!-- 错误条 -->
    <p v-if="errorMsg" class="data-collect-view__error">
      ⚠ {{ errorMsg }}
      <button class="data-collect-view__error-close" @click="errorMsg = ''">×</button>
    </p>

    <!-- 列表 -->
    <DatasetCollectList
      :items="items"
      :page="page"
      :size="size"
      :count="items.length"
      :total="totalHint"
      :loading="loading"
      :uploading-ids="uploadingIds"
      @page-change="onPageChange"
      @size-change="onSizeChange"
      @upload="onUpload"
      @view="onView"
    />

    <!-- 上传 Drawer -->
    <UploadDrawer
      :open="uploadDrawerOpen"
      :dataset="uploadDrawerDataset"
      :uploading="uploading"
      :progress="uploadProgress"
      :error-msg="uploadError"
      :upload-label="uploadLabel"
      @close="closeUploadDrawer"
      @submit="submitUpload"
    />

    <!-- 文件管理 Modal -->
    <FileManageModal
      :open="modalOpen"
      :dataset="modalDataset"
      :items="modalItems"
      :loading="modalLoading"
      @close="closeModal"
      @download="onModalDownload"
      @remove="onModalRemove"
      @trigger-upload="onTriggerUploadFromModal"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import {
  buildDownloadUrl,
  deleteDownload as apiDeleteDownload,
  listDatasets as apiListDatasets,
  listDownloads as apiListDownloads,
  upload as apiUpload,
  type DatasetSelectItem,
  type DownloadListItem,
} from '@/api/data-collect'
import DatasetCollectList from '@/components/data-collect/DatasetCollectList.vue'
import UploadDrawer from '@/components/data-collect/UploadDrawer.vue'
import FileManageModal from '@/components/data-collect/FileManageModal.vue'

// ───────── 列表状态 ─────────
const items = ref<DatasetSelectItem[]>([])
const page = ref(1)
const size = ref(20)
const totalHint = ref<number | undefined>(undefined)
const loading = ref(false)
const errorMsg = ref('')
const uploadingIds = reactive(new Set<string>())

async function refresh() {
  loading.value = true
  errorMsg.value = ''
  try {
    const res = await apiListDatasets(page.value, size.value)
    items.value = res.items
    totalHint.value = res.count
  } catch (e) {
    errorMsg.value = (e as Error).message
  } finally {
    loading.value = false
  }
}

function onPageChange(p: number) {
  page.value = p
  void refresh()
}

function onSizeChange(s: number) {
  size.value = s
  page.value = 1
  void refresh()
}

// ───────── 行操作 ─────────
function onUpload(item: DatasetSelectItem) {
  uploadDrawerDataset.value = item
  uploadError.value = ''
  uploadProgress.value = 0
  uploadDrawerOpen.value = true
}

async function onView(item: DatasetSelectItem) {
  modalDataset.value = item
  modalOpen.value = true
  modalLoading.value = true
  try {
    const res = await apiListDownloads(item.id, 1, 100)
    modalItems.value = res.items
  } catch (e) {
    errorMsg.value = (e as Error).message
  } finally {
    modalLoading.value = false
  }
}

// ───────── Upload Drawer ─────────
const uploadDrawerOpen = ref(false)
const uploadDrawerDataset = ref<DatasetSelectItem | null>(null)
const uploadProgress = ref(0)
const uploadError = ref('')
const uploading = ref(false)

function closeUploadDrawer() {
  if (uploading.value) return
  uploadDrawerOpen.value = false
  uploadError.value = ''
  uploadProgress.value = 0
  void refresh()
}

const uploadLabel = computed(() => {
  if (!uploading.value) return ''
  if (!uploadDrawerDataset.value) return '上传中…'
  return `正在上传 ${currentFileIndex.value + 1}/${currentFileTotal.value} …`
})

const currentFileIndex = ref(0)
const currentFileTotal = ref(0)

async function submitUpload(payload: { dataset_id: string; files: File[] }) {
  uploadingIds.add(payload.dataset_id)
  uploading.value = true
  uploadError.value = ''
  uploadProgress.value = 0

  const { dataset_id, files } = payload
  const total = files.length
  currentFileTotal.value = total

  try {
    for (let i = 0; i < total; i++) {
      currentFileIndex.value = i
      const file = files[i]

      try {
        await apiUpload(dataset_id, file, (filePct) => {
          // 整体进度 = 已完成文件的基础进度 + 当前文件加权进度
          const pct = Math.round(((i + filePct / 100) / total) * 100)
          uploadProgress.value = pct
        })
        // 每个文件完成后更新基础进度
        uploadProgress.value = Math.round(((i + 1) / total) * 100)
      } catch (e) {
        uploadError.value = `'${file.name}' 上传失败: ${(e as Error).message}`
        return // 停止后续上传
      }
    }

    // 全部完成
    uploadProgress.value = 100
    await refresh()
    // 如果 modal 开着且是同一个 dataset，刷新 modal 列表
    if (modalOpen.value && modalDataset.value?.id === dataset_id) {
      const res = await apiListDownloads(dataset_id, 1, 100)
      modalItems.value = res.items
    }
  } finally {
    uploading.value = false
    uploadingIds.delete(payload.dataset_id)
  }
}

// ───────── File Manage Modal ─────────
const modalOpen = ref(false)
const modalDataset = ref<DatasetSelectItem | null>(null)
const modalItems = ref<DownloadListItem[]>([])
const modalLoading = ref(false)

function closeModal() {
  modalOpen.value = false
  modalDataset.value = null
  modalItems.value = []
}

function onTriggerUploadFromModal(ds: DatasetSelectItem) {
  modalOpen.value = false
  onUpload(ds)
}

function onModalDownload(item: DownloadListItem) {
  const a = document.createElement('a')
  a.href = buildDownloadUrl(item.id)
  a.download = item.file_name
  document.body.appendChild(a)
  a.click()
  a.remove()
}

async function onModalRemove(item: DownloadListItem) {
  if (!window.confirm(`确认删除 ${item.file_name} ?`)) return
  try {
    await apiDeleteDownload(item.id)
    if (modalDataset.value) {
      const res = await apiListDownloads(modalDataset.value.id, 1, 100)
      modalItems.value = res.items
    }
    await refresh()
    if (modalItems.value.length === 0) {
      modalOpen.value = false
    }
  } catch (e) {
    errorMsg.value = (e as Error).message
  }
}

// ───────── 初始加载 ─────────
onMounted(() => {
  void refresh()
})
</script>

<style scoped>
.data-collect-view {
  display: flex;
  flex-direction: column;
  width: 100%;
  max-width: 1280px;
  margin: 0 auto;
  padding: var(--sp-6);
  box-sizing: border-box;
  gap: var(--sp-4);
}

.data-collect-view__head {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
}

.data-collect-view__eyebrow {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--ink-mute);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  margin: 0;
}

.data-collect-view__eyebrow-tag {
  color: var(--accent);
  border: 1px solid var(--accent-border);
  background: var(--accent-bg);
  padding: 2px var(--sp-2);
  border-radius: var(--radius-sm);
}
.data-collect-view__eyebrow-sep { color: var(--hairline-strong); }
.data-collect-view__eyebrow-mute { color: var(--ink-mute); }

.data-collect-view__title {
  font-family: var(--font-display);
  font-size: var(--text-xl);
  font-weight: 400;
  color: var(--ink);
  margin: 0;
  letter-spacing: -0.02em;
}

.data-collect-view__lead {
  font-family: var(--font-sans);
  font-size: var(--text-md);
  color: var(--ink-sub);
  margin: 0;
  line-height: 1.55;
}

.data-collect-view__rule {
  margin: 0;
  border: none;
  border-top: 1px solid var(--hairline);
}

.data-collect-view__toolbar {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--sp-2);
}

.data-collect-view__btn {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  letter-spacing: 0.05em;
  text-transform: uppercase;
  padding: var(--sp-2) var(--sp-4);
  border: 1px solid var(--hairline-strong);
  background: var(--paper);
  color: var(--ink);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: border-color 0.12s, color 0.12s;
}
.data-collect-view__btn:hover:not(:disabled) {
  border-color: var(--accent);
  color: var(--accent);
}
.data-collect-view__btn:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 1px;
}
.data-collect-view__btn:disabled { opacity: 0.4; cursor: not-allowed; }

.data-collect-view__error {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  color: var(--accent);
  border: 1px solid var(--accent);
  background: var(--accent-bg);
  padding: var(--sp-2) var(--sp-3);
  border-radius: var(--radius-sm);
  margin: 0;
}

.data-collect-view__error-close {
  margin-left: auto;
  background: transparent;
  border: none;
  color: var(--accent);
  font-size: var(--text-md);
  cursor: pointer;
  padding: 0 var(--sp-2);
}
</style>
