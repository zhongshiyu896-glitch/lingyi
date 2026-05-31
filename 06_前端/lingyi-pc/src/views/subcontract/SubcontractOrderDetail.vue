<template>
  <div class="purchase-detail-page">
    <el-card shadow="never" data-testid="mvp-purchase-production-safety">
      <template #header>
        <div class="header-row">
          <div>
            <h2>采购 / 外协前置单据详情（本地草稿）</h2>
            <p class="sub-title">MVP-CAND-005 / local-dev/sqlite/scenario_tag</p>
          </div>
          <el-button @click="goList">返回列表</el-button>
        </div>
      </template>
      <el-alert
        type="warning"
        :closable="false"
        title="写入仅限 local-dev/sqlite/scenario_tag；禁止生产写、ERPNext production 写、真实账号写。"
      />
    </el-card>

    <el-card shadow="never" data-testid="mvp-purchase-order-master">
      <template #header>
        <span>单据主信息</span>
      </template>
      <el-form label-width="130px">
        <el-form-item label="单据号">
          <el-input v-model="form.documentNo" />
        </el-form-item>
        <el-form-item label="供应商/加工厂">
          <el-input v-model="form.partnerName" />
        </el-form-item>
        <el-form-item label="伙伴类型">
          <el-select v-model="form.partnerType" style="width: 220px">
            <el-option label="supplier" value="supplier" />
            <el-option label="factory" value="factory" />
          </el-select>
        </el-form-item>
        <el-form-item label="单据类型">
          <el-select v-model="form.documentType" style="width: 220px">
            <el-option label="purchase" value="purchase" />
            <el-option label="subcontract" value="subcontract" />
          </el-select>
        </el-form-item>
        <el-form-item label="业务日期">
          <el-date-picker v-model="form.businessDate" type="date" value-format="YYYY-MM-DD" style="width: 220px" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="form.status" style="width: 220px">
            <el-option label="draft" value="draft" />
            <el-option label="saved" value="saved" />
            <el-option label="cancelled" value="cancelled" />
          </el-select>
        </el-form-item>
        <el-form-item label="物料类别">
          <el-select v-model="form.materialCategory" style="width: 220px">
            <el-option label="fabric" value="fabric" />
            <el-option label="trim" value="trim" />
            <el-option label="packaging" value="packaging" />
            <el-option label="mixed" value="mixed" />
          </el-select>
        </el-form-item>
        <el-form-item label="前置单据">
          <el-input v-model="form.predecessorDocNo" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.note" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" data-testid="mvp-purchase-material-line">
      <template #header>
        <span>物料明细（至少 1 条）</span>
      </template>
      <el-table :data="materialLines" border>
        <el-table-column label="物料编码" min-width="150">
          <template #default="{ row }">
            <el-input v-model="row.materialCode" />
          </template>
        </el-table-column>
        <el-table-column label="物料名称" min-width="150">
          <template #default="{ row }">
            <el-input v-model="row.materialName" />
          </template>
        </el-table-column>
        <el-table-column label="颜色/规格" min-width="140">
          <template #default="{ row }">
            <el-input v-model="row.colorSpec" />
          </template>
        </el-table-column>
        <el-table-column label="单位" width="100">
          <template #default="{ row }">
            <el-input v-model="row.uom" />
          </template>
        </el-table-column>
        <el-table-column label="需求数量" width="130">
          <template #default="{ row }">
            <el-input-number v-model="row.demandQty" :min="0" :precision="3" :step="1" />
          </template>
        </el-table-column>
        <el-table-column label="采购/外协数量" width="140">
          <template #default="{ row }">
            <el-input-number v-model="row.purchaseQty" :min="0" :precision="3" :step="1" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="90">
          <template #default="{ $index }">
            <el-button link type="danger" @click="removeMaterialLine($index)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="line-actions">
        <el-button @click="addMaterialLine">新增物料行</el-button>
      </div>
    </el-card>

    <el-card shadow="never" data-testid="mvp-purchase-issue-return">
      <template #header>
        <span>发料 / 回料状态</span>
      </template>
      <el-form label-width="130px">
        <el-form-item label="发料数量">
          <el-input-number v-model="issueReturn.issuedQty" :min="0" :precision="3" :step="1" />
        </el-form-item>
        <el-form-item label="回料数量">
          <el-input-number v-model="issueReturn.returnedQty" :min="0" :precision="3" :step="1" />
        </el-form-item>
        <el-form-item label="差异数量">
          <strong>{{ issueReturnDelta }}</strong>
        </el-form-item>
        <el-form-item label="操作状态">
          <el-select v-model="issueReturn.state" style="width: 220px">
            <el-option label="draft" value="draft" />
            <el-option label="saved" value="saved" />
            <el-option label="checked" value="checked" />
          </el-select>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" data-testid="mvp-purchase-inspection-settlement">
      <template #header>
        <span>验货 / 结算预览</span>
      </template>
      <el-form label-width="130px">
        <el-form-item label="验收数量">
          <el-input-number v-model="inspection.acceptedQty" :min="0" :precision="3" :step="1" />
        </el-form-item>
        <el-form-item label="不良数量">
          <el-input-number v-model="inspection.rejectedQty" :min="0" :precision="3" :step="1" />
        </el-form-item>
        <el-form-item label="结算数量">
          <el-input-number v-model="inspection.settlementQty" :min="0" :precision="3" :step="1" />
        </el-form-item>
        <el-form-item label="预估金额">
          <el-input-number v-model="inspection.estimatedAmount" :min="0" :precision="2" :step="10" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="inspection.state" style="width: 220px">
            <el-option label="draft" value="draft" />
            <el-option label="saved" value="saved" />
            <el-option label="previewed" value="previewed" />
          </el-select>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" data-testid="mvp-purchase-local-draft">
      <template #header>
        <span>本地草稿写闭环</span>
      </template>

      <el-form :inline="true">
        <el-form-item label="scenario_tag">
          <el-input v-model="scenarioTag" style="width: 320px" />
        </el-form-item>
      </el-form>

      <div class="local-actions">
        <el-button type="primary" :loading="localWriteLoading" data-testid="mvp-purchase-local-save" @click="saveDraft">
          保存草稿
        </el-button>
        <el-button
          :loading="localWriteLoading"
          :disabled="!currentDraftId"
          data-testid="mvp-purchase-local-cancel"
          @click="cancelDraft"
        >
          取消草稿
        </el-button>
        <el-button
          :loading="localWriteLoading"
          :disabled="!currentDraftId"
          data-testid="mvp-purchase-local-readback"
          @click="readbackDraft"
        >
          回读草稿
        </el-button>
        <el-button
          type="danger"
          plain
          :loading="localWriteLoading"
          data-testid="mvp-purchase-rollback-zero-residual"
          @click="rollbackScenario"
        >
          rollback + zero_residual
        </el-button>
      </div>

      <el-alert v-if="feedback" :title="feedback" type="info" :closable="false" class="feedback" />

      <el-descriptions border :column="2">
        <el-descriptions-item label="draft_id">{{ currentDraftId || '-' }}</el-descriptions-item>
        <el-descriptions-item label="scenario_tag">{{ scenarioTag || '-' }}</el-descriptions-item>
        <el-descriptions-item label="save_success">{{ String(loopState.saveSuccess) }}</el-descriptions-item>
        <el-descriptions-item label="draft_id_created">{{ String(loopState.draftIdCreated) }}</el-descriptions-item>
        <el-descriptions-item label="material_line_saved">{{ String(loopState.materialLineSaved) }}</el-descriptions-item>
        <el-descriptions-item label="issue_return_or_inspection_saved">
          {{ String(loopState.issueReturnOrInspectionSaved) }}
        </el-descriptions-item>
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
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { request } from '@/api/request'

