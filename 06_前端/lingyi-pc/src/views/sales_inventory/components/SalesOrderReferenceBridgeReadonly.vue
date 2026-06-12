<template>
  <section class="bridge-shell" data-testid="cand146-sales-order-reference-bridge-readonly">
    <div class="bridge-header">
      <div class="bridge-title-group">
        <span class="bridge-title">引用链 / 客户工厂映射扩展</span>
        <span class="bridge-note">{{ summary.bridgeSummaryLabel }}</span>
      </div>
      <el-tag :type="completenessTagType(summary.completenessState)" effect="plain">
        {{ summary.completenessLabel }}
      </el-tag>
    </div>

    <div class="summary-grid">
      <div
        v-for="field in SALES_ORDER_REFERENCE_BRIDGE_SUMMARY_FIELDS"
        :key="field.key"
        class="summary-card"
      >
        <span class="summary-label">{{ field.label }}</span>
        <strong class="summary-value">{{ summaryValue(field.key) }}</strong>
      </div>
    </div>

    <el-alert
      type="info"
      :closable="false"
      class="bridge-guard"
      :title="summary.readonlyGuardReason"
      data-testid="cand146-sales-order-reference-bridge-guard"
    />

    <el-descriptions
      border
      :column="3"
      class="bridge-summary"
      data-testid="cand146-sales-order-reference-bridge-summary"
    >
      <el-descriptions-item label="来源单据">{{ summary.sourceDocumentLabel }}</el-descriptions-item>
      <el-descriptions-item label="来源类型">{{ summary.sourceTypeLabel }}</el-descriptions-item>
      <el-descriptions-item label="桥接摘要">{{ summary.mappingModeLabel }}</el-descriptions-item>
      <el-descriptions-item label="客户引用链">{{ summary.customerChainLabel }}</el-descriptions-item>
      <el-descriptions-item label="工厂引用链">{{ summary.factoryChainLabel }}</el-descriptions-item>
      <el-descriptions-item label="只读 guard">桥接链路保持只读展示，相关动作入口未开放</el-descriptions-item>
    </el-descriptions>

    <div class="bridge-columns">
      <section class="bridge-column" data-testid="cand146-sales-order-customer-chain">
        <header class="column-title">客户引用链</header>
        <div class="tag-group">
          <el-tag
            v-for="node in summary.customerNodes"
            :key="node.key"
            type="primary"
            effect="plain"
          >
            {{ node.label }} / {{ node.detail }}
          </el-tag>
        </div>
      </section>

      <section class="bridge-column" data-testid="cand146-sales-order-factory-chain">
        <header class="column-title">工厂映射</header>
        <div class="tag-group">
          <el-tag
            v-for="node in summary.factoryNodes"
            :key="node.key"
            :type="node.key === 'pending-factory' ? 'warning' : 'success'"
            effect="plain"
          >
            {{ node.label }} / {{ node.detail }}
          </el-tag>
        </div>
      </section>

      <section class="bridge-column" data-testid="cand146-sales-order-material-tags">
        <header class="column-title">物料明细标签</header>
        <div class="tag-group">
          <el-tag
            v-for="itemCode in summary.materialDetailTags"
            :key="itemCode"
            type="info"
            effect="plain"
          >
            {{ itemCode }}
          </el-tag>
          <span v-if="summary.materialDetailTags.length === 0" class="empty-note">暂无来源款号</span>
        </div>
      </section>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { SalesOrderReferenceBridgeReadonlySummary } from '@/api/sales_inventory_sales_orders'
import {
  SALES_ORDER_REFERENCE_BRIDGE_COMPLETENESS_TAGS,
  SALES_ORDER_REFERENCE_BRIDGE_SUMMARY_FIELDS,
  type SalesOrderReferenceBridgeCompletenessState,
} from '@/views/sales_inventory/constants/salesOrderReferenceBridgeFields'

const props = defineProps<{
  summary: SalesOrderReferenceBridgeReadonlySummary
}>()

const summaryValue = (
  key: (typeof SALES_ORDER_REFERENCE_BRIDGE_SUMMARY_FIELDS)[number]['key'],
): string => {
  switch (key) {
    case 'customerNodeCount':
      return String(props.summary.customerNodeCount)
    case 'factoryNodeCount':
      return String(props.summary.factoryNodeCount)
    case 'sourceDocumentCount':
      return String(props.summary.sourceDocumentCount)
    case 'mappingModeLabel':
      return props.summary.mappingModeLabel
    case 'completenessLabel':
      return props.summary.completenessLabel
    default:
      return '-'
  }
}

const completenessTagType = (
  state: SalesOrderReferenceBridgeCompletenessState,
): 'success' | 'warning' | 'danger' => SALES_ORDER_REFERENCE_BRIDGE_COMPLETENESS_TAGS[state]
</script>

<style scoped>
.bridge-shell {
  margin-bottom: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.bridge-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.bridge-title-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.bridge-title {
  font-size: 16px;
  font-weight: 600;
}

.bridge-note,
.empty-note {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.summary-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
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

.summary-label {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.summary-value {
  font-size: 18px;
}

.bridge-columns {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
}

.bridge-column {
  border: 1px solid var(--el-border-color-light);
  border-radius: 8px;
  padding: 12px 14px;
  background: var(--el-fill-color-blank);
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.column-title {
  font-size: 13px;
  font-weight: 600;
}

.tag-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
</style>
