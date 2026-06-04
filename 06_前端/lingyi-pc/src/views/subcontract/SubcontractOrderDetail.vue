<template>
  <div class="subcontract-detail-page" data-testid="yisuan-1to1-subcontract-detail-shell">
    <el-card shadow="never">
      <template #header>
        <div class="header-row">
          <div>
            <h2>委外订单详情（本地可试用）</h2>
            <p class="sub-title">local-dev only / read-only usable slice / no receipt or inventory release</p>
          </div>
          <div class="header-actions">
            <el-button @click="goList">返回列表</el-button>
            <el-button type="primary" plain :loading="loading" @click="refreshDetail">刷新详情</el-button>
          </div>
        </div>
      </template>
      <el-alert
        type="warning"
        :closable="false"
        title="本页只展示 local-dev 详情，不触发收货、入库、结算 release、库存 outbox、worker push 或 ERPNext 生命周期。"
      />
      <el-alert
        v-if="isMaterialPurchaseParity"
        class="feedback"
        type="info"
        :closable="false"
        data-testid="realobj-subcontract-detail-parity-alert"
        title="materialPurchase final_path: /materialPurchase/materialPurchaseProcess -> /subcontract/detail?parity=material-purchase"
      />
      <el-alert v-if="feedback" class="feedback" type="info" :closable="false" :title="feedback" />
    </el-card>

    <el-card shadow="never" data-testid="yisuan-1to1-subcontract-detail-header-summary">
      <template #header>
        <span>订单基础信息</span>
      </template>
      <el-descriptions border :column="2">
        <el-descriptions-item label="单据号">{{ state.subcontractNo || '-' }}</el-descriptions-item>
        <el-descriptions-item label="供应商/加工厂">{{ state.supplier || '-' }}</el-descriptions-item>
        <el-descriptions-item label="公司">{{ state.company || '-' }}</el-descriptions-item>
        <el-descriptions-item label="物料编码">{{ state.itemCode || '-' }}</el-descriptions-item>
        <el-descriptions-item label="工序">{{ state.processName || '-' }}</el-descriptions-item>
        <el-descriptions-item label="BOM ID">{{ state.bomId || '-' }}</el-descriptions-item>
        <el-descriptions-item label="交期参考">{{ formatDateTime(state.createdAt) }}</el-descriptions-item>
        <el-descriptions-item label="最近更新时间">{{ formatDateTime(state.updatedAt) }}</el-descriptions-item>
        <el-descriptions-item label="计划数量">{{ formatNumber(state.plannedQty) }}</el-descriptions-item>
        <el-descriptions-item label="主款/工单">{{ state.salesOrder || '-' }} / {{ state.workOrder || '-' }}</el-descriptions-item>
      </el-descriptions>
      <div class="tag-stack detail-tags">
        <el-tag :type="statusType(state.status)">{{ statusLabel(state.status) }}</el-tag>
        <el-tag :type="resourceScopeType(state.resourceScopeStatus)" effect="plain">
          {{ resourceScopeLabel(state.resourceScopeStatus) }}
        </el-tag>
        <el-tag :type="profitScopeType(state.profitScopeStatus)" effect="plain">
          {{ profitScopeLabel(state.profitScopeStatus) }}
        </el-tag>
      </div>
    </el-card>

    <el-card shadow="never" data-testid="yisuan-1to1-subcontract-detail-guard-summary">
      <template #header>
        <div class="summary-header">
          <span>详情摘要与入库前置守卫</span>
          <div class="readonly-actions">
            <el-tooltip v-for="action in readonlyGuardActions" :key="action.label" :content="action.reason" placement="top">
              <span>
                <el-button disabled>{{ action.label }}</el-button>
              </span>
            </el-tooltip>
          </div>
        </div>
      </template>
      <el-descriptions border :column="3">
        <el-descriptions-item label="收料批次">{{ detailReadonlySummary.receiptBatchCount }}</el-descriptions-item>
        <el-descriptions-item label="验货记录">{{ detailReadonlySummary.inspectionCount }}</el-descriptions-item>
        <el-descriptions-item label="回料进度">{{ detailReadonlySummary.receiptProgressRatio }}</el-descriptions-item>
        <el-descriptions-item label="验收进度">{{ detailReadonlySummary.acceptanceProgressRatio }}</el-descriptions-item>
        <el-descriptions-item label="待收货">{{ formatNumber(detailReadonlySummary.remainingReceiptQty) }}</el-descriptions-item>
        <el-descriptions-item label="待验货">{{ formatNumber(detailReadonlySummary.remainingAcceptanceQty) }}</el-descriptions-item>
      </el-descriptions>
      <div class="guard-list">
        <div v-for="guard in guardStates" :key="guard.label" class="guard-item">
          <el-tag :type="guard.type">{{ guard.label }}</el-tag>
          <span>{{ guard.reason }}</span>
        </div>
      </div>
    </el-card>

    <SubcontractReceiptTimelineReadonly
      v-if="timelineState && timelineMilestones.length > 0"
      :milestones="timelineMilestones"
      :settlement-state="timelineState"
      :abnormal-nodes="abnormalNodes"
    />

    <SubcontractScopeBridgeReadonly
      v-if="scopeBridgeReadonly"
      :summary="scopeBridgeReadonly"
      :guard-states="scopeBridgeGuardStates"
      :final-path="finalPath"
      :parity-token="parityToken"
    />

    <el-card shadow="never" data-testid="yisuan-1to1-subcontract-material-lines">
      <template #header>
        <span>物料明细（只读）</span>
      </template>
      <el-table :data="materialLines" border empty-text="暂无物料明细">
        <el-table-column prop="materialCode" label="物料编码" min-width="160" />
        <el-table-column prop="materialName" label="物料名称" min-width="180" />
        <el-table-column prop="colorSpec" label="颜色/规格" min-width="180" />
        <el-table-column prop="uom" label="单位" width="90" />
        <el-table-column prop="demandQty" label="需求数量" width="120" />
        <el-table-column prop="purchaseQty" label="委外/回料数量" width="150" />
      </el-table>
    </el-card>

    <section class="issue-inspection-panel" data-testid="yisuan-1to1-subcontract-issue-return-inspection-panel">
      <el-card shadow="never">
        <template #header>
          <span>收料/验货/金额概览</span>
        </template>
        <el-descriptions border :column="2">
          <el-descriptions-item label="发料">{{ formatNumber(state.issuedQty) }}</el-descriptions-item>
          <el-descriptions-item label="回料">{{ formatNumber(state.receivedQty) }}</el-descriptions-item>
          <el-descriptions-item label="验收">{{ formatNumber(state.acceptedQty) }}</el-descriptions-item>
          <el-descriptions-item label="不良">{{ formatNumber(state.rejectedQty) }}</el-descriptions-item>
          <el-descriptions-item label="总额">{{ formatNumber(state.grossAmount, 2) }}</el-descriptions-item>
          <el-descriptions-item label="净额">{{ formatNumber(state.netAmount, 2) }}</el-descriptions-item>
        </el-descriptions>
      </el-card>

      <el-card shadow="never">
        <template #header>
          <span>收料批次</span>
        </template>
        <el-table :data="receipts" border empty-text="暂无收料记录">
          <el-table-column prop="receiptBatchNo" label="批次号" min-width="150" />
          <el-table-column prop="warehouse" label="回料仓" min-width="130" />
          <el-table-column prop="receivedQty" label="回料数量" width="120" />
          <el-table-column prop="syncStatus" label="同步状态" width="150" />
        </el-table>
      </el-card>

      <el-card shadow="never">
        <template #header>
          <span>验货结果</span>
        </template>
        <el-table :data="inspections" border empty-text="暂无验货记录">
          <el-table-column prop="inspectionNo" label="验货单号" min-width="160" />
          <el-table-column prop="inspectedQty" label="验货数量" width="120" />
          <el-table-column prop="acceptedQty" label="合格数量" width="120" />
          <el-table-column prop="rejectedQty" label="不良数量" width="120" />
          <el-table-column prop="netAmount" label="净额" width="120" />
        </el-table>
      </el-card>
    </section>

    <el-card shadow="never" data-testid="realobj-subcontract-readback-evidence">
      <template #header>
        <span>本地可试用证据字段</span>
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
        <el-descriptions-item label="receipt_guard_visible">
          {{ guardStates.length > 0 ? 'true' : 'false' }}
        </el-descriptions-item>
        <el-descriptions-item label="inventory_write_release">false</el-descriptions-item>
        <el-descriptions-item label="receipt_real_effect">false</el-descriptions-item>
        <el-descriptions-item label="worker_push">false</el-descriptions-item>
        <el-descriptions-item label="erpnext_production">false</el-descriptions-item>
        <el-descriptions-item label="fallback_snapshot_used">
          {{ fallbackSnapshotUsed ? 'true' : 'false' }}
        </el-descriptions-item>
        <el-descriptions-item label="readonly_actions_guarded">true</el-descriptions-item>
        <el-descriptions-item label="receipt_timeline_visible">
          {{ timelineMilestones.length > 0 ? 'true' : 'false' }}
        </el-descriptions-item>
        <el-descriptions-item label="settlement_readonly_state_visible">
          {{ timelineState ? 'true' : 'false' }}
        </el-descriptions-item>
        <el-descriptions-item label="abnormal_node_readback_visible">
          {{ abnormalNodes.length > 0 ? 'true' : 'false' }}
        </el-descriptions-item>
        <el-descriptions-item label="scope_bridge_visible">
          {{ scopeBridgeReadonly ? 'true' : 'false' }}
        </el-descriptions-item>
        <el-descriptions-item label="profit_scope_status_visible">
          {{ scopeBridgeReadonly?.profitScopeLabel ? 'true' : 'false' }}
        </el-descriptions-item>
        <el-descriptions-item label="material_detail_readonly_tags_visible">
          {{ scopeBridgeReadonly && scopeBridgeReadonly.materialTags.length > 0 ? 'true' : 'false' }}
        </el-descriptions-item>
        <el-descriptions-item label="readonly_guard_states_visible">
          {{ scopeBridgeGuardStates.length > 0 ? 'true' : 'false' }}
        </el-descriptions-item>
        <el-descriptions-item label="cand110_base_readback_retained">true</el-descriptions-item>
        <el-descriptions-item label="cand134_timeline_settlement_retained">
          {{ timelineMilestones.length > 0 && timelineState ? 'true' : 'false' }}
        </el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type {
  SubcontractInspectionDetailItem,
  SubcontractOrderDetailData,
  SubcontractOrderListItem,
  SubcontractReceiptDetailItem,
} from '@/api/subcontract'
import {
  fetchSubcontractOrderDetailReadback,
  resolveFallbackSubcontractOrderRow,
} from '@/api/subcontract_readback'
import SubcontractReceiptTimelineReadonly from './components/SubcontractReceiptTimelineReadonly.vue'
import SubcontractScopeBridgeReadonly from './components/SubcontractScopeBridgeReadonly.vue'
import { useSubcontractReadonly } from './composables/useSubcontractReadonly'

