<!--
  UrlInput: URL 多行输入（每行一个 URL）

  Props:
    modelValue : string   — 双向绑定的 textarea 内容
    placeholder: string   — 占位符文本
    max        : number   — 允许的最大 URL 数（> max 时禁用提交）

  Emits:
    update:modelValue : (v: string)
    submit            : ()       — 按下「提交」按钮（由父组件触发 ingest）
-->
<template>
  <div class="url-input">
    <label class="url-input__label">
      <span class="url-input__label-text">数据源 URL（每行一个，最多 {{ max }} 条）</span>
      <span class="url-input__label-count">
        {{ urlCount }} / {{ max }}
      </span>
    </label>

    <textarea
      class="url-input__textarea"
      :value="modelValue"
      :placeholder="placeholder"
      :rows="rows"
      spellcheck="false"
      @input="onInput"
    />

    <p class="url-input__hint">
      仅支持 http / https 协议；提交后逐个抓取，约需 30~60 秒/条。
    </p>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    modelValue: string
    placeholder?: string
    max?: number
    rows?: number
  }>(),
  {
    placeholder: 'https://data.example.gov.cn/dataset/xxx\nhttps://data.example.gov.cn/dataset/yyy',
    max: 50,
    rows: 8,
  },
)

const emit = defineEmits<{
  'update:modelValue': [v: string]
}>()

const urlCount = computed(() => {
  return props.modelValue
    .split('\n')
    .map((s) => s.trim())
    .filter((s) => s.length > 0).length
})

function onInput(e: Event) {
  const t = e.target as HTMLTextAreaElement
  emit('update:modelValue', t.value)
}
</script>

<style scoped>
.url-input {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
}

.url-input__label {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--ink-mute);
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.url-input__label-count {
  color: var(--ink);
  font-feature-settings: 'tnum';
}

.url-input__textarea {
  width: 100%;
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  line-height: 1.6;
  padding: var(--sp-3);
  border: 1px solid var(--hairline-strong);
  border-radius: var(--radius-sm);
  background: var(--paper);
  color: var(--ink);
  resize: vertical;
  min-height: 140px;
  box-sizing: border-box;
}
.url-input__textarea:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 1px var(--accent);
}

.url-input__hint {
  font-family: var(--font-display);
  font-style: italic;
  font-size: var(--text-xs);
  color: var(--ink-mute);
  margin: 0;
}
</style>
