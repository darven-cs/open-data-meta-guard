<!--
  MetaCollectView: 元数据采集（Phase 1 完整实现）

  顶部操作区：搜索 + 状态过滤 + 刷新 + 「新增采集」
  中部表格：DatasetList（查看 / 修改 / 删除）
  侧滑 Drawer：
    - 新增采集：UrlInput + 提交（同步显示结果）
    - 查看详情：DatasetDialog view 模式（JSON 折叠树）
    - 修改：DatasetDialog edit 模式（JSON 编辑器）
-->
<template>
  <div class="meta-collect-view">
    <!-- 头部说明 -->
    <header class="meta-collect-view__head">
      <p class="meta-collect-view__eyebrow">
        <span class="meta-collect-view__eyebrow-tag">Phase 1</span>
        <span class="meta-collect-view__eyebrow-sep">/</span>
        <span class="meta-collect-view__eyebrow-mute">Metadata Ingestion</span>
      </p>
      <h1 class="meta-collect-view__title">元数据采集</h1>
    </header>

    <hr class="meta-collect-view__rule" />

    <!-- 操作区 -->
    <div class="meta-collect-view__toolbar">
      <div class="meta-collect-view__filters">
        <label class="meta-collect-view__field">
          <span class="meta-collect-view__field-label">状态</span>
          <select v-model="statusFilter" class="meta-collect-view__select" @change="onFilterChange">
            <option value="">全部</option>
            <option value="scraped">已采集</option>
            <option value="failed">失败</option>
            <option value="pending">采集中</option>
          </select>
        </label>
      </div>

      <div class="meta-collect-view__actions">
        <button
          type="button"
          class="meta-collect-view__btn"
          :disabled="loading"
          @click="refresh"
        >
          {{ loading ? '刷新中…' : '刷新' }}
        </button>
        <button
          type="button"
          class="meta-collect-view__btn meta-collect-view__btn--primary"
          @click="openIngest"
        >
          + 新增采集
        </button>
      </div>
    </div>

    <!-- 错误条 -->
    <p v-if="errorMsg" class="meta-collect-view__error">
      ⚠ {{ errorMsg }}
      <button class="meta-collect-view__error-close" @click="errorMsg = ''">×</button>
    </p>

    <!-- 表格 -->
    <DatasetList
      :items="items"
      :page="page"
      :size="size"
      :count="items.length"
      :total="totalHint"
      :loading="loading"
      @page-change="onPageChange"
      @view="openView"
      @edit="openEdit"
      @remove="onDelete"
    />

    <!-- 新增采集 Drawer -->
    <Teleport to="body">
      <div v-if="ingestOpen" class="ingest-dialog" role="dialog" aria-modal="true">
        <div class="ingest-dialog__backdrop" @click="closeIngest" />

        <aside class="ingest-dialog__panel">
          <header class="ingest-dialog__head">
            <div class="ingest-dialog__head-meta">
              <span class="ingest-dialog__eyebrow">Ingest</span>
              <h2 class="ingest-dialog__title">新增采集</h2>
            </div>
            <button
              type="button"
              class="ingest-dialog__close"
              aria-label="关闭"
              @click="closeIngest"
            >×</button>
          </header>

          <div class="ingest-dialog__body">
            <UrlInput
              v-model="ingestText"
              :max="50"
            />

            <div v-if="ingestResult" class="ingest-dialog__result">
              <p class="ingest-dialog__result-summary">
                采集完成：
                <span class="ingest-dialog__result-ok">
                  {{ ingestResult.success_count }} 成功
                </span>
                /
                <span class="ingest-dialog__result-fail">
                  {{ ingestResult.failed_count }} 失败
                </span>
                / 共 {{ ingestResult.items.length }} 条
              </p>

              <ul class="ingest-dialog__result-list">
                <li
                  v-for="(it, idx) in ingestResult.items"
                  :key="idx"
                  class="ingest-dialog__result-row"
                >
                  <span
                    class="ingest-dialog__result-badge"
                    :class="it.status === 'scraped' ? 'badge--success' : 'badge--danger'"
                  >
                    {{ it.status === 'scraped' ? 'OK' : 'FAIL' }}
                  </span>
                  <span class="ingest-dialog__result-url" :title="it.url">
                    {{ truncate(it.url, 50) }}
                  </span>
                  <span v-if="it.error_message" class="ingest-dialog__result-err">
                    {{ it.error_message }}
                  </span>
                </li>
              </ul>
            </div>
          </div>

          <footer class="ingest-dialog__foot">
            <button
              type="button"
              class="meta-collect-view__btn"
              :disabled="ingesting"
              @click="closeIngest"
            >
              {{ ingestResult ? '关闭' : '取消' }}
            </button>
            <button
              type="button"
              class="meta-collect-view__btn meta-collect-view__btn--primary"
              :disabled="ingesting || !canIngest || !!ingestResult"
              @click="submitIngest"
            >
              {{ ingesting ? '采集中…' : '提交' }}
            </button>
          </footer>
        </aside>
      </div>
    </Teleport>

    <!-- 详情 / 编辑 Drawer -->
    <DatasetDialog
      :open="dialogOpen"
      :mode="dialogMode"
      :dataset="dialogDataset"
      :saving="dialogSaving"
      @close="closeDialog"
      @save="onSaveEdit"
      @delete="onDeleteFromDialog"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  deleteDataset as apiDelete,
  getDataset as apiGet,
  ingest as apiIngest,
  listDatasets as apiList,
  updateDataset as apiUpdate,
  type Dataset,
  type IngestResponse,
} from '@/api/meta-collect'
import DatasetList from '@/components/meta-collect/DatasetList.vue'
import UrlInput from '@/components/meta-collect/UrlInput.vue'
import DatasetDialog from '@/components/meta-collect/DatasetDialog.vue'

