<template>
  <div class="production-plan-page" data-testid="yisuan-1to1-production-plan-shell">
    <el-card shadow="never">
      <template #header>
        <div class="header-row">
          <div>
            <h2>生产计划</h2>
            <p class="sub-title">衣算云 UI 1:1 + REALOBJ-CAND-003 回读壳层（local-dev only）</p>
          </div>
          <div class="header-actions">
            <el-button @click="goSalesOrders">销售订单</el-button>
            <el-button type="primary" plain @click="goHome">工作台</el-button>
          </div>
        </div>
      </template>

      <el-alert type="info" :closable="false" class="scope-alert">
        <template #title>
          当前页面用于生产计划 readback 汇总；可筛选与观察，不触发新增、更新、下发到生产环境。
        </template>
      </el-alert>

      <section class="source-readback" data-testid="yisuan-1to1-ui-source-readback">
        <el-tag type="success">contract_source_readback_present=true</el-tag>
        <el-tag type="primary">covered_contract_ids=A002,A006</el-tag>
        <el-tag type="warning">A006 blocked/unknown => not_claimed</el-tag>
        <el-tag type="info">real_business_object_created=false (production)</el-tag>
        <el-tag type="info">linked_calculation_enabled=false (cross-module)</el-tag>
        <el-tag v-if="parityTag" type="warning">parity_route={{ parityTag }}</el-tag>
      </section>

      <section class="status-board" data-testid="yisuan-1to1-production-plan-status-board">
        <el-card v-for="card in statusBoard" :key="card.name" shadow="never" class="status-card">
          <div class="status-name">{{ card.name }}</div>
          <div class="status-value">{{ card.value }}</div>
          <div class="status-note">{{ card.note }}</div>
        </el-card>
      </section>

      <el-form :model="query" inline class="query-panel">
        <el-form-item label="关键字">
          <el-input v-model="query.keyword" clearable placeholder="计划号/订单号/款号" />
        </el-form-item>
        <el-form-item label="计划状态">
          <el-select v-model="query.status" clearable placeholder="全部" style="width: 160px">
            <el-option label="全部" value="" />
            <el-option label="已计划" value="planned" />
            <el-option label="已物料检查" value="material_checked" />
            <el-option label="工单待同步" value="work_order_pending" />
            <el-option label="已创建工单" value="work_order_created" />
          </el-select>
        </el-form-item>
        <el-form-item label="生产组">
          <el-select v-model="query.group" clearable placeholder="全部" style="width: 160px">
            <el-option label="本地计划组" value="本地计划组" />
            <el-option label="样衣计划镜像" value="样衣计划镜像" />
            <el-option label="生产跟进镜像" value="生产跟进镜像" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button :loading="listLoading" type="primary" plain @click="refreshPlans">刷新列表</el-button>
        </el-form-item>
        <el-form-item>
          <el-button @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>

      <el-alert v-if="listError" type="warning" :closable="false" :title="listError" class="scope-alert" />

      <section data-testid="yisuan-1to1-production-plan-table">
        <el-table :data="filteredPlans" border class="result-table" v-loading="listLoading">
          <el-table-column prop="planNo" label="计划号" min-width="160" />
          <el-table-column prop="orderNo" label="订单号" min-width="160" />
          <el-table-column prop="styleCode" label="款号" min-width="130" />
          <el-table-column prop="customer" label="客户" min-width="140" />
          <el-table-column prop="group" label="生产组" min-width="110" />
          <el-table-column prop="plannedQty" label="计划数量" min-width="110" />
          <el-table-column prop="progress" label="进度" min-width="110" />
          <el-table-column prop="planDate" label="计划日期" min-width="120" />
          <el-table-column prop="status" label="状态" min-width="120">
            <template #default="{ row }">
              <el-tag :type="statusType(row.statusCode)" effect="plain">{{ row.statusLabel }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="workOrderStatus" label="工单同步" min-width="120" />
          <el-table-column label="操作" width="120" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="openDetail(row)">查看详情</el-button>
            </template>
          </el-table-column>
        </el-table>
      </section>
    </el-card>

    <el-card shadow="never" data-testid="realobj-production-plan-readback">
      <template #header>
        <div class="panel-header">
          <span>REALOBJ-CAND-003 生产计划回读</span>
          <el-tag type="info">local-dev/sqlite/scenario_tag/test_data only</el-tag>
        </div>
      </template>

      <el-form :inline="true" class="readback-query-form">
        <el-form-item label="scenario_tag">
          <el-input v-model="readbackQuery.scenarioTag" style="width: 280px" data-testid="realobj-production-plan-scenario-tag" />
        </el-form-item>
        <el-form-item>
          <el-button :loading="localReadback.loading" @click="refreshReadback">刷新回读</el-button>
        </el-form-item>
      </el-form>

      <el-alert v-if="localReadback.error" type="warning" :closable="false" :title="localReadback.error" />

      <el-descriptions border :column="2" class="readback-descriptions">
        <el-descriptions-item label="scenario_tag">{{ readbackQuery.scenarioTag || '-' }}</el-descriptions-item>
        <el-descriptions-item label="sales_order_readback_total">{{ localReadback.salesOrderTotal }}</el-descriptions-item>
        <el-descriptions-item label="production_plan_readback_total">{{ localReadback.productionPlanTotal }}</el-descriptions-item>
        <el-descriptions-item label="production_plan_readback_success">
          {{ localReadback.productionPlanReadbackSuccess ? 'true' : 'false' }}
        </el-descriptions-item>
        <el-descriptions-item label="latest_plan_no">{{ localReadback.latestPlanNo || '-' }}</el-descriptions-item>
        <el-descriptions-item label="latest_plan_object_id">{{ localReadback.latestPlanObjectId || '-' }}</el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  fetchLocalReadbackProductionPlans,
  fetchLocalReadbackSalesOrders,
  fetchProductionPlans,
  type ProductionPlanListItem,
} from '@/api/production'

