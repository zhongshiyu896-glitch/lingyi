<template>
  <div class="subcontract-detail-page" data-testid="subcontract-order-detail-page">
    <el-card shadow="never" v-loading="loading">
      <template #header>
        <div class="header-row">
          <div>
            <h2>委外订单详情</h2>
            <p class="sub-title">LOCAL_DEV_WRITE_CLOSURE，仅允许 create 之后的 issue / receive / inspect / settlement preview 本地闭环。</p>
          </div>
          <div class="header-actions">
            <el-button data-testid="subcontract-detail-back" @click="goList">返回列表</el-button>
            <el-button type="primary" plain :loading="loading" data-testid="subcontract-detail-refresh" @click="refreshDetail">
              刷新详情
            </el-button>
          </div>
        </div>
      </template>

      <el-alert
        type="info"
        :closable="false"
        title="允许写端点仅限 create / issue-material / receive / inspect / settlement-preview。"
      />
      <el-alert
        class="top-alert"
        type="warning"
        :closable="false"
        title="禁止 settlement-locks、release、stock-sync/retry、internal run-once、ERPNext、worker 与 production write。"
      />
      <el-alert
        v-if="actionFeedback"
        class="top-alert"
        :title="actionFeedback"
        type="success"
        :closable="false"
        data-testid="subcontract-action-feedback"
      />
      <el-alert
        v-if="loadError"
        class="top-alert"
        :title="loadError"
        type="error"
        :closable="false"
        data-testid="subcontract-detail-error"
      />

      <el-empty v-if="!orderId" description="缺少委外单 ID" data-testid="subcontract-detail-missing-id" />
      <el-empty v-else-if="!detail && !loading && !loadError" description="未找到委外单" data-testid="subcontract-detail-empty" />
      <template v-else-if="detail">
        <el-descriptions border :column="3" data-testid="subcontract-detail-main-fields">
          <el-descriptions-item label="单据号">{{ detail.subcontract_no }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="statusTag(detail.status)">{{ detail.status }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="资源范围">
            <el-tag :type="detail.resource_scope_status === 'ready' ? 'success' : 'warning'" effect="plain">
              {{ detail.resource_scope_status }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="公司">{{ detail.company || '-' }}</el-descriptions-item>
          <el-descriptions-item label="供应商">{{ detail.supplier }}</el-descriptions-item>
          <el-descriptions-item label="物料">{{ detail.item_code }}</el-descriptions-item>
          <el-descriptions-item label="工序">{{ detail.process_name }}</el-descriptions-item>
          <el-descriptions-item label="BOM ID">{{ detail.bom_id }}</el-descriptions-item>
          <el-descriptions-item label="工单 / 计划">{{ detail.work_order || '-' }} / {{ detail.production_plan_id || '-' }}</el-descriptions-item>
          <el-descriptions-item label="计划数量">{{ formatNumber(detail.planned_qty) }}</el-descriptions-item>
          <el-descriptions-item label="已发料">{{ formatNumber(detail.issued_qty) }}</el-descriptions-item>
          <el-descriptions-item label="已回料">{{ formatNumber(detail.received_qty) }}</el-descriptions-item>
          <el-descriptions-item label="已验货">{{ formatNumber(detail.inspected_qty) }}</el-descriptions-item>
          <el-descriptions-item label="已验收">{{ formatNumber(detail.accepted_qty) }}</el-descriptions-item>
          <el-descriptions-item label="不良数量">{{ formatNumber(detail.rejected_qty) }}</el-descriptions-item>
          <el-descriptions-item label="总额">{{ formatNumber(detail.gross_amount, 2) }}</el-descriptions-item>
          <el-descriptions-item label="净额">{{ formatNumber(detail.net_amount, 2) }}</el-descriptions-item>
          <el-descriptions-item label="结算状态">{{ detail.settlement_status || '-' }}</el-descriptions-item>
        </el-descriptions>

        <div class="action-row" data-testid="subcontract-detail-actions">
          <el-button
            type="warning"
            :disabled="!canIssue"
            :loading="actionSubmitting && activeAction === 'issue'"
            data-testid="subcontract-issue-button"
            data-action-type="write"
            @click="openIssueDialog"
          >
            发料
          </el-button>
          <el-button
            type="primary"
            :disabled="!canReceive"
            :loading="actionSubmitting && activeAction === 'receive'"
            data-testid="subcontract-receive-button"
            data-action-type="write"
            @click="openReceiveDialog"
          >
            回料
          </el-button>
          <el-button
            type="success"
            :disabled="!canInspect"
            :loading="actionSubmitting && activeAction === 'inspect'"
            data-testid="subcontract-inspect-button"
            data-action-type="write"
            @click="openInspectDialog"
          >
            验货
          </el-button>
          <el-button
            type="info"
            :disabled="!canPreviewSettlement"
            :loading="actionSubmitting && activeAction === 'preview'"
            data-testid="subcontract-settlement-preview-button"
            data-action-type="write"
            @click="openPreviewDialog"
          >
            结算预览
          </el-button>
        </div>
        <p class="permission-tip" data-testid="subcontract-action-state">{{ actionStateText }}</p>
      </template>
    </el-card>

    <el-card v-if="detail" shadow="never">
      <template #header>
        <span>收料批次</span>
      </template>
      <el-table :data="detail.receipts || []" border empty-text="暂无收料批次" data-testid="subcontract-receipts-table">
        <el-table-column prop="receipt_batch_no" label="批次号" min-width="150" />
        <el-table-column prop="receipt_warehouse" label="回料仓" min-width="140" />
        <el-table-column label="回料数量" width="120">
          <template #default="{ row }">{{ formatNumber(row.received_qty) }}</template>
        </el-table-column>
        <el-table-column prop="sync_status" label="同步状态" width="140" />
        <el-table-column prop="stock_entry_name" label="本地 stock entry" min-width="180" />
      </el-table>
    </el-card>

    <el-card v-if="detail" shadow="never">
      <template #header>
        <span>验货结果</span>
      </template>
      <el-table :data="detail.inspections || []" border empty-text="暂无验货记录" data-testid="subcontract-inspections-table">
        <el-table-column prop="inspection_no" label="验货单号" min-width="160" />
        <el-table-column prop="receipt_batch_no" label="批次号" min-width="150" />
        <el-table-column label="验货数量" width="120">
          <template #default="{ row }">{{ formatNumber(row.inspected_qty) }}</template>
        </el-table-column>
        <el-table-column label="不良数量" width="120">
          <template #default="{ row }">{{ formatNumber(row.rejected_qty) }}</template>
        </el-table-column>
        <el-table-column label="净额" width="120">
          <template #default="{ row }">{{ formatNumber(row.net_amount, 2) }}</template>
        </el-table-column>
        <el-table-column prop="remark" label="备注" min-width="160" />
      </el-table>
    </el-card>

    <el-card v-if="detail" shadow="never">
      <template #header>
        <span>结算候选与预览</span>
      </template>
      <el-alert
        v-if="settlementError"
        class="top-alert"
        type="error"
        :closable="false"
        :title="settlementError"
      />
      <el-table
        :data="settlementCandidates"
        border
        empty-text="暂无 settlement candidate，请先完成验货。"
        data-testid="subcontract-settlement-candidates-table"
      >
        <el-table-column prop="inspection_id" label="inspection_id" width="120" />
        <el-table-column prop="receipt_batch_no" label="批次号" min-width="140" />
        <el-table-column label="验货数量" width="120">
          <template #default="{ row }">{{ formatNumber(row.inspected_qty) }}</template>
        </el-table-column>
        <el-table-column label="净额" width="120">
          <template #default="{ row }">{{ formatNumber(row.net_amount, 2) }}</template>
        </el-table-column>
        <el-table-column prop="settlement_status" label="结算状态" min-width="140" />
      </el-table>

      <el-descriptions
        v-if="settlementPreview"
        class="preview-summary"
        border
        :column="2"
        data-testid="subcontract-settlement-preview-result"
      >
        <el-descriptions-item label="line_count">{{ settlementPreview.line_count }}</el-descriptions-item>
        <el-descriptions-item label="total_qty">{{ formatNumber(settlementPreview.total_qty) }}</el-descriptions-item>
        <el-descriptions-item label="gross_amount">{{ formatNumber(settlementPreview.gross_amount, 2) }}</el-descriptions-item>
        <el-descriptions-item label="deduction_amount">{{ formatNumber(settlementPreview.deduction_amount, 2) }}</el-descriptions-item>
        <el-descriptions-item label="net_amount">{{ formatNumber(settlementPreview.net_amount, 2) }}</el-descriptions-item>
        <el-descriptions-item label="supplier">{{ settlementPreview.supplier || '-' }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <el-dialog v-model="issueDialogVisible" title="发料" width="560px" destroy-on-close>
      <el-form label-width="120px">
        <el-form-item label="仓库">
          <el-input v-model="issueForm.warehouse" data-testid="subcontract-issue-warehouse" />
        </el-form-item>
        <el-form-item label="carrier quantity">
          <el-input v-model="issueForm.quantity" data-testid="subcontract-issue-quantity" />
        </el-form-item>
        <el-form-item label="scenario_tag">
          <el-input v-model="issueForm.scenario_tag" />
        </el-form-item>
        <el-form-item label="request_id">
          <el-input :model-value="issueRequestId" readonly />
        </el-form-item>
        <el-form-item>
          <el-text type="info">materials 留空时，后端会按 BOM 自动展开剩余可发料物料。</el-text>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="issueDialogVisible = false">取消</el-button>
        <el-button
          type="primary"
          :loading="actionSubmitting && activeAction === 'issue'"
          data-testid="subcontract-issue-submit"
          @click="submitIssue"
        >
          确认发料
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="receiveDialogVisible" title="回料" width="560px" destroy-on-close>
      <el-form label-width="120px">
        <el-form-item label="回料仓">
          <el-input v-model="receiveForm.receipt_warehouse" data-testid="subcontract-receive-warehouse" />
        </el-form-item>
        <el-form-item label="回料数量">
          <el-input v-model="receiveForm.received_qty" data-testid="subcontract-receive-qty" />
        </el-form-item>
        <el-form-item label="颜色">
          <el-input v-model="receiveForm.color" />
        </el-form-item>
        <el-form-item label="尺码">
          <el-input v-model="receiveForm.size" />
        </el-form-item>
        <el-form-item label="批号">
          <el-input v-model="receiveForm.batch_no" />
        </el-form-item>
        <el-form-item label="单位">
          <el-input v-model="receiveForm.uom" />
        </el-form-item>
        <el-form-item label="scenario_tag">
          <el-input v-model="receiveForm.scenario_tag" />
        </el-form-item>
        <el-form-item label="request_id">
          <el-input :model-value="receiveRequestId" readonly />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="receiveDialogVisible = false">取消</el-button>
        <el-button
          type="primary"
          :loading="actionSubmitting && activeAction === 'receive'"
          data-testid="subcontract-receive-submit"
          @click="submitReceive"
        >
          确认回料
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="inspectDialogVisible" title="验货" width="560px" destroy-on-close>
      <el-form label-width="120px">
        <el-form-item label="回料批次">
          <el-select v-model="inspectForm.receipt_batch_no" style="width: 100%" data-testid="subcontract-inspect-batch">
            <el-option
              v-for="receipt in detail?.receipts || []"
              :key="receipt.receipt_batch_no"
              :label="receipt.receipt_batch_no"
              :value="receipt.receipt_batch_no"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="验货数量">
          <el-input v-model="inspectForm.inspected_qty" data-testid="subcontract-inspect-qty" />
        </el-form-item>
        <el-form-item label="不良数量">
          <el-input v-model="inspectForm.rejected_qty" data-testid="subcontract-inspect-rejected" />
        </el-form-item>
        <el-form-item label="单件扣款">
          <el-input v-model="inspectForm.deduction_amount_per_piece" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="inspectForm.remark" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="scenario_tag">
          <el-input v-model="inspectForm.scenario_tag" />
        </el-form-item>
        <el-form-item label="request_id">
          <el-input :model-value="inspectRequestId" readonly />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="inspectDialogVisible = false">取消</el-button>
        <el-button
          type="primary"
          :loading="actionSubmitting && activeAction === 'inspect'"
          data-testid="subcontract-inspect-submit"
          @click="submitInspect"
        >
          确认验货
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="previewDialogVisible" title="结算预览" width="560px" destroy-on-close>
      <el-form label-width="120px">
        <el-form-item label="inspection_ids">
          <el-input :model-value="previewInspectionIdsText" readonly />
        </el-form-item>
        <el-form-item label="carrier quantity">
          <el-input v-model="previewForm.quantity" data-testid="subcontract-preview-qty" />
        </el-form-item>
        <el-form-item label="scenario_tag">
          <el-input v-model="previewForm.scenario_tag" />
        </el-form-item>
        <el-form-item label="request_id">
          <el-input :model-value="previewRequestId" readonly />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="previewDialogVisible = false">取消</el-button>
        <el-button
          type="primary"
          :loading="actionSubmitting && activeAction === 'preview'"
          data-testid="subcontract-preview-submit"
          @click="submitPreview"
        >
          生成预览
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type {
  NumericLike,
  SubcontractInspectRequestPayload,
  SubcontractOrderDetailData,
  SubcontractReceiveRequestPayload,
  SubcontractSettlementCandidateListItem,
  SubcontractSettlementPreviewData,
  SubcontractSettlementPreviewRequestPayload,
  SubcontractIssueMaterialRequestPayload,
} from '@/api/subcontract'
import {
  buildSubcontractRequestId,
  buildSubcontractScenarioTag,
  fetchSubcontractOrderDetail,
  fetchSubcontractSettlementCandidates,
  inspectSubcontractOrder,
  issueSubcontractMaterial,
  previewSubcontractSettlement,
  receiveSubcontractOrder,
} from '@/api/subcontract'

interface IssueFormState {
  warehouse: string
  quantity: string
  scenario_tag: string
  idempotency_key: string
}

interface ReceiveFormState {
  receipt_warehouse: string
  received_qty: string
  color: string
  size: string
  batch_no: string
  uom: string
  scenario_tag: string
  idempotency_key: string
}

interface InspectFormState {
  receipt_batch_no: string
  inspected_qty: string
  rejected_qty: string
  deduction_amount_per_piece: string
  remark: string
  scenario_tag: string
  idempotency_key: string
}

interface PreviewFormState {
  quantity: string
  scenario_tag: string
  idempotency_key: string
}

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const loadError = ref('')
const settlementError = ref('')
const actionFeedback = ref('')
const actionSubmitting = ref(false)
const activeAction = ref<'issue' | 'receive' | 'inspect' | 'preview' | ''>('')

const detail = ref<SubcontractOrderDetailData | null>(null)
const settlementCandidates = ref<SubcontractSettlementCandidateListItem[]>([])
const settlementPreview = ref<SubcontractSettlementPreviewData | null>(null)

const issueDialogVisible = ref(false)
const receiveDialogVisible = ref(false)
const inspectDialogVisible = ref(false)
const previewDialogVisible = ref(false)

const buildNonce = (prefix: string): string => `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`

const parseNumber = (value: NumericLike | undefined | null): number => {
  const parsed = Number(value || 0)
  return Number.isFinite(parsed) ? parsed : 0
}

const formatNumber = (value: NumericLike | undefined | null, digits = 0): string =>
  parseNumber(value).toLocaleString('zh-CN', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })

const statusTag = (status: string): 'info' | 'success' | 'warning' | 'danger' => {
  if (status === 'completed') return 'success'
  if (status === 'draft') return 'info'
  if (status === 'issued' || status === 'waiting_receive' || status === 'waiting_inspection') return 'warning'
  return 'danger'
}

const normalizeWorkOrderRef = (): string => {
  if (detail.value?.work_order) return detail.value.work_order
  if (detail.value?.production_plan_id) return String(detail.value.production_plan_id)
  return 'NO-WORK-ORDER'
}

const orderId = computed(() => {
  const raw = route.query.id
  const resolved = Array.isArray(raw) ? raw[0] : raw
  const parsed = Number(resolved || 0)
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 0
})

const issueForm = reactive<IssueFormState>({
  warehouse: 'WH-SUB-LOCAL',
  quantity: '1',
  scenario_tag: buildSubcontractScenarioTag(),
  idempotency_key: '',
})

const receiveForm = reactive<ReceiveFormState>({
  receipt_warehouse: 'WH-SUB-LOCAL',
  received_qty: '1',
  color: '白色',
  size: 'M',
  batch_no: '',
  uom: 'PCS',
  scenario_tag: buildSubcontractScenarioTag(),
  idempotency_key: '',
})

const inspectForm = reactive<InspectFormState>({
  receipt_batch_no: '',
  inspected_qty: '1',
  rejected_qty: '0',
  deduction_amount_per_piece: '0',
  remark: '',
  scenario_tag: buildSubcontractScenarioTag(),
  idempotency_key: '',
})

const previewForm = reactive<PreviewFormState>({
  quantity: '1',
  scenario_tag: buildSubcontractScenarioTag(),
  idempotency_key: '',
})

const canIssue = computed(() => {
  const status = detail.value?.status || ''
  return ['draft', 'issued', 'processing', 'waiting_receive'].includes(status)
})

const canReceive = computed(() => {
  const status = detail.value?.status || ''
  return ['issued', 'processing', 'waiting_receive', 'waiting_inspection'].includes(status)
})

const canInspect = computed(() => {
  const status = detail.value?.status || ''
  return ['waiting_receive', 'waiting_inspection'].includes(status) && (detail.value?.receipts?.length || 0) > 0
})

const canPreviewSettlement = computed(() => settlementCandidates.value.length > 0)

const actionStateText = computed(() => {
  if (!detail.value) return '缺少委外单详情'
  const reasons: string[] = []
  if (!canIssue.value) reasons.push('发料状态不满足')
  if (!canReceive.value) reasons.push('回料状态不满足')
  if (!canInspect.value) reasons.push('验货需要至少一个已回料批次')
  if (!canPreviewSettlement.value) reasons.push('结算预览需要 settlement candidates')
  return reasons.length > 0 ? `当前受限：${reasons.join('；')}` : '当前单据已满足本地写闭环前置条件。'
})

const issueRequestId = computed(() => {
  const scenarioTag = issueForm.scenario_tag.trim() || buildSubcontractScenarioTag()
  const idempotencyKey = issueForm.idempotency_key.trim() || 'pending-idempotency-key'
  const quantity = issueForm.quantity.trim() || '1'
  return buildSubcontractRequestId({
    scenarioTag,
    operation: 'issue_material',
    idempotencyKey,
    sourceRef: `${scenarioTag}:issue:${orderId.value}:${quantity}`,
    subcontractRef: String(orderId.value || detail.value?.subcontract_no || '0'),
    supplierRef: detail.value?.supplier || 'SUP-A',
    workOrderRef: normalizeWorkOrderRef(),
    itemCode: detail.value?.item_code || 'DEMO-TEE',
    statusAction: 'issue_material',
  })
})

const receiveRequestId = computed(() => {
  const scenarioTag = receiveForm.scenario_tag.trim() || buildSubcontractScenarioTag()
  const idempotencyKey = receiveForm.idempotency_key.trim() || 'pending-idempotency-key'
  const quantity = receiveForm.received_qty.trim() || '1'
  return buildSubcontractRequestId({
    scenarioTag,
    operation: 'receive',
    idempotencyKey,
    sourceRef: `${scenarioTag}:receive:${orderId.value}:${quantity}`,
    subcontractRef: String(orderId.value || detail.value?.subcontract_no || '0'),
    supplierRef: detail.value?.supplier || 'SUP-A',
    workOrderRef: normalizeWorkOrderRef(),
    itemCode: detail.value?.item_code || 'DEMO-TEE',
    statusAction: 'receive',
  })
})

const inspectRequestId = computed(() => {
  const scenarioTag = inspectForm.scenario_tag.trim() || buildSubcontractScenarioTag()
  const idempotencyKey = inspectForm.idempotency_key.trim() || 'pending-idempotency-key'
  const quantity = inspectForm.inspected_qty.trim() || '1'
  return buildSubcontractRequestId({
    scenarioTag,
    operation: 'inspect',
    idempotencyKey,
    sourceRef: `${scenarioTag}:inspect:${orderId.value}:${inspectForm.receipt_batch_no || 'batch'}`,
    subcontractRef: String(orderId.value || detail.value?.subcontract_no || '0'),
    supplierRef: detail.value?.supplier || 'SUP-A',
    workOrderRef: normalizeWorkOrderRef(),
    itemCode: detail.value?.item_code || 'DEMO-TEE',
    statusAction: 'inspect',
  })
})

const previewInspectionIds = computed(() => settlementCandidates.value.map((row) => row.inspection_id))
const previewInspectionIdsText = computed(() => previewInspectionIds.value.join(', '))

const previewRequestId = computed(() => {
  const scenarioTag = previewForm.scenario_tag.trim() || buildSubcontractScenarioTag()
  const idempotencyKey = previewForm.idempotency_key.trim() || 'pending-idempotency-key'
  const quantity = previewForm.quantity.trim() || '1'
  return buildSubcontractRequestId({
    scenarioTag,
    operation: 'settlement_preview',
    idempotencyKey,
    sourceRef: `${scenarioTag}:settlement-preview:${orderId.value}:${previewInspectionIdsText.value || 'none'}`,
    subcontractRef: String(orderId.value || detail.value?.subcontract_no || '0'),
    supplierRef: detail.value?.supplier || 'SUP-A',
    workOrderRef: normalizeWorkOrderRef(),
    itemCode: detail.value?.item_code || 'DEMO-TEE',
    statusAction: 'settlement_preview',
  })
})

const loadSettlementCandidates = async (): Promise<void> => {
  if (!detail.value) {
    settlementCandidates.value = []
    settlementPreview.value = null
    return
  }
  try {
    const response = await fetchSubcontractSettlementCandidates({
      company: detail.value.company || undefined,
      supplier: detail.value.supplier || undefined,
      item_code: detail.value.item_code || undefined,
      process_name: detail.value.process_name || undefined,
      page: 1,
      page_size: 100,
    })
    settlementCandidates.value = (response.data.items || []).filter((row) => row.subcontract_id === detail.value?.id)
    settlementError.value = ''
  } catch (error) {
    settlementCandidates.value = []
    settlementPreview.value = null
    settlementError.value = (error as Error).message || '结算候选加载失败'
  }
}

const refreshDetail = async (): Promise<void> => {
  if (!orderId.value) return
  loading.value = true
  loadError.value = ''
  try {
    const response = await fetchSubcontractOrderDetail(orderId.value)
    detail.value = response.data
    await loadSettlementCandidates()
  } catch (error) {
    detail.value = null
    settlementCandidates.value = []
    settlementPreview.value = null
    loadError.value = (error as Error).message || '委外订单详情加载失败'
  } finally {
    loading.value = false
  }
}

const withAction = async (action: 'issue' | 'receive' | 'inspect' | 'preview', runner: () => Promise<void>) => {
  activeAction.value = action
  actionSubmitting.value = true
  try {
    await runner()
  } finally {
    actionSubmitting.value = false
    activeAction.value = ''
  }
}

const openIssueDialog = (): void => {
  const remaining = Math.max(parseNumber(detail.value?.planned_qty) - parseNumber(detail.value?.issued_qty), 1)
  issueForm.warehouse = 'WH-SUB-LOCAL'
  issueForm.quantity = String(remaining)
  issueForm.scenario_tag = buildSubcontractScenarioTag()
  issueForm.idempotency_key = buildNonce('subcontract-issue')
  issueDialogVisible.value = true
}

const openReceiveDialog = (): void => {
  const remaining = Math.max(parseNumber(detail.value?.planned_qty) - parseNumber(detail.value?.received_qty), 1)
  receiveForm.receipt_warehouse = 'WH-SUB-LOCAL'
  receiveForm.received_qty = String(remaining)
  receiveForm.color = '白色'
  receiveForm.size = 'M'
  receiveForm.batch_no = ''
  receiveForm.uom = 'PCS'
  receiveForm.scenario_tag = buildSubcontractScenarioTag()
  receiveForm.idempotency_key = buildNonce('subcontract-receive')
  receiveDialogVisible.value = true
}

const openInspectDialog = (): void => {
  const latestReceipt = detail.value?.receipts?.[detail.value.receipts.length - 1]
  const remaining = Math.max(parseNumber(detail.value?.received_qty) - parseNumber(detail.value?.inspected_qty), 1)
  inspectForm.receipt_batch_no = latestReceipt?.receipt_batch_no || ''
  inspectForm.inspected_qty = String(remaining)
  inspectForm.rejected_qty = '0'
  inspectForm.deduction_amount_per_piece = '0'
  inspectForm.remark = ''
  inspectForm.scenario_tag = buildSubcontractScenarioTag()
  inspectForm.idempotency_key = buildNonce('subcontract-inspect')
  inspectDialogVisible.value = true
}

const openPreviewDialog = (): void => {
  const quantity = Math.max(parseNumber(detail.value?.accepted_qty) || parseNumber(detail.value?.inspected_qty), 1)
  previewForm.quantity = String(quantity)
  previewForm.scenario_tag = buildSubcontractScenarioTag()
  previewForm.idempotency_key = buildNonce('subcontract-preview')
  previewDialogVisible.value = true
}

const submitIssue = async (): Promise<void> => {
  if (!detail.value) return
  const currentDetail = detail.value
  await withAction('issue', async () => {
    const payload: SubcontractIssueMaterialRequestPayload = {
      request_id: issueRequestId.value,
      idempotency_key: issueForm.idempotency_key,
      scenario_tag: issueForm.scenario_tag,
      source_ref: `${issueForm.scenario_tag}:issue:${orderId.value}:${issueForm.quantity}`,
      subcontract_ref: String(orderId.value),
      supplier_ref: currentDetail.supplier,
      work_order_ref: normalizeWorkOrderRef(),
      operation: 'issue_material',
      item_code: currentDetail.item_code,
      quantity: issueForm.quantity,
      status_action: 'issue_material',
      warehouse: issueForm.warehouse.trim(),
      materials: [],
    }
    const response = await issueSubcontractMaterial(orderId.value, payload)
    issueDialogVisible.value = false
    actionFeedback.value = `发料成功：batch=${response.data.issue_batch_no}，outbox=${response.data.outbox_id}，status=${response.data.sync_status}`
    ElMessage.success('发料成功')
    await refreshDetail()
  }).catch((error) => {
    ElMessage.error((error as Error).message || '发料失败')
  })
}

const submitReceive = async (): Promise<void> => {
  if (!detail.value) return
  const currentDetail = detail.value
  await withAction('receive', async () => {
    const payload: SubcontractReceiveRequestPayload = {
      request_id: receiveRequestId.value,
      idempotency_key: receiveForm.idempotency_key,
      scenario_tag: receiveForm.scenario_tag,
      source_ref: `${receiveForm.scenario_tag}:receive:${orderId.value}:${receiveForm.received_qty}`,
      subcontract_ref: String(orderId.value),
      supplier_ref: currentDetail.supplier,
      work_order_ref: normalizeWorkOrderRef(),
      operation: 'receive',
      item_code: currentDetail.item_code,
      quantity: receiveForm.received_qty,
      status_action: 'receive',
      receipt_warehouse: receiveForm.receipt_warehouse.trim(),
      received_qty: receiveForm.received_qty,
      color: receiveForm.color.trim() || null,
      size: receiveForm.size.trim() || null,
      batch_no: receiveForm.batch_no.trim() || null,
      uom: receiveForm.uom.trim() || null,
    }
    const response = await receiveSubcontractOrder(orderId.value, payload)
    receiveDialogVisible.value = false
    actionFeedback.value = `回料成功：batch=${response.data.receipt_batch_no}，outbox=${response.data.outbox_id}，status=${response.data.sync_status}`
    ElMessage.success('回料成功')
    await refreshDetail()
  }).catch((error) => {
    ElMessage.error((error as Error).message || '回料失败')
  })
}

const submitInspect = async (): Promise<void> => {
  if (!detail.value) return
  const currentDetail = detail.value
  await withAction('inspect', async () => {
    const payload: SubcontractInspectRequestPayload = {
      request_id: inspectRequestId.value,
      idempotency_key: inspectForm.idempotency_key,
      scenario_tag: inspectForm.scenario_tag,
      source_ref: `${inspectForm.scenario_tag}:inspect:${orderId.value}:${inspectForm.receipt_batch_no}`,
      subcontract_ref: String(orderId.value),
      supplier_ref: currentDetail.supplier,
      work_order_ref: normalizeWorkOrderRef(),
      operation: 'inspect',
      item_code: currentDetail.item_code,
      quantity: inspectForm.inspected_qty,
      status_action: 'inspect',
      receipt_batch_no: inspectForm.receipt_batch_no,
      inspected_qty: inspectForm.inspected_qty,
      rejected_qty: inspectForm.rejected_qty,
      deduction_amount_per_piece: inspectForm.deduction_amount_per_piece,
      remark: inspectForm.remark.trim() || null,
    }
    const response = await inspectSubcontractOrder(orderId.value, payload)
    inspectDialogVisible.value = false
    actionFeedback.value = `验货成功：inspection=${response.data.inspection_no}，net=${formatNumber(response.data.net_amount, 2)}`
    ElMessage.success('验货成功')
    await refreshDetail()
  }).catch((error) => {
    ElMessage.error((error as Error).message || '验货失败')
  })
}

const submitPreview = async (): Promise<void> => {
  if (!detail.value) return
  const currentDetail = detail.value
  await withAction('preview', async () => {
    const payload: SubcontractSettlementPreviewRequestPayload = {
      request_id: previewRequestId.value,
      idempotency_key: previewForm.idempotency_key,
      scenario_tag: previewForm.scenario_tag,
      source_ref: `${previewForm.scenario_tag}:settlement-preview:${orderId.value}:${previewInspectionIdsText.value || 'none'}`,
      subcontract_ref: String(orderId.value),
      supplier_ref: currentDetail.supplier,
      work_order_ref: normalizeWorkOrderRef(),
      operation: 'settlement_preview',
      item_code: currentDetail.item_code,
      quantity: previewForm.quantity,
      status_action: 'settlement_preview',
      inspection_ids: previewInspectionIds.value,
      company: currentDetail.company || null,
      supplier: currentDetail.supplier || null,
      filter_item_code: currentDetail.item_code || null,
      process_name: currentDetail.process_name || null,
    }
    const response = await previewSubcontractSettlement(payload)
    settlementPreview.value = response.data
    previewDialogVisible.value = false
    actionFeedback.value = `结算预览成功：line_count=${response.data.line_count}，net=${formatNumber(response.data.net_amount, 2)}`
    ElMessage.success('结算预览成功')
    await loadSettlementCandidates()
  }).catch((error) => {
    ElMessage.error((error as Error).message || '结算预览失败')
  })
}

const goList = (): void => {
  router.push('/subcontract/list')
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
  margin: 4px 0 0;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.header-actions,
.action-row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.top-alert {
  margin-top: 12px;
}

.action-row {
  margin-top: 16px;
}

.permission-tip {
  margin: 12px 0 0;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.preview-summary {
  margin-top: 16px;
}
</style>
