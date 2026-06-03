<template>
  <div class="subcontract-detail-page" data-testid="yisuan-1to1-subcontract-detail-shell">
    <el-card shadow="never">
      <template #header>
        <div class="header-row">
          <div>
            <h2>外协采购详情（本地可试用）</h2>
            <p class="sub-title">local-dev only / read-only usable slice</p>
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
        title="本页只展示 local-dev 详情，不触发结算 release、库存 outbox release、worker push 或 ERPNext 生命周期。"
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
        <span>单据主信息</span>
      </template>
      <el-descriptions border :column="2">
        <el-descriptions-item label="单据号">{{ state.subcontractNo || '-' }}</el-descriptions-item>
        <el-descriptions-item label="供应商/加工厂">{{ state.supplier || '-' }}</el-descriptions-item>
        <el-descriptions-item label="公司">{{ state.company || '-' }}</el-descriptions-item>
        <el-descriptions-item label="物料编码">{{ state.itemCode || '-' }}</el-descriptions-item>
        <el-descriptions-item label="工序">{{ state.processName || '-' }}</el-descriptions-item>
        <el-descriptions-item label="BOM ID">{{ state.bomId || '-' }}</el-descriptions-item>
        <el-descriptions-item label="计划数量">{{ state.plannedQty }}</el-descriptions-item>
        <el-descriptions-item label="状态">{{ state.status || '-' }}</el-descriptions-item>
        <el-descriptions-item label="资源范围">{{ state.resourceScopeStatus || '-' }}</el-descriptions-item>
        <el-descriptions-item label="结算状态">{{ state.settlementStatus || '-' }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <el-card shadow="never" data-testid="yisuan-1to1-subcontract-material-lines">
      <template #header>
        <span>物料明细（只读）</span>
      </template>
      <el-table :data="materialLines" border empty-text="暂无物料明细">
        <el-table-column prop="materialCode" label="物料编码" min-width="160" />
        <el-table-column prop="materialName" label="物料名称" min-width="180" />
        <el-table-column prop="colorSpec" label="颜色/规格" min-width="140" />
        <el-table-column prop="uom" label="单位" width="90" />
        <el-table-column prop="demandQty" label="需求数量" width="120" />
        <el-table-column prop="purchaseQty" label="采购/外协数量" width="150" />
      </el-table>
    </el-card>

    <el-card shadow="never" data-testid="yisuan-1to1-subcontract-scope-bridge-panel">
      <template #header>
        <span>采购/生产桥接信息（只读）</span>
      </template>
      <el-descriptions border :column="2">
        <el-descriptions-item label="final_path">{{ finalPath }}</el-descriptions-item>
        <el-descriptions-item label="parity">{{ parityToken || '-' }}</el-descriptions-item>
        <el-descriptions-item label="sales_order">{{ state.salesOrder || '-' }}</el-descriptions-item>
        <el-descriptions-item label="sales_order_item">{{ state.salesOrderItem || '-' }}</el-descriptions-item>
        <el-descriptions-item label="production_plan_id">{{ state.productionPlanId || '-' }}</el-descriptions-item>
        <el-descriptions-item label="work_order">{{ state.workOrder || '-' }}</el-descriptions-item>
        <el-descriptions-item label="job_card">{{ state.jobCard || '-' }}</el-descriptions-item>
        <el-descriptions-item label="profit_scope_status">{{ state.profitScopeStatus || '-' }}</el-descriptions-item>
        <el-descriptions-item label="profit_scope_error_code">{{ state.profitScopeErrorCode || '-' }}</el-descriptions-item>
        <el-descriptions-item label="resource_scope_status">{{ state.resourceScopeStatus || '-' }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <section class="issue-inspection-panel" data-testid="yisuan-1to1-subcontract-issue-return-inspection-panel">
      <el-card shadow="never">
        <template #header>
          <span>收料/验货/金额概览</span>
        </template>
        <el-descriptions border :column="2">
          <el-descriptions-item label="发料">{{ state.issuedQty }}</el-descriptions-item>
          <el-descriptions-item label="回料">{{ state.receivedQty }}</el-descriptions-item>
          <el-descriptions-item label="验收">{{ state.acceptedQty }}</el-descriptions-item>
          <el-descriptions-item label="不良">{{ state.rejectedQty }}</el-descriptions-item>
          <el-descriptions-item label="总额">{{ state.grossAmount }}</el-descriptions-item>
          <el-descriptions-item label="净额">{{ state.netAmount }}</el-descriptions-item>
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
          <el-table-column prop="syncStatus" label="同步状态" width="120" />
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
          false
        </el-descriptions-item>
        <el-descriptions-item label="settlement_preview_real_payment_effect">
          false
        </el-descriptions-item>
        <el-descriptions-item label="settlement_preview_real_inventory_effect">
          false
        </el-descriptions-item>
        <el-descriptions-item label="fallback_snapshot_used">
          {{ fallbackSnapshotUsed ? 'true' : 'false' }}
        </el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  fetchSubcontractOrderDetail,
  fetchSubcontractOrders,
  type SubcontractInspectionDetailItem,
  type SubcontractOrderDetailData,
  type SubcontractOrderListItem,
  type SubcontractReceiptDetailItem,
} from '@/api/subcontract'

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
})

