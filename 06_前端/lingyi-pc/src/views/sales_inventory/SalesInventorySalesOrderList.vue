<template>
  <div class="sales-order-list-page" data-testid="yisuan-1to1-sales-order-list-shell">
    <el-card shadow="never">
      <template #header>
        <div class="header-row">
          <div>
            <h2>大货管理 / 销售订单</h2>
            <p class="sub-title">衣算云 UI 1:1 + REALOBJ-CAND-003 本地写入闭环（local-dev only）</p>
          </div>
          <div class="header-actions">
            <el-button size="small" @click="goProductionPlans">生产计划</el-button>
            <el-button size="small" type="primary" plain @click="goHome">返回工作台</el-button>
          </div>
        </div>
      </template>

      <el-alert type="info" :closable="false" class="scope-alert">
        <template #title>
          本页面允许 local-dev/sqlite/scenario_tag/test_data 的 create/update/readback/rollback，
          不触发 ERPNext 或生产写入。
        </template>
      </el-alert>

      <section class="source-readback" data-testid="yisuan-1to1-ui-source-readback">
        <el-tag type="success">contract_source_readback_present=true</el-tag>
        <el-tag type="primary">covered_contract_ids=A002,A006</el-tag>
        <el-tag type="warning">A006 blocked/unknown = not_claimed</el-tag>
        <el-tag type="info">real_business_object_created=false (production)</el-tag>
        <el-tag type="info">linked_calculation_enabled=false (cross-module)</el-tag>
      </section>

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
              <el-tag :type="statusTagType(row.status)" effect="plain">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="契约边界" min-width="220">
            <template #default="{ row }">
              <el-tag type="info" effect="plain">{{ row.contractBoundary }}</el-tag>
              <el-tag size="small" type="warning" effect="plain">popup_only</el-tag>
              <el-tag size="small" type="danger" effect="plain">not_claimed</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="180">
            <template #default="{ row }">
              <el-button link type="primary" @click="loadRowToLoop(row)">写入闭环</el-button>
              <el-button link type="primary" @click="openDetail(row)">查看详情</el-button>
            </template>
          </el-table-column>
        </el-table>
      </section>
    </el-card>

    <el-card shadow="never" class="local-write-panel" data-testid="realobj-sales-order-local-loop">
      <template #header>
        <div class="panel-header">
          <strong>REALOBJ-CAND-003 本地对象写入闭环（销售订单 + 数量矩阵 + 生产计划）</strong>
          <el-tag type="info">local-dev/sqlite/scenario_tag/test_data only</el-tag>
        </div>
      </template>

      <el-form :inline="true" :model="draftForm">
        <el-form-item label="scenario_tag">
          <el-input
            v-model="draftForm.scenarioTag"
            style="width: 260px"
            data-testid="realobj-sales-order-scenario-tag"
          />
        </el-form-item>
        <el-form-item label="订单号">
          <el-input v-model="draftForm.orderNo" style="width: 180px" />
        </el-form-item>
        <el-form-item label="客户">
          <el-input v-model="draftForm.customerName" style="width: 170px" />
        </el-form-item>
        <el-form-item label="款号">
          <el-input v-model="draftForm.styleCode" style="width: 150px" />
        </el-form-item>
        <el-form-item label="交期">
          <el-input v-model="draftForm.deliveryDate" style="width: 140px" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="draftForm.status" style="width: 140px">
            <el-option label="草稿" value="draft" />
            <el-option label="待确认" value="pending" />
            <el-option label="已排产" value="planned" />
          </el-select>
        </el-form-item>
      </el-form>

      <el-form :inline="true" :model="draftForm" class="matrix-form">
        <el-form-item label="矩阵(米白 M)">
          <el-input-number v-model="draftForm.matrixWhiteMOrdered" :min="1" :max="99999" />
        </el-form-item>
        <el-form-item label="矩阵(米白 M 已排产)">
          <el-input-number v-model="draftForm.matrixWhiteMPlanned" :min="0" :max="99999" />
        </el-form-item>
        <el-form-item label="矩阵(烟灰 L)">
          <el-input-number v-model="draftForm.matrixGrayLOrdered" :min="1" :max="99999" />
        </el-form-item>
        <el-form-item label="矩阵(烟灰 L 已排产)">
          <el-input-number v-model="draftForm.matrixGrayLPlanned" :min="0" :max="99999" />
        </el-form-item>
      </el-form>

      <el-form :inline="true" :model="draftForm" class="plan-form">
        <el-form-item label="计划号">
          <el-input v-model="draftForm.planNo" style="width: 180px" />
        </el-form-item>
        <el-form-item label="计划数量">
          <el-input-number v-model="draftForm.plannedQty" :min="1" :max="99999" />
        </el-form-item>
        <el-form-item label="计划日期">
          <el-input v-model="draftForm.planDate" style="width: 140px" />
        </el-form-item>
        <el-form-item label="计划状态">
          <el-select v-model="draftForm.planStatus" style="width: 140px">
            <el-option label="草稿" value="draft" />
            <el-option label="待锁定" value="pending_lock" />
            <el-option label="进行中" value="running" />
          </el-select>
        </el-form-item>
      </el-form>

      <div class="local-write-actions">
        <el-button type="primary" :loading="localWriteLoading" @click="saveObject">
          {{ saveButtonLabel }}
        </el-button>
        <el-button :loading="localWriteLoading" :disabled="!currentObjectId" @click="readbackObject">回读本地对象</el-button>
        <el-button :loading="localWriteLoading" :disabled="!currentPlanObjectId" @click="rollbackScenario">回滚 scenario</el-button>
        <el-button :loading="localWriteLoading" @click="checkZeroResidual">zero_residual 校验</el-button>
      </div>

      <el-alert
        v-if="localWriteFeedback"
        type="info"
        :closable="false"
        :title="localWriteFeedback"
        class="feedback-alert"
      />

      <el-descriptions border :column="2" class="readback-descriptions">
        <el-descriptions-item label="object_id">{{ currentObjectId || '-' }}</el-descriptions-item>
        <el-descriptions-item label="plan_object_id">{{ currentPlanObjectId || '-' }}</el-descriptions-item>
        <el-descriptions-item label="scenario_tag">{{ draftForm.scenarioTag }}</el-descriptions-item>
        <el-descriptions-item label="readback_total">{{ readbackTotal }}</el-descriptions-item>
        <el-descriptions-item label="plan_total">{{ planReadbackTotal }}</el-descriptions-item>
        <el-descriptions-item label="residual_records">{{ loopState.residualRecordsAfterRollback }}</el-descriptions-item>
        <el-descriptions-item label="create_success">{{ loopState.createSuccess ? 'true' : 'false' }}</el-descriptions-item>
        <el-descriptions-item label="update_success">{{ loopState.updateSuccess ? 'true' : 'false' }}</el-descriptions-item>
        <el-descriptions-item label="readback_success">{{ loopState.readbackSuccess ? 'true' : 'false' }}</el-descriptions-item>
        <el-descriptions-item label="rollback_success">{{ loopState.rollbackSuccess ? 'true' : 'false' }}</el-descriptions-item>
        <el-descriptions-item label="zero_residual_success">{{ loopState.zeroResidualSuccess ? 'true' : 'false' }}</el-descriptions-item>
        <el-descriptions-item label="test_data_used">true</el-descriptions-item>
      </el-descriptions>

      <el-descriptions
        v-if="readbackState"
        border
        :column="2"
        class="readback-descriptions"
        data-testid="realobj-sales-order-readback-evidence"
      >
        <el-descriptions-item label="sales_order_readback_success">
          {{ readbackState.readback_flags.sales_order_readback_success ? 'true' : 'false' }}
        </el-descriptions-item>
        <el-descriptions-item label="order_detail_readback_success">
          {{ readbackState.readback_flags.order_detail_readback_success ? 'true' : 'false' }}
        </el-descriptions-item>
        <el-descriptions-item label="quantity_matrix_readback_success">
          {{ readbackState.readback_flags.quantity_matrix_readback_success ? 'true' : 'false' }}
        </el-descriptions-item>
        <el-descriptions-item label="production_plan_readback_success">
          {{ readbackState.readback_flags.production_plan_readback_success ? 'true' : 'false' }}
        </el-descriptions-item>
        <el-descriptions-item label="status_validation_readback_success">
          {{ readbackState.readback_flags.status_validation_readback_success ? 'true' : 'false' }}
        </el-descriptions-item>
        <el-descriptions-item label="scenario_tag_present">
          {{ readbackState.readback_flags.scenario_tag_present ? 'true' : 'false' }}
        </el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { request } from '@/api/request'

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