interface MaterialLineView {
  materialCode: string
  materialName: string
  colorSpec: string
  uom: string
  demandQty: string
  purchaseQty: string
}

interface ReceiptView {
  receiptBatchNo: string
  warehouse: string
  receivedQty: string
  syncStatus: string
}

interface InspectionView {
  inspectionNo: string
  inspectedQty: string
  acceptedQty: string
  rejectedQty: string
  netAmount: string
}

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const feedback = ref('')
const fallbackSnapshotUsed = ref(false)
const currentDetail = ref<SubcontractOrderDetailData | null>(null)

const {
  abnormalNodes: buildAbnormalNodes,
  buildReceiptPreconditionGuard,
  detailSummary,
  formatDateTime,
  formatNumber,
  profitScopeLabel,
  profitScopeType,
  readonlyGuardActions,
  resourceScopeLabel,
  resourceScopeType,
  scopeBridgeDetailSummary: buildScopeBridgeDetailSummary,
  scopeGuardStates: buildScopeGuardStates,
  settlementReadonlyState: buildSettlementReadonlyState,
  statusLabel,
  statusType,
  timelineMilestones: buildTimelineMilestones,
} = useSubcontractReadonly()

const parityToken = computed(() => {
  const raw = route.query.parity
  if (Array.isArray(raw)) return String(raw[0] || '').trim()
  return String(raw || '').trim()
})

