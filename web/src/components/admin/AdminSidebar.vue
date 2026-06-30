<!--
  AdminSidebar: 管理后台侧栏导航
  - v2.0 调整为 5 功能入口(采集 2 + 评估 2 + 数据小D)
  - 采集:元数据采集 + 数据采集
  - 评估:元数据评估 + 数据质量评估
  - 数据小D:特殊 ⤢ 角标,全屏模式提示
  - active 项朱红左竖线 + 朱红文字
  - inject 'adminDrawer' 控制抽屉状态
-->
<template>
  <nav class="admin-sidebar" :class="{ 'admin-sidebar--open': drawerOpen }">
    <!-- 顶部 brand 块 -->
    <div class="admin-sidebar__brand">
      <span class="admin-sidebar__brand-name">open-data-meta-guard</span>
      <span class="admin-sidebar__brand-tag">开放数据元数据治理</span>
    </div>

    <hr class="admin-sidebar__rule" />

    <!-- 分组:采集 -->
    <div class="admin-sidebar__group">
      <p class="admin-sidebar__group-label">采集</p>
      <RouterLink
        v-for="f in collectGroup"
        :key="f.id"
        :to="`/${f.id}`"
        class="admin-sidebar__item"
        :class="{ 'admin-sidebar__item--active': isActive(f.id) }"
        :aria-current="isActive(f.id) ? 'page' : undefined"
      >
        <svg
          class="admin-sidebar__icon"
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.5"
          stroke-linecap="square"
          stroke-linejoin="miter"
          aria-hidden="true"
        >
          <path :d="f.iconPath" />
        </svg>
        <span class="admin-sidebar__item-text">
          <span class="admin-sidebar__item-cn">{{ f.title }}</span>
          <span class="admin-sidebar__item-en">{{ f.subtitle }}</span>
        </span>
      </RouterLink>
    </div>

    <!-- 分组:评估 -->
    <div class="admin-sidebar__group">
      <p class="admin-sidebar__group-label">评估</p>
      <RouterLink
        v-for="f in evaluateGroup"
        :key="f.id"
        :to="`/${f.id}`"
        class="admin-sidebar__item"
        :class="{ 'admin-sidebar__item--active': isActive(f.id) }"
        :aria-current="isActive(f.id) ? 'page' : undefined"
      >
        <svg
          class="admin-sidebar__icon"
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.5"
          stroke-linecap="square"
          stroke-linejoin="miter"
          aria-hidden="true"
        >
          <path :d="f.iconPath" />
        </svg>
        <span class="admin-sidebar__item-text">
          <span class="admin-sidebar__item-cn">{{ f.title }}</span>
          <span class="admin-sidebar__item-en">{{ f.subtitle }}</span>
        </span>
      </RouterLink>
    </div>

    <div class="admin-sidebar__spacer" />

    <!-- 底部:数据小D(特殊处理) -->
    <div class="admin-sidebar__footer">
      <RouterLink
        to="/chat"
        class="admin-sidebar__item admin-sidebar__item--chat"
        :class="{ 'admin-sidebar__item--active': isActive('chat') }"
        :aria-current="isActive('chat') ? 'page' : undefined"
      >
        <svg
          class="admin-sidebar__icon"
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.5"
          stroke-linecap="square"
          stroke-linejoin="miter"
          aria-hidden="true"
        >
          <path :d="chatFeature.iconPath" />
        </svg>
        <span class="admin-sidebar__item-text">
          <span class="admin-sidebar__item-cn">{{ chatFeature.title }}</span>
          <span class="admin-sidebar__item-en">{{ chatFeature.subtitle }}</span>
        </span>
        <!-- ⤢ 角标,提示全屏模式 -->
        <svg
          class="admin-sidebar__expand-hint"
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.5"
          aria-hidden="true"
        >
          <path d="M4 8V4h4M20 8V4h-4M4 16v4h4M20 16v4h-4" />
        </svg>
      </RouterLink>
    </div>
  </nav>
</template>

<script setup lang="ts">
import { computed, inject } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import { FEATURES } from '@/data/features'

const route = useRoute()