interface SalesOrderReadbackFlags {
  scenario_tag_present: boolean
  sales_order_readback_success: boolean
  order_detail_readback_success: boolean
  quantity_matrix_readback_success: boolean
  production_plan_readback_success: boolean
  status_validation_readback_success: boolean
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
  readback_flags: SalesOrderReadbackFlags
  created_at: string
  updated_at: string
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

interface RollbackData {
  scenario_tag: string
  object_id: number
  sales_deleted_count: number
  plan_deleted_count: number
  sales_residual_records_after_rollback: number
  plan_residual_records_after_rollback: number
  residual_records_after_rollback: number
  rollback_success: boolean
  zero_residual_success: boolean
}

const router = useRouter()

const SALES_ORDER_ENDPOINT = '/api/local-dev/sales-orders'
const PRODUCTION_PLAN_ENDPOINT = '/api/local-dev/production-plans'

const query = reactive({
  keyword: '',
  customer: '',
  styleCode: '',
  status: '',
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

const buildDatePart = (): string => {
  const now = new Date()
  const yyyy = now.getFullYear()
  const mm = String(now.getMonth() + 1).padStart(2, '0')
  const dd = String(now.getDate()).padStart(2, '0')
  return `${yyyy}${mm}${dd}`
}

const buildDefaultScenarioTag = (): string => `REALOBJ-CAND003-B019-${buildDatePart()}-001`
const normalizeScenarioTag = (value: string): string => value.trim() || buildDefaultScenarioTag()

const draftForm = reactive({
  scenarioTag: buildDefaultScenarioTag(),
  orderNo: 'SO-YS-260601',
  customerName: '青禾服饰',
  styleCode: 'JK-2410',
  deliveryDate: '2026-06-12',
  status: 'draft',
  note: 'REALOBJ-CAND-003 test_data',
  matrixWhiteMOrdered: 320,
  matrixWhiteMPlanned: 210,
  matrixGrayLOrdered: 280,
  matrixGrayLPlanned: 170,
  planNo: `PP-REALOBJ-${buildDatePart()}-001`,
  plannedQty: 380,
  planDate: '2026-06-08',
  planStatus: 'draft',
})

const localWriteLoading = ref(false)
const localWriteFeedback = ref('')
const currentObjectId = ref<number | null>(null)
const currentPlanObjectId = ref<number | null>(null)
const readbackState = ref<SalesOrderReadbackData | null>(null)
const readbackTotal = ref(0)
const planReadbackTotal = ref(0)

const loopState = reactive({
  createSuccess: false,
  updateSuccess: false,
  readbackSuccess: false,
  rollbackSuccess: false,
  zeroResidualSuccess: false,
  residualRecordsAfterRollback: -1,
})

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
    return true
  })
})

