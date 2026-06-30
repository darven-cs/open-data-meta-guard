<!--
  EntityDrawer: 实体详情右侧抽屉
  Teleport to body，显示实体基本信息和关联数据集列表
-->
<template>
  <Teleport to="body">
    <Transition name="drawer">
      <div v-if="open" class="entity-drawer-overlay" @click.self="$emit('close')">
        <aside class="entity-drawer" role="dialog" aria-label="实体详情">
          <header class="entity-drawer__head">
            <span class="entity-drawer__type-tag">{{ entity?.type }}</span>
            <h2 class="entity-drawer__title">{{ entity?.name }}</h2>
            <button class="entity-drawer__close" @click="$emit('close')" aria-label="关闭">
              ×
            </button>
          </header>

          <div v-if="loading" class="entity-drawer__loading">加载中…</div>
          <div v-else-if="!entity" class="entity-drawer__empty">暂无数据</div>
          <div v-else class="entity-drawer__body">
            <section>
              <h3 class="entity-drawer__section-title">关联数据集 ({{ entity.related_datasets.length }})</h3>
              <div v-if="entity.related_datasets.length === 0" class="entity-drawer__empty">
                暂无关联数据集
              </div>
              <ul v-else class="entity-drawer__list">
                <li
                  v-for="ds in entity.related_datasets"
                  :key="ds.dataset_id"
                  class="entity-drawer__list-item"
                >
                  <div class="entity-drawer__ds-id">{{ ds.dataset_id.slice(0, 16) }}…</div>
                  <div class="entity-drawer__ds-meta">
                    <span class="entity-drawer__ds-rel">{{ ds.rel_type }}</span>
                    <span v-if="ds.confidence" class="entity-drawer__ds-conf">
                      置信度: {{ (ds.confidence * 100).toFixed(0) }}%
                    </span>
                  </div>
                </li>
              </ul>
            </section>
          </div>
        </aside>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import type { EntityDetail } from '@/api/kg'

defineProps<{
  open: boolean
  entity: EntityDetail | null
  loading: boolean
}>()

defineEmits<{
  close: []
}>()
</script>

<style scoped>
.entity-drawer-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.2);
  z-index: 1000;
  display: flex;
  justify-content: flex-end;
}

.entity-drawer {
  width: 400px;
  max-width: 90vw;
  height: 100%;
  background: var(--paper);
  border-left: 1px solid var(--hairline-strong);
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  box-shadow: -4px 0 12px rgba(0, 0, 0, 0.08);
}

.entity-drawer__head {
  display: flex;
  align-items: flex-start;
  gap: var(--sp-3);
  padding: var(--sp-5);
  border-bottom: 1px solid var(--hairline);
  flex-wrap: wrap;
}

.entity-drawer__type-tag {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--accent);
  border: 1px solid var(--accent-border);
  background: var(--accent-bg);
  padding: 2px var(--sp-2);
  border-radius: var(--radius-sm);
}

.entity-drawer__title {
  flex: 1;
  font-family: var(--font-display);
  font-size: var(--text-lg);
  font-weight: 400;
  color: var(--ink);
  margin: 0;
  min-width: 0;
  word-break: break-all;
}

.entity-drawer__close {
  background: none;
  border: none;
  font-size: 24px;
  color: var(--ink-mute);
  cursor: pointer;
  padding: 0;
  line-height: 1;
}
.entity-drawer__close:hover {
  color: var(--ink);
}

.entity-drawer__body {
  padding: var(--sp-5);
  flex: 1;
}

.entity-drawer__loading,
.entity-drawer__empty {
  padding: var(--sp-8);
  text-align: center;
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  color: var(--ink-mute);
}

.entity-drawer__section-title {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--ink-mute);
  margin: 0 0 var(--sp-3);
}

.entity-drawer__list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
}

.entity-drawer__list-item {
  padding: var(--sp-3);
  border: 1px solid var(--hairline);
  border-radius: var(--radius-sm);
  display: flex;
  flex-direction: column;
  gap: var(--sp-1);
}

.entity-drawer__ds-id {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--ink-sub);
}

.entity-drawer__ds-meta {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  font-size: var(--text-xs);
}

.entity-drawer__ds-rel {
  font-family: var(--font-mono);
  color: var(--accent);
}

.entity-drawer__ds-conf {
  color: var(--ink-mute);
}

/* Transition */
.drawer-enter-active,
.drawer-leave-active {
  transition: opacity 0.2s ease;
}
.drawer-enter-active .entity-drawer,
.drawer-leave-active .entity-drawer {
  transition: transform 0.2s ease;
}
.drawer-enter-from,
.drawer-leave-to {
  opacity: 0;
}
.drawer-enter-from .entity-drawer,
.drawer-leave-to .entity-drawer {
  transform: translateX(100%);
}
</style>
