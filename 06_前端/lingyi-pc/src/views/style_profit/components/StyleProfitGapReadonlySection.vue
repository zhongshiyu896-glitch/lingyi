<template>
  <section class="gap-section" :data-testid="`${testIdPrefix}-section`">
    <div class="gap-header">
      <div class="gap-title-group">
        <span class="gap-title">利润缺口只读区</span>
        <span class="gap-note">{{ summary.subtitle }}</span>
      </div>
      <el-tag type="info" effect="plain" :data-testid="`${testIdPrefix}-scope-tag`">
        {{ summary.parityScopeLabel }}
      </el-tag>
    </div>
    <div class="gap-grid">
      <div v-for="field in metricFields" :key="field.key" class="gap-card">
        <span class="gap-card-label">{{ field.label }}</span>
        <strong class="gap-card-value">{{ summary.metricValues[field.key] }}</strong>
      </div>
    </div>
    <el-descriptions border :column="1" size="small" :data-testid="`${testIdPrefix}-descriptions`">
      <el-descriptions-item label="成本来源差异">{{ summary.differenceSummary }}</el-descriptions-item>
      <el-descriptions-item label="利润快照缺项">{{ summary.missingSummary }}</el-descriptions-item>
      <el-descriptions-item label="缺项原因">{{ summary.reasonSummary }}</el-descriptions-item>
      <el-descriptions-item label="只读守卫">{{ summary.writeBoundary }}</el-descriptions-item>
    </el-descriptions>
    <el-alert
      type="warning"
      :closable="false"
      :title="summary.readonlyGuardReason"
      class="gap-alert"
      :data-testid="`${testIdPrefix}-guard-alert`"
    />
    <el-alert
      type="info"
      :closable="false"
      :title="summary.remainingGap"
      :data-testid="`${testIdPrefix}-remaining-gap-alert`"
    />
  </section>
</template>

<script setup lang="ts">
import type { StyleProfitGapReadonlySummary } from '@/views/style_profit/composables/useStyleProfitGapReadonly'
import type { StyleProfitGapMetricField } from '@/views/style_profit/constants/styleProfitGapFields'

defineProps<{
  testIdPrefix: string
  summary: StyleProfitGapReadonlySummary
  metricFields: ReadonlyArray<StyleProfitGapMetricField>
}>()
</script>

<style scoped>
.gap-section {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.gap-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.gap-title-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.gap-title {
  font-size: 15px;
  font-weight: 600;
}

.gap-note,
.gap-card-label {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.gap-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 12px;
}

.gap-card {
  border: 1px solid var(--el-border-color-light);
  border-radius: 8px;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  background: var(--el-fill-color-blank);
}

.gap-card-value {
  font-size: 18px;
}

.gap-alert {
  margin-top: 0;
}
</style>
