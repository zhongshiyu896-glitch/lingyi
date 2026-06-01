<template>
  <div class="purchase-detail-page" data-testid="yisuan-1to1-subcontract-detail-shell">
    <el-card shadow="never">
      <template #header>
        <div class="header-row">
          <div>
            <h2>外协/采购详情（本地回读）</h2>
            <p class="sub-title">REALOBJ-CAND-004 / local-dev readback only</p>
          </div>
          <div class="header-actions">
            <el-button @click="goList">返回列表</el-button>
            <el-button type="primary" plain :loading="loading" @click="refreshReadback">刷新本地回读</el-button>
          </div>
        </div>
      </template>
      <el-alert
        type="warning"
        :closable="false"
        title="本页仅展示 local-dev 回读，不触发真实采购/外协/库存/财务结算动作。"
      />
    </el-card>

    <el-card shadow="never" data-testid="yisuan-1to1-subcontract-detail-header-summary">
      <template #header>
        <span>单据主信息（readback）</span>
      </template>
      <el-descriptions border :column="2">
        <el-descriptions-item label="object_id">{{ state.objectId || '-' }}</el-descriptions-item>
        <el-descriptions-item label="scenario_tag">{{ state.scenarioTag || '-' }}</el-descriptions-item>
        <el-descriptions-item label="单据号">{{ state.documentNo || '-' }}</el-descriptions-item>
        <el-descriptions-item label="伙伴">{{ state.partnerName || '-' }}</el-descriptions-item>
        <el-descriptions-item label="伙伴类型">{{ state.partnerType || '-' }}</el-descriptions-item>
        <el-descriptions-item label="单据类型">{{ state.documentType || '-' }}</el-descriptions-item>
        <el-descriptions-item label="业务日期">{{ state.businessDate || '-' }}</el-descriptions-item>
        <el-descriptions-item label="状态">{{ state.status || '-' }}</el-descriptions-item>
        <el-descriptions-item label="物料类别">{{ state.materialCategory || '-' }}</el-descriptions-item>
        <el-descriptions-item label="前置单据">{{ state.predecessorDocNo || '-' }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <el-card shadow="never" data-testid="yisuan-1to1-subcontract-material-lines">
      <template #header>
        <span>物料明细（readback）</span>
      </template>
      <el-table :data="materialLines" border empty-text="暂无物料明细">
        <el-table-column prop="materialCode" label="物料编码" min-width="170" />
        <el-table-column prop="materialName" label="物料名称" min-width="180" />
        <el-table-column prop="colorSpec" label="颜色/规格" min-width="150" />
        <el-table-column prop="uom" label="单位" width="90" />
        <el-table-column prop="demandQty" label="需求数量" width="130" />
        <el-table-column prop="purchaseQty" label="采购/外协数量" width="150" />
      </el-table>
    </el-card>

    <section class="issue-inspection-panel" data-testid="yisuan-1to1-subcontract-issue-return-inspection-panel">
      <el-card shadow="never">
        <template #header>
          <span>发料 / 回料状态（readback）</span>
        </template>
        <el-descriptions border :column="2">
          <el-descriptions-item label="发料">{{ issueReturn.issuedQty }}</el-descriptions-item>
          <el-descriptions-item label="回料">{{ issueReturn.returnedQty }}</el-descriptions-item>
          <el-descriptions-item label="差异">{{ issueReturn.deltaQty }}</el-descriptions-item>
          <el-descriptions-item label="状态">{{ issueReturn.state }}</el-descriptions-item>
        </el-descriptions>
      </el-card>

      <el-card shadow="never">
        <template #header>
          <span>结算预览（readback）</span>
        </template>
        <el-descriptions border :column="2">
          <el-descriptions-item label="验收">{{ settlementPreview.acceptedQty }}</el-descriptions-item>
          <el-descriptions-item label="不良">{{ settlementPreview.rejectedQty }}</el-descriptions-item>
          <el-descriptions-item label="结算数量">{{ settlementPreview.settlementQty }}</el-descriptions-item>
          <el-descriptions-item label="预估金额">{{ settlementPreview.estimatedAmount }}</el-descriptions-item>
          <el-descriptions-item label="状态">{{ settlementPreview.state }}</el-descriptions-item>
        </el-descriptions>
      </el-card>
    </section>

    <el-card shadow="never" data-testid="realobj-subcontract-readback-evidence">
      <template #header>
        <span>回读证据字段</span>
      </template>
      <el-descriptions border :column="2">
        <el-descriptions-item label="subcontract_or_purchase_readback_success">
          {{ flags.subcontractOrPurchaseReadbackSuccess ? 'true' : 'false' }}
        </el-descriptions-item>
        <el-descriptions-item label="material_line_readback_success">
          {{ flags.materialLineReadbackSuccess ? 'true' : 'false' }}
        </el-descriptions-item>
        <el-descriptions-item label="issue_return_or_inspection_readback_success">
          {{ flags.issueReturnOrInspectionReadbackSuccess ? 'true' : 'false' }}
        </el-descriptions-item>
        <el-descriptions-item label="settlement_preview_readback_success">
          {{ flags.settlementPreviewReadbackSuccess ? 'true' : 'false' }}
        </el-descriptions-item>
        <el-descriptions-item label="settlement_preview_status_observed">
          {{ flags.settlementPreviewStatusObserved ? 'true' : 'false' }}
        </el-descriptions-item>
        <el-descriptions-item label="settlement_preview_amount_or_summary_observed">
          {{ flags.settlementPreviewAmountOrSummaryObserved ? 'true' : 'false' }}
        </el-descriptions-item>
        <el-descriptions-item label="settlement_preview_real_finance_effect">
          {{ flags.settlementPreviewRealFinanceEffect ? 'true' : 'false' }}
        </el-descriptions-item>
        <el-descriptions-item label="settlement_preview_real_payment_effect">
          {{ flags.settlementPreviewRealPaymentEffect ? 'true' : 'false' }}
        </el-descriptions-item>
        <el-descriptions-item label="settlement_preview_real_inventory_effect">
          {{ flags.settlementPreviewRealInventoryEffect ? 'true' : 'false' }}
        </el-descriptions-item>
        <el-descriptions-item label="scenario_tag_present">
          {{ flags.scenarioTagPresent ? 'true' : 'false' }}
        </el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { request } from '@/api/request'

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

interface MaterialLine {
  material_code: string
  material_name: string
  color_spec: string
  uom: string
  demand_qty: number
  purchase_qty: number
}

interface ReadbackData {
  object_id: number
  draft_id: number
  scenario_tag: string
  subcontract_or_purchase: {
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
  }
  material_lines: MaterialLine[]
  issue_return: {
    issued_qty: number
    returned_qty: number
    delta_qty: number
    state: string
  }
  settlement_preview: {
    accepted_qty: number
    rejected_qty: number
    settlement_qty: number
    estimated_amount: number
    state: string
  }
  readback_flags: ReadbackFlags
}

const SUBCONTRACT_ENDPOINT = '/api/local-dev/subcontract/orders'

const route = useRoute()
const router = useRouter()
const loading = ref(false)

const state = reactive({
  objectId: 0,
  scenarioTag: '',
  documentNo: '',
  partnerName: '',
  partnerType: '',
  documentType: '',
  businessDate: '',
  status: '',
  materialCategory: '',
  predecessorDocNo: '',
})

const materialLines = ref<Array<{ materialCode: string; materialName: string; colorSpec: string; uom: string; demandQty: number; purchaseQty: number }>>([])

const issueReturn = reactive({
  issuedQty: 0,
  returnedQty: 0,
  deltaQty: 0,
  state: '',
})

const settlementPreview = reactive({
  acceptedQty: 0,
  rejectedQty: 0,
  settlementQty: 0,
  estimatedAmount: 0,
  state: '',
})

const flags = reactive({
  scenarioTagPresent: false,
  subcontractOrPurchaseReadbackSuccess: false,
  materialLineReadbackSuccess: false,
  issueReturnOrInspectionReadbackSuccess: false,
  settlementPreviewReadbackSuccess: false,
  settlementPreviewStatusObserved: false,
  settlementPreviewAmountOrSummaryObserved: false,
  settlementPreviewRealFinanceEffect: false,
  settlementPreviewRealPaymentEffect: false,
  settlementPreviewRealInventoryEffect: false,
})

const normalizeScenarioTag = (): string => {
  const raw = Array.isArray(route.query.scenario_tag) ? route.query.scenario_tag[0] : route.query.scenario_tag
  return String(raw || '').trim()
}

const normalizeDraftId = (): number => {
  const raw = Array.isArray(route.query.id) ? route.query.id[0] : route.query.id
  return Number(raw || 0)
}

const applyReadback = (data: ReadbackData): void => {
  state.objectId = Number(data.object_id || data.draft_id || 0)
  state.scenarioTag = data.scenario_tag || ''
  state.documentNo = data.subcontract_or_purchase.document_no || ''
  state.partnerName = data.subcontract_or_purchase.partner_name || ''
  state.partnerType = data.subcontract_or_purchase.partner_type || ''
  state.documentType = data.subcontract_or_purchase.document_type || ''
  state.businessDate = data.subcontract_or_purchase.business_date || ''
  state.status = data.subcontract_or_purchase.status || ''
  state.materialCategory = data.subcontract_or_purchase.material_category || ''
  state.predecessorDocNo = data.subcontract_or_purchase.predecessor_doc_no || ''
  materialLines.value = (data.material_lines || []).map((item) => ({
    materialCode: item.material_code,
    materialName: item.material_name,
    colorSpec: item.color_spec,
    uom: item.uom,
    demandQty: Number(item.demand_qty || 0),
    purchaseQty: Number(item.purchase_qty || 0),
  }))
  issueReturn.issuedQty = Number(data.issue_return.issued_qty || 0)
  issueReturn.returnedQty = Number(data.issue_return.returned_qty || 0)
  issueReturn.deltaQty = Number(data.issue_return.delta_qty || 0)
  issueReturn.state = data.issue_return.state || ''
  settlementPreview.acceptedQty = Number(data.settlement_preview.accepted_qty || 0)
  settlementPreview.rejectedQty = Number(data.settlement_preview.rejected_qty || 0)
  settlementPreview.settlementQty = Number(data.settlement_preview.settlement_qty || 0)
  settlementPreview.estimatedAmount = Number(data.settlement_preview.estimated_amount || 0)
  settlementPreview.state = data.settlement_preview.state || ''
  flags.scenarioTagPresent = data.readback_flags.scenario_tag_present
  flags.subcontractOrPurchaseReadbackSuccess = data.readback_flags.subcontract_or_purchase_readback_success
  flags.materialLineReadbackSuccess = data.readback_flags.material_line_readback_success
  flags.issueReturnOrInspectionReadbackSuccess = data.readback_flags.issue_return_or_inspection_readback_success
  flags.settlementPreviewReadbackSuccess = data.readback_flags.settlement_preview_readback_success
  flags.settlementPreviewStatusObserved = data.readback_flags.settlement_preview_status_observed
  flags.settlementPreviewAmountOrSummaryObserved = data.readback_flags.settlement_preview_amount_or_summary_observed
  flags.settlementPreviewRealFinanceEffect = data.readback_flags.settlement_preview_real_finance_effect
  flags.settlementPreviewRealPaymentEffect = data.readback_flags.settlement_preview_real_payment_effect
  flags.settlementPreviewRealInventoryEffect = data.readback_flags.settlement_preview_real_inventory_effect
}

const refreshReadback = async (): Promise<void> => {
  const draftId = normalizeDraftId()
  const scenarioTag = normalizeScenarioTag()
  if (!draftId || !scenarioTag) {
    ElMessage.warning('缺少 id 或 scenario_tag，无法回读')
    return
  }
  loading.value = true
  try {
    const response = await request<ReadbackData>(
      `${SUBCONTRACT_ENDPOINT}/${draftId}/readback?scenario_tag=${encodeURIComponent(scenarioTag)}`,
    )
    applyReadback(response.data)
  } catch (error) {
    ElMessage.error((error as Error).message || '本地回读失败')
  } finally {
    loading.value = false
  }
}

const goList = (): void => {
  const parity = Array.isArray(route.query.parity) ? route.query.parity[0] : route.query.parity
  const scenarioTag = Array.isArray(route.query.scenario_tag) ? route.query.scenario_tag[0] : route.query.scenario_tag
  router.push({
    path: '/subcontract/list',
    query: {
      parity: parity || undefined,
      scenario_tag: scenarioTag || undefined,
    },
  })
}

onMounted(() => {
  void refreshReadback()
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

.header-actions {
  display: flex;
  gap: 8px;
}

.issue-inspection-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
</style>
