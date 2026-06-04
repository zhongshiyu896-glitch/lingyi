<template>
  <div class="production-plan-page" data-testid="yisuan-1to1-production-plan-shell">
    <el-card shadow="never">
      <template #header>
        <div class="header-row">
          <div>
            <h2>生产计划</h2>
            <p class="sub-title">本地只读计划列表与 parity 入口</p>
          </div>
          <div class="header-actions">
            <el-button @click="goSampleParity">样衣入口</el-button>
            <el-button @click="goOrderParity">订单入口</el-button>
            <el-button @click="goProductionParity">生产跟进入口</el-button>
            <el-button type="primary" plain @click="goHome">工作台</el-button>
          </div>
        </div>
      </template>

      <el-alert type="info" :closable="false" class="scope-alert">
        <template #title>
          当前页面仅用于生产计划 list/detail 只读查询与 parity alias 入口，不触发工单下发、outbox、worker 或 ERPNext 生产写链路。
        </template>
      </el-alert>

      <section class="source-context" data-testid="yisuan-1to1-ui-source-readback">
        <el-tag type="success">production_plan_readonly=true</el-tag>
        <el-tag type="primary">list_detail_query_only=true</el-tag>
        <el-tag type="warning">work_order_push=false</el-tag>
        <el-tag type="warning">outbox_worker_release=false</el-tag>
        <el-tag v-if="parityTag" type="info">parity_route={{ parityTag }}</el-tag>
        <el-tag type="info">parity_label={{ currentParityLabel }}</el-tag>
      </section>

      <section class="status-board" data-testid="yisuan-1to1-production-plan-status-board">
        <el-card v-for="card in statusBoard" :key="card.name" shadow="never" class="status-card">
          <div class="status-name">{{ card.name }}</div>
          <div class="status-value">{{ card.value }}</div>
          <div class="status-note">{{ card.note }}</div>
        </el-card>
      </section>

      <el-card shadow="never" class="alias-card">
        <template #header>
          <div class="panel-header">
            <span>入口对齐</span>
            <el-tag type="info">local-dev only</el-tag>
          </div>
        </template>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="主入口">/production/plans</el-descriptions-item>
            <el-descriptions-item label="样衣入口">/sample/sampleListV2 -> /production/plans?parity=sample-list</el-descriptions-item>
            <el-descriptions-item label="样衣跟进入口">/sample/sampleProcess -> /production/plans?parity=sample-list</el-descriptions-item>
            <el-descriptions-item label="订单入口">
              /production/productOrder -> /production/plans?parity=production-order
            </el-descriptions-item>
            <el-descriptions-item label="生产跟进入口">
              /production/productionProcess -> /production/plans?parity=production-followup-template
            </el-descriptions-item>
          </el-descriptions>
      </el-card>

      <el-card shadow="never" class="summary-card" data-testid="production-plan-readback-summary">
        <template #header>
          <div class="panel-header">
            <span>计划摘要 / 数量矩阵</span>
            <el-tag type="warning">readonly snapshot</el-tag>
          </div>
        </template>
        <el-descriptions :column="4" border>
          <el-descriptions-item label="当前入口">{{ currentParityLabel }}</el-descriptions-item>
          <el-descriptions-item label="筛选后计划数">{{ filteredPlans.length }}</el-descriptions-item>
          <el-descriptions-item label="计划总数量">{{ filteredPlannedQty }}</el-descriptions-item>
          <el-descriptions-item label="工单待同步">{{ pendingWorkOrderCount }}</el-descriptions-item>
          <el-descriptions-item label="数量矩阵">{{ quantityMatrixSummary }}</el-descriptions-item>
          <el-descriptions-item label="快照来源">{{ snapshotSourceSummary }}</el-descriptions-item>
          <el-descriptions-item label="只读动作 guard">create/update/delete disabled</el-descriptions-item>
          <el-descriptions-item label="筛选联动">keyword + status + group</el-descriptions-item>
        </el-descriptions>
      </el-card>

      <ProductionFollowupReadonly :summary="followupReadonlySummary" />
      <ProductionOrderParityReadonly :summary="productionOrderParitySummary" />

      <el-card shadow="never" class="readonly-guard-card" data-testid="production-plan-readonly-guard-card">
        <template #header>
          <div class="panel-header">
            <span>只读动作 guard</span>
            <el-tag type="danger">write disabled</el-tag>
          </div>
        </template>
        <div class="guard-actions">
          <div v-for="action in readonlyGuardActions" :key="action.label" class="guard-action">
            <el-button disabled>{{ action.label }}</el-button>
            <span class="guard-reason">{{ action.reason }}</span>
          </div>
        </div>
      </el-card>

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
          <el-select v-model="query.group" clearable placeholder="全部" style="width: 180px">
            <el-option label="本地计划组" value="本地计划组" />
            <el-option label="样衣计划镜像" value="样衣计划镜像" />
            <el-option label="订单计划镜像" value="订单计划镜像" />
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
          <el-table-column prop="group" label="生产组" min-width="140" />
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
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  fetchProductionFollowupTemplates,
  fetchProductionPlans,
  type ProductionFollowupTemplateListItem,
  type ProductionPlanListItem,
} from '@/api/production'
import ProductionFollowupReadonly from '@/views/production/components/ProductionFollowupReadonly.vue'
import ProductionOrderParityReadonly from '@/views/production/components/ProductionOrderParityReadonly.vue'
import { useProductionPlanReadback } from './composables/useProductionPlanReadback'

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
const followupTemplates = ref<ProductionFollowupTemplateListItem[]>([])
const {
  buildProductionOrderParityListSummary,
  buildProductionFollowupListSummary,
  groupLabel,
  parseQueryString,
  parityRouteLabel,
  progressLabel,
  readonlyGuardActions,
  statusLabel,
  statusType,
} = useProductionPlanReadback()

