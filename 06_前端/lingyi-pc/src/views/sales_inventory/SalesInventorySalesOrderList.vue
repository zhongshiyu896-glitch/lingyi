<template>
  <div class="sales-order-list-page">
    <el-card shadow="never">
      <template #header>
        <div class="header-row">
          <div>
            <h2>大货管理 / 销售订单</h2>
            <p class="sub-title">MVP-CAND-004 本地可用闭环（local-dev/sqlite/scenario_tag）</p>
          </div>
          <el-button size="small" @click="goProductionPlans">查看生产计划</el-button>
        </div>
      </template>

      <el-alert
        type="info"
        :closable="false"
        title="本页仅展示和查询销售订单草稿，写入动作在详情页完成；所有写入必须走 local-dev endpoint。"
        class="scope-alert"
      />

      <section class="query-panel" data-testid="mvp-sales-order-list-query">
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
            <el-select
              v-model="query.status"
              clearable
              placeholder="全部"
              style="width: 160px"
              data-testid="mvp-sales-order-status-filter"
            >
              <el-option label="全部" value="" />
              <el-option label="draft" value="draft" />
              <el-option label="saved" value="saved" />
              <el-option label="cancelled" value="cancelled" />
            </el-select>
          </el-form-item>
          <el-form-item label="scenario_tag">
            <el-input v-model="query.scenarioTag" clearable placeholder="MVP-CAND004-..." />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="loading" @click="refreshRows">查询</el-button>
            <el-button @click="resetQuery">重置</el-button>
          </el-form-item>
        </el-form>
      </section>

      <el-table :data="filteredRows" border v-loading="loading" class="result-table">
        <el-table-column prop="orderNo" label="订单号" min-width="170" />
        <el-table-column prop="customerName" label="客户" min-width="140" />
        <el-table-column prop="styleCode" label="款号" min-width="140" />
        <el-table-column prop="deliveryDate" label="交期" min-width="130" />
        <el-table-column prop="status" label="状态" min-width="110">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" effect="plain">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="matrixTotal" label="矩阵数量" min-width="100" />
        <el-table-column prop="plannedQty" label="已排产数量" min-width="110" />
        <el-table-column prop="deltaQty" label="差异数量" min-width="100" />
        <el-table-column prop="scenarioTag" label="scenario_tag" min-width="220" />
        <el-table-column label="操作" width="140">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row)">编辑草稿</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { request } from '@/api/request'

interface SalesOrderMatrixCell {
  color: string
  size: string
  ordered_qty: number
  planned_qty: number
  delta_qty: number
}

interface SalesOrderDraftData {
  draft_id: number
  scenario_tag: string
  order_no: string
  customer_name: string
  style_code: string
  delivery_date: string
  status: string
  quantity_matrix: SalesOrderMatrixCell[]
  linked_plan_draft_id: number | null
  state: string
}

interface SalesOrderDraftListResponse {
  items: SalesOrderDraftData[]
  total: number
}

interface SalesOrderRowView {
  draftId: number | null
  orderNo: string
  customerName: string
  styleCode: string
  deliveryDate: string
  status: string
  scenarioTag: string
  matrixTotal: number
  plannedQty: number
  deltaQty: number
}

const router = useRouter()

const loading = ref(false)
const draftRows = ref<SalesOrderRowView[]>([])

const query = reactive({
  keyword: '',
  customer: '',
  styleCode: '',
  status: '',
  scenarioTag: '',
})

const demoRows: SalesOrderRowView[] = [
  {
    draftId: null,
    orderNo: 'SO-DEMO-2401',
    customerName: '蓝小姐工坊',
    styleCode: 'STYLE-TEE-01',
    deliveryDate: '2026-06-20',
    status: 'draft',
    scenarioTag: 'MVP-CAND004-DEMO-BASELINE',
    matrixTotal: 120,
    plannedQty: 80,
    deltaQty: 40,
  },
]

