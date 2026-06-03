<template>
  <div class="sales-order-detail-page" data-testid="cand013-sales-order-detail-page">
    <el-card shadow="never" data-testid="cand013-sales-order-detail-shell">
      <template #header>
        <div class="header-row">
          <div class="title-group">
            <span class="title">物料进销存 / 销售订单详情</span>
            <span class="sub-title">本地只读详情首版</span>
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
        title="当前仅开放销售订单详情只读查询，不触发 draft create/cancel、库存写回或 ERPNext 生产写入。"
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
        data-testid="cand013-sales-order-detail-error"
      />

      <template v-if="detail">
        <el-descriptions
          border
          :column="3"
          class="header-summary"
          data-testid="cand013-sales-order-detail-summary"
        >
          <el-descriptions-item label="订单号">{{ detail.name }}</el-descriptions-item>
          <el-descriptions-item label="公司">{{ detail.company }}</el-descriptions-item>
          <el-descriptions-item label="客户">{{ detail.customer || '-' }}</el-descriptions-item>
          <el-descriptions-item label="下单日期">{{ detail.transaction_date || '-' }}</el-descriptions-item>
          <el-descriptions-item label="交期">{{ detail.delivery_date || '-' }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="statusTagType(detail.status)" effect="plain">
              {{ detail.status || '未标记' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="单据状态">{{ detail.docstatus }}</el-descriptions-item>
          <el-descriptions-item label="金额">
            {{ formatMoney(detail.grand_total, detail.currency) }}
          </el-descriptions-item>
          <el-descriptions-item label="币种">{{ detail.currency || '-' }}</el-descriptions-item>
        </el-descriptions>

        <el-table
          v-loading="loading"
          :data="detail.items"
          border
          class="detail-table"
          :empty-text="detailEmptyText"
          data-testid="cand013-sales-order-detail-items"
        >
          <el-table-column prop="item_code" label="款号" min-width="150" />
          <el-table-column prop="item_name" label="物料名称" min-width="180" />
          <el-table-column label="订单数量" min-width="110">
            <template #default="{ row }">{{ formatNumber(row.qty) }}</template>
          </el-table-column>
          <el-table-column label="已交数量" min-width="110">
            <template #default="{ row }">{{ formatNumber(row.delivered_qty) }}</template>
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
        data-testid="cand013-sales-order-detail-empty"
      />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  fetchSalesInventorySalesOrderDetail,
  fetchSalesInventorySalesOrders,
  type SalesOrderDetailData,
} from '@/api/sales_inventory'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const lastError = ref('')
const detail = ref<SalesOrderDetailData | null>(null)
const usedFallbackOrder = ref(false)

const routeOrderName = computed(() => {
  const raw = Array.isArray(route.query.name) ? route.query.name[0] : route.query.name
  return typeof raw === 'string' ? raw.trim() : ''
})

const detailEmptyText = computed(() => {
  if (loading.value) return '正在加载订单详情'
  if (lastError.value) return '订单详情加载失败'
  return '暂无订单明细'
})

const statusTagType = (status?: string | null): 'success' | 'warning' | 'info' => {
  if (status === 'Completed' || status === 'To Deliver and Bill') return 'success'
  if (status === 'Draft' || status === 'To Bill') return 'warning'
  return 'info'
}

const formatNumber = (value?: string | number | null): string => {
  if (value === null || value === undefined || value === '') return '-'
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) return String(value)
  return numeric.toLocaleString('zh-CN', { maximumFractionDigits: 2 })
}

const formatMoney = (amount?: string | number | null, currency?: string | null): string => {
  if (amount === null || amount === undefined || amount === '') return '-'
  const numeric = Number(amount)
  if (!Number.isFinite(numeric)) return String(amount)
  const money = numeric.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  return currency ? `${money} ${currency}` : money
}

const resolveOrderName = async (): Promise<string> => {
  if (routeOrderName.value) {
    usedFallbackOrder.value = false
    return routeOrderName.value
  }
  const response = await fetchSalesInventorySalesOrders({ page: 1, page_size: 1 })
  const fallback = response.data.items[0]?.name || ''
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
    const response = await fetchSalesInventorySalesOrderDetail(orderName)
    detail.value = response.data
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

.header-actions {
  display: flex;
  gap: 8px;
}

.scope-alert,
.error-alert {
  margin-bottom: 16px;
}

.header-summary {
  margin-bottom: 16px;
}

.detail-table {
  width: 100%;
}
</style>
