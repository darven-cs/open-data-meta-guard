<!--
  UploadList: 上传记录表格 + 分页 + 行操作（下载 / 删除）

  Props:
    items   : DownloadListItem[]
    page    : 当前页
    size    : 每页
    count   : 当前页条数
    total   : 总数（可选）
    loading : 加载中

  Emits:
    page-change : (page: number)
    download    : (item)
    remove      : (item)
-->
<template>
  <div class="upload-list">
    <div class="upload-list__table" :aria-busy="loading">
      <div v-if="loading" class="upload-list__overlay">加载中…</div>

      <div class="upload-list__head">
        <div class="upload-list__col upload-list__col--id">ID</div>
        <div class="upload-list__col upload-list__col--dataset">DATASET</div>
        <div class="upload-list__col upload-list__col--name">文件名</div>
        <div class="upload-list__col upload-list__col--fmt">格式</div>
        <div class="upload-list__col upload-list__col--size">大小</div>
        <div class="upload-list__col upload-list__col--time">上传时间</div>
        <div class="upload-list__col upload-list__col--ops">操作</div>
      </div>

      <div v-if="items.length === 0 && !loading" class="upload-list__empty">
        暂无上传记录。请先选择 dataset，然后点击「上传」。
      </div>

      <div
        v-for="it in items"
        :key="it.id"
        class="upload-list__row"
      >
        <div class="upload-list__col upload-list__col--id">
          <span class="upload-list__id">{{ it.id }}</span>
        </div>
        <div class="upload-list__col upload-list__col--dataset">
          <span class="upload-list__ds" :title="it.dataset_id">
            {{ truncate(it.dataset_id, 14) }}
          </span>
        </div>
        <div class="upload-list__col upload-list__col--name">
          <span class="upload-list__name" :title="it.file_name">
            {{ truncate(it.file_name, 36) }}
          </span>
        </div>
        <div class="upload-list__col upload-list__col--fmt">
          <span class="upload-list__fmt">{{ it.file_format.toUpperCase() }}</span>
        </div>
        <div class="upload-list__col upload-list__col--size">
          <span class="upload-list__size">{{ formatSize(it.file_size) }}</span>
        </div>
        <div class="upload-list__col upload-list__col--time">
          <span class="upload-list__time">{{ formatTime(it.created_at) }}</span>
        </div>
        <div class="upload-list__col upload-list__col--ops">
          <button
            type="button"
            class="upload-list__btn"
            @click="emit('download', it)"
          >
            下载
          </button>
          <button
            type="button"
            class="upload-list__btn upload-list__btn--danger"
            @click="emit('remove', it)"
          >
            删除
          </button>
        </div>
      </div>
    </div>

    <div v-if="totalPages > 1" class="upload-list__pager">
      <button
        type="button"
        class="upload-list__page-btn"
        :disabled="page <= 1"
        @click="emit('page-change', page - 1)"
      >
        ← 上一页
      </button>
      <span class="upload-list__page-info">{{ page }} / {{ totalPages }}</span>
      <button
        type="button"
        class="upload-list__page-btn"
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
import type { DownloadListItem } from '@/api/data-collect'

const props = defineProps<{
  items: DownloadListItem[]
  page: number
  size: number
  count: number
  total?: number
  loading?: boolean
}>()

const emit = defineEmits<{
  'page-change': [page: number]
  download: [item: DownloadListItem]
  remove: [item: DownloadListItem]
}>()

const totalPages = computed(() => {
  const t = props.total ?? props.count
  return Math.max(1, Math.ceil(t / props.size))
})

function truncate(s: string, max: number): string {
  if (!s) return ''
  return s.length > max ? s.slice(0, max) + '…' : s
}

function formatSize(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes <= 0) return '—'
  const units = ['B', 'KB', 'MB', 'GB']
  let v = bytes
  let i = 0
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024
    i += 1
  }
  return `${v.toFixed(v >= 100 || i === 0 ? 0 : 1)} ${units[i]}`
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
.upload-list {
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
}

.upload-list__table {
  position: relative;
  border: 1px solid var(--hairline);
  border-radius: var(--radius-sm);
  background: var(--paper);
  overflow: hidden;
}

.upload-list__head,
.upload-list__row {
  display: grid;
  grid-template-columns: 60px 140px 1fr 70px 90px 150px 160px;
  gap: var(--sp-3);
  align-items: center;
  padding: var(--sp-2) var(--sp-3);
  font-size: var(--text-sm);
}

.upload-list__head {
  background: var(--paper-sub);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--ink-mute);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  border-bottom: 1px solid var(--hairline);
}

.upload-list__row {
  border-bottom: 1px solid var(--hairline);
  transition: background 0.12s;
}
.upload-list__row:last-child { border-bottom: none; }
.upload-list__row:hover { background: var(--paper-sub); }

.upload-list__col {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.upload-list__id,
.upload-list__ds,
.upload-list__name,
.upload-list__size,
.upload-list__time {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--ink-sub);
}

.upload-list__name { color: var(--ink); }

.upload-list__fmt {
  display: inline-block;
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  padding: 1px var(--sp-2);
  border: 1px solid var(--hairline-strong);
  border-radius: var(--radius-sm);
  color: var(--ink-sub);
  background: var(--paper-sub);
}

.upload-list__col--ops {
  display: flex;
  gap: var(--sp-1);
  flex-wrap: wrap;
}

.upload-list__btn {
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
.upload-list__btn:hover { border-color: var(--accent); color: var(--accent); }
.upload-list__btn--danger:hover { color: var(--accent); }
.upload-list__btn:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 1px;
}

.upload-list__empty {
  padding: var(--sp-7) var(--sp-4);
  text-align: center;
  color: var(--ink-mute);
  font-family: var(--font-display);
  font-style: italic;
  font-size: var(--text-md);
}

.upload-list__overlay {
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

.upload-list__pager {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--sp-3);
  padding: var(--sp-3) 0;
}

.upload-list__page-btn {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  padding: var(--sp-1) var(--sp-3);
  border: 1px solid var(--hairline-strong);
  background: var(--paper);
  color: var(--ink);
  border-radius: var(--radius-sm);
  cursor: pointer;
}
.upload-list__page-btn:hover:not(:disabled) { border-color: var(--accent); color: var(--accent); }
.upload-list__page-btn:disabled { opacity: 0.4; cursor: not-allowed; }

.upload-list__page-info {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--ink-mute);
}

@media (max-width: 960px) {
  .upload-list__head,
  .upload-list__row {
    grid-template-columns: 50px 110px 1fr 60px 130px;
  }
  .upload-list__col--size,
  .upload-list__col--time { display: none; }
}
</style>