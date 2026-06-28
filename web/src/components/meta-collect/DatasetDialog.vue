<!--
  DatasetDialog: 详情 / 编辑 Drawer

  Props:
    open   : boolean         — 是否显示
    mode   : 'view' | 'edit' — 查看 / 编辑模式
    dataset: Dataset | null  — 当前操作的数据集
    saving : boolean         — 保存中（禁用按钮 + 显示 spinner）

  Emits:
    close   : ()          — 关闭 Drawer
    save    : (metadata)  — 编辑模式下点「保存」
    delete  : ()          — 任一模式下点「删除」
-->
<template>
  <Teleport to="body">
    <div v-if="open" class="dataset-dialog" role="dialog" aria-modal="true">
      <div class="dataset-dialog__backdrop" @click="emit('close')" />

      <aside class="dataset-dialog__panel">
        <!-- 头部 -->
        <header class="dataset-dialog__head">
          <div class="dataset-dialog__head-meta">
            <span class="dataset-dialog__eyebrow">
              {{ mode === 'view' ? 'View' : 'Edit' }}
            </span>
            <h2 class="dataset-dialog__title">
              {{ dataset ? truncate(dataset.url, 50) : '' }}
            </h2>
            <p v-if="dataset" class="dataset-dialog__sub">
              <span class="dataset-dialog__badge" :class="badgeClass(dataset.status)">
                {{ statusLabel(dataset.status) }}
              </span>
              <span class="dataset-dialog__id">{{ dataset.id.slice(0, 16) }}…</span>
            </p>
          </div>
          <button
            type="button"
            class="dataset-dialog__close"
            aria-label="关闭"
            @click="emit('close')"
          >×</button>
        </header>

        <!-- 正文 -->
        <div class="dataset-dialog__body">
          <!-- view 模式：折叠树 -->
          <div v-if="mode === 'view'" class="dataset-dialog__json">
            <JsonTree :data="dataset?.metadata ?? {}" />
          </div>

          <!-- edit 模式：textarea 编辑 -->
          <div v-else class="dataset-dialog__editor">
            <textarea
              v-model="editText"
              class="dataset-dialog__textarea"
              spellcheck="false"
              rows="22"
            />
            <p v-if="parseError" class="dataset-dialog__error">
              JSON 解析失败：{{ parseError }}
            </p>
          </div>
        </div>

        <!-- 底部 -->
        <footer class="dataset-dialog__foot">
          <button
            type="button"
            class="dataset-dialog__btn dataset-dialog__btn--danger"
            :disabled="saving"
            @click="onDelete"
          >
            删除
          </button>

          <div class="dataset-dialog__foot-right">
            <button
              type="button"
              class="dataset-dialog__btn"
              :disabled="saving"
              @click="emit('close')"
            >
              取消
            </button>
            <button
              v-if="mode === 'edit'"
              type="button"
              class="dataset-dialog__btn dataset-dialog__btn--primary"
              :disabled="saving || !!parseError"
              @click="onSave"
            >
              {{ saving ? '保存中…' : '保存' }}
            </button>
          </div>
        </footer>
      </aside>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { Dataset } from '@/api/meta-collect'
import JsonTree from './JsonTree.vue'

const props = defineProps<{
  open: boolean
  mode: 'view' | 'edit'
  dataset: Dataset | null
  saving?: boolean
}>()

const emit = defineEmits<{
  close: []
  save: [metadata: Record<string, unknown>]
  delete: []
}>()

const editText = ref<string>('{}')

watch(
  () => [props.open, props.mode, props.dataset] as const,
  () => {
    if (props.open && props.mode === 'edit' && props.dataset) {
      editText.value = JSON.stringify(props.dataset.metadata, null, 2)
    }
  },
  { immediate: true },
)

const parseError = computed<string | null>(() => {
  if (props.mode !== 'edit') return null
  try {
    JSON.parse(editText.value)
    return null
  } catch (e) {
    return (e as Error).message
  }
})

