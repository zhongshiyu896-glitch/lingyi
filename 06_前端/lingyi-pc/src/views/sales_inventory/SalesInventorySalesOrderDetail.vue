<template>
  <div class="sales-order-detail-page">
    <el-card shadow="never" data-testid="mvp-sales-order-detail-master">
      <template #header>
        <div class="header-row">
          <div>
            <h2>销售订单详情（本地草稿）</h2>
            <p class="sub-title">MVP-CAND-004 / local-dev/sqlite/scenario_tag</p>
          </div>
          <div class="header-actions">
            <el-button @click="goList">返回列表</el-button>
            <el-button type="primary" plain data-testid="mvp-production-plan-link" @click="goProductionPlan">
              查看生产计划联动
            </el-button>
          </div>
        </div>
      </template>

      <el-alert
        type="info"
        :closable="false"
        title="本页面写入仅走 local-dev 接口；禁止生产写、ERPNext 生产写、真实生产账号。"
        class="scope-alert"
      />

      <el-form label-width="120px">
        <el-form-item label="订单号">
          <el-input v-model="form.orderNo" data-testid="mvp-sales-order-order-no-input" />
        </el-form-item>
        <el-form-item label="客户">
          <el-input v-model="form.customerName" data-testid="mvp-sales-order-customer-input" />
        </el-form-item>
        <el-form-item label="款号">
          <el-input v-model="form.styleCode" data-testid="mvp-sales-order-style-code-input" />
        </el-form-item>
        <el-form-item label="交期">
          <el-date-picker v-model="form.deliveryDate" type="date" value-format="YYYY-MM-DD" style="width: 240px" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="form.status" style="width: 220px">
            <el-option label="draft" value="draft" />
            <el-option label="saved" value="saved" />
            <el-option label="cancelled" value="cancelled" />
          </el-select>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" data-testid="mvp-sales-order-quantity-matrix">
      <template #header>
        <div class="card-title">数量矩阵（至少 2 个颜色/尺码格）</div>
      </template>
      <el-table :data="matrixRows" border>
        <el-table-column prop="color" label="颜色" min-width="120">
          <template #default="{ row }">
            <el-input v-model="row.color" />
          </template>
        </el-table-column>
        <el-table-column prop="size" label="尺码" min-width="120">
          <template #default="{ row }">
            <el-input v-model="row.size" />
          </template>
        </el-table-column>
        <el-table-column prop="orderedQty" label="订单数量" min-width="140">
          <template #default="{ row }">
            <el-input-number v-model="row.orderedQty" :min="0" :precision="0" :step="1" />
          </template>
        </el-table-column>
        <el-table-column prop="plannedQty" label="已排产数量" min-width="150">
          <template #default="{ row }">
            <el-input-number v-model="row.plannedQty" :min="0" :precision="0" :step="1" />
          </template>
        </el-table-column>
        <el-table-column label="差异数量" min-width="130">
          <template #default="{ row }">
            <strong>{{ row.orderedQty - row.plannedQty }}</strong>
          </template>
        </el-table-column>
      </el-table>
      <div class="matrix-delta" data-testid="mvp-sales-order-matrix-delta">
        合计订单数量：{{ matrixSummary.orderedQty }}；合计已排产：{{ matrixSummary.plannedQty }}；差异：{{ matrixSummary.deltaQty }}
      </div>
    </el-card>

    <el-card shadow="never" data-testid="mvp-sales-order-local-draft">
      <template #header>
        <div class="card-title">本地草稿写闭环</div>
      </template>

      <el-form :inline="true">
        <el-form-item label="scenario_tag">
          <el-input v-model="scenarioTag" style="width: 300px" data-testid="mvp-sales-order-scenario-tag-input" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="note" style="width: 360px" />
        </el-form-item>
      </el-form>

      <div class="local-actions">
        <el-button
          type="primary"
          :loading="localWriteLoading"
          data-testid="mvp-sales-order-local-save"
          @click="saveDraft"
        >
          保存草稿
        </el-button>
        <el-button
          :loading="localWriteLoading"
          :disabled="!currentDraftId"
          data-testid="mvp-sales-order-local-cancel"
          @click="cancelDraft"
        >
          取消草稿
        </el-button>
        <el-button
          :loading="localWriteLoading"
          :disabled="!currentDraftId"
          data-testid="mvp-sales-order-local-readback"
          @click="readbackDraft"
        >
          回读草稿
        </el-button>
        <el-button
          type="danger"
          plain
          :loading="localWriteLoading"
          data-testid="mvp-sales-order-rollback-zero-residual"
          @click="rollbackScenario"
        >
          rollback + zero_residual
        </el-button>
      </div>

      <el-alert v-if="feedback" :title="feedback" type="info" :closable="false" class="scope-alert" />

      <el-descriptions border :column="2">
        <el-descriptions-item label="draft_id">{{ currentDraftId || '-' }}</el-descriptions-item>
        <el-descriptions-item label="scenario_tag">{{ scenarioTag || '-' }}</el-descriptions-item>
        <el-descriptions-item label="save_success">{{ String(loopState.saveSuccess) }}</el-descriptions-item>
        <el-descriptions-item label="draft_id_created">{{ String(loopState.draftIdCreated) }}</el-descriptions-item>
        <el-descriptions-item label="quantity_matrix_saved">{{ String(loopState.quantityMatrixSaved) }}</el-descriptions-item>
        <el-descriptions-item label="production_plan_draft_created">{{ String(loopState.productionPlanDraftCreated) }}</el-descriptions-item>
        <el-descriptions-item label="cancel_success">{{ String(loopState.cancelSuccess) }}</el-descriptions-item>
        <el-descriptions-item label="readback_success">{{ String(loopState.readbackSuccess) }}</el-descriptions-item>
        <el-descriptions-item label="rollback_success">{{ String(loopState.rollbackSuccess) }}</el-descriptions-item>
        <el-descriptions-item label="zero_residual_success">{{ String(loopState.zeroResidualSuccess) }}</el-descriptions-item>
        <el-descriptions-item label="residual_records_after_rollback">
          {{ loopState.residualRecordsAfterRollback }}
        </el-descriptions-item>
        <el-descriptions-item label="data_classification">test_data</el-descriptions-item>
        <el-descriptions-item label="seed_data_used">false</el-descriptions-item>
        <el-descriptions-item label="sqlite_not_formal_database">true</el-descriptions-item>
        <el-descriptions-item label="sqlite_direct_reuse_for_production_forbidden">true</el-descriptions-item>
      </el-descriptions>

      <div class="loop-metrics">
        <span class="anchor-mark" data-testid="mvp-sales-loop-save-success">{{ String(loopState.saveSuccess) }}</span>
        <span class="anchor-mark" data-testid="mvp-sales-loop-draft-id-created">{{ String(loopState.draftIdCreated) }}</span>
        <span class="anchor-mark" data-testid="mvp-sales-loop-quantity-matrix-saved">{{ String(loopState.quantityMatrixSaved) }}</span>
        <span class="anchor-mark" data-testid="mvp-sales-loop-plan-draft-created">{{ String(loopState.productionPlanDraftCreated) }}</span>
        <span class="anchor-mark" data-testid="mvp-sales-loop-cancel-success">{{ String(loopState.cancelSuccess) }}</span>
        <span class="anchor-mark" data-testid="mvp-sales-loop-readback-success">{{ String(loopState.readbackSuccess) }}</span>
        <span class="anchor-mark" data-testid="mvp-sales-loop-rollback-success">{{ String(loopState.rollbackSuccess) }}</span>
        <span class="anchor-mark" data-testid="mvp-sales-loop-zero-residual-success">{{ String(loopState.zeroResidualSuccess) }}</span>
        <span class="anchor-mark" data-testid="mvp-sales-loop-residual">{{ String(loopState.residualRecordsAfterRollback) }}</span>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { request } from '@/api/request'

