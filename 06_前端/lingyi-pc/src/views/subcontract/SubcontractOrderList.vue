<template>
  <div class="purchase-list-page" data-testid="yisuan-1to1-subcontract-list-shell">
    <el-card shadow="never">
      <template #header>
        <div class="header-row">
          <div>
            <h2>采购 / 外协单据（本地真实对象闭环）</h2>
            <p class="sub-title">REALOBJ-CAND-004 / local-dev + sqlite + scenario_tag + test_data</p>
          </div>
          <div class="header-actions">
            <el-button type="primary" plain :loading="loading" @click="loadRows">刷新列表</el-button>
          </div>
        </div>
      </template>
      <el-alert
        type="warning"
        :closable="false"
        title="仅允许 local-dev/test_data 写入闭环；禁止任何 production/ERPNext 写入与真实结算/财务/库存影响。"
      />
      <el-alert
        v-if="isMaterialPurchaseParity"
        class="parity-alert"
        type="info"
        :closable="false"
        data-testid="realobj-subcontract-parity-alert"
        title="materialPurchase final_path: /materialPurchase/materialPurchaseProcess -> /subcontract/list?parity=material-purchase"
      />
    </el-card>

    <el-card shadow="never" data-testid="yisuan-1to1-subcontract-list-filter-panel">
      <el-form :inline="true">
        <el-form-item label="关键字">
          <el-input v-model="query.keyword" clearable placeholder="单据号/供应商/物料编码" style="width: 220px" />
        </el-form-item>
        <el-form-item label="伙伴">
          <el-input v-model="query.partnerName" clearable placeholder="供应商/加工厂" style="width: 180px" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.status" clearable placeholder="全部" style="width: 130px">
            <el-option label="draft" value="draft" />
            <el-option label="saved" value="saved" />
            <el-option label="cancelled" value="cancelled" />
          </el-select>
        </el-form-item>
        <el-form-item label="物料类别">
          <el-select v-model="query.materialCategory" clearable placeholder="全部" style="width: 150px">
            <el-option label="fabric" value="fabric" />
            <el-option label="trim" value="trim" />
            <el-option label="packaging" value="packaging" />
            <el-option label="mixed" value="mixed" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="applyQuery">查询</el-button>
          <el-button :loading="loading" @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>

      <el-alert v-if="feedback" :title="feedback" type="info" :closable="false" class="feedback" />

      <el-table :data="rows" border v-loading="loading" empty-text="暂无本地草稿对象（readback only）">
        <el-table-column prop="document_no" label="单据号" min-width="170" />
        <el-table-column prop="partner_name" label="伙伴" min-width="150" />
        <el-table-column prop="document_type" label="类型" min-width="100" />
        <el-table-column prop="material_category" label="物料类别" min-width="110" />
        <el-table-column label="物料行" min-width="100">
          <template #default="{ row }">{{ row.material_lines.length }}</template>
        </el-table-column>
        <el-table-column label="发料/回料" min-width="170">
          <template #default="{ row }">
            发 {{ row.issue_return.issued_qty }} / 回 {{ row.issue_return.returned_qty }} / 差 {{ row.issue_return.delta_qty }}
          </template>
        </el-table-column>
        <el-table-column label="验货/结算预览" min-width="220">
          <template #default="{ row }">
            验 {{ row.inspection_settlement.accepted_qty }} / 退 {{ row.inspection_settlement.rejected_qty }} / 结算
            {{ row.inspection_settlement.settlement_qty }} / 预估 {{ row.inspection_settlement.estimated_amount }}
          </template>
        </el-table-column>
        <el-table-column label="状态" min-width="100">
          <template #default="{ row }">
            <el-tag :type="tagType(row.status)">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="210" fixed="right">
          <template #default="{ row }">
            <div class="row-actions">
              <el-button link type="primary" @click="loadRowToLoop(row)">写入闭环</el-button>
              <el-button link type="primary" @click="openDetail(row.draft_id)">查看详情</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card shadow="never" class="local-write-panel" data-testid="realobj-subcontract-local-loop">
      <template #header>
        <div class="panel-header">
          <strong>REALOBJ-CAND-004 本地写入闭环（采购/外协 + 结算预览）</strong>
          <el-tag type="info">local-dev/sqlite/scenario_tag/test_data only</el-tag>
        </div>
      </template>

      <el-form :inline="true">
        <el-form-item label="scenario_tag">
          <el-input
            v-model="draftForm.scenarioTag"
            data-testid="realobj-subcontract-scenario-tag"
            style="width: 280px"
          />
        </el-form-item>
        <el-form-item label="单据号">
          <el-input v-model="draftForm.documentNo" style="width: 180px" />
        </el-form-item>
        <el-form-item label="伙伴">
          <el-input v-model="draftForm.partnerName" style="width: 170px" />
        </el-form-item>
        <el-form-item label="伙伴类型">
          <el-select v-model="draftForm.partnerType" style="width: 120px">
            <el-option label="supplier" value="supplier" />
            <el-option label="factory" value="factory" />
          </el-select>
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="draftForm.documentType" style="width: 120px">
            <el-option label="purchase" value="purchase" />
            <el-option label="subcontract" value="subcontract" />
          </el-select>
        </el-form-item>
      </el-form>

      <el-form :inline="true" class="loop-form-row">
        <el-form-item label="业务日期">
          <el-input v-model="draftForm.businessDate" style="width: 130px" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="draftForm.status" style="width: 120px">
            <el-option label="draft" value="draft" />
            <el-option label="saved" value="saved" />
            <el-option label="cancelled" value="cancelled" />
          </el-select>
        </el-form-item>
        <el-form-item label="物料类别">
          <el-select v-model="draftForm.materialCategory" style="width: 130px">
            <el-option label="fabric" value="fabric" />
            <el-option label="trim" value="trim" />
            <el-option label="packaging" value="packaging" />
            <el-option label="mixed" value="mixed" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="draftForm.note" style="width: 300px" />
        </el-form-item>
      </el-form>

      <el-form :inline="true" class="loop-form-row">
        <el-form-item label="面料需求/采购">
          <el-input-number v-model="draftForm.fabricDemandQty" :min="1" :max="99999" />
          <span class="inline-sep">/</span>
          <el-input-number v-model="draftForm.fabricPurchaseQty" :min="1" :max="99999" />
        </el-form-item>
        <el-form-item label="辅料需求/采购">
          <el-input-number v-model="draftForm.trimDemandQty" :min="1" :max="99999" />
          <span class="inline-sep">/</span>
          <el-input-number v-model="draftForm.trimPurchaseQty" :min="1" :max="99999" />
        </el-form-item>
        <el-form-item label="发料/回料">
          <el-input-number v-model="draftForm.issuedQty" :min="0" :max="99999" />
          <span class="inline-sep">/</span>
          <el-input-number v-model="draftForm.returnedQty" :min="0" :max="99999" />
        </el-form-item>
      </el-form>

      <el-form :inline="true" class="loop-form-row">
        <el-form-item label="验收/不良">
          <el-input-number v-model="draftForm.acceptedQty" :min="0" :max="99999" />
          <span class="inline-sep">/</span>
          <el-input-number v-model="draftForm.rejectedQty" :min="0" :max="99999" />
        </el-form-item>
        <el-form-item label="结算数量">
          <el-input-number v-model="draftForm.settlementQty" :min="0" :max="99999" />
        </el-form-item>
        <el-form-item label="预估金额">
          <el-input-number v-model="draftForm.estimatedAmount" :min="0" :max="99999999" />
        </el-form-item>
        <el-form-item label="结算状态">
          <el-input v-model="draftForm.settlementState" style="width: 140px" />
        </el-form-item>
      </el-form>

      <div class="local-write-actions">
        <el-button type="primary" :loading="localWriteLoading" @click="saveObject">
          {{ saveButtonLabel }}
        </el-button>
        <el-button :loading="localWriteLoading" :disabled="!currentDraftId" @click="updateSettlementPreview">
          更新结算预览
        </el-button>
        <el-button :loading="localWriteLoading" :disabled="!currentDraftId" @click="readbackObject">回读本地对象</el-button>
        <el-button :loading="localWriteLoading" :disabled="!currentDraftId" @click="rollbackScenario">回滚 scenario</el-button>
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
        <el-descriptions-item label="object_id">{{ currentDraftId || '-' }}</el-descriptions-item>
        <el-descriptions-item label="scenario_tag">{{ draftForm.scenarioTag }}</el-descriptions-item>
        <el-descriptions-item label="create_success">{{ loopState.createSuccess ? 'true' : 'false' }}</el-descriptions-item>
        <el-descriptions-item label="update_success">{{ loopState.updateSuccess ? 'true' : 'false' }}</el-descriptions-item>
        <el-descriptions-item label="readback_success">{{ loopState.readbackSuccess ? 'true' : 'false' }}</el-descriptions-item>
        <el-descriptions-item label="rollback_success">{{ loopState.rollbackSuccess ? 'true' : 'false' }}</el-descriptions-item>
        <el-descriptions-item label="zero_residual_success">{{ loopState.zeroResidualSuccess ? 'true' : 'false' }}</el-descriptions-item>
        <el-descriptions-item label="residual_records">{{ loopState.residualRecords }}</el-descriptions-item>
        <el-descriptions-item label="settlement_preview_created_or_updated">
          {{ loopState.settlementPreviewCreatedOrUpdated ? 'true' : 'false' }}
        </el-descriptions-item>
        <el-descriptions-item label="settlement_preview_readback_success">
          {{ loopState.settlementPreviewReadbackSuccess ? 'true' : 'false' }}
        </el-descriptions-item>
        <el-descriptions-item label="settlement_preview_status_observed">
          {{ loopState.settlementPreviewStatusObserved ? 'true' : 'false' }}
        </el-descriptions-item>
        <el-descriptions-item label="settlement_preview_amount_or_summary_observed">
          {{ loopState.settlementPreviewAmountOrSummaryObserved ? 'true' : 'false' }}
        </el-descriptions-item>
      </el-descriptions>

      <el-descriptions v-if="readbackState" border :column="2" class="readback-descriptions">
        <el-descriptions-item label="subcontract_or_purchase_readback_success">
          {{ readbackState.readback_flags.subcontract_or_purchase_readback_success ? 'true' : 'false' }}
        </el-descriptions-item>
        <el-descriptions-item label="material_line_readback_success">
          {{ readbackState.readback_flags.material_line_readback_success ? 'true' : 'false' }}
        </el-descriptions-item>
        <el-descriptions-item label="issue_return_or_inspection_readback_success">
          {{ readbackState.readback_flags.issue_return_or_inspection_readback_success ? 'true' : 'false' }}
        </el-descriptions-item>
        <el-descriptions-item label="settlement_preview_readback_success">
          {{ readbackState.readback_flags.settlement_preview_readback_success ? 'true' : 'false' }}
        </el-descriptions-item>
        <el-descriptions-item label="settlement_preview_status_observed">
          {{ readbackState.readback_flags.settlement_preview_status_observed ? 'true' : 'false' }}
        </el-descriptions-item>
        <el-descriptions-item label="settlement_preview_amount_or_summary_observed">
          {{ readbackState.readback_flags.settlement_preview_amount_or_summary_observed ? 'true' : 'false' }}
        </el-descriptions-item>
        <el-descriptions-item label="settlement_preview_real_finance_effect">
          {{ readbackState.readback_flags.settlement_preview_real_finance_effect ? 'true' : 'false' }}
        </el-descriptions-item>
        <el-descriptions-item label="settlement_preview_real_payment_effect">
          {{ readbackState.readback_flags.settlement_preview_real_payment_effect ? 'true' : 'false' }}
        </el-descriptions-item>
        <el-descriptions-item label="settlement_preview_real_inventory_effect">
          {{ readbackState.readback_flags.settlement_preview_real_inventory_effect ? 'true' : 'false' }}
        </el-descriptions-item>
        <el-descriptions-item label="scenario_tag_present">
          {{ readbackState.readback_flags.scenario_tag_present ? 'true' : 'false' }}
        </el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { request } from '@/api/request'