// ───────── 列表状态 ─────────
const items = ref<Dataset[]>([])
const page = ref(1)
const size = ref(20)
const totalHint = ref<number | undefined>(undefined)
const statusFilter = ref<string>('')
const loading = ref(false)
const errorMsg = ref('')

async function refresh() {
  loading.value = true
  errorMsg.value = ''
  try {
    const res = await apiList(page.value, size.value, statusFilter.value || undefined)
    items.value = res.items
    totalHint.value = res.count
  } catch (e) {
    errorMsg.value = (e as Error).message
  } finally {
    loading.value = false
  }
}

function onFilterChange() {
  page.value = 1
  void refresh()
}

function onPageChange(p: number) {
  page.value = p
  void refresh()
}

// ───────── 新增采集 Drawer ─────────
const ingestOpen = ref(false)
const ingestText = ref('')
const ingesting = ref(false)
const ingestResult = ref<IngestResponse | null>(null)

const canIngest = computed(() => {
  return ingestText.value
    .split('\n')
    .map((s) => s.trim())
    .filter((s) => s.length > 0).length > 0
})

function openIngest() {
  ingestText.value = ''
  ingestResult.value = null
  ingestOpen.value = true
}

function closeIngest() {
  if (ingesting.value) return
  ingestOpen.value = false
  ingestResult.value = null
  ingestText.value = ''
  // 刷新列表（可能新增了数据集）
  void refresh()
}

async function submitIngest() {
  if (!canIngest.value) return
  const urls = ingestText.value
    .split('\n')
    .map((s) => s.trim())
    .filter((s) => s.length > 0)

  ingesting.value = true
  errorMsg.value = ''
  try {
    const res = await apiIngest(urls)
    ingestResult.value = res
  } catch (e) {
    errorMsg.value = (e as Error).message
  } finally {
    ingesting.value = false
  }
}

// ───────── 详情 / 编辑 Drawer ─────────
const dialogOpen = ref(false)
const dialogMode = ref<'view' | 'edit'>('view')
const dialogDataset = ref<Dataset | null>(null)
const dialogSaving = ref(false)