const isMaterialPurchaseParity = computed(() => parityToken.value === 'material-purchase')

const finalPath = computed(() =>
  isMaterialPurchaseParity.value ? '/subcontract/detail?parity=material-purchase' : '/subcontract/detail',
)

const state = reactive({
  id: 0,
  subcontractNo: '',
  supplier: '',
  company: '',
  itemCode: '',
  bomId: 0,
  processName: '',
  plannedQty: '0',
  issuedQty: '0',
  receivedQty: '0',
  acceptedQty: '0',
  rejectedQty: '0',
  grossAmount: '0',
  netAmount: '0',
  status: '',
  settlementStatus: '',
  resourceScopeStatus: '',
  salesOrder: '',
  salesOrderItem: '',
  productionPlanId: '',
  workOrder: '',
  jobCard: '',
  profitScopeStatus: '',
  profitScopeErrorCode: '',
  createdAt: '',
  updatedAt: '',
})

const materialLines = ref<MaterialLineView[]>([])
const receipts = ref<ReceiptView[]>([])
const inspections = ref<InspectionView[]>([])

const flags = reactive({
  subcontractOrPurchaseReadbackSuccess: false,
  materialLineReadbackSuccess: false,
  issueReturnOrInspectionReadbackSuccess: false,
})

const detailReadonlySummary = computed(() =>
  currentDetail.value
    ? detailSummary(currentDetail.value)
    : {
        receiptBatchCount: 0,
        inspectionCount: 0,
        remainingReceiptQty: 0,
        remainingAcceptanceQty: 0,
        receiptProgressRatio: '0%',
        acceptanceProgressRatio: '0%',
      },
)