interface MaterialLineRow {
  materialCode: string
  materialName: string
  colorSpec: string
  uom: string
  demandQty: number
  purchaseQty: number
}

interface PurchaseDraftPayload {
  draft_id?: number
  scenario_tag: string
  document_no: string
  partner_name: string
  partner_type: string
  document_type: string
  business_date: string
  status: string
  material_category: string
  predecessor_doc_no: string
  note: string
  material_lines: Array<{
    material_code: string
    material_name: string
    color_spec: string
    uom: string
    demand_qty: number
    purchase_qty: number
  }>
  issue_return: {
    issued_qty: number
    returned_qty: number
    state: string
  }
  inspection_settlement: {
    accepted_qty: number
    rejected_qty: number
    settlement_qty: number
    estimated_amount: number
    state: string
  }
}

interface PurchaseDraftData {
  draft_id: number
  scenario_tag: string
  document_no: string
  partner_name: string
  partner_type: string
  document_type: string
  business_date: string
  status: string
  material_category: string
  predecessor_doc_no: string
  note: string
  state: string
  material_lines: Array<{
    material_code: string
    material_name: string
    color_spec: string
    uom: string
    demand_qty: number
    purchase_qty: number
  }>
  issue_return: {
    issued_qty: number
    returned_qty: number
    delta_qty: number
    state: string
  }
  inspection_settlement: {
    accepted_qty: number
    rejected_qty: number
    settlement_qty: number
    estimated_amount: number
    state: string
  }
  material_line_saved: boolean
  issue_return_or_inspection_saved: boolean
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
  documentNo: '',
  partnerName: '',
  partnerType: 'supplier',
  documentType: 'subcontract',
  businessDate: '',
  status: 'draft',
  materialCategory: 'mixed',
  predecessorDocNo: '',
  note: '',
})

