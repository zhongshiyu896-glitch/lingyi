<template>
  <section class="readonly-shell" data-testid="cand526-sales-inventory-stock-ledger-movement-baseline-readonly-section">
    <div class="readonly-header">
      <div class="title-group">
        <span class="title">stock-ledger movement-baseline 只读核对</span>
        <span class="note" data-testid="cand526-sales-inventory-stock-ledger-movement-baseline-query-state">
          {{ summary.queryStateLabel }}
        </span>
      </div>
      <div class="header-tags">
        <el-tag
          :type="summary.parityTone"
          effect="plain"
          data-testid="cand526-sales-inventory-stock-ledger-movement-baseline-parity"
        >
          {{ summary.parityLabel }}
        </el-tag>
        <el-tag
          :type="summary.focusTone"
          effect="plain"
          data-testid="cand526-sales-inventory-stock-ledger-movement-baseline-focus"
        >
          {{ summary.focusLabel }}
        </el-tag>
        <el-tag
          :type="summary.stateTone"
          effect="plain"
          data-testid="cand526-sales-inventory-stock-ledger-movement-baseline-state"
        >
          {{ summary.stateLabel }}
        </el-tag>
        <el-tag
          :type="summary.sourceStatusTone"
          effect="plain"
          data-testid="cand526-sales-inventory-stock-ledger-movement-baseline-source-status"
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
      data-testid="cand526-sales-inventory-stock-ledger-movement-baseline-blocked-reason"
    />

    <el-alert
      type="info"
      :closable="false"
      :title="summary.readonlyGuardReason"
      data-testid="cand526-sales-inventory-stock-ledger-movement-baseline-readonly-guard"
    />

    <el-alert
      type="info"
      :closable="false"
      :title="summary.remainingGap"
      data-testid="cand526-sales-inventory-stock-ledger-movement-baseline-remaining-gap"
    />

    <el-descriptions border :column="2" class="readonly-descriptions">
      <el-descriptions-item label="写入边界">
        <span data-testid="cand526-sales-inventory-stock-ledger-movement-baseline-write-boundary">
          {{ summary.writeBoundary }}
        </span>
      </el-descriptions-item>
      <el-descriptions-item label="来源状态">
        <span data-testid="cand526-sales-inventory-stock-ledger-movement-baseline-source-status-text">
          {{ summary.sourceStatusLabel }}
        </span>
      </el-descriptions-item>
      <el-descriptions-item label="仓库/状态">
        <span data-testid="cand526-sales-inventory-stock-ledger-movement-baseline-item-status">
          {{ summary.itemStatusLabel }}
        </span>
      </el-descriptions-item>
      <el-descriptions-item label="聚焦来源">
        <span data-testid="cand526-sales-inventory-stock-ledger-movement-baseline-focus-text">
          {{ summary.focusLabel }}
        </span>
      </el-descriptions-item>
      <el-descriptions-item label="联动状态">{{ summary.stateLabel }}</el-descriptions-item>
      <el-descriptions-item label="只读守卫">{{ summary.readonlyGuardReason }}</el-descriptions-item>
    </el-descriptions>

    <div class="guarded-actions" data-testid="cand526-sales-inventory-stock-ledger-movement-baseline-guarded-actions">
      <el-button
        v-for="action in summary.disabledActions"
        :key="action.key"
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

    <ul class="disabled-reason-list" data-testid="cand526-sales-inventory-stock-ledger-movement-baseline-disabled-reasons">
      <li v-for="action in summary.disabledActions" :key="`${action.key}-reason`">
        {{ action.label }}: {{ action.reason }}
      </li>
    </ul>

    <el-table
      :data="summary.items"
      border
      size="small"
      empty-text="暂无 movement-baseline 只读条目"
      data-testid="cand526-sales-inventory-stock-ledger-movement-baseline-item-table"
    >
      <el-table-column prop="subjectLabel" label="条目" min-width="180" />
      <el-table-column prop="statusLabel" label="状态" min-width="220" />
      <el-table-column prop="sourceLabel" label="来源" min-width="220" />
      <el-table-column prop="blockedReason" label="阻断原因" min-width="280" />
    </el-table>
  </section>
</template>

<script setup lang="ts">
import type { SalesInventoryMovementBaselineReadonlyViewSummary } from '@/views/sales_inventory/composables/useSalesInventoryMovementBaselineReadonly'

defineProps<{
  summary: SalesInventoryMovementBaselineReadonlyViewSummary
}>()
</script>

<style scoped>
.readonly-shell {
  margin-bottom: 16px;
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
.summary-label,
.disabled-reason-list {
  font-size: 12px;
  color: var(--el-text-color-secondary);
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
  gap: 12px;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
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

.disabled-reason-list {
  margin: 0;
  padding-left: 18px;
  display: grid;
  gap: 4px;
}

.readonly-descriptions :deep(.el-descriptions__label) {
  width: 120px;
}
</style>
