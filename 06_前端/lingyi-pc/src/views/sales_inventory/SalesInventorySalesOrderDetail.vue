<template>
  <div class="sales-order-detail-page" data-testid="yisuan-1to1-sales-order-detail-shell">
    <el-card shadow="never">
      <template #header>
        <div class="header-row">
          <div>
            <h2>销售订单详情</h2>
            <p class="sub-title">衣算云 UI 1:1 + REALOBJ-CAND-003 回读壳层（local-dev only）</p>
          </div>
          <div class="header-actions">
            <el-button @click="goList">返回列表</el-button>
            <el-button :loading="localReadback.loading" :disabled="!localReadback.objectId" @click="refreshLocalReadback">
              刷新本地回读
            </el-button>
            <el-button type="primary" plain @click="goProductionPlan">查看生产计划</el-button>
          </div>
        </div>
      </template>

      <el-alert type="info" :closable="false" class="scope-alert">
        <template #title>本页仅用于订单详情 + 数量矩阵 + 生产计划回读观察，不触发生产写入。</template>
      </el-alert>

      <section class="source-readback" data-testid="yisuan-1to1-ui-source-readback">
        <el-tag type="success">contract_source_readback_present=true</el-tag>
        <el-tag type="primary">covered_contract_ids=A002,A006</el-tag>
        <el-tag type="warning">A006 blocked/unknown = not_claimed</el-tag>
        <el-tag type="info">real_business_object_created=false (production)</el-tag>
        <el-tag type="info">linked_calculation_enabled=false (cross-module)</el-tag>
      </section>

      <el-descriptions :column="4" border class="header-summary" data-testid="yisuan-1to1-sales-order-header-summary">
        <el-descriptions-item label="订单号">{{ detail.orderNo }}</el-descriptions-item>
        <el-descriptions-item label="客户">{{ detail.customerName }}</el-descriptions-item>
        <el-descriptions-item label="款号">{{ detail.styleCode }}</el-descriptions-item>
        <el-descriptions-item label="业务员">{{ detail.owner }}</el-descriptions-item>
        <el-descriptions-item label="下单日期">{{ detail.orderDate }}</el-descriptions-item>
        <el-descriptions-item label="交期">{{ detail.deliveryDate }}</el-descriptions-item>
        <el-descriptions-item label="订单状态">
          <el-tag type="warning" effect="plain">{{ detail.orderStatus }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="生产状态">
          <el-tag type="success" effect="plain">{{ detail.productionStatus }}</el-tag>
        </el-descriptions-item>
      </el-descriptions>
    </el-card>

    <el-card shadow="never" data-testid="realobj-sales-order-detail-readback">
      <template #header>
        <div class="panel-header">
          <span>REALOBJ-CAND-003 本地对象回读</span>
          <el-tag type="info">local-dev/sqlite/scenario_tag/test_data only</el-tag>
        </div>
      </template>

      <el-alert
        v-if="localReadback.error"
        type="warning"
        :closable="false"
        :title="localReadback.error"
      />
      <el-alert
        v-else-if="!localReadback.data"
        type="info"
        :closable="false"
        title="未携带 object_id/scenario_tag，当前显示静态详情壳层。"
      />

      <el-descriptions
        v-if="localReadback.data"
        border
        :column="2"
        class="readback-descriptions"
        data-testid="realobj-sales-order-readback-evidence"
      >
        <el-descriptions-item label="object_id">{{ localReadback.data.object_id }}</el-descriptions-item>
        <el-descriptions-item label="scenario_tag">{{ localReadback.data.scenario_tag }}</el-descriptions-item>
        <el-descriptions-item label="sales_order_readback_success">
          {{ localReadback.data.readback_flags.sales_order_readback_success ? 'true' : 'false' }}
        </el-descriptions-item>
        <el-descriptions-item label="order_detail_readback_success">
          {{ localReadback.data.readback_flags.order_detail_readback_success ? 'true' : 'false' }}
        </el-descriptions-item>
        <el-descriptions-item label="quantity_matrix_readback_success">
          {{ localReadback.data.readback_flags.quantity_matrix_readback_success ? 'true' : 'false' }}
        </el-descriptions-item>
        <el-descriptions-item label="production_plan_readback_success">
          {{ localReadback.data.readback_flags.production_plan_readback_success ? 'true' : 'false' }}
        </el-descriptions-item>
      </el-descriptions>
    </el-card>

    <el-card shadow="never" data-testid="yisuan-1to1-sales-order-quantity-matrix">
      <template #header>
        <div class="card-title">数量矩阵</div>
      </template>
      <el-table :data="displayMatrixRows" border>
        <el-table-column prop="color" label="颜色" min-width="110" />
        <el-table-column prop="size" label="尺码" min-width="90" />
        <el-table-column prop="orderedQty" label="订单数量" min-width="120" />
        <el-table-column prop="plannedQty" label="已排产" min-width="100" />
        <el-table-column prop="deltaQty" label="差异" min-width="100" />
      </el-table>
      <div class="matrix-delta">
        总订单数量：{{ matrixSummary.orderedQty }}，已排产：{{ matrixSummary.plannedQty }}，差异：{{ matrixSummary.deltaQty }}
      </div>
    </el-card>

    <el-card shadow="never" data-testid="yisuan-1to1-sales-order-production-plan">
      <template #header>
        <div class="card-title">关联生产计划</div>
      </template>
      <el-descriptions :column="3" border>
        <el-descriptions-item label="计划号">{{ displayPlan.planNo }}</el-descriptions-item>
        <el-descriptions-item label="计划数量">{{ displayPlan.plannedQty }}</el-descriptions-item>
        <el-descriptions-item label="计划日期">{{ displayPlan.planDate }}</el-descriptions-item>
        <el-descriptions-item label="计划状态">
          <el-tag type="info" effect="plain">{{ displayPlan.status }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="计划对象 ID">{{ displayPlan.planObjectId }}</el-descriptions-item>
        <el-descriptions-item label="订单对象 ID">{{ displayPlan.orderObjectId }}</el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { request } from '@/api/request'

interface QuantityMatrixCell {
  color: string
  size: string
  ordered_qty: number
  planned_qty: number
  delta_qty: number
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
  draft_id: number
  scenario_tag: string
  sales_order: {
    order_no: string
    customer_name: string
    style_code: string
    delivery_date: string
    status: string
    state: string
    note: string
  }
  order_detail: {
    linked_plan_draft_id: number | null
    quantity_matrix_cells: number
    quantity_matrix_total_ordered: number
    quantity_matrix_total_planned: number
    state: string
  }
  quantity_matrix: QuantityMatrixCell[]
  production_plan: ProductionPlanReadback | null
  readback_flags: {
    scenario_tag_present: boolean
    sales_order_readback_success: boolean
    order_detail_readback_success: boolean
    quantity_matrix_readback_success: boolean
    production_plan_readback_success: boolean
    status_validation_readback_success: boolean
  }
}

const router = useRouter()
const route = useRoute()

const detail = reactive({
  orderNo: String(Array.isArray(route.query.order_no) ? route.query.order_no[0] : route.query.order_no || 'SO-YS-260601'),
  customerName: String(
    Array.isArray(route.query.customer_name) ? route.query.customer_name[0] : route.query.customer_name || '青禾服饰',
  ),
  styleCode: String(Array.isArray(route.query.style_code) ? route.query.style_code[0] : route.query.style_code || 'JK-2410'),
  owner: '陈林',
  orderDate: '2026-05-25',
  deliveryDate: '2026-06-12',
  orderStatus: '待交期确认',
  productionStatus: '样前齐料',
})

const localReadback = reactive<{
  loading: boolean
  data: SalesOrderReadbackData | null
  error: string
  objectId: number | null
  scenarioTag: string
}>({
  loading: false,
  data: null,
  error: '',
  objectId: null,
  scenarioTag: '',
})

const parseObjectId = (value: unknown): number | null => {
  const raw = Array.isArray(value) ? value[0] : value
  const parsed = Number(raw)
  if (!Number.isFinite(parsed) || parsed <= 0) return null
  return Math.floor(parsed)
}

const parseScenarioTag = (value: unknown): string => {
  const raw = Array.isArray(value) ? value[0] : value
  return typeof raw === 'string' ? raw.trim() : ''
}

const objectIdFromQuery = computed<number | null>(() => parseObjectId(route.query.object_id))
const scenarioTagFromQuery = computed<string>(() => parseScenarioTag(route.query.scenario_tag))

const staticMatrixRows = reactive([
  { color: '米白', size: 'M', orderedQty: 300, plannedQty: 210, deltaQty: 90 },
  { color: '烟灰', size: 'L', orderedQty: 260, plannedQty: 170, deltaQty: 90 },
])

const displayMatrixRows = computed(() => {
  if (localReadback.data?.quantity_matrix?.length) {
    return localReadback.data.quantity_matrix.map((row) => ({
      color: row.color,
      size: row.size,
      orderedQty: Number(row.ordered_qty || 0),
      plannedQty: Number(row.planned_qty || 0),
      deltaQty: Number(row.delta_qty || 0),
    }))
  }
  return staticMatrixRows
})

const matrixSummary = computed(() => {
  const orderedQty = displayMatrixRows.value.reduce((sum, row) => sum + row.orderedQty, 0)
  const plannedQty = displayMatrixRows.value.reduce((sum, row) => sum + row.plannedQty, 0)
  return {
    orderedQty,
    plannedQty,
    deltaQty: orderedQty - plannedQty,
  }
})

const displayPlan = computed(() => {
  const plan = localReadback.data?.production_plan
  return {
    planNo: plan?.plan_no || 'PLAN-PLACEHOLDER',
    plannedQty: plan?.planned_qty ?? '-',
    planDate: plan?.plan_date || '-',
    status: plan?.status || 'draft',
    planObjectId: plan?.draft_id ?? '-',
    orderObjectId: localReadback.data?.object_id ?? '-',
  }
})

const refreshLocalReadback = async (): Promise<void> => {
  const objectId = objectIdFromQuery.value
  const scenarioTag = scenarioTagFromQuery.value
  localReadback.objectId = objectId
  localReadback.scenarioTag = scenarioTag
  if (!objectId || !scenarioTag) {
    localReadback.data = null
    localReadback.error = ''
    return
  }
  localReadback.loading = true
  localReadback.error = ''
  try {
    const queryString = new URLSearchParams({ scenario_tag: scenarioTag }).toString()
    const response = await request<SalesOrderReadbackData>(`/api/local-dev/sales-orders/${objectId}/readback?${queryString}`)
    localReadback.data = response.data
    detail.orderNo = response.data.sales_order.order_no || detail.orderNo
    detail.customerName = response.data.sales_order.customer_name || detail.customerName
    detail.styleCode = response.data.sales_order.style_code || detail.styleCode
    detail.deliveryDate = response.data.sales_order.delivery_date || detail.deliveryDate
    detail.orderStatus = response.data.sales_order.status || detail.orderStatus
    detail.productionStatus = response.data.production_plan?.status || detail.productionStatus
  } catch (error) {
    localReadback.data = null
    localReadback.error = `本地回读失败：${(error as Error).message}`
    ElMessage.warning(localReadback.error)
  } finally {
    localReadback.loading = false
  }
}

watch([objectIdFromQuery, scenarioTagFromQuery], () => {
  void refreshLocalReadback()
})

onMounted(() => {
  void refreshLocalReadback()
})

const goList = (): void => {
  router.push('/sales-inventory/sales-orders')
}

const goProductionPlan = (): void => {
  router.push({
    path: '/production/plans',
    query: {
      scenario_tag: localReadback.scenarioTag || scenarioTagFromQuery.value,
      object_id: localReadback.data?.production_plan?.draft_id
        ? String(localReadback.data.production_plan.draft_id)
        : '',
      parity: 'realobj-cand003-local-loop',
    },
  })
}
</script>

<style scoped>
.sales-order-detail-page {
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

.header-actions {
  display: flex;
  gap: 8px;
}

.scope-alert {
  margin-bottom: 12px;
}

.source-readback {
  margin-bottom: 10px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.header-summary {
  margin-top: 2px;
}

.card-title {
  font-weight: 600;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.readback-descriptions {
  margin-top: 10px;
}

.matrix-delta {
  margin-top: 12px;
  color: var(--el-text-color-regular);
}
</style>
