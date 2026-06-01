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
            <el-option label="待锁定" value="待锁定" />
            <el-option label="进行中" value="进行中" />
            <el-option label="待复核" value="待复核" />
          </el-select>
        </el-form-item>
        <el-form-item label="生产组">
          <el-select v-model="query.group" clearable placeholder="全部" style="width: 160px">
            <el-option label="A 线" value="A线" />
            <el-option label="B 线" value="B线" />
            <el-option label="外协组" value="外协组" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>

      <section data-testid="yisuan-1to1-production-plan-table">
        <el-table :data="filteredPlans" border class="result-table">
          <el-table-column prop="planNo" label="计划号" min-width="160" />
          <el-table-column prop="orderNo" label="订单号" min-width="160" />
          <el-table-column prop="styleCode" label="款号" min-width="130" />
          <el-table-column prop="group" label="生产组" min-width="110" />
          <el-table-column prop="plannedQty" label="计划数量" min-width="110" />
          <el-table-column prop="progress" label="进度" min-width="110" />
          <el-table-column prop="planDate" label="计划日期" min-width="120" />
          <el-table-column prop="status" label="状态" min-width="120">
            <template #default="{ row }">
              <el-tag :type="statusType(row.status)" effect="plain">{{ row.status }}</el-tag>
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
import { computed, onMounted, reactive } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { request } from '@/api/request'

interface PlanRow {
  planNo: string
  orderNo: string
  styleCode: string
  group: string
  plannedQty: number
  progress: string
  planDate: string
  status: string
}

interface ProductionPlanReadback {
  draft_id: number
  plan_no: string
  planned_qty: number
  plan_date: string
  status: string
  state: string
  order_no: string
  style_code: string
}

interface SalesOrderReadbackData {
  object_id: number
  production_plan: ProductionPlanReadback | null
  readback_flags: {
    production_plan_readback_success: boolean
  }
}

interface SalesOrderListData {
  scenario_tag: string
  total: number
  records: SalesOrderReadbackData[]
}

interface ProductionPlanListData {
  scenario_tag: string
  total: number
  records: ProductionPlanReadback[]
}

const router = useRouter()
const route = useRoute()

const query = reactive({
  keyword: '',
  status: '',
  group: '',
})

const plans: PlanRow[] = [
  {
    planNo: 'PP-2606-A01',
    orderNo: 'SO-YS-260601',
    styleCode: 'JK-2410',
    group: 'A线',
    plannedQty: 480,
    progress: '62%',
    planDate: '2026-06-03',
    status: '进行中',
  },
  {
    planNo: 'PP-2606-B07',
    orderNo: 'SO-YS-260614',
    styleCode: 'DR-8831',
    group: '外协组',
    plannedQty: 300,
    progress: '35%',
    planDate: '2026-06-07',
    status: '待复核',
  },
  {
    planNo: 'PP-2606-C11',
    orderNo: 'SO-YS-260626',
    styleCode: 'TS-1077',
    group: 'B线',
    plannedQty: 560,
    progress: '12%',
    planDate: '2026-06-12',
    status: '待锁定',
  },
]

const statusBoard = [
  { name: '待锁定计划', value: '3', note: '交期确认前不可下发' },
  { name: '进行中计划', value: '8', note: '本周执行中的生产单' },
  { name: '异常待处理', value: '2', note: '涉及面料或工序冲突' },
]

const parseScenarioTag = (value: unknown): string => {
  const raw = Array.isArray(value) ? value[0] : value
  return typeof raw === 'string' ? raw.trim() : ''
}

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

const filteredPlans = computed(() => {
  const keyword = query.keyword.trim().toLowerCase()
  return plans.filter((row) => {
    if (keyword && !`${row.planNo} ${row.orderNo} ${row.styleCode}`.toLowerCase().includes(keyword)) return false
    if (query.status && row.status !== query.status) return false
    if (query.group && row.group !== query.group) return false
    return true
  })
})

const statusType = (status: string): 'success' | 'warning' | 'danger' | 'info' => {
  if (status === '进行中') return 'success'
  if (status === '待复核') return 'danger'
  if (status === '待锁定') return 'warning'
  return 'info'
}

const resetQuery = (): void => {
  query.keyword = ''
  query.status = ''
  query.group = ''
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
    const queryString = new URLSearchParams({ scenario_tag: scenarioTag }).toString()
    const orderResp = await request<SalesOrderListData>(`/api/local-dev/sales-orders?${queryString}`)
    const planResp = await request<ProductionPlanListData>(`/api/local-dev/production-plans?${queryString}`)
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
