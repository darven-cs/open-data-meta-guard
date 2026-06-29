<!--
  FileManageModal: 居中弹窗 — 展示 dataset 下的所有上传文件

  Props:
    open    : boolean
    dataset : DatasetSelectItem | null
    items   : DownloadListItem[]
    loading : boolean

  Emits:
    close          : ()
    download       : (item)
    remove         : (item)
    trigger-upload : (dataset)
-->
<template>
  <Teleport to="body">
    <div v-if="open" class="file-manage-modal" role="dialog" aria-modal="true">
      <div class="file-manage-modal__backdrop" @click="emit('close')" />

      <div class="file-manage-modal__panel">
        <header class="file-manage-modal__head">
          <div class="file-manage-modal__head-meta">
            <h2 class="file-manage-modal__title">文件管理</h2>
            <p v-if="dataset" class="file-manage-modal__sub">
              {{ truncate(dataset.url, 56) }}
              <span class="file-manage-modal__ds-id" :title="dataset.id">{{ truncate(dataset.id, 12) }}</span>
            </p>
          </div>
          <button
            type="button"
            class="file-manage-modal__close"
            aria-label="关闭"
            @click="emit('close')"
          >×</button>
        </header>

        <div class="file-manage-modal__body">
          <div v-if="loading" class="file-manage-modal__loading">加载中…</div>

          <template v-else>
            <!-- 表头 -->
            <div class="file-manage-modal__head-row">
              <div class="file-manage-modal__col file-manage-modal__col--name">文件名</div>
              <div class="file-manage-modal__col file-manage-modal__col--fmt">格式</div>
              <div class="file-manage-modal__col file-manage-modal__col--size">大小</div>
              <div class="file-manage-modal__col file-manage-modal__col--time">上传时间</div>
              <div class="file-manage-modal__col file-manage-modal__col--ops">操作</div>
            </div>

            <!-- 行 -->
            <div
              v-for="it in items"
              :key="it.id"
              class="file-manage-modal__row"
            >
              <div class="file-manage-modal__col file-manage-modal__col--name">
                <span class="file-manage-modal__name" :title="it.file_name">
                  {{ truncate(it.file_name, 40) }}
                </span>
              </div>
              <div class="file-manage-modal__col file-manage-modal__col--fmt">
                <span class="file-manage-modal__fmt">{{ it.file_format.toUpperCase() }}</span>
              </div>
              <div class="file-manage-modal__col file-manage-modal__col--size">
                <span class="file-manage-modal__size">{{ formatSize(it.file_size) }}</span>
              </div>
              <div class="file-manage-modal__col file-manage-modal__col--time">
                <span class="file-manage-modal__time">{{ formatTime(it.created_at) }}</span>
              </div>
              <div class="file-manage-modal__col file-manage-modal__col--ops">
                <button
                  type="button"
                  class="file-manage-modal__btn"
                  @click="emit('download', it)"
                >
                  下载
                </button>
                <button
                  type="button"
                  class="file-manage-modal__btn file-manage-modal__btn--danger"
                  @click="emit('remove', it)"
                >
                  删除
                </button>
              </div>
            </div>

            <!-- 空态 -->
            <div v-if="items.length === 0" class="file-manage-modal__empty">
              暂无上传记录
            </div>
          </template>
        </div>

        <footer class="file-manage-modal__foot">
          <button
            type="button"
            class="file-manage-modal__btn"
            @click="emit('close')"
          >
            关闭
          </button>
          <button
            v-if="dataset"
            type="button"
            class="file-manage-modal__btn file-manage-modal__btn--primary"
            @click="emit('trigger-upload', dataset)"
          >
            + 上传新文件
          </button>
        </footer>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import type { DatasetSelectItem } from '@/api/data-collect'
import type { DownloadListItem } from '@/api/data-collect'

defineProps<{
  open: boolean
  dataset: DatasetSelectItem | null
  items: DownloadListItem[]
  loading: boolean
}>()

