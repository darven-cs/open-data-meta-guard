<!--
  DatasetCollectList: 按 dataset 维度展示列表 + 行级 state-aware 按钮

  Props:
    items        : DatasetSelectItem[]
    page         : 当前页
    size         : 每页条数
    count        : 当前页条数
    total        : 总数（可选）
    loading      : 加载中
    uploadingIds : Set<string>  — 正在上传的 dataset_id 集合

  Emits:
    page-change : (page)
    upload      : (item)   — 未上传行「上传」按钮
    view        : (item)   — 已上传行「查看文件」按钮
-->
<template>
  <div class="dataset-collect-list">
    <div class="dataset-collect-list__table" :aria-busy="loading">
      <div v-if="loading" class="dataset-collect-list__overlay">加载中…</div>

      <div class="dataset-collect-list__head">
        <div class="dataset-collect-list__col dataset-collect-list__col--dataset">Dataset</div>
        <div class="dataset-collect-list__col dataset-collect-list__col--status">采集状态</div>
        <div class="dataset-collect-list__col dataset-collect-list__col--file">文件信息</div>
        <div class="dataset-collect-list__col dataset-collect-list__col--action">操作</div>
      </div>

      <div v-if="items.length === 0 && !loading" class="dataset-collect-list__empty">
        暂无 dataset。请先在元数据采集页采集数据。
      </div>

      <div
        v-for="it in items"
        :key="it.id"
        class="dataset-collect-list__row"
      >
        <div class="dataset-collect-list__col dataset-collect-list__col--dataset">
          <a
            :href="it.url"
            target="_blank"
            rel="noopener noreferrer"
            class="dataset-collect-list__link"
            :title="it.url"
          >
            {{ truncate(it.url, 60) }}
          </a>
          <span class="dataset-collect-list__ds-id" :title="it.id">
            {{ truncate(it.id, 12) }}
          </span>
        </div>
        <div class="dataset-collect-list__col dataset-collect-list__col--status">
          <span class="dataset-collect-list__badge" :class="statusBadge(it.status)">
            {{ statusLabel(it.status) }}
          </span>
        </div>
        <div class="dataset-collect-list__col dataset-collect-list__col--file">
          <span v-if="it.has_uploaded" class="dataset-collect-list__file-hint">已上传</span>
          <span v-else class="dataset-collect-list__none">— 未上传 —</span>
        </div>
        <div class="dataset-collect-list__col dataset-collect-list__col--action">
          <!-- pending: 采集中 -->
          <button
            v-if="it.status === 'pending'"
            type="button"
            class="dataset-collect-list__btn"
            disabled
          >
            采集中…
          </button>
          <!-- failed: 采集失败 -->
          <button
            v-else-if="it.status === 'failed'"
            type="button"
            class="dataset-collect-list__btn dataset-collect-list__btn--danger"
            disabled
          >
            采集失败
          </button>
          <!-- 上传中 -->
          <button
            v-else-if="uploadingIds.has(it.id)"
            type="button"
            class="dataset-collect-list__btn dataset-collect-list__btn--loading"
            disabled
          >
            上传中…
          </button>
          <!-- 未上传: 上传 -->
          <button
            v-else-if="!it.has_uploaded"
            type="button"
            class="dataset-collect-list__btn dataset-collect-list__btn--primary"
            @click="emit('upload', it)"
          >
            上传
          </button>
          <!-- 已上传: 查看文件 + 继续上传 -->
          <template v-else>
            <button
              type="button"
              class="dataset-collect-list__btn dataset-collect-list__btn--view"
              @click="emit('view', it)"
            >
              查看文件
            </button>
            <button
              type="button"
              class="dataset-collect-list__btn dataset-collect-list__btn--reup"
              @click="emit('upload', it)"
            >
              继续上传
            </button>
          </template>
        </div>
      </div>
    </div>

    <div v-if="totalPages > 1" class="dataset-collect-list__pager">
      <button
        type="button"
        class="dataset-collect-list__page-btn"
        :disabled="page <= 1"
        @click="emit('page-change', page - 1)"
      >
        ← 上一页
      </button>
      <span class="dataset-collect-list__page-info">{{ page }} / {{ totalPages }}</span>
      <button
        type="button"
        class="dataset-collect-list__page-btn"
        :disabled="page >= totalPages"
        @click="emit('page-change', page + 1)"
      >
        下一页 →
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { DatasetSelectItem } from '@/api/data-collect'

const props = defineProps<{
  items: DatasetSelectItem[]
  page: number
  size: number
  count: number
  total?: number
  loading?: boolean
  uploadingIds?: Set<string>
}>()

const emit = defineEmits<{
  'page-change': [page: number]
  upload: [item: DatasetSelectItem]
  view: [item: DatasetSelectItem]
}>()

const uploadingIds = computed(() => props.uploadingIds ?? new Set<string>())

const totalPages = computed(() => {
  const t = props.total ?? props.count
  return Math.max(1, Math.ceil(t / props.size))
})

function truncate(s: string, max: number): string {
  if (!s) return ''
  return s.length > max ? s.slice(0, max) + '…' : s
}

function statusLabel(s: string): string {
  switch (s) {
    case 'scraped': return '已采集'
    case 'failed':  return '采集失败'
    case 'pending': return '采集中'
    default:        return s
  }
}

