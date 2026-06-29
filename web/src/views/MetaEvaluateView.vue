<!--
  MetaEvaluateView: 元数据评估（Phase 2 完整实现 · 行级评估按钮版）

  直接展示 datasets 列表，每行右边一个 state-aware 按钮：
    - status='pending'                              → 「采集中…」禁用
    - status=其他 + latest_evaluation == null       → 「触发评估」（点击行内触发）
    - status=其他 + latest_evaluation != null       → 「查看评估」（点击打开 Drawer）
  触发中：按钮变为「评估中…」禁用；触发成功后自动刷新并打开 Drawer。
-->
<template>
  <div class="meta-evaluate-view">
    <!-- 头部 -->
    <header class="meta-evaluate-view__head">
      <p class="meta-evaluate-view__eyebrow">
        <span class="meta-evaluate-view__eyebrow-tag">Phase 2</span>
        <span class="meta-evaluate-view__eyebrow-sep">/</span>
        <span class="meta-evaluate-view__eyebrow-mute">Metadata Evaluation</span>
      </p>
      <h1 class="meta-evaluate-view__title">元数据评估</h1>
    </header>

    <hr class="meta-evaluate-view__rule" />

    <!-- 工具栏 -->
    <div class="meta-evaluate-view__toolbar">
      <button
        type="button"
        class="meta-evaluate-view__btn"
        :disabled="loading"
        @click="refresh"
      >
        {{ loading ? '刷新中…' : '刷新' }}
      </button>
    </div>

    <!-- 错误条 -->
    <p v-if="errorMsg" class="meta-evaluate-view__error">
      ⚠ {{ errorMsg }}
      <button class="meta-evaluate-view__error-close" @click="errorMsg = ''">×</button>
    </p>

    <!-- 列表 -->
    <EvaluationList
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
    <EvaluationDialog
      :open="dialogOpen"
      :evaluation="dialogEvaluation"
      :dataset="dialogDataset"
      :loading="dialogLoading"
      @close="closeDialog"
    />
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import {
  getEvaluation as apiGetEvaluation,
  getEvaluationJob as apiGetJob,
  listDatasetsWithEvaluation as apiListDatasets,
  triggerEvaluate as apiTrigger,
  type DatasetEvalItem,
  type EvaluationDetail,
} from '@/api/meta-evaluate'
import EvaluationList from '@/components/meta-evaluate/EvaluationList.vue'
import EvaluationDialog from '@/components/meta-evaluate/EvaluationDialog.vue'

// ───────── 列表状态 ─────────
const items = ref<DatasetEvalItem[]>([])
const page = ref(1)
const size = ref(20)
const totalHint = ref<number | undefined>(undefined)
const loading = ref(false)
const errorMsg = ref('')
const evaluatingIds = reactive(new Set<string>())

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

// ───────── 触发评估（行内） ─────────
async function triggerForItem(item: DatasetEvalItem) {
  await doTrigger(item)
}

function confirmReevaluate(item: DatasetEvalItem) {
  if (evaluatingIds.has(item.id)) return
  if (item.status === 'pending') return
  const ok = window.confirm(
    `确认重新评估「${truncate(item.url, 40)}」？\n\n将会生成新的评估记录,历史记录会保留。`
  )
  if (!ok) return
  void doTrigger(item)
}

function truncate(s: string, max: number): string {
  if (!s) return ''
  return s.length > max ? s.slice(0, max) + '…' : s
}

