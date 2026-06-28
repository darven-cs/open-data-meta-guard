<!--
  AdminLayout: 管理后台布局壳
  - 纯布局壳,0 业务逻辑(不放 fetch / store mutation)
  - 桌面:240px sidebar 常驻 + 56px topbar + main scroll
  - 移动端 (<960px):sidebar 收为抽屉,topbar hamburger 唤出
  - provide 'adminDrawer' 给 AdminSidebar / AdminTopbar 控制抽屉
-->
<template>
  <div class="admin-layout">
    <AdminSidebar class="admin-layout__sidebar" :class="{ 'admin-layout__sidebar--open': drawerOpen }" />
    <AdminTopbar class="admin-layout__topbar" />
    <main class="admin-layout__main">
      <slot />
    </main>

    <!-- 移动端抽屉 backdrop -->
    <div
      v-if="drawerOpen"
      class="admin-layout__backdrop"
      @click="closeDrawer"
    />
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, provide, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import AdminSidebar from './AdminSidebar.vue'
import AdminTopbar from './AdminTopbar.vue'

const route = useRoute()

// ───────── 抽屉状态 ─────────
const drawerOpen = ref(false)

function openDrawer() {
  drawerOpen.value = true
}
function closeDrawer() {
  drawerOpen.value = false
}
function toggleDrawer() {
  drawerOpen.value = !drawerOpen.value
}

provide('adminDrawer', {
  drawerOpen,
  openDrawer,
  closeDrawer,
  toggleDrawer,
})

// ───────── 路由切换自动关抽屉 ─────────
watch(
  () => route.path,
  () => closeDrawer(),
)

// ───────── Esc 关闭抽屉 ─────────
function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape' && drawerOpen.value) {
    closeDrawer()
  }
}

// ───────── body scroll lock ─────────
watch(drawerOpen, (open) => {
  if (typeof document === 'undefined') return
  document.body.style.overflow = open ? 'hidden' : ''
})

onMounted(() => {
  if (typeof window !== 'undefined') {
    window.addEventListener('keydown', onKeydown)
  }
})

onBeforeUnmount(() => {
  if (typeof window !== 'undefined') {
    window.removeEventListener('keydown', onKeydown)
  }
  // 清理 body overflow
  if (typeof document !== 'undefined') {
    document.body.style.overflow = ''
  }
})
</script>

<style scoped>
.admin-layout {
  display: grid;
  grid-template-columns: var(--sidebar-width) 1fr;
  grid-template-rows: var(--topbar-height) 1fr;
  grid-template-areas:
    "sidebar topbar"
    "sidebar main";
  height: 100vh;             /* 锁死 */
  width: 100%;
  background: var(--paper);
  color: var(--ink);
}

.admin-layout__sidebar { grid-area: sidebar; }
.admin-layout__topbar  { grid-area: topbar; }

.admin-layout__main {
  grid-area: main;
  overflow-y: auto;        /* 关键:内部滚动 */
  min-height: 0;           /* 关键:grid 子项需要这个才能 scroll */
}

@media (max-width: 960px) {
  .admin-layout__sidebar {
    position: fixed;
    top: 0; left: 0; bottom: 0;
    width: 240px;
    z-index: var(--sidebar-z);
    transform: translateX(-100%);
    transition: transform 0.22s ease;
  }
  .admin-layout__sidebar--open {
    transform: translateX(0);
  }
  .admin-layout__backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.4);
    z-index: var(--backdrop-z);
  }
}

@media (prefers-reduced-motion: reduce) {
  .admin-layout__sidebar {
    transition: none;
  }
}
</style>