interface MatrixRow {
  color: string
  size: string
  orderedQty: number
  plannedQty: number
}

interface SalesOrderDraftPayload {
  draft_id?: number
  scenario_tag: string
  order_no: string
  customer_name: string
  style_code: string
  delivery_date: string
  status: string
  quantity_matrix: Array<{
    color: string
    size: string
    ordered_qty: number
    planned_qty: number
    delta_qty: number
  }>
  linked_plan_draft_id?: number
  note: string
}

interface SalesOrderDraftData {
  draft_id: number
  scenario_tag: string
  order_no: string
  customer_name: string
  style_code: string
  delivery_date: string
  status: string
  quantity_matrix: Array<{
    color: string
    size: string
    ordered_qty: number
    planned_qty: number
    delta_qty: number
  }>
  linked_plan_draft_id: number | null
  state: string
  quantity_matrix_saved: boolean
  production_plan_draft_created: boolean
}

interface ProductionPlanDraftData {
  draft_id: number
  scenario_tag: string
  order_draft_id: number | null
  order_no: string
  style_code: string
  plan_no: string
  planned_qty: number
  plan_date: string
  status: string
}

interface RollbackData {
  rollback_success: boolean
  zero_residual_success: boolean
  residual_records_after_rollback: number
}

interface ResidualData {
  total: number
}

