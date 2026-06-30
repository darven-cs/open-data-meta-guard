<!--
  EvaluationList: 元数据评估页 datasets 表格 + 行级评估按钮（state-aware）

  Props:
    items          : DatasetEvalItem[]  — datasets 列表（带 latest_evaluation）
    page           : 当前页（1-based）
    size           : 每页条数
    count          : 当前页条数
    total          : 总条数（可选）
    loading        : 加载中
    evaluatingIds  : Set<string>        — 当前正在评估的 dataset_id 集合

  Emits:
    page-change : (page)
    view        : (item)   — 已评估行「查看评估」按钮
    trigger     : (item)   — 未评估行「触发评估」按钮
    reevaluate  : (item)   — 已评估行「重新评估」按钮
-->
<template>
  <div class="evaluation-list">
    <div class="evaluation-list__table" :aria-busy="loading">
      <div v-if="loading" class="evaluation-list__overlay">加载中…</div>

      <div class="evaluation-list__head">
        <div class="evaluation-list__col evaluation-list__col--dataset">Dataset</div>
        <div class="evaluation-list__col evaluation-list__col--status">采集状态</div>
        <div class="evaluation-list__col evaluation-list__col--eval">最近评估</div>
        <div class="evaluation-list__col evaluation-list__col--action">操作</div>
      </div>

      <div v-if="items.length === 0 && !loading" class="evaluation-list__empty">
        暂无 dataset。请先在元数据采集页采集数据。
      </div>

      <div
        v-for="it in items"
        :key="it.id"
        class="evaluation-list__row"
      >
        <div class="evaluation-list__col evaluation-list__col--dataset">
          <a
            :href="it.url"
            target="_blank"
            rel="noopener noreferrer"
            class="evaluation-list__link"
            :title="it.url"
          >
            {{ truncate(it.url, 60) }}
          </a>
          <span class="evaluation-list__ds-id" :title="it.id">
            {{ truncate(it.id, 12) }}
          </span>
        </div>
        <div class="evaluation-list__col evaluation-list__col--status">
          <span class="evaluation-list__badge" :class="statusBadge(it.status)">
            {{ statusLabel(it.status) }}
          </span>
        </div>
        <div class="evaluation-list__col evaluation-list__col--eval">
          <template v-if="it.latest_evaluation">
            <span
              class="evaluation-list__grade"
              :class="gradeClass(it.latest_evaluation.grade)"
            >
              {{ it.latest_evaluation.grade }}
            </span>
            <span class="evaluation-list__score">
              {{ it.latest_evaluation.score_total }}<span class="evaluation-list__score-max">/405</span>
            </span>
            <span class="evaluation-list__eval-time">
              {{ formatTime(it.latest_evaluation.created_at) }}
            </span>
          </template>
          <span v-else class="evaluation-list__none">— 未评估 —</span>
        </div>
        <div class="evaluation-list__col evaluation-list__col--action">
          <!-- 采集中：禁用 -->
          <button
            v-if="it.status === 'pending'"
            type="button"
            class="evaluation-list__btn"
            disabled
          >
            采集中…
          </button>
          <!-- 评估中：禁用 -->
          <button
            v-else-if="evaluatingIds.has(it.id)"
            type="button"
            class="evaluation-list__btn evaluation-list__btn--loading"
            disabled
          >
            评估中…
          </button>
          <!-- 已评估：查看 + 重新评估（并排） -->
          <template v-else-if="it.latest_evaluation">
            <button
              type="button"
              class="evaluation-list__btn evaluation-list__btn--view"
              @click="emit('view', it)"
            >
              查看评估
            </button>
            <button
              type="button"
              class="evaluation-list__btn evaluation-list__btn--reevaluate"
              @click="emit('reevaluate', it)"
            >
              重新评估
            </button>
          </template>
          <!-- 未评估：触发 -->
          <button
            v-else
            type="button"
            class="evaluation-list__btn evaluation-list__btn--primary"
            @click="emit('trigger', it)"
          >
            触发评估
          </button>
        </div>
      </div>
    </div>

    <Pager
      :page="page"
      :size="size"
      :total="total ?? count"
      :loading="loading"
      @page-change="(p: number) => emit('page-change', p)"
      @size-change="(s: number) => emit('size-change', s)"
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { DatasetEvalItem } from '@/api/meta-evaluate'
import Pager from '@/components/common/Pager.vue'

const props = defineProps<{
  items: DatasetEvalItem[]
  page: number
  size: number
  count: number
  total?: number
  loading?: boolean
  evaluatingIds?: Set<string>
}>()

const emit = defineEmits<{
  'page-change': [page: number]
  'size-change': [size: number]
  view: [item: DatasetEvalItem]
  trigger: [item: DatasetEvalItem]
  reevaluate: [item: DatasetEvalItem]
}>()

const evaluatingIds = computed(() => props.evaluatingIds ?? new Set<string>())

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
    case 'scraped': return 'evaluation-list__badge--success'
    case 'failed':  return 'evaluation-list__badge--danger'
    case 'pending': return 'evaluation-list__badge--warn'
    default:        return ''
  }
}

