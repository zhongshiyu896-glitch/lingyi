<template>
  <section class="readonly-section" data-testid="cand363-warehouse-adapter-worker-readonly-section">
    <div class="readonly-header">
      <div>
        <h3 data-testid="cand363-warehouse-adapter-worker-title">仓库 adapter-worker 只读区</h3>
        <p data-testid="cand363-warehouse-adapter-worker-subtitle">
          当前仅核对库存 adapter/worker 状态、product-stock parity 与 worker-chain focus，不开放真实库存执行。
        </p>
      </div>
      <div class="tag-list" data-testid="cand363-warehouse-adapter-worker-tags">
        <el-tag
          v-for="tag in summary.tags"
          :key="tag.key"
          :type="tag.type"
          effect="plain"
          :data-testid="`cand363-warehouse-adapter-worker-tag-${tag.key}`"
        >
          {{ tag.label }}
        </el-tag>
      </div>
    </div>

    <div class="metric-grid" data-testid="cand363-warehouse-adapter-worker-metrics">
      <div
        v-for="metric in summary.metrics"
        :key="metric.key"
        class="metric-card"
        :data-testid="`cand363-warehouse-adapter-worker-metric-${metric.key}`"
      >
        <span class="metric-label">{{ metric.label }}</span>
        <strong class="metric-value">{{ metric.value }}</strong>
      </div>
    </div>

    <div class="diagnostic-card-grid" data-testid="cand363-warehouse-adapter-worker-cards">
      <article
        v-for="card in summary.cards"
        :key="card.key"
        class="diagnostic-card"
        :data-testid="`cand363-warehouse-adapter-worker-card-${card.key}`"
      >
        <div class="diagnostic-card-header">
          <div>
            <h4>{{ card.title }}</h4>
            <p>{{ card.sourceDescription }}</p>
          </div>
          <el-tag :type="card.statusTone" effect="plain">{{ card.statusLabel }}</el-tag>
        </div>
        <strong class="diagnostic-card-count">{{ card.count }} 条</strong>
        <div class="diagnostic-card-meta">
          <span>source_module={{ card.sourceModule }}</span>
          <span>source_route={{ card.sourceRoute }}</span>
        </div>
        <small>{{ card.blockedReason }}</small>
        <small>{{ card.note }}</small>
      </article>
    </div>

    <el-descriptions
      :column="2"
      border
      size="small"
      class="readonly-descriptions"
      data-testid="cand363-warehouse-adapter-worker-summary"
    >
      <el-descriptions-item label="adapter-worker 摘要">{{ summary.adapterWorkerStatusSummary }}</el-descriptions-item>
      <el-descriptions-item label="product-stock parity">{{ summary.parityLabel }}</el-descriptions-item>
      <el-descriptions-item label="worker-chain focus">{{ summary.focusStateLabel }}</el-descriptions-item>
      <el-descriptions-item label="blocked reason">{{ summary.blockedReasonSummary }}</el-descriptions-item>
      <el-descriptions-item label="只读来源">{{ summary.readonlySourceLabel }}</el-descriptions-item>
      <el-descriptions-item label="只读模式">{{ summary.readonlyModeLabel }}</el-descriptions-item>
      <el-descriptions-item label="状态">
        <el-tag :type="summary.adapterWorkerStatusTone" effect="plain">{{ summary.adapterWorkerStatusLabel }}</el-tag>
      </el-descriptions-item>
      <el-descriptions-item label="写边界">{{ summary.writeBoundary }}</el-descriptions-item>
    </el-descriptions>

    <div class="guarded-action-list" data-testid="cand363-warehouse-adapter-worker-guarded-actions">
      <div
        v-for="action in summary.guardedActions"
        :key="action.key"
        class="guarded-action-card"
        :data-testid="`cand363-warehouse-adapter-worker-guarded-action-${action.key}`"
      >
        <el-button size="small" disabled data-write-guard>{{ action.label }}</el-button>
        <span>{{ action.reason }}</span>
      </div>
    </div>

    <el-alert
      type="warning"
      :closable="false"
      show-icon
      :title="summary.guardMessage"
      data-testid="cand363-warehouse-adapter-worker-readonly-guard"
    />
    <el-alert
      type="info"
      :closable="false"
      show-icon
      :title="summary.remainingGap"
      data-testid="cand363-warehouse-adapter-worker-remaining-gap"
    />
  </section>
</template>

<script setup lang="ts">
import type { WarehouseAdapterWorkerReadonlySummary } from '../composables/useWarehouseAdapterWorkerReadonly'

defineProps<{
  summary: WarehouseAdapterWorkerReadonlySummary
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

.tag-list,
.diagnostic-card-meta {
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
  grid-template-columns: repeat(3, minmax(0, 1fr));
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
