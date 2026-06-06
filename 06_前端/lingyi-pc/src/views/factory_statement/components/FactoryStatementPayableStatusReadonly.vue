<template>
  <section class="payable-shell" data-testid="factory-statement-payable-readonly">
    <div class="payable-header">
      <div class="title-group">
        <span class="title">加工厂对账应付状态只读摘要</span>
        <span class="note">{{ summary.sourceLabel }}</span>
      </div>
      <div class="header-tags">
        <el-tag effect="plain" data-testid="factory-statement-payable-get-only">GET-only</el-tag>
        <el-tag type="info" effect="plain" data-testid="factory-statement-payable-query-state">
          {{ summary.queryStateLabel }}
        </el-tag>
        <el-tag :type="summary.parityTone" effect="plain" data-testid="factory-statement-foundation-factory-parity-tag">
          {{ summary.parityLabel }}
        </el-tag>
        <el-tag type="warning" effect="plain" data-testid="factory-statement-payable-focus-state">
          {{ summary.focusLabel }}
        </el-tag>
        <el-tag :type="summary.payableStatusTone" effect="plain" data-testid="factory-statement-payable-status-tag">
          {{ summary.payableStatusLabel }}
        </el-tag>
        <el-tag :type="summary.payableBlockedTone" effect="plain" data-testid="factory-statement-payable-guard-tag">
          {{ summary.payableBlockedLabel }}
        </el-tag>
      </div>
    </div>

    <el-descriptions
      v-if="summary.routeItems.length"
      border
      :column="1"
      class="payable-route-scope"
      data-testid="factory-statement-payable-route-scope"
    >
      <el-descriptions-item
        v-for="item in summary.routeItems"
        :key="item.key"
        :label="item.label"
      >
        <span :data-testid="`factory-statement-payable-route-${item.key}`">{{ item.route }}</span>
        <el-tag
          size="small"
          effect="plain"
          :type="item.active ? 'success' : 'info'"
          style="margin-left: 8px"
        >
          {{ item.active ? 'active' : 'readonly' }}
        </el-tag>
        <span class="route-note">{{ item.note }}</span>
      </el-descriptions-item>
    </el-descriptions>

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
      <el-descriptions-item label="source/status">
        <span data-testid="factory-statement-payable-source-status">{{ summary.sourceStatusLabel }}</span>
      </el-descriptions-item>
      <el-descriptions-item label="item/status">
        <span data-testid="factory-statement-payable-item-status">{{ summary.payableItemStatusLabel }}</span>
      </el-descriptions-item>
      <el-descriptions-item label="写入边界">{{ summary.writeBoundary }}</el-descriptions-item>
      <el-descriptions-item label="CAND116">
        <span data-testid="factory-statement-cand116-retained">
          {{ summary.retainedCand116 ? '详情/打印基础回读 retained' : '未保留' }}
        </span>
      </el-descriptions-item>
    </el-descriptions>

    <div class="guard-grid" data-testid="factory-statement-payable-guard-grid">
      <div
        v-for="action in summary.guardActions"
        :key="action.key"
        class="guard-item"
        :data-testid="`factory-statement-payable-guard-${action.key}`"
      >
        <div class="guard-label">{{ action.label }}</div>
        <el-button size="small" disabled>{{ action.label }}</el-button>
        <div class="guard-hint">{{ action.reason }}</div>
      </div>
    </div>
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
.summary-label,
.guard-hint,
.route-note {
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

.payable-route-scope {
  margin-top: 4px;
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

.guard-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
}

.guard-item {
  border: 1px dashed var(--el-border-color);
  border-radius: 8px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  background: var(--el-fill-color-lighter);
}

.guard-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}
</style>