interface MaterialLine {
  material_code: string
  material_name: string
  color_spec: string
  uom: string
  demand_qty: number
  purchase_qty: number
}

interface IssueReturnState {
  issued_qty: number
  returned_qty: number
  delta_qty: number
  state: string
}

interface InspectionSettlementState {
  accepted_qty: number
  rejected_qty: number
  settlement_qty: number
  estimated_amount: number
  state: string
}

interface PurchaseDraftItem {
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
  material_lines: MaterialLine[]
  issue_return: IssueReturnState
  inspection_settlement: InspectionSettlementState
}

interface ListData {
  items: PurchaseDraftItem[]
  total: number
  page: number
  page_size: number
  parity: string
}

interface ReadbackFlags {
  scenario_tag_present: boolean
  subcontract_or_purchase_readback_success: boolean
  material_line_readback_success: boolean
  issue_return_or_inspection_readback_success: boolean
  settlement_preview_readback_success: boolean
  settlement_preview_status_observed: boolean
  settlement_preview_amount_or_summary_observed: boolean
  settlement_preview_real_finance_effect: boolean
  settlement_preview_real_payment_effect: boolean
  settlement_preview_real_inventory_effect: boolean
}

interface ReadbackData {
  object_id: number
  draft_id: number
  scenario_tag: string
  material_lines: MaterialLine[]
  issue_return: IssueReturnState
  inspection_settlement: InspectionSettlementState
  settlement_preview: InspectionSettlementState
  readback_flags: ReadbackFlags
}

