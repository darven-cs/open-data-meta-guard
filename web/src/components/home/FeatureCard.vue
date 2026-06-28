<template>
  <component
    :is="feature.ready ? 'router-link' : 'router-link'"
    :to="`/${feature.id}`"
    class="feature-card"
    :class="{ 'feature-card--ready': feature.ready }"
  >
    <!-- 顶部 meta 行:序号 + 角标 -->
    <div class="feature-card__meta">
      <span class="feature-card__index">{{ String(index).padStart(2, '0') }}</span>
      <span v-if="!feature.ready" class="feature-card__badge">In Preparation</span>
      <span v-else class="feature-card__badge feature-card__badge--ready">Available</span>
    </div>

    <!-- 图标:朱红 24×24,1.5px stroke,Swiss 几何 -->
    <svg
      class="feature-card__icon"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="1.5"
      stroke-linecap="square"
      stroke-linejoin="miter"
      aria-hidden="true"
    >
      <path :d="feature.iconPath" />
    </svg>

    <!-- 标题:Fraunces 衬线 -->
    <h3 class="feature-card__title">{{ feature.title }}</h3>

    <!-- 副标题:Fraunces italic 英文 -->
    <p class="feature-card__subtitle">{{ feature.subtitle }}</p>

    <!-- 描述:Inter Tight 正文 -->
    <p class="feature-card__description">{{ feature.description }}</p>

    <!-- 底部:箭头 + 行动点 -->
    <span class="feature-card__cta">
      {{ feature.ready ? 'Open agent' : 'View detail' }}
      <span class="feature-card__arrow" aria-hidden="true">→</span>
    </span>
  </component>
</template>

<script setup lang="ts">
import type { Feature } from '@/data/features'

defineProps<{
  feature: Feature
  index: number
}>()
</script>

<style scoped>
.feature-card {
  /* 卡片容器 */
  position: relative;
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
  padding: var(--sp-5);
  border: 1px solid var(--hairline);
  border-radius: var(--radius-md);
  background: var(--paper);
  color: inherit;
  text-decoration: none;
  /* 瑞士风硬切,无阴影 */
  transition:
    border-color 0.18s ease,
    background-color 0.18s ease,
    transform 0.18s ease;
  min-height: 220px;
  cursor: pointer;
}

/* hover:边框转油墨黑 + 整体微抬 1px */
.feature-card:hover {
  border-color: var(--ink);
  transform: translateY(-1px);
}

/* 顶部 meta 行 */
.feature-card__meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--ink-mute);
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.feature-card__index {
  font-variant-numeric: tabular-nums;
}

/* 角标:未就绪 = 油墨 mute 小色块;已就绪 = 朱红实色 */
.feature-card__badge {
  display: inline-block;
  padding: 2px var(--sp-2);
  font-family: var(--font-sans);
  font-size: var(--text-xs);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  border-radius: var(--radius-sm);
  background: var(--paper-sub);
  color: var(--ink-mute);
  border: 1px solid var(--hairline);
}

.feature-card__badge--ready {
  background: var(--accent);
  color: var(--paper);
  border-color: var(--accent);
}

/* 图标:朱红 */
.feature-card__icon {
  color: var(--accent);
  flex-shrink: 0;
  margin-top: var(--sp-1);
}

/* 标题:Fraunces 衬线 */
.feature-card__title {
  font-family: var(--font-display);
  font-size: var(--text-lg);
  font-weight: 400;
  color: var(--ink);
  margin: 0;
  letter-spacing: -0.01em;
  /* hover 时朱红下划线(用 underline + decoration-color 控制颜色) */
  text-decoration: underline;
  text-decoration-color: transparent;
  text-decoration-thickness: 1.5px;
  text-underline-offset: 4px;
  transition: text-decoration-color 0.18s ease;
}
.feature-card:hover .feature-card__title {
  text-decoration-color: var(--accent);
}

/* 副标题:Fraunces italic */
.feature-card__subtitle {
  font-family: var(--font-display);
  font-style: italic;
  font-size: var(--text-sm);
  color: var(--ink-mute);
  margin: 0;
  line-height: 1.4;
}

/* 描述:Inter Tight 正文 */
.feature-card__description {
  font-family: var(--font-sans);
  font-size: var(--text-base);
  color: var(--ink-sub);
  line-height: 1.55;
  margin: 0;
  /* 描述占满剩余空间,让 CTA 贴底 */
  flex: 1;
}

/* 底部 CTA */
.feature-card__cta {
  display: inline-flex;
  align-items: center;
  gap: var(--sp-2);
  font-family: var(--font-sans);
  font-size: var(--text-sm);
  color: var(--ink);
  margin-top: var(--sp-2);
  border-top: 1px solid var(--hairline);
  padding-top: var(--sp-3);
  letter-spacing: 0.01em;
}

.feature-card__arrow {
  color: var(--accent);
  font-family: var(--font-mono);
  transition: transform 0.18s ease;
}
.feature-card:hover .feature-card__arrow {
  transform: translateX(3px);
}

/* ready 卡片:hover 时 CTA 文字变朱红 */
.feature-card--ready .feature-card__cta {
  color: var(--accent);
}

/* 全局 focus-visible 由 base.css 提供:朱红 outline 2px */
</style>
