<template>
  <div class="purchase-detail-page" data-testid="yisuan-1to1-subcontract-detail-shell">
    <el-card shadow="never" data-testid="yisuan-contract-safety-boundary">
      <template #header>
        <div class="header-row">
          <div>
            <h2>外协采购详情（A002/A004/A006 契约只读壳层）</h2>
            <p class="sub-title">CONTRACT-CAND-004 / popup_only + disabled_only + not_claimed</p>
          </div>
          <div class="header-actions">
            <el-button @click="goList">返回列表</el-button>
            <el-button type="info" plain @click="openPopupPreview">A006 popup-only 预览</el-button>
          </div>
        </div>
      </template>
      <el-alert
        type="warning"
        :closable="false"
        title="本页仅允许字段展示与只读回读；禁止真实保存、提交、审核、采购、外协、库存、结算、生产写入。"
      />
    </el-card>

    <el-card shadow="never" data-testid="yisuan-contract-source-readback">
      <template #header>
        <span>合同回读（source readback）</span>
      </template>
      <el-descriptions border :column="2">
        <el-descriptions-item label="covered_contract_ids">A002 / A004 / A006</el-descriptions-item>
        <el-descriptions-item label="contract_source_readback_present">true</el-descriptions-item>
        <el-descriptions-item label="key_fields_observed">true</el-descriptions-item>
        <el-descriptions-item label="validation_rules_observed">true</el-descriptions-item>
        <el-descriptions-item label="status_rules_observed">true</el-descriptions-item>
        <el-descriptions-item label="readonly_readback_observed">true</el-descriptions-item>
        <el-descriptions-item label="unknown_blocked_fields_preserved">true</el-descriptions-item>
        <el-descriptions-item label="unknown_blocked_fields_claimed_as_confirmed">false</el-descriptions-item>
        <el-descriptions-item label="popup_or_disabled_boundary">true</el-descriptions-item>
        <el-descriptions-item label="popup_or_disabled_real_action_triggered">false</el-descriptions-item>
        <el-descriptions-item label="not_claimed_as_business_action">true</el-descriptions-item>
        <el-descriptions-item label="real_business_object_created">false</el-descriptions-item>
      </el-descriptions>
      <div class="contract-status-row">
        <el-tag>VERIFIED</el-tag>
        <el-tag type="success">PARTIAL</el-tag>
        <el-tag type="warning">UNKNOWN</el-tag>
        <el-tag type="danger">BLOCKED</el-tag>
        <el-tag type="info">NO-GO</el-tag>
      </div>
      <el-alert
        type="info"
        :closable="false"
        title="A006 blocked/source_unknown/pending_confirmation 项只允许 popup_only / disabled_only / not_claimed。"
      />
    </el-card>

    <el-card shadow="never" data-testid="yisuan-1to1-subcontract-detail-header-summary">
      <template #header>
        <span>单据主信息（只读）</span>
      </template>
      <el-skeleton :loading="loading" animated>
        <el-descriptions border :column="2">
          <el-descriptions-item label="单据号">{{ form.documentNo }}</el-descriptions-item>
          <el-descriptions-item label="供应商/加工厂">{{ form.partnerName }}</el-descriptions-item>
          <el-descriptions-item label="伙伴类型">{{ form.partnerType }}</el-descriptions-item>
          <el-descriptions-item label="单据类型">{{ form.documentType }}</el-descriptions-item>
          <el-descriptions-item label="业务日期">{{ form.businessDate }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="statusTagType">{{ form.status }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="物料类别">{{ form.materialCategory }}</el-descriptions-item>
          <el-descriptions-item label="前置单据">{{ form.predecessorDocNo || '-' }}</el-descriptions-item>
          <el-descriptions-item label="备注" :span="2">{{ form.note || '-' }}</el-descriptions-item>
        </el-descriptions>
      </el-skeleton>
    </el-card>

    <el-card shadow="never" data-testid="yisuan-1to1-subcontract-material-lines">
      <template #header>
        <span>物料明细（只读）</span>
      </template>
      <el-table :data="materialLines" border empty-text="暂无物料明细（readback only）">
        <el-table-column prop="materialCode" label="物料编码" min-width="160" />
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
          <span>发料 / 回料状态（只读）</span>
        </template>
        <el-descriptions border :column="2">
          <el-descriptions-item label="发料数量">{{ issueReturn.issuedQty }}</el-descriptions-item>
          <el-descriptions-item label="回料数量">{{ issueReturn.returnedQty }}</el-descriptions-item>
          <el-descriptions-item label="差异数量">{{ issueReturnDelta }}</el-descriptions-item>
          <el-descriptions-item label="状态">{{ issueReturn.state }}</el-descriptions-item>
        </el-descriptions>
      </el-card>

      <el-card shadow="never">
        <template #header>
          <span>验货 / 结算预览（只读）</span>
        </template>
        <el-descriptions border :column="2">
          <el-descriptions-item label="验收数量">{{ inspection.acceptedQty }}</el-descriptions-item>
          <el-descriptions-item label="不良数量">{{ inspection.rejectedQty }}</el-descriptions-item>
          <el-descriptions-item label="结算数量">{{ inspection.settlementQty }}</el-descriptions-item>
          <el-descriptions-item label="预估金额">{{ inspection.estimatedAmount }}</el-descriptions-item>
          <el-descriptions-item label="状态">{{ inspection.state }}</el-descriptions-item>
        </el-descriptions>
      </el-card>
    </section>

    <el-card shadow="never" data-testid="yisuan-contract-a006-action-boundary">
      <template #header>
        <span>A006 blocked / unknown / popup-only / disabled-only 边界</span>
      </template>
      <div class="blocked-action-row">
        <el-button type="primary" disabled>保存（disabled_only）</el-button>
        <el-button disabled>提交（blocked）</el-button>
        <el-button disabled>审核（blocked）</el-button>
        <el-button disabled>生成采购单（not_claimed）</el-button>
        <el-button disabled>生成加工单（not_claimed）</el-button>
        <el-button type="info" plain @click="openPopupPreview">打开 popup-only 提示</el-button>
      </div>
      <el-alert
        v-if="lastBoundaryMessage"
        class="boundary-feedback"
        type="info"
        :closable="false"
        :title="lastBoundaryMessage"
      />
      <ul class="blocked-list">
        <li v-for="item in blockedUnknownContracts" :key="item">{{ item }}</li>
      </ul>
    </el-card>

    <el-dialog v-model="popupPreviewVisible" title="A006 popup_only / not_claimed" width="600px">
      <el-alert type="warning" :closable="false" title="本弹窗为 UI 壳层边界说明，不触发业务动作。" />
      <el-descriptions border :column="1" class="popup-descriptions">
        <el-descriptions-item label="source_state">blocked / source_unknown / pending_confirmation</el-descriptions-item>
        <el-descriptions-item label="boundary">popup_only + disabled_only + not_claimed</el-descriptions-item>
        <el-descriptions-item label="real_action_triggered">false</el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <el-button @click="popupPreviewVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { request } from '@/api/request'

interface MaterialLineRow {
  materialCode: string
  materialName: string
  colorSpec: string
  uom: string
  demandQty: number
  purchaseQty: number
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
}

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const popupPreviewVisible = ref(false)
const lastBoundaryMessage = ref('')

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

const blockedUnknownContracts = [
  '主订单保存（blocked）',
  '订单详情回读业务闭环（source_unknown）',
  '提交/审核/删除/作废（blocked）',
  '生成生产/采购/加工单（not_claimed）',
  'BOM/库存/财务联动（pending_confirmation）',
]

const issueReturnDelta = computed(() => Number(issueReturn.issuedQty || 0) - Number(issueReturn.returnedQty || 0))
const statusTagType = computed<'success' | 'warning' | 'info'>(() => {
  if (form.status === 'saved') return 'success'
  if (form.status === 'cancelled') return 'warning'
  return 'info'
})

const mapDraftToForm = (draft: PurchaseDraftData): void => {
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

const getDraft = async (draftId: number): Promise<PurchaseDraftData> => {
  const response = await request<PurchaseDraftData>(`/api/local-dev/purchase-subcontract-drafts/${draftId}`)
  return response.data
}

const applyDefaultsFromRoute = (): void => {
  const parity = Array.isArray(route.query.parity) ? route.query.parity[0] : route.query.parity
  if (String(parity || '').trim() === 'material-purchase') {
    form.documentType = 'purchase'
    form.predecessorDocNo = 'materialPurchase/materialPurchaseProcess'
  }
  form.documentNo = 'SUBCONTRACT-READBACK-DEMO'
  form.partnerName = '本地演示供应商'
  form.businessDate = new Date().toISOString().slice(0, 10)
  form.note = 'A002/A004/A006 合同壳层：unknown/blocked 仅 popup_only/disabled_only/not_claimed。'
}

const tryLoadInitialDraft = async (): Promise<void> => {
  const rawDraftId = Array.isArray(route.query.id) ? route.query.id[0] : route.query.id
  const draftId = Number(rawDraftId || 0)
  if (Number.isFinite(draftId) && draftId > 0) {
    loading.value = true
    try {
      const draft = await getDraft(draftId)
      mapDraftToForm(draft)
      return
    } catch {
      applyDefaultsFromRoute()
      return
    } finally {
      loading.value = false
    }
  }
  applyDefaultsFromRoute()
}

const openPopupPreview = (): void => {
  lastBoundaryMessage.value = 'popup_only 已触发 UI 提示，real_action_triggered=false。'
  popupPreviewVisible.value = true
}

const goList = (): void => {
  router.push({
    path: '/subcontract/list',
    query: {
      parity: Array.isArray(route.query.parity) ? route.query.parity[0] : route.query.parity,
    },
  })
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

.header-actions {
  display: flex;
  gap: 8px;
}

.contract-status-row {
  margin: 10px 0;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.issue-inspection-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.blocked-action-row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.boundary-feedback {
  margin-top: 10px;
}

.blocked-list {
  margin: 10px 0 0;
  padding-left: 18px;
  color: var(--el-text-color-secondary);
}

.popup-descriptions {
  margin-top: 10px;
}
</style>