interface ResidualCountData {
  scenario_tag: string
  total: number
}

interface RollbackData {
  scenario_tag: string
  object_id: number
  deleted_count: number
  residual_records_after_rollback: number
  rollback_success: boolean
  zero_residual_success: boolean
}

const SUBCONTRACT_ENDPOINT = '/api/local-dev/subcontract/orders'
const PURCHASE_ENDPOINT = '/api/local-dev/purchase-subcontract-drafts'

const route = useRoute()
const router = useRouter()

const rows = ref<PurchaseDraftItem[]>([])
const total = ref(0)
const loading = ref(false)
const feedback = ref('')
const localWriteLoading = ref(false)
const localWriteFeedback = ref('')
const currentDraftId = ref<number | null>(null)
const readbackState = ref<ReadbackData | null>(null)

const query = reactive({
  keyword: '',
  partnerName: '',
  status: '',
  materialCategory: '',
  page: 1,
  page_size: 20,
})

const buildDatePart = (): string => {
  const now = new Date()
  const yyyy = now.getFullYear()
  const mm = String(now.getMonth() + 1).padStart(2, '0')
  const dd = String(now.getDate()).padStart(2, '0')
  return `${yyyy}${mm}${dd}`
}
const buildDefaultScenarioTag = (): string => `REALOBJ-CAND004-B027-${buildDatePart()}-001`
const normalizeScenarioTag = (value: string): string => value.trim() || buildDefaultScenarioTag()