const guardStates = computed(() =>
  currentDetail.value ? buildReceiptPreconditionGuard(currentDetail.value) : [],
)

const timelineMilestones = computed(() =>
  currentDetail.value ? buildTimelineMilestones(currentDetail.value) : [],
)

const timelineState = computed(() =>
  currentDetail.value ? buildSettlementReadonlyState(currentDetail.value) : null,
)

const abnormalNodes = computed(() =>
  currentDetail.value ? buildAbnormalNodes(currentDetail.value) : [],
)

const scopeBridgeReadonly = computed(() =>
  currentDetail.value ? buildScopeBridgeDetailSummary(currentDetail.value, parityToken.value) : null,
)

const scopeBridgeGuardStates = computed(() => buildScopeGuardStates(scopeBridgeReadonly.value))

const normalizeOrderId = (): number => {
  const raw = route.query.id
  if (Array.isArray(raw)) return Number(raw[0] || 0)
  return Number(raw || 0)
}

const buildSyntheticListItem = (): SubcontractOrderListItem => ({
  id: 900601,
  subcontract_no: 'SC-LOCAL-USABLE-001',
  supplier: parityToken.value === 'material-purchase' ? '本地演示供应商' : '本地演示外协厂',
  item_code: 'ITEM-A',
  company: 'COMP-A',
  bom_id: 1,
  process_name: '外发裁剪',
  planned_qty: '120',
  subcontract_rate: '0.65',
  issued_qty: '90',
  received_qty: '56',
  inspected_qty: '56',
  rejected_qty: '3',
  accepted_qty: '53',
  gross_amount: '6800',
  deduction_amount: '180',
  net_amount: '6620',
  status: 'processing',
  resource_scope_status: 'ready',
  profit_scope_status: 'resolved',
  profit_scope_error_code: '',
  latest_issue_outbox_id: null,
  latest_issue_sync_status: null,
  latest_issue_stock_entry_name: null,
  latest_issue_idempotency_key: null,
  latest_issue_error_code: null,
  latest_receipt_outbox_id: null,
  latest_receipt_sync_status: null,
  latest_receipt_stock_entry_name: null,
  latest_receipt_idempotency_key: null,
  latest_receipt_error_code: null,
  sales_order: parityToken.value === 'material-purchase' ? 'SO-LOCAL-001' : 'SO-LOCAL-TRACE',
  sales_order_item: parityToken.value === 'material-purchase' ? 'SO-LOCAL-001-1' : 'SO-LOCAL-TRACE-1',
  production_plan_id: parityToken.value === 'material-purchase' ? 3001 : 3002,
  work_order: parityToken.value === 'material-purchase' ? 'WO-LOCAL-3001' : 'WO-LOCAL-3002',
  job_card: parityToken.value === 'material-purchase' ? 'JC-LOCAL-3001' : 'JC-LOCAL-3002',
  created_at: new Date().toISOString(),
})