// ───────── 数据分组 ─────────
// v2.0:采集 = meta-collect + data-collect,评估 = meta-evaluate + data-quality
const collectGroup = FEATURES.filter((f) =>
  ['meta-collect', 'data-collect'].includes(f.id),
)
const evaluateGroup = FEATURES.filter((f) =>
  ['meta-evaluate', 'data-quality', 'kg'].includes(f.id),
)
const chatFeature = FEATURES.find((f) => f.id === 'chat')!

// ───────── active 判定 ─────────
function isActive(id: string) {
  return route.name === id
}

// ───────── 抽屉控制(inject) ─────────
interface DrawerCtx {
  drawerOpen: import('vue').Ref<boolean>
  openDrawer: () => void
  closeDrawer: () => void
  toggleDrawer: () => void
}
const drawerCtx = inject<DrawerCtx | null>('adminDrawer', null)
const drawerOpen = computed(() => drawerCtx?.drawerOpen.value ?? false)
</script>

<style scoped>
.admin-sidebar {
  display: flex;
  flex-direction: column;
  background: var(--paper-sub);
  border-right: 1px solid var(--hairline);
  overflow-y: auto;
  height: 100%;
  box-sizing: border-box;
  padding: var(--sp-4) 0;
}

/* brand 块 */
.admin-sidebar__brand {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: var(--sp-2) var(--sp-5) var(--sp-4);
}
.admin-sidebar__brand-name {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  color: var(--ink);
  letter-spacing: 0;
}
.admin-sidebar__brand-tag {
  font-family: var(--font-display);
  font-style: italic;
  font-size: var(--text-xs);
  color: var(--ink-mute);
  letter-spacing: 0.02em;
}

.admin-sidebar__rule {
  margin: 0 var(--sp-5) var(--sp-3);
  border: none;
  border-top: 1px solid var(--hairline);
}

/* 分组 */
.admin-sidebar__group {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 0 var(--sp-3);
  margin-bottom: var(--sp-3);
}
.admin-sidebar__group-label {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--ink-mute);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  margin: 0 0 var(--sp-1);
  padding: 0 var(--sp-2);
}

.admin-sidebar__item {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  padding: var(--sp-2) var(--sp-3);
  border-radius: var(--radius-sm);
  text-decoration: none;
  color: var(--ink-mute);
  transition: color 0.12s, background 0.12s;
  border-left: 3px solid transparent;
  margin-left: -3px;
}

.admin-sidebar__item:hover {
  color: var(--ink);
  background: var(--paper);
}

.admin-sidebar__item--active {
  color: var(--accent);
  background: var(--paper);
  border-left-color: var(--accent);
}

.admin-sidebar__icon {
  flex-shrink: 0;
  color: currentColor;
}

.admin-sidebar__item-text {
  display: flex;
  flex-direction: column;
  gap: 0;
  min-width: 0;
}

.admin-sidebar__item-cn {
  font-family: var(--font-display);
  font-size: var(--text-base);
  line-height: 1.2;
  font-weight: 400;
}

.admin-sidebar__item-en {
  font-family: var(--font-display);
  font-style: italic;
  font-size: var(--text-xs);
  color: var(--ink-mute);
  line-height: 1.3;
  letter-spacing: 0.01em;
}

.admin-sidebar__item--active .admin-sidebar__item-en {
  color: var(--ink-mute);
  opacity: 0.85;
}

/* spacer */
.admin-sidebar__spacer {
  flex: 1;
}

/* footer */
.admin-sidebar__footer {
  padding: 0 var(--sp-3) var(--sp-2);
  border-top: 1px solid var(--hairline);
  padding-top: var(--sp-3);
  margin-top: var(--sp-3);
}

.admin-sidebar__item--chat {
  position: relative;
}

.admin-sidebar__expand-hint {
  flex-shrink: 0;
  color: var(--ink-mute);
  margin-left: auto;
  opacity: 0.6;
  transition: opacity 0.12s, color 0.12s;
}

.admin-sidebar__item--chat:hover .admin-sidebar__expand-hint {
  opacity: 1;
  color: var(--accent);
}

.admin-sidebar__item--chat.admin-sidebar__item--active .admin-sidebar__expand-hint {
  opacity: 1;
  color: var(--accent);
}

/* 滚动条变细 */
.admin-sidebar::-webkit-scrollbar {
  width: 6px;
}

@media (prefers-reduced-motion: reduce) {
  .admin-sidebar__item { transition: none; }
  .admin-sidebar__expand-hint { transition: none; }
}
</style>