const statusTagType = (status: string): 'success' | 'warning' | 'danger' | 'info' => {
  if (status === 'saved' || status === 'active') return 'success'
  if (status === 'cancelled') return 'danger'
  if (status === 'draft') return 'warning'
  return 'info'
}

const calculateSummary = (matrix: SalesOrderMatrixCell[]): { matrixTotal: number; plannedQty: number; deltaQty: number } => {
  const matrixTotal = matrix.reduce((sum, cell) => sum + Number(cell.ordered_qty || 0), 0)
  const plannedQty = matrix.reduce((sum, cell) => sum + Number(cell.planned_qty || 0), 0)
  return {
    matrixTotal,
    plannedQty,
    deltaQty: matrixTotal - plannedQty,
  }
}

const mapDraftToRow = (draft: SalesOrderDraftData): SalesOrderRowView => {
  const summary = calculateSummary(draft.quantity_matrix || [])
  return {
    draftId: draft.draft_id,
    orderNo: draft.order_no,
    customerName: draft.customer_name,
    styleCode: draft.style_code,
    deliveryDate: draft.delivery_date,
    status: draft.state || draft.status || 'draft',
    scenarioTag: draft.scenario_tag,
    matrixTotal: summary.matrixTotal,
    plannedQty: summary.plannedQty,
    deltaQty: summary.deltaQty,
  }
}

const filteredRows = computed<SalesOrderRowView[]>(() => {
  const source = draftRows.value.length > 0 ? draftRows.value : demoRows
  const keyword = query.keyword.trim().toLowerCase()
  const customer = query.customer.trim().toLowerCase()
  const styleCode = query.styleCode.trim().toLowerCase()
  const status = query.status.trim().toLowerCase()
  const scenarioTag = query.scenarioTag.trim()
  return source.filter((row) => {
    if (keyword && !`${row.orderNo} ${row.customerName} ${row.styleCode}`.toLowerCase().includes(keyword)) return false
    if (customer && !row.customerName.toLowerCase().includes(customer)) return false
    if (styleCode && !row.styleCode.toLowerCase().includes(styleCode)) return false
    if (status && row.status.toLowerCase() !== status) return false
    if (scenarioTag && row.scenarioTag !== scenarioTag) return false
    return true
  })
})

const refreshRows = async (): Promise<void> => {
  loading.value = true
  try {
    const params = new URLSearchParams()
    if (query.keyword.trim()) params.set('keyword', query.keyword.trim())
    if (query.customer.trim()) params.set('customer_name', query.customer.trim())
    if (query.styleCode.trim()) params.set('style_code', query.styleCode.trim())
    if (query.status.trim()) params.set('status', query.status.trim())
    if (query.scenarioTag.trim()) params.set('scenario_tag', query.scenarioTag.trim())
    const queryString = params.toString()
    const url = queryString ? `/api/local-dev/sales-order-drafts?${queryString}` : '/api/local-dev/sales-order-drafts'
    const response = await request<SalesOrderDraftListResponse>(url)
    draftRows.value = response.data.items.map(mapDraftToRow)
  } catch (error) {
    ElMessage.error(`查询失败：${(error as Error).message}`)
  } finally {
    loading.value = false
  }
}

const resetQuery = (): void => {
  query.keyword = ''
  query.customer = ''
  query.styleCode = ''
  query.status = ''
  query.scenarioTag = ''
  void refreshRows()
}

const openDetail = (row: SalesOrderRowView): void => {
  router.push({
    path: '/sales-inventory/sales-orders/detail',
    query: {
      draft_id: row.draftId ? String(row.draftId) : undefined,
      scenario_tag: row.scenarioTag || undefined,
      order_no: row.orderNo,
      style_code: row.styleCode,
      customer_name: row.customerName,
    },
  })
}

const goProductionPlans = (): void => {
  router.push({
    path: '/production/plans',
    query: {
      scenario_tag: query.scenarioTag || undefined,
      parity: 'sales-order-local-plan',
    },
  })
}

onMounted(() => {
  void refreshRows()
})
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
}

.result-table {
  width: 100%;
}
</style>