const draftForm = reactive({
  scenarioTag: buildDefaultScenarioTag(),
  documentNo: 'SUB-YS-260601',
  partnerName: '本地演示供应商',
  partnerType: 'supplier',
  documentType: 'purchase',
  businessDate: new Date().toISOString().slice(0, 10),
  status: 'draft',
  materialCategory: 'mixed',
  predecessorDocNo: 'materialPurchase/materialPurchaseProcess',
  note: 'REALOBJ-CAND-004 local loop test data',
  fabricDemandQty: 120,
  fabricPurchaseQty: 90,
  trimDemandQty: 500,
  trimPurchaseQty: 420,
  issuedQty: 90,
  returnedQty: 30,
  acceptedQty: 56,
  rejectedQty: 3,
  settlementQty: 56,
  estimatedAmount: 6800,
  settlementState: 'previewed',
})

const loopState = reactive({
  createSuccess: false,
  updateSuccess: false,
  readbackSuccess: false,
  rollbackSuccess: false,
  zeroResidualSuccess: false,
  residualRecords: -1,
  settlementPreviewCreatedOrUpdated: false,
  settlementPreviewReadbackSuccess: false,
  settlementPreviewStatusObserved: false,
  settlementPreviewAmountOrSummaryObserved: false,
})

const parityToken = computed(() => {
  const raw = route.query.parity
  if (Array.isArray(raw)) return String(raw[0] || '').trim()
  return String(raw || '').trim()
})
const isMaterialPurchaseParity = computed(() => parityToken.value === 'material-purchase')
const saveButtonLabel = computed(() => (currentDraftId.value ? '更新本地对象' : '保存本地对象'))

