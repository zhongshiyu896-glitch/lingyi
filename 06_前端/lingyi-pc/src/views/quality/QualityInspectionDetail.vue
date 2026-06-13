<template>
  <div class="quality-detail-page" data-testid="quality-inspection-detail-page">
    <el-card shadow="never" v-loading="loading" data-testid="quality-inspection-detail-card">
      <template #header>
        <div class="header-row" data-testid="quality-inspection-detail-header">
          <span data-testid="quality-inspection-detail-title">质量检验单详情</span>
          <el-button data-testid="quality-inspection-detail-back" @click="backToList">返回列表</el-button>
        </div>
      </template>

      <el-alert
        v-if="actionFeedback"
        :title="actionFeedback"
        type="warning"
        :closable="false"
        show-icon
        data-testid="quality-inspection-detail-action-feedback"
      />

      <el-alert
        type="info"
        :closable="false"
        data-testid="quality-inspection-detail-readonly-parity-hint"
        :title="`quality parity=${qualityDetailParity}（LOCAL_DEV_WRITE_CLOSURE，仅 development + sqlite 允许写入）`"
      />

      <el-empty
        v-if="!canRead"
        description="无质量管理查看权限"
        data-testid="quality-inspection-detail-permission-state"
      />
      <el-empty
        v-else-if="!inspectionId"
        description="缺少质量检验单 ID"
        data-testid="quality-inspection-detail-missing-id-state"
      />
      <template v-else>
        <el-alert
          v-if="loadError"
          :title="loadError"
          type="error"
          show-icon
          :closable="false"
          data-testid="quality-inspection-detail-error-state"
        />
        <el-empty
          v-else-if="!detail"
          description="未找到质量检验单"
          data-testid="quality-inspection-detail-empty-state"
        />
        <template v-else>
          <el-descriptions :column="3" border data-testid="quality-inspection-detail-main-fields">
            <el-descriptions-item label="检验单号">
              <span data-testid="quality-inspection-detail-field-inspection-no">{{ detail.inspection_no }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="statusTag(detail.status)" data-testid="quality-inspection-detail-status-tag">
                {{ statusLabel(detail.status) }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="结果">
              <el-tag :type="resultTag(detail.result)" data-testid="quality-inspection-detail-result-tag">
                {{ resultLabel(detail.result) }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="公司">{{ detail.company }}</el-descriptions-item>
            <el-descriptions-item label="物料">{{ detail.item_code }}</el-descriptions-item>
            <el-descriptions-item label="供应商">{{ detail.supplier || '-' }}</el-descriptions-item>
            <el-descriptions-item label="来源类型">{{ sourceTypeLabel(detail.source_type) }}</el-descriptions-item>
            <el-descriptions-item label="来源单号">{{ detail.source_id || '-' }}</el-descriptions-item>
            <el-descriptions-item label="仓库">{{ detail.warehouse || '-' }}</el-descriptions-item>
            <el-descriptions-item label="检验日期">{{ detail.inspection_date }}</el-descriptions-item>
            <el-descriptions-item label="检验数量">{{ formatAmount(detail.inspected_qty) }}</el-descriptions-item>
            <el-descriptions-item label="合格数量">{{ formatAmount(detail.accepted_qty) }}</el-descriptions-item>
            <el-descriptions-item label="不合格数量">{{ formatAmount(detail.rejected_qty) }}</el-descriptions-item>
            <el-descriptions-item label="缺陷数量">{{ formatAmount(detail.defect_qty) }}</el-descriptions-item>
            <el-descriptions-item label="缺陷率">{{ formatRate(detail.defect_rate) }}</el-descriptions-item>
            <el-descriptions-item label="备注">{{ detail.remark || '-' }}</el-descriptions-item>
          </el-descriptions>

          <el-alert
            v-if="outboxStatus"
            class="outbox-alert"
            type="info"
            :closable="false"
            :title="`Outbox 状态：${outboxStatus.status}（尝试 ${outboxStatus.attempts}/${outboxStatus.max_attempts}）`"
            data-testid="quality-inspection-detail-outbox-status"
          />

          <div class="action-row" data-testid="quality-inspection-detail-actions">
            <el-button
              v-if="canUpdate"
              type="primary"
              :disabled="!canUpdate"
              :loading="actionSubmitting && activeAction === 'update'"
              data-testid="quality-inspection-detail-action-edit"
              data-action-type="write"
              data-write-guard="local_dev:quality-detail-update"
              data-guard-state="enabled_local_dev"
              @click="openUpdateDialog"
            >
              编辑草稿
            </el-button>
            <el-button
              v-if="canUpdate"
              type="warning"
              :disabled="!canUpdate"
              :loading="actionSubmitting && activeAction === 'defects'"
              data-testid="quality-inspection-detail-action-defect"
              data-action-type="write"
              data-write-guard="local_dev:quality-detail-defects"
              data-guard-state="enabled_local_dev"
              @click="openDefectDialog"
            >
              录入缺陷
            </el-button>
            <el-button
              v-if="canConfirm"
              type="success"
              :disabled="!canConfirm"
              :loading="actionSubmitting && activeAction === 'confirm'"
              data-testid="quality-inspection-detail-action-confirm"
              data-action-type="write"
              data-write-guard="local_dev:quality-detail-confirm"
              data-guard-state="enabled_local_dev"
              @click="openConfirmDialog"
            >
              确认检验单
            </el-button>
            <el-button
              v-if="canCancel"
              type="danger"
              :disabled="!canCancel"
              :loading="actionSubmitting && activeAction === 'cancel'"
              data-testid="quality-inspection-detail-action-cancel"
              data-action-type="write"
              data-write-guard="local_dev:quality-detail-cancel"
              data-guard-state="enabled_local_dev"
              @click="openCancelDialog"
            >
              取消检验单
            </el-button>
          </div>
          <p class="permission-tip" data-testid="quality-inspection-detail-permission-disabled-state">
            {{ permissionStateText }}
          </p>
        </template>
      </template>
    </el-card>

    <el-card v-if="detail" shadow="never" data-testid="quality-inspection-detail-items-section">
      <template #header>
        <span>检验明细</span>
      </template>
      <el-table
        :data="detail.items || []"
        border
        empty-text="暂无检验明细"
        data-testid="quality-inspection-detail-items-table"
      >
        <el-table-column prop="line_no" label="行号" width="70" />
        <el-table-column prop="item_code" label="物料" min-width="140" />
        <el-table-column label="抽样数量" width="110">
          <template #default="scope">{{ formatAmount(scope.row.sample_qty) }}</template>
        </el-table-column>
        <el-table-column label="合格数量" width="110">
          <template #default="scope">{{ formatAmount(scope.row.accepted_qty) }}</template>
        </el-table-column>
        <el-table-column label="不合格数量" width="120">
          <template #default="scope">{{ formatAmount(scope.row.rejected_qty) }}</template>
        </el-table-column>
        <el-table-column label="缺陷数量" width="110">
          <template #default="scope">{{ formatAmount(scope.row.defect_qty) }}</template>
        </el-table-column>
        <el-table-column label="结果" width="110">
          <template #default="scope">{{ resultLabel(scope.row.result) }}</template>
        </el-table-column>
        <el-table-column prop="remark" label="备注" min-width="160" />
      </el-table>
    </el-card>

    <el-card v-if="detail" shadow="never" data-testid="quality-inspection-detail-defects-section">
      <template #header>
        <span>缺陷记录</span>
      </template>
      <el-table
        :data="detail.defects || []"
        border
        empty-text="暂无缺陷记录"
        data-testid="quality-inspection-detail-defects-table"
      >
        <el-table-column prop="defect_code" label="缺陷编码" min-width="120" />
        <el-table-column prop="defect_name" label="缺陷名称" min-width="160" />
        <el-table-column label="缺陷数量" width="110">
          <template #default="scope">{{ formatAmount(scope.row.defect_qty) }}</template>
        </el-table-column>
        <el-table-column prop="severity" label="严重度" width="110" />
        <el-table-column prop="remark" label="备注" min-width="160" />
      </el-table>
    </el-card>

    <el-card v-if="detail" shadow="never" data-testid="quality-inspection-detail-logs-section">
      <template #header>
        <span>操作日志</span>
      </template>
      <el-table
        :data="detail.logs || []"
        border
        empty-text="暂无操作日志"
        data-testid="quality-inspection-detail-logs-table"
      >
        <el-table-column prop="action" label="动作" min-width="120" />
        <el-table-column prop="from_status" label="原状态" min-width="120" />
        <el-table-column prop="to_status" label="新状态" min-width="120" />
        <el-table-column prop="operator" label="操作人" min-width="120" />
        <el-table-column prop="remark" label="备注" min-width="180" />
        <el-table-column prop="operated_at" label="时间" min-width="180" />
      </el-table>
    </el-card>

    <el-dialog v-model="updateDialogVisible" title="编辑草稿" width="560px" destroy-on-close>
      <el-form label-width="120px">
        <el-form-item label="scenario_tag">
          <el-input v-model="updateForm.scenario_tag" />
        </el-form-item>
        <el-form-item label="idempotency_key">
          <el-input v-model="updateForm.idempotency_key" />
        </el-form-item>
        <el-form-item label="request_id">
          <el-input v-model="updateForm.request_id" readonly />
        </el-form-item>
        <el-form-item label="检验日期">
          <el-date-picker v-model="updateForm.inspection_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <el-form-item label="检验数量">
          <el-input v-model="updateForm.inspected_qty" />
        </el-form-item>
        <el-form-item label="合格数量">
          <el-input v-model="updateForm.accepted_qty" />
        </el-form-item>
        <el-form-item label="不合格数量">
          <el-input v-model="updateForm.rejected_qty" />
        </el-form-item>
        <el-form-item label="缺陷数量">
          <el-input v-model="updateForm.defect_qty" />
        </el-form-item>
        <el-form-item label="结果">
          <el-select v-model="updateForm.result" style="width: 100%">
            <el-option label="待定" value="pending" />
            <el-option label="合格" value="pass" />
            <el-option label="不合格" value="fail" />
            <el-option label="部分合格" value="partial" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="updateForm.remark" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="updateDialogVisible = false">取消</el-button>
        <el-button
          type="primary"
          :disabled="!canUpdate"
          :loading="actionSubmitting && activeAction === 'update'"
          data-write-guard="local_dev:quality-detail-update-submit"
          data-guard-state="enabled_local_dev"
          @click="submitUpdate"
        >
          保存
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="defectDialogVisible" title="录入缺陷" width="560px" destroy-on-close>
      <el-form label-width="120px">
        <el-form-item label="scenario_tag">
          <el-input v-model="defectForm.scenario_tag" />
        </el-form-item>
        <el-form-item label="idempotency_key">
          <el-input v-model="defectForm.idempotency_key" />
        </el-form-item>
        <el-form-item label="request_id">
          <el-input v-model="defectForm.request_id" readonly />
        </el-form-item>
        <el-form-item label="缺陷编码">
          <el-input v-model="defectForm.defect_code" />
        </el-form-item>
        <el-form-item label="缺陷名称">
          <el-input v-model="defectForm.defect_name" />
        </el-form-item>
        <el-form-item label="缺陷数量">
          <el-input v-model="defectForm.defect_qty" />
        </el-form-item>
        <el-form-item label="严重度">
          <el-select v-model="defectForm.severity" style="width: 100%">
            <el-option label="轻微" value="minor" />
            <el-option label="主要" value="major" />
            <el-option label="严重" value="critical" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="defectForm.remark" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="defectDialogVisible = false">取消</el-button>
        <el-button
          type="primary"
          :disabled="!canUpdate"
          :loading="actionSubmitting && activeAction === 'defects'"
          data-write-guard="local_dev:quality-detail-defects-submit"
          data-guard-state="enabled_local_dev"
          @click="submitDefect"
        >
          保存
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="confirmDialogVisible" title="确认检验单" width="520px" destroy-on-close>
      <el-form label-width="120px">
        <el-form-item label="scenario_tag">
          <el-input v-model="confirmForm.scenario_tag" />
        </el-form-item>
        <el-form-item label="idempotency_key">
          <el-input v-model="confirmForm.idempotency_key" />
        </el-form-item>
        <el-form-item label="request_id">
          <el-input v-model="confirmForm.request_id" readonly />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="confirmForm.remark" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="confirmDialogVisible = false">取消</el-button>
        <el-button
          type="success"
          :disabled="!canConfirm"
          :loading="actionSubmitting && activeAction === 'confirm'"
          data-write-guard="local_dev:quality-detail-confirm-submit"
          data-guard-state="enabled_local_dev"
          @click="submitConfirm"
        >
          确认
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="cancelDialogVisible" title="取消检验单" width="520px" destroy-on-close>
      <el-form label-width="120px">
        <el-form-item label="scenario_tag">
          <el-input v-model="cancelForm.scenario_tag" />
        </el-form-item>
        <el-form-item label="idempotency_key">
          <el-input v-model="cancelForm.idempotency_key" />
        </el-form-item>
        <el-form-item label="request_id">
          <el-input v-model="cancelForm.request_id" readonly />
        </el-form-item>
        <el-form-item label="取消原因">
          <el-input v-model="cancelForm.reason" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="cancelDialogVisible = false">返回</el-button>
        <el-button
          type="danger"
          :disabled="!canCancel"
          :loading="actionSubmitting && activeAction === 'cancel'"
          data-write-guard="local_dev:quality-detail-cancel-submit"
          data-guard-state="enabled_local_dev"
          @click="submitCancel"
        >
          确认取消
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  addDefectRecord,
  buildQualityInspectionRequestId,
  cancelQualityInspection,
  confirmQualityInspection,
  ensureQualityInspectionScenarioTag,
  extractQualityInspectionScenarioTag,
  fetchQualityInspectionDetail,
  updateDraftInspection,
  type QualityInspectionCancelPayload,
  type QualityInspectionConfirmPayload,
  type QualityInspectionDefectCreatePayload,
  type QualityInspectionDetailData,
  type QualityInspectionUpdatePayload,
  type QualityOutboxStatusData,
} from '@/api/quality'
import { usePermissionStore } from '@/stores/permission'

const route = useRoute()
const router = useRouter()
const permissionStore = usePermissionStore()

const loading = ref<boolean>(false)
const detail = ref<QualityInspectionDetailData | null>(null)
const outboxStatus = ref<QualityOutboxStatusData | null>(null)
const loadError = ref<string>('')
const actionFeedback = ref<string>('')
const actionSubmitting = ref<boolean>(false)
const activeAction = ref<'update' | 'defects' | 'confirm' | 'cancel' | null>(null)
const updateDialogVisible = ref<boolean>(false)
const defectDialogVisible = ref<boolean>(false)
const confirmDialogVisible = ref<boolean>(false)
const cancelDialogVisible = ref<boolean>(false)

interface QualityCarrierForm {
  scenario_tag: string
  idempotency_key: string
  request_id: string
  source_ref: string
  inspection_ref: string
  source_type: string
  item_code: string
  result: string
}

const updateForm = reactive<QualityCarrierForm & {
  inspection_date: string
  inspected_qty: string
  accepted_qty: string
  rejected_qty: string
  defect_qty: string
  remark: string
}>({
  scenario_tag: '',
  idempotency_key: '',
  request_id: '',
  source_ref: '',
  inspection_ref: '',
  source_type: '',
  item_code: '',
  result: '',
  inspection_date: '',
  inspected_qty: '',
  accepted_qty: '',
  rejected_qty: '',
  defect_qty: '',
  remark: '',
})

const defectForm = reactive<QualityCarrierForm & {
  defect_code: string
  defect_name: string
  defect_qty: string
  severity: 'minor' | 'major' | 'critical'
  remark: string
}>({
  scenario_tag: '',
  idempotency_key: '',
  request_id: '',
  source_ref: '',
  inspection_ref: '',
  source_type: '',
  item_code: '',
  result: '',
  defect_code: 'DEFECT-Z003',
  defect_name: '样例缺陷',
  defect_qty: '1',
  severity: 'minor',
  remark: '',
})

const confirmForm = reactive<QualityCarrierForm & { remark: string }>({
  scenario_tag: '',
  idempotency_key: '',
  request_id: '',
  source_ref: '',
  inspection_ref: '',
  source_type: '',
  item_code: '',
  result: '',
  remark: '',
})

const cancelForm = reactive<QualityCarrierForm & { reason: string }>({
  scenario_tag: '',
  idempotency_key: '',
  request_id: '',
  source_ref: '',
  inspection_ref: '',
  source_type: '',
  item_code: '',
  result: '',
  reason: '',
})

const inspectionId = computed<number>(() => Number(route.query.id || '0'))
const canRead = computed<boolean>(() => permissionStore.state.buttonPermissions.quality_read)
const canUpdatePermission = computed<boolean>(() => permissionStore.state.buttonPermissions.quality_update)
const canConfirmPermission = computed<boolean>(() => permissionStore.state.buttonPermissions.quality_confirm)
const canCancelPermission = computed<boolean>(() => permissionStore.state.buttonPermissions.quality_cancel)
const canUpdate = computed<boolean>(() => canUpdatePermission.value && detail.value?.status === 'draft')
const canConfirm = computed<boolean>(() => canConfirmPermission.value && detail.value?.status === 'draft')
const canCancel = computed<boolean>(() => canCancelPermission.value && detail.value?.status === 'confirmed')
const qualityDetailParity = computed<string>(() => {
  const parity = String(route.query.parity || 'quality-inspections-detail').trim()
  return parity || 'quality-inspections-detail'
})

const permissionStateText = computed<string>(() => {
  if (!canRead.value) return '当前账号缺少质量检验详情读取权限。'
  return '当前为本地 development 写闭环验证阶段；写请求仍受 local-dev gate、request_id carrier 与状态机 fail-closed 保护。'
})

const formatAmount = (value: string | number | null | undefined): string => {
  if (value === null || value === undefined || value === '') return '-'
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric.toFixed(2) : String(value)
}

const formatRate = (value: string | number | null | undefined): string => {
  if (value === null || value === undefined || value === '') return '-'
  const numeric = Number(value)
  return Number.isFinite(numeric) ? `${(numeric * 100).toFixed(2)}%` : String(value)
}

const sourceTypeLabel = (value: string): string => {
  if (value === 'incoming_material') return '来料检验'
  if (value === 'subcontract_receipt') return '外发收货检验'
  if (value === 'finished_goods') return '成品检验'
  if (value === 'manual') return '手工检验'
  return value || '-'
}

const resultLabel = (value: string): string => {
  if (value === 'pending') return '待定'
  if (value === 'pass') return '合格'
  if (value === 'fail') return '不合格'
  if (value === 'partial') return '部分合格'
  return value || '-'
}

const statusLabel = (value: string): string => {
  if (value === 'draft') return '草稿'
  if (value === 'confirmed') return '已确认'
  if (value === 'cancelled') return '已取消'
  return value || '-'
}

const resultTag = (value: string): 'success' | 'danger' | 'warning' | 'info' => {
  if (value === 'pass') return 'success'
  if (value === 'fail') return 'danger'
  if (value === 'partial') return 'warning'
  return 'info'
}

const statusTag = (value: string): 'success' | 'danger' | 'warning' | 'info' => {
  if (value === 'draft') return 'warning'
  if (value === 'confirmed') return 'success'
  if (value === 'cancelled') return 'danger'
  return 'info'
}

const cleanText = (value: string | null | undefined): string | null => {
  const normalized = (value || '').trim()
  return normalized ? normalized : null
}

const toFiniteNumber = (value: string, fieldLabel: string): number => {
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) {
    throw new Error(`${fieldLabel}格式非法`)
  }
  return numeric
}

const buildActionIdempotencyKey = (scenarioTag: string, operation: string): string => {
  const randomPart = Math.random().toString(36).slice(2, 8).toUpperCase()
  return `${scenarioTag}-${operation.toUpperCase()}-${randomPart}`
}

const buildCarrierForm = (
  operation: 'update' | 'defects' | 'confirm' | 'cancel',
  result: string,
): QualityCarrierForm => {
  if (!detail.value) {
    throw new Error('检验单详情不存在')
  }
  const sourceRef = (detail.value.source_id || '').trim()
  if (!sourceRef) {
    throw new Error('source_ref 缺失，无法构造受控写请求')
  }
  const extractedScenarioTag = extractQualityInspectionScenarioTag(sourceRef)
  if (!extractedScenarioTag) {
    throw new Error('source_ref 未包含 Z003 scenario_tag，无法构造受控写请求')
  }
  const scenarioTag = ensureQualityInspectionScenarioTag(extractedScenarioTag)
  const idempotencyKey = buildActionIdempotencyKey(scenarioTag, operation)
  const inspectionRef = String(detail.value.id || detail.value.inspection_no)
  const sourceType = String(detail.value.source_type || '').trim()
  const itemCode = String(detail.value.item_code || '').trim()
  if (!sourceType || !itemCode) {
    throw new Error('source_type 或 item_code 缺失，无法构造受控写请求')
  }
  const requestId = buildQualityInspectionRequestId({
    scenarioTag,
    operation,
    idempotencyKey,
    sourceRef,
    inspectionRef,
    itemCode,
    result,
  })
  return {
    scenario_tag: scenarioTag,
    idempotency_key: idempotencyKey,
    request_id: requestId,
    source_ref: sourceRef,
    inspection_ref: inspectionRef,
    source_type: sourceType,
    item_code: itemCode,
    result,
  }
}

const refreshCarrierRequestId = (
  form: QualityCarrierForm,
  operation: 'update' | 'defects' | 'confirm' | 'cancel',
): void => {
  const scenarioTag = ensureQualityInspectionScenarioTag(form.scenario_tag)
  const idempotencyKey = form.idempotency_key.trim()
  const sourceRef = form.source_ref.trim()
  const inspectionRef = form.inspection_ref.trim()
  const itemCode = form.item_code.trim()
  const result = form.result.trim()
  if (!idempotencyKey || !sourceRef || !inspectionRef || !itemCode || !result) {
    throw new Error('carrier 字段缺失，无法刷新 request_id')
  }
  form.scenario_tag = scenarioTag
  form.request_id = buildQualityInspectionRequestId({
    scenarioTag,
    operation,
    idempotencyKey,
    sourceRef,
    inspectionRef,
    itemCode,
    result,
  })
}

const loadOutboxStatus = async (): Promise<void> => {
  outboxStatus.value = null
}

const loadDetail = async (): Promise<void> => {
  actionFeedback.value = ''
  loadError.value = ''
  if (!canRead.value || !inspectionId.value) {
    detail.value = null
    outboxStatus.value = null
    return
  }
  loading.value = true
  try {
    const result = await fetchQualityInspectionDetail(inspectionId.value)
    detail.value = result.data
    await loadOutboxStatus()
  } catch (error) {
    detail.value = null
    outboxStatus.value = null
    const message = (error as Error).message || '详情加载失败'
    loadError.value = `检验详情加载失败：${message}`
    ElMessage.error(loadError.value)
  } finally {
    loading.value = false
  }
}

const openUpdateDialog = (): void => {
  if (!detail.value || !canUpdate.value) {
    ElMessage.error('当前状态不允许编辑草稿')
    return
  }
  try {
    Object.assign(updateForm, buildCarrierForm('update', detail.value.result), {
      inspection_date: detail.value.inspection_date,
      inspected_qty: String(detail.value.inspected_qty ?? ''),
      accepted_qty: String(detail.value.accepted_qty ?? ''),
      rejected_qty: String(detail.value.rejected_qty ?? ''),
      defect_qty: String(detail.value.defect_qty ?? ''),
      remark: detail.value.remark || '',
    })
    updateDialogVisible.value = true
  } catch (error) {
    ElMessage.error((error as Error).message)
  }
}

const openDefectDialog = (): void => {
  if (!detail.value || !canUpdate.value) {
    ElMessage.error('当前状态不允许录入缺陷')
    return
  }
  try {
    Object.assign(defectForm, buildCarrierForm('defects', detail.value.result), {
      defect_code: 'DEFECT-Z003',
      defect_name: '样例缺陷',
      defect_qty: '1',
      severity: 'minor',
      remark: '',
    })
    defectDialogVisible.value = true
  } catch (error) {
    ElMessage.error((error as Error).message)
  }
}

const openConfirmDialog = (): void => {
  if (!detail.value || !canConfirm.value) {
    ElMessage.error('当前状态不允许确认检验单')
    return
  }
  try {
    Object.assign(confirmForm, buildCarrierForm('confirm', detail.value.result), {
      remark: '',
    })
    confirmDialogVisible.value = true
  } catch (error) {
    ElMessage.error((error as Error).message)
  }
}

const openCancelDialog = (): void => {
  if (!detail.value || !canCancel.value) {
    ElMessage.error('当前状态不允许取消检验单')
    return
  }
  try {
    Object.assign(cancelForm, buildCarrierForm('cancel', detail.value.result), {
      reason: '',
    })
    cancelDialogVisible.value = true
  } catch (error) {
    ElMessage.error((error as Error).message)
  }
}

const submitUpdate = async (): Promise<void> => {
  if (!detail.value || !inspectionId.value) {
    return
  }
  const inspectedQty = toFiniteNumber(updateForm.inspected_qty, '检验数量')
  const acceptedQty = toFiniteNumber(updateForm.accepted_qty, '合格数量')
  const rejectedQty = toFiniteNumber(updateForm.rejected_qty, '不合格数量')
  const defectQty = toFiniteNumber(updateForm.defect_qty, '缺陷数量')
  if (inspectedQty <= 0) {
    ElMessage.error('检验数量必须大于 0')
    return
  }
  if (Math.abs(acceptedQty + rejectedQty - inspectedQty) > 0.000001) {
    ElMessage.error('合格数量 + 不合格数量必须等于检验数量')
    return
  }
  if (defectQty > inspectedQty) {
    ElMessage.error('缺陷数量不能超过检验数量')
    return
  }
  actionSubmitting.value = true
  activeAction.value = 'update'
  try {
    refreshCarrierRequestId(updateForm, 'update')
    const payload: QualityInspectionUpdatePayload = {
      request_id: updateForm.request_id,
      idempotency_key: updateForm.idempotency_key,
      scenario_tag: updateForm.scenario_tag,
      source_ref: updateForm.source_ref,
      inspection_ref: updateForm.inspection_ref,
      source_type: updateForm.source_type,
      source_doc: updateForm.source_ref,
      item_code: updateForm.item_code,
      operation: 'update',
      result: updateForm.result,
      supplier: cleanText(detail.value?.supplier),
      warehouse: cleanText(detail.value?.warehouse),
      work_order: cleanText(detail.value?.work_order),
      sales_order: cleanText(detail.value?.sales_order),
      inspection_date: updateForm.inspection_date,
      inspected_qty: inspectedQty,
      accepted_qty: acceptedQty,
      rejected_qty: rejectedQty,
      defect_qty: defectQty,
      remark: cleanText(updateForm.remark),
    }
    await updateDraftInspection(inspectionId.value, payload)
    updateDialogVisible.value = false
    ElMessage.success('草稿更新成功')
    await loadDetail()
  } catch (error) {
    actionFeedback.value = (error as Error).message
    ElMessage.error(actionFeedback.value)
  } finally {
    actionSubmitting.value = false
    activeAction.value = null
  }
}

const submitDefect = async (): Promise<void> => {
  if (!detail.value || !inspectionId.value) {
    return
  }
  const defectQty = toFiniteNumber(defectForm.defect_qty, '缺陷数量')
  if (defectQty <= 0) {
    ElMessage.error('缺陷数量必须大于 0')
    return
  }
  if (!defectForm.defect_code.trim() || !defectForm.defect_name.trim()) {
    ElMessage.error('缺陷编码与缺陷名称不能为空')
    return
  }
  actionSubmitting.value = true
  activeAction.value = 'defects'
  try {
    refreshCarrierRequestId(defectForm, 'defects')
    const payload: QualityInspectionDefectCreatePayload = {
      request_id: defectForm.request_id,
      idempotency_key: defectForm.idempotency_key,
      scenario_tag: defectForm.scenario_tag,
      source_ref: defectForm.source_ref,
      inspection_ref: defectForm.inspection_ref,
      source_type: defectForm.source_type,
      source_doc: defectForm.source_ref,
      item_code: defectForm.item_code,
      operation: 'defects',
      result: defectForm.result,
      defects: [
        {
          defect_code: defectForm.defect_code.trim(),
          defect_name: defectForm.defect_name.trim(),
          defect_qty: defectQty,
          severity: defectForm.severity,
          remark: cleanText(defectForm.remark),
        },
      ],
    }
    await addDefectRecord(inspectionId.value, payload)
    defectDialogVisible.value = false
    ElMessage.success('缺陷录入成功')
    await loadDetail()
  } catch (error) {
    actionFeedback.value = (error as Error).message
    ElMessage.error(actionFeedback.value)
  } finally {
    actionSubmitting.value = false
    activeAction.value = null
  }
}

const submitConfirm = async (): Promise<void> => {
  if (!detail.value || !inspectionId.value) {
    return
  }
  actionSubmitting.value = true
  activeAction.value = 'confirm'
  try {
    refreshCarrierRequestId(confirmForm, 'confirm')
    const payload: QualityInspectionConfirmPayload = {
      request_id: confirmForm.request_id,
      idempotency_key: confirmForm.idempotency_key,
      scenario_tag: confirmForm.scenario_tag,
      source_ref: confirmForm.source_ref,
      inspection_ref: confirmForm.inspection_ref,
      source_type: confirmForm.source_type,
      source_doc: confirmForm.source_ref,
      item_code: confirmForm.item_code,
      operation: 'confirm',
      result: confirmForm.result,
      remark: cleanText(confirmForm.remark),
    }
    await confirmQualityInspection(inspectionId.value, payload)
    confirmDialogVisible.value = false
    ElMessage.success('检验单已确认')
    await loadDetail()
  } catch (error) {
    actionFeedback.value = (error as Error).message
    ElMessage.error(actionFeedback.value)
  } finally {
    actionSubmitting.value = false
    activeAction.value = null
  }
}

const submitCancel = async (): Promise<void> => {
  if (!detail.value || !inspectionId.value) {
    return
  }
  actionSubmitting.value = true
  activeAction.value = 'cancel'
  try {
    refreshCarrierRequestId(cancelForm, 'cancel')
    const payload: QualityInspectionCancelPayload = {
      request_id: cancelForm.request_id,
      idempotency_key: cancelForm.idempotency_key,
      scenario_tag: cancelForm.scenario_tag,
      source_ref: cancelForm.source_ref,
      inspection_ref: cancelForm.inspection_ref,
      source_type: cancelForm.source_type,
      source_doc: cancelForm.source_ref,
      item_code: cancelForm.item_code,
      operation: 'cancel',
      result: cancelForm.result,
      reason: cleanText(cancelForm.reason),
    }
    await cancelQualityInspection(inspectionId.value, payload)
    cancelDialogVisible.value = false
    ElMessage.success('检验单已取消')
    await loadDetail()
  } catch (error) {
    actionFeedback.value = (error as Error).message
    ElMessage.error(actionFeedback.value)
  } finally {
    actionSubmitting.value = false
    activeAction.value = null
  }
}

const backToList = (): void => {
  router.push({ path: '/quality/inspections', query: { parity: qualityDetailParity.value } })
}

onMounted(async () => {
  actionFeedback.value = ''
  try {
    await permissionStore.loadCurrentUser()
    await permissionStore.loadModuleActions('quality')
  } catch (error) {
    loadError.value = (error as Error).message || '权限加载失败'
    ElMessage.error(loadError.value)
    return
  }
  await loadDetail()
  if (String(route.query.from || '') === 'create' && detail.value) {
    actionFeedback.value = '已从创建入口进入详情页，请继续执行缺陷录入、确认与取消闭环。'
  }
})
</script>

<style scoped>
.quality-detail-page {
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
  margin-top: 16px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.outbox-alert {
  margin-top: 12px;
}

.permission-tip {
  margin: 12px 0 0;
  color: #909399;
  font-size: 12px;
}
</style>