function truncate(s: string, max: number): string {
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
    case 'scraped': return 'badge--success'
    case 'failed':  return 'badge--danger'
    case 'pending': return 'badge--warn'
    default:        return ''
  }
}

function onSave() {
  if (parseError.value) return
  try {
    const parsed = JSON.parse(editText.value)
    if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
      throw new Error('metadata 必须是 JSON 对象')
    }
    emit('save', parsed as Record<string, unknown>)
  } catch (e) {
    // parseError 已显示，无需重复
    void e
  }
}

function onDelete() {
  if (!props.dataset) return
  if (!window.confirm(`确认删除数据集 ${props.dataset.id.slice(0, 12)}…?`)) return
  emit('delete')
}
</script>

<style scoped>
.dataset-dialog {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: flex;
  justify-content: flex-end;
}

.dataset-dialog__backdrop {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
}

.dataset-dialog__panel {
  position: relative;
  width: min(720px, 100vw);
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

.dataset-dialog__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--sp-3);
  padding: var(--sp-5);
  border-bottom: 1px solid var(--hairline);
}

.dataset-dialog__head-meta {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: var(--sp-1);
}

.dataset-dialog__eyebrow {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--accent);
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.dataset-dialog__title {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  color: var(--ink);
  margin: 0;
  word-break: break-all;
  line-height: 1.4;
}

.dataset-dialog__sub {
  display: flex;
  gap: var(--sp-2);
  align-items: center;
  margin: var(--sp-1) 0 0;
  font-size: var(--text-xs);
  color: var(--ink-mute);
}

.dataset-dialog__badge {
  display: inline-block;
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  padding: 1px var(--sp-2);
  border: 1px solid var(--hairline-strong);
  border-radius: var(--radius-sm);
  color: var(--ink-sub);
}
.badge--success { color: var(--success); border-color: var(--success); background: var(--success-bg); }
.badge--danger  { color: var(--accent);  border-color: var(--accent);  background: var(--accent-bg); }
.badge--warn    { color: var(--warning); border-color: var(--warning); background: var(--warning-bg); }

.dataset-dialog__id {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--ink-mute);
}

.dataset-dialog__close {
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
.dataset-dialog__close:hover { color: var(--accent); border-color: var(--accent); }

.dataset-dialog__body {
  flex: 1;
  overflow: auto;
  padding: var(--sp-5);
}

.dataset-dialog__json {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  color: var(--ink);
}

.dataset-dialog__textarea {
  width: 100%;
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  line-height: 1.55;
  padding: var(--sp-3);
  border: 1px solid var(--hairline-strong);
  border-radius: var(--radius-sm);
  background: var(--paper-sub);
  color: var(--ink);
  resize: vertical;
  min-height: 320px;
  box-sizing: border-box;
}
.dataset-dialog__textarea:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 1px var(--accent);
}

.dataset-dialog__error {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--accent);
  margin: var(--sp-2) 0 0;
}

.dataset-dialog__foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--sp-3) var(--sp-5);
  border-top: 1px solid var(--hairline);
  background: var(--paper-sub);
}

.dataset-dialog__foot-right {
  display: flex;
  gap: var(--sp-2);
}

.dataset-dialog__btn {
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
}
.dataset-dialog__btn:hover:not(:disabled) {
  border-color: var(--accent);
  color: var(--accent);
}
.dataset-dialog__btn:disabled { opacity: 0.4; cursor: not-allowed; }

.dataset-dialog__btn--primary {
  background: var(--accent);
  border-color: var(--accent);
  color: var(--paper);
}
.dataset-dialog__btn--primary:hover:not(:disabled) {
  background: var(--accent);
  color: var(--paper);
  filter: brightness(1.05);
}

.dataset-dialog__btn--danger:hover:not(:disabled) {
  border-color: var(--accent);
  color: var(--accent);
}

@media (max-width: 720px) {
  .dataset-dialog__panel { width: 100vw; }
}
</style>