async function doTrigger(item: DatasetEvalItem) {
  if (evaluatingIds.has(item.id)) return
  if (item.status === 'pending') return
  evaluatingIds.add(item.id)
  errorMsg.value = ''
  // 立即打开 Drawer 显示 loading，避免等后端完成期间出现空窗
  dialogDataset.value = item
  dialogOpen.value = true
  dialogEvaluation.value = null
  dialogLoading.value = true
  try {
    const job = await apiTrigger(item.id)
    const MAX_POLLS = 120
    const POLL_INTERVAL_MS = 1500
    for (let i = 0; i < MAX_POLLS; i++) {
      await sleep(POLL_INTERVAL_MS)
      const status = await apiGetJob(job.job_id)
      if (status.status === 'completed' && status.evaluation_id) {
        await openDetailById(status.evaluation_id)
        return
      }
      if (status.status === 'failed' || status.status === 'cancelled') {
        dialogOpen.value = false
        errorMsg.value =
          status.error || `评估${status.status === 'failed' ? '失败' : '已取消'}`
        return
      }
    }
    dialogOpen.value = false
    errorMsg.value = '评估超时,请稍后刷新列表查看结果'
  } catch (e) {
    errorMsg.value = (e as Error).message
    dialogOpen.value = false
  } finally {
    dialogLoading.value = false
    evaluatingIds.delete(item.id)
  }
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

// ───────── 详情 Drawer ─────────
const dialogOpen = ref(false)
const dialogEvaluation = ref<EvaluationDetail | null>(null)
const dialogDataset = ref<DatasetEvalItem | null>(null)
const dialogLoading = ref(false)

async function openDetailByItem(item: DatasetEvalItem) {
  if (!item.latest_evaluation) return
  dialogDataset.value = item
  await openDetailById(item.latest_evaluation.id)
}

async function openDetailById(id: number | string) {
  dialogOpen.value = true
  dialogEvaluation.value = null
  dialogLoading.value = true
  try {
    dialogEvaluation.value = await apiGetEvaluation(id)
  } catch (e) {
    errorMsg.value = (e as Error).message
    dialogOpen.value = false
  } finally {
    dialogLoading.value = false
  }
}

function closeDialog() {
  dialogOpen.value = false
  dialogEvaluation.value = null
  dialogDataset.value = null
}

// ───────── 初始加载 ─────────
onMounted(() => {
  void refresh()
})
</script>

<style scoped>
.meta-evaluate-view {
  display: flex;
  flex-direction: column;
  width: 100%;
  max-width: 1280px;
  margin: 0 auto;
  padding: var(--sp-6);
  box-sizing: border-box;
  gap: var(--sp-4);
}

.meta-evaluate-view__head {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
}

.meta-evaluate-view__eyebrow {
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

.meta-evaluate-view__eyebrow-tag {
  color: var(--accent);
  border: 1px solid var(--accent-border);
  background: var(--accent-bg);
  padding: 2px var(--sp-2);
  border-radius: var(--radius-sm);
}
.meta-evaluate-view__eyebrow-sep { color: var(--hairline-strong); }
.meta-evaluate-view__eyebrow-mute { color: var(--ink-mute); }

.meta-evaluate-view__title {
  font-family: var(--font-display);
  font-size: var(--text-xl);
  font-weight: 400;
  color: var(--ink);
  margin: 0;
  letter-spacing: -0.02em;
}

.meta-evaluate-view__lead {
  font-family: var(--font-sans);
  font-size: var(--text-sm);
  color: var(--ink-sub);
  margin: 0;
  line-height: 1.55;
}

.meta-evaluate-view__rule {
  margin: 0;
  border: none;
  border-top: 1px solid var(--hairline);
}

.meta-evaluate-view__toolbar {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--sp-2);
}

.meta-evaluate-view__btn {
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
.meta-evaluate-view__btn:hover:not(:disabled) {
  border-color: var(--accent);
  color: var(--accent);
}
.meta-evaluate-view__btn:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 1px;
}
.meta-evaluate-view__btn:disabled { opacity: 0.4; cursor: not-allowed; }

.meta-evaluate-view__error {
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

.meta-evaluate-view__error-close {
  margin-left: auto;
  background: transparent;
  border: none;
  color: var(--accent);
  font-size: var(--text-md);
  cursor: pointer;
  padding: 0 var(--sp-2);
}
</style>