const buildListQuery = (): string => {
  const params = new URLSearchParams()
  if (query.keyword.trim()) params.set('keyword', query.keyword.trim())
  if (query.partnerName.trim()) params.set('partner_name', query.partnerName.trim())
  if (query.status.trim()) params.set('status', query.status.trim())
  if (query.materialCategory.trim()) params.set('material_category', query.materialCategory.trim())
  if (parityToken.value) params.set('parity', parityToken.value)
  params.set('page', String(query.page))
  params.set('page_size', String(query.page_size))
  return params.toString()
}

const buildObjectPayload = (): Record<string, unknown> => {
  const scenarioTag = normalizeScenarioTag(draftForm.scenarioTag)
  draftForm.scenarioTag = scenarioTag
  return {
    draft_id: currentDraftId.value ?? undefined,
    scenario_tag: scenarioTag,
    document_no: draftForm.documentNo.trim(),
    partner_name: draftForm.partnerName.trim(),
    partner_type: draftForm.partnerType,
    document_type: draftForm.documentType,
    business_date: draftForm.businessDate,
    status: draftForm.status,
    material_category: draftForm.materialCategory,
    predecessor_doc_no: draftForm.predecessorDocNo,
    note: draftForm.note.trim(),
    material_lines: [
      {
        material_code: 'FABRIC-COTTON-WHITE',
        material_name: '棉布(米白)',
        color_spec: '米白/M',
        uom: '米',
        demand_qty: Number(draftForm.fabricDemandQty),
        purchase_qty: Number(draftForm.fabricPurchaseQty),
      },
      {
        material_code: 'TRIM-BUTTON-20L',
        material_name: '纽扣(20L)',
        color_spec: '黑色',
        uom: '粒',
        demand_qty: Number(draftForm.trimDemandQty),
        purchase_qty: Number(draftForm.trimPurchaseQty),
      },
    ],
    issue_return: {
      issued_qty: Number(draftForm.issuedQty),
      returned_qty: Number(draftForm.returnedQty),
      state: 'saved',
    },
    inspection_settlement: {
      accepted_qty: Number(draftForm.acceptedQty),
      rejected_qty: Number(draftForm.rejectedQty),
      settlement_qty: Number(draftForm.settlementQty),
      estimated_amount: Number(draftForm.estimatedAmount),
      state: draftForm.settlementState.trim() || 'previewed',
    },
  }
}

const loadRows = async (): Promise<void> => {
  loading.value = true
  feedback.value = ''
  try {
    const queryString = buildListQuery()
    const response = await request<ListData>(`${SUBCONTRACT_ENDPOINT}?${queryString}`)
    rows.value = response.data.items || []
    total.value = Number(response.data.total || 0)
    if (isMaterialPurchaseParity.value) {
      feedback.value = 'materialPurchase parity 已命中（test_data only）'
    }
  } catch (error) {
    rows.value = []
    total.value = 0
    feedback.value = (error as Error).message || '列表加载失败'
  } finally {
    loading.value = false
  }
}

const applyQuery = (): void => {
  query.page = 1
  void loadRows()
}

const resetQuery = (): void => {
  query.keyword = ''
  query.partnerName = ''
  query.status = ''
  query.materialCategory = ''
  query.page = 1
  query.page_size = 20
  void loadRows()
}

const loadRowToLoop = (row: PurchaseDraftItem): void => {
  currentDraftId.value = row.draft_id
  draftForm.scenarioTag = row.scenario_tag
  draftForm.documentNo = row.document_no
  draftForm.partnerName = row.partner_name
  draftForm.partnerType = row.partner_type
  draftForm.documentType = row.document_type
  draftForm.businessDate = row.business_date
  draftForm.status = row.status
  draftForm.materialCategory = row.material_category
  draftForm.predecessorDocNo = row.predecessor_doc_no
  draftForm.note = row.note
  if (row.material_lines[0]) {
    draftForm.fabricDemandQty = Number(row.material_lines[0].demand_qty || 0)
    draftForm.fabricPurchaseQty = Number(row.material_lines[0].purchase_qty || 0)
  }
  if (row.material_lines[1]) {
    draftForm.trimDemandQty = Number(row.material_lines[1].demand_qty || 0)
    draftForm.trimPurchaseQty = Number(row.material_lines[1].purchase_qty || 0)
  }
  draftForm.issuedQty = Number(row.issue_return.issued_qty || 0)
  draftForm.returnedQty = Number(row.issue_return.returned_qty || 0)
  draftForm.acceptedQty = Number(row.inspection_settlement.accepted_qty || 0)
  draftForm.rejectedQty = Number(row.inspection_settlement.rejected_qty || 0)
  draftForm.settlementQty = Number(row.inspection_settlement.settlement_qty || 0)
  draftForm.estimatedAmount = Number(row.inspection_settlement.estimated_amount || 0)
  draftForm.settlementState = row.inspection_settlement.state || 'previewed'
}

