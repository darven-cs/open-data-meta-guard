<!--
  UploadDrawer: 数据采集上传 Drawer（dataset 锁定模式，支持多文件）

  Props:
    open        : boolean
    dataset     : DatasetSelectItem | null  — 锁定的 dataset
    uploading   : boolean
    progress    : number — 0..100
    errorMsg    : string
    uploadLabel?: string — 自定义上传中文案（默认「上传中…」）

  Emits:
    close  : ()
    submit : ({ dataset_id, files: File[] })
-->
<template>
  <Teleport to="body">
    <div v-if="open" class="upload-drawer" role="dialog" aria-modal="true">
      <div class="upload-drawer__backdrop" @click="emit('close')" />

      <aside class="upload-drawer__panel">
        <header class="upload-drawer__head">
          <div class="upload-drawer__head-meta">
            <span class="upload-drawer__eyebrow">Phase 3 / Data Upload</span>
            <h2 class="upload-drawer__title">上传数据集文件</h2>
            <p v-if="dataset" class="upload-drawer__sub">
              {{ truncate(dataset.url, 56) }}
              <span class="upload-drawer__ds-id" :title="dataset.id">{{ truncate(dataset.id, 12) }}</span>
            </p>
          </div>
          <button
            type="button"
            class="upload-drawer__close"
            aria-label="关闭"
            @click="emit('close')"
          >×</button>
        </header>

        <div class="upload-drawer__body">
          <!-- 锁定 dataset 信息 -->
          <div v-if="dataset" class="upload-drawer__locked-ds">
            <span class="upload-drawer__field-label">锁定 Dataset</span>
            <span class="upload-drawer__locked-value" :title="dataset.url">
              {{ truncate(dataset.url, 72) }}
            </span>
          </div>

          <FileUploadInput
            :accept="'.csv,.xlsx,.json'"
            hint="拖拽文件到此处，或点击选择"
            @files-selected="onFilesSelected"
          />

          <UploadProgress
            v-if="uploading || progress > 0"
            :progress="progress"
            :label="uploading ? (uploadLabel || '上传中…') : '完成'"
          />

          <p v-if="errorMsg" class="upload-drawer__error">
            ⚠ {{ errorMsg }}
          </p>
        </div>

        <footer class="upload-drawer__foot">
          <button
            type="button"
            class="upload-drawer__btn"
            :disabled="uploading"
            @click="emit('close')"
          >
            取消
          </button>
          <button
            type="button"
            class="upload-drawer__btn upload-drawer__btn--primary"
            :disabled="!canSubmit || uploading"
            @click="onSubmit"
          >
            {{ uploading ? (uploadLabel || '上传中…') : '上传 (' + files.length + ')' }}
          </button>
        </footer>
      </aside>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import FileUploadInput from './FileUploadInput.vue'
import UploadProgress from './UploadProgress.vue'
import type { DatasetSelectItem } from '@/api/data-collect'

const props = defineProps<{
  open: boolean
  dataset: DatasetSelectItem | null
  uploading: boolean
  progress: number
  errorMsg?: string
  uploadLabel?: string
}>()

const emit = defineEmits<{
  close: []
  submit: [payload: { dataset_id: string; files: File[] }]
}>()

const files = ref<File[]>([])

watch(
  () => props.open,
  (v) => {
    if (v) {
      files.value = []
    }
  },
)

const canSubmit = computed(
  () => props.dataset !== null && files.value.length > 0,
)

function onFilesSelected(list: File[]) {
  files.value = list
}

function onSubmit() {
  if (!canSubmit.value || !props.dataset) return
  emit('submit', { dataset_id: props.dataset.id, files: [...files.value] })
}

function truncate(s: string, max: number): string {
  if (!s) return ''
  return s.length > max ? s.slice(0, max) + '…' : s
}
</script>

<style scoped>
.upload-drawer {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: flex;
  justify-content: flex-end;
}

.upload-drawer__backdrop {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
}

.upload-drawer__panel {
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

.upload-drawer__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--sp-3);
  padding: var(--sp-5);
  border-bottom: 1px solid var(--hairline);
}

.upload-drawer__head-meta {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--sp-1);
}

.upload-drawer__eyebrow {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--accent);
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.upload-drawer__title {
  font-family: var(--font-display);
  font-size: var(--text-lg);
  color: var(--ink);
  margin: 0;
  font-weight: 400;
}

.upload-drawer__sub {
  font-family: var(--font-sans);
  font-size: var(--text-sm);
  color: var(--ink-sub);
  margin: 0;
  line-height: 1.55;
  display: flex;
  align-items: center;
  gap: var(--sp-2);
}

.upload-drawer__ds-id {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--ink-mute);
}

.upload-drawer__close {
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
.upload-drawer__close:hover { color: var(--accent); border-color: var(--accent); }

.upload-drawer__body {
  flex: 1;
  overflow: auto;
  padding: var(--sp-5);
  display: flex;
  flex-direction: column;
  gap: var(--sp-4);
}

.upload-drawer__locked-ds {
  display: flex;
  flex-direction: column;
  gap: var(--sp-1);
  padding: var(--sp-2) var(--sp-3);
  border: 1px solid var(--hairline);
  border-radius: var(--radius-sm);
  background: var(--paper-sub);
}

.upload-drawer__field-label {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--ink-mute);
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.upload-drawer__locked-value {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  color: var(--ink);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.upload-drawer__error {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  color: var(--accent);
  border: 1px solid var(--accent);
  background: var(--accent-bg);
  padding: var(--sp-2) var(--sp-3);
  border-radius: var(--radius-sm);
  margin: 0;
}

.upload-drawer__foot {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--sp-2);
  padding: var(--sp-3) var(--sp-5);
  border-top: 1px solid var(--hairline);
  background: var(--paper-sub);
}

.upload-drawer__btn {
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
.upload-drawer__btn:hover:not(:disabled) {
  border-color: var(--accent);
  color: var(--accent);
}
.upload-drawer__btn:disabled { opacity: 0.4; cursor: not-allowed; }

.upload-drawer__btn--primary {
  background: var(--accent);
  border-color: var(--accent);
  color: var(--paper);
}
.upload-drawer__btn--primary:hover:not(:disabled) {
  background: var(--accent);
  color: var(--paper);
  filter: brightness(1.08);
}

@media (max-width: 720px) {
  .upload-drawer__panel { width: 100vw; }
}
</style>
