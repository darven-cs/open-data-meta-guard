<!--
  QualityDialog: 数据质量评估详情 Drawer

  Props:
    open       : boolean
    quality    : QualityDetail | null
    download   : DownloadWithQualityItem | null  — 左侧数据文件信息
    loading    : boolean

  Emits:
    close

  布局：左右两栏
    左栏 → data_download 信息（file_name / format / size / dataset_id）
    右栏 → 评估结果（Summary 卡片 / Issues 列表 / Markdown 报告）
-->
<template>
  <Teleport to="body">
    <div v-if="open" class="quality-dialog" role="dialog" aria-modal="true">
      <div class="quality-dialog__backdrop" @click="emit('close')" />

      <aside class="quality-dialog__panel">
        <!-- 头部 -->
        <header class="quality-dialog__head">
          <div class="quality-dialog__head-meta">
            <span class="quality-dialog__eyebrow">Data Quality Assessment</span>
            <h2 class="quality-dialog__title">
              {{ download ? truncate(download.file_name, 40) : '评估详情' }}
            </h2>
            <p v-if="quality" class="quality-dialog__sub">
              <span class="quality-dialog__id">#{{ quality.id }}</span>
            </p>
          </div>
          <button
            type="button"
            class="quality-dialog__close"
            aria-label="关闭"
            @click="emit('close')"
          >×</button>
        </header>

        <!-- 主体 -->
        <div class="quality-dialog__main">
          <!-- 左栏：data_download 信息 -->
          <aside class="quality-dialog__side">
            <div class="quality-dialog__side-head">
              <span class="quality-dialog__eyebrow">Data Download</span>
              <button
                v-if="narrow"
                type="button"
                class="quality-dialog__side-toggle"
                @click="sideCollapsed = !sideCollapsed"
              >
                {{ sideCollapsed ? '展开' : '收起' }}
              </button>
            </div>
            <div v-if="!sideCollapsed" class="quality-dialog__side-body">
              <div v-if="download" class="quality-dialog__meta">
                <div class="quality-dialog__meta-row">
                  <span class="quality-dialog__meta-label">文件名</span>
                  <span class="quality-dialog__meta-value">{{ download.file_name }}</span>
                </div>
                <div class="quality-dialog__meta-row">
                  <span class="quality-dialog__meta-label">格式</span>
                  <span class="quality-dialog__badge quality-dialog__badge--format">
                    {{ download.file_format }}
                  </span>
                </div>
                <div class="quality-dialog__meta-row">
                  <span class="quality-dialog__meta-label">大小</span>
                  <span class="quality-dialog__meta-value">{{ formatSize(download.file_size) }}</span>
                </div>
                <div class="quality-dialog__meta-row">
                  <span class="quality-dialog__meta-label">SHA256</span>
                  <span class="quality-dialog__meta-value quality-dialog__meta-mono">
                    {{ truncate(download.file_sha256, 20) }}
                  </span>
                </div>
                <div class="quality-dialog__meta-row">
                  <span class="quality-dialog__meta-label">Dataset ID</span>
                  <span class="quality-dialog__meta-value quality-dialog__meta-mono" :title="download.dataset_id">
                    {{ truncate(download.dataset_id, 24) }}
                  </span>
                </div>
              </div>
              <div v-else class="quality-dialog__side-empty">无数据文件信息</div>
            </div>
          </aside>

          <!-- 右栏：评估结果 -->
          <section class="quality-dialog__content">
            <div v-if="loading" class="quality-dialog__loading">加载中…</div>
            <div v-else-if="!quality" class="quality-dialog__loading">暂无数据</div>
            <div v-else class="quality-dialog__body">
              <!-- Summary 卡片 -->
              <section class="quality-dialog__section">
                <h3 class="quality-dialog__section-title">统计摘要</h3>
                <div class="quality-dialog__cards">
                  <div
                    v-for="card in summaryCards"
                    :key="card.label"
                    class="quality-dialog__card"
                  >
                    <span class="quality-dialog__card-value">{{ card.value }}</span>
                    <span class="quality-dialog__card-label">{{ card.label }}</span>
                  </div>
                </div>
              </section>

              <!-- Issues 列表 -->
              <section class="quality-dialog__section">
                <h3 class="quality-dialog__section-title">
                  数据质量问题
                  <span v-if="structuralIssues.length > 0" class="quality-dialog__count">
                    {{ structuralIssues.length }}
                  </span>
                </h3>
                <div v-if="structuralIssues.length === 0" class="quality-dialog__no-issues">
                  未检测到明显的数据质量问题
                </div>
                <div v-else class="quality-dialog__issues">
                  <div
                    v-for="(issue, idx) in structuralIssues"
                    :key="idx"
                    class="quality-dialog__issue"
                    :class="`quality-dialog__issue--${issue.severity || 'info'}`"
                  >
                    <span class="quality-dialog__issue-badge">
                      {{ severityLabel(issue.severity as string) }}
                    </span>
                    <div class="quality-dialog__issue-body">
                      <span class="quality-dialog__issue-check">{{ issue.check }}</span>
                      <span class="quality-dialog__issue-detail">{{ issue.detail }}</span>
                    </div>
                  </div>
                </div>
              </section>

              <!-- 语义分析 -->
              <section v-if="hasSemantic" class="quality-dialog__section">
                <h3 class="quality-dialog__section-title">语义分析（LLM）</h3>

                <!-- 维度评分条 -->
                <div class="quality-dialog__dim-scores">
                  <div
                    v-for="dim in dimensionScores"
                    :key="dim.key"
                    class="quality-dialog__dim-row"
                  >
                    <span class="quality-dialog__dim-label">{{ dim.label }}</span>
                    <div class="quality-dialog__dim-bar-bg">
                      <div
                        class="quality-dialog__dim-bar"
                        :style="{ width: dim.score + '%' }"
                        :class="dimScoreClass(dim.score)"
                      />
                    </div>
                    <span class="quality-dialog__dim-value">{{ dim.score }}</span>
                  </div>
                  <div class="quality-dialog__dim-row quality-dialog__dim-row--total">
                    <span class="quality-dialog__dim-label">综合评分</span>
                    <div class="quality-dialog__dim-bar-bg">
                      <div
                        class="quality-dialog__dim-bar"
                        :style="{ width: overallScore + '%' }"
                        :class="dimScoreClass(overallScore)"
                      />
                    </div>
                    <span class="quality-dialog__dim-value">{{ overallScore }}</span>
                  </div>
                </div>

                <!-- 语义 Issues -->
                <div v-if="semanticIssues.length > 0" class="quality-dialog__issues">
                  <div
                    v-for="(issue, idx) in semanticIssues"
                    :key="idx"
                    class="quality-dialog__issue"
                    :class="`quality-dialog__issue--${issue.severity}`"
                  >
                    <span class="quality-dialog__issue-badge">
                      {{ severityLabel(issue.severity) }}
                    </span>
                    <div class="quality-dialog__issue-body">
                      <span class="quality-dialog__issue-check">
                        [{{ issue.category }}] {{ issue.dimension }}
                        <span v-if="issue.field" class="quality-dialog__issue-field">
                          @{{ issue.field }}
                        </span>
                      </span>
                      <span class="quality-dialog__issue-detail">{{ issue.description }}</span>
                      <span v-if="issue.suggestion" class="quality-dialog__issue-sug">
                        建议: {{ issue.suggestion }}
                      </span>
                    </div>
                  </div>
                </div>
              </section>

              <!-- Markdown 报告 -->
              <section class="quality-dialog__section">
                <h3 class="quality-dialog__section-title">Markdown 报告</h3>
                <div class="quality-dialog__md">
                  <MarkdownView :content="quality.evaluation_content" />
                </div>
              </section>
            </div>
          </section>
        </div>
      </aside>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import type { DownloadWithQualityItem, QualityDetail } from '@/api/data-quality'
