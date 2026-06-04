<template>
  <section class="followup-shell" data-testid="production-followup-readonly">
    <div class="followup-header">
      <div class="title-group">
        <span class="title">生产跟进模板 / 样衣流程回读</span>
        <span class="note">{{ summary.sourceLabel }}</span>
      </div>
      <div class="header-tags">
        <el-tag
          :type="summary.templateStatusTone"
          effect="plain"
          data-testid="production-followup-template-status"
        >
          {{ summary.templateStatusLabel }}
        </el-tag>
        <el-tag
          :type="summary.sampleParityTone"
          effect="plain"
          data-testid="production-followup-sample-parity"
        >
          {{ summary.sampleParityLabel }}
        </el-tag>
        <el-tag
          :type="summary.progressExceptionTone"
          effect="plain"
          data-testid="production-followup-progress-status"
        >
          {{ summary.progressExceptionLabel }}
        </el-tag>
      </div>
    </div>

    <div class="summary-grid">
      <div
        v-for="field in PRODUCTION_FOLLOWUP_METRIC_FIELDS"
        :key="field.key"
        class="summary-card"
      >
        <span class="summary-label">{{ field.label }}</span>
        <strong class="summary-value">{{ summaryValue(field.key) }}</strong>
      </div>
    </div>

    <el-alert
      type="warning"
      :closable="false"
      :title="summary.readonlyGuardReason"
      data-testid="production-followup-readonly-guard"
    />

    <el-alert
      type="info"
      :closable="false"
      :title="summary.remainingGap"
      data-testid="production-followup-remaining-gap"
    />

    <el-descriptions border :column="3" class="followup-descriptions">
      <el-descriptions-item label="当前入口">{{ summary.parityScopeLabel }}</el-descriptions-item>
      <el-descriptions-item label="模板来源">{{ summary.sourceLabel }}</el-descriptions-item>
      <el-descriptions-item label="写入边界">
        create-work-order / sync-job-cards disabled
      </el-descriptions-item>
      <el-descriptions-item label="模板状态">{{ summary.templateStatusLabel }}</el-descriptions-item>
      <el-descriptions-item label="样衣 parity">{{ summary.sampleParityLabel }}</el-descriptions-item>
      <el-descriptions-item label="进度异常">{{ summary.progressExceptionLabel }}</el-descriptions-item>
    </el-descriptions>
  </section>
</template>

<script setup lang="ts">
import type { ProductionFollowupReadonlySummary } from '@/views/production/composables/useProductionPlanReadback'
import {
  PRODUCTION_FOLLOWUP_METRIC_FIELDS,
  type ProductionFollowupMetricKey,
} from '@/views/production/constants/productionFollowupFields'

const props = defineProps<{
  summary: ProductionFollowupReadonlySummary
}>()

const summaryValue = (key: ProductionFollowupMetricKey): string => {
  switch (key) {
    case 'templateCount':
      return String(props.summary.templateCount)
    case 'sampleProcessCount':
      return String(props.summary.sampleProcessCount)
    case 'exceptionCount':
      return String(props.summary.exceptionCount)
    case 'progressSnapshot':
      return props.summary.progressSnapshot
    default:
      return '-'
  }
}
</script>

<style scoped>
.followup-shell {
  margin-bottom: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.followup-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.title-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.title {
  font-size: 16px;
  font-weight: 600;
}

.note,
.summary-label {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.header-tags {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 12px;
}

.summary-card {
  border: 1px solid var(--el-border-color-light);
  border-radius: 8px;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  background: var(--el-fill-color-blank);
}

.summary-value {
  font-size: 18px;
}
</style>
