<!--
  GraphCanvas: D3 力导向图组件
  - 节点颜色按类型：Dataset=深色、Publisher=蓝色、Theme=绿色、Keyword=橙色、Format=紫色
  - 拖拽/缩放/标签显示
  - emit node-click 事件
-->
<template>
  <div ref="containerRef" class="graph-canvas" />
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as d3 from 'd3'
import type { SimulationNodeDatum, SimulationLinkDatum } from 'd3'
import type { GraphNode, GraphEdge } from '@/api/kg'

const props = defineProps<{
  nodes: GraphNode[]
  edges: GraphEdge[]
  loading: boolean
}>()

const emit = defineEmits<{
  'node-click': [id: string]
}>()

const containerRef = ref<HTMLDivElement | null>(null)

// 颜色映射
const TYPE_COLORS: Record<string, string> = {
  Dataset: '#2c3e50',
  Publisher: '#4a90d9',
  Theme: '#50b87a',
  Keyword: '#e68a2e',
  Format: '#9b59b6',
}

function getColor(type: string): string {
  return TYPE_COLORS[type] || '#95a5a6'
}

// D3 状态
let svg: d3.Selection<SVGSVGElement, unknown, null, undefined> | null = null
let simulation: d3.Simulation<SimDatum, SimLink> | null = null
let gLink: d3.Selection<SVGGElement, SimLink, SVGGElement, unknown> | null = null
let gNode: d3.Selection<SVGGElement, SimDatum, SVGGElement, unknown> | null = null

interface SimDatum extends SimulationNodeDatum {
  id: string
  type: string
  label: string
}

interface SimLink extends SimulationLinkDatum<SimDatum> {
  type: string
  weight: number
}

function initSvg() {
  if (!containerRef.value) return
  const rect = containerRef.value.getBoundingClientRect()
  const width = rect.width || 800
  const height = rect.height || 600

  svg = d3.select(containerRef.value)
    .append('svg')
    .attr('width', width)
    .attr('height', height)
    .attr('viewBox', [0, 0, width, height])
    .style('display', 'block')

  // 缩放
  const g = svg.append('g')
  svg.call(
    d3.zoom<SVGSVGElement, unknown>()
      .extent([[0, 0], [width, height]])
      .scaleExtent([0.1, 8])
      .on('zoom', (event) => {
        g.attr('transform', event.transform)
      }),
  )

  gLink = g.append('g').attr('class', 'links')
  gNode = g.append('g').attr('class', 'nodes')
}

function render() {
  if (!svg || !gNode || !gLink) return

  const simData: SimDatum[] = props.nodes.map((n) => ({
    id: n.id,
    type: n.type,
    label: n.label,
  }))

  const simLinks: SimLink[] = props.edges.map((e) => ({
    source: e.source,
    target: e.target,
    type: e.type,
    weight: e.weight,
  }))

  // 清理旧 simulation
  if (simulation) {
    simulation.stop()
  }

  // 创建新 simulation
  simulation = d3.forceSimulation<SimDatum>(simData)
    .force('link', d3.forceLink<SimDatum, SimLink>(simLinks).id((d) => d.id).distance(100))
    .force('charge', d3.forceManyBody().strength(-300))
    .force('center', d3.forceCenter(
      (svg!.node() as SVGSVGElement).clientWidth / 2,
      (svg!.node() as SVGSVGElement).clientHeight / 2,
    ))
    .force('collision', d3.forceCollide().radius(30))

  // 边
  gLink = (gLink as d3.Selection<SVGGElement, SimLink, SVGGElement, unknown>)
    .selectAll<SVGLineElement, SimLink>('line')
    .data(simLinks)
    .join('line')
    .attr('stroke', '#ccc')
    .attr('stroke-width', (d) => Math.max(0.5, d.weight * 2))
    .attr('stroke-opacity', 0.6)

  // 节点容器
  const nodeGroup = (gNode as d3.Selection<SVGGElement, SimDatum, SVGGElement, unknown>)
    .selectAll<SVGGElement, SimDatum>('g')
    .data(simData)
    .join('g')
    .attr('cursor', 'pointer')
    .call(
      d3.drag<SVGGElement, SimDatum>()
        .on('start', (event, d) => {
          if (!event.active && simulation) simulation.alphaTarget(0.3).restart()
          d.fx = d.x
          d.fy = d.y
        })
        .on('drag', (event, d) => {
          d.fx = event.x
          d.fy = event.y
        })
        .on('end', (event, d) => {
          if (!event.active && simulation) simulation.alphaTarget(0)
          d.fx = null
          d.fy = null
        }),
    )

  // 圆形
  nodeGroup.append('circle')
    .attr('r', (d) => (d.type === 'Dataset' ? 12 : 7))
    .attr('fill', (d) => getColor(d.type))
    .attr('stroke', '#fff')
    .attr('stroke-width', 1.5)

  // 标签（仅对非 Dataset 和 hover）
  nodeGroup.append('text')
    .text((d) => d.label)
    .attr('dx', (d) => (d.type === 'Dataset' ? 16 : 10))
    .attr('dy', 4)
    .attr('font-size', '10px')
    .attr('font-family', 'var(--font-mono), monospace')
    .attr('fill', 'var(--ink-sub)')
    .style('pointer-events', 'none')
    .style('opacity', 0.8)

  // 点击
  nodeGroup.on('click', (_event, d) => {
    emit('node-click', d.id)
  })

  // Simulation tick
  simulation.on('tick', () => {
    (gLink as d3.Selection<SVGGElement, SimLink, SVGGElement, unknown>)
      .selectAll('line')
      .attr('x1', (d) => (d.source as SimDatum).x ?? 0)
      .attr('y1', (d) => (d.source as SimDatum).y ?? 0)
      .attr('x2', (d) => (d.target as SimDatum).x ?? 0)
      .attr('y2', (d) => (d.target as SimDatum).y ?? 0)

    nodeGroup.attr('transform', (d) => `translate(${d.x ?? 0},${d.y ?? 0})`)
  })
}

function destroy() {
  if (simulation) {
    simulation.stop()
    simulation = null
  }
  if (svg) {
    svg.remove()
    svg = null
  }
  gLink = null
  gNode = null
}

onMounted(() => {
  initSvg()
})

onUnmounted(() => {
  destroy()
})

watch(
  () => [props.nodes, props.edges],
  () => {
    if (props.loading) return
    render()
  },
  { deep: true },
)
</script>

<style scoped>
.graph-canvas {
  width: 100%;
  height: 100%;
  min-height: 500px;
  background: var(--paper);
  border: 1px solid var(--hairline);
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.graph-canvas :deep(line) {
  stroke-linecap: round;
}
</style>