interface PlanRow {
  id: number | null
  planNo: string
  orderNo: string
  styleCode: string
  customer: string
  group: string
  plannedQty: number
  progress: string
  planDate: string
  statusCode: string
  statusLabel: string
  workOrderStatus: string
  source: 'backend' | 'synthetic'
}

const router = useRouter()
const route = useRoute()
const listLoading = ref(false)
const listError = ref('')
const planRows = ref<PlanRow[]>([])

const query = reactive({
  keyword: '',
  status: '',
  group: '',
})

const parseScenarioTag = (value: unknown): string => {
  const raw = Array.isArray(value) ? value[0] : value
  return typeof raw === 'string' ? raw.trim() : ''
}

const parityTag = computed(() => parseScenarioTag(route.query.parity))

const fallbackPlanSeeds: PlanRow[] = [
  {
    id: null,
    planNo: 'PP-LOCAL-260601',
    orderNo: 'SO-LOCAL-260601',
    styleCode: 'ITEM-A',
    customer: '本地样例客户',
    group: '本地计划组',
    plannedQty: 180,
    progress: '0%',
    planDate: '2026-06-03',
    statusCode: 'planned',
    statusLabel: '已计划',
    workOrderStatus: '-',
    source: 'synthetic',
  },
  {
    id: null,
    planNo: 'PP-LOCAL-260602',
    orderNo: 'SO-LOCAL-260602',
    styleCode: 'ITEM-B',
    customer: '样衣镜像客户',
    group: '样衣计划镜像',
    plannedQty: 240,
    progress: '35%',
    planDate: '2026-06-05',
    statusCode: 'material_checked',
    statusLabel: '已物料检查',
    workOrderStatus: 'pending',
    source: 'synthetic',
  },
  {
    id: null,
    planNo: 'PP-LOCAL-260603',
    orderNo: 'SO-LOCAL-260603',
    styleCode: 'ITEM-C',
    customer: '生产跟进镜像客户',
    group: '生产跟进镜像',
    plannedQty: 320,
    progress: '68%',
    planDate: '2026-06-08',
    statusCode: 'work_order_pending',
    statusLabel: '工单待同步',
    workOrderStatus: 'pending',
    source: 'synthetic',
  },
]

const readbackQuery = reactive({
  scenarioTag: parseScenarioTag(route.query.scenario_tag),
})

const localReadback = reactive({
  loading: false,
  error: '',
  salesOrderTotal: 0,
  productionPlanTotal: 0,
  productionPlanReadbackSuccess: false,
  latestPlanNo: '',
  latestPlanObjectId: 0,
})

const statusLabel = (status: string): string => {
  const labels: Record<string, string> = {
    planned: '已计划',
    material_checked: '已物料检查',
    work_order_pending: '工单待同步',
    work_order_created: '已创建工单',
    job_cards_synced: '工序卡已同步',
    cancelled: '已取消',
    failed: '失败',
  }
  return labels[status] || status
}

const progressLabel = (status: string): string => {
  const labels: Record<string, string> = {
    planned: '0%',
    material_checked: '35%',
    work_order_pending: '68%',
    work_order_created: '85%',
    job_cards_synced: '100%',
    cancelled: '0%',
    failed: '0%',
  }
  return labels[status] || '0%'
}

const groupLabel = (parity: string, company: string): string => {
  if (parity === 'sample-list') return '样衣计划镜像'
  if (parity === 'production-followup-template') return '生产跟进镜像'
  return company === 'LY-LOCAL-TEST' ? '本地计划组' : company
}

const statusBoard = computed(() => {
  const rows = planRows.value
  const countByStatus = (status: string) => rows.filter((row) => row.statusCode === status).length
  return [
    { name: '已计划', value: String(countByStatus('planned')), note: '仅本地只读清单，不触发下发' },
    { name: '工单待同步', value: String(countByStatus('work_order_pending')), note: '仅保留映射状态，不触发 outbox' },
    { name: '本地只读记录', value: String(rows.length), note: 'backend 为空时回退 synthetic snapshot' },
  ]
})

const filteredPlans = computed(() => {
  const keyword = query.keyword.trim().toLowerCase()
  return planRows.value.filter((row) => {
    if (keyword && !`${row.planNo} ${row.orderNo} ${row.styleCode}`.toLowerCase().includes(keyword)) return false
    if (query.status && row.statusCode !== query.status) return false
    if (query.group && row.group !== query.group) return false
    return true
  })
})

