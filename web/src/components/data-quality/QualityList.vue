<!--
  QualityList: 数据质量评估页 data_downloads 表格 + 行级评估按钮

  Props:
    items          : DownloadWithQualityItem[]  — data_downloads 列表
    page           : 当前页
    size           : 每页条数
    count          : 当前页条数
    total          : 总条数（可选）
    loading        : 加载中
    evaluatingIds  : Set<number> — 当前正在评估的 data_download_id

  Emits:
    page-change : (page)
    view        : (item)   — 已评估行「查看评估」
    trigger     : (item)   — 未评估行「触发评估」
    reevaluate  : (item)   — 已评估行「重新评估」
-->
<template>
  <div class="quality-list">
    <div class="quality-list__table" :aria-busy="loading">
      <div v-if="loading" class="quality-list__overlay">加载中…</div>

      <div class="quality-list__head">
        <div class="quality-list__col quality-list__col--file">文件</div>
        <div class="quality-list__col quality-list__col--dataset">Dataset</div>
        <div class="quality-list__col quality-list__col--eval">最近评估</div>
        <div class="quality-list__col quality-list__col--action">操作</div>
      </div>

      <div v-if="items.length === 0 && !loading" class="quality-list__empty">
        暂无数据。请先在数据采集页上传文件。
      </div>

      <div
        v-for="it in items"
        :key="it.id"
        class="quality-list__row"
      >
        <div class="quality-list__col quality-list__col--file">
          <span class="quality-list__file-name" :title="it.file_name">
            {{ truncate(it.file_name, 40) }}
          </span>
          <span class="quality-list__file-meta">
            <span class="quality-list__badge quality-list__badge--format">{{ it.file_format }}</span>
            <span class="quality-list__file-size">{{ formatSize(it.file_size) }}</span>
          </span>
        </div>
        <div class="quality-list__col quality-list__col--dataset">
          <span class="quality-list__ds-id" :title="it.dataset_id">
            {{ truncate(it.dataset_id, 12) }}
          </span>
        </div>
        <div class="quality-list__col quality-list__col--eval">
          <template v-if="it.latest_evaluation">
            <span class="quality-list__eval-summary">
              {{ summarize(it.latest_evaluation.summary) }}
            </span>
            <span class="quality-list__eval-time">
              {{ formatTime(it.latest_evaluation.created_at) }}
            </span>
          </template>
          <span v-else class="quality-list__none">— 未评估 —</span>
        </div>
        <div class="quality-list__col quality-list__col--action">
          <!-- 评估中：禁用 -->
          <button
            v-if="evaluatingIds.has(it.id)"
            type="button"
            class="quality-list__btn quality-list__btn--loading"
            disabled
          >
            评估中…
          </button>
          <!-- 已评估：查看 + 重新评估 -->
          <template v-else-if="it.latest_evaluation">
            <button
              type="button"
              class="quality-list__btn quality-list__btn--view"
              @click="emit('view', it)"
            >
              查看评估
            </button>
            <button
              type="button"
              class="quality-list__btn quality-list__btn--reevaluate"
              @click="emit('reevaluate', it)"
            >
              重新评估
            </button>
          </template>
          <!-- 未评估：触发 -->
          <button
            v-else
            type="button"
            class="quality-list__btn quality-list__btn--primary"
            @click="emit('trigger', it)"
          >
            触发评估
          </button>
        </div>
      </div>
    </div>

    <div v-if="totalPages > 1" class="quality-list__pager">
      <button
        type="button"
        class="quality-list__page-btn"
        :disabled="page <= 1"
        @click="emit('page-change', page - 1)"
      >
        ← 上一页
      </button>
      <span class="quality-list__page-info">{{ page }} / {{ totalPages }}</span>
      <button
        type="button"
        class="quality-list__page-btn"
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
import type { DownloadWithQualityItem } from '@/api/data-quality'

const props = defineProps<{
  items: DownloadWithQualityItem[]
  page: number
  size: number
  count: number
  total?: number
  loading?: boolean
  evaluatingIds?: Set<number>
}>()

const emit = defineEmits<{
  'page-change': [page: number]
  view: [item: DownloadWithQualityItem]
  trigger: [item: DownloadWithQualityItem]
  reevaluate: [item: DownloadWithQualityItem]
}>()

const evaluatingIds = computed(() => props.evaluatingIds ?? new Set<number>())

const totalPages = computed(() => {
  const t = props.total ?? props.count
  return Math.max(1, Math.ceil(t / props.size))
})

function truncate(s: string, max: number): string {
  if (!s) return ''
  return s.length > max ? s.slice(0, max) + '…' : s
}