const materialLines = ref<MaterialLineRow[]>([
  {
    materialCode: 'MAT-LOCAL-001',
    materialName: '棉布',
    colorSpec: '黑色/L',
    uom: '米',
    demandQty: 100,
    purchaseQty: 80,
  },
])

const issueReturn = reactive({
  issuedQty: 60,
  returnedQty: 40,
  state: 'saved',
})

const inspection = reactive({
  acceptedQty: 36,
  rejectedQty: 4,
  settlementQty: 36,
  estimatedAmount: 1280,
  state: 'previewed',
})

const scenarioTag = ref('')
const currentDraftId = ref<number | null>(null)
const localWriteLoading = ref(false)
const feedback = ref('')

const loopState = reactive({
  saveSuccess: false,
  draftIdCreated: false,
  materialLineSaved: false,
  issueReturnOrInspectionSaved: false,
  cancelSuccess: false,
  readbackSuccess: false,
  rollbackSuccess: false,
  zeroResidualSuccess: false,
  residualRecordsAfterRollback: -1,
})

const issueReturnDelta = computed(() => Number(issueReturn.issuedQty || 0) - Number(issueReturn.returnedQty || 0))

const buildScenarioTag = (): string => {
  const stamp = new Date().toISOString().replace(/[-:TZ.]/g, '').slice(0, 14)
  return `MVP-CAND005-${stamp}`
}

const normalizeScenarioTag = (value: string): string => value.trim() || buildScenarioTag()

const materialLinePayload = () =>
  materialLines.value.map((line) => ({
    material_code: line.materialCode.trim(),
    material_name: line.materialName.trim(),
    color_spec: line.colorSpec.trim(),
    uom: line.uom.trim() || 'PCS',
    demand_qty: Number(line.demandQty || 0),
    purchase_qty: Number(line.purchaseQty || 0),
  }))

const mapDraftToForm = (draft: PurchaseDraftData): void => {
  currentDraftId.value = draft.draft_id
  scenarioTag.value = draft.scenario_tag
  form.documentNo = draft.document_no
  form.partnerName = draft.partner_name
  form.partnerType = draft.partner_type
  form.documentType = draft.document_type
  form.businessDate = draft.business_date
  form.status = draft.status
  form.materialCategory = draft.material_category
  form.predecessorDocNo = draft.predecessor_doc_no
  form.note = draft.note
  materialLines.value = draft.material_lines.map((line) => ({
    materialCode: line.material_code,
    materialName: line.material_name,
    colorSpec: line.color_spec,
    uom: line.uom,
    demandQty: Number(line.demand_qty || 0),
    purchaseQty: Number(line.purchase_qty || 0),
  }))
  issueReturn.issuedQty = Number(draft.issue_return.issued_qty || 0)
  issueReturn.returnedQty = Number(draft.issue_return.returned_qty || 0)
  issueReturn.state = draft.issue_return.state || 'saved'
  inspection.acceptedQty = Number(draft.inspection_settlement.accepted_qty || 0)
  inspection.rejectedQty = Number(draft.inspection_settlement.rejected_qty || 0)
  inspection.settlementQty = Number(draft.inspection_settlement.settlement_qty || 0)
  inspection.estimatedAmount = Number(draft.inspection_settlement.estimated_amount || 0)
  inspection.state = draft.inspection_settlement.state || 'previewed'
}

const upsertDraft = async (payload: PurchaseDraftPayload): Promise<PurchaseDraftData> => {
  const response = await request<PurchaseDraftData>('/api/local-dev/purchase-subcontract-drafts', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  return response.data
}

const getDraft = async (draftId: number): Promise<PurchaseDraftData> => {
  const response = await request<PurchaseDraftData>(`/api/local-dev/purchase-subcontract-drafts/${draftId}`)
  return response.data
}

const cancelDraftById = async (draftId: number, tag: string): Promise<PurchaseDraftData> => {
  const response = await request<PurchaseDraftData>(`/api/local-dev/purchase-subcontract-drafts/${draftId}/cancel`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scenario_tag: tag, reason: `CANCEL-${tag}` }),
  })
  return response.data
}

const rollbackByScenario = async (tag: string): Promise<RollbackData> => {
  const response = await request<RollbackData>('/api/local-dev/purchase-subcontract-drafts/rollback-by-scenario', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scenario_tag: tag }),
  })
  return response.data
}

const fetchResidual = async (tag: string): Promise<number> => {
  const query = new URLSearchParams({ scenario_tag: tag }).toString()
  const response = await request<ResidualData>(`/api/local-dev/purchase-subcontract-drafts/residual-count?${query}`)
  return Number(response.data.total || 0)
}

