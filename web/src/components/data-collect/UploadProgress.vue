<!--
  UploadProgress: 受控进度条

  Props:
    progress : number  — 0..100
    label    : string  — 进度条上方文案（可选）
-->
<template>
  <div class="upload-progress">
    <div v-if="label" class="upload-progress__label">
      <span>{{ label }}</span>
      <span class="upload-progress__pct">{{ clamped }}%</span>
    </div>
    <div class="upload-progress__track" role="progressbar" :aria-valuenow="clamped" aria-valuemin="0" aria-valuemax="100">
      <div class="upload-progress__bar" :style="{ width: clamped + '%' }" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    progress: number
    label?: string
  }>(),
  { label: '' },
)

const clamped = computed(() => {
  const p = Number(props.progress) || 0
  if (p < 0) return 0
  if (p > 100) return 100
  return Math.round(p)
})
</script>

<style scoped>
.upload-progress {
  display: flex;
  flex-direction: column;
  gap: var(--sp-1);
  width: 100%;
}

.upload-progress__label {
  display: flex;
  justify-content: space-between;
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--ink-sub);
  letter-spacing: 0.05em;
}

.upload-progress__pct {
  color: var(--accent);
}

.upload-progress__track {
  position: relative;
  height: 6px;
  background: var(--paper-sub);
  border: 1px solid var(--hairline-strong);
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.upload-progress__bar {
  position: absolute;
  inset: 0 auto 0 0;
  background: var(--accent);
  transition: width 0.18s ease-out;
}
</style>