import MarkdownView from '@/components/chat/MarkdownView.vue'

const props = defineProps<{
  open: boolean
  quality: QualityDetail | null
  download?: DownloadWithQualityItem | null
  loading?: boolean
}>()

const emit = defineEmits<{ close: [] }>()

// 窄屏检测
const NARROW_BREAKPOINT = 900
const narrow = ref(false)
let mq: MediaQueryList | null = null

function syncNarrow(e: MediaQueryListEvent | MediaQueryList) {
  narrow.value = e.matches
}

onMounted(() => {
  if (typeof window === 'undefined') return
  mq = window.matchMedia(`(max-width: ${NARROW_BREAKPOINT}px)`)
  syncNarrow(mq)
  mq.addEventListener('change', syncNarrow)
})
onBeforeUnmount(() => {
  if (mq) mq.removeEventListener('change', syncNarrow)
})

const sideCollapsed = ref(false)

const summaryCards = computed(() => {
  if (!props.quality?.summary) return []
  const s = props.quality.summary as Record<string, unknown>
  const cards: { label: string; value: string }[] = []
  const map: Record<string, string> = {
    n: '行数', p: '列数',
    p_missing: '缺失率', p_duplicates: '重复率',
    memory_size: '内存占用',
  }
  for (const [k, label] of Object.entries(map)) {
    if (s[k] !== undefined) {
      cards.push({ label, value: String(s[k]) })
    }
  }
  return cards
})