const saveDraft = async (): Promise<void> => {
  const tag = normalizeScenarioTag(scenarioTag.value)
  scenarioTag.value = tag

  if (!form.documentNo.trim() || !form.partnerName.trim()) {
    ElMessage.warning('请填写单据号和供应商/加工厂')
    return
  }
  const lines = materialLinePayload().filter((line) => line.material_code && line.purchase_qty > 0)
  if (lines.length < 1) {
    ElMessage.warning('至少保留 1 条有效物料明细')
    return
  }

  localWriteLoading.value = true
  feedback.value = ''
  try {
    const saved = await upsertDraft({
      draft_id: currentDraftId.value || undefined,
      scenario_tag: tag,
      document_no: form.documentNo.trim(),
      partner_name: form.partnerName.trim(),
      partner_type: form.partnerType,
      document_type: form.documentType,
      business_date: form.businessDate || new Date().toISOString().slice(0, 10),
      status: form.status,
      material_category: form.materialCategory,
      predecessor_doc_no: form.predecessorDocNo.trim(),
      note: form.note.trim(),
      material_lines: materialLinePayload(),
      issue_return: {
        issued_qty: Number(issueReturn.issuedQty || 0),
        returned_qty: Number(issueReturn.returnedQty || 0),
        state: issueReturn.state,
      },
      inspection_settlement: {
        accepted_qty: Number(inspection.acceptedQty || 0),
        rejected_qty: Number(inspection.rejectedQty || 0),
        settlement_qty: Number(inspection.settlementQty || 0),
        estimated_amount: Number(inspection.estimatedAmount || 0),
        state: inspection.state,
      },
    })
    mapDraftToForm(saved)
    loopState.saveSuccess = true
    loopState.draftIdCreated = Boolean(saved.draft_id)
    loopState.materialLineSaved = saved.material_line_saved
    loopState.issueReturnOrInspectionSaved = saved.issue_return_or_inspection_saved
    feedback.value = `save_success=true, draft_id=${saved.draft_id}, scenario_tag=${saved.scenario_tag}`
    ElMessage.success('采购/外协草稿保存成功')
  } catch (error) {
    loopState.saveSuccess = false
    loopState.draftIdCreated = false
    loopState.materialLineSaved = false
    loopState.issueReturnOrInspectionSaved = false
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
    const cancelled = await cancelDraftById(currentDraftId.value, tag)
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
    const readback = await getDraft(currentDraftId.value)
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
    const rollback = await rollbackByScenario(tag)
    const residual = await fetchResidual(tag)
    loopState.rollbackSuccess = rollback.rollback_success
    loopState.zeroResidualSuccess = residual === 0
    loopState.residualRecordsAfterRollback = residual
    if (residual === 0) {
      currentDraftId.value = null
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

const addMaterialLine = (): void => {
  materialLines.value.push({
    materialCode: '',
    materialName: '',
    colorSpec: '',
    uom: 'PCS',
    demandQty: 0,
    purchaseQty: 0,
  })
}

const removeMaterialLine = (index: number): void => {
  if (materialLines.value.length <= 1) {
    ElMessage.warning('至少保留 1 条物料明细')
    return
  }
  materialLines.value.splice(index, 1)
}

const goList = (): void => {
  router.push({
    path: '/subcontract/list',
    query: {
      parity: Array.isArray(route.query.parity) ? route.query.parity[0] : route.query.parity,
    },
  })
}

const applyDefaultsFromRoute = (): void => {
  const parity = Array.isArray(route.query.parity) ? route.query.parity[0] : route.query.parity
  if (String(parity || '').trim() === 'material-purchase') {
    form.documentType = 'purchase'
  }
  form.documentNo = `PO-LOCAL-${Date.now().toString().slice(-6)}`
  form.partnerName = '本地演示供应商'
  form.businessDate = new Date().toISOString().slice(0, 10)
  scenarioTag.value = normalizeScenarioTag(
    String(Array.isArray(route.query.scenario_tag) ? route.query.scenario_tag[0] : route.query.scenario_tag || ''),
  )
}

const tryLoadInitialDraft = async (): Promise<void> => {
  const rawDraftId = Array.isArray(route.query.id) ? route.query.id[0] : route.query.id
  const draftId = Number(rawDraftId || 0)
  if (Number.isFinite(draftId) && draftId > 0) {
    try {
      const draft = await getDraft(draftId)
      mapDraftToForm(draft)
      return
    } catch {
      // ignore and fallback to defaults
    }
  }
  applyDefaultsFromRoute()
}

onMounted(() => {
  void tryLoadInitialDraft()
})
</script>

<style scoped>
.purchase-detail-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.header-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.header-row h2 {
  margin: 0;
  font-size: 18px;
}

.sub-title {
  margin: 2px 0 0;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.line-actions {
  margin-top: 10px;
}

.local-actions {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.feedback {
  margin-bottom: 12px;
}
</style>
