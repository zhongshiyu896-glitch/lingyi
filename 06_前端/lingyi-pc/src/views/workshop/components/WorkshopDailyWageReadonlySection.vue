<template>
  <section class="readonly-section" data-testid="workshop-daily-wage-readonly-section">
    <div class="readonly-header">
      <div>
        <h3 data-testid="workshop-daily-wage-readonly-title">日薪异常摘要与工票回流</h3>
        <p data-testid="workshop-daily-wage-readonly-subtitle">
          当前仅核对日薪统计、工票来源与异常原因，不开放真实写动作。
        </p>
      </div>
      <div class="tag-list" data-testid="workshop-daily-wage-readonly-tags">
        <el-tag
          v-for="tag in summary.tags"
          :key="tag.key"
          :type="tag.type"
          effect="plain"
          :data-testid="`workshop-daily-wage-readonly-tag-${tag.key}`"
        >
          {{ tag.label }}
        </el-tag>
      </div>
    </div>

    <div class="metric-grid" data-testid="workshop-daily-wage-readonly-metrics">
      <div
        v-for="metric in summary.metrics"
        :key="metric.key"
        class="metric-card"
        :data-testid="`workshop-daily-wage-readonly-metric-${metric.key}`"
      >
        <span class="metric-label">{{ metric.label }}</span>
        <strong class="metric-value">{{ metric.value }}</strong>
      </div>
    </div>

    <el-descriptions
      :column="2"
      border
      size="small"
      class="readonly-descriptions"
      data-testid="workshop-daily-wage-readonly-source-summary"
    >
    <el-descriptions-item label="只读来源">{{ summary.readonlySourceLabel }}</el-descriptions-item>
    <el-descriptions-item label="模式">{{ summary.readonlyModeLabel }}</el-descriptions-item>
  </el-descriptions>

    <div class="guarded-action-list" data-testid="workshop-daily-wage-readonly-guarded-actions">
      <div
        v-for="action in summary.guardedActions"
        :key="action.key"
        class="guarded-action-card"
        :data-testid="`workshop-daily-wage-guarded-action-${action.key}`"
      >
        <strong>{{ action.label }}</strong>
        <span>{{ action.reason }}</span>
      </div>
    </div>

    <div class="issue-list" data-testid="workshop-daily-wage-readonly-issues">
      <el-alert
        v-for="issue in summary.issues"
        :key="issue.key"
        :title="issue.title"
        :description="issue.message"
        :type="issue.type"
        :closable="false"
        show-icon
        class="issue-alert"
        :data-testid="`workshop-daily-wage-readonly-issue-${issue.key}`"
      />
    </div>

    <el-alert
      type="warning"
      :closable="false"
      show-icon
      :title="summary.guardMessage"
      data-testid="workshop-daily-wage-readonly-guard"
    />
    <el-alert
      type="info"
      :closable="false"
      show-icon
      :title="summary.remainingGap"
      data-testid="workshop-daily-wage-readonly-remaining-gap"
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
  flex-direction: column;
  gap: 4px;
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