// 结构化 issues（不含 source=semantic）
const structuralIssues = computed(() => {
  if (!props.quality?.issues) return []
  return props.quality.issues.filter((i: Record<string, unknown>) => i.source !== 'semantic')
})

// 语义 issues（source=semantic）
const semanticIssues = computed(() => {
  if (!props.quality?.issues) return []
  return props.quality.issues
    .filter((i: Record<string, unknown>) => i.source === 'semantic')
    .map((i: Record<string, unknown>) => ({
      severity: (i.severity as string) || 'info',
      category: (i.category as string) || '',
      dimension: (i.dimension as string) || '',
      field: (i.field as string | null) || null,
      description: (i.detail as string) || '',
      suggestion: (i.suggestion as string) || '',
    }))
})

// 是否有语义评估结果
const hasSemantic = computed(() => {
  if (!props.quality?.summary) return false
  const s = props.quality.summary as Record<string, unknown>
  return typeof s.overall_score === 'number'
})

// 8 维度评分
const DIMENSION_LABELS: Record<string, string> = {
  completeness_score: '完整性',
  consistency_score: '一致性',
  accuracy_score: '准确性',
  timeliness_score: '时效性',
  uniqueness_score: '唯一性',
  normativity_score: '规范性',
  openness_score: '开放性',
  security_score: '安全性',
}

const dimensionScores = computed(() => {
  if (!props.quality?.summary) return []
  const s = props.quality.summary as Record<string, unknown>
  return Object.entries(DIMENSION_LABELS).map(([key, label]) => ({
    key,
    label,
    score: typeof s[key] === 'number' ? (s[key] as number) : 0,
  }))
})

const overallScore = computed(() => {
  if (!props.quality?.summary) return 0
  const s = props.quality.summary as Record<string, unknown>
  return typeof s.overall_score === 'number' ? (s.overall_score as number) : 0
})

function dimScoreClass(score: number): string {
  if (score >= 80) return 'quality-dialog__dim-bar--high'
  if (score >= 60) return 'quality-dialog__dim-bar--mid'
  return 'quality-dialog__dim-bar--low'
}

function severityLabel(s: string): string {
  switch (s) {
    case 'error': return '错误'
    case 'warning': return '警告'
    case 'info': return '信息'
    default: return s
  }
}

