<!--
  FileUploadInput: 拖拽 + 点击选择文件（支持多文件）

  Props:
    accept   : string   — accept 字符串（默认 '.csv,.xlsx,.json'）
    hint     : string   — 提示文案
    maxMb    : number   — 单文件最大 MB
    multiple : boolean  — 是否允许多文件选择（默认 true）

  Emits:
    files-selected : (files: File[]) — 选中 / 清空
-->
<template>
  <div class="file-upload-input">
    <!-- 已选文件列表 -->
    <ul v-if="current.length > 0" class="file-upload-input__list">
      <li
        v-for="(f, idx) in current"
        :key="f.name + f.size + idx"
        class="file-upload-input__item"
      >
        <span class="file-upload-input__icon">📄</span>
        <span class="file-upload-input__name" :title="f.name">{{ f.name }}</span>
        <span class="file-upload-input__size">{{ fmtSize(f.size) }}</span>
        <button
          type="button"
          class="file-upload-input__remove"
          aria-label="移除文件"
          @click.stop="removeFile(idx)"
        >×</button>
      </li>
    </ul>

    <!-- 拖拽区域 -->
    <div
      class="file-upload-input__drop"
      :class="{
        'file-upload-input__drop--hover': hovering,
        'file-upload-input__drop--compact': current.length > 0,
      }"
      @dragenter.prevent="onEnter"
      @dragover.prevent="onEnter"
      @dragleave.prevent="onLeave"
      @drop.prevent="onDrop"
      @click="openPicker"
    >
      <input
        ref="inputEl"
        type="file"
        class="file-upload-input__native"
        :accept="accept"
        :multiple="multiple"
        @change="onPick"
      />

      <div class="file-upload-input__inner">
        <p class="file-upload-input__hint">
          <template v-if="current.length > 0">
            拖拽或点击继续添加文件
          </template>
          <template v-else>
            {{ hint }}
          </template>
        </p>
        <p class="file-upload-input__sub">
          支持 {{ accept }} · 最大 {{ maxMb }} MB
        </p>
      </div>
    </div>

    <!-- 文件总数 + 清空 -->
    <div v-if="current.length > 0" class="file-upload-input__summary">
      <span class="file-upload-input__count">已选 {{ current.length }} 个文件</span>
      <button
        type="button"
        class="file-upload-input__clear-all"
        @click.stop="clear"
      >清空</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const props = withDefaults(
  defineProps<{
    accept?: string
    hint?: string
    maxMb?: number
    multiple?: boolean
  }>(),
  {
    accept: '.csv,.xlsx,.json',
    hint: '拖拽文件到此处，或点击选择',
    maxMb: 500,
    multiple: true,
  },
)
void props

const emit = defineEmits<{
  'files-selected': [files: File[]]
}>()

const inputEl = ref<HTMLInputElement | null>(null)
const hovering = ref(false)
const current = ref<File[]>([])

function onEnter() {
  hovering.value = true
}

function onLeave() {
  hovering.value = false
}

function onDrop(e: DragEvent) {
  hovering.value = false
  const incoming = e.dataTransfer?.files
  if (!incoming) return
  addFiles(Array.from(incoming))
}

function onPick(e: Event) {
  const target = e.target as HTMLInputElement
  const incoming = target.files
  if (!incoming) return
  // 点击选择：替换已有列表（与原生 file input 行为一致）
  const files = Array.from(incoming)
  // 重置 input 以便再次选择同名文件
  if (inputEl.value) inputEl.value.value = ''
  current.value = files
  emit('files-selected', [...current.value])
}

function addFiles(incoming: File[]) {
  const deduped = incoming.filter(
    (f) => !current.value.some((e) => e.name === f.name && e.size === f.size),
  )
  if (deduped.length > 0) {
    current.value = [...current.value, ...deduped]
    emit('files-selected', [...current.value])
  }
}

function removeFile(idx: number) {
  current.value.splice(idx, 1)
  // 重置 input 以便再次选择同名文件
  if (inputEl.value) inputEl.value.value = ''
  emit('files-selected', [...current.value])
}

function clear() {
  current.value = []
  if (inputEl.value) inputEl.value.value = ''
  emit('files-selected', [])
}

function openPicker() {
  inputEl.value?.click()
}

function fmtSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(2) + ' MB'
}
</script>

<style scoped>
.file-upload-input {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
}

.file-upload-input__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 1px;
  border: 1px solid var(--hairline);
  border-radius: var(--radius-sm);
  overflow: hidden;
  max-height: 240px;
  overflow-y: auto;
}

.file-upload-input__item {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  padding: var(--sp-2) var(--sp-3);
  background: var(--paper-sub);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
}

.file-upload-input__item:nth-child(even) {
  background: var(--paper);
}

.file-upload-input__icon {
  flex-shrink: 0;
  font-size: var(--text-md);
}

.file-upload-input__name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--ink);
  min-width: 0;
}

.file-upload-input__size {
  flex-shrink: 0;
  color: var(--ink-mute);
  font-size: var(--text-xs);
}

.file-upload-input__remove {
  flex-shrink: 0;
  width: 20px;
  height: 20px;
  border: 1px solid var(--hairline-strong);
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--ink-sub);
  cursor: pointer;
  font-size: var(--text-sm);
  line-height: 1;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}
.file-upload-input__remove:hover {
  color: var(--accent);
  border-color: var(--accent);
}

.file-upload-input__drop {
  position: relative;
  border: 1px dashed var(--hairline-strong);
  border-radius: var(--radius-sm);
  background: var(--paper-sub);
  padding: var(--sp-6) var(--sp-4);
  text-align: center;
  cursor: pointer;
  transition: border-color 0.12s, background 0.12s;
}
.file-upload-input__drop:hover,
.file-upload-input__drop--hover {
  border-color: var(--accent);
  background: var(--accent-bg);
}

.file-upload-input__drop--compact {
  padding: var(--sp-3) var(--sp-4);
}

.file-upload-input__native {
  display: none;
}

.file-upload-input__inner {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
  align-items: center;
}

.file-upload-input__hint {
  font-family: var(--font-sans);
  font-size: var(--text-sm);
  color: var(--ink-sub);
  margin: 0;
}

.file-upload-input__sub {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--ink-mute);
  margin: 0;
  letter-spacing: 0.05em;
}

.file-upload-input__summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-2);
}

.file-upload-input__count {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--accent);
  letter-spacing: 0.05em;
}

.file-upload-input__clear-all {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--ink-mute);
  background: transparent;
  border: 1px solid var(--hairline-strong);
  border-radius: var(--radius-sm);
  padding: 2px var(--sp-2);
  cursor: pointer;
  letter-spacing: 0.05em;
}
.file-upload-input__clear-all:hover {
  color: var(--accent);
  border-color: var(--accent);
}
</style>
