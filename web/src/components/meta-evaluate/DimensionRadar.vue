<!--
  DimensionRadar: EU MQA 5 维雷达图（纯 SVG）

  Props:
    discover, access, interop, reuse, context : number  (5 维实际得分)

  5 维满分：100/100/110/75/20
  渲染：五边形雷达 + 数据多边形 + 顶点标签 (F / A / I / R / C + 分数)
-->
<template>
  <div class="radar">
    <div class="radar__head">
      <span class="radar__title">5 维分项</span>
      <span class="radar__sub">实际 / 满分</span>
    </div>
    <svg
      class="radar__svg"
      :viewBox="`0 0 ${size} ${size}`"
      role="img"
      :aria-label="`雷达图：F ${discover}/${max.discover}, A ${access}/${max.access}, I ${interop}/${max.interop}, R ${reuse}/${max.reuse}, C ${context}/${max.context}`"
    >
      <!-- 5 圈网格 -->
      <g class="radar__grid">
        <polygon
          v-for="r in gridRings"
          :key="r"
          :points="polygonPoints(r)"
          fill="none"
          stroke="var(--hairline-strong)"
          stroke-width="1"
        />
      </g>

      <!-- 5 轴辐射线 -->
      <g class="radar__axis">
        <line
          v-for="(pt, i) in axisLines"
          :key="i"
          :x1="cx"
          :y1="cy"
          :x2="pt.x"
          :y2="pt.y"
          stroke="var(--hairline-strong)"
          stroke-width="1"
        />
      </g>

      <!-- 数据多边形 -->
      <polygon
        :points="dataPolygonPoints"
        fill="var(--accent)"
        fill-opacity="0.18"
        stroke="var(--accent)"
        stroke-width="2"
      />

      <!-- 5 顶点 + 标签 -->
      <g class="radar__points">
        <circle
          v-for="(pt, i) in dataPoints"
          :key="i"
          :cx="pt.x"
          :cy="pt.y"
          r="4"
          fill="var(--accent)"
          stroke="var(--paper)"
          stroke-width="2"
        />
      </g>

      <g class="radar__labels">
        <text
          v-for="(lb, i) in labels"
          :key="i"
          :x="lb.x"
          :y="lb.y"
          :text-anchor="lb.anchor"
          :dy="lb.dy"
          font-family="var(--font-mono)"
          font-size="13"
          fill="var(--ink)"
        >
          {{ lb.code }} · {{ lb.score }}/{{ lb.max }}
        </text>
      </g>
    </svg>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  discover: number
  access: number
  interop: number
  reuse: number
  context: number
}>()

const max = {
  discover: 100,
  access: 100,
  interop: 110,
  reuse: 75,
  context: 20,
}

const size = 320
const cx = size / 2
const cy = size / 2
const radius = 120
const labelOffset = 36

const gridRings = [0.25, 0.5, 0.75, 1.0]

// 5 顶点角度（顺时针：F = 顶部，A = 右上，I = 右下，R = 左下，C = 左上）
const angles = [
  -Math.PI / 2,                          // F (top)
  -Math.PI / 2 + (2 * Math.PI) / 5,      // A
  -Math.PI / 2 + (4 * Math.PI) / 5,      // I
  -Math.PI / 2 + (6 * Math.PI) / 5,      // R
  -Math.PI / 2 + (8 * Math.PI) / 5,      // C
]

function pointAt(angle: number, r: number): { x: number; y: number } {
  return {
    x: cx + r * Math.cos(angle),
    y: cy + r * Math.sin(angle),
  }
}

function polygonPoints(fraction: number): string {
  return angles
    .map((a) => {
      const pt = pointAt(a, radius * fraction)
      return `${pt.x},${pt.y}`
    })
    .join(' ')
}

const axisLines = computed(() =>
  angles.map((a) => pointAt(a, radius)),
)

const dataPoints = computed(() => {
  const scores = [
    props.discover, props.access, props.interop, props.reuse, props.context,
  ]
  return scores.map((s, i) => {
    const m = max[Object.keys(max)[i] as keyof typeof max] || 1
    const fraction = Math.max(0, Math.min(1, s / m))
    return pointAt(angles[i], radius * fraction)
  })
})

const dataPolygonPoints = computed(() =>
  dataPoints.value.map((p) => `${p.x},${p.y}`).join(' '),
)

const labels = computed(() => {
  const codes = ['F', 'A', 'I', 'R', 'C']
  const scores = [
    props.discover, props.access, props.interop, props.reuse, props.context,
  ]
  const maxKeys: (keyof typeof max)[] = ['discover', 'access', 'interop', 'reuse', 'context']
  return angles.map((a, i) => {
    const pt = pointAt(a, radius + labelOffset)
    let anchor: 'start' | 'middle' | 'end' = 'middle'
    const cos = Math.cos(a)
    if (cos > 0.2) anchor = 'start'
    else if (cos < -0.2) anchor = 'end'
    return {
      x: pt.x,
      y: pt.y,
      anchor,
      dy: 4,
      code: codes[i],
      score: scores[i],
      max: max[maxKeys[i]],
    }
  })
})
</script>

<style scoped>
.radar {
  border: 1px solid var(--hairline);
  border-radius: var(--radius-sm);
  background: var(--paper);
  padding: var(--sp-4);
}

.radar__head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: var(--sp-3);
  padding-bottom: var(--sp-2);
  border-bottom: 1px solid var(--hairline);
}

.radar__title {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--ink-mute);
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.radar__sub {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--ink-mute);
}

.radar__svg {
  width: 100%;
  height: auto;
  max-width: 320px;
  margin: 0 auto;
  display: block;
}
</style>