const saveButtonLabel = computed(() => (currentObjectId.value ? '更新本地对象' : '保存本地对象'))

const buildQuantityMatrix = (): QuantityMatrixCell[] => [
  {
    color: '米白',
    size: 'M',
    ordered_qty: Number(draftForm.matrixWhiteMOrdered),
    planned_qty: Number(draftForm.matrixWhiteMPlanned),
    delta_qty: Number(draftForm.matrixWhiteMOrdered) - Number(draftForm.matrixWhiteMPlanned),
  },
  {
    color: '烟灰',
    size: 'L',
    ordered_qty: Number(draftForm.matrixGrayLOrdered),
    planned_qty: Number(draftForm.matrixGrayLPlanned),
    delta_qty: Number(draftForm.matrixGrayLOrdered) - Number(draftForm.matrixGrayLPlanned),
  },
]

const buildUpsertPayload = () => {
  const scenarioTag = normalizeScenarioTag(draftForm.scenarioTag)
  draftForm.scenarioTag = scenarioTag
  return {
    scenario_tag: scenarioTag,
    sales_order: {
      order_no: draftForm.orderNo.trim(),
      customer_name: draftForm.customerName.trim(),
      style_code: draftForm.styleCode.trim(),
      delivery_date: draftForm.deliveryDate.trim(),
      status: draftForm.status,
      note: draftForm.note.trim(),
    },
    quantity_matrix: buildQuantityMatrix(),
    production_plan: {
      plan_no: draftForm.planNo.trim(),
      planned_qty: Number(draftForm.plannedQty),
      plan_date: draftForm.planDate.trim(),
      status: draftForm.planStatus,
      note: 'sales-order-local-loop',
    },
    note: draftForm.note.trim(),
  }
}

