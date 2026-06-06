<template>
  <section class="readonly-section" data-testid="cand407-workshop-ticket-job-card-readonly-section">
    <div class="readonly-header">
      <div>
        <h3 data-testid="cand407-workshop-ticket-job-card-readonly-title">Job Card parity 只读区</h3>
        <p data-testid="cand407-workshop-ticket-job-card-readonly-subtitle">
          当前仅核对 job-card-readonly 查询态、production-order parity 与 job-card-source focus，不开放真实派工、确认、同步、导出或 worker 执行。
        </p>
      </div>
      <div class="tag-list" data-testid="cand407-workshop-ticket-job-card-readonly-tags">
        <el-tag
          v-for="tag in summary.tags"
          :key="tag.key"
          :type="tag.type"
          effect="plain"
          :data-testid="`cand407-workshop-ticket-job-card-tag-${tag.key}`"
        >
          {{ tag.label }}
        </el-tag>
      </div>
    </div>

    <el-alert
      type="info"
      :closable="false"
      :title="`job-card-readonly query state: ${summary.readonlySourceLabel}`"
      :description="`parity=${summary.parityLabel}; focus=${summary.focusStateLabel}; filters=${summary.queryStateLabel}`"
      data-testid="cand407-workshop-ticket-job-card-query-state"
    />

    <div class="marker-grid" data-testid="cand407-workshop-ticket-job-card-key-markers">
      <div class="marker-card" data-testid="cand407-workshop-ticket-job-card-marker-parity">
        <span class="marker-label">production-order parity</span>
        <strong class="marker-value">{{ summary.parityLabel }}</strong>
      </div>
      <div class="marker-card" data-testid="cand407-workshop-ticket-job-card-marker-status">
        <span class="marker-label">job-card item/status</span>
        <strong class="marker-value">{{ summary.itemStatusLabel }}</strong>
      </div>
      <div class="marker-card" data-testid="cand407-workshop-ticket-job-card-marker-focus">
        <span class="marker-label">job-card-source focus</span>
        <strong class="marker-value">{{ summary.focusStateLabel }}</strong>
      </div>
      <div class="marker-card" data-testid="cand407-workshop-ticket-job-card-marker-source">
        <span class="marker-label">source/status</span>
        <strong class="marker-value">{{ summary.sourceStatusLabel }}</strong>
      </div>
    </div>

    <el-alert
      type="warning"
      :closable="false"
      :title="`blocked reason: ${summary.blockedReasonSummary}`"
      data-testid="cand407-workshop-ticket-job-card-blocked-reason"
    />

    <el-alert
      type="warning"
      :closable="false"
      show-icon
      :title="summary.guardMessage"
      data-testid="cand407-workshop-ticket-job-card-readonly-guard"
    />
    <el-alert
      type="info"
      :closable="false"
      show-icon
      :title="summary.remainingGap"
      data-testid="cand407-workshop-ticket-job-card-remaining-gap"
    />

    <div class="metric-grid" data-testid="cand407-workshop-ticket-job-card-metrics">
      <div
        v-for="metric in summary.metrics"
        :key="metric.key"
        class="metric-card"
        :data-testid="`cand407-workshop-ticket-job-card-metric-${metric.key}`"
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
      data-testid="cand407-workshop-ticket-job-card-summary"
    >
      <el-descriptions-item label="工序卡摘要">{{ summary.jobCardSummary }}</el-descriptions-item>
      <el-descriptions-item label="production-order parity">{{ summary.parityLabel }}</el-descriptions-item>
      <el-descriptions-item label="focus state">{{ summary.focusStateLabel }}</el-descriptions-item>
      <el-descriptions-item label="source/status">{{ summary.sourceStatusLabel }}</el-descriptions-item>
      <el-descriptions-item label="blocked reason">{{ summary.blockedReasonSummary }}</el-descriptions-item>
      <el-descriptions-item label="只读来源">{{ summary.readonlySourceLabel }}</el-descriptions-item>
      <el-descriptions-item label="只读模式">{{ summary.readonlyModeLabel }}</el-descriptions-item>
      <el-descriptions-item label="查询镜像">{{ summary.queryStateLabel }}</el-descriptions-item>
      <el-descriptions-item label="状态">
        <el-tag :type="summary.itemStatusTone" effect="plain">{{ summary.itemStatusLabel }}</el-tag>
      </el-descriptions-item>
      <el-descriptions-item label="写边界">{{ summary.writeBoundary }}</el-descriptions-item>
    </el-descriptions>

    <div class="item-list" data-testid="cand407-workshop-ticket-job-card-items">
      <details
        v-for="item in summary.items"
        :key="item.key"
        class="item-card"
        :open="item.key === 'job-card-primary'"
        :data-testid="`cand407-workshop-ticket-job-card-item-${item.key}`"
      >
        <summary class="item-summary">
          <div class="item-title-wrap">
            <strong>{{ item.title }}</strong>
            <span>{{ item.scopeLabel }}</span>
          </div>
          <div class="item-meta">
            <el-tag :type="item.statusTone" effect="plain">{{ item.statusLabel }}</el-tag>
            <span>{{ item.sourceStatusLabel }}</span>
          </div>
        </summary>
        <div class="item-content">
          <small>{{ item.blockedReason }}</small>
          <small>{{ item.note }}</small>
        </div>
      </details>
    </div>

    <div class="guarded-action-list" data-testid="cand407-workshop-ticket-job-card-guarded-actions">
      <div
        v-for="action in summary.guardedActions"
        :key="action.key"
        class="guarded-action-card"
        :data-testid="`cand407-workshop-ticket-job-card-guarded-action-${action.key}`"
      >
        <el-button size="small" disabled data-write-guard>{{ action.label }}</el-button>
        <span>{{ action.reason }}</span>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { WorkshopTicketJobCardReadonlySummary } from '../composables/useWorkshopTicketJobCardReadonly'

defineProps<{
  summary: WorkshopTicketJobCardReadonlySummary
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
}

.readonly-header p,
.item-content small {
  margin: 0;
  color: var(--el-text-color-secondary);
  font-size: 13px;
  line-height: 1.5;
}

.tag-list,
.item-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.metric-grid,
.marker-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}

.metric-card,
.marker-card,
.item-card,
.guarded-action-card {
  padding: 10px 12px;
  border-radius: 6px;
  background: var(--el-bg-color);
}

.metric-card,
.marker-card,
.item-card {
  border: 1px solid var(--el-border-color-lighter);
}

.metric-card {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.metric-label,
.marker-label {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.metric-value {
  font-size: 16px;
  color: var(--el-text-color-primary);
}

.marker-value {
  font-size: 14px;
  color: var(--el-text-color-primary);
}

.readonly-descriptions {
  background: var(--el-bg-color);
}

.item-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.item-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.item-summary {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  cursor: pointer;
}

.item-title-wrap {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.item-title-wrap span,
.item-meta span {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.item-content {
  display: flex;
  flex-direction: column;
  gap: 6px;
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
  .item-summary {
    flex-direction: column;
  }

  .metric-grid,
  .marker-grid,
  .item-list,
  .guarded-action-list {
    grid-template-columns: 1fr;
  }
}
</style>