const buildSyntheticDetail = (base?: Partial<SubcontractOrderListItem>): SubcontractOrderDetailData => ({
  id: Number(base?.id || 900601),
  subcontract_no: String(base?.subcontract_no || 'SC-LOCAL-USABLE-001'),
  supplier: String(base?.supplier || '本地演示外协厂'),
  item_code: String(base?.item_code || 'ITEM-A'),
  company: String(base?.company || 'COMP-A'),
  bom_id: Number(base?.bom_id || 1),
  process_name: String(base?.process_name || '外发裁剪'),
  planned_qty: String(base?.planned_qty || '120'),
  subcontract_rate: String(base?.subcontract_rate || '0.65'),
  issued_qty: String(base?.issued_qty || '90'),
  received_qty: String(base?.received_qty || '56'),
  inspected_qty: String(base?.inspected_qty || '56'),
  rejected_qty: String(base?.rejected_qty || '3'),
  accepted_qty: String(base?.accepted_qty || '53'),
  gross_amount: String(base?.gross_amount || '6800'),
  deduction_amount: String(base?.deduction_amount || '180'),
  net_amount: String(base?.net_amount || '6620'),
  status: String(base?.status || 'processing'),
  settlement_status: 'preview_only',
  resource_scope_status: String(base?.resource_scope_status || 'ready'),
  profit_scope_status: String(base?.profit_scope_status || 'resolved'),
  profit_scope_error_code: String(base?.profit_scope_error_code || ''),
  sales_order: String(base?.sales_order || 'SO-LOCAL-TRACE'),
  sales_order_item: String(base?.sales_order_item || 'SO-LOCAL-TRACE-1'),
  production_plan_id: Number(base?.production_plan_id || 3002) || null,
  work_order: String(base?.work_order || 'WO-LOCAL-3002'),
  job_card: String(base?.job_card || 'JC-LOCAL-3002'),
  scope_error_code: null,
  latest_issue_outbox_id: null,
  latest_issue_sync_status: null,
  latest_issue_stock_entry_name: null,
  latest_issue_idempotency_key: null,
  latest_receipt_outbox_id: null,
  latest_receipt_sync_status: null,
  latest_receipt_stock_entry_name: null,
  latest_receipt_idempotency_key: null,
  receipts: [
    {
      receipt_batch_no: 'RB-LOCAL-001',
      receipt_warehouse: 'WH-LOCAL-A',
      item_code: String(base?.item_code || 'ITEM-A'),
      color: '黑色',
      size: 'M',
      batch_no: 'BATCH-LOCAL-001',
      uom: 'PCS',
      received_qty: '56',
      sync_status: 'not_released',
      stock_entry_name: null,
      inspect_status: 'waiting_inspection',
      idempotency_key: null,
      received_by: 'local-dev',
      received_at: new Date().toISOString(),
    },
  ],
  inspections: [
    {
      inspection_no: 'INSP-LOCAL-001',
      receipt_batch_no: 'RB-LOCAL-001',
      inspected_qty: '56',
      accepted_qty: '53',
      rejected_qty: '3',
      rejected_rate: '0.0536',
      subcontract_rate: String(base?.subcontract_rate || '0.65'),
      gross_amount: String(base?.gross_amount || '6800'),
      deduction_amount_per_piece: '60',
      deduction_amount: String(base?.deduction_amount || '180'),
      net_amount: String(base?.net_amount || '6620'),
      inspected_by: 'local-dev',
      inspected_at: new Date().toISOString(),
      remark: 'synthetic snapshot',
    },
  ],
  created_at: String(base?.created_at || new Date().toISOString()),
  updated_at: new Date().toISOString(),
})

const buildMaterialLines = (detail: SubcontractOrderDetailData): MaterialLineView[] => [
  {
    materialCode: detail.item_code,
    materialName: '主物料',
    colorSpec: '默认规格',
    uom: 'PCS',
    demandQty: String(detail.planned_qty || '0'),
    purchaseQty: String(detail.received_qty || detail.planned_qty || '0'),
  },
  {
    materialCode: `${detail.item_code}-AUX`,
    materialName: '辅料占位',
    colorSpec: parityToken.value === 'material-purchase' ? 'material-purchase parity' : 'local-dev synthetic',
    uom: 'PCS',
    demandQty: String(detail.planned_qty || '0'),
    purchaseQty: String(detail.accepted_qty || detail.received_qty || '0'),
  },
]

const mapReceipts = (items: SubcontractReceiptDetailItem[]): ReceiptView[] =>
  items.map((item) => ({
    receiptBatchNo: item.receipt_batch_no,
    warehouse: item.receipt_warehouse || '-',
    receivedQty: String(item.received_qty || '0'),
    syncStatus: item.sync_status || '-',
  }))