function openView(item: Dataset) {
  dialogMode.value = 'view'
  dialogDataset.value = item
  dialogOpen.value = true
}

function openEdit(item: Dataset) {
  dialogMode.value = 'edit'
  dialogDataset.value = item
  dialogOpen.value = true
}

function closeDialog() {
  dialogOpen.value = false
  dialogSaving.value = false
  // 不立刻清 dialogDataset，留给动画结束；下一次打开会被覆盖
}

async function onSaveEdit(metadata: Record<string, unknown>) {
  if (!dialogDataset.value) return
  dialogSaving.value = true
  errorMsg.value = ''
  try {
    const updated = await apiUpdate(dialogDataset.value.id, metadata)
    dialogDataset.value = updated
    // 同步刷新列表中对应行（重新拉详情）
    const idx = items.value.findIndex((x) => x.id === updated.id)
    if (idx >= 0) items.value[idx] = updated
    dialogOpen.value = false
  } catch (e) {
    errorMsg.value = (e as Error).message
  } finally {
    dialogSaving.value = false
  }
}

async function onDeleteFromDialog() {
  if (!dialogDataset.value) return
  try {
    await apiDelete(dialogDataset.value.id)
    items.value = items.value.filter((x) => x.id !== dialogDataset.value!.id)
    dialogOpen.value = false
  } catch (e) {
    errorMsg.value = (e as Error).message
  }
}

async function onDelete(item: Dataset) {
  if (!window.confirm(`确认删除数据集 ${item.id.slice(0, 12)}…?`)) return
  try {
    await apiDelete(item.id)
    items.value = items.value.filter((x) => x.id !== item.id)
  } catch (e) {
    errorMsg.value = (e as Error).message
  }
}

// ───────── helpers ─────────
function truncate(s: string, max: number): string {
  return s.length > max ? s.slice(0, max) + '…' : s
}

// ───────── 初始加载 ─────────
onMounted(() => {
  void refresh()
})

// 暴露刷新方法（占位，预留给 HomeView 卡片跳转时直接刷新场景）
void apiGet
void apiUpdate
</script>

<style scoped>
.meta-collect-view {
  display: flex;
  flex-direction: column;
  width: 100%;
  max-width: 1280px;
  margin: 0 auto;
  padding: var(--sp-6);
  box-sizing: border-box;
  gap: var(--sp-4);
}

.meta-collect-view__head {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
}

.meta-collect-view__eyebrow {
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

.meta-collect-view__eyebrow-tag {
  color: var(--accent);
  border: 1px solid var(--accent-border);
  background: var(--accent-bg);
  padding: 2px var(--sp-2);
  border-radius: var(--radius-sm);
}
.meta-collect-view__eyebrow-sep { color: var(--hairline-strong); }
.meta-collect-view__eyebrow-mute { color: var(--ink-mute); }

.meta-collect-view__title {
  font-family: var(--font-display);
  font-size: var(--text-xl);
  font-weight: 400;
  color: var(--ink);
  margin: 0;
  letter-spacing: -0.02em;
}

.meta-collect-view__lead {
  font-family: var(--font-sans);
  font-size: var(--text-md);
  color: var(--ink-sub);
  margin: 0;
  line-height: 1.55;
}

.meta-collect-view__rule {
  margin: 0;
  border: none;
  border-top: 1px solid var(--hairline);
}

.meta-collect-view__toolbar {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--sp-4);
  flex-wrap: wrap;
}

.meta-collect-view__filters {
  display: flex;
  gap: var(--sp-3);
}

.meta-collect-view__field {
  display: flex;
  flex-direction: column;
  gap: var(--sp-1);
}

.meta-collect-view__field-label {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--ink-mute);
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.meta-collect-view__select {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  padding: var(--sp-1) var(--sp-3);
  border: 1px solid var(--hairline-strong);
  border-radius: var(--radius-sm);
  background: var(--paper);
  color: var(--ink);
  cursor: pointer;
}
.meta-collect-view__select:focus { outline: none; border-color: var(--accent); }