function formatSize(bytes: number): string {
  if (!bytes) return '0 B'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function truncate(s: string, max: number): string {
  if (!s) return ''
  return s.length > max ? s.slice(0, max) + '…' : s
}
</script>

<style scoped>
.quality-dialog {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: flex;
  justify-content: flex-end;
}

.quality-dialog__backdrop {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
}

.quality-dialog__panel {
  position: relative;
  width: min(1240px, 96vw);
  height: 100%;
  background: var(--paper);
  border-left: 1px solid var(--hairline);
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
  animation: slide-in 0.18s ease-out;
}

@keyframes slide-in {
  from { transform: translateX(20px); opacity: 0; }
  to   { transform: translateX(0); opacity: 1; }
}

.quality-dialog__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--sp-3);
  padding: var(--sp-5);
  border-bottom: 1px solid var(--hairline);
}

.quality-dialog__head-meta {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: var(--sp-1);
}

.quality-dialog__eyebrow {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--accent);
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.quality-dialog__title {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  color: var(--ink);
  margin: 0;
  word-break: break-all;
  line-height: 1.4;
}

.quality-dialog__sub {
  display: flex;
  gap: var(--sp-2);
  align-items: center;
  margin: var(--sp-1) 0 0;
  font-size: var(--text-xs);
}

.quality-dialog__id {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--ink-mute);
}

.quality-dialog__close {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  border: 1px solid var(--hairline-strong);
  background: transparent;
  border-radius: var(--radius-sm);
  font-size: var(--text-md);
  color: var(--ink-sub);
  cursor: pointer;
}
.quality-dialog__close:hover { color: var(--accent); border-color: var(--accent); }

.quality-dialog__main {
  flex: 1;
  display: grid;
  grid-template-columns: minmax(340px, 400px) 1fr;
  min-height: 0;
}

.quality-dialog__side {
  border-right: 1px solid var(--hairline);
  background: var(--paper-sub);
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.quality-dialog__side-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-2);
  padding: var(--sp-4) var(--sp-5);
  border-bottom: 1px solid var(--hairline);
}

.quality-dialog__side-toggle {
  display: none;
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  padding: 2px var(--sp-2);
  border: 1px solid var(--hairline-strong);
  background: transparent;
  color: var(--ink-sub);
  border-radius: var(--radius-sm);
  cursor: pointer;
}

.quality-dialog__side-body {
  flex: 1;
  overflow: auto;
  padding: var(--sp-4) var(--sp-5);
}

.quality-dialog__side-empty {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--ink-mute);
  font-style: italic;
}

.quality-dialog__meta {
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
}

.quality-dialog__meta-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--sp-2);
}

.quality-dialog__meta-label {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--ink-mute);
}

.quality-dialog__meta-value {
  font-family: var(--font-sans);
  font-size: var(--text-sm);
  color: var(--ink);
  text-align: right;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 220px;
}

.quality-dialog__meta-mono {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--ink-sub);
}

.quality-dialog__badge--format {
  display: inline-block;
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  padding: 2px var(--sp-2);
  border: 1px solid var(--hairline-strong);
  border-radius: var(--radius-sm);
  color: var(--ink-sub);
  background: var(--paper-sub);
  text-transform: uppercase;
}

.quality-dialog__content {
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.quality-dialog__body {
  flex: 1;
  overflow: auto;
  padding: var(--sp-5);
  display: flex;
  flex-direction: column;
  gap: var(--sp-5);
}

.quality-dialog__loading {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  color: var(--ink-mute);
  padding: var(--sp-5);
}

.quality-dialog__section {
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
}

.quality-dialog__section-title {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--ink-mute);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  margin: 0;
  display: flex;
  align-items: center;
  gap: var(--sp-2);
}

.quality-dialog__count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  width: 18px;
  height: 18px;
  background: var(--accent);
  color: var(--paper);
  border-radius: 50%;
}

.quality-dialog__cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: var(--sp-2);
}

.quality-dialog__card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--sp-1);
  padding: var(--sp-3);
  border: 1px solid var(--hairline);
  border-radius: var(--radius-sm);
  background: var(--paper-sub);
}

