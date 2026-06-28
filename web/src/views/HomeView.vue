<!--
  HomeView: 总览页（v2.0 简化版）
  - 复用 AdminLayout 提供的导航 + 顶栏
  - 仅 2 区块:欢迎语 + 5 个 FeatureCard 网格
  - 不带批次 / 系统状态等 Dashboard 元素（v2.0 Phase 0 占位，不查 API）
-->
<template>
  <div class="home-view">
    <!-- 1. 欢迎区 -->
    <section class="home-view__welcome">
      <p class="home-view__eyebrow">
        <span class="home-view__eyebrow-num">v2.0</span>
        <span class="home-view__eyebrow-sep" aria-hidden="true">/</span>
        <span class="home-view__eyebrow-mute">Phase 0 · Infrastructure</span>
      </p>
      <h1 class="home-view__title">开放数据元数据治理</h1>
      <p class="home-view__lead">
        采集 → 评估 → 上传 → 质量评估 → Chat —— 最短业务链上的统一平台。
      </p>
      <p class="home-view__lead-en">
        Open Data Metadata Governance — A unified platform for ingestion, evaluation, upload, quality, and conversation.
      </p>
    </section>

    <hr class="home-view__rule" />

    <!-- 2. 5 功能卡 -->
    <section class="home-view__section">
      <h2 class="home-view__section-title">功能模块</h2>
      <FeatureGrid :features="features" />
    </section>
  </div>
</template>

<script setup lang="ts">
import { FEATURES } from '@/data/features'
import FeatureGrid from '@/components/home/FeatureGrid.vue'

const features = FEATURES
</script>

<style scoped>
.home-view {
  display: flex;
  flex-direction: column;
  width: 100%;
  max-width: 1280px;
  margin: 0 auto;
  padding: var(--sp-6);
  box-sizing: border-box;
  gap: var(--sp-6);
}

.home-view__rule {
  margin: 0;
  border: none;
  border-top: 1px solid var(--hairline);
}

/* ─────────── 1. 欢迎区 ─────────── */
.home-view__welcome {
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
  padding-top: var(--sp-3);
}

.home-view__eyebrow {
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

.home-view__eyebrow-num {
  color: var(--ink);
}

.home-view__eyebrow-sep {
  color: var(--hairline-strong);
}

.home-view__eyebrow-mute {
  color: var(--accent);
  border: 1px solid var(--accent-border);
  background: var(--accent-bg);
  padding: 2px var(--sp-2);
  border-radius: var(--radius-sm);
}

.home-view__title {
  font-family: var(--font-display);
  font-size: var(--text-xl);
  font-weight: 400;
  color: var(--ink);
  letter-spacing: -0.02em;
  margin: 0;
  line-height: 1.15;
}

.home-view__lead {
  font-family: var(--font-sans);
  font-size: var(--text-md);
  color: var(--ink-sub);
  margin: 0;
  line-height: 1.55;
}

.home-view__lead-en {
  font-family: var(--font-display);
  font-style: italic;
  font-size: var(--text-sm);
  color: var(--ink-mute);
  margin: 0;
  line-height: 1.55;
}

/* ─────────── 2. 功能区 ─────────── */
.home-view__section {
  display: flex;
  flex-direction: column;
  gap: var(--sp-4);
  padding: var(--sp-2) 0;
}

.home-view__section-title {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--ink-mute);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  margin: 0;
}

/* ─────────── 响应式 ─────────── */
@media (max-width: 720px) {
  .home-view {
    padding: var(--sp-4);
  }
}
</style>
