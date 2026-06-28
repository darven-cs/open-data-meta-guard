<template>
  <div class="feature-grid">
    <FeatureCard
      v-for="(feature, i) in features"
      :key="feature.id"
      :feature="feature"
      :index="i + 1"
    />
  </div>
</template>

<script setup lang="ts">
import FeatureCard from './FeatureCard.vue'
import type { Feature } from '@/data/features'

defineProps<{
  features: Feature[]
}>()
</script>

<style scoped>
.feature-grid {
  /* 3 列 2 行,移动端 1 列 6 行(响应式兜底) */
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--sp-5);
  width: 100%;
}

@media (max-width: 960px) {
  .feature-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 640px) {
  .feature-grid {
    grid-template-columns: 1fr;
  }
}
</style>
