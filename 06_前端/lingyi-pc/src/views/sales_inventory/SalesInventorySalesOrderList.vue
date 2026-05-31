<template>
  <div class="sales-order-list-page" data-testid="yisuan-1to1-sales-order-list-shell">
    <el-card shadow="never">
      <template #header>
        <div class="header-row">
          <div>
            <h2>大货管理 / 销售订单</h2>
            <p class="sub-title">衣算云 UI 1:1 对齐（只读态，无写请求）</p>
          </div>
          <div class="header-actions">
            <el-button size="small" @click="goProductionPlans">生产计划</el-button>
            <el-button size="small" type="primary" plain @click="goHome">返回工作台</el-button>
          </div>
        </div>
      </template>

      <el-alert type="info" :closable="false" class="scope-alert">
        <template #title>
          页面仅做 UI parity 展示，保留列表筛选、状态观察与详情跳转，不触发新增/更新写操作。
        </template>
      </el-alert>

      <section class="query-panel" data-testid="yisuan-1to1-sales-order-filter-panel">
        <el-form :model="query" inline>
          <el-form-item label="关键字">
            <el-input v-model="query.keyword" clearable placeholder="订单号/客户/款号" />
          </el-form-item>
          <el-form-item label="客户">
            <el-input v-model="query.customer" clearable placeholder="客户名称" />
          </el-form-item>
          <el-form-item label="款号">
            <el-input v-model="query.styleCode" clearable placeholder="款号" />
          </el-form-item>
          <el-form-item label="状态">
            <el-select v-model="query.status" clearable placeholder="全部" style="width: 160px">
              <el-option label="全部" value="" />
              <el-option label="待确认" value="待确认" />
              <el-option label="已排产" value="已排产" />
              <el-option label="待交期评估" value="待交期评估" />
            </el-select>
          </el-form-item>
          <el-form-item label="交期档位">
            <el-select v-model="query.deliveryBucket" clearable placeholder="全部" style="width: 140px">
              <el-option label="本周" value="week" />
              <el-option label="两周内" value="two_weeks" />
              <el-option label="本月" value="month" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button @click="resetQuery">重置筛选</el-button>
          </el-form-item>
        </el-form>
      </section>

      <section data-testid="yisuan-1to1-sales-order-table">
        <el-table :data="filteredRows" border class="result-table">
          <el-table-column prop="orderNo" label="订单号" min-width="170" />
          <el-table-column prop="customerName" label="客户" min-width="140" />
          <el-table-column prop="styleCode" label="款号" min-width="130" />
          <el-table-column prop="deliveryDate" label="交期" min-width="120" />
          <el-table-column prop="orderQty" label="订单数" min-width="100" />
          <el-table-column prop="plannedQty" label="排产数" min-width="100" />
          <el-table-column prop="delayRisk" label="交期风险" min-width="110" />
          <el-table-column prop="status" label="状态" min-width="130">
            <template #default="{ row }">
              <span data-testid="yisuan-1to1-sales-order-status-tags">
                <el-tag :type="statusTagType(row.status)" effect="plain">{{ row.status }}</el-tag>
              </span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120">
            <template #default="{ row }">
              <el-button link type="primary" @click="openDetail(row)">查看详情</el-button>
            </template>
          </el-table-column>
        </el-table>
      </section>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive } from 'vue'
import { useRouter } from 'vue-router'

interface SalesOrderRow {
  orderNo: string
  customerName: string
  styleCode: string
  deliveryDate: string
  orderQty: number
  plannedQty: number
  delayRisk: string
  status: string
}

const router = useRouter()

const query = reactive({
  keyword: '',
  customer: '',
  styleCode: '',
  status: '',
  deliveryBucket: '',
})

const rows: SalesOrderRow[] = [
  {
    orderNo: 'SO-YS-260601',
    customerName: '青禾服饰',
    styleCode: 'JK-2410',
    deliveryDate: '2026-06-12',
    orderQty: 1280,
    plannedQty: 900,
    delayRisk: '中',
    status: '已排产',
  },
  {
    orderNo: 'SO-YS-260614',
    customerName: '曜石商贸',
    styleCode: 'DR-8831',
    deliveryDate: '2026-06-21',
    orderQty: 860,
    plannedQty: 420,
    delayRisk: '高',
    status: '待交期评估',
  },
  {
    orderNo: 'SO-YS-260626',
    customerName: '北岸零售',
    styleCode: 'TS-1077',
    deliveryDate: '2026-06-29',
    orderQty: 1560,
    plannedQty: 0,
    delayRisk: '中',
    status: '待确认',
  },
]

const withinBucket = (deliveryDate: string, bucket: string): boolean => {
  if (!bucket) return true
  const today = new Date('2026-06-01')
  const delivery = new Date(deliveryDate)
  const delta = Math.floor((delivery.getTime() - today.getTime()) / (24 * 3600 * 1000))
  if (bucket === 'week') return delta <= 7
  if (bucket === 'two_weeks') return delta <= 14
  if (bucket === 'month') return delta <= 30
  return true
}

const filteredRows = computed<SalesOrderRow[]>(() => {
  const keyword = query.keyword.trim().toLowerCase()
  const customer = query.customer.trim().toLowerCase()
  const styleCode = query.styleCode.trim().toLowerCase()
  const status = query.status.trim()
  return rows.filter((row) => {
    if (keyword && !`${row.orderNo} ${row.customerName} ${row.styleCode}`.toLowerCase().includes(keyword)) return false
    if (customer && !row.customerName.toLowerCase().includes(customer)) return false
    if (styleCode && !row.styleCode.toLowerCase().includes(styleCode)) return false
    if (status && row.status !== status) return false
    if (!withinBucket(row.deliveryDate, query.deliveryBucket.trim())) return false
    return true
  })
})

const resetQuery = (): void => {
  query.keyword = ''
  query.customer = ''
  query.styleCode = ''
  query.status = ''
  query.deliveryBucket = ''
}

const statusTagType = (status: string): 'success' | 'warning' | 'danger' | 'info' => {
  if (status === '已排产') return 'success'
  if (status === '待交期评估') return 'danger'
  if (status === '待确认') return 'warning'
  return 'info'
}

const openDetail = (row: SalesOrderRow): void => {
  router.push({
    path: '/sales-inventory/sales-orders/detail',
    query: {
      order_no: row.orderNo,
      customer_name: row.customerName,
      style_code: row.styleCode,
      parity: 'yisuan-1to1-cand004',
    },
  })
}

const goProductionPlans = (): void => {
  router.push({
    path: '/production/plans',
    query: {
      parity: 'sales-order-ui-parity',
    },
  })
}

const goHome = (): void => {
  router.push('/home')
}
</script>

<style scoped>
.sales-order-list-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.header-row h2 {
  margin: 0;
  font-size: 18px;
  line-height: 1.4;
}

.sub-title {
  margin: 2px 0 0;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.scope-alert {
  margin-bottom: 12px;
}

.query-panel {
  margin-bottom: 8px;
  padding: 8px 0 0;
}

.result-table {
  width: 100%;
}
</style>