const query = reactive({
  keyword: '',
  status: '',
  group: '',
})

const parityTag = computed(() => parseQueryString(route.query.parity))
const currentParityLabel = computed(() => parityRouteLabel(parityTag.value))

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
  {
    id: null,
    planNo: 'PP-LOCAL-260604',
    orderNo: 'SO-LOCAL-260604',
    styleCode: 'ITEM-D',
    customer: '订单镜像客户',
    group: '订单计划镜像',
    plannedQty: 260,
    progress: '52%',
    planDate: '2026-06-09',
    statusCode: 'work_order_pending',
    statusLabel: '工单待同步',
    workOrderStatus: 'blocked_scope',
    source: 'synthetic',
  },
]

const statusBoard = computed(() => {
  const rows = planRows.value
  const countByStatus = (status: string) => rows.filter((row) => row.statusCode === status).length
  return [
    { name: '已计划', value: String(countByStatus('planned')), note: '只读计划清单，不触发下发' },
    { name: '工单待同步', value: String(countByStatus('work_order_pending')), note: '仅保留同步状态，不触发 outbox' },
    { name: '本地只读记录', value: String(rows.length), note: `${currentParityLabel.value} / backend 为空时回退 synthetic snapshot` },
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

const filteredPlannedQty = computed(() =>
  filteredPlans.value.reduce((sum, row) => sum + Number(row.plannedQty || 0), 0).toLocaleString('zh-CN'),
)

const pendingWorkOrderCount = computed(() => filteredPlans.value.filter((row) => row.workOrderStatus === 'pending').length)

const quantityMatrixSummary = computed(() => {
  if (!filteredPlans.value.length) return '暂无计划数量矩阵快照'
  const items = filteredPlans.value.slice(0, 3).map((row) => `${row.styleCode}:${row.plannedQty}`)
  return `${items.join(' / ')}${filteredPlans.value.length > 3 ? ' ...' : ''}`
})

const snapshotSourceSummary = computed(() => {
  const syntheticCount = filteredPlans.value.filter((row) => row.source === 'synthetic').length
  const backendCount = filteredPlans.value.length - syntheticCount
  return `backend ${backendCount} / synthetic ${syntheticCount}`
})

const followupReadonlySummary = computed(() =>
  buildProductionFollowupListSummary({
    parity: parityTag.value,
    rows: filteredPlans.value,
    templates: followupTemplates.value,
  }),
)

const productionOrderParitySummary = computed(() =>
  buildProductionOrderParityListSummary({
    parity: parityTag.value,
    rows: filteredPlans.value,
  }),
)

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
  if (parityTag.value) {
    queryParams.parity = parityTag.value
  }
  return queryParams
}

const openDetail = (row: PlanRow): void => {
  router.push({ path: '/production/plans/detail', query: buildDetailQuery(row) })
}

const loadFollowupTemplates = async (): Promise<void> => {
  try {
    const response = await fetchProductionFollowupTemplates({
      page: 1,
      page_size: 20,
      keyword: query.keyword.trim() || undefined,
      item_code: parityTag.value === 'production-followup-template' ? undefined : undefined,
    })
    followupTemplates.value = response.data.items
  } catch {
    followupTemplates.value = []
  }
}

const refreshPlans = async (): Promise<void> => {
  listLoading.value = true
  listError.value = ''
  try {
    const [response] = await Promise.all([
      fetchProductionPlans({
        keyword: query.keyword.trim() || undefined,
        status: query.status || undefined,
        page: 1,
        page_size: 20,
      }),
      loadFollowupTemplates(),
    ])
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

const resetQuery = (): void => {
  query.keyword = ''
  query.status = ''
  query.group = ''
  void refreshPlans()
}

const goSampleParity = (): void => {
  router.push('/sample/sampleListV2')
}

const goOrderParity = (): void => {
  router.push('/production/productOrder')
}

const goProductionParity = (): void => {
  router.push('/production/productionProcess')
}

const goHome = (): void => {
  router.push('/home')
}

onMounted(() => {
  void refreshPlans()
})
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

.source-context {
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

.alias-card {
  margin-bottom: 12px;
}

.summary-card,
.readonly-guard-card {
  margin-bottom: 12px;
}

.query-panel {
  margin-bottom: 8px;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.guard-actions {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.guard-action {
  display: flex;
  align-items: center;
  gap: 10px;
}

.guard-reason {
  font-size: 12px;
  color: var(--el-text-color-secondary);
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
</style>
