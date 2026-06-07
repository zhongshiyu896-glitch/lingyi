<template>
  <section class="readonly-section" data-testid="cand437-workshop-daily-wage-readonly-section">
    <div class="anchor-row" data-testid="cand437-workshop-daily-wage-anchor" />

    <div class="readonly-header">
      <div>
        <h3 data-testid="cand437-workshop-daily-wage-title">日工资只读摘要</h3>
        <p data-testid="cand437-workshop-daily-wage-subtitle">
          当前仅核对 daily-wage-source、日工资统计与异常原因，不开放真实工资确认或跨模块执行。
        </p>
      </div>
      <div class="tag-list" data-testid="cand437-workshop-daily-wage-tags">
        <el-tag
          v-for="tag in summary.tags"
          :key="tag.key"
          :type="tag.type"
          effect="plain"
          :data-testid="`cand437-workshop-daily-wage-tag-${tag.key}`"
        >
          {{ tag.label }}
        </el-tag>
      </div>
    </div>

    <el-descriptions
      :column="2"
      border
      size="small"
      class="readonly-descriptions"
      data-testid="cand437-workshop-daily-wage-query-state"
    >
      <el-descriptions-item label="query-state">
        <span data-testid="cand437-workshop-daily-wage-query-state-value">{{ summary.currentPathLabel }}</span>
      </el-descriptions-item>
      <el-descriptions-item label="parity">
        <span data-testid="cand437-workshop-daily-wage-marker-parity">{{ summary.parityLabel }}</span>
      </el-descriptions-item>
      <el-descriptions-item label="focus">
        <span data-testid="cand437-workshop-daily-wage-marker-focus">{{ summary.focusLabel }}</span>
      </el-descriptions-item>
      <el-descriptions-item label="source/status">
        <span data-testid="cand437-workshop-daily-wage-marker-status">{{ summary.sourceStatusLabel }}</span>
      </el-descriptions-item>
    </el-descriptions>

    <div class="metric-grid" data-testid="cand437-workshop-daily-wage-metrics">
      <div
        v-for="metric in summary.metrics"
        :key="metric.key"
        class="metric-card"
        :data-testid="`cand437-workshop-daily-wage-metric-${metric.key}`"
      >
        <span class="metric-label">{{ metric.label }}</span>
        <strong class="metric-value">{{ metric.value }}</strong>
      </div>
    </div>

    <el-alert
      type="info"
      :closable="false"
      show-icon
      :title="summary.itemStatusSummary"
      data-testid="cand437-workshop-daily-wage-item-status"
    />

    <div class="guarded-action-list" data-testid="cand437-workshop-daily-wage-guarded-actions">
      <div
        v-for="action in summary.guardedActions"
        :key="action.key"
        class="guarded-action-card"
        :data-testid="`cand437-workshop-daily-wage-guarded-action-${action.key}`"
      >
        <el-button size="small" disabled>{{ action.label }}</el-button>
        <span>{{ action.reason }}</span>
      </div>
    </div>

    <div class="issue-list" data-testid="cand437-workshop-daily-wage-issues">
      <el-alert
        v-for="issue in summary.issues"
        :key="issue.key"
        :title="issue.title"
        :description="issue.message"
        :type="issue.type"
        :closable="false"
        show-icon
        class="issue-alert"
        :data-testid="`cand437-workshop-daily-wage-issue-${issue.key}`"
      />
    </div>

    <el-alert
      type="warning"
      :closable="false"
      show-icon
      :title="summary.blockedReason"
      data-testid="cand437-workshop-daily-wage-blocked-reason"
    />
    <el-alert
      type="warning"
      :closable="false"
      show-icon
      :title="summary.readonlyGuard"
      data-testid="cand437-workshop-daily-wage-readonly-guard"
    />
    <el-alert
      type="info"
      :closable="false"
      show-icon
      :title="summary.remainingGap"
      data-testid="cand437-workshop-daily-wage-remaining-gap"
    />
  </section>
</template>

<script setup lang="ts">
import type { WorkshopDailyWageReadonlySummary } from '../composables/useWorkshopDailyWageReadonly'

defineProps<{
  summary: WorkshopDailyWageReadonlySummary
}>()
</script>

<style scoped>
.readonly-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 12px;
  padding: 12px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 6px;
  background: var(--el-fill-color-lighter);
}

.anchor-row {
  width: 100%;
  height: 0;
}

.readonly-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.readonly-header h3 {
  margin: 0 0 4px;
  font-size: 15px;
}

.readonly-header p {
  margin: 0;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}

.metric-card {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 12px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 6px;
  background: var(--el-bg-color);
}

.metric-label {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.metric-value {
  font-size: 16px;
  color: var(--el-text-color-primary);
}

.readonly-descriptions {
  background: var(--el-bg-color);
}

.guarded-action-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.guarded-action-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border: 1px dashed var(--el-border-color);
  border-radius: 6px;
  background: var(--el-bg-color);
  color: var(--el-text-color-regular);
  font-size: 13px;
}

.issue-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.issue-alert {
  margin: 0;
}

@media (max-width: 960px) {
  .readonly-header {
    flex-direction: column;
  }

  .tag-list {
    justify-content: flex-start;
  }

  .metric-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .guarded-action-list {
    grid-template-columns: 1fr;
  }
}
</style>
