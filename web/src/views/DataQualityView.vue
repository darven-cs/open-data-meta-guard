<!--
  DataQualityView: 数据质量评估（Phase 4 完整实现）

  展示 data_downloads 列表，每行带评估状态和触发/查看按钮。
  完全仿造 MetaEvaluateView 的交互模式。
-->
<template>
  <div class="data-quality-view">
    <!-- 头部 -->
    <header class="data-quality-view__head">
      <p class="data-quality-view__eyebrow">
        <span class="data-quality-view__eyebrow-tag">Phase 4</span>
        <span class="data-quality-view__eyebrow-sep">/</span>
        <span class="data-quality-view__eyebrow-mute">Data Quality Assessment</span>
      </p>
      <h1 class="data-quality-view__title">数据质量评估</h1>
    </header>

    <hr class="data-quality-view__rule" />

    <!-- 工具栏 -->
    <div class="data-quality-view__toolbar">
      <button
        type="button"
        class="data-quality-view__btn"
        :disabled="loading"
        @click="refresh"
      >
        {{ loading ? '刷新中…' : '刷新' }}
      </button>
    </div>

    <!-- 错误条 -->
    <p v-if="errorMsg" class="data-quality-view__error">
      ⚠ {{ errorMsg }}
      <button class="data-quality-view__error-close" @click="errorMsg = ''">×</button>
    </p>

    <!-- 列表 -->
    <QualityList
      :items="items"
      :page="page"
      :size="size"
      :count="items.length"
      :total="totalHint"
      :loading="loading"
      :evaluating-ids="evaluatingIds"
      @page-change="onPageChange"
      @view="openDetailByItem"
      @trigger="triggerForItem"
      @reevaluate="confirmReevaluate"
    />

    <!-- 详情 Drawer -->
    <QualityDialog
      :open="dialogOpen"
      :quality="dialogQuality"
      :download="dialogDownload"
      :loading="dialogLoading"
      @close="closeDialog"
    />
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import {
  evaluate as apiEvaluate,
  getQuality as apiGetQuality,
  listDownloadsWithQuality as apiListDownloads,
  type DownloadWithQualityItem,
  type QualityDetail,
} from '@/api/data-quality'
import QualityList from '@/components/data-quality/QualityList.vue'
import QualityDialog from '@/components/data-quality/QualityDialog.vue'

// ───────── 列表状态 ─────────
const items = ref<DownloadWithQualityItem[]>([])
const page = ref(1)
const size = ref(20)
const totalHint = ref<number | undefined>(undefined)
const loading = ref(false)
const errorMsg = ref('')
const evaluatingIds = reactive(new Set<number>())

async function refresh() {
  loading.value = true
  errorMsg.value = ''
  try {
    const res = await apiListDownloads(page.value, size.value)
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

// ───────── 触发评估（行内，同步） ─────────
async function triggerForItem(item: DownloadWithQualityItem) {
  await doTrigger(item)
}

function confirmReevaluate(item: DownloadWithQualityItem) {
  if (evaluatingIds.has(item.id)) return
  const ok = window.confirm(
    `确认重新评估「${truncate(item.file_name, 40)}」？\n\n将会生成新的评估记录，历史记录会保留。`
  )
  if (!ok) return
  void doTrigger(item)
}

async function doTrigger(item: DownloadWithQualityItem) {
  if (evaluatingIds.has(item.id)) return
  evaluatingIds.add(item.id)
  errorMsg.value = ''
  dialogDownload.value = item
  dialogOpen.value = true
  dialogQuality.value = null
  dialogLoading.value = true
  try {
    const res = await apiEvaluate(item.id)
    await openDetailById(res.evaluation_id)
  } catch (e) {
    errorMsg.value = (e as Error).message
    dialogOpen.value = false
  } finally {
    dialogLoading.value = false
    evaluatingIds.delete(item.id)
  }
}

function truncate(s: string, max: number): string {
  if (!s) return ''
  return s.length > max ? s.slice(0, max) + '…' : s
}

// ───────── 详情 Drawer ─────────
const dialogOpen = ref(false)
const dialogQuality = ref<QualityDetail | null>(null)
const dialogDownload = ref<DownloadWithQualityItem | null>(null)
const dialogLoading = ref(false)

async function openDetailByItem(item: DownloadWithQualityItem) {
  if (!item.latest_evaluation) return
  dialogDownload.value = item
  await openDetailById(item.latest_evaluation.id)
}

async function openDetailById(id: number) {
  dialogOpen.value = true
  dialogQuality.value = null
  dialogLoading.value = true
  try {
    dialogQuality.value = await apiGetQuality(id)
  } catch (e) {
    errorMsg.value = (e as Error).message
    dialogOpen.value = false
  } finally {
    dialogLoading.value = false
  }
}

function closeDialog() {
  dialogOpen.value = false
  dialogQuality.value = null
  dialogDownload.value = null
}

// ───────── 初始加载 ─────────
onMounted(() => {
  void refresh()
})
</script>

<style scoped>
.data-quality-view {
  display: flex;
  flex-direction: column;
  width: 100%;
  max-width: 1280px;
  margin: 0 auto;
  padding: var(--sp-6);
  box-sizing: border-box;
  gap: var(--sp-4);
}

.data-quality-view__head {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
}

.data-quality-view__eyebrow {
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

.data-quality-view__eyebrow-tag {
  color: var(--accent);
  border: 1px solid var(--accent-border);
  background: var(--accent-bg);
  padding: 2px var(--sp-2);
  border-radius: var(--radius-sm);
}
.data-quality-view__eyebrow-sep { color: var(--hairline-strong); }
.data-quality-view__eyebrow-mute { color: var(--ink-mute); }

.data-quality-view__title {
  font-family: var(--font-display);
  font-size: var(--text-xl);
  font-weight: 400;
  color: var(--ink);
  margin: 0;
  letter-spacing: -0.02em;
}

.data-quality-view__lead {
  font-family: var(--font-sans);
  font-size: var(--text-sm);
  color: var(--ink-sub);
  margin: 0;
  line-height: 1.55;
}

.data-quality-view__rule {
  margin: 0;
  border: none;
  border-top: 1px solid var(--hairline);
}

.data-quality-view__toolbar {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--sp-2);
}

.data-quality-view__btn {
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
.data-quality-view__btn:hover:not(:disabled) {
  border-color: var(--accent);
  color: var(--accent);
}
.data-quality-view__btn:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 1px;
}
.data-quality-view__btn:disabled { opacity: 0.4; cursor: not-allowed; }

.data-quality-view__error {
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

.data-quality-view__error-close {
  margin-left: auto;
  background: transparent;
  border: none;
  color: var(--accent);
  font-size: var(--text-md);
  cursor: pointer;
  padding: 0 var(--sp-2);
}
</style>
