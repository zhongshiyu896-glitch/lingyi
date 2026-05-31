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

      <section class="source-readback" data-testid="yisuan-1to1-ui-source-readback">
        <el-tag type="success">contract_source_readback_present=true</el-tag>
        <el-tag type="primary">covered_contract_ids=A002,A006</el-tag>
        <el-tag type="warning">A006 blocked/unknown = not_claimed</el-tag>
        <el-tag type="info">real_business_object_created=false</el-tag>
        <el-tag type="info">linked_calculation_enabled=false</el-tag>
        <span>来源：A002/A006 contract sources（B018 继承，no-write）</span>
      </section>

      <el-card shadow="never" class="contract-boundary-card">
        <template #header>
          <div class="contract-header">
            <strong>合同边界回读（A002/A006）</strong>
            <el-tag type="danger" effect="plain">popup_only / not_claimed</el-tag>
          </div>
        </template>

        <div class="contract-grid">
          <div class="contract-block" data-testid="yisuan-contract-key-fields">
            <h4>key_fields</h4>
            <div class="tag-row">
              <el-tag v-for="field in keyFields" :key="`key-${field}`" type="success" effect="light">
                {{ field }} VERIFIED
              </el-tag>
            </div>
          </div>

          <div class="contract-block" data-testid="yisuan-contract-validation-rules">
            <h4>validation_rules</h4>
            <ul>
              <li v-for="rule in validationRules" :key="`validation-${rule}`">
                {{ rule }} => blocked / source_unknown / pending_confirmation / not_claimed
              </li>
            </ul>
          </div>

          <div class="contract-block" data-testid="yisuan-contract-status-rules">
            <h4>status_rules</h4>
            <div class="tag-row">
              <el-tag v-for="state in statusRules" :key="`state-${state}`" type="info" effect="light">{{ state }}</el-tag>
              <el-tag type="warning" effect="light">A006_popup_only_boundary=true</el-tag>
            </div>
          </div>

          <div class="contract-block" data-testid="yisuan-contract-readonly-readback-rules">
            <h4>readonly/readback rules</h4>
            <ul>
              <li v-for="rule in readbackRules" :key="`readback-${rule}`">{{ rule }}</li>
            </ul>
          </div>
        </div>
      </el-card>

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
          <el-table-column label="契约边界" min-width="220">
            <template #default="{ row }">
              <el-tag type="info" effect="plain">{{ row.contractBoundary }}</el-tag>
              <el-tag size="small" type="warning" effect="plain">popup_only</el-tag>
              <el-tag size="small" type="danger" effect="plain">not_claimed</el-tag>
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
  contractBoundary: string
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
    contractBoundary: 'VERIFIED',
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
    contractBoundary: 'PARTIAL',
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
    contractBoundary: 'BLOCKED',
  },
]

const keyFields = [
  '订单',
  '客户',
  '下单日期',
  '业务员',
  '汇率',
  '币种',
  '备注',
  '款号',
  '款名',
  '颜色',
  '尺码',
  '单价',
]

const validationRules = [
  '主订单保存',
  '订单详情回读动作',
  '生产制单',
  '加工单',
  'BOM',
  '工序',
  '库存',
  '财务',
  '提交/审核/删除/作废',
  '生成生产/采购/加工单',
]

const statusRules = ['VERIFIED', 'PARTIAL', 'UNKNOWN', 'NO-GO', 'BLOCKED']

const readbackRules = [
  'UI 静态证据不等同业务算法 1:1',
  'mainOrderSaveClicked=false',
  'orderCreated=false',
  'orderNumberGenerated=false',
  'A006 blocked/unknown fields only for shell expression',
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

.source-readback {
  margin-bottom: 12px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.contract-boundary-card {
  margin-bottom: 12px;
}

.contract-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.contract-grid {
  display: grid;
  gap: 10px;
}

.contract-block h4 {
  margin: 0 0 8px;
  font-size: 13px;
}

.contract-block ul {
  margin: 0;
  padding-left: 18px;
  color: var(--el-text-color-secondary);
  line-height: 1.5;
}

.tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.query-panel {
  margin-bottom: 8px;
  padding: 8px 0 0;
}

.result-table {
  width: 100%;
}
</style>
