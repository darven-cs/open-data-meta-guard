<!--
  EvaluationDialog: 评估详情 Drawer

  Props:
    open      : boolean
    evaluation: EvaluationDetail | null
    loading   : boolean

  Emits:
    close

  内容布局：
    1. 顶部评分卡（grade 徽章 + 总分大字 + dataset_id）
    2. 5 维分项数字（紧凑表格）
    3. <DimensionRadar> 雷达图
    4. <RuleScoresChart> 23 条规则条形图
    5. Markdown 报告（MarkdownView 渲染 evaluation_content）
    6. 改进建议列表（llm_notes.improvement_suggestions）
-->
<template>
  <Teleport to="body">
    <div v-if="open" class="eval-dialog" role="dialog" aria-modal="true">
      <div class="eval-dialog__backdrop" @click="emit('close')" />

      <aside class="eval-dialog__panel">
        <!-- 头部 -->
        <header class="eval-dialog__head">
          <div class="eval-dialog__head-meta">
            <span class="eval-dialog__eyebrow">MQA Evaluation</span>
            <h2 class="eval-dialog__title">
              {{ evaluation ? truncate(evaluation.dataset_id, 24) : '评估详情' }}
            </h2>
            <p v-if="evaluation" class="eval-dialog__sub">
              <span
                class="eval-dialog__badge"
                :class="gradeBadgeClass(evaluation.grade)"
              >
                {{ evaluation.grade }}
              </span>
              <span class="eval-dialog__score">
                {{ evaluation.score_total }} / 405
              </span>
              <span class="eval-dialog__id">#{{ evaluation.id }}</span>
            </p>
          </div>
          <button
            type="button"
            class="eval-dialog__close"
            aria-label="关闭"
            @click="emit('close')"
          >×</button>
        </header>

        <!-- 正文 -->
        <div v-if="loading" class="eval-dialog__loading">加载中…</div>
        <div v-else-if="!evaluation" class="eval-dialog__loading">暂无数据</div>
        <div v-else class="eval-dialog__body">
          <!-- 5 维数字表 -->
          <section class="eval-dialog__section">
            <h3 class="eval-dialog__section-title">5 维分项</h3>
            <div class="eval-dialog__dims">
              <div
                v-for="d in dims"
                :key="d.key"
                class="eval-dialog__dim"
              >
                <span class="eval-dialog__dim-code">{{ d.code }}</span>
                <span class="eval-dialog__dim-name">{{ d.name }}</span>
                <span class="eval-dialog__dim-score">
                  {{ d.score }} <span class="eval-dialog__dim-max">/ {{ d.max }}</span>
                </span>
              </div>
            </div>
          </section>

          <!-- 雷达图 -->
          <section class="eval-dialog__section eval-dialog__section--radar">
            <DimensionRadar
              :discover="evaluation.score_discover"
              :access="evaluation.score_access"
              :interop="evaluation.score_interop"
              :reuse="evaluation.score_reuse"
              :context="evaluation.score_context"
            />
          </section>

          <!-- 23 条规则条形图 -->
          <section class="eval-dialog__section">
            <RuleScoresChart :rule-scores="evaluation.rule_scores" />
          </section>

          <!-- 改进建议 -->
          <section v-if="suggestions.length > 0" class="eval-dialog__section">
            <h3 class="eval-dialog__section-title">改进建议</h3>
            <ol class="eval-dialog__suggest">
              <li
                v-for="(s, idx) in suggestions"
                :key="idx"
                class="eval-dialog__suggest-item"
              >
                {{ s }}
              </li>
            </ol>
          </section>

          <!-- Markdown 报告 -->
          <section class="eval-dialog__section">
            <h3 class="eval-dialog__section-title">Markdown 报告</h3>
            <div class="eval-dialog__md">
              <MarkdownView :content="evaluation.evaluation_content" />
            </div>
          </section>
        </div>
      </aside>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { EvaluationDetail } from '@/api/meta-evaluate'
import DimensionRadar from './DimensionRadar.vue'
import RuleScoresChart from './RuleScoresChart.vue'
import MarkdownView from '@/components/chat/MarkdownView.vue'

const props = defineProps<{
  open: boolean
  evaluation: EvaluationDetail | null
  loading?: boolean
}>()

const emit = defineEmits<{ close: [] }>()

const dims = computed(() => {
  if (!props.evaluation) return []
  const e = props.evaluation
  return [
    { key: 'discover', code: 'F', name: 'Findability',    score: e.score_discover, max: 100  },
    { key: 'access',   code: 'A', name: 'Accessibility',  score: e.score_access,   max: 100  },
    { key: 'interop',  code: 'I', name: 'Interoperability', score: e.score_interop, max: 110 },
    { key: 'reuse',    code: 'R', name: 'Reusability',    score: e.score_reuse,    max: 75   },
    { key: 'context',  code: 'C', name: 'Contextuality',  score: e.score_context,  max: 20   },
  ]
})