const route = useRoute()
const router = useRouter()

const form = reactive({
  orderNo: '',
  customerName: '',
  styleCode: '',
  deliveryDate: '',
  status: 'draft',
})

const scenarioTag = ref('')
const note = ref('')
const currentDraftId = ref<number | null>(null)
const linkedPlanDraftId = ref<number | null>(null)
const localWriteLoading = ref(false)
const feedback = ref('')

const matrixRows = ref<MatrixRow[]>([
  { color: '白色', size: 'M', orderedQty: 60, plannedQty: 30 },
  { color: '黑色', size: 'L', orderedQty: 50, plannedQty: 25 },
])

const loopState = reactive({
  saveSuccess: false,
  draftIdCreated: false,
  quantityMatrixSaved: false,
  productionPlanDraftCreated: false,
  cancelSuccess: false,
  readbackSuccess: false,
  rollbackSuccess: false,
  zeroResidualSuccess: false,
  residualRecordsAfterRollback: -1,
})

const matrixSummary = computed(() => {
  const orderedQty = matrixRows.value.reduce((sum, row) => sum + Number(row.orderedQty || 0), 0)
  const plannedQty = matrixRows.value.reduce((sum, row) => sum + Number(row.plannedQty || 0), 0)
  return {
    orderedQty,
    plannedQty,
    deltaQty: orderedQty - plannedQty,
  }
})

const buildScenarioTag = (): string => {
  const stamp = new Date().toISOString().replace(/[-:TZ.]/g, '').slice(0, 14)
  return `MVP-CAND004-${stamp}`
}

const normalizeScenarioTag = (value: string): string => value.trim() || buildScenarioTag()

const matrixPayload = () =>
  matrixRows.value.map((row) => ({
    color: row.color.trim(),
    size: row.size.trim(),
    ordered_qty: Number(row.orderedQty || 0),
    planned_qty: Number(row.plannedQty || 0),
    delta_qty: Number(row.orderedQty || 0) - Number(row.plannedQty || 0),
  }))

const mapDraftToForm = (draft: SalesOrderDraftData): void => {
  currentDraftId.value = draft.draft_id
  linkedPlanDraftId.value = draft.linked_plan_draft_id
  scenarioTag.value = draft.scenario_tag
  form.orderNo = draft.order_no
  form.customerName = draft.customer_name
  form.styleCode = draft.style_code
  form.deliveryDate = draft.delivery_date
  form.status = draft.status || 'draft'
  matrixRows.value = draft.quantity_matrix.map((cell) => ({
    color: cell.color,
    size: cell.size,
    orderedQty: Number(cell.ordered_qty || 0),
    plannedQty: Number(cell.planned_qty || 0),
  }))
}

const upsertSalesOrderDraft = async (payload: SalesOrderDraftPayload): Promise<SalesOrderDraftData> => {
  const response = await request<SalesOrderDraftData>('/api/local-dev/sales-order-drafts', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  return response.data
}

const getSalesOrderDraft = async (draftId: number): Promise<SalesOrderDraftData> => {
  const response = await request<SalesOrderDraftData>(`/api/local-dev/sales-order-drafts/${draftId}`)
  return response.data
}

const cancelSalesOrderDraft = async (draftId: number, tag: string): Promise<SalesOrderDraftData> => {
  const response = await request<SalesOrderDraftData>(`/api/local-dev/sales-order-drafts/${draftId}/cancel`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scenario_tag: tag, reason: `CANCEL-${tag}` }),
  })
  return response.data
}

const upsertProductionPlanDraft = async (payload: {
  scenario_tag: string
  order_draft_id: number
  order_no: string
  style_code: string
  planned_qty: number
  plan_date: string
  status: string
  note: string
  draft_id?: number
}): Promise<ProductionPlanDraftData> => {
  const response = await request<ProductionPlanDraftData>('/api/local-dev/production-plan-drafts', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  return response.data
}

const rollbackSalesOrderByScenario = async (tag: string): Promise<RollbackData> => {
  const response = await request<RollbackData>('/api/local-dev/sales-order-drafts/rollback-by-scenario', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scenario_tag: tag }),
  })
  return response.data
}

