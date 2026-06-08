<template>
  <section class="readonly-shell" data-testid="cand538-sales-order-downstream-guard-readonly-section">
    <div class="readonly-header">
      <div class="title-group">
        <span class="title">销售订单 downstream guard 只读守卫</span>
        <span class="note" data-testid="cand538-sales-order-downstream-query-state">
          {{ summary.queryStateLabel }}
        </span>
      </div>
      <div class="header-tags">
        <el-tag
          :type="summary.parityTone"
          effect="plain"
          data-testid="cand538-sales-order-downstream-marker-parity"
        >
          {{ summary.parityLabel }}
        </el-tag>
        <el-tag
          :type="summary.focusTone"
          effect="plain"
          data-testid="cand538-sales-order-downstream-marker-focus"
        >
          {{ summary.focusLabel }}
        </el-tag>
        <el-tag
          :type="summary.stateTone"
          effect="plain"
          data-testid="cand538-sales-order-downstream-marker-state"
        >
          {{ summary.stateLabel }}
        </el-tag>
        <el-tag
          :type="summary.sourceStatusTone"
          effect="plain"
          data-testid="cand538-sales-order-downstream-source-status"
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
      data-testid="cand538-sales-order-downstream-blocked-reason"
    />

    <el-alert
      type="info"
      :closable="false"
      :title="summary.readonlyGuardReason"
      data-testid="cand538-sales-order-downstream-readonly-guard"
    />

    <el-alert
      type="info"
      :closable="false"
      :title="summary.remainingGap"
      data-testid="cand538-sales-order-downstream-remaining-gap"
    />

    <el-descriptions border :column="2" class="readonly-descriptions">
      <el-descriptions-item label="写入边界">
        <span data-testid="cand538-sales-order-downstream-write-boundary">
          {{ summary.writeBoundary }}
        </span>
      </el-descriptions-item>
      <el-descriptions-item label="来源状态">
        <span data-testid="cand538-sales-order-downstream-source-status-text">
          {{ summary.sourceStatusLabel }}
        </span>
      </el-descriptions-item>
      <el-descriptions-item label="伙伴/条目状态">
        <span data-testid="cand538-sales-order-downstream-item-status">
          {{ summary.itemStatusLabel }}
        </span>
      </el-descriptions-item>
      <el-descriptions-item label="聚焦来源">
        <span data-testid="cand538-sales-order-downstream-focus-text">
          {{ summary.focusLabel }}
        </span>
      </el-descriptions-item>
      <el-descriptions-item label="联动状态">{{ summary.stateLabel }}</el-descriptions-item>
      <el-descriptions-item label="只读守卫">{{ summary.readonlyGuardReason }}</el-descriptions-item>
    </el-descriptions>

    <div
      class="guarded-actions"
      data-testid="cand538-sales-order-downstream-guarded-actions"
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

    <el-table
      :data="summary.items"
      border
      size="small"
      empty-text="暂无 downstream guard 只读条目"
      data-testid="cand538-sales-order-downstream-item-table"
    >
      <el-table-column prop="subjectLabel" label="伙伴 / 条目" min-width="200" />
      <el-table-column prop="statusLabel" label="状态" min-width="160" />
      <el-table-column prop="sourceLabel" label="来源 / focus" min-width="220" />
      <el-table-column prop="blockedReason" label="阻断原因" min-width="240" />
    </el-table>
  </section>
</template>

<script setup lang="ts">
import type { SalesOrderDownstreamGuardReadonlyViewSummary } from '@/views/sales_inventory/composables/useSalesOrderDownstreamGuardReadonly'

defineProps<{
  summary: SalesOrderDownstreamGuardReadonlyViewSummary
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
.summary-label {
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

.readonly-descriptions :deep(.el-descriptions__label) {
  width: 120px;
}
</style>
