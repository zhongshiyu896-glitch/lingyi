<template>
  <section class="matrix-shell" data-testid="cand133-sales-order-matrix-readonly">
    <div class="matrix-header">
      <div class="matrix-title-group">
        <span class="matrix-title">数量矩阵 / 交付进度扩展</span>
        <span class="matrix-note">{{ matrixCoverageNote }}</span>
      </div>
      <el-tag type="warning" effect="plain">readonly matrix</el-tag>
    </div>

    <div class="summary-grid">
      <div v-for="field in SALES_ORDER_MATRIX_SUMMARY_FIELDS" :key="field.key" class="summary-card">
        <span class="summary-label">{{ field.label }}</span>
        <strong class="summary-value">{{ summaryValue(field.key) }}</strong>
      </div>
    </div>

    <el-alert
      type="info"
      :closable="false"
      class="matrix-guard"
      :title="guardMessage"
      data-testid="cand133-sales-order-matrix-guard"
    />

    <el-table
      :data="summary.rows"
      border
      class="matrix-table"
      empty-text="暂无可展示的颜色尺码矩阵"
      data-testid="cand133-sales-order-matrix-table"
    >
      <el-table-column prop="styleKey" label="款式聚合" min-width="160" />
      <el-table-column prop="color" label="颜色" min-width="100" />
      <el-table-column prop="size" label="尺码" min-width="100" />
      <el-table-column label="订单数量" min-width="110">
        <template #default="{ row }">{{ formatNumber(row.orderedQty) }}</template>
      </el-table-column>
      <el-table-column label="已交数量" min-width="110">
        <template #default="{ row }">{{ formatNumber(row.deliveredQty) }}</template>
      </el-table-column>
      <el-table-column label="未交数量" min-width="110">
        <template #default="{ row }">{{ formatNumber(row.remainingQty) }}</template>
      </el-table-column>
      <el-table-column prop="completionRateLabel" label="完成率" min-width="100" />
      <el-table-column prop="deliveryDateLabel" label="承诺交期" min-width="120" />
      <el-table-column label="交付状态" min-width="120">
        <template #default="{ row }">
          <el-tag :type="progressTagType(row.progressState)" effect="plain">
            {{ progressLabel(row.progressState) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="sourceItemsLabel" label="来源款号" min-width="220" show-overflow-tooltip />
    </el-table>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { SalesOrderQuantityMatrixReadonlySummary } from '@/api/sales_inventory_sales_orders'
import {
  SALES_ORDER_MATRIX_PROGRESS_LABELS,
  SALES_ORDER_MATRIX_PROGRESS_TAGS,
  SALES_ORDER_MATRIX_SUMMARY_FIELDS,
  type SalesOrderMatrixProgressState,
} from '@/views/sales_inventory/constants/salesOrderMatrixFields'

const props = defineProps<{
  summary: SalesOrderQuantityMatrixReadonlySummary
  formatNumber: (value?: string | number | null, digits?: number) => string
}>()

const guardMessage = computed(
  () =>
    '数量矩阵只开放只读核对；create / update / delete / export / inventory impact 均保持 guarded readonly，不触发真实销售写链路。',
)

const matrixCoverageNote = computed(
  () =>
    `已交 ${props.formatNumber(props.summary.totalDeliveredQty)} / 订单 ${props.formatNumber(props.summary.totalOrderedQty)}，待交 ${props.formatNumber(props.summary.totalRemainingQty)}。`,
)

const summaryValue = (key: (typeof SALES_ORDER_MATRIX_SUMMARY_FIELDS)[number]['key']): string => {
  switch (key) {
    case 'matrixCellCount':
      return String(props.summary.matrixCellCount)
    case 'colorCount':
      return String(props.summary.colorCount)
    case 'sizeCount':
      return String(props.summary.sizeCount)
    case 'delayedLineCount':
      return String(props.summary.delayedLineCount)
    case 'completedLineCount':
      return String(props.summary.completedLineCount)
    case 'matrixCompletionRateLabel':
      return props.summary.matrixCompletionRateLabel
    default:
      return '-'
  }
}

const progressLabel = (state: SalesOrderMatrixProgressState): string => SALES_ORDER_MATRIX_PROGRESS_LABELS[state]

const progressTagType = (
  state: SalesOrderMatrixProgressState,
): 'info' | 'primary' | 'warning' | 'success' | 'danger' => SALES_ORDER_MATRIX_PROGRESS_TAGS[state]
</script>

<style scoped>
.matrix-shell {
  margin-bottom: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.matrix-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.matrix-title-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.matrix-title {
  font-size: 16px;
  font-weight: 600;
}

.matrix-note {
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

.matrix-guard {
  margin: 0;
}

.matrix-table {
  width: 100%;
}
</style>
