<!--
  RuleScoresChart: EU MQA 23 条 indicator 水平条形图

  Props:
    ruleScores : Record<string, number>  (23 条 indicator → 得分)

  渲染：23 行水平条形图，CSS width: %，深色条 + 浅色背景
  显示：indicator 名（snake_case）+ 得分 / 满分
-->
<template>
  <div class="rule-chart">
    <div class="rule-chart__head">
      <span class="rule-chart__head-title">23 条 indicator 明细</span>
      <span class="rule-chart__head-sub">得分 / 满分</span>
    </div>
    <ul class="rule-chart__list">
      <li
        v-for="key in EU_MQA_RULE_KEYS"
        :key="key"
        class="rule-chart__row"
      >
        <span class="rule-chart__label" :title="key">{{ key }}</span>
        <div class="rule-chart__bar-track">
          <div
            class="rule-chart__bar-fill"
            :style="{ width: barWidth(key) + '%' }"
          ></div>
        </div>
        <span class="rule-chart__value">
          {{ ruleScores?.[key] ?? 0 }} / {{ EU_MQA_RULE_MAX[key] }}
        </span>
      </li>
    </ul>
  </div>
</template>

<script setup lang="ts">
import { EU_MQA_RULE_KEYS, EU_MQA_RULE_MAX } from '@/api/meta-evaluate'

const props = defineProps<{
  ruleScores?: Record<string, number>
}>()

function barWidth(key: string): number {
  const max = EU_MQA_RULE_MAX[key] || 1
  const score = props.ruleScores?.[key] ?? 0
  return Math.min(100, Math.round((score / max) * 100))
}
</script>

<style scoped>
.rule-chart {
  border: 1px solid var(--hairline);
  border-radius: var(--radius-sm);
  background: var(--paper);
  padding: var(--sp-4);
}

.rule-chart__head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: var(--sp-3);
  padding-bottom: var(--sp-2);
  border-bottom: 1px solid var(--hairline);
}

.rule-chart__head-title {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--ink-mute);
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.rule-chart__head-sub {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--ink-mute);
}

.rule-chart__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
}

.rule-chart__row {
  display: grid;
  grid-template-columns: 220px 1fr 90px;
  gap: var(--sp-3);
  align-items: center;
}

.rule-chart__label {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--ink-sub);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rule-chart__bar-track {
  height: 8px;
  background: var(--paper-sub);
  border-radius: var(--radius-sm);
  overflow: hidden;
  border: 1px solid var(--hairline);
}

.rule-chart__bar-fill {
  height: 100%;
  background: var(--accent);
  transition: width 0.3s ease;
}

.rule-chart__value {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--ink);
  text-align: right;
}

@media (max-width: 720px) {
  .rule-chart__row {
    grid-template-columns: 140px 1fr 70px;
  }
}
</style>