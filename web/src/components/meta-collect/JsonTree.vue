<!--
  JsonTree: 极简 JSON 折叠树

  Props:
    data    : any         — 要渲染的数据
    depth   : number      — 内部递归用，初次调用不用传
    keyName : string      — 父级 key（仅递归时由父节点传入）

  设计：
  - 对象/数组节点可点击展开/折叠
  - 叶子节点直接显示
  - 字符串加双引号；null / 数字 / 布尔原样输出
-->
<template>
  <div class="json-tree">
    <!-- 空容器 -->
    <div v-if="isEmpty" class="json-tree__empty">∅</div>

    <!-- 数组 -->
    <ul v-else-if="isArray" class="json-tree__list">
      <li v-for="(item, idx) in (data as unknown[])" :key="idx" class="json-tree__row">
        <span class="json-tree__idx">[{{ idx }}]</span>
        <JsonTree :data="item" :depth="depth + 1" :key-name="String(idx)" />
      </li>
    </ul>

    <!-- 对象 -->
    <ul v-else-if="isObject" class="json-tree__list">
      <li v-for="(value, key) in (data as Record<string, unknown>)" :key="key" class="json-tree__row">
        <button
          v-if="isExpandable(value)"
          type="button"
          class="json-tree__caret"
          :class="{ 'json-tree__caret--open': openKeys.has(keyPath) }"
          @click="toggle(keyPath)"
        >
          {{ openKeys.has(keyPath) ? '▾' : '▸' }}
        </button>
        <span v-else class="json-tree__caret json-tree__caret--leaf">·</span>

        <span class="json-tree__key">"{{ key }}"</span>
        <span class="json-tree__sep">:</span>

        <span v-if="isExpandable(value) && !openKeys.has(keyPath)" class="json-tree__hint">
          {{ value && Array.isArray(value) ? `Array(${(value as unknown[]).length})` : `Object(${Object.keys(value as object).length})` }}
        </span>
        <JsonTree
          v-else-if="isExpandable(value)"
          :data="value"
          :depth="depth + 1"
          :key-name="key"
        />
        <span v-else class="json-tree__val" :class="valueClass(value)">
          {{ formatValue(value) }}
        </span>
      </li>
    </ul>

    <!-- 标量 -->
    <span v-else class="json-tree__val" :class="valueClass(data)">
      {{ formatValue(data) }}
    </span>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

const props = withDefaults(
  defineProps<{
    data: unknown
    depth?: number
    keyName?: string
  }>(),
  { depth: 0, keyName: '' },
)

const openKeys = ref<Set<string>>(new Set())

const keyPath = computed(() => {
  return props.keyName ? `${props.depth}:${props.keyName}` : `${props.depth}:root`
})

const isArray = computed(() => Array.isArray(props.data))
const isObject = computed(
  () => props.data !== null && typeof props.data === 'object' && !Array.isArray(props.data),
)
const isEmpty = computed(
  () =>
    props.data === null ||
    (typeof props.data === 'object' &&
      Object.keys(props.data as object).length === 0),
)

function isExpandable(v: unknown): boolean {
  return v !== null && typeof v === 'object'
}

function toggle(path: string) {
  if (openKeys.value.has(path)) {
    openKeys.value.delete(path)
  } else {
    openKeys.value.add(path)
  }
}

function formatValue(v: unknown): string {
  if (v === null) return 'null'
  if (typeof v === 'string') return JSON.stringify(v)
  if (typeof v === 'number' || typeof v === 'boolean') return String(v)
  return String(v)
}

function valueClass(v: unknown): string {
  if (v === null) return 'json-tree__val--null'
  if (typeof v === 'string') return 'json-tree__val--string'
  if (typeof v === 'number') return 'json-tree__val--number'
  if (typeof v === 'boolean') return 'json-tree__val--bool'
  return ''
}
</script>

<style scoped>
.json-tree {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  line-height: 1.7;
}

.json-tree__empty {
  color: var(--ink-mute);
  font-style: italic;
}

.json-tree__list {
  list-style: none;
  margin: 0;
  padding-left: var(--sp-4);
  border-left: 1px dashed var(--hairline);
}

.json-tree__row {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: var(--sp-1);
}

.json-tree__caret {
  display: inline-block;
  width: 14px;
  text-align: center;
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--accent);
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 0;
  line-height: 1;
}
.json-tree__caret--open { color: var(--accent); }
.json-tree__caret--leaf { color: var(--ink-mute); cursor: default; }

.json-tree__idx {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--ink-mute);
  margin-right: var(--sp-1);
}

.json-tree__key {
  color: var(--ink);
}

.json-tree__sep {
  color: var(--ink-mute);
  margin-right: var(--sp-1);
}

.json-tree__hint {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--ink-mute);
  font-style: italic;
}

.json-tree__val {
  word-break: break-word;
}
.json-tree__val--string { color: var(--success); }
.json-tree__val--number { color: var(--accent); }
.json-tree__val--bool   { color: var(--warning); }
.json-tree__val--null  { color: var(--ink-mute); font-style: italic; }
</style>