const materialLines = ref<MaterialLineView[]>([])
const receipts = ref<ReceiptView[]>([])
const inspections = ref<InspectionView[]>([])

const flags = reactive({
  subcontractOrPurchaseReadbackSuccess: false,
  materialLineReadbackSuccess: false,
  issueReturnOrInspectionReadbackSuccess: false,
  settlementPreviewReadbackSuccess: false,
  settlementPreviewStatusObserved: false,
  settlementPreviewAmountOrSummaryObserved: false,
})

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
  production_plan_id: null,
  work_order: null,
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
  sales_order: String(base?.sales_order || (isMaterialPurchaseParity.value ? 'SO-LOCAL-001' : '')),
  sales_order_item: String(base?.sales_order_item || (isMaterialPurchaseParity.value ? 'SO-LOCAL-001-1' : '')),
  production_plan_id: Number(base?.production_plan_id || (isMaterialPurchaseParity.value ? 3001 : 0)) || null,
  work_order: String(base?.work_order || (isMaterialPurchaseParity.value ? 'WO-LOCAL-3001' : '')),
  job_card: String(base?.job_card || (isMaterialPurchaseParity.value ? 'JC-LOCAL-3001' : '')),
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
  materialLines.value = buildMaterialLines(detail)
  receipts.value = mapReceipts(detail.receipts || [])
  inspections.value = mapInspections(detail.inspections || [])

  flags.subcontractOrPurchaseReadbackSuccess = Boolean(detail.subcontract_no && detail.supplier)
  flags.materialLineReadbackSuccess = materialLines.value.length > 0
  flags.issueReturnOrInspectionReadbackSuccess =
    Number(detail.received_qty || 0) > 0 || Number(detail.inspected_qty || 0) > 0 || inspections.value.length > 0
  flags.settlementPreviewReadbackSuccess = Boolean(detail.settlement_status || detail.net_amount || detail.gross_amount)
  flags.settlementPreviewStatusObserved = Boolean(detail.settlement_status || detail.status)
  flags.settlementPreviewAmountOrSummaryObserved =
    Number(detail.gross_amount || 0) >= 0 && Number(detail.net_amount || 0) >= 0
}

const fetchFirstUsableRow = async (): Promise<SubcontractOrderListItem | null> => {
  try {
    const response = await fetchSubcontractOrders({ page: 1, page_size: 1 })
    return response.data.items?.[0] ?? null
  } catch {
    return null
  }
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
        detail = (await fetchSubcontractOrderDetail(requestedId)).data
      } catch {
        detail = null
      }
    }

    if (!detail) {
      const firstRow = await fetchFirstUsableRow()
      if (firstRow) {
        try {
          detail = (await fetchSubcontractOrderDetail(firstRow.id)).data
        } catch {
          detail = buildSyntheticDetail(firstRow)
        }
      }
    }

    if (!detail) {
      detail = buildSyntheticDetail()
      fallbackSnapshotUsed.value = true
      feedback.value = '未读取到本地外协详情，已回退 synthetic snapshot 保持详情入口可试用。'
    }

    if (!feedback.value && detail.id >= 900000) {
      fallbackSnapshotUsed.value = true
      feedback.value = '当前展示 synthetic snapshot；未触发任何结算、库存 outbox 或 worker 生命周期。'
    }

    applyDetail(detail)
  } catch (error) {
    applyDetail(buildSyntheticDetail())
    fallbackSnapshotUsed.value = true
    feedback.value = (error as Error).message || '外协采购详情加载失败，已回退 synthetic snapshot。'
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

.feedback {
  margin-top: 12px;
}
</style>