.quality-dialog__card-value {
  font-family: var(--font-display);
  font-size: var(--text-lg);
  color: var(--ink);
  font-weight: 500;
}

.quality-dialog__card-label {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--ink-mute);
}

.quality-dialog__no-issues {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  color: var(--success);
  padding: var(--sp-3) 0;
}

.quality-dialog__issues {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
}

.quality-dialog__issue {
  display: flex;
  align-items: flex-start;
  gap: var(--sp-3);
  padding: var(--sp-3);
  border: 1px solid var(--hairline);
  border-radius: var(--radius-sm);
  background: var(--paper-sub);
}

.quality-dialog__issue--error {
  border-color: var(--accent);
  background: var(--accent-bg);
}

.quality-dialog__issue--warning {
  border-color: var(--warning);
  background: var(--warning-bg);
}

.quality-dialog__issue-badge {
  flex-shrink: 0;
  font-family: var(--font-mono);
  font-size: 10px;
  padding: 1px var(--sp-2);
  border: 1px solid var(--hairline-strong);
  border-radius: var(--radius-sm);
  color: var(--ink-sub);
  text-transform: uppercase;
  min-width: 36px;
  text-align: center;
}

.quality-dialog__issue--error .quality-dialog__issue-badge {
  color: var(--accent);
  border-color: var(--accent);
}

.quality-dialog__issue--warning .quality-dialog__issue-badge {
  color: var(--warning);
  border-color: var(--warning);
}

.quality-dialog__issue-body {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.quality-dialog__issue-check {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--ink);
  font-weight: 500;
}

.quality-dialog__issue-detail {
  font-family: var(--font-sans);
  font-size: var(--text-sm);
  color: var(--ink-sub);
  line-height: 1.5;
  word-break: break-all;
}

.quality-dialog__issue-field {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--accent);
  background: var(--accent-bg);
  padding: 1px var(--sp-1);
  border-radius: var(--radius-sm);
}

.quality-dialog__issue-sug {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--ink-mute);
  margin-top: 2px;
  line-height: 1.4;
}

/* 维度评分条 */
.quality-dialog__dim-scores {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
  padding: var(--sp-3);
  border: 1px solid var(--hairline);
  border-radius: var(--radius-sm);
  background: var(--paper-sub);
}

.quality-dialog__dim-row {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
}

.quality-dialog__dim-row--total {
  padding-top: var(--sp-2);
  margin-top: var(--sp-1);
  border-top: 1px solid var(--hairline);
}

.quality-dialog__dim-label {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--ink);
  width: 64px;
  flex-shrink: 0;
}

.quality-dialog__dim-bar-bg {
  flex: 1;
  height: 8px;
  background: var(--hairline-strong);
  border-radius: 4px;
  overflow: hidden;
}

.quality-dialog__dim-bar {
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s ease;
}

.quality-dialog__dim-bar--high { background: var(--success); }
.quality-dialog__dim-bar--mid  { background: var(--warning); }
.quality-dialog__dim-bar--low  { background: var(--accent); }

.quality-dialog__dim-value {
  font-family: var(--font-display);
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--ink);
  width: 28px;
  text-align: right;
}

.quality-dialog__dim-row--total .quality-dialog__dim-value {
  font-weight: 600;
}

.quality-dialog__md {
  border: 1px solid var(--hairline);
  border-radius: var(--radius-sm);
  background: var(--paper-sub);
  padding: var(--sp-4);
}

@media (max-width: 900px) {
  .quality-dialog__main {
    grid-template-columns: 1fr;
    grid-template-rows: auto 1fr;
  }
  .quality-dialog__side {
    border-right: none;
    border-bottom: 1px solid var(--hairline);
    max-height: 40vh;
  }
  .quality-dialog__side-toggle { display: inline-block; }
  .quality-dialog__cards { grid-template-columns: repeat(3, 1fr); }
}

@media (max-width: 720px) {
  .quality-dialog__panel { width: 100vw; }
  .quality-dialog__cards { grid-template-columns: repeat(2, 1fr); }
}
</style>
