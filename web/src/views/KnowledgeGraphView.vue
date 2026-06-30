<!--
  KnowledgeGraphView: 知识图谱主视图（Phase 5）
  - 头部信息
  - 构建按钮 + 刷新
  - 实体类型过滤
  - D3 力导向图
  - 实体详情抽屉
-->
<template>
  <div class="kg-view">
    <!-- 头部 -->
    <header class="kg-view__head">
      <p class="kg-view__eyebrow">
        <span class="kg-view__eyebrow-tag">Phase 5</span>
        <span class="kg-view__eyebrow-sep">/</span>
        <span class="kg-view__eyebrow-mute">Knowledge Graph</span>
      </p>
      <h1 class="kg-view__title">知识图谱</h1>
    </header>

    <hr class="kg-view__rule" />

    <!-- 错误条 -->
    <p v-if="errorMsg" class="kg-view__error">
      ⚠ {{ errorMsg }}
      <button class="kg-view__error-close" @click="errorMsg = ''">×</button>
    </p>

    <!-- 工具栏 -->
    <div class="kg-view__toolbar">
      <button
        type="button"
        class="kg-view__btn"
        :disabled="building"
        @click="doBuild"
      >
        {{ building ? '构建中…' : '全量构建' }}
      </button>
      <button
        type="button"
        class="kg-view__btn"
        :disabled="loading"
        @click="refresh"
      >
        {{ loading ? '刷新中…' : '刷新' }}
      </button>
      <span v-if="buildResult" class="kg-view__build-info">
        实体 {{ buildResult.entities_upserted }} / 关系 {{ buildResult.relationships_created }} /
        相似 {{ buildResult.similar_edges }}
      </span>
    </div>

    <!-- 实体类型过滤 -->
    <GraphControls v-model:active-types="activeTypes" />

    <!-- 图区 -->
    <div class="kg-view__canvas-wrap">
      <GraphCanvas
        :nodes="filteredNodes"
        :edges="filteredEdges"
        :loading="loading"
        @node-click="onNodeClick"
      />
    </div>

    <!-- 实体详情抽屉 -->
    <EntityDrawer
      :open="drawerOpen"
      :entity="drawerEntity"
      :loading="drawerLoading"
      @close="closeDrawer"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  buildGraph as apiBuildGraph,
  getGraph as apiGetGraph,
  getEntityDetail as apiGetEntityDetail,
  type GraphNode,
  type GraphEdge,
  type KgBuildResult,
  type EntityDetail,
} from '@/api/kg'
import GraphCanvas from '@/components/kg/GraphCanvas.vue'
import GraphControls from '@/components/kg/GraphControls.vue'
import EntityDrawer from '@/components/kg/EntityDrawer.vue'

// ───────── 状态 ─────────
const loading = ref(false)
const building = ref(false)
const errorMsg = ref('')

const allNodes = ref<GraphNode[]>([])
const allEdges = ref<GraphEdge[]>([])
const activeTypes = ref<string[]>(['Publisher', 'Theme', 'Keyword', 'Format'])
const buildResult = ref<KgBuildResult | null>(null)

// 过滤节点
const filteredNodes = computed(() => {
  const types = new Set(activeTypes.value)
  // 节点：保留 Dataset 以及符合 activeTypes 类型的实体
  return allNodes.value.filter(
    (n) => n.type === 'Dataset' || types.has(n.type),
  )
})

// 过滤边：只保留两端节点都在 filteredNodes 中的边
const filteredEdges = computed(() => {
  const nodeIds = new Set(filteredNodes.value.map((n) => n.id))
  return allEdges.value.filter(
    (e) => nodeIds.has(e.source) && nodeIds.has(e.target),
  )
})

// ───────── 抽屉状态 ─────────
const drawerOpen = ref(false)
const drawerEntity = ref<EntityDetail | null>(null)
const drawerLoading = ref(false)

async function onNodeClick(id: string) {
  // 如果点击的是 Dataset 节点，不打开详情
  const node = allNodes.value.find((n) => n.id === id)
  if (!node || node.type === 'Dataset') return

  drawerOpen.value = true
  drawerEntity.value = null
  drawerLoading.value = true
  try {
    drawerEntity.value = await apiGetEntityDetail(id)
  } catch (e) {
    errorMsg.value = (e as Error).message
    drawerOpen.value = false
  } finally {
    drawerLoading.value = false
  }
}

function closeDrawer() {
  drawerOpen.value = false
  drawerEntity.value = null
}

// ───────── 操作 ─────────
async function doBuild() {
  if (building.value) return
  building.value = true
  errorMsg.value = ''
  buildResult.value = null
  try {
    buildResult.value = await apiBuildGraph()
    await refresh()
  } catch (e) {
    errorMsg.value = (e as Error).message
  } finally {
    building.value = false
  }
}

async function refresh() {
  loading.value = true
  errorMsg.value = ''
  try {
    const data = await apiGetGraph()
    allNodes.value = data.nodes
    allEdges.value = data.edges
  } catch (e) {
    errorMsg.value = (e as Error).message
  } finally {
    loading.value = false
  }
}

// ───────── 初始 ─────────
onMounted(() => {
  void refresh()
})
</script>

<style scoped>
.kg-view {
  display: flex;
  flex-direction: column;
  width: 100%;
  max-width: 1280px;
  margin: 0 auto;
  padding: var(--sp-6);
  box-sizing: border-box;
  gap: var(--sp-3);
}

.kg-view__head {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
}

.kg-view__eyebrow {
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

.kg-view__eyebrow-tag {
  color: var(--accent);
  border: 1px solid var(--accent-border);
  background: var(--accent-bg);
  padding: 2px var(--sp-2);
  border-radius: var(--radius-sm);
}
.kg-view__eyebrow-sep { color: var(--hairline-strong); }
.kg-view__eyebrow-mute { color: var(--ink-mute); }

.kg-view__title {
  font-family: var(--font-display);
  font-size: var(--text-xl);
  font-weight: 400;
  color: var(--ink);
  margin: 0;
  letter-spacing: -0.02em;
}

.kg-view__rule {
  margin: 0;
  border: none;
  border-top: 1px solid var(--hairline);
}

.kg-view__toolbar {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  flex-wrap: wrap;
}

.kg-view__btn {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  letter-spacing: 0.05em;
  text-transform: uppercase;
  padding: var(--sp-2) var(--sp-4);
  border: 1px solid var(--hairline-strong);
  background: var(--paper);
  color: var(--ink);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: border-color 0.12s, color 0.12s;
}
.kg-view__btn:hover:not(:disabled) {
  border-color: var(--accent);
  color: var(--accent);
}
.kg-view__btn:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 1px;
}
.kg-view__btn:disabled { opacity: 0.4; cursor: not-allowed; }

.kg-view__build-info {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--ink-mute);
  margin-left: auto;
}

.kg-view__error {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  color: var(--accent);
  border: 1px solid var(--accent);
  background: var(--accent-bg);
  padding: var(--sp-2) var(--sp-3);
  border-radius: var(--radius-sm);
  margin: 0;
}

.kg-view__error-close {
  margin-left: auto;
  background: transparent;
  border: none;
  color: var(--accent);
  font-size: var(--text-md);
  cursor: pointer;
  padding: 0 var(--sp-2);
}

.kg-view__canvas-wrap {
  flex: 1;
  min-height: 500px;
}
</style>