const postLocalSalesOrder = async (payload: Record<string, unknown>): Promise<SalesOrderReadbackData> => {
  const response = await request<SalesOrderReadbackData>(SALES_ORDER_ENDPOINT, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  return response.data
}

const patchLocalSalesOrder = async (objectId: number, payload: Record<string, unknown>): Promise<SalesOrderReadbackData> => {
  const response = await request<SalesOrderReadbackData>(`${SALES_ORDER_ENDPOINT}/${objectId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  return response.data
}

const getSalesOrderReadback = async (objectId: number, scenarioTag: string): Promise<SalesOrderReadbackData> => {
  const queryString = new URLSearchParams({ scenario_tag: scenarioTag }).toString()
  const response = await request<SalesOrderReadbackData>(`${SALES_ORDER_ENDPOINT}/${objectId}/readback?${queryString}`)
  return response.data
}

const rollbackProductionPlanByScenario = async (planId: number, scenarioTag: string): Promise<RollbackData> => {
  const response = await request<RollbackData>(`${PRODUCTION_PLAN_ENDPOINT}/${planId}/rollback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scenario_tag: scenarioTag }),
  })
  return response.data
}

const refreshReadbackSummary = async (scenarioTag: string): Promise<void> => {
  const queryString = new URLSearchParams({ scenario_tag: scenarioTag }).toString()
  const orderResp = await request<SalesOrderListData>(`${SALES_ORDER_ENDPOINT}?${queryString}`)
  readbackTotal.value = orderResp.data.total
  const planResp = await request<ProductionPlanListData>(`${PRODUCTION_PLAN_ENDPOINT}?${queryString}`)
  planReadbackTotal.value = planResp.data.total
}

const saveObject = async (): Promise<void> => {
  if (!draftForm.orderNo.trim() || !draftForm.customerName.trim() || !draftForm.styleCode.trim()) {
    ElMessage.warning('请先填写订单号、客户和款号')
    return
  }
  localWriteLoading.value = true
  localWriteFeedback.value = ''
  try {
    const payload = buildUpsertPayload()
    const saved = currentObjectId.value
      ? await patchLocalSalesOrder(currentObjectId.value, payload)
      : await postLocalSalesOrder(payload)

    const wasCreated = !currentObjectId.value
    currentObjectId.value = saved.object_id || saved.draft_id
    currentPlanObjectId.value = saved.production_plan?.draft_id || null
    readbackState.value = saved
    await refreshReadbackSummary(saved.scenario_tag)
    if (wasCreated) {
      loopState.createSuccess = true
    } else {
      loopState.updateSuccess = true
    }
    if (loopState.createSuccess && !wasCreated) {
      loopState.updateSuccess = true
    }
    localWriteFeedback.value = `save_success=true, object_id=${currentObjectId.value}, plan_id=${currentPlanObjectId.value || '-'}, scenario_tag=${saved.scenario_tag}`
    ElMessage.success('本地对象写入成功')
  } catch (error) {
    localWriteFeedback.value = `保存失败：${(error as Error).message}`
    ElMessage.error(localWriteFeedback.value)
  } finally {
    localWriteLoading.value = false
  }
}

const readbackObject = async (): Promise<void> => {
  if (!currentObjectId.value) {
    ElMessage.warning('请先保存本地对象')
    return
  }
  localWriteLoading.value = true
  try {
    const scenarioTag = normalizeScenarioTag(draftForm.scenarioTag)
    draftForm.scenarioTag = scenarioTag
    const readback = await getSalesOrderReadback(currentObjectId.value, scenarioTag)
    readbackState.value = readback
    currentPlanObjectId.value = readback.production_plan?.draft_id || currentPlanObjectId.value
    await refreshReadbackSummary(scenarioTag)
    loopState.readbackSuccess = true
    localWriteFeedback.value = `readback_success=true, object_id=${currentObjectId.value}`
    ElMessage.success('本地对象回读成功')
  } catch (error) {
    loopState.readbackSuccess = false
    localWriteFeedback.value = `回读失败：${(error as Error).message}`
    ElMessage.error(localWriteFeedback.value)
  } finally {
    localWriteLoading.value = false
  }
}

