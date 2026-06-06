<template>
  <section class="readonly-section" data-testid="cand377-warehouse-finished-goods-inbound-readonly-section">
    <div class="readonly-header">
      <div>
        <h3 data-testid="cand377-warehouse-finished-goods-inbound-title">成品入库只读区</h3>
        <p data-testid="cand377-warehouse-finished-goods-inbound-subtitle">
          当前仅核对 finished-goods inbound 候选、product-stock parity 与 inbound-readonly focus，不开放真实成品入库执行。
        </p>
      </div>
      <div class="tag-list" data-testid="cand377-warehouse-finished-goods-inbound-tags">
        <el-tag
          v-for="tag in summary.tags"
          :key="tag.key"
          :type="tag.type"
          effect="plain"
          :data-testid="`cand377-warehouse-finished-goods-inbound-tag-${tag.key}`"
        >
          {{ tag.label }}
        </el-tag>
      </div>
    </div>

    <div class="metric-grid" data-testid="cand377-warehouse-finished-goods-inbound-metrics">
      <div
        v-for="metric in summary.metrics"
        :key="metric.key"
        class="metric-card"
        :data-testid="`cand377-warehouse-finished-goods-inbound-metric-${metric.key}`"
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
      data-testid="cand377-warehouse-finished-goods-inbound-summary"
    >
      <el-descriptions-item label="finished-goods inbound 摘要">{{ summary.inboundSummary }}</el-descriptions-item>
      <el-descriptions-item label="product-stock parity">{{ summary.parityLabel }}</el-descriptions-item>
      <el-descriptions-item label="focus state">{{ summary.focusStateLabel }}</el-descriptions-item>
      <el-descriptions-item label="blocked reason">{{ summary.blockedReasonSummary }}</el-descriptions-item>
      <el-descriptions-item label="只读来源">{{ summary.readonlySourceLabel }}</el-descriptions-item>
      <el-descriptions-item label="只读模式">{{ summary.readonlyModeLabel }}</el-descriptions-item>
      <el-descriptions-item label="候选入口">{{ summary.disabledEntryLabel }}</el-descriptions-item>
      <el-descriptions-item label="入口阻断">{{ summary.disabledEntryReason }}</el-descriptions-item>
      <el-descriptions-item label="allocation contract">{{ summary.allocationContractLabel }}</el-descriptions-item>
      <el-descriptions-item label="show completed">{{ summary.showCompletedForcedLabel }}</el-descriptions-item>
      <el-descriptions-item label="状态">
        <el-tag :type="summary.inboundStatusTone" effect="plain">{{ summary.inboundStatusLabel }}</el-tag>
      </el-descriptions-item>
      <el-descriptions-item label="写边界">{{ summary.writeBoundary }}</el-descriptions-item>
    </el-descriptions>

    <div class="item-list" data-testid="cand377-warehouse-finished-goods-inbound-items">
      <details
        v-for="item in summary.items"
        :key="item.key"
        class="item-card"
        :open="summary.items.length === 1"
        :data-testid="`cand377-warehouse-finished-goods-inbound-item-${item.key}`"
      >
        <summary class="item-summary">
          <div class="item-title-wrap">
            <strong>{{ item.title }}</strong>
            <span>{{ item.itemCode }}</span>
          </div>
          <div class="item-meta">
            <el-tag :type="item.statusTone" effect="plain">{{ item.statusLabel }}</el-tag>
            <span>{{ item.quantityLabel }}</span>
          </div>
        </summary>
        <div class="item-content">
          <div class="item-grid">
            <span>source_id={{ item.sourceId }}</span>
            <span>qty={{ item.quantityLabel }}</span>
          </div>
          <small>{{ item.blockedReason }}</small>
          <small>{{ item.note }}</small>
        </div>
      </details>
    </div>

    <div class="guarded-action-list" data-testid="cand377-warehouse-finished-goods-inbound-guarded-actions">
      <div
        v-for="action in summary.guardedActions"
        :key="action.key"
        class="guarded-action-card"
        :data-testid="`cand377-warehouse-finished-goods-inbound-guarded-action-${action.key}`"
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
      data-testid="cand377-warehouse-finished-goods-inbound-readonly-guard"
    />
    <el-alert
      type="info"
      :closable="false"
      show-icon
      :title="summary.remainingGap"
      data-testid="cand377-warehouse-finished-goods-inbound-remaining-gap"
    />
  </section>
</template>

<script setup lang="ts">
import type { WarehouseFinishedGoodsInboundReadonlySummary } from '../composables/useWarehouseFinishedGoodsInboundReadonly'

defineProps<{
  summary: WarehouseFinishedGoodsInboundReadonlySummary
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
.item-grid,
.item-meta {
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
.item-card,
.guarded-action-card {
  padding: 10px 12px;
  border-radius: 6px;
  background: var(--el-bg-color);
}

.metric-card,
.item-card {
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

.metric-value {
  font-size: 16px;
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
  gap: 12px;
  align-items: center;
  cursor: pointer;
}

.item-title-wrap {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.item-title-wrap span {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.item-content {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 8px;
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
    align-items: flex-start;
  }

  .metric-grid,
  .item-list,
  .guarded-action-list {
    grid-template-columns: 1fr;
  }
}
</style>
