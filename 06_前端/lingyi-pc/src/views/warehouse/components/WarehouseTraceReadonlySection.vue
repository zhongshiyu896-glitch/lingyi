<template>
  <section class="readonly-section" data-testid="cand433-warehouse-trace-readonly-section">
    <div class="anchor-row" data-testid="cand433-warehouse-trace-anchor" />

    <div class="readonly-header">
      <div>
        <h3 data-testid="cand433-warehouse-trace-title">仓库追溯只读区</h3>
        <p data-testid="cand433-warehouse-trace-subtitle">
          当前仅核对 trace-source、批次/序列来源状态与追溯流水摘要，不开放真实库存动作。
        </p>
      </div>
      <div class="tag-list" data-testid="cand433-warehouse-trace-tags">
        <el-tag
          v-for="tag in summary.tags"
          :key="tag.key"
          :type="tag.type"
          effect="plain"
          :data-testid="`cand433-warehouse-trace-tag-${tag.key}`"
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
      data-testid="cand433-warehouse-trace-query-state"
    >
      <el-descriptions-item label="query-state">
        <span data-testid="cand433-warehouse-trace-query-state-value">{{ summary.currentPathLabel }}</span>
      </el-descriptions-item>
      <el-descriptions-item label="parity">
        <span data-testid="cand433-warehouse-trace-marker-parity">{{ summary.parityLabel }}</span>
      </el-descriptions-item>
      <el-descriptions-item label="focus">
        <span data-testid="cand433-warehouse-trace-marker-focus">{{ summary.focusLabel }}</span>
      </el-descriptions-item>
      <el-descriptions-item label="source/status">
        <span data-testid="cand433-warehouse-trace-marker-status">{{ summary.sourceStatusLabel }}</span>
      </el-descriptions-item>
    </el-descriptions>

    <div class="metric-grid" data-testid="cand433-warehouse-trace-metrics">
      <div
        v-for="metric in summary.metrics"
        :key="metric.key"
        class="metric-card"
        :data-testid="`cand433-warehouse-trace-metric-${metric.key}`"
      >
        <span class="metric-label">{{ metric.label }}</span>
        <strong class="metric-value">{{ metric.value }}</strong>
      </div>
    </div>

    <div class="diagnostic-card-grid" data-testid="cand433-warehouse-trace-cards">
      <article
        v-for="card in summary.statusCards"
        :key="card.key"
        class="diagnostic-card"
        :data-testid="`cand433-warehouse-trace-card-${card.key}`"
      >
        <div class="diagnostic-card-header">
          <div>
            <h4>{{ card.title }}</h4>
            <p>{{ card.note }}</p>
          </div>
          <el-tag :type="card.statusTone" effect="plain">{{ card.statusLabel }}</el-tag>
        </div>
        <strong
          class="diagnostic-card-count"
          :data-testid="card.key === 'trace_item' ? 'cand433-warehouse-trace-item-status' : card.key === 'source_status' ? 'cand433-warehouse-trace-source-status' : undefined"
        >
          {{ card.value }}
        </strong>
      </article>
    </div>

    <el-alert
      type="info"
      :closable="false"
      show-icon
      :title="summary.itemStatusSummary"
      data-testid="cand433-warehouse-trace-item-summary"
    />
    <el-alert
      type="warning"
      :closable="false"
      show-icon
      :title="summary.blockedReason"
      data-testid="cand433-warehouse-trace-blocked-reason"
    />

    <div class="guarded-action-list" data-testid="cand433-warehouse-trace-guarded-actions">
      <div
        v-for="action in summary.guardedActions"
        :key="action.key"
        class="guarded-action-card"
        :data-testid="`cand433-warehouse-trace-guarded-action-${action.key}`"
      >
        <el-button size="small" disabled>{{ action.label }}</el-button>
        <span>{{ action.reason }}</span>
      </div>
    </div>

    <el-alert
      type="warning"
      :closable="false"
      show-icon
      :title="summary.readonlyGuard"
      data-testid="cand433-warehouse-trace-readonly-guard"
    />
    <el-alert
      type="info"
      :closable="false"
      show-icon
      :title="summary.remainingGap"
      data-testid="cand433-warehouse-trace-remaining-gap"
    />
  </section>
</template>

<script setup lang="ts">
import type { WarehouseTraceReadonlySummary } from '../composables/useWarehouseTraceReadonly'

defineProps<{
  summary: WarehouseTraceReadonlySummary
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

.readonly-header,
.diagnostic-card-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.readonly-header h3,
.diagnostic-card h4 {
  margin: 0 0 4px;
}

.readonly-header p,
.diagnostic-card p,
.diagnostic-card small {
  margin: 0;
  color: var(--el-text-color-secondary);
  font-size: 13px;
  line-height: 1.5;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}

.metric-card,
.diagnostic-card,
.guarded-action-card {
  padding: 10px 12px;
  border-radius: 6px;
  background: var(--el-bg-color);
}

.metric-card,
.diagnostic-card {
  border: 1px solid var(--el-border-color-lighter);
}

.metric-card {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.metric-label {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.metric-value,
.diagnostic-card-count {
  font-size: 16px;
  color: var(--el-text-color-primary);
}

.diagnostic-card-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}

.diagnostic-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
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
  border: 1px dashed var(--el-border-color);
  color: var(--el-text-color-regular);
  font-size: 13px;
}

@media (max-width: 960px) {
  .readonly-header,
  .diagnostic-card-header {
    flex-direction: column;
  }

  .metric-grid,
  .diagnostic-card-grid,
  .guarded-action-list {
    grid-template-columns: 1fr;
  }
}
</style>