const rollbackProductionPlansByScenario = async (tag: string): Promise<RollbackData> => {
  const response = await request<RollbackData>('/api/local-dev/production-plan-drafts/rollback-by-scenario', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scenario_tag: tag }),
  })
  return response.data
}

const fetchSalesOrderResidual = async (tag: string): Promise<number> => {
  const query = new URLSearchParams({ scenario_tag: tag }).toString()
  const response = await request<ResidualData>(`/api/local-dev/sales-order-drafts/residual-count?${query}`)
  return Number(response.data.total || 0)
}

const fetchProductionPlanResidual = async (tag: string): Promise<number> => {
  const query = new URLSearchParams({ scenario_tag: tag }).toString()
  const response = await request<ResidualData>(`/api/local-dev/production-plan-drafts/residual-count?${query}`)
  return Number(response.data.total || 0)
}

const saveDraft = async (): Promise<void> => {
  const tag = normalizeScenarioTag(scenarioTag.value)
  scenarioTag.value = tag
  if (!form.orderNo.trim() || !form.customerName.trim() || !form.styleCode.trim()) {
    ElMessage.warning('请填写订单号、客户、款号')
    return
  }
  if (matrixRows.value.length < 2) {
    ElMessage.warning('至少保留两个数量矩阵格')
    return
  }

  localWriteLoading.value = true
  feedback.value = ''
  try {
    const saved = await upsertSalesOrderDraft({
      draft_id: currentDraftId.value || undefined,
      scenario_tag: tag,
      order_no: form.orderNo.trim(),
      customer_name: form.customerName.trim(),
      style_code: form.styleCode.trim(),
      delivery_date: form.deliveryDate || new Date().toISOString().slice(0, 10),
      status: 'draft',
      quantity_matrix: matrixPayload(),
      linked_plan_draft_id: linkedPlanDraftId.value || undefined,
      note: note.value.trim(),
    })
    mapDraftToForm(saved)
    loopState.saveSuccess = true
    loopState.draftIdCreated = Boolean(saved.draft_id)
    loopState.quantityMatrixSaved = saved.quantity_matrix_saved

    const plan = await upsertProductionPlanDraft({
      draft_id: linkedPlanDraftId.value || undefined,
      scenario_tag: tag,
      order_draft_id: saved.draft_id,
      order_no: form.orderNo.trim(),
      style_code: form.styleCode.trim(),
      planned_qty: Math.max(1, matrixSummary.value.plannedQty || Math.floor(matrixSummary.value.orderedQty * 0.7)),
      plan_date: form.deliveryDate || new Date().toISOString().slice(0, 10),
      status: 'draft',
      note: `AUTO-LINK-${tag}`,
    })
    linkedPlanDraftId.value = plan.draft_id
    await upsertSalesOrderDraft({
      draft_id: saved.draft_id,
      scenario_tag: tag,
      order_no: form.orderNo.trim(),
      customer_name: form.customerName.trim(),
      style_code: form.styleCode.trim(),
      delivery_date: form.deliveryDate || new Date().toISOString().slice(0, 10),
      status: 'draft',
      quantity_matrix: matrixPayload(),
      linked_plan_draft_id: plan.draft_id,
      note: note.value.trim(),
    })
    loopState.productionPlanDraftCreated = true
    feedback.value = `save_success=true, draft_id=${saved.draft_id}, production_plan_draft_id=${plan.draft_id}, scenario_tag=${tag}`
    ElMessage.success('销售订单与生产计划草稿保存成功')
  } catch (error) {
    loopState.saveSuccess = false
    loopState.draftIdCreated = false
    loopState.quantityMatrixSaved = false
    loopState.productionPlanDraftCreated = false
    feedback.value = `保存失败：${(error as Error).message}`
    ElMessage.error(feedback.value)
  } finally {
    localWriteLoading.value = false
  }
}

