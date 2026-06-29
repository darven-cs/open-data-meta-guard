<!--
  FileUploadInput: 拖拽 + 点击选择文件

  Props:
    accept : string   — accept 字符串（默认 '.csv,.xlsx,.json'）
    hint   : string   — 提示文案

  Emits:
    file-selected : (file: File | null) — 选中 / 清空
-->
<template>
  <div
    class="file-upload-input"
    :class="{ 'file-upload-input--hover': hovering }"
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
      @change="onPick"
    />

    <div class="file-upload-input__inner">
      <p v-if="!current" class="file-upload-input__hint">
        {{ hint }}
      </p>
      <p v-else class="file-upload-input__current">
        <span class="file-upload-input__icon">📄</span>
        <span class="file-upload-input__name">{{ current.name }}</span>
        <button
          type="button"
          class="file-upload-input__clear"
          aria-label="清除"
          @click.stop="clear"
        >×</button>
      </p>
      <p class="file-upload-input__sub">
        支持 {{ accept }} · 最大 {{ maxMb }} MB
      </p>
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
  }>(),
  {
    accept: '.csv,.xlsx,.json',
    hint: '拖拽文件到此处，或点击选择',
    maxMb: 500,
  },
)
void props

const emit = defineEmits<{
  'file-selected': [file: File | null]
}>()

const inputEl = ref<HTMLInputElement | null>(null)
const hovering = ref(false)
const current = ref<File | null>(null)

function onEnter() {
  hovering.value = true
}

function onLeave() {
  hovering.value = false
}

function onDrop(e: DragEvent) {
  hovering.value = false
  const f = e.dataTransfer?.files?.[0]
  if (f) acceptFile(f)
}

function onPick(e: Event) {
  const target = e.target as HTMLInputElement
  const f = target.files?.[0]
  if (f) acceptFile(f)
}

function openPicker() {
  inputEl.value?.click()
}

function acceptFile(f: File) {
  current.value = f
  emit('file-selected', f)
}

function clear() {
  current.value = null
  if (inputEl.value) inputEl.value.value = ''
  emit('file-selected', null)
}
</script>

<style scoped>
.file-upload-input {
  position: relative;
  border: 1px dashed var(--hairline-strong);
  border-radius: var(--radius-sm);
  background: var(--paper-sub);
  padding: var(--sp-6) var(--sp-4);
  text-align: center;
  cursor: pointer;
  transition: border-color 0.12s, background 0.12s;
}
.file-upload-input:hover,
.file-upload-input--hover {
  border-color: var(--accent);
  background: var(--accent-bg);
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

.file-upload-input__current {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  color: var(--ink);
  margin: 0;
}

.file-upload-input__icon {
  font-size: var(--text-md);
}

.file-upload-input__name {
  max-width: 320px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-upload-input__clear {
  background: transparent;
  border: 1px solid var(--hairline-strong);
  border-radius: var(--radius-sm);
  width: 24px;
  height: 24px;
  line-height: 1;
  color: var(--ink-sub);
  cursor: pointer;
  font-size: var(--text-md);
}
.file-upload-input__clear:hover { color: var(--accent); border-color: var(--accent); }

.file-upload-input__sub {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--ink-mute);
  margin: 0;
  letter-spacing: 0.05em;
}
</style>