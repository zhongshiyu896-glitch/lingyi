<template>
  <section class="guard-shell" data-testid="cand154-sales-order-downstream-guard">
    <div class="guard-header">
      <div class="guard-title-group">
        <span class="guard-title">来源完整度 / 下游联动前置守卫</span>
        <span class="guard-note">{{ summary.blockingReasonLabel }}</span>
      </div>
      <el-tag :type="stateTagType(summary.state)" effect="plain">
        {{ summary.stateLabel }}
      </el-tag>
    </div>

    <div class="summary-grid">
      <div
        v-for="field in SALES_ORDER_DOWNSTREAM_GUARD_SUMMARY_FIELDS"
        :key="field.key"
        class="summary-card"
      >
        <span class="summary-label">{{ field.label }}</span>
        <strong class="summary-value">{{ summaryValue(field.key) }}</strong>
      </div>
    </div>

    <el-alert
      type="warning"
      :closable="false"
      class="guard-alert"
      :title="summary.guardReason"
      data-testid="cand154-sales-order-downstream-guard-alert"
    />

    <el-descriptions
      border
      :column="3"
      class="guard-summary"
      data-testid="cand154-sales-order-downstream-guard-summary"
    >
      <el-descriptions-item label="来源完整度">{{ summary.sourceCompletenessLabel }}</el-descriptions-item>
      <el-descriptions-item label="生产联动">{{ summary.productionGuardLabel }}</el-descriptions-item>
      <el-descriptions-item label="采购联动">{{ summary.purchaseGuardLabel }}</el-descriptions-item>
      <el-descriptions-item label="阻断原因">{{ summary.blockingReasonLabel }}</el-descriptions-item>
      <el-descriptions-item label="只读动作">create / update / delete / export disabled</el-descriptions-item>
      <el-descriptions-item label="remaining_gap">真实保存、库存影响、销售写入仍未开放</el-descriptions-item>
    </el-descriptions>

    <div class="guard-columns">
      <section class="guard-column" data-testid="cand154-sales-order-downstream-missing-tags">
        <header class="column-title">缺失桥接 / 阻断项</header>
        <div class="tag-group">
          <el-tag
            v-for="tag in summary.missingBridgeTags"
            :key="tag"
            type="danger"
            effect="plain"
          >
            {{ tag }}
          </el-tag>
          <span v-if="summary.missingBridgeTags.length === 0" class="empty-note">当前无桥接缺失项</span>
        </div>
      </section>

      <section class="guard-column" data-testid="cand154-sales-order-downstream-readonly-tags">
        <header class="column-title">只读 guard 状态</header>
        <div class="tag-group">
          <el-tag
            v-for="tag in summary.readonlyGuardTags"
            :key="tag"
            type="info"
            effect="plain"
          >
            {{ tag }}
          </el-tag>
        </div>
      </section>
    </div>

    <el-table
      :data="summary.actions"
      border
      class="guard-table"
      data-testid="cand154-sales-order-downstream-actions"
    >
      <el-table-column prop="label" label="动作" min-width="140" />
      <el-table-column label="状态" min-width="120">
        <template #default="{ row }">
          <el-tag :type="actionTagType(row.state)" effect="plain">
            {{ row.stateLabel }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="reason" label="原因" min-width="280" />
    </el-table>
  </section>
</template>

<script setup lang="ts">
import type { SalesOrderDownstreamGuardReadonlySummary } from '@/api/sales_inventory_sales_orders'
import {
  SALES_ORDER_DOWNSTREAM_GUARD_ACTION_TAGS,
  SALES_ORDER_DOWNSTREAM_GUARD_STATE_TAGS,
  SALES_ORDER_DOWNSTREAM_GUARD_SUMMARY_FIELDS,
  type SalesOrderDownstreamGuardActionState,
  type SalesOrderDownstreamGuardState,
} from '@/views/sales_inventory/constants/salesOrderDownstreamGuardFields'

const props = defineProps<{
  summary: SalesOrderDownstreamGuardReadonlySummary
}>()

const summaryValue = (
  key: (typeof SALES_ORDER_DOWNSTREAM_GUARD_SUMMARY_FIELDS)[number]['key'],
): string => {
  switch (key) {
    case 'sourceCompletenessLabel':
      return props.summary.sourceCompletenessLabel
    case 'downstreamStateLabel':
      return props.summary.downstreamStateLabel
    case 'productionGuardLabel':
      return props.summary.productionGuardLabel
    case 'purchaseGuardLabel':
      return props.summary.purchaseGuardLabel
    case 'blockingCount':
      return String(props.summary.blockingCount)
    default:
      return '-'
  }
}

const stateTagType = (
  state: SalesOrderDownstreamGuardState,
): 'success' | 'warning' | 'danger' => SALES_ORDER_DOWNSTREAM_GUARD_STATE_TAGS[state]

const actionTagType = (
  state: SalesOrderDownstreamGuardActionState,
): 'success' | 'warning' | 'info' => SALES_ORDER_DOWNSTREAM_GUARD_ACTION_TAGS[state]
</script>

<style scoped>
.guard-shell {
  margin-bottom: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.guard-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.guard-title-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.guard-title {
  font-size: 16px;
  font-weight: 600;
}

.guard-note,
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

.guard-columns {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
}

.guard-column {
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

.guard-table {
  width: 100%;
}
</style>