.meta-collect-view__actions {
  display: flex;
  gap: var(--sp-2);
}

.meta-collect-view__btn {
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
.meta-collect-view__btn:hover:not(:disabled) {
  border-color: var(--accent);
  color: var(--accent);
}
.meta-collect-view__btn:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 1px;
}
.meta-collect-view__btn:disabled { opacity: 0.4; cursor: not-allowed; }

.meta-collect-view__btn--primary {
  background: var(--accent);
  border-color: var(--accent);
  color: var(--paper);
}
.meta-collect-view__btn--primary:hover:not(:disabled) {
  background: var(--accent);
  color: var(--paper);
  filter: brightness(1.08);
}

.meta-collect-view__error {
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

.meta-collect-view__error-close {
  margin-left: auto;
  background: transparent;
  border: none;
  color: var(--accent);
  font-size: var(--text-md);
  cursor: pointer;
  padding: 0 var(--sp-2);
}

/* ─────── 新增采集 Drawer ─────── */
.ingest-dialog {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: flex;
  justify-content: flex-end;
}

.ingest-dialog__backdrop {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
}

.ingest-dialog__panel {
  position: relative;
  width: min(560px, 100vw);
  height: 100%;
  background: var(--paper);
  border-left: 1px solid var(--hairline);
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
  animation: slide-in 0.18s ease-out;
}

@keyframes slide-in {
  from { transform: translateX(20px); opacity: 0; }
  to   { transform: translateX(0); opacity: 1; }
}

.ingest-dialog__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--sp-3);
  padding: var(--sp-5);
  border-bottom: 1px solid var(--hairline);
}

.ingest-dialog__head-meta {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--sp-1);
}

.ingest-dialog__eyebrow {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--accent);
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.ingest-dialog__title {
  font-family: var(--font-display);
  font-size: var(--text-lg);
  color: var(--ink);
  margin: 0;
  font-weight: 400;
}

.ingest-dialog__close {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  border: 1px solid var(--hairline-strong);
  background: transparent;
  border-radius: var(--radius-sm);
  font-size: var(--text-md);
  color: var(--ink-sub);
  cursor: pointer;
}
.ingest-dialog__close:hover { color: var(--accent); border-color: var(--accent); }

.ingest-dialog__body {
  flex: 1;
  overflow: auto;
  padding: var(--sp-5);
  display: flex;
  flex-direction: column;
  gap: var(--sp-4);
}

.ingest-dialog__result {
  border: 1px solid var(--hairline);
  border-radius: var(--radius-sm);
  background: var(--paper-sub);
  padding: var(--sp-3);
}

.ingest-dialog__result-summary {
  font-family: var(--font-sans);
  font-size: var(--text-sm);
  color: var(--ink);
  margin: 0 0 var(--sp-2);
}

.ingest-dialog__result-ok   { color: var(--success); font-weight: 500; }
.ingest-dialog__result-fail { color: var(--accent);  font-weight: 500; }

.ingest-dialog__result-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--sp-1);
}

.ingest-dialog__result-row {
  display: flex;
  gap: var(--sp-2);
  align-items: center;
  font-family: var(--font-mono);
  font-size: var(--text-xs);
}

.ingest-dialog__result-badge {
  display: inline-block;
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  padding: 0 var(--sp-2);
  border-radius: var(--radius-sm);
}
.badge--success {
  color: var(--success);
  border: 1px solid var(--success);
  background: var(--success-bg);
}
.badge--danger {
  color: var(--accent);
  border: 1px solid var(--accent);
  background: var(--accent-bg);
}

.ingest-dialog__result-url {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--ink-sub);
}

.ingest-dialog__result-err {
  color: var(--accent);
  font-style: italic;
  font-size: var(--text-xs);
}

.ingest-dialog__foot {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--sp-2);
  padding: var(--sp-3) var(--sp-5);
  border-top: 1px solid var(--hairline);
  background: var(--paper-sub);
}

@media (max-width: 720px) {
  .ingest-dialog__panel { width: 100vw; }
}
</style>
