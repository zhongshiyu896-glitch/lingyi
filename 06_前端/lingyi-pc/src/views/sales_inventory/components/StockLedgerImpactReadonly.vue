<template>
  <section class="readonly-shell" data-testid="stock-ledger-impact-readonly">
    <div class="readonly-header">
      <div class="title-group">
        <span class="title">StockLedger 库存影响只读回退</span>
        <span class="note">{{ summary.sourceLabel }}</span>
      </div>
      <div class="header-tags">
        <el-tag :type="summary.parityTone" effect="plain" data-testid="stock-ledger-impact-parity-tag">
          {{ summary.parityLabel }}
        </el-tag>
        <el-tag :type="summary.impactStatusTone" effect="plain" data-testid="stock-ledger-impact-status-tag">
          {{ summary.impactStatusLabel }}
        </el-tag>
        <el-tag :type="summary.safetyStatusTone" effect="plain" data-testid="stock-ledger-safety-status-tag">
          {{ summary.safetyStatusLabel }}
        </el-tag>
        <el-tag :type="summary.readonlyGuardTone" effect="plain" data-testid="stock-ledger-readonly-guard-tag">
          {{ summary.readonlyGuardLabel }}
        </el-tag>
      </div>
    </div>

    <div class="summary-grid">
      <div v-for="field in STOCK_LEDGER_IMPACT_FIELDS" :key="field.key" class="summary-card">
        <span class="summary-label">{{ field.label }}</span>
        <strong class="summary-value">{{ summaryValue(field.key) }}</strong>
      </div>
    </div>

    <el-alert
      type="warning"
      :closable="false"
      :title="summary.sourceGapPrompt"
      data-testid="stock-ledger-impact-source-gap"
    />

    <el-alert
      type="info"
      :closable="false"
      :title="summary.readonlyGuardReason"
      data-testid="stock-ledger-impact-readonly-guard"
    />

    <el-alert
      type="info"
      :closable="false"
      :title="summary.remainingGap"
      data-testid="stock-ledger-impact-remaining-gap"
    />

    <el-descriptions border :column="2" class="readonly-descriptions">
      <el-descriptions-item label="当前入口">{{ summary.parityScopeLabel }}</el-descriptions-item>
      <el-descriptions-item label="批次关系">
        <span data-testid="stock-ledger-impact-batch-relation">{{ summary.relationSummary }}</span>
      </el-descriptions-item>
      <el-descriptions-item label="写入边界">{{ summary.writeBoundary }}</el-descriptions-item>
      <el-descriptions-item label="CAND014">
        <span data-testid="stock-ledger-impact-cand014-retained">
          {{ summary.retainedCand014 ? '仓库看板基础能力 retained' : '未保留' }}
        </span>
      </el-descriptions-item>
      <el-descriptions-item label="CAND032">
        <span data-testid="stock-ledger-impact-cand032-retained">
          {{ summary.retainedCand032 ? '仓库追踪链能力 retained' : '未保留' }}
        </span>
      </el-descriptions-item>
    </el-descriptions>
  </section>
</template>

<script setup lang="ts">
import type { StockLedgerImpactReadonlySummary } from '@/views/sales_inventory/composables/useStockLedgerImpactReadonly'
import {
  STOCK_LEDGER_IMPACT_FIELDS,
  type StockLedgerImpactFieldKey,
} from '@/views/sales_inventory/composables/useStockLedgerImpactReadonly'

const props = defineProps<{
  summary: StockLedgerImpactReadonlySummary
}>()

const summaryValue = (key: StockLedgerImpactFieldKey): string => {
  switch (key) {
    case 'summaryBalanceQtyLabel':
      return props.summary.summaryBalanceQtyLabel
    case 'actualQtyTotalLabel':
      return props.summary.actualQtyTotalLabel
    case 'orderedQtyTotalLabel':
      return props.summary.orderedQtyTotalLabel
    case 'indentedQtyTotalLabel':
      return props.summary.indentedQtyTotalLabel
    case 'warehouseCountLabel':
      return props.summary.warehouseCountLabel
    case 'belowSafetyCountLabel':
      return props.summary.belowSafetyCountLabel
    default:
      return '-'
  }
}
</script>

<style scoped>
.readonly-shell {
  margin: 12px 0;
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

.header-tags {
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
