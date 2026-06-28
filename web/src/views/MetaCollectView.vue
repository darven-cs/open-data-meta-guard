<!--
  MetaCollectView: 元数据采集（Phase 0 占位）
  - Phase 1 替换为真实页面：URL 输入 → Playwright 抓取 → datasets 列表
-->
<template>
  <PlaceholderView feature-id="meta-collect" :phase-number="1" />
</template>

<script setup lang="ts">
import PlaceholderView from './PlaceholderView.vue'
</script>
