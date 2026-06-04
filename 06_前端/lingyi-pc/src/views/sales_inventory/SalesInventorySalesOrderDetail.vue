<template>
  <div class="sales-order-detail-page" data-testid="cand104-sales-order-detail-page">
    <el-card shadow="never" data-testid="cand104-sales-order-detail-shell">
      <template #header>
        <div class="header-row">
          <div class="title-group">
            <span class="title">大货管理 / 销售订单详情回读</span>
            <span class="sub-title">NEXT-CAND-104 / detail readonly summary</span>
          </div>
          <div class="header-actions">
            <el-button @click="goList">返回列表</el-button>
            <el-button type="primary" plain :loading="loading" @click="refreshDetail">刷新</el-button>
          </div>
        </div>
      </template>

      <el-alert
        type="info"
        :closable="false"
        class="scope-alert"
        title="当前仅开放销售订单详情只读查询，不触发草稿写入、库存影响、导出或 ERPNext 写链路。"
      />

      <el-alert
        v-if="usedFallbackOrder"
        type="info"
        :closable="false"
        class="scope-alert"
        title="未指定订单号，当前展示首条可读销售订单。"
      />

      <el-alert
        v-if="lastError"
        type="error"
        :closable="false"
        class="error-alert"
        :title="lastError"
        data-testid="cand104-sales-order-detail-error"
      />

      <section class="guarded-actions-panel" data-testid="cand104-sales-order-detail-guarded-actions">
        <el-button
          v-for="action in readonlyGuardActions"
          :key="action.label"
          disabled
          data-action-type="write"
          data-guard-state="disabled"
        >
          {{ action.label }}
        </el-button>
      </section>

      <template v-if="detail">
        <section class="summary-grid" data-testid="cand104-sales-order-detail-stat-grid">
          <div class="summary-card">
            <span class="summary-label">明细行数</span>
            <strong class="summary-value">{{ detailReadonlySummary.itemCount }}</strong>
          </div>
          <div class="summary-card">
            <span class="summary-label">订单数量</span>
            <strong class="summary-value">{{ formatNumber(detailReadonlySummary.totalOrderedQty) }}</strong>
          </div>
          <div class="summary-card">
            <span class="summary-label">已交数量</span>
            <strong class="summary-value">{{ formatNumber(detailReadonlySummary.deliveredQty) }}</strong>
          </div>
          <div class="summary-card">
            <span class="summary-label">未交数量</span>
            <strong class="summary-value">{{ formatNumber(detailReadonlySummary.remainingQty) }}</strong>
          </div>
          <div class="summary-card">
            <span class="summary-label">主款号</span>
            <strong class="summary-value">{{ detailReadonlySummary.primaryItemCode }}</strong>
          </div>
          <div class="summary-card">
            <span class="summary-label">交付进度</span>
            <strong class="summary-value">{{ detailReadonlySummary.deliveryCompletionRatio }}</strong>
          </div>
        </section>

        <el-descriptions
          border
          :column="3"
          class="header-summary"
          data-testid="cand104-sales-order-detail-summary"
        >
          <el-descriptions-item label="订单号">{{ detail.name }}</el-descriptions-item>
          <el-descriptions-item label="公司">{{ detail.company }}</el-descriptions-item>
          <el-descriptions-item label="客户">{{ customerLabel(detail.customer) }}</el-descriptions-item>
          <el-descriptions-item label="下单日期">{{ detail.transaction_date || '-' }}</el-descriptions-item>
          <el-descriptions-item label="交期">{{ detail.delivery_date || '-' }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="statusType(detail.status)" effect="plain">
              {{ statusLabel(detail.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="跟进分组">
            <el-tag :type="followupGroupType(detailGroup)" effect="plain">
              {{ followupGroupLabel(detailGroup) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="单据状态">{{ detail.docstatus }}</el-descriptions-item>
          <el-descriptions-item label="金额">
            {{ formatMoney(detail.grand_total, detail.currency) }}
          </el-descriptions-item>
          <el-descriptions-item label="币种">{{ detail.currency || '-' }}</el-descriptions-item>
          <el-descriptions-item label="主款名称">{{ detailReadonlySummary.primaryItemName }}</el-descriptions-item>
          <el-descriptions-item label="只读动作">guarded / disabled</el-descriptions-item>
        </el-descriptions>

        <section class="readonly-panel" data-testid="cand104-sales-order-detail-readback-notes">
          <el-descriptions border :column="3">
            <el-descriptions-item label="route_scope">/sales-inventory/sales-orders/detail</el-descriptions-item>
            <el-descriptions-item label="最后刷新">{{ lastLoadedAt || '-' }}</el-descriptions-item>
            <el-descriptions-item label="write_chain">disabled</el-descriptions-item>
            <el-descriptions-item label="当前客户">{{ customerLabel(detail.customer) }}</el-descriptions-item>
            <el-descriptions-item label="主款号">{{ detailReadonlySummary.primaryItemCode }}</el-descriptions-item>
            <el-descriptions-item label="交付进度">{{ detailReadonlySummary.deliveryCompletionRatio }}</el-descriptions-item>
            <el-descriptions-item label="矩阵格数">{{ quantityMatrixReadonlySummary.matrixCellCount }}</el-descriptions-item>
            <el-descriptions-item label="延期格数">{{ quantityMatrixReadonlySummary.delayedLineCount }}</el-descriptions-item>
            <el-descriptions-item label="矩阵完成率">
              {{ quantityMatrixReadonlySummary.matrixCompletionRateLabel }}
            </el-descriptions-item>
          </el-descriptions>
        </section>

        <SalesOrderQuantityMatrixReadonly
          :summary="quantityMatrixReadonlySummary"
          :format-number="formatNumber"
        />

        <el-table
          v-loading="loading"
          :data="detail.items"
          border
          class="detail-table"
          :empty-text="detailEmptyText"
          data-testid="cand104-sales-order-detail-items"
        >
          <el-table-column prop="item_code" label="款号" min-width="150" />
          <el-table-column prop="item_name" label="物料名称" min-width="180" />
          <el-table-column label="订单数量" min-width="110">
            <template #default="{ row }">{{ formatNumber(row.qty) }}</template>
          </el-table-column>
          <el-table-column label="已交数量" min-width="110">
            <template #default="{ row }">{{ formatNumber(row.delivered_qty) }}</template>
          </el-table-column>
          <el-table-column label="未交数量" min-width="110">
            <template #default="{ row }">
              {{ formatNumber(Math.max(toNumeric(row.qty) - toNumeric(row.delivered_qty), 0)) }}
            </template>
          </el-table-column>
          <el-table-column label="单价" min-width="110">
            <template #default="{ row }">{{ formatNumber(row.rate) }}</template>
          </el-table-column>
          <el-table-column label="金额" min-width="120">
            <template #default="{ row }">{{ formatMoney(row.amount, detail.currency) }}</template>
          </el-table-column>
          <el-table-column prop="warehouse" label="仓库" min-width="140" />
          <el-table-column prop="delivery_date" label="交期" min-width="120" />
        </el-table>
      </template>

      <el-empty
        v-else-if="!loading && !lastError"
        description="暂无可查看的销售订单"
        data-testid="cand104-sales-order-detail-empty"
      />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { SalesOrderDetailData } from '@/api/sales_inventory'
import {
  fetchSalesInventorySalesOrderDetailReadback,
  resolveFallbackSalesOrderName,
  type SalesOrderReadonlyGroup,
} from '@/api/sales_inventory_sales_orders'
import SalesOrderQuantityMatrixReadonly from '@/views/sales_inventory/components/SalesOrderQuantityMatrixReadonly.vue'
import { useSalesOrderReadback } from '@/views/sales_inventory/composables/useSalesOrderReadback'

const route = useRoute()
const router = useRouter()

const {
  customerLabel,
  detailSummary,
  followupGroupFromRow,
  followupGroupLabel,
  followupGroupType,
  formatNumber,
  parseQueryString,
  quantityMatrixSummary,
  readonlyGuardActions,
  statusLabel,
  statusType,
} = useSalesOrderReadback()

const loading = ref(false)
const lastError = ref('')
const detail = ref<SalesOrderDetailData | null>(null)
const usedFallbackOrder = ref(false)
const lastLoadedAt = ref('')

const routeOrderName = computed(() => parseQueryString(route.query.name))
const detailReadonlySummary = computed(() =>
  detail.value
    ? detailSummary(detail.value)
    : {
        itemCount: 0,
        totalOrderedQty: 0,
        deliveredQty: 0,
        remainingQty: 0,
        primaryItemCode: '-',
        primaryItemName: '-',
        deliveryCompletionRatio: '0%',
      },
)
const detailGroup = computed<SalesOrderReadonlyGroup>(() =>
  detail.value ? followupGroupFromRow(detail.value) : 'draft-watch',
)
const quantityMatrixReadonlySummary = computed(() =>
  detail.value
    ? quantityMatrixSummary(detail.value)
    : {
        matrixCellCount: 0,
        colorCount: 0,
        sizeCount: 0,
        delayedLineCount: 0,
        completedLineCount: 0,
        inProgressLineCount: 0,
        totalOrderedQty: 0,
        totalDeliveredQty: 0,
        totalRemainingQty: 0,
        matrixCompletionRate: 0,
        matrixCompletionRateLabel: '0%',
        rows: [],
      },
)

const detailEmptyText = computed(() => {
  if (loading.value) return '正在加载订单详情'
  if (lastError.value) return '订单详情加载失败'
  return '暂无订单明细'
})

const formatMoney = (amount?: string | number | null, currency?: string | null): string => {
  if (amount === null || amount === undefined || amount === '') return '-'
  const numeric = Number(amount)
  if (!Number.isFinite(numeric)) return String(amount)
  const money = numeric.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  return currency ? `${money} ${currency}` : money
}

const toNumeric = (value?: string | number | null): number => {
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric : 0
}

const updateLoadedAt = (): void => {
  lastLoadedAt.value = new Date().toISOString()
}

const resolveOrderName = async (): Promise<string> => {
  if (routeOrderName.value) {
    usedFallbackOrder.value = false
    return routeOrderName.value
  }
  const fallback = await resolveFallbackSalesOrderName()
  usedFallbackOrder.value = Boolean(fallback)
  return fallback
}

const loadDetail = async (): Promise<void> => {
  loading.value = true
  lastError.value = ''
  detail.value = null
  try {
    const orderName = await resolveOrderName()
    if (!orderName) {
      lastError.value = '暂无可查看的销售订单'
      return
    }
    const response = await fetchSalesInventorySalesOrderDetailReadback(orderName)
    detail.value = response.data
    updateLoadedAt()
  } catch (error) {
    lastError.value = (error as Error).message || '订单详情加载失败'
  } finally {
    loading.value = false
  }
}

const refreshDetail = (): void => {
  void loadDetail()
}

const goList = (): void => {
  router.push('/sales-inventory/sales-orders')
}

watch(routeOrderName, () => {
  void loadDetail()
})

onMounted(() => {
  void loadDetail()
})
</script>

<style scoped>
.sales-order-detail-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.title-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.title {
  font-size: 18px;
  font-weight: 600;
}

.sub-title {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.header-actions,
.guarded-actions-panel {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.scope-alert,
.error-alert {
  margin-bottom: 16px;
}

.summary-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  margin-bottom: 16px;
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

.header-summary,
.readonly-panel {
  margin-bottom: 16px;
}

.detail-table {
  width: 100%;
}
</style>