function gradeClass(g: string): string {
  switch (g) {
    case 'Excellent':  return 'evaluation-list__grade--excellent'
    case 'Good':       return 'evaluation-list__grade--good'
    case 'Sufficient': return 'evaluation-list__grade--sufficient'
    case 'Bad':        return 'evaluation-list__grade--bad'
    default:           return ''
  }
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
.evaluation-list {
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
}

.evaluation-list__table {
  position: relative;
  border: 1px solid var(--hairline);
  border-radius: var(--radius-sm);
  background: var(--paper);
  overflow: hidden;
}

.evaluation-list__head,
.evaluation-list__row {
  display: grid;
  grid-template-columns: minmax(280px, 2fr) 100px minmax(220px, 1.5fr) 180px;
  gap: var(--sp-3);
  align-items: center;
  padding: var(--sp-2) var(--sp-3);
  font-size: var(--text-sm);
}

.evaluation-list__head {
  background: var(--paper-sub);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--ink-mute);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  border-bottom: 1px solid var(--hairline);
}

.evaluation-list__row {
  border-bottom: 1px solid var(--hairline);
  transition: background 0.12s;
}
.evaluation-list__row:last-child { border-bottom: none; }
.evaluation-list__row:hover { background: var(--paper-sub); }

.evaluation-list__col {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.evaluation-list__col--dataset {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.evaluation-list__col--action {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  flex-wrap: wrap;
}
.evaluation-list__col--action > .evaluation-list__btn {
  flex: 0 0 auto;
}

.evaluation-list__link {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--ink);
  text-decoration: none;
  border-bottom: 1px dashed var(--hairline-strong);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.evaluation-list__link:hover { color: var(--accent); border-bottom-color: var(--accent); }

.evaluation-list__ds-id {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--ink-mute);
}

.evaluation-list__badge {
  display: inline-block;
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  padding: 1px var(--sp-2);
  border: 1px solid var(--hairline-strong);
  border-radius: var(--radius-sm);
  color: var(--ink-sub);
  background: var(--paper-sub);
}
.evaluation-list__badge--success {
  color: var(--success);
  border-color: var(--success);
  background: var(--success-bg);
}
.evaluation-list__badge--danger {
  color: var(--accent);
  border-color: var(--accent);
  background: var(--accent-bg);
}
.evaluation-list__badge--warn {
  color: var(--warning);
  border-color: var(--warning);
  background: var(--warning-bg);
}

.evaluation-list__col--eval {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  flex-wrap: wrap;
}

.evaluation-list__grade {
  display: inline-block;
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  padding: 1px var(--sp-2);
  border: 1px solid var(--hairline-strong);
  border-radius: var(--radius-sm);
  font-weight: 500;
}
.evaluation-list__grade--excellent {
  color: var(--success);
  border-color: var(--success);
  background: var(--success-bg);
}
.evaluation-list__grade--good {
  color: var(--accent);
  border-color: var(--accent);
  background: var(--accent-bg);
}
.evaluation-list__grade--sufficient {
  color: var(--warning);
  border-color: var(--warning);
  background: var(--warning-bg);
}
.evaluation-list__grade--bad {
  color: var(--accent);
  border-color: var(--accent);
  background: var(--accent-bg);
  opacity: 0.75;
}

.evaluation-list__score {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  color: var(--ink);
  font-weight: 500;
}
.evaluation-list__score-max {
  color: var(--ink-mute);
  font-weight: 400;
  font-size: var(--text-xs);
}

.evaluation-list__eval-time {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--ink-mute);
}

.evaluation-list__none {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--ink-mute);
  font-style: italic;
}

.evaluation-list__btn {
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
.evaluation-list__btn:hover:not(:disabled) {
  border-color: var(--accent);
  color: var(--accent);
}
.evaluation-list__btn:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 1px;
}
.evaluation-list__btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.evaluation-list__btn--primary {
  background: var(--accent);
  border-color: var(--accent);
  color: var(--paper);
}
.evaluation-list__btn--primary:hover:not(:disabled) {
  background: var(--accent);
  color: var(--paper);
  filter: brightness(1.08);
}

.evaluation-list__btn--view {
  border-color: var(--hairline-strong);
  color: var(--ink-sub);
}
.evaluation-list__btn--view:hover:not(:disabled) {
  border-color: var(--success);
  color: var(--success);
}

.evaluation-list__btn--reevaluate {
  border-color: var(--warning);
  color: var(--warning);
}
.evaluation-list__btn--reevaluate:hover:not(:disabled) {
  border-color: var(--warning);
  color: var(--paper);
  background: var(--warning);
  filter: none;
}

.evaluation-list__btn--loading {
  background: var(--paper-sub);
  border-color: var(--hairline-strong);
  color: var(--ink-mute);
  font-style: italic;
}

.evaluation-list__empty {
  padding: var(--sp-7) var(--sp-4);
  text-align: center;
  color: var(--ink-mute);
  font-family: var(--font-display);
  font-style: italic;
  font-size: var(--text-md);
}

.evaluation-list__overlay {
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

@media (max-width: 960px) {
  .evaluation-list__head,
  .evaluation-list__row {
    grid-template-columns: minmax(220px, 1.6fr) 90px minmax(180px, 1fr) 160px;
  }
}
</style>