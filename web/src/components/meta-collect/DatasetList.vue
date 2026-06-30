<!--
  DatasetList: 数据集表格 + 分页 + 行操作（查看/修改/删除）

  Props:
    items    : Dataset[]
    page     : 当前页（1-based）
    size     : 每页条数
    count    : 当前页条数
    total    : 总条数（可选，若提供则计算总页数）
    loading  : 加载中（控制 spinner + 禁用行点击）

  Emits:
    page-change    : (page: number)
    view           : (item: Dataset)        — 行「查看」按钮
    edit           : (item: Dataset)        — 行「修改」按钮
    remove         : (item: Dataset)        — 行「删除」按钮
-->
<template>
  <div class="dataset-list">
    <!-- 表格本体 -->
    <div class="dataset-list__table" :aria-busy="loading">
      <div v-if="loading" class="dataset-list__overlay">加载中…</div>

      <div class="dataset-list__head">
        <div class="dataset-list__col dataset-list__col--id">ID</div>
        <div class="dataset-list__col dataset-list__col--url">URL</div>
        <div class="dataset-list__col dataset-list__col--status">状态</div>
        <div class="dataset-list__col dataset-list__col--time">采集时间</div>
        <div class="dataset-list__col dataset-list__col--ops">操作</div>
      </div>

      <div v-if="items.length === 0 && !loading" class="dataset-list__empty">
        暂无数据集。点击右上「新增采集」开始第一批。
      </div>

      <div
        v-for="it in items"
        :key="it.id"
        class="dataset-list__row"
      >
        <div class="dataset-list__col dataset-list__col--id">
          <span class="dataset-list__id" :title="it.id">
            {{ truncate(it.id, 10) }}
          </span>
        </div>
        <div class="dataset-list__col dataset-list__col--url">
          <a
            :href="it.url"
            target="_blank"
            rel="noopener noreferrer"
            class="dataset-list__link"
            :title="it.url"
          >
            {{ truncate(it.url, 60) }}
          </a>
        </div>
        <div class="dataset-list__col dataset-list__col--status">
          <span class="dataset-list__badge" :class="badgeClass(it.status)">
            {{ statusLabel(it.status) }}
          </span>
        </div>
        <div class="dataset-list__col dataset-list__col--time">
          <span class="dataset-list__time">{{ formatTime(it.created_at) }}</span>
        </div>
        <div class="dataset-list__col dataset-list__col--ops">
          <button
            type="button"
            class="dataset-list__btn"
            @click="emit('view', it)"
          >
            查看
          </button>
          <button
            type="button"
            class="dataset-list__btn"
            @click="emit('edit', it)"
          >
            修改
          </button>
          <button
            type="button"
            class="dataset-list__btn dataset-list__btn--danger"
            @click="emit('remove', it)"
          >
            删除
          </button>
        </div>
      </div>
    </div>

    <!-- 分页 -->
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
import type { Dataset } from '@/api/meta-collect'
import Pager from '@/components/common/Pager.vue'

defineProps<{
  items: Dataset[]
  page: number
  size: number
  count: number
  total?: number
  loading?: boolean
}>()

const emit = defineEmits<{
  'page-change': [page: number]
  'size-change': [size: number]
  view: [item: Dataset]
  edit: [item: Dataset]
  remove: [item: Dataset]
}>()

function truncate(s: string, max: number): string {
  if (!s) return ''
  return s.length > max ? s.slice(0, max) + '…' : s
}

function statusLabel(s: string): string {
  switch (s) {
    case 'scraped': return '已采集'
    case 'failed':  return '失败'
    case 'pending': return '采集中'
    default:        return s
  }
}

function badgeClass(s: string): string {
  switch (s) {
    case 'scraped': return 'dataset-list__badge--success'
    case 'failed':  return 'dataset-list__badge--danger'
    case 'pending': return 'dataset-list__badge--warn'
    default:        return ''
  }
}

function formatTime(iso: string | null): string {
  if (!iso) return '—'
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
.dataset-list {
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
}

.dataset-list__table {
  position: relative;
  border: 1px solid var(--hairline);
  border-radius: var(--radius-sm);
  background: var(--paper);
  overflow: hidden;
}

.dataset-list__head,
.dataset-list__row {
  display: grid;
  grid-template-columns: 140px 1fr 90px 150px 220px;
  gap: var(--sp-3);
  align-items: center;
  padding: var(--sp-2) var(--sp-3);
  font-size: var(--text-sm);
}

.dataset-list__head {
  background: var(--paper-sub);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--ink-mute);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  border-bottom: 1px solid var(--hairline);
}

.dataset-list__row {
  border-bottom: 1px solid var(--hairline);
  transition: background 0.12s;
}
.dataset-list__row:last-child { border-bottom: none; }
.dataset-list__row:hover { background: var(--paper-sub); }

.dataset-list__col {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dataset-list__col--url { font-family: var(--font-mono); font-size: var(--text-xs); }

.dataset-list__id {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--ink-sub);
}

.dataset-list__link {
  color: var(--ink);
  text-decoration: none;
  border-bottom: 1px dashed var(--hairline-strong);
}
.dataset-list__link:hover { color: var(--accent); border-bottom-color: var(--accent); }

.dataset-list__badge {
  display: inline-block;
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  padding: 1px var(--sp-2);
  border: 1px solid var(--hairline-strong);
  border-radius: var(--radius-sm);
  color: var(--ink-sub);
  background: var(--paper-sub);
}
.dataset-list__badge--success {
  color: var(--success);
  border-color: var(--success);
  background: var(--success-bg);
}
.dataset-list__badge--danger {
  color: var(--accent);
  border-color: var(--accent);
  background: var(--accent-bg);
}
.dataset-list__badge--warn {
  color: var(--warning);
  border-color: var(--warning);
  background: var(--warning-bg);
}

.dataset-list__time {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--ink-mute);
}

.dataset-list__col--ops {
  display: flex;
  gap: var(--sp-1);
  flex-wrap: wrap;
}

.dataset-list__btn {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  padding: 2px var(--sp-2);
  border: 1px solid var(--hairline-strong);
  background: var(--paper);
  color: var(--ink);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: border-color 0.12s, color 0.12s;
}
.dataset-list__btn:hover { border-color: var(--accent); color: var(--accent); }
.dataset-list__btn--danger:hover { color: var(--accent); }
.dataset-list__btn:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 1px;
}

.dataset-list__empty {
  padding: var(--sp-7) var(--sp-4);
  text-align: center;
  color: var(--ink-mute);
  font-family: var(--font-display);
  font-style: italic;
  font-size: var(--text-md);
}

.dataset-list__overlay {
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
  .dataset-list__head,
  .dataset-list__row {
    grid-template-columns: 90px 1fr 70px 180px;
  }
  .dataset-list__col--time { display: none; }
}
</style>