function formatSize(bytes: number): string {
  if (!bytes) return '0 B'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function summarize(s: Record<string, unknown>): string {
  if (!s || typeof s !== 'object') return ''
  const parts: string[] = []
  if (typeof s.n === 'number') parts.push(`${s.n} 行`)
  if (typeof s.p === 'number') parts.push(`${s.p} 列`)
  if (typeof s.p_missing === 'number') parts.push(`缺失 ${s.p_missing}%`)
  return parts.join(' · ') || '—'
}

function formatTime(iso: string | null): string {
  if (!iso) return ''
  try {
    const d = new Date(iso)
    return d.toLocaleString('zh-CN', {
      year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit',
    })
  } catch {
    return iso
  }
}
</script>

<style scoped>
.quality-list {
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
}

.quality-list__table {
  position: relative;
  border: 1px solid var(--hairline);
  border-radius: var(--radius-sm);
  background: var(--paper);
  overflow: hidden;
}

.quality-list__head,
.quality-list__row {
  display: grid;
  grid-template-columns: minmax(260px, 2fr) 140px minmax(200px, 1.5fr) 180px;
  gap: var(--sp-3);
  align-items: center;
  padding: var(--sp-2) var(--sp-3);
  font-size: var(--text-sm);
}

.quality-list__head {
  background: var(--paper-sub);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--ink-mute);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  border-bottom: 1px solid var(--hairline);
}

.quality-list__row {
  border-bottom: 1px solid var(--hairline);
  transition: background 0.12s;
}
.quality-list__row:last-child { border-bottom: none; }
.quality-list__row:hover { background: var(--paper-sub); }

.quality-list__col {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.quality-list__col--file {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.quality-list__col--action {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  flex-wrap: wrap;
}

.quality-list__file-name {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--ink);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.quality-list__file-meta {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  font-size: 10px;
}

.quality-list__badge--format {
  display: inline-block;
  font-family: var(--font-mono);
  font-size: 10px;
  padding: 1px var(--sp-2);
  border: 1px solid var(--hairline-strong);
  border-radius: var(--radius-sm);
  color: var(--ink-sub);
  background: var(--paper-sub);
  text-transform: uppercase;
}

.quality-list__file-size {
  font-family: var(--font-mono);
  color: var(--ink-mute);
}

.quality-list__ds-id {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--ink-sub);
}

.quality-list__col--eval {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.quality-list__eval-summary {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--ink);
}

.quality-list__eval-time {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--ink-mute);
}

.quality-list__none {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--ink-mute);
  font-style: italic;
}

.quality-list__btn {
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
.quality-list__btn:hover:not(:disabled) {
  border-color: var(--accent);
  color: var(--accent);
}
.quality-list__btn:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 1px;
}
.quality-list__btn:disabled { opacity: 0.4; cursor: not-allowed; }

.quality-list__btn--primary {
  background: var(--accent);
  border-color: var(--accent);
  color: var(--paper);
}
.quality-list__btn--primary:hover:not(:disabled) {
  background: var(--accent);
  color: var(--paper);
  filter: brightness(1.08);
}

.quality-list__btn--view {
  border-color: var(--hairline-strong);
  color: var(--ink-sub);
}
.quality-list__btn--view:hover:not(:disabled) {
  border-color: var(--success);
  color: var(--success);
}

.quality-list__btn--reevaluate {
  border-color: var(--warning);
  color: var(--warning);
}
.quality-list__btn--reevaluate:hover:not(:disabled) {
  border-color: var(--warning);
  color: var(--paper);
  background: var(--warning);
  filter: none;
}

.quality-list__btn--loading {
  background: var(--paper-sub);
  border-color: var(--hairline-strong);
  color: var(--ink-mute);
  font-style: italic;
}

.quality-list__empty {
  padding: var(--sp-7) var(--sp-4);
  text-align: center;
  color: var(--ink-mute);
  font-family: var(--font-display);
  font-style: italic;
  font-size: var(--text-md);
}

.quality-list__overlay {
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

.quality-list__pager {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--sp-3);
  padding: var(--sp-3) 0;
}

.quality-list__page-btn {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  padding: var(--sp-1) var(--sp-3);
  border: 1px solid var(--hairline-strong);
  background: var(--paper);
  color: var(--ink);
  border-radius: var(--radius-sm);
  cursor: pointer;
}
.quality-list__page-btn:hover:not(:disabled) {
  border-color: var(--accent);
  color: var(--accent);
}
.quality-list__page-btn:disabled { opacity: 0.4; cursor: not-allowed; }

.quality-list__page-info {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--ink-mute);
}

@media (max-width: 960px) {
  .quality-list__head,
  .quality-list__row {
    grid-template-columns: minmax(200px, 1.6fr) 120px minmax(160px, 1fr) 160px;
  }
}
</style>
