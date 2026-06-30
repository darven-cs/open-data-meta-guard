<!--
  GraphControls: 图谱视图控制栏
  多选框控制显示哪些实体类型
-->
<template>
  <div class="graph-controls">
    <label
      v-for="opt in typeOptions"
      :key="opt.value"
      class="graph-controls__checkbox"
    >
      <input
        type="checkbox"
        :checked="activeTypes.includes(opt.value)"
        @change="toggleType(opt.value)"
      />
      <span
        class="graph-controls__dot"
        :style="{ background: opt.color }"
      />
      {{ opt.label }}
    </label>
  </div>
</template>

<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    activeTypes: string[]
  }>(),
  { activeTypes: () => ['Publisher', 'Theme', 'Keyword', 'Format'] },
)

const emit = defineEmits<{
  'update:activeTypes': [types: string[]]
}>()

const typeOptions = [
  { value: 'Publisher', label: '发布机构', color: '#4a90d9' },
  { value: 'Theme', label: '主题分类', color: '#50b87a' },
  { value: 'Keyword', label: '关键词', color: '#e68a2e' },
  { value: 'Format', label: '数据格式', color: '#9b59b6' },
]

function toggleType(value: string) {
  const current = [...props.activeTypes]
  const idx = current.indexOf(value)
  if (idx >= 0) {
    current.splice(idx, 1)
  } else {
    current.push(value)
  }
  emit('update:activeTypes', current)
}
</script>

<style scoped>
.graph-controls {
  display: flex;
  align-items: center;
  gap: var(--sp-4);
  padding: var(--sp-2) 0;
  flex-wrap: wrap;
}

.graph-controls__checkbox {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--ink-sub);
  cursor: pointer;
  user-select: none;
}

.graph-controls__dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.graph-controls__checkbox input[type='checkbox'] {
  accent-color: var(--accent);
}
</style>