function statusBadge(s: string): string {
  switch (s) {
    case 'scraped': return 'dataset-collect-list__badge--success'
    case 'failed':  return 'dataset-collect-list__badge--danger'
    case 'pending': return 'dataset-collect-list__badge--warn'
    default:        return ''
  }
}
</script>

<style scoped>
.dataset-collect-list {
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
}

.dataset-collect-list__table {
  position: relative;
  border: 1px solid var(--hairline);
  border-radius: var(--radius-sm);
  background: var(--paper);
  overflow: hidden;
}

.dataset-collect-list__head,
.dataset-collect-list__row {
  display: grid;
  grid-template-columns: minmax(280px, 2fr) 100px minmax(220px, 1.5fr) 180px;
  gap: var(--sp-3);
  align-items: center;
  padding: var(--sp-2) var(--sp-3);
  font-size: var(--text-sm);
}

.dataset-collect-list__head {
  background: var(--paper-sub);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--ink-mute);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  border-bottom: 1px solid var(--hairline);
}

.dataset-collect-list__row {
  border-bottom: 1px solid var(--hairline);
  transition: background 0.12s;
}
.dataset-collect-list__row:last-child { border-bottom: none; }
.dataset-collect-list__row:hover { background: var(--paper-sub); }

.dataset-collect-list__col {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dataset-collect-list__col--dataset {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.dataset-collect-list__col--action {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  flex-wrap: wrap;
}
.dataset-collect-list__col--action > .dataset-collect-list__btn {
  flex: 0 0 auto;
}

.dataset-collect-list__link {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--ink);
  text-decoration: none;
  border-bottom: 1px dashed var(--hairline-strong);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.dataset-collect-list__link:hover { color: var(--accent); border-bottom-color: var(--accent); }

.dataset-collect-list__ds-id {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--ink-mute);
}

.dataset-collect-list__badge {
  display: inline-block;
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  padding: 1px var(--sp-2);
  border: 1px solid var(--hairline-strong);
  border-radius: var(--radius-sm);
  color: var(--ink-sub);
  background: var(--paper-sub);
}
.dataset-collect-list__badge--success {
  color: var(--success);
  border-color: var(--success);
  background: var(--success-bg);
}
.dataset-collect-list__badge--danger {
  color: var(--accent);
  border-color: var(--accent);
  background: var(--accent-bg);
}
.dataset-collect-list__badge--warn {
  color: var(--warning);
  border-color: var(--warning);
  background: var(--warning-bg);
}

.dataset-collect-list__file-hint {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--success);
}

.dataset-collect-list__none {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--ink-mute);
  font-style: italic;
}

.dataset-collect-list__btn {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  padding: var(--sp-1) var(--sp-3);
  border: 1px solid var(--hairline-strong);
  background: var(--paper);
  color: var(--ink);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: border-color 0.12s, color 0.12s, background 0.12s;
  white-space: nowrap;
}
.dataset-collect-list__btn:hover:not(:disabled) {
  border-color: var(--accent);
  color: var(--accent);
}
.dataset-collect-list__btn:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 1px;
}
.dataset-collect-list__btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.dataset-collect-list__btn--primary {
  background: var(--accent);
  border-color: var(--accent);
  color: var(--paper);
}
.dataset-collect-list__btn--primary:hover:not(:disabled) {
  background: var(--accent);
  color: var(--paper);
  filter: brightness(1.08);
}

.dataset-collect-list__btn--view {
  border-color: var(--hairline-strong);
  color: var(--ink-sub);
}
.dataset-collect-list__btn--view:hover:not(:disabled) {
  border-color: var(--success);
  color: var(--success);
}

.dataset-collect-list__btn--reup {
  border-color: var(--warning);
  color: var(--warning);
}
.dataset-collect-list__btn--reup:hover:not(:disabled) {
  border-color: var(--warning);
  color: var(--paper);
  background: var(--warning);
}

.dataset-collect-list__btn--danger {
  border-color: var(--accent);
  color: var(--accent);
}

.dataset-collect-list__btn--loading {
  background: var(--paper-sub);
  border-color: var(--hairline-strong);
  color: var(--ink-mute);
  font-style: italic;
}

.dataset-collect-list__empty {
  padding: var(--sp-7) var(--sp-4);
  text-align: center;
  color: var(--ink-mute);
  font-family: var(--font-display);
  font-style: italic;
  font-size: var(--text-md);
}

.dataset-collect-list__overlay {
  position: absolute;
  inset: 0;
  background: rgba(255, 255, 255, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  color: var(--ink-mute);
  z-index: 1;
}

.dataset-collect-list__pager {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--sp-3);
  padding: var(--sp-3) 0;
}

.dataset-collect-list__page-btn {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  padding: var(--sp-1) var(--sp-3);
  border: 1px solid var(--hairline-strong);
  background: var(--paper);
  color: var(--ink);
  border-radius: var(--radius-sm);
  cursor: pointer;
}
.dataset-collect-list__page-btn:hover:not(:disabled) {
  border-color: var(--accent);
  color: var(--accent);
}
.dataset-collect-list__page-btn:disabled { opacity: 0.4; cursor: not-allowed; }

.dataset-collect-list__page-info {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--ink-mute);
}

@media (max-width: 960px) {
  .dataset-collect-list__head,
  .dataset-collect-list__row {
    grid-template-columns: minmax(220px, 1.6fr) 90px minmax(180px, 1fr) 160px;
  }
}
</style>
