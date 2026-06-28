<!--
  AdminTopbar: 顶栏
  - 移动端 hamburger(唤出 / 关闭 sidebar 抽屉)
  - 中央:当前页标题(中文 + 英文斜体)
  - 右侧:版本号
-->
<template>
  <header class="admin-topbar">
    <!-- 移动端 hamburger -->
    <button
      class="admin-topbar__hamburger"
      type="button"
      :aria-expanded="drawerOpen"
      :aria-label="drawerOpen ? '关闭导航' : '打开导航'"
      @click="toggleDrawer"
    >
      <svg
        width="20"
        height="20"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="1.5"
        stroke-linecap="square"
        aria-hidden="true"
      >
        <path d="M4 7h16M4 12h16M4 17h16" />
      </svg>
    </button>

    <!-- 当前页标题(中央,靠左) -->
    <div class="admin-topbar__title">
      <span class="admin-topbar__title-cn">{{ currentTitle }}</span>
      <span class="admin-topbar__title-sep" aria-hidden="true">/</span>
      <span class="admin-topbar__title-en">{{ currentSubtitle }}</span>
    </div>

    <!-- 右侧版本号 -->
    <span class="admin-topbar__version">v2.0</span>
  </header>
</template>

<script setup lang="ts">
import { computed, inject } from 'vue'
import { useRoute } from 'vue-router'
import { FEATURES } from '@/data/features'

const route = useRoute()

// ───────── 当前页标题 ─────────
const currentTitle = computed(() => {
  if (route.name) {
    const f = FEATURES.find((x) => x.id === route.name)
    if (f) return f.title
  }
  return '总览'
})

const currentSubtitle = computed(() => {
  if (route.name) {
    const f = FEATURES.find((x) => x.id === route.name)
    if (f) return f.subtitle
  }
  return 'Dashboard'
})

// ───────── 抽屉控制(inject) ─────────
interface DrawerCtx {
  drawerOpen: import('vue').Ref<boolean>
  openDrawer: () => void
  closeDrawer: () => void
  toggleDrawer: () => void
}
const drawerCtx = inject<DrawerCtx | null>('adminDrawer', null)
const drawerOpen = computed(() => drawerCtx?.drawerOpen.value ?? false)
const toggleDrawer = () => drawerCtx?.toggleDrawer()
</script>

<style scoped>
.admin-topbar {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  padding: 0 var(--sp-6);
  background: var(--paper);
  border-bottom: 1px solid var(--hairline);
  height: var(--topbar-height);
  box-sizing: border-box;
}

/* hamburger:桌面隐藏 */
.admin-topbar__hamburger {
  display: none;
  background: transparent;
  border: 1px solid var(--hairline);
  border-radius: var(--radius-sm);
  padding: 6px;
  cursor: pointer;
  color: var(--ink);
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
}
.admin-topbar__hamburger:hover {
  color: var(--accent);
  border-color: var(--accent-border);
}

/* 标题 */
.admin-topbar__title {
  display: flex;
  align-items: baseline;
  gap: var(--sp-2);
  min-width: 0;
  flex: 1;
}
.admin-topbar__title-cn {
  font-family: var(--font-display);
  font-size: var(--text-md);
  font-weight: 400;
  color: var(--ink);
  letter-spacing: -0.01em;
}
.admin-topbar__title-sep {
  font-family: var(--font-display);
  font-weight: 300;
  color: var(--hairline-strong);
}
.admin-topbar__title-en {
  font-family: var(--font-display);
  font-style: italic;
  font-size: var(--text-sm);
  color: var(--ink-sub);
  letter-spacing: 0.01em;
}

/* 版本号 */
.admin-topbar__version {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--ink-mute);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  flex-shrink: 0;
}

@media (max-width: 960px) {
  .admin-topbar__hamburger {
    display: inline-flex;
  }
  .admin-topbar {
    padding: 0 var(--sp-4);
  }
}
</style>