<template>
  <section class="source-audit-section" :data-testid="`${testIdPrefix}-readonly-section`">
    <div class="source-audit-header">
      <div class="source-audit-title-group">
        <h3 :data-testid="`${testIdPrefix}-title`">Style Profit source-audit 只读区</h3>
        <p :data-testid="`${testIdPrefix}-subtitle`">{{ summary.subtitle }}</p>
      </div>
      <div class="source-audit-tag-list">
        <el-tag type="info" effect="plain" :data-testid="`${testIdPrefix}-parity`">
          {{ summary.parityLabel }}
        </el-tag>
        <el-tag type="warning" effect="plain" :data-testid="`${testIdPrefix}-focus`">
          {{ summary.focusLabel }}
        </el-tag>
        <el-tag type="success" effect="plain" :data-testid="`${testIdPrefix}-source-status`">
          {{ summary.sourceStatusLabel }}
        </el-tag>
      </div>
    </div>

    <el-alert
      type="info"
      :closable="false"
      :title="`source-audit query state: ${summary.queryStateLabel}`"
      :description="`parity=${summary.parityLabel}; focus=${summary.focusLabel}`"
      :data-testid="`${testIdPrefix}-query-state`"
    />

    <div class="source-audit-metric-grid" :data-testid="`${testIdPrefix}-metrics`">
      <div
        v-for="field in STYLE_PROFIT_SOURCE_AUDIT_METRIC_FIELDS"
        :key="field.key"
        class="source-audit-metric-card"
        :data-testid="`${testIdPrefix}-metric-${field.key}`"
      >
        <span class="source-audit-metric-label">{{ field.label }}</span>
        <strong class="source-audit-metric-value">{{ summary.metricValues[field.key] }}</strong>
      </div>
    </div>

    <el-descriptions
      :column="2"
      border
      size="small"
      class="source-audit-descriptions"
      :data-testid="`${testIdPrefix}-descriptions`"
    >
      <el-descriptions-item label="收入口径">{{ summary.revenueModeLabel }}</el-descriptions-item>
      <el-descriptions-item label="快照状态">{{ summary.snapshotStatusLabel }}</el-descriptions-item>
      <el-descriptions-item label="映射状态">{{ summary.allocationStatusLabel }}</el-descriptions-item>
      <el-descriptions-item label="来源类型">{{ summary.sourceTypeLabel }}</el-descriptions-item>
      <el-descriptions-item label="来源状态">{{ summary.sourceStatusLabel }}</el-descriptions-item>
      <el-descriptions-item label="写入边界">{{ summary.writeBoundary }}</el-descriptions-item>
    </el-descriptions>

    <el-alert
      type="warning"
      :closable="false"
      :title="`blocked reason: ${summary.blockedReasonSummary}`"
      :data-testid="`${testIdPrefix}-blocked-reason`"
    />
    <el-alert
      type="warning"
      :closable="false"
      show-icon
      :title="summary.readonlyGuardReason"
      :data-testid="`${testIdPrefix}-readonly-guard`"
    />
    <el-alert
      type="info"
      :closable="false"
      show-icon
      :title="summary.remainingGap"
      :data-testid="`${testIdPrefix}-remaining-gap`"
    />

    <div class="source-audit-item-list" :data-testid="`${testIdPrefix}-item-status-rows`">
      <details
        v-for="item in summary.itemRows"
        :key="item.key"
        class="source-audit-item-card"
        :open="item.key === summary.itemRows[0]?.key"
        :data-testid="`${testIdPrefix}-item-${item.key}`"
      >
        <summary class="source-audit-item-summary">
          <div class="source-audit-item-title-wrap">
            <strong>{{ item.title }}</strong>
            <span>{{ item.scopeLabel }}</span>
          </div>
          <div class="source-audit-item-meta">
            <el-tag :type="item.statusTone" effect="plain">{{ item.statusLabel }}</el-tag>
            <span>{{ item.sourceStatusLabel }}</span>
          </div>
        </summary>
        <div class="source-audit-item-content">
          <small>{{ item.blockedReason }}</small>
          <small>{{ item.note }}</small>
        </div>
      </details>
    </div>

    <div class="source-audit-guarded-action-list" :data-testid="`${testIdPrefix}-guarded-actions`">
      <div
        v-for="action in summary.guardedActions"
        :key="action.key"
        class="source-audit-guarded-action-card"
        :data-testid="`${testIdPrefix}-guarded-action-${action.key}`"
      >
        <el-button size="small" disabled data-write-guard>{{ action.label }}</el-button>
        <span>{{ action.reason }}</span>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import {
  STYLE_PROFIT_SOURCE_AUDIT_METRIC_FIELDS,
} from '@/views/style_profit/constants/styleProfitSourceAuditFields'
import type { StyleProfitSourceAuditReadonlySummary } from '@/views/style_profit/composables/useStyleProfitSourceAuditReadonly'

defineProps<{
  summary: StyleProfitSourceAuditReadonlySummary
  testIdPrefix: string
}>()
</script>

<style scoped>
.source-audit-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 12px;
  padding: 12px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 6px;
  background: var(--el-fill-color-lighter);
}

.source-audit-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.source-audit-title-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.source-audit-title-group h3,
.source-audit-title-group p {
  margin: 0;
}

.source-audit-title-group p,
.source-audit-metric-label,
.source-audit-item-content small {
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 1.5;
}

.source-audit-tag-list,
.source-audit-item-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.source-audit-metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}

.source-audit-metric-card,
.source-audit-item-card,
.source-audit-guarded-action-card {
  padding: 10px 12px;
  border-radius: 6px;
  background: var(--el-bg-color);
}

.source-audit-metric-card,
.source-audit-item-card {
  border: 1px solid var(--el-border-color-lighter);
}

.source-audit-metric-card {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.source-audit-metric-value {
  font-size: 16px;
  color: var(--el-text-color-primary);
}

.source-audit-descriptions {
  background: var(--el-bg-color);
}

.source-audit-item-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.source-audit-item-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.source-audit-item-summary {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  cursor: pointer;
}

.source-audit-item-title-wrap {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.source-audit-item-title-wrap span {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.source-audit-item-content {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.source-audit-guarded-action-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.source-audit-guarded-action-card {
  display: flex;
  flex-direction: column;
  gap: 6px;
  border: 1px dashed var(--el-border-color);
}

.source-audit-guarded-action-card span {
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 1.5;
}
</style>
