<!--
  PlaceholderView: Phase 0 占位页通用组件
  - 由 4 个 Phase View（MetaCollect/MetaEvaluate/DataCollect/DataQuality）import 复用
  - 根据 featureId 显示对应功能的「建设中」状态
  - Phase 1-5 各自实现真实页面后，删除对应 View 中对本组件的引用
-->
<template>
  <div v-if="feature" class="placeholder">
    <header class="placeholder__header">
      <p class="placeholder__eyebrow">
        <span class="placeholder__eyebrow-num">{{ String(index).padStart(2, '0') }}</span>
        <span class="placeholder__eyebrow-sep" aria-hidden="true">/</span>
        <span class="placeholder__eyebrow-mute">Phase {{ phaseNumber }} · In Preparation</span>
      </p>
      <h1 class="placeholder__title">
        <span class="placeholder__title-cn">{{ feature.title }}</span>
        <span class="placeholder__title-sep" aria-hidden="true">/</span>
        <span class="placeholder__title-en">{{ feature.subtitle }}</span>
      </h1>
    </header>

    <hr class="placeholder__rule" />

    <main class="placeholder__body">
      <div class="placeholder__icon-wrap">
        <svg
          class="placeholder__icon"
          width="48"
          height="48"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.25"
          stroke-linecap="square"
          stroke-linejoin="miter"
          aria-hidden="true"
        >
          <path :d="feature.iconPath" />
        </svg>
      </div>

      <div class="placeholder__text">
        <p class="placeholder__description">{{ feature.description }}</p>

        <p class="placeholder__note">
          此功能将在 <strong>Phase {{ phaseNumber }}</strong> 落地。Phase 0（基础设施）已就绪。
          <router-link to="/chat" class="placeholder__note-link">
            试试「数据小D」 →
          </router-link>
        </p>
      </div>
    </main>

    <hr class="placeholder__rule" />

    <footer class="placeholder__foot">
      <span class="placeholder__foot-mute">
        Status: <span class="placeholder__foot-status">Pending</span>
      </span>
      <span class="placeholder__foot-mute">v2.0 · Phase 0</span>
    </footer>
  </div>

  <div v-else class="placeholder placeholder--missing">
    <p>未知功能页:<code>{{ featureId }}</code></p>
    <router-link to="/">返回首页</router-link>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { findFeature, FEATURES } from '@/data/features'

const props = defineProps<{
  featureId: string
  phaseNumber: number
}>()

const feature = computed(() => findFeature(props.featureId))

const index = computed(() => {
  const f = feature.value
  if (!f) return 0
  return FEATURES.findIndex((x) => x.id === f.id) + 1
})
</script>

<style scoped>
.placeholder {
  display: flex;
  flex-direction: column;
  width: 100%;
  padding: var(--sp-5) var(--sp-6);
  box-sizing: border-box;
  gap: var(--sp-5);
}

.placeholder__header {
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
  padding-top: var(--sp-2);
}

.placeholder__eyebrow {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--ink-mute);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  margin: 0;
}
.placeholder__eyebrow-num { color: var(--ink); }
.placeholder__eyebrow-sep { color: var(--hairline-strong); }
.placeholder__eyebrow-mute {
  color: var(--accent);
  border: 1px solid var(--accent-border);
  background: var(--accent-bg);
  padding: 2px var(--sp-2);
  border-radius: var(--radius-sm);
}

.placeholder__title {
  font-family: var(--font-display);
  font-size: var(--text-xl);
  font-weight: 400;
  color: var(--ink);
  letter-spacing: -0.02em;
  margin: 0;
  line-height: 1.2;
  display: flex;
  align-items: baseline;
  gap: var(--sp-3);
  flex-wrap: wrap;
}
.placeholder__title-cn { color: var(--ink); }
.placeholder__title-sep { color: var(--hairline-strong); font-weight: 300; }
.placeholder__title-en { font-style: italic; color: var(--ink-sub); }

.placeholder__rule {
  margin: 0;
  border: none;
  border-top: 1px solid var(--hairline);
}

.placeholder__body {
  flex: 1;
  display: grid;
  grid-template-columns: auto 1fr;
  gap: var(--sp-6);
  align-items: center;
  padding: var(--sp-7) 0;
}

.placeholder__icon-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 96px;
  height: 96px;
  border: 1px solid var(--hairline);
  border-radius: var(--radius-md);
  background: var(--paper);
  color: var(--accent);
}

.placeholder__icon { display: block; }

.placeholder__text {
  display: flex;
  flex-direction: column;
  gap: var(--sp-4);
  max-width: 640px;
}

.placeholder__description {
  font-family: var(--font-sans);
  font-size: var(--text-md);
  color: var(--ink-sub);
  line-height: 1.6;
  margin: 0;
}

.placeholder__note {
  font-family: var(--font-sans);
  font-size: var(--text-base);
  color: var(--ink-mute);
  margin: 0;
  padding-top: var(--sp-3);
  border-top: 1px solid var(--hairline);
}

.placeholder__note-link {
  color: var(--accent);
  text-decoration: underline;
  text-underline-offset: 3px;
  font-family: var(--font-sans);
  font-size: var(--text-base);
  margin-left: var(--sp-2);
}

.placeholder__foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: var(--sp-2);
  padding-bottom: var(--sp-3);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--ink-mute);
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.placeholder__foot-status {
  color: var(--accent);
  margin-left: var(--sp-1);
}

.placeholder--missing {
  align-items: center;
  justify-content: center;
  text-align: center;
}

@media (max-width: 720px) {
  .placeholder { padding: var(--sp-4); }
  .placeholder__body {
    grid-template-columns: 1fr;
    text-align: left;
    gap: var(--sp-4);
  }
  .placeholder__icon-wrap { width: 72px; height: 72px; }
  .placeholder__title { font-size: 24px; }
}
</style>
