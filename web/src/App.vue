<!--
  App.vue: 根
  - AdminLayout 条件包裹:route.meta.layout === 'admin' 时套壳
  - :key="route.path"(不是 fullPath)避免 query 切换触发组件重建
  - /chat 不加 meta.layout,保持 ChatLayout 原全屏行为

  v2.0 调整：复用 v1.0 的 AdminLayout 条件包裹机制，路由表改为 5 条。
-->
<template>
  <RouterView v-slot="{ Component, route }">
    <AdminLayout v-if="route.meta.layout === 'admin'">
      <component :is="Component" :key="route.path" />
    </AdminLayout>
    <component v-else :is="Component" :key="route.path" />
  </RouterView>
</template>

<script setup lang="ts">
import AdminLayout from '@/components/admin/AdminLayout.vue'
</script>