const mapInspections = (items: SubcontractInspectionDetailItem[]): InspectionView[] =>
  items.map((item) => ({
    inspectionNo: item.inspection_no,
    inspectedQty: String(item.inspected_qty || '0'),
    acceptedQty: String(item.accepted_qty || '0'),
    rejectedQty: String(item.rejected_qty || '0'),
    netAmount: String(item.net_amount || '0'),
  }))

const applyDetail = (detail: SubcontractOrderDetailData): void => {
  currentDetail.value = detail
  state.id = Number(detail.id || 0)
  state.subcontractNo = detail.subcontract_no || ''
  state.supplier = detail.supplier || ''
  state.company = detail.company || ''
  state.itemCode = detail.item_code || ''
  state.bomId = Number(detail.bom_id || 0)
  state.processName = detail.process_name || ''
  state.plannedQty = String(detail.planned_qty || '0')
  state.issuedQty = String(detail.issued_qty || '0')
  state.receivedQty = String(detail.received_qty || '0')
  state.acceptedQty = String(detail.accepted_qty || '0')
  state.rejectedQty = String(detail.rejected_qty || '0')
  state.grossAmount = String(detail.gross_amount || '0')
  state.netAmount = String(detail.net_amount || '0')
  state.status = detail.status || ''
  state.settlementStatus = detail.settlement_status || ''
  state.resourceScopeStatus = detail.resource_scope_status || ''
  state.salesOrder = detail.sales_order || ''
  state.salesOrderItem = detail.sales_order_item || ''
  state.productionPlanId = detail.production_plan_id ? String(detail.production_plan_id) : ''
  state.workOrder = detail.work_order || ''
  state.jobCard = detail.job_card || ''
  state.profitScopeStatus = detail.profit_scope_status || ''
  state.profitScopeErrorCode = detail.profit_scope_error_code || ''
  state.createdAt = detail.created_at || ''
  state.updatedAt = detail.updated_at || detail.created_at || ''
  materialLines.value = buildMaterialLines(detail)
  receipts.value = mapReceipts(detail.receipts || [])
  inspections.value = mapInspections(detail.inspections || [])

  flags.subcontractOrPurchaseReadbackSuccess = Boolean(detail.subcontract_no && detail.supplier)
  flags.materialLineReadbackSuccess = materialLines.value.length > 0
  flags.issueReturnOrInspectionReadbackSuccess =
    Number(detail.received_qty || 0) > 0 || Number(detail.inspected_qty || 0) > 0 || inspections.value.length > 0
}

const refreshDetail = async (): Promise<void> => {
  loading.value = true
  feedback.value = ''
  fallbackSnapshotUsed.value = false
  try {
    const requestedId = normalizeOrderId()
    let detail: SubcontractOrderDetailData | null = null

    if (requestedId > 0) {
      try {
        detail = (await fetchSubcontractOrderDetailReadback(requestedId)).data
      } catch {
        detail = null
      }
    }

    if (!detail) {
      const firstRow = await resolveFallbackSubcontractOrderRow()
      if (firstRow) {
        try {
          detail = (await fetchSubcontractOrderDetailReadback(firstRow.id)).data
        } catch {
          detail = buildSyntheticDetail(firstRow)
        }
      }
    }

    if (!detail) {
      detail = buildSyntheticDetail(buildSyntheticListItem())
      fallbackSnapshotUsed.value = true
      feedback.value = '未读取到本地委外详情，已回退 synthetic snapshot 保持详情入口可试用。'
    }

    if (!feedback.value && detail.id >= 900000) {
      fallbackSnapshotUsed.value = true
      feedback.value = '当前展示 synthetic snapshot；未触发任何收货、入库、库存 outbox 或 worker 生命周期。'
    }

    applyDetail(detail)
  } catch (error) {
    applyDetail(buildSyntheticDetail(buildSyntheticListItem()))
    fallbackSnapshotUsed.value = true
    feedback.value = (error as Error).message || '委外订单详情加载失败，已回退 synthetic snapshot。'
  } finally {
    loading.value = false
  }
}

const goList = (): void => {
  router.push({
    path: '/subcontract/list',
    query: {
      parity: parityToken.value || undefined,
    },
  })
}

onMounted(() => {
  void refreshDetail()
})
</script>

<style scoped>
.subcontract-detail-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.header-row,
.summary-header {
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

.header-actions,
.readonly-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.issue-inspection-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.feedback {
  margin-top: 12px;
}

.tag-stack,
.guard-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.detail-tags {
  margin-top: 12px;
}

.guard-item {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--el-text-color-regular);
}
</style>