const rollbackScenario = async (): Promise<void> => {
  if (!currentPlanObjectId.value) {
    ElMessage.warning('缺少生产计划对象，请先保存本地对象')
    return
  }
  localWriteLoading.value = true
  try {
    const scenarioTag = normalizeScenarioTag(draftForm.scenarioTag)
    draftForm.scenarioTag = scenarioTag
    const rolled = await rollbackProductionPlanByScenario(currentPlanObjectId.value, scenarioTag)
    loopState.rollbackSuccess = rolled.rollback_success
    loopState.zeroResidualSuccess = rolled.zero_residual_success
    loopState.residualRecordsAfterRollback = rolled.residual_records_after_rollback
    currentObjectId.value = null
    currentPlanObjectId.value = null
    readbackState.value = null
    await refreshReadbackSummary(scenarioTag)
    localWriteFeedback.value = `rollback_success=${rolled.rollback_success}, zero_residual_success=${rolled.zero_residual_success}, residual=${rolled.residual_records_after_rollback}`
    ElMessage.success('scenario 回滚完成')
  } catch (error) {
    loopState.rollbackSuccess = false
    localWriteFeedback.value = `回滚失败：${(error as Error).message}`
    ElMessage.error(localWriteFeedback.value)
  } finally {
    localWriteLoading.value = false
  }
}

const checkZeroResidual = async (): Promise<void> => {
  const scenarioTag = normalizeScenarioTag(draftForm.scenarioTag)
  draftForm.scenarioTag = scenarioTag
  localWriteLoading.value = true
  try {
    await refreshReadbackSummary(scenarioTag)
    const residual = Math.max(readbackTotal.value, planReadbackTotal.value)
    loopState.residualRecordsAfterRollback = residual
    loopState.zeroResidualSuccess = residual === 0
    localWriteFeedback.value = `zero_residual_check: scenario_tag=${scenarioTag}, residual=${residual}`
    if (residual === 0) {
      ElMessage.success('zero_residual 校验通过')
    } else {
      ElMessage.warning(`zero_residual 未通过，残留 ${residual} 条`)
    }
  } catch (error) {
    localWriteFeedback.value = `zero_residual 校验失败：${(error as Error).message}`
    ElMessage.error(localWriteFeedback.value)
  } finally {
    localWriteLoading.value = false
  }
}

const resetQuery = (): void => {
  query.keyword = ''
  query.customer = ''
  query.styleCode = ''
  query.status = ''
}

const statusTagType = (status: string): 'success' | 'warning' | 'danger' | 'info' => {
  if (status === '已排产') return 'success'
  if (status === '待交期评估') return 'danger'
  if (status === '待确认') return 'warning'
  return 'info'
}

const loadRowToLoop = (row: SalesOrderRow): void => {
  draftForm.orderNo = row.orderNo
  draftForm.customerName = row.customerName
  draftForm.styleCode = row.styleCode
  draftForm.deliveryDate = row.deliveryDate
  draftForm.planNo = `PP-${row.orderNo}`
  draftForm.note = `from:${row.orderNo}`
  draftForm.matrixWhiteMOrdered = Math.max(120, Math.floor(row.orderQty * 0.55))
  draftForm.matrixWhiteMPlanned = Math.max(80, Math.floor(row.plannedQty * 0.55))
  draftForm.matrixGrayLOrdered = Math.max(120, row.orderQty - draftForm.matrixWhiteMOrdered)
  draftForm.matrixGrayLPlanned = Math.max(60, row.plannedQty - draftForm.matrixWhiteMPlanned)
  draftForm.plannedQty = Math.max(1, row.plannedQty || draftForm.matrixWhiteMPlanned + draftForm.matrixGrayLPlanned)
  ElMessage.info(`已加载 ${row.orderNo} 到本地对象表单`)
}

const openDetail = (row: SalesOrderRow): void => {
  router.push({
    path: '/sales-inventory/sales-orders/detail',
    query: {
      order_no: row.orderNo,
      customer_name: row.customerName,
      style_code: row.styleCode,
      object_id: currentObjectId.value ? String(currentObjectId.value) : '',
      scenario_tag: normalizeScenarioTag(draftForm.scenarioTag),
      parity: 'realobj-cand003-local-loop',
    },
  })
}

const goProductionPlans = (): void => {
  router.push({
    path: '/production/plans',
    query: {
      scenario_tag: normalizeScenarioTag(draftForm.scenarioTag),
      object_id: currentPlanObjectId.value ? String(currentPlanObjectId.value) : '',
      parity: 'realobj-cand003-local-loop',
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

.query-panel {
  margin-bottom: 8px;
  padding: 8px 0 0;
}

.result-table {
  width: 100%;
}

.local-write-panel {
  margin-top: 2px;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.matrix-form,
.plan-form {
  margin-top: 8px;
}

.local-write-actions {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.feedback-alert {
  margin-top: 10px;
}

.readback-descriptions {
  margin-top: 10px;
}
</style>
