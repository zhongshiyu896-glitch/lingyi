<template>
  <div class="sales-order-list-page" data-testid="cand013-sales-order-list-page">
    <el-card shadow="never" data-testid="cand013-sales-order-shell">
      <template #header>
        <div class="header-row">
          <div class="title-group">
            <span class="title">物料进销存 / 销售订单查询</span>
            <span class="sub-title">本地只读查询首版</span>
          </div>
          <el-tag type="info" effect="plain">local read-only</el-tag>
        </div>
      </template>

      <el-alert
        type="info"
        :closable="false"
        class="scope-alert"
        title="当前仅开放销售订单列表/详情只读查询，不触发 draft create/cancel、库存写回或 ERPNext 生产写入。"
      />

      <section class="query-panel" data-testid="cand013-sales-order-query-panel">
        <el-form :model="query" inline class="query-form">
          <el-form-item label="订单号">
            <el-input v-model="query.order_no" clearable placeholder="订单号" @keyup.enter="onSearch" />
          </el-form-item>
          <el-form-item label="关键字">
            <el-input v-model="query.keyword" clearable placeholder="订单号/客户/公司/状态" @keyup.enter="onSearch" />
          </el-form-item>
          <el-form-item label="客户">
            <el-input v-model="query.customer" clearable placeholder="客户名称" @keyup.enter="onSearch" />
          </el-form-item>
          <el-form-item label="公司">
            <el-input v-model="query.company" clearable placeholder="公司" @keyup.enter="onSearch" />
          </el-form-item>
          <el-form-item label="款号">
            <el-input v-model="query.item_code" clearable placeholder="款号" @keyup.enter="onSearch" />
          </el-form-item>
          <el-form-item label="开始日期">
            <el-date-picker
              v-model="query.from_date"
              type="date"
              value-format="YYYY-MM-DD"
              placeholder="开始日期"
              clearable
            />
          </el-form-item>
          <el-form-item label="结束日期">
            <el-date-picker
              v-model="query.to_date"
              type="date"
              value-format="YYYY-MM-DD"
              placeholder="结束日期"
              clearable
            />
          </el-form-item>
          <el-form-item>
            <el-button @click="onReset">重置</el-button>
            <el-button type="primary" @click="onSearch">查询</el-button>
          </el-form-item>
        </el-form>
      </section>

      <el-alert
        v-if="lastError"
        type="error"
        :closable="false"
        :title="lastError"
        class="error-alert"
        data-testid="cand013-sales-order-error"
      />

      <div class="summary-row" data-testid="cand013-sales-order-summary">
        <el-tag type="info" effect="plain">查询结果：{{ total }}</el-tag>
        <el-tag type="success" effect="plain">当前页：{{ rows.length }}</el-tag>
        <el-tag type="warning" effect="plain">只读详情可用</el-tag>
      </div>

      <el-table
        v-loading="loading"
        :data="rows"
        border
        class="result-table"
        :empty-text="emptyText"
        data-testid="cand013-sales-order-table"
      >
        <el-table-column prop="name" label="订单号" min-width="170" />
        <el-table-column prop="company" label="公司" min-width="140" />
        <el-table-column prop="customer" label="客户" min-width="150" />
        <el-table-column prop="transaction_date" label="下单日期" min-width="120" />
        <el-table-column prop="delivery_date" label="交期" min-width="120" />
        <el-table-column label="状态" min-width="130">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" effect="plain">
              {{ row.status || '未标记' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="金额" min-width="140">
          <template #default="{ row }">
            {{ formatMoney(row.grand_total, row.currency) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row)">查看详情</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pager" data-testid="cand013-sales-order-pagination">
        <el-pagination
          background
          layout="prev, pager, next, total, sizes"
          :current-page="query.page"
          :page-size="query.page_size"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          @current-change="onPageChange"
          @size-change="onSizeChange"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  fetchSalesInventorySalesOrders,
  type SalesInventoryListQuery,
  type SalesOrderListItem,
} from '@/api/sales_inventory'

const router = useRouter()

const loading = ref(false)
const lastError = ref('')
const rows = ref<SalesOrderListItem[]>([])
const total = ref(0)

const createDefaultQuery = (): SalesInventoryListQuery => ({
  order_no: '',
  keyword: '',
  company: '',
  customer: '',
  item_code: '',
  from_date: '',
  to_date: '',
  page: 1,
  page_size: 20,
})

const query = reactive<SalesInventoryListQuery>(createDefaultQuery())

const emptyText = computed(() => {
  if (loading.value) return '正在加载销售订单'
  if (lastError.value) return '查询失败'
  return '暂无销售订单数据'
})

const statusTagType = (status?: string | null): 'success' | 'warning' | 'info' => {
  if (status === 'Completed' || status === 'To Deliver and Bill') return 'success'
  if (status === 'Draft' || status === 'To Bill') return 'warning'
  return 'info'
}

const formatMoney = (amount?: string | number | null, currency?: string | null): string => {
  if (amount === null || amount === undefined || amount === '') return '-'
  const numeric = Number(amount)
  if (!Number.isFinite(numeric)) return String(amount)
  const money = numeric.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  return currency ? `${money} ${currency}` : money
}

const loadOrders = async (): Promise<void> => {
  loading.value = true
  lastError.value = ''
  try {
    const response = await fetchSalesInventorySalesOrders(query)
    rows.value = response.data.items
    total.value = response.data.total
    query.page = response.data.page
    query.page_size = response.data.page_size
  } catch (error) {
    rows.value = []
    total.value = 0
    lastError.value = (error as Error).message || '销售订单查询失败'
  } finally {
    loading.value = false
  }
}

const onSearch = (): void => {
  query.page = 1
  void loadOrders()
}

const onReset = (): void => {
  Object.assign(query, createDefaultQuery())
  void loadOrders()
}

const onPageChange = (page: number): void => {
  query.page = page
  void loadOrders()
}

const onSizeChange = (size: number): void => {
  query.page = 1
  query.page_size = size
  void loadOrders()
}

const openDetail = (row: SalesOrderListItem): void => {
  router.push({
    path: '/sales-inventory/sales-orders/detail',
    query: { name: row.name },
  })
}

onMounted(() => {
  void loadOrders()
})
</script>

<style scoped>
.sales-order-list-page {
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

.scope-alert,
.error-alert {
  margin-bottom: 16px;
}

.query-panel {
  margin-bottom: 16px;
}

.query-form {
  row-gap: 8px;
}

.summary-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}

.result-table {
  width: 100%;
}

.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
