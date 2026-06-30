<!--
  Pager: 通用分页器。统一使用项目已有 CSS 设计 token(沿用 List 组件同款视觉)。

  Props:
    page        : 当前页(1-based)
    size        : 每页条数
    total       : 匹配总数(后端 res.count),undefined 时不显示共几条但仍可翻页
    loading     : 加载中(禁用 Prev/Next 与 size 下拉)
    sizeOptions : 每页条数候选,默认 [10, 20, 50, 100]

  Emits:
    page-change : (page: number)
    size-change : (size: number)

  行为:
    - totalPages <= 1 且 total 未提供 → 整个组件隐藏(早期数据少时)
    - total 已提供且 <= 0 → 显示「共 0 条」但不显示分页按钮
    - 切换 size 不会自动调接口;由父组件拿到 size-change 后将 page 重置为 1 并刷新
-->
<template>
  <div v-if="visible" class="pager">
    <div class="pager__nav">
      <button
        type="button"
        class="pager__btn"
        :disabled="page <= 1 || loading"
        @click="emit('page-change', page - 1)"
      >
        ← 上一页
      </button>
      <span class="pager__info">{{ page }} / {{ totalPages }}</span>
      <button
        type="button"
        class="pager__btn"
        :disabled="page >= totalPages || loading"
        @click="emit('page-change', page + 1)"
      >
        下一页 →
      </button>
    </div>
    <div class="pager__meta">
      <span v-if="total !== undefined" class="pager__total">
        共 {{ total }} 条
      </span>
      <label class="pager__size">
        每页
        <select
          :value="size"
          :disabled="loading"
          @change="onSizeChange"
        >
          <option v-for="s in sizeOptions" :key="s" :value="s">
            {{ s }}
          </option>
        </select>
        条
      </label>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    page: number
    size: number
    total?: number
    loading?: boolean
    sizeOptions?: number[]
  }>(),
  {
    sizeOptions: () => [10, 20, 50, 100],
    loading: false,
  },
)

const emit = defineEmits<{
  'page-change': [page: number]
  'size-change': [size: number]
}>()

const totalPages = computed(() => {
  if (props.total === undefined) return 1
  return Math.max(1, Math.ceil(props.total / props.size))
})

const visible = computed(() => {
  if (props.total !== undefined && props.total > 0) return true
  return totalPages.value > 1
})

function onSizeChange(e: Event) {
  const v = Number((e.target as HTMLSelectElement).value)
  if (!Number.isNaN(v) && v > 0) {
    emit('size-change', v)
  }
}
</script>

<style scoped>
.pager {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: var(--sp-3);
  padding: var(--sp-3) 0;
  font-size: var(--text-xs);
}

.pager__nav {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
}

.pager__btn {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  padding: var(--sp-1) var(--sp-3);
  border: 1px solid var(--hairline-strong);
  background: var(--paper);
  color: var(--ink);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: border-color 0.12s, color 0.12s;
}
.pager__btn:hover:not(:disabled) {
  border-color: var(--accent);
  color: var(--accent);
}
.pager__btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.pager__btn:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 1px;
}

.pager__info {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--ink-mute);
  padding: 0 var(--sp-2);
}

.pager__meta {
  display: flex;
  align-items: center;
  gap: var(--sp-4);
  color: var(--ink-mute);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
}

.pager__total {
  white-space: nowrap;
}

.pager__size {
  display: inline-flex;
  align-items: center;
  gap: var(--sp-1);
  white-space: nowrap;
}

.pager__size select {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  padding: 1px var(--sp-1);
  margin: 0 var(--sp-1);
  border: 1px solid var(--hairline-strong);
  border-radius: var(--radius-sm);
  background: var(--paper);
  color: var(--ink);
  cursor: pointer;
}
.pager__size select:focus {
  outline: none;
  border-color: var(--accent);
}
</style>
