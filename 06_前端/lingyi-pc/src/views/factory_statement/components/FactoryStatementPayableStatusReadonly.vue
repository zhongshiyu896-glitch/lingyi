<template>
  <section class="payable-shell" data-testid="factory-statement-payable-readonly">
    <div class="payable-header">
      <div class="title-group">
        <span class="title">payable 状态 / 打印镜像只读回退</span>
        <span class="note">{{ summary.sourceLabel }}</span>
      </div>
      <div class="header-tags">
        <el-tag :type="summary.parityTone" effect="plain" data-testid="factory-statement-foundation-factory-parity-tag">
          {{ summary.parityLabel }}
        </el-tag>
        <el-tag :type="summary.payableStatusTone" effect="plain" data-testid="factory-statement-payable-status-tag">
          {{ summary.payableStatusLabel }}
        </el-tag>
        <el-tag :type="summary.payableBlockedTone" effect="plain" data-testid="factory-statement-payable-guard-tag">
          {{ summary.payableBlockedLabel }}
        </el-tag>
      </div>
    </div>

    <div class="summary-grid">
      <div v-for="field in FACTORY_STATEMENT_PAYABLE_FIELDS" :key="field.key" class="summary-card">
        <span class="summary-label">{{ field.label }}</span>
        <strong class="summary-value">{{ summaryValue(field.key) }}</strong>
      </div>
    </div>

    <el-alert
      type="warning"
      :closable="false"
      :title="summary.sourceGapPrompt"
      data-testid="factory-statement-payable-source-gap"
    />

    <el-alert
      type="info"
      :closable="false"
      :title="summary.readonlyGuardReason"
      data-testid="factory-statement-payable-readonly-guard"
    />

    <el-alert
      type="info"
      :closable="false"
      :title="summary.remainingGap"
      data-testid="factory-statement-payable-remaining-gap"
    />

    <el-descriptions border :column="3" class="payable-descriptions">
      <el-descriptions-item label="当前入口">{{ summary.parityScopeLabel }}</el-descriptions-item>
      <el-descriptions-item label="写入边界">{{ summary.writeBoundary }}</el-descriptions-item>
      <el-descriptions-item label="CAND116">
        <span data-testid="factory-statement-cand116-retained">
          {{ summary.retainedCand116 ? '详情/打印基础回读 retained' : '未保留' }}
        </span>
      </el-descriptions-item>
    </el-descriptions>
  </section>
</template>

<script setup lang="ts">
import type { FactoryStatementPayableReadonlySummary } from '@/views/factory_statement/composables/useFactoryStatementPayableReadonly'
import {
  FACTORY_STATEMENT_PAYABLE_FIELDS,
  type FactoryStatementPayableFieldKey,
} from '@/views/factory_statement/constants/factoryStatementPayableFields'

const props = defineProps<{
  summary: FactoryStatementPayableReadonlySummary
}>()

const summaryValue = (key: FactoryStatementPayableFieldKey): string => {
  switch (key) {
    case 'payableInvoiceLabel':
      return props.summary.payableInvoiceLabel
    case 'latestOutboxStatusLabel':
      return props.summary.latestOutboxStatusLabel
    case 'payableOutboxCountLabel':
      return props.summary.payableOutboxCountLabel
    case 'payableErrorLabel':
      return props.summary.payableErrorLabel
    default:
      return '-'
  }
}
</script>

<style scoped>
.payable-shell {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.payable-header {
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
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
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
</style>