const emit = defineEmits<{
  close: []
  download: [item: DownloadListItem]
  remove: [item: DownloadListItem]
  'trigger-upload': [dataset: DatasetSelectItem]
}>()

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
.file-manage-modal {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: flex;
  align-items: center;
  justify-content: center;
}

.file-manage-modal__backdrop {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
}

.file-manage-modal__panel {
  position: relative;
  width: min(800px, 92vw);
  max-height: 80vh;
  background: var(--paper);
  border: 1px solid var(--hairline);
  border-radius: var(--radius-md);
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
  animation: modal-in 0.16s ease-out;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.18);
}

@keyframes modal-in {
  from { transform: translateY(12px); opacity: 0; }
  to   { transform: translateY(0); opacity: 1; }
}

.file-manage-modal__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--sp-3);
  padding: var(--sp-5);
  border-bottom: 1px solid var(--hairline);
}

.file-manage-modal__head-meta {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--sp-1);
}

.file-manage-modal__title {
  font-family: var(--font-display);
  font-size: var(--text-lg);
  color: var(--ink);
  margin: 0;
  font-weight: 400;
}

.file-manage-modal__sub {
  font-family: var(--font-sans);
  font-size: var(--text-sm);
  color: var(--ink-sub);
  margin: 0;
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-manage-modal__ds-id {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--ink-mute);
  flex-shrink: 0;
}

.file-manage-modal__close {
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
.file-manage-modal__close:hover { color: var(--accent); border-color: var(--accent); }

.file-manage-modal__body {
  flex: 1;
  overflow: auto;
  padding: 0;
}

.file-manage-modal__loading {
  padding: var(--sp-8) var(--sp-4);
  text-align: center;
  color: var(--ink-mute);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
}

.file-manage-modal__head-row,
.file-manage-modal__row {
  display: grid;
  grid-template-columns: 1fr 80px 100px 170px 80px;
  gap: var(--sp-3);
  align-items: center;
  padding: var(--sp-2) var(--sp-5);
  font-size: var(--text-sm);
}

.file-manage-modal__head-row {
  background: var(--paper-sub);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--ink-mute);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  border-bottom: 1px solid var(--hairline);
  position: sticky;
  top: 0;
  z-index: 1;
}

.file-manage-modal__row {
  border-bottom: 1px solid var(--hairline);
  transition: background 0.12s;
}
.file-manage-modal__row:last-child { border-bottom: none; }
.file-manage-modal__row:hover { background: var(--paper-sub); }

.file-manage-modal__col {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-manage-modal__name {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--ink);
}

.file-manage-modal__fmt {
  display: inline-block;
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  padding: 1px var(--sp-2);
  border: 1px solid var(--hairline-strong);
  border-radius: var(--radius-sm);
  color: var(--ink-sub);
  background: var(--paper-sub);
}

.file-manage-modal__size,
.file-manage-modal__time {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--ink-sub);
}

.file-manage-modal__col--ops {
  display: flex;
  gap: var(--sp-1);
}

.file-manage-modal__btn {
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
.file-manage-modal__btn:hover { border-color: var(--accent); color: var(--accent); }
.file-manage-modal__btn--danger:hover { color: var(--accent); }
.file-manage-modal__btn:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 1px;
}
.file-manage-modal__btn--primary {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  letter-spacing: 0.05em;
  text-transform: uppercase;
  padding: var(--sp-2) var(--sp-4);
  background: var(--accent);
  border: 1px solid var(--accent);
  color: var(--paper);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: filter 0.12s;
}
.file-manage-modal__btn--primary:hover {
  filter: brightness(1.08);
}

.file-manage-modal__empty {
  padding: var(--sp-7) var(--sp-4);
  text-align: center;
  color: var(--ink-mute);
  font-family: var(--font-display);
  font-style: italic;
  font-size: var(--text-md);
}

.file-manage-modal__foot {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--sp-2);
  padding: var(--sp-3) var(--sp-5);
  border-top: 1px solid var(--hairline);
  background: var(--paper-sub);
}
</style>