const cancelDraft = async (): Promise<void> => {
  if (!currentDraftId.value) {
    ElMessage.warning('请先保存草稿')
    return
  }
  const tag = normalizeScenarioTag(scenarioTag.value)
  localWriteLoading.value = true
  try {
    const cancelled = await cancelSalesOrderDraft(currentDraftId.value, tag)
    loopState.cancelSuccess = cancelled.state === 'cancelled'
    feedback.value = `cancel_success=${loopState.cancelSuccess}, state=${cancelled.state}`
    ElMessage.success('草稿取消成功')
  } catch (error) {
    loopState.cancelSuccess = false
    feedback.value = `取消失败：${(error as Error).message}`
    ElMessage.error(feedback.value)
  } finally {
    localWriteLoading.value = false
  }
}

const readbackDraft = async (): Promise<void> => {
  if (!currentDraftId.value) {
    ElMessage.warning('请先保存草稿')
    return
  }
  localWriteLoading.value = true
  try {
    const readback = await getSalesOrderDraft(currentDraftId.value)
    mapDraftToForm(readback)
    loopState.readbackSuccess = true
    feedback.value = `readback_success=true, draft_id=${readback.draft_id}, scenario_tag=${readback.scenario_tag}`
    ElMessage.success('草稿回读成功')
  } catch (error) {
    loopState.readbackSuccess = false
    feedback.value = `回读失败：${(error as Error).message}`
    ElMessage.error(feedback.value)
  } finally {
    localWriteLoading.value = false
  }
}

const rollbackScenario = async (): Promise<void> => {
  const tag = normalizeScenarioTag(scenarioTag.value)
  scenarioTag.value = tag
  localWriteLoading.value = true
  try {
    const salesRollback = await rollbackSalesOrderByScenario(tag)
    const planRollback = await rollbackProductionPlansByScenario(tag)
    const salesResidual = await fetchSalesOrderResidual(tag)
    const planResidual = await fetchProductionPlanResidual(tag)
    const residual = salesResidual + planResidual
    loopState.rollbackSuccess = salesRollback.rollback_success && planRollback.rollback_success
    loopState.zeroResidualSuccess = residual === 0
    loopState.residualRecordsAfterRollback = residual
    if (residual === 0) {
      currentDraftId.value = null
      linkedPlanDraftId.value = null
    }
    feedback.value = `rollback_success=${loopState.rollbackSuccess}, zero_residual_success=${loopState.zeroResidualSuccess}, residual=${residual}`
    ElMessage.success('rollback 完成')
  } catch (error) {
    loopState.rollbackSuccess = false
    loopState.zeroResidualSuccess = false
    feedback.value = `rollback 失败：${(error as Error).message}`
    ElMessage.error(feedback.value)
  } finally {
    localWriteLoading.value = false
  }
}

const goList = (): void => {
  router.push('/sales-inventory/sales-orders')
}

const goProductionPlan = (): void => {
  router.push({
    path: '/production/plans',
    query: {
      scenario_tag: scenarioTag.value || undefined,
      order_no: form.orderNo || undefined,
      style_code: form.styleCode || undefined,
    },
  })
}

const tryLoadInitialDraft = async (): Promise<void> => {
  const rawDraftId = Array.isArray(route.query.draft_id) ? route.query.draft_id[0] : route.query.draft_id
  const draftId = Number(rawDraftId || 0)
  if (Number.isFinite(draftId) && draftId > 0) {
    try {
      const draft = await getSalesOrderDraft(draftId)
      mapDraftToForm(draft)
      return
    } catch {
      // ignore initial readback error and continue with query defaults
    }
  }
  form.orderNo = String(Array.isArray(route.query.order_no) ? route.query.order_no[0] : route.query.order_no || `SO-${Date.now()}`)
  form.customerName = String(
    Array.isArray(route.query.customer_name) ? route.query.customer_name[0] : route.query.customer_name || '本地演示客户',
  )
  form.styleCode = String(Array.isArray(route.query.style_code) ? route.query.style_code[0] : route.query.style_code || 'STYLE-LOCAL-01')
  form.deliveryDate = new Date().toISOString().slice(0, 10)
  scenarioTag.value = normalizeScenarioTag(
    String(Array.isArray(route.query.scenario_tag) ? route.query.scenario_tag[0] : route.query.scenario_tag || ''),
  )
}

onMounted(() => {
  void tryLoadInitialDraft()
})
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

.card-title {
  font-weight: 600;
}

.matrix-delta {
  margin-top: 12px;
  color: var(--el-text-color-regular);
}

.local-actions {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.loop-metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 6px 10px;
  margin-top: 12px;
}

.anchor-mark {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
</style>