const openDetail = (draftId: number): void => {
  router.push({
    path: '/subcontract/detail',
    query: {
      id: String(draftId),
      parity: parityToken.value || undefined,
      scenario_tag: normalizeScenarioTag(draftForm.scenarioTag),
    },
  })
}

const saveObject = async (): Promise<void> => {
  localWriteLoading.value = true
  try {
    const hadObject = Boolean(currentDraftId.value)
    const payload = buildObjectPayload()
    const endpoint = hadObject && currentDraftId.value
      ? `${SUBCONTRACT_ENDPOINT}/${currentDraftId.value}`
      : SUBCONTRACT_ENDPOINT
    const method = hadObject ? 'PATCH' : 'POST'
    const response = await request<PurchaseDraftItem>(endpoint, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    const objectId = Number(response.data.draft_id || 0)
    currentDraftId.value = objectId > 0 ? objectId : null
    if (hadObject) {
      loopState.updateSuccess = true
      localWriteFeedback.value = `update_success=true, object_id=${currentDraftId.value}`
      ElMessage.success('本地对象更新成功')
    } else {
      loopState.createSuccess = true
      localWriteFeedback.value = `create_success=true, object_id=${currentDraftId.value}`
      ElMessage.success('本地对象创建成功')
    }
    await loadRows()
  } catch (error) {
    localWriteFeedback.value = `save failed: ${(error as Error).message}`
    ElMessage.error((error as Error).message || '保存失败')
  } finally {
    localWriteLoading.value = false
  }
}

const updateSettlementPreview = async (): Promise<void> => {
  if (!currentDraftId.value) {
    ElMessage.warning('请先保存本地对象')
    return
  }
  localWriteLoading.value = true
  try {
    const scenarioTag = normalizeScenarioTag(draftForm.scenarioTag)
    const response = await request<{ settlement_preview: InspectionSettlementState }>(
      `${SUBCONTRACT_ENDPOINT}/${currentDraftId.value}/settlement-preview`,
      {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          scenario_tag: scenarioTag,
          accepted_qty: Number(draftForm.acceptedQty),
          rejected_qty: Number(draftForm.rejectedQty),
          settlement_qty: Number(draftForm.settlementQty),
          estimated_amount: Number(draftForm.estimatedAmount),
          state: draftForm.settlementState.trim() || 'previewed',
        }),
      },
    )
    const settlement = response.data.settlement_preview
    loopState.updateSuccess = true
    loopState.settlementPreviewCreatedOrUpdated = true
    loopState.settlementPreviewReadbackSuccess = true
    loopState.settlementPreviewStatusObserved = String(settlement.state || '').trim().length > 0
    loopState.settlementPreviewAmountOrSummaryObserved = (
      Number(settlement.estimated_amount || 0) > 0
      || Number(settlement.settlement_qty || 0) > 0
      || Number(settlement.accepted_qty || 0) > 0
      || Number(settlement.rejected_qty || 0) > 0
    )
    localWriteFeedback.value = `settlement_preview_updated=true, object_id=${currentDraftId.value}`
    ElMessage.success('结算预览更新成功')
  } catch (error) {
    localWriteFeedback.value = `settlement_preview update failed: ${(error as Error).message}`
    ElMessage.error((error as Error).message || '结算预览更新失败')
  } finally {
    localWriteLoading.value = false
  }
}