const statusType = (status: string): 'success' | 'warning' | 'danger' | 'info' => {
  if (status === 'work_order_created' || status === 'job_cards_synced') return 'success'
  if (status === 'failed') return 'danger'
  if (status === 'planned' || status === 'material_checked' || status === 'work_order_pending') return 'warning'
  return 'info'
}

const mapPlanRow = (item: ProductionPlanListItem): PlanRow => ({
  id: item.id,
  planNo: item.plan_no,
  orderNo: item.sales_order,
  styleCode: item.item_code,
  customer: item.customer || '-',
  group: groupLabel(parityTag.value, item.company),
  plannedQty: Number(item.planned_qty),
  progress: progressLabel(item.status),
  planDate: item.planned_start_date || '-',
  statusCode: item.status,
  statusLabel: statusLabel(item.status),
  workOrderStatus: item.latest_work_order_outbox?.status || '-',
  source: 'backend',
})

const resetQuery = (): void => {
  query.keyword = ''
  query.status = ''
  query.group = ''
  void refreshPlans()
}

const buildDetailQuery = (row: PlanRow): Record<string, string> => {
  const queryParams: Record<string, string> = {}
  if (row.id !== null) {
    queryParams.id = String(row.id)
  }
  if (row.source === 'synthetic') {
    queryParams.synthetic = '1'
    queryParams.plan_no = row.planNo
    queryParams.sales_order = row.orderNo
    queryParams.item_code = row.styleCode
    queryParams.customer = row.customer
    queryParams.company = 'LY-LOCAL-TEST'
    queryParams.planned_qty = String(row.plannedQty)
    queryParams.planned_start_date = row.planDate
    queryParams.status = row.statusCode
  }
  if (readbackQuery.scenarioTag.trim()) {
    queryParams.scenario = readbackQuery.scenarioTag.trim()
  }
  if (parityTag.value) {
    queryParams.parity = parityTag.value
  }
  return queryParams
}

const openDetail = (row: PlanRow): void => {
  router.push({ path: '/production/plans/detail', query: buildDetailQuery(row) })
}

const refreshPlans = async (): Promise<void> => {
  listLoading.value = true
  listError.value = ''
  try {
    const response = await fetchProductionPlans({
      keyword: query.keyword.trim() || undefined,
      status: query.status || undefined,
      page: 1,
      page_size: 20,
    })
    if (response.data.items.length > 0) {
      planRows.value = response.data.items.map(mapPlanRow)
      return
    }
    planRows.value = fallbackPlanSeeds.map((row) => ({ ...row }))
    listError.value = '未读取到本地生产计划记录，已回退到 synthetic snapshot。'
  } catch (error) {
    planRows.value = fallbackPlanSeeds.map((row) => ({ ...row }))
    listError.value = `读取生产计划失败，已回退到 synthetic snapshot：${(error as Error).message}`
  } finally {
    listLoading.value = false
  }
}

const refreshReadback = async (): Promise<void> => {
  const scenarioTag = readbackQuery.scenarioTag.trim()
  if (!scenarioTag) {
    localReadback.salesOrderTotal = 0
    localReadback.productionPlanTotal = 0
    localReadback.productionPlanReadbackSuccess = false
    localReadback.latestPlanNo = ''
    localReadback.latestPlanObjectId = 0
    return
  }

  localReadback.loading = true
  localReadback.error = ''
  try {
    const orderResp = await fetchLocalReadbackSalesOrders(scenarioTag)
    const planResp = await fetchLocalReadbackProductionPlans(scenarioTag)
    localReadback.salesOrderTotal = orderResp.data.total
    localReadback.productionPlanTotal = planResp.data.total
    localReadback.productionPlanReadbackSuccess = orderResp.data.records.some((record) =>
      Boolean(record.readback_flags.production_plan_readback_success),
    )
    const latestPlan = planResp.data.records[0]
    localReadback.latestPlanNo = latestPlan?.plan_no || ''
    localReadback.latestPlanObjectId = latestPlan?.draft_id || 0
  } catch (error) {
    localReadback.error = `回读失败：${(error as Error).message}`
    ElMessage.warning(localReadback.error)
  } finally {
    localReadback.loading = false
  }
}

onMounted(() => {
  void refreshPlans()
  void refreshReadback()
})

const goSalesOrders = (): void => {
  router.push('/sales-inventory/sales-orders')
}

const goHome = (): void => {
  router.push('/home')
}
</script>

<style scoped>
.production-plan-page {
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

.status-board {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 12px;
}

.status-card {
  border: 1px solid var(--el-border-color-lighter);
}

.status-name {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.status-value {
  font-size: 24px;
  line-height: 1.2;
  margin-top: 6px;
}

.status-note {
  margin-top: 6px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.query-panel {
  margin-bottom: 8px;
}

.result-table {
  width: 100%;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.readback-query-form {
  margin-bottom: 8px;
}

.readback-descriptions {
  margin-top: 10px;
}
</style>
