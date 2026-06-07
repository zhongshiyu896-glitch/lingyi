<template>
  <section
    class="readonly-shell"
    data-testid="cand442-sales-order-delivery-window-readonly-section"
  >
    <div class="readonly-header">
      <div class="title-group">
        <span class="title">销售订单交付窗口只读回读</span>
        <span
          class="note"
          data-testid="cand442-sales-order-delivery-window-query-state"
        >
          {{ summary.queryStateLabel }}
        </span>
      </div>
      <div class="header-tags">
        <el-tag
          :type="summary.parityTone"
          effect="plain"
          data-testid="cand442-sales-order-delivery-window-marker-parity"
        >
          {{ summary.parityLabel }}
        </el-tag>
        <el-tag
          :type="summary.focusTone"
          effect="plain"
          data-testid="cand442-sales-order-delivery-window-marker-focus"
        >
          {{ summary.focusLabel }}
        </el-tag>
        <el-tag
          :type="summary.deliveryStatusTone"
          effect="plain"
          data-testid="cand442-sales-order-delivery-window-marker-status"
        >
          {{ summary.deliveryStatusLabel }}
        </el-tag>
        <el-tag
          :type="summary.sourceStatusTone"
          effect="plain"
          data-testid="cand442-sales-order-delivery-window-source-status"
        >
          {{ summary.sourceStatusLabel }}
        </el-tag>
      </div>
    </div>

    <div class="summary-grid">
      <div v-for="card in summary.cards" :key="card.key" class="summary-card">
        <span class="summary-label">{{ card.label }}</span>
        <strong class="summary-value">{{ card.value }}</strong>
      </div>
    </div>

    <el-alert
      type="warning"
      :closable="false"
      :title="summary.blockedReason"
      data-testid="cand442-sales-order-delivery-window-blocked-reason"
    />

    <el-alert
      type="info"
      :closable="false"
      :title="summary.readonlyGuardReason"
      data-testid="cand442-sales-order-delivery-window-readonly-guard"
    />

    <el-alert
      type="info"
      :closable="false"
      :title="summary.remainingGap"
      data-testid="cand442-sales-order-delivery-window-remaining-gap"
    />

    <el-descriptions border :column="2" class="readonly-descriptions">
      <el-descriptions-item label="写入边界">
        <span data-testid="cand442-sales-order-delivery-window-write-boundary">
          {{ summary.writeBoundary }}
        </span>
      </el-descriptions-item>
      <el-descriptions-item label="来源状态">
        <span data-testid="cand442-sales-order-delivery-window-source-status-text">
          {{ summary.sourceStatusLabel }}
        </span>
      </el-descriptions-item>
      <el-descriptions-item label="交付条目状态">
        <span data-testid="cand442-sales-order-delivery-window-item-status">
          {{ summary.itemStatusLabel }}
        </span>
      </el-descriptions-item>
      <el-descriptions-item label="目标聚焦">
        <span data-testid="cand442-sales-order-delivery-window-focus-text">
          {{ summary.focusLabel }}
        </span>
      </el-descriptions-item>
    </el-descriptions>

    <div
      class="guarded-actions"
      data-testid="cand442-sales-order-delivery-window-guarded-actions"
    >
      <el-button
        v-for="action in summary.disabledActions"
        :key="action.label"
        disabled
        type="info"
        plain
        data-action-type="write"
        data-guard-state="disabled"
        :title="action.reason"
      >
        {{ action.label }}
      </el-button>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { SalesOrderDeliveryWindowReadonlySummary } from '@/views/sales_inventory/composables/useSalesOrderDeliveryWindowReadonly'

defineProps<{
  summary: SalesOrderDeliveryWindowReadonlySummary
}>()
</script>

<style scoped>
.readonly-shell {
  margin: 12px 0 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.readonly-header {
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
  font-size: 15px;
  font-weight: 600;
}

.note,
.summary-label {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.header-tags,
.guarded-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
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
  font-size: 16px;
  line-height: 1.2;
  color: var(--el-text-color-primary);
}

.readonly-descriptions :deep(.el-descriptions__label) {
  width: 120px;
}
</style>