const readbackObject = async (): Promise<void> => {
  if (!currentDraftId.value) {
    ElMessage.warning('请先保存本地对象')
    return
  }
  localWriteLoading.value = true
  try {
    const scenarioTag = normalizeScenarioTag(draftForm.scenarioTag)
    const response = await request<ReadbackData>(
      `${SUBCONTRACT_ENDPOINT}/${currentDraftId.value}/readback?scenario_tag=${encodeURIComponent(scenarioTag)}`,
    )
    readbackState.value = response.data
    loopState.readbackSuccess = true
    loopState.settlementPreviewReadbackSuccess = response.data.readback_flags.settlement_preview_readback_success
    loopState.settlementPreviewStatusObserved = response.data.readback_flags.settlement_preview_status_observed
    loopState.settlementPreviewAmountOrSummaryObserved = response.data.readback_flags.settlement_preview_amount_or_summary_observed
    localWriteFeedback.value = `readback_success=true, object_id=${currentDraftId.value}`
    ElMessage.success('本地回读成功')
  } catch (error) {
    localWriteFeedback.value = `readback failed: ${(error as Error).message}`
    ElMessage.error((error as Error).message || '回读失败')
  } finally {
    localWriteLoading.value = false
  }
}

const rollbackScenario = async (): Promise<void> => {
  if (!currentDraftId.value) {
    ElMessage.warning('缺少对象ID，请先保存本地对象')
    return
  }
  localWriteLoading.value = true
  try {
    const scenarioTag = normalizeScenarioTag(draftForm.scenarioTag)
    const response = await request<RollbackData>(`${SUBCONTRACT_ENDPOINT}/${currentDraftId.value}/rollback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scenario_tag: scenarioTag }),
    })
    loopState.rollbackSuccess = Boolean(response.data.rollback_success)
    loopState.zeroResidualSuccess = Boolean(response.data.zero_residual_success)
    loopState.residualRecords = Number(response.data.residual_records_after_rollback || -1)
    localWriteFeedback.value = `rollback_success=${response.data.rollback_success}, zero_residual_success=${response.data.zero_residual_success}, residual=${response.data.residual_records_after_rollback}`
    await loadRows()
    ElMessage.success('scenario 回滚完成')
  } catch (error) {
    localWriteFeedback.value = `rollback failed: ${(error as Error).message}`
    ElMessage.error((error as Error).message || '回滚失败')
  } finally {
    localWriteLoading.value = false
  }
}

const checkZeroResidual = async (): Promise<void> => {
  localWriteLoading.value = true
  try {
    const scenarioTag = normalizeScenarioTag(draftForm.scenarioTag)
    const response = await request<ResidualCountData>(
      `${PURCHASE_ENDPOINT}/residual-count?scenario_tag=${encodeURIComponent(scenarioTag)}`,
    )
    const residual = Number(response.data.total || 0)
    loopState.residualRecords = residual
    loopState.zeroResidualSuccess = residual === 0
    localWriteFeedback.value = `zero_residual_check: scenario_tag=${scenarioTag}, residual=${residual}`
    if (residual === 0) {
      ElMessage.success('zero_residual 校验通过')
    } else {
      ElMessage.warning(`zero_residual 未通过，残留 ${residual} 条`)
    }
  } catch (error) {
    localWriteFeedback.value = `zero_residual check failed: ${(error as Error).message}`
    ElMessage.error((error as Error).message || 'zero_residual 校验失败')
  } finally {
    localWriteLoading.value = false
  }
}

const tagType = (status: string): 'success' | 'warning' | 'info' => {
  if (status === 'saved') return 'success'
  if (status === 'cancelled') return 'warning'
  return 'info'
}

onMounted(() => {
  if (isMaterialPurchaseParity.value) {
    draftForm.documentType = 'purchase'
    draftForm.predecessorDocNo = 'materialPurchase/materialPurchaseProcess'
  }
  void loadRows()
})
</script>

<style scoped>
.purchase-list-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
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

.header-actions {
  display: flex;
  gap: 8px;
}

.parity-alert {
  margin-top: 8px;
}

.feedback {
  margin-bottom: 10px;
}

.row-actions {
  display: inline-flex;
  gap: 8px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
}

.loop-form-row {
  margin-top: 4px;
}

.inline-sep {
  margin: 0 8px;
  color: var(--el-text-color-secondary);
}

.local-write-actions {
  margin-top: 10px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.feedback-alert {
  margin-top: 10px;
}

.readback-descriptions {
  margin-top: 10px;
}
</style>