const suggestions = computed<string[]>(() => {
  if (!props.evaluation) return []
  const notes = props.evaluation.llm_notes || {}
  const raw = (notes as any).improvement_suggestions
  if (Array.isArray(raw)) return raw.filter((s) => typeof s === 'string') as string[]
  return []
})

function gradeBadgeClass(g: string): string {
  switch (g) {
    case 'Excellent':  return 'eval-dialog__badge--excellent'
    case 'Good':       return 'eval-dialog__badge--good'
    case 'Sufficient': return 'eval-dialog__badge--sufficient'
    case 'Bad':        return 'eval-dialog__badge--bad'
    default:           return ''
  }
}

function truncate(s: string, max: number): string {
  return s.length > max ? s.slice(0, max) + '…' : s
}
</script>

<style scoped>
.eval-dialog {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: flex;
  justify-content: flex-end;
}

.eval-dialog__backdrop {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
}

.eval-dialog__panel {
  position: relative;
  width: min(820px, 100vw);
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

.eval-dialog__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--sp-3);
  padding: var(--sp-5);
  border-bottom: 1px solid var(--hairline);
}

.eval-dialog__head-meta {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: var(--sp-1);
}

.eval-dialog__eyebrow {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--accent);
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.eval-dialog__title {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  color: var(--ink);
  margin: 0;
  word-break: break-all;
  line-height: 1.4;
}

.eval-dialog__sub {
  display: flex;
  gap: var(--sp-2);
  align-items: center;
  margin: var(--sp-1) 0 0;
  font-size: var(--text-xs);
}

.eval-dialog__badge {
  display: inline-block;
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  padding: 2px var(--sp-2);
  border: 1px solid var(--hairline-strong);
  border-radius: var(--radius-sm);
  font-weight: 500;
}
.eval-dialog__badge--excellent {
  color: var(--success);
  border-color: var(--success);
  background: var(--success-bg);
}
.eval-dialog__badge--good {
  color: var(--accent);
  border-color: var(--accent);
  background: var(--accent-bg);
}
.eval-dialog__badge--sufficient {
  color: var(--warning);
  border-color: var(--warning);
  background: var(--warning-bg);
}
.eval-dialog__badge--bad {
  color: var(--accent);
  border-color: var(--accent);
  background: var(--accent-bg);
  opacity: 0.7;
}

.eval-dialog__score {
  font-family: var(--font-display);
  font-size: var(--text-lg);
  color: var(--ink);
  font-weight: 500;
}

.eval-dialog__id {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--ink-mute);
}

.eval-dialog__close {
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
.eval-dialog__close:hover { color: var(--accent); border-color: var(--accent); }

.eval-dialog__body {
  flex: 1;
  overflow: auto;
  padding: var(--sp-5);
  display: flex;
  flex-direction: column;
  gap: var(--sp-5);
}

.eval-dialog__loading {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  color: var(--ink-mute);
}

.eval-dialog__section {
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
}

.eval-dialog__section--radar {
  align-items: center;
}

.eval-dialog__section-title {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--ink-mute);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  margin: 0;
}

.eval-dialog__dims {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: var(--sp-2);
}

.eval-dialog__dim {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--sp-1);
  padding: var(--sp-3) var(--sp-2);
  border: 1px solid var(--hairline);
  border-radius: var(--radius-sm);
  background: var(--paper-sub);
}

.eval-dialog__dim-code {
  font-family: var(--font-mono);
  font-size: var(--text-md);
  color: var(--accent);
  font-weight: 500;
}

.eval-dialog__dim-name {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--ink-mute);
  letter-spacing: 0.04em;
}

.eval-dialog__dim-score {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  color: var(--ink);
  font-weight: 500;
}

.eval-dialog__dim-max {
  color: var(--ink-mute);
  font-weight: 400;
  font-size: var(--text-xs);
}

.eval-dialog__suggest {
  margin: 0;
  padding-left: var(--sp-5);
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
}

.eval-dialog__suggest-item {
  font-family: var(--font-sans);
  font-size: var(--text-sm);
  color: var(--ink);
  line-height: 1.55;
}

.eval-dialog__md {
  border: 1px solid var(--hairline);
  border-radius: var(--radius-sm);
  background: var(--paper-sub);
  padding: var(--sp-4);
}

@media (max-width: 720px) {
  .eval-dialog__panel { width: 100vw; }
  .eval-dialog__dims { grid-template-columns: repeat(2, 1fr); }
}
</style>