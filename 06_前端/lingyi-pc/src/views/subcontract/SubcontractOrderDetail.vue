<template>
  <div class="subcontract-detail-page" data-testid="subcontract-detail-page">
    <el-card shadow="never" v-loading="loading" data-testid="subcontract-detail-main-card">
      <template #header>
        <div class="header-row" data-testid="subcontract-detail-header">
          <span data-testid="subcontract-detail-title">外发单详情</span>
          <el-button data-testid="subcontract-detail-back" @click="goBack">返回</el-button>
        </div>
      </template>
      <el-skeleton v-if="!permissionReady" :rows="4" animated data-testid="subcontract-detail-loading-state" />
      <el-empty
        v-else-if="!canRead"
        description="无外发查看权限"
        data-testid="subcontract-detail-permission-state"
      />
      <template v-else>
        <el-empty
          v-if="missingOrderId"
          description="请从外发单列表进入详情页"
          data-testid="subcontract-detail-missing-id-state"
        />
        <el-alert
          v-else-if="loadError"
          :title="loadError"
          type="error"
          show-icon
          :closable="false"
          data-testid="subcontract-detail-error-state"
        />
        <el-empty v-else-if="!detail" description="未找到外发单详情" data-testid="subcontract-detail-empty-state" />
        <template v-else>
          <el-descriptions :column="3" border data-testid="subcontract-detail-main-fields">
            <el-descriptions-item label="外发单号">
              <span data-testid="subcontract-detail-field-subcontract-no">{{ detail.subcontract_no }}</span>
            </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag data-testid="subcontract-detail-status-tag">{{ statusLabel(detail.status) }}</el-tag>
            <el-tag
              v-if="isScopeBlocked"
              type="danger"
              class="scope-tag"
              data-testid="subcontract-detail-scope-blocked-tag"
            >
              权限范围异常
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="公司">{{ detail.company || '-' }}</el-descriptions-item>
          <el-descriptions-item label="加工厂">{{ detail.supplier }}</el-descriptions-item>
          <el-descriptions-item label="款式">{{ detail.item_code }}</el-descriptions-item>
          <el-descriptions-item label="工序">{{ detail.process_name }}</el-descriptions-item>
          <el-descriptions-item label="计划数量">{{ detail.planned_qty }}</el-descriptions-item>
          <el-descriptions-item label="已发料">{{ detail.issued_qty }}</el-descriptions-item>
          <el-descriptions-item label="已回料">{{ detail.received_qty }}</el-descriptions-item>
          <el-descriptions-item label="已验货">{{ detail.inspected_qty }}</el-descriptions-item>
          <el-descriptions-item label="不合格数量">{{ detail.rejected_qty }}</el-descriptions-item>
          <el-descriptions-item label="合格数量">{{ detail.accepted_qty }}</el-descriptions-item>
          <el-descriptions-item label="加工单价">{{ detail.subcontract_rate }}</el-descriptions-item>
          <el-descriptions-item label="验货总金额">{{ detail.gross_amount }}</el-descriptions-item>
          <el-descriptions-item label="扣款金额">{{ detail.deduction_amount }}</el-descriptions-item>
          <el-descriptions-item label="净应付金额">{{ detail.net_amount }}</el-descriptions-item>
          <el-descriptions-item label="发料同步状态">
            <span data-testid="subcontract-detail-issue-sync-status">
              {{ stockSyncLabel(detail.latest_issue_sync_status) || '-' }}
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="回料同步状态">
            <span data-testid="subcontract-detail-receipt-sync-status">
              {{ stockSyncLabel(detail.latest_receipt_sync_status) || '-' }}
            </span>
          </el-descriptions-item>
          </el-descriptions>

          <div class="action-row" data-testid="subcontract-detail-guarded-actions">
            <el-button
              data-testid="subcontract-detail-action-issue"
              data-action-type="write"
              :disabled="!detail"
              @click="openIssueDialog"
            >
              发料
            </el-button>
            <el-button
              data-testid="subcontract-detail-action-receipt"
              data-action-type="write"
              :disabled="!detail"
              @click="openReceiveDialog"
            >
              回料
            </el-button>
            <el-button
              data-testid="subcontract-detail-action-inspection"
              data-action-type="write"
              :disabled="!detail"
              @click="openInspectDialog"
            >
              验货
            </el-button>
            <el-button
              data-testid="subcontract-detail-action-settlement"
              data-action-type="write"
              :disabled="!detail"
              @click="openSettlementDialog"
            >
              结算
            </el-button>
            <el-button
              data-testid="subcontract-detail-action-retry-sync"
              data-action-type="write"
              data-write-guard="guarded:readonly"
              @click="guardedWriteAction('同步重试')"
            >
              同步重试
            </el-button>
            <el-button
              data-testid="subcontract-detail-action-export"
              data-action-type="write"
              data-write-guard="guarded:readonly"
              @click="guardedWriteAction('导出')"
            >
              导出
            </el-button>
            <el-button
              data-testid="subcontract-detail-action-print"
              data-action-type="write"
              data-write-guard="guarded:readonly"
              @click="guardedWriteAction('打印')"
            >
              打印
            </el-button>
          </div>

          <el-alert
            v-if="guardedFeedback"
            :title="guardedFeedback"
            type="warning"
            :closable="false"
            show-icon
            data-testid="subcontract-detail-guarded-feedback"
          />

          <p class="permission-tip" data-testid="subcontract-detail-permission-or-disabled-state">
            写动作已启用 Z003 本地闭环门禁，所有请求携带 scenario_tag 与业务载体一致性校验。
          </p>
        </template>
      </template>
    </el-card>

    <el-card v-if="canRead" shadow="never" data-testid="subcontract-detail-readonly-hint-card">
      <el-alert
        title="当前页面为只读履约投影基线，普通前端已冻结新建外发单、发料、回料、验货和同步重试入口。"
        type="info"
        :closable="false"
        show-icon
      />
    </el-card>

    <el-card v-if="canRead && detail" shadow="never" data-testid="subcontract-detail-receipt-section">
      <template #header><span>回料批次</span></template>
      <el-table
        :data="detail?.receipts || []"
        border
        empty-text="暂无回料批次数据"
        data-testid="subcontract-detail-receipt-table"
      >
        <el-table-column prop="receipt_batch_no" label="回料批次" min-width="160" />
        <el-table-column prop="receipt_warehouse" label="回料仓" min-width="120" />
        <el-table-column prop="received_qty" label="回料数量" width="120" />
        <el-table-column label="同步状态" width="120">
          <template #default="scope">
            <span data-testid="subcontract-detail-receipt-sync-tag">
              {{ stockSyncLabel(scope.row.sync_status) || '-' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="stock_entry_name" label="Stock Entry" min-width="180" />
      </el-table>
    </el-card>

    <el-card v-if="canRead && detail" shadow="never" data-testid="subcontract-detail-inspection-section">
      <template #header><span>验货明细</span></template>
      <el-table
        :data="detail?.inspections || []"
        border
        empty-text="暂无验货明细数据"
        data-testid="subcontract-detail-inspection-table"
      >
        <el-table-column prop="inspection_no" label="验货单号" min-width="180" />
        <el-table-column prop="receipt_batch_no" label="回料批次" min-width="160" />
        <el-table-column prop="inspected_qty" label="验货数量" width="110" />
        <el-table-column prop="accepted_qty" label="合格数量" width="110" />
        <el-table-column prop="rejected_qty" label="不合格数量" width="120" />
        <el-table-column prop="gross_amount" label="验货总金额" width="120" />
        <el-table-column prop="deduction_amount" label="扣款金额" width="120" />
        <el-table-column prop="net_amount" label="净应付金额" width="120" />
        <el-table-column prop="inspected_by" label="验货人" width="120" />
        <el-table-column prop="inspected_at" label="验货时间" min-width="180" />
      </el-table>
    </el-card>

    <el-card v-if="canRead && detail" shadow="never" data-testid="subcontract-detail-settlement-section">
      <template #header><span>结算候选</span></template>
      <div class="settlement-toolbar">
        <el-button size="small" :loading="settlementLoading" data-testid="subcontract-settlement-candidates-refresh" @click="loadSettlementCandidates">刷新候选</el-button>
        <el-button size="small" :loading="settlementLoading" data-testid="subcontract-settlement-preview-button" @click="runSettlementPreview">预览结算</el-button>
      </div>
      <el-table
        :data="settlementCandidates"
        border
        empty-text="暂无可结算候选"
        data-testid="subcontract-settlement-candidates-table"
      >
        <el-table-column prop="inspection_id" label="验货ID" width="100" />
        <el-table-column prop="subcontract_no" label="外发单号" min-width="180" />
        <el-table-column prop="receipt_batch_no" label="回料批次" min-width="160" />
        <el-table-column prop="inspected_qty" label="验货数量" width="110" />
        <el-table-column prop="gross_amount" label="总金额" width="120" />
        <el-table-column prop="net_amount" label="净金额" width="120" />
      </el-table>
      <el-descriptions v-if="settlementPreview" :column="3" border class="settlement-preview" data-testid="subcontract-settlement-preview-summary">
        <el-descriptions-item label="行数">{{ settlementPreview.line_count }}</el-descriptions-item>
        <el-descriptions-item label="总数量">{{ settlementPreview.total_qty }}</el-descriptions-item>
        <el-descriptions-item label="净金额">{{ settlementPreview.net_amount }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <el-dialog
      v-model="issueDialogVisible"
      title="发料"
      width="560px"
      destroy-on-close
      append-to-body
      data-testid="subcontract-issue-dialog"
    >
      <el-form :model="issueForm" label-width="120px">
        <el-form-item label="发料仓">
          <el-input v-model="issueForm.warehouse" data-testid="subcontract-issue-warehouse-input" />
        </el-form-item>
        <el-form-item label="物料编码">
          <el-input v-model="issueForm.material_item_code" data-testid="subcontract-issue-material-input" />
        </el-form-item>
        <el-form-item label="需求数量">
          <el-input-number v-model="issueForm.required_qty" :min="0.001" :step="1" :precision="3" data-testid="subcontract-issue-required-qty-input" />
        </el-form-item>
        <el-form-item label="本次发料">
          <el-input-number v-model="issueForm.issued_qty" :min="0.001" :step="1" :precision="3" data-testid="subcontract-issue-issued-qty-input" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button data-testid="subcontract-issue-cancel-button" @click="issueDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="issueSubmitting" data-testid="subcontract-issue-submit-button" @click="submitIssue">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="receiveDialogVisible"
      title="回料"
      width="560px"
      destroy-on-close
      append-to-body
      data-testid="subcontract-receive-dialog"
    >
      <el-form :model="receiveForm" label-width="120px">
        <el-form-item label="回料仓">
          <el-input v-model="receiveForm.receipt_warehouse" data-testid="subcontract-receive-warehouse-input" />
        </el-form-item>
        <el-form-item label="回料数量">
          <el-input-number v-model="receiveForm.received_qty" :min="0.001" :step="1" :precision="3" data-testid="subcontract-receive-qty-input" />
        </el-form-item>
        <el-form-item label="批次号">
          <el-input v-model="receiveForm.batch_no" data-testid="subcontract-receive-batch-input" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button data-testid="subcontract-receive-cancel-button" @click="receiveDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="receiveSubmitting" data-testid="subcontract-receive-submit-button" @click="submitReceive">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="inspectDialogVisible"
      title="验货"
      width="560px"
      destroy-on-close
      append-to-body
      data-testid="subcontract-inspect-dialog"
    >
      <el-form :model="inspectForm" label-width="120px">
        <el-form-item label="回料批次">
          <el-input v-model="inspectForm.receipt_batch_no" data-testid="subcontract-inspect-batch-input" />
        </el-form-item>
        <el-form-item label="验货数量">
          <el-input-number v-model="inspectForm.inspected_qty" :min="0.001" :step="1" :precision="3" data-testid="subcontract-inspect-inspected-qty-input" />
        </el-form-item>
        <el-form-item label="不合格数量">
          <el-input-number v-model="inspectForm.rejected_qty" :min="0" :step="1" :precision="3" data-testid="subcontract-inspect-rejected-qty-input" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button data-testid="subcontract-inspect-cancel-button" @click="inspectDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="inspectSubmitting" data-testid="subcontract-inspect-submit-button" @click="submitInspect">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="settlementDialogVisible"
      title="结算锁定 / 释放"
      width="620px"
      destroy-on-close
      append-to-body
      data-testid="subcontract-settlement-dialog"
    >
      <el-form :model="settlementForm" label-width="120px">
        <el-form-item label="结算单号">
          <el-input v-model="settlementForm.statement_no" data-testid="subcontract-settlement-statement-no-input" />
        </el-form-item>
        <el-form-item label="选择验货ID">
          <el-select
            v-model="settlementForm.inspection_ids"
            multiple
            collapse-tags
            collapse-tags-tooltip
            style="width: 100%"
            data-testid="subcontract-settlement-inspection-ids-select"
          >
            <el-option
              v-for="candidate in settlementCandidates"
              :key="candidate.inspection_id"
              :label="`${candidate.inspection_id} / ${candidate.subcontract_no}`"
              :value="candidate.inspection_id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="释放原因">
          <el-input v-model="settlementForm.reason" data-testid="subcontract-settlement-reason-input" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button data-testid="subcontract-settlement-cancel-button" @click="settlementDialogVisible = false">取消</el-button>
        <el-button
          :loading="settlementSubmitting"
          data-testid="subcontract-settlement-lock-button"
          type="primary"
          @click="submitSettlementLock"
        >
          锁定
        </el-button>
        <el-button
          :loading="settlementSubmitting"
          data-testid="subcontract-settlement-release-button"
          type="warning"
          @click="submitSettlementRelease"
        >
          释放
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  buildSubcontractRequestId,
  buildSubcontractScenarioTag,
  fetchSubcontractOrderDetail,
  fetchSubcontractSettlementCandidates,
  inspectSubcontractOrder,
  issueSubcontractMaterial,
  lockSubcontractSettlement,
  previewSubcontractSettlement,
  receiveSubcontractOrder,
  releaseSubcontractSettlement,
  type SubcontractOrderDetailData,
  type SubcontractSettlementCandidateListItem,
  type SubcontractSettlementPreviewData,
  type SubcontractWriteOperation,
} from '@/api/subcontract'
import { usePermissionStore } from '@/stores/permission'

const route = useRoute()
const router = useRouter()
const permissionStore = usePermissionStore()
const detail = ref<SubcontractOrderDetailData | null>(null)
const missingOrderId = ref<boolean>(false)
const loading = ref<boolean>(false)
const permissionReady = ref<boolean>(false)
const loadError = ref<string>('')
const guardedFeedback = ref<string>('')
const issueDialogVisible = ref<boolean>(false)
const receiveDialogVisible = ref<boolean>(false)
const inspectDialogVisible = ref<boolean>(false)
const settlementDialogVisible = ref<boolean>(false)
const issueSubmitting = ref<boolean>(false)
const receiveSubmitting = ref<boolean>(false)
const inspectSubmitting = ref<boolean>(false)
const settlementSubmitting = ref<boolean>(false)
const settlementLoading = ref<boolean>(false)
const settlementCandidates = ref<SubcontractSettlementCandidateListItem[]>([])
const settlementPreview = ref<SubcontractSettlementPreviewData | null>(null)

const canRead = computed<boolean>(() => permissionStore.state.buttonPermissions.read)
const orderId = computed<number>(() => Number(route.query.id || '0'))
const hasValidOrderId = computed<boolean>(() => Number.isInteger(orderId.value) && orderId.value > 0)
const isScopeBlocked = computed<boolean>(() => detail.value?.resource_scope_status === 'blocked_scope')

const stockSyncLabel = (value?: string | null): string => {
  if (!value) return ''
  const labels: Record<string, string> = {
    pending: '待同步',
    processing: '同步中',
    succeeded: '已同步',
    failed: '同步失败',
    dead: '死信',
    blocked_scope: '范围阻断',
  }
  return labels[value] || value
}

const statusLabel = (value: string): string => {
  const labels: Record<string, string> = {
    draft: '草稿',
    issued: '已发料',
    processing: '加工中',
    waiting_receive: '待回料',
    waiting_inspection: '待验货',
    completed: '已完成',
    cancelled: '已取消',
  }
  return labels[value] || value
}

const issueForm = reactive({
  warehouse: '原材料仓',
  material_item_code: 'RM-DEMO-001',
  required_qty: 10,
  issued_qty: 10,
})

const receiveForm = reactive({
  receipt_warehouse: '成品待验仓',
  received_qty: 10,
  batch_no: '',
  color: 'BLACK',
  size: 'L',
  uom: 'PCS',
})

const inspectForm = reactive({
  receipt_batch_no: '',
  inspected_qty: 10,
  rejected_qty: 0,
  deduction_amount_per_piece: 0,
  remark: '',
})

const settlementForm = reactive({
  statement_no: '',
  inspection_ids: [] as number[],
  reason: 'release-for-local-cleanup',
})

const buildWriteCarrier = <T extends SubcontractWriteOperation>(
  operation: T,
  statusAction: string,
  quantity: number,
  sourceSuffix: string,
) => {
  if (!detail.value) {
    throw new Error('外发单详情未加载')
  }
  const scenarioTag = buildSubcontractScenarioTag()
  const sourceRef = `${scenarioTag}-${sourceSuffix}`
  const subcontractRef = detail.value.subcontract_no
  const supplierRef = detail.value.supplier
  const workOrderRef = (detail.value.work_order || String(detail.value.production_plan_id || '')).trim() || 'NO-WORK-ORDER'
  const itemCode = detail.value.item_code
  const idempotencyKey = `${scenarioTag}-${operation}-${Date.now()}`
  const requestId = buildSubcontractRequestId({
    scenarioTag,
      operation,
    idempotencyKey,
    sourceRef,
    subcontractRef,
    supplierRef,
    workOrderRef,
    itemCode,
    statusAction,
  })
  return {
    request_id: requestId,
    idempotency_key: idempotencyKey,
    scenario_tag: scenarioTag,
    source_ref: sourceRef,
    subcontract_ref: subcontractRef,
    supplier_ref: supplierRef,
    work_order_ref: workOrderRef,
      operation,
    item_code: itemCode,
    quantity,
    status_action: statusAction,
  }
}

const setDefaultReceiptBatch = (): void => {
  if (!inspectForm.receipt_batch_no && detail.value?.receipts?.length) {
    inspectForm.receipt_batch_no = detail.value.receipts[0].receipt_batch_no
  }
}

const loadSettlementCandidates = async (): Promise<void> => {
  if (!detail.value) {
    settlementCandidates.value = []
    settlementPreview.value = null
    return
  }
  settlementLoading.value = true
  try {
    const result = await fetchSubcontractSettlementCandidates({
      supplier: detail.value.supplier,
      item_code: detail.value.item_code,
      page: 1,
      page_size: 100,
    })
    settlementCandidates.value = result.data.items.filter(
      (item) => item.subcontract_no === detail.value?.subcontract_no,
    )
    if (!settlementForm.inspection_ids.length) {
      settlementForm.inspection_ids = settlementCandidates.value.slice(0, 10).map((item) => item.inspection_id)
    }
  } catch (error) {
    settlementCandidates.value = []
    settlementPreview.value = null
    ElMessage.warning((error as Error).message || '结算候选加载失败')
  } finally {
    settlementLoading.value = false
  }
}

const loadDetail = async (): Promise<void> => {
  guardedFeedback.value = ''
  loadError.value = ''
  if (!canRead.value) {
    detail.value = null
    missingOrderId.value = false
    return
  }
  if (!hasValidOrderId.value) {
    detail.value = null
    missingOrderId.value = true
    return
  }
  missingOrderId.value = false
  loading.value = true
  try {
    const result = await fetchSubcontractOrderDetail(orderId.value)
    detail.value = result.data
    setDefaultReceiptBatch()
    await loadSettlementCandidates()
  } catch (error) {
    detail.value = null
    settlementCandidates.value = []
    settlementPreview.value = null
    const message = (error as Error).message || '详情加载失败'
    loadError.value = `外发单详情加载失败：${message}`
    ElMessage.error(loadError.value)
  } finally {
    loading.value = false
  }
}

const guardedWriteAction = (actionName: string): void => {
  guardedFeedback.value = `当前为只读模式，${actionName}已禁用。`
  ElMessage.warning(guardedFeedback.value)
}

const openIssueDialog = (): void => {
  if (!detail.value) return
  issueForm.warehouse = detail.value.receipts?.[0]?.receipt_warehouse || '原材料仓'
  issueForm.material_item_code = detail.value.item_code
  issueForm.required_qty = Number(detail.value.planned_qty || 0) || 1
  issueForm.issued_qty = Number(detail.value.planned_qty || 0) || 1
  issueDialogVisible.value = true
}

const openReceiveDialog = (): void => {
  if (!detail.value) return
  receiveForm.receipt_warehouse = detail.value.receipts?.[0]?.receipt_warehouse || '成品待验仓'
  receiveForm.received_qty = Number(detail.value.planned_qty || 0) || 1
  receiveForm.batch_no = ''
  receiveDialogVisible.value = true
}

const openInspectDialog = (): void => {
  if (!detail.value) return
  setDefaultReceiptBatch()
  inspectForm.inspected_qty = Number(detail.value.received_qty || 0) || Number(detail.value.planned_qty || 0) || 1
  inspectForm.rejected_qty = 0
  inspectForm.deduction_amount_per_piece = 0
  inspectDialogVisible.value = true
}

const openSettlementDialog = async (): Promise<void> => {
  if (!detail.value) return
  await loadSettlementCandidates()
  settlementDialogVisible.value = true
}

const submitIssue = async (): Promise<void> => {
  if (!detail.value || issueSubmitting.value) return
  if (!issueForm.warehouse.trim() || !issueForm.material_item_code.trim()) {
    ElMessage.warning('请填写发料仓和物料编码')
    return
  }
  issueSubmitting.value = true
  try {
    const carrier = buildWriteCarrier('issue_material', 'issue_material', Number(issueForm.issued_qty), 'SRC-ISSUE')
    await issueSubcontractMaterial(orderId.value, {
      ...carrier,
      warehouse: issueForm.warehouse.trim(),
      materials: [
        {
          material_item_code: issueForm.material_item_code.trim(),
          required_qty: issueForm.required_qty,
          issued_qty: issueForm.issued_qty,
        },
      ],
    })
    issueDialogVisible.value = false
    await loadDetail()
    ElMessage.success('发料成功')
  } catch (error) {
    ElMessage.error((error as Error).message || '发料失败')
  } finally {
    issueSubmitting.value = false
  }
}

const submitReceive = async (): Promise<void> => {
  if (!detail.value || receiveSubmitting.value) return
  if (!receiveForm.receipt_warehouse.trim()) {
    ElMessage.warning('请填写回料仓')
    return
  }
  receiveSubmitting.value = true
  try {
    const carrier = buildWriteCarrier('receive', 'receive', Number(receiveForm.received_qty), 'SRC-RECEIVE')
    await receiveSubcontractOrder(orderId.value, {
      ...carrier,
      receipt_warehouse: receiveForm.receipt_warehouse.trim(),
      received_qty: receiveForm.received_qty,
      item_code: detail.value.item_code,
      batch_no: receiveForm.batch_no.trim() || null,
      color: receiveForm.color.trim() || null,
      size: receiveForm.size.trim() || null,
      uom: receiveForm.uom.trim() || null,
    })
    receiveDialogVisible.value = false
    await loadDetail()
    ElMessage.success('回料成功')
  } catch (error) {
    ElMessage.error((error as Error).message || '回料失败')
  } finally {
    receiveSubmitting.value = false
  }
}

const submitInspect = async (): Promise<void> => {
  if (!detail.value || inspectSubmitting.value) return
  if (!inspectForm.receipt_batch_no.trim()) {
    ElMessage.warning('请填写回料批次')
    return
  }
  inspectSubmitting.value = true
  try {
    const carrier = buildWriteCarrier('inspect', 'inspect', Number(inspectForm.inspected_qty), 'SRC-INSPECT')
    await inspectSubcontractOrder(orderId.value, {
      ...carrier,
      receipt_batch_no: inspectForm.receipt_batch_no.trim(),
      inspected_qty: inspectForm.inspected_qty,
      rejected_qty: inspectForm.rejected_qty,
      deduction_amount_per_piece: inspectForm.deduction_amount_per_piece,
      remark: inspectForm.remark.trim() || null,
    })
    inspectDialogVisible.value = false
    await loadDetail()
    ElMessage.success('验货成功')
  } catch (error) {
    ElMessage.error((error as Error).message || '验货失败')
  } finally {
    inspectSubmitting.value = false
  }
}

const runSettlementPreview = async (): Promise<void> => {
  if (!detail.value || settlementLoading.value) return
  settlementLoading.value = true
  try {
    const inspectionIds = settlementForm.inspection_ids.length
      ? settlementForm.inspection_ids
      : settlementCandidates.value.map((item) => item.inspection_id)
    const carrier = buildWriteCarrier(
      'settlement_preview',
      'settlement_preview',
      Math.max(inspectionIds.length, 1),
      'SRC-SETTLE-PREVIEW',
    )
    const result = await previewSubcontractSettlement({
      ...carrier,
      inspection_ids: inspectionIds,
      company: detail.value.company || null,
      supplier: detail.value.supplier,
      filter_item_code: detail.value.item_code,
      process_name: detail.value.process_name,
    })
    settlementPreview.value = result.data
    ElMessage.success('结算预览已更新')
  } catch (error) {
    ElMessage.error((error as Error).message || '结算预览失败')
  } finally {
    settlementLoading.value = false
  }
}

const submitSettlementLock = async (): Promise<void> => {
  if (!detail.value || settlementSubmitting.value) return
  if (!settlementForm.inspection_ids.length) {
    ElMessage.warning('请至少选择一个验货ID')
    return
  }
  settlementSubmitting.value = true
  try {
    const carrier = buildWriteCarrier(
      'settlement_lock',
      'settlement_lock',
      settlementForm.inspection_ids.length,
      'SRC-SETTLE-LOCK',
    )
    await lockSubcontractSettlement({
      ...carrier,
      statement_no: settlementForm.statement_no.trim() || `${carrier.scenario_tag}-STMT`,
      statement_id: null,
      inspection_ids: settlementForm.inspection_ids,
      remark: `locked-by-${carrier.scenario_tag}`,
    })
    await loadDetail()
    await runSettlementPreview()
    ElMessage.success('结算锁定成功')
  } catch (error) {
    ElMessage.error((error as Error).message || '结算锁定失败')
  } finally {
    settlementSubmitting.value = false
  }
}

const submitSettlementRelease = async (): Promise<void> => {
  if (!detail.value || settlementSubmitting.value) return
  if (!settlementForm.inspection_ids.length) {
    ElMessage.warning('请至少选择一个验货ID')
    return
  }
  settlementSubmitting.value = true
  try {
    const carrier = buildWriteCarrier(
      'release',
      'release',
      settlementForm.inspection_ids.length,
      'SRC-SETTLE-RELEASE',
    )
    await releaseSubcontractSettlement({
      ...carrier,
      statement_no: settlementForm.statement_no.trim() || `${carrier.scenario_tag}-STMT`,
      statement_id: null,
      inspection_ids: settlementForm.inspection_ids,
      reason: settlementForm.reason.trim() || 'release-for-local-cleanup',
    })
    await loadDetail()
    await runSettlementPreview()
    ElMessage.success('结算释放成功')
  } catch (error) {
    ElMessage.error((error as Error).message || '结算释放失败')
  } finally {
    settlementSubmitting.value = false
  }
}

const goBack = (): void => {
  router.push('/subcontract/list')
}

watch(
  () => orderId.value,
  async () => {
    await loadDetail()
  },
)

onMounted(async () => {
  try {
    await permissionStore.loadCurrentUser()
    await permissionStore.loadModuleActions('subcontract')
  } catch (error) {
    const message = (error as Error).message || '权限加载失败'
    loadError.value = message
    ElMessage.error(message)
  } finally {
    permissionReady.value = true
  }
  await loadDetail()
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
  justify-content: space-between;
  align-items: center;
}

.action-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.permission-tip {
  margin-top: 8px;
  color: var(--el-text-color-secondary);
}

.scope-tag {
  margin-left: 8px;
}

.settlement-toolbar {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.settlement-preview {
  margin-top: 12px;
}
</style>
