<template>
  <div class="factory-statement-detail-page">
    <el-card shadow="never" v-loading="loading">
      <template #header>
        <div class="header-row">
          <span>加工厂对账单详情</span>
          <el-button @click="goBack">返回列表</el-button>
        </div>
      </template>

      <el-empty v-if="!canRead" description="无加工厂对账单查看权限" />
      <template v-else>
        <el-empty v-if="!detail" description="未找到对账单数据" />
        <template v-else>
          <el-descriptions :column="3" border>
            <el-descriptions-item label="对账单号">{{ detail.statement_no }}</el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="statusTag(detail.statement_status)">
                {{ statementStatusLabel(detail.statement_status) }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="供应商">{{ detail.supplier }}</el-descriptions-item>
            <el-descriptions-item label="公司">{{ detail.company }}</el-descriptions-item>
            <el-descriptions-item label="期间">{{ detail.from_date }} ~ {{ detail.to_date }}</el-descriptions-item>
            <el-descriptions-item label="来源条数">{{ detail.source_count }}</el-descriptions-item>
            <el-descriptions-item label="加工费">{{ formatAmount(detail.gross_amount) }}</el-descriptions-item>
            <el-descriptions-item label="扣款">{{ formatAmount(detail.deduction_amount) }}</el-descriptions-item>
            <el-descriptions-item label="实付金额">{{ formatAmount(detail.net_amount) }}</el-descriptions-item>
            <el-descriptions-item label="验货总数">{{ formatAmount(detail.inspected_qty) }}</el-descriptions-item>
            <el-descriptions-item label="次品总数">{{ formatAmount(detail.rejected_qty) }}</el-descriptions-item>
            <el-descriptions-item label="次品率">{{ formatRate(detail.rejected_rate) }}</el-descriptions-item>
            <el-descriptions-item label="应付草稿同步">
              {{ outboxStatusLabel(effectiveOutboxStatus) }}
            </el-descriptions-item>
            <el-descriptions-item label="ERP 发票草稿">
              {{ detail.purchase_invoice_name || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="创建时间">{{ detail.created_at }}</el-descriptions-item>
          </el-descriptions>

          <el-alert
            v-if="hasActivePayableOutbox"
            type="warning"
            :closable="false"
            show-icon
            title="当前存在应付草稿同步流程，暂不可取消对账单。"
            class="warn-alert"
          />
          <el-alert
            v-if="summaryMissing"
            type="warning"
            :closable="false"
            show-icon
            title="应付摘要缺失，按钮已按 fail-closed 策略禁用。"
            class="warn-alert"
          />

          <div class="action-row">
            <el-button
              v-if="canConfirm"
              type="primary"
              :loading="confirming"
              @click="openConfirmDialog"
            >
              确认对账单
            </el-button>
            <el-button
              v-if="canCancel || (canCancelPermission && isDraftOrConfirmed)"
              type="danger"
              :disabled="!canCancel"
              :loading="cancelling"
              @click="openCancelDialog"
            >
              取消对账单
            </el-button>
            <el-button
              v-if="canCreatePayableDraft"
              type="success"
              :loading="creatingPayable"
              @click="openPayableDialog"
            >
              生成应付草稿
            </el-button>
            <el-button type="info" plain :disabled="loading || !detail" @click="openPrintView">
              打印
            </el-button>
            <el-button type="info" plain :disabled="loading || !detail" @click="exportDetailCsv">
              导出明细 CSV
            </el-button>
          </div>
        </template>
      </template>
    </el-card>

    <el-card shadow="never">
      <template #header>
        <span>对账明细</span>
      </template>
      <el-table :data="items" border>
        <el-table-column prop="line_no" label="行号" width="70" />
        <el-table-column prop="inspection_no" label="验货单号" min-width="150" />
        <el-table-column prop="subcontract_no" label="外发单号" min-width="150" />
        <el-table-column prop="item_code" label="款式" min-width="120" />
        <el-table-column label="验货数量" width="110">
          <template #default="scope">{{ formatAmount(scope.row.inspected_qty) }}</template>
        </el-table-column>
        <el-table-column label="次品数量" width="110">
          <template #default="scope">{{ formatAmount(scope.row.rejected_qty) }}</template>
        </el-table-column>
        <el-table-column label="合格数量" width="110">
          <template #default="scope">{{ formatAmount(scope.row.accepted_qty) }}</template>
        </el-table-column>
        <el-table-column label="加工费" width="130">
          <template #default="scope">{{ formatAmount(scope.row.gross_amount) }}</template>
        </el-table-column>
        <el-table-column label="扣款" width="130">
          <template #default="scope">{{ formatAmount(scope.row.deduction_amount) }}</template>
        </el-table-column>
        <el-table-column label="实付" width="130">
          <template #default="scope">{{ formatAmount(scope.row.net_amount) }}</template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card shadow="never">
      <template #header>
        <span>操作日志</span>
      </template>
      <el-table :data="logs" border>
        <el-table-column prop="action" label="动作" min-width="120" />
        <el-table-column prop="from_status" label="原状态" min-width="120" />
        <el-table-column prop="to_status" label="新状态" min-width="120" />
        <el-table-column prop="operator" label="操作人" min-width="120" />
        <el-table-column prop="remark" label="备注" min-width="180" />
        <el-table-column prop="operated_at" label="时间" min-width="180" />
      </el-table>
    </el-card>

    <el-dialog v-model="confirmDialogVisible" title="确认对账单" width="480px" destroy-on-close>
      <el-form :model="confirmForm" label-width="120px">
        <el-form-item label="幂等键" required>
          <el-input v-model="confirmForm.idempotency_key" clearable placeholder="idempotency_key" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="confirmForm.remark" type="textarea" :rows="3" maxlength="200" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="confirmDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="confirming" @click="submitConfirm">确认</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="cancelDialogVisible" title="取消对账单" width="480px" destroy-on-close>
      <el-form :model="cancelForm" label-width="120px">
        <el-form-item label="幂等键" required>
          <el-input v-model="cancelForm.idempotency_key" clearable placeholder="idempotency_key" />
        </el-form-item>
        <el-form-item label="取消原因">
          <el-input v-model="cancelForm.reason" type="textarea" :rows="3" maxlength="200" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="cancelDialogVisible = false">返回</el-button>
        <el-button type="danger" :loading="cancelling" @click="submitCancel">确认取消</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="payableDialogVisible" title="生成应付草稿" width="560px" destroy-on-close>
      <el-form :model="payableForm" label-width="120px">
        <el-form-item label="应付科目" required>
          <el-input v-model="payableForm.payable_account" clearable placeholder="payable_account" />
        </el-form-item>
        <el-form-item label="成本中心" required>
          <el-input v-model="payableForm.cost_center" clearable placeholder="cost_center" />
        </el-form-item>
        <el-form-item label="过账日期" required>
          <el-date-picker
            v-model="payableForm.posting_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="posting_date"
            clearable
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="幂等键" required>
          <el-input v-model="payableForm.idempotency_key" clearable placeholder="idempotency_key" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="payableForm.remark" type="textarea" :rows="3" maxlength="200" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="payableDialogVisible = false">取消</el-button>
        <el-button type="success" :loading="creatingPayable" @click="submitPayableDraft">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  cancelFactoryStatement,
  confirmFactoryStatement,
  createFactoryStatementPayableDraft,
  fetchFactoryStatementDetail,
  type FactoryStatementDetailData,
  type FactoryStatementDetailItem,
  type FactoryStatementLogItem,
} from '@/api/factory_statement'
import { exportFactoryStatementDetailCsv } from '@/utils/factoryStatementExport'
import { usePermissionStore } from '@/stores/permission'

const ACTIVE_PAYABLE_OUTBOX_STATUS = new Set(['pending', 'processing', 'succeeded'])

const route = useRoute()
const router = useRouter()
const permissionStore = usePermissionStore()

const loading = ref<boolean>(false)
const confirming = ref<boolean>(false)
const cancelling = ref<boolean>(false)
const creatingPayable = ref<boolean>(false)

const detail = ref<FactoryStatementDetailData | null>(null)
const items = ref<FactoryStatementDetailItem[]>([])
const logs = ref<FactoryStatementLogItem[]>([])

const confirmDialogVisible = ref<boolean>(false)
const cancelDialogVisible = ref<boolean>(false)
const payableDialogVisible = ref<boolean>(false)

const confirmForm = ref({ idempotency_key: '', remark: '' })
const cancelForm = ref({ idempotency_key: '', reason: '' })
const payableForm = ref({
  payable_account: '',
  cost_center: '',
  posting_date: '',
  idempotency_key: '',
  remark: '',
})

const canRead = computed<boolean>(() => permissionStore.state.buttonPermissions.factory_statement_read)
const canConfirmPermission = computed<boolean>(() => permissionStore.state.buttonPermissions.factory_statement_confirm)
const canCancelPermission = computed<boolean>(() => permissionStore.state.buttonPermissions.factory_statement_cancel)
const canPayablePermission = computed<boolean>(
  () => permissionStore.state.buttonPermissions.factory_statement_payable_draft_create,
)

const statementId = computed<number>(() => Number(route.query.id || '0'))
const statementStatus = computed<string>(() => detail.value?.statement_status || '')

const hasPayableSummary = computed<boolean>(
  () => detail.value?.payable_outbox_status !== undefined && detail.value?.purchase_invoice_name !== undefined,
)
const summaryMissing = computed<boolean>(() => Boolean(detail.value) && !hasPayableSummary.value)

const effectiveOutboxStatus = computed<string>(() => {
  if (!hasPayableSummary.value) {
    return '__unknown__'
  }
  const directStatus = detail.value?.payable_outbox_status
  if (directStatus) {
    return directStatus
  }
  return ''
})

const hasActivePayableOutbox = computed<boolean>(
  () => !hasPayableSummary.value || ACTIVE_PAYABLE_OUTBOX_STATUS.has(effectiveOutboxStatus.value),
)
const isDraftOrConfirmed = computed<boolean>(
  () => statementStatus.value === 'draft' || statementStatus.value === 'confirmed',
)

const canConfirm = computed<boolean>(() => canConfirmPermission.value && statementStatus.value === 'draft')
const canCancel = computed<boolean>(
  () => canCancelPermission.value && isDraftOrConfirmed.value && hasPayableSummary.value && !hasActivePayableOutbox.value,
)
const canCreatePayableDraft = computed<boolean>(
  () =>
    canPayablePermission.value &&
    statementStatus.value === 'confirmed' &&
    hasPayableSummary.value &&
    !hasActivePayableOutbox.value,
)

const formatAmount = (value: string | number | null | undefined): string => {
  if (value === null || value === undefined || value === '') {
    return '-'
  }
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric.toFixed(2) : String(value)
}

const formatRate = (value: string | number | null | undefined): string => {
  if (value === null || value === undefined || value === '') {
    return '-'
  }
  const numeric = Number(value)
  return Number.isFinite(numeric) ? `${(numeric * 100).toFixed(2)}%` : String(value)
}

const statementStatusLabel = (status: string | null | undefined): string => {
  if (status === 'draft') {
    return '草稿'
  }
  if (status === 'confirmed') {
    return '已确认'
  }
  if (status === 'cancelled') {
    return '已取消'
  }
  if (status === 'payable_draft_created') {
    return '应付草稿已生成'
  }
  return status || '-'
}

const outboxStatusLabel = (status: string | null | undefined): string => {
  if (status === 'pending') {
    return '待同步'
  }
  if (status === 'processing') {
    return '同步中'
  }
  if (status === 'succeeded') {
    return '已生成草稿'
  }
  if (status === 'failed') {
    return '同步失败'
  }
  if (status === 'dead') {
    return '同步死信'
  }
  if (status === '__unknown__') {
    return '摘要缺失'
  }
  return '-'
}

const statusTag = (status: string | null | undefined): 'warning' | 'success' | 'danger' | 'info' => {
  if (status === 'draft') {
    return 'warning'
  }
  if (status === 'confirmed') {
    return 'success'
  }
  if (status === 'cancelled') {
    return 'danger'
  }
  return 'info'
}

const goBack = (): void => {
  router.push({ path: '/factory-statements/list' })
}

const openPrintView = (): void => {
  if (!detail.value) {
    ElMessage.warning('暂无可打印数据')
    return
  }
  router.push({ path: '/factory-statements/print', query: { id: String(statementId.value) } })
}

const exportDetailCsv = (): void => {
  if (!detail.value) {
    ElMessage.warning('暂无可导出数据')
    return
  }
  const filename = exportFactoryStatementDetailCsv(detail.value)
  ElMessage.success(`已导出：${filename}`)
}

const loadDetail = async (): Promise<void> => {
  if (!canRead.value) {
    detail.value = null
    items.value = []
    logs.value = []
    return
  }
  if (!Number.isInteger(statementId.value) || statementId.value <= 0) {
    ElMessage.warning('缺少有效 statement_id')
    return
  }

  loading.value = true
  try {
    const result = await fetchFactoryStatementDetail(statementId.value)
    detail.value = result.data
    items.value = result.data.items || []
    logs.value = result.data.logs || []
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    loading.value = false
  }
}

const resetConfirmForm = (): void => {
  confirmForm.value.idempotency_key = ''
  confirmForm.value.remark = ''
}

const resetCancelForm = (): void => {
  cancelForm.value.idempotency_key = ''
  cancelForm.value.reason = ''
}

const resetPayableForm = (): void => {
  payableForm.value.payable_account = ''
  payableForm.value.cost_center = ''
  payableForm.value.posting_date = ''
  payableForm.value.idempotency_key = ''
  payableForm.value.remark = ''
}

const openConfirmDialog = (): void => {
  resetConfirmForm()
  confirmDialogVisible.value = true
}

const openCancelDialog = (): void => {
  if (!canCancel.value) {
    ElMessage.warning('当前状态不可取消')
    return
  }
  resetCancelForm()
  cancelDialogVisible.value = true
}

const openPayableDialog = (): void => {
  resetPayableForm()
  payableDialogVisible.value = true
}

const submitConfirm = async (): Promise<void> => {
  if (!canConfirm.value) {
    ElMessage.warning('当前状态不可确认')
    return
  }
  const idempotencyKey = confirmForm.value.idempotency_key.trim()
  if (!idempotencyKey) {
    ElMessage.warning('idempotency_key 不能为空')
    return
  }

  confirming.value = true
  try {
    const result = await confirmFactoryStatement(statementId.value, {
      idempotency_key: idempotencyKey,
      remark: confirmForm.value.remark.trim() || undefined,
    })
    ElMessage.success(`确认成功：${result.data.statement_no}`)
    confirmDialogVisible.value = false
    await loadDetail()
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    confirming.value = false
  }
}

const submitCancel = async (): Promise<void> => {
  if (!canCancel.value) {
    ElMessage.warning('当前状态不可取消')
    return
  }
  const idempotencyKey = cancelForm.value.idempotency_key.trim()
  if (!idempotencyKey) {
    ElMessage.warning('idempotency_key 不能为空')
    return
  }

  cancelling.value = true
  try {
    const result = await cancelFactoryStatement(statementId.value, {
      idempotency_key: idempotencyKey,
      reason: cancelForm.value.reason.trim() || undefined,
    })
    ElMessage.success(`已取消：${result.data.statement_no}`)
    cancelDialogVisible.value = false
    await loadDetail()
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    cancelling.value = false
  }
}

const submitPayableDraft = async (): Promise<void> => {
  if (!canCreatePayableDraft.value) {
    ElMessage.warning('当前状态不可生成应付草稿')
    return
  }
  const payload = {
    payable_account: payableForm.value.payable_account.trim(),
    cost_center: payableForm.value.cost_center.trim(),
    posting_date: payableForm.value.posting_date,
    idempotency_key: payableForm.value.idempotency_key.trim(),
    remark: payableForm.value.remark.trim() || undefined,
  }
  if (!payload.payable_account || !payload.cost_center || !payload.posting_date || !payload.idempotency_key) {
    ElMessage.warning('请完整填写 payable_account/cost_center/posting_date/idempotency_key')
    return
  }

  creatingPayable.value = true
  try {
    const result = await createFactoryStatementPayableDraft(statementId.value, payload)
    ElMessage.success(`已创建应付草稿 outbox：${result.data.payable_outbox_id}`)
    payableDialogVisible.value = false
    await loadDetail()
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    creatingPayable.value = false
  }
}

onMounted(async () => {
  try {
    await permissionStore.loadCurrentUser()
    await permissionStore.loadModuleActions('factory_statement')
  } catch (error) {
    ElMessage.error((error as Error).message)
    return
  }
  await loadDetail()
})
</script>

<style scoped>
.factory-statement-detail-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.warn-alert {
  margin-top: 12px;
}

.action-row {
  margin-top: 12px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
</style>
