<template>
  <div class="subcontract-detail-page">
    <el-card shadow="never" v-loading="loading">
      <template #header>
        <div class="header-row">
          <span>外发单详情</span>
          <el-button @click="goBack">返回</el-button>
        </div>
      </template>
      <el-empty v-if="!canRead" description="无外发查看权限" />
      <template v-else>
        <el-descriptions v-if="detail" :column="3" border>
          <el-descriptions-item label="外发单号">{{ detail.subcontract_no }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag>{{ statusLabel(detail.status) }}</el-tag>
            <el-tag v-if="isScopeBlocked" type="danger" class="scope-tag">权限范围异常</el-tag>
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
            {{ stockSyncLabel(detail.latest_issue_sync_status) || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="回料同步状态">
            {{ stockSyncLabel(detail.latest_receipt_sync_status) || '-' }}
          </el-descriptions-item>
        </el-descriptions>
      </template>
    </el-card>

    <el-card v-if="canIssueAction" shadow="never">
      <template #header><span>发料登记</span></template>
      <el-form :model="issueForm" label-width="140px">
        <el-form-item label="幂等键">
          <el-input v-model="issueForm.idempotency_key" />
        </el-form-item>
        <el-form-item label="发料仓">
          <el-input v-model="issueForm.warehouse" />
        </el-form-item>
        <el-form-item label="物料编码">
          <el-input v-model="issueForm.material_item_code" placeholder="留空则按 BOM 自动展开" />
        </el-form-item>
        <el-form-item label="需求数量">
          <el-input-number v-model="issueForm.required_qty" :min="0" />
        </el-form-item>
        <el-form-item label="发料数量">
          <el-input-number v-model="issueForm.issued_qty" :min="0" />
        </el-form-item>
      </el-form>
      <el-button type="primary" :loading="issuing" @click="issueMaterial">提交发料</el-button>
    </el-card>

    <el-card v-if="canReceiveAction" shadow="never">
      <template #header><span>回料登记</span></template>
      <el-form :model="receiveForm" label-width="140px">
        <el-form-item label="幂等键">
          <el-input v-model="receiveForm.idempotency_key" />
        </el-form-item>
        <el-form-item label="回料仓">
          <el-input v-model="receiveForm.receipt_warehouse" />
        </el-form-item>
        <el-form-item label="回料数量">
          <el-input-number v-model="receiveForm.received_qty" :min="0" />
        </el-form-item>
        <el-form-item label="颜色">
          <el-input v-model="receiveForm.color" />
        </el-form-item>
        <el-form-item label="尺码">
          <el-input v-model="receiveForm.size" />
        </el-form-item>
        <el-form-item label="批次号">
          <el-input v-model="receiveForm.batch_no" />
        </el-form-item>
        <el-form-item label="单位">
          <el-input v-model="receiveForm.uom" />
        </el-form-item>
      </el-form>
      <el-button type="primary" :loading="receiving" @click="receive">登记回料</el-button>
    </el-card>

    <el-card v-if="canInspectAction" shadow="never">
      <template #header><span>验货登记</span></template>
      <el-form :model="inspectForm" label-width="160px">
        <el-form-item label="回料批次">
          <el-select v-model="inspectForm.receipt_batch_no" style="width: 280px">
            <el-option
              v-for="item in inspectableBatchOptions"
              :key="item.receipt_batch_no"
              :label="`${item.receipt_batch_no}（剩余可验 ${item.remaining_qty}）`"
              :value="item.receipt_batch_no"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="幂等键">
          <el-input v-model="inspectForm.idempotency_key" />
        </el-form-item>
        <el-form-item label="验货数量">
          <el-input-number v-model="inspectForm.inspected_qty" :min="0" />
        </el-form-item>
        <el-form-item label="不合格数量">
          <el-input-number v-model="inspectForm.rejected_qty" :min="0" />
        </el-form-item>
        <el-form-item label="单件扣款金额">
          <el-input-number v-model="inspectForm.deduction_amount_per_piece" :min="0" :step="0.1" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="inspectForm.remark" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <el-button type="success" :loading="inspecting" @click="inspect">完成验货</el-button>
    </el-card>

    <el-card v-if="canShowRetryCard" shadow="never">
      <template #header><span>库存同步重试</span></template>
      <div class="retry-actions">
        <el-button
          v-if="canRetryIssue"
          type="warning"
          :loading="retryingAction === 'issue'"
          @click="retrySync('issue')"
        >
          重试发料同步
        </el-button>
        <el-button
          v-if="canRetryReceipt"
          type="warning"
          :loading="retryingAction === 'receipt'"
          @click="retrySync('receipt')"
        >
          重试回料同步
        </el-button>
      </div>
    </el-card>

    <el-card shadow="never">
      <template #header><span>回料批次</span></template>
      <el-table :data="detail?.receipts || []" border>
        <el-table-column prop="receipt_batch_no" label="回料批次" min-width="160" />
        <el-table-column prop="receipt_warehouse" label="回料仓" min-width="120" />
        <el-table-column prop="received_qty" label="回料数量" width="120" />
        <el-table-column prop="sync_status" label="同步状态" width="120" />
        <el-table-column prop="stock_entry_name" label="Stock Entry" min-width="180" />
      </el-table>
    </el-card>

    <el-card shadow="never">
      <template #header><span>验货明细</span></template>
      <el-table :data="detail?.inspections || []" border>
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
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  fetchSubcontractOrderDetail,
  inspectSubcontract,
  issueSubcontractMaterial,
  receiveSubcontract,
  retrySubcontractStockSync,
  type SubcontractOrderDetailData,
} from '@/api/subcontract'
import { usePermissionStore } from '@/stores/permission'

interface InspectableBatchOption {
  receipt_batch_no: string
  remaining_qty: string
}

const route = useRoute()
const router = useRouter()
const permissionStore = usePermissionStore()
const detail = ref<SubcontractOrderDetailData | null>(null)
const loading = ref<boolean>(false)
const issuing = ref<boolean>(false)
const receiving = ref<boolean>(false)
const inspecting = ref<boolean>(false)
const retryingAction = ref<'issue' | 'receipt' | ''>('')

const canRead = computed<boolean>(() => permissionStore.state.buttonPermissions.read)
const canIssuePermission = computed<boolean>(() => permissionStore.state.buttonPermissions.issue_material)
const canReceivePermission = computed<boolean>(() => permissionStore.state.buttonPermissions.receive)
const canInspectPermission = computed<boolean>(() => permissionStore.state.buttonPermissions.inspect)
const canRetryPermission = computed<boolean>(() => permissionStore.state.buttonPermissions.stock_sync_retry)

const orderId = computed<number>(() => Number(route.query.id || '0'))
const currentStatus = computed<string>(() => detail.value?.status || '')
const isScopeBlocked = computed<boolean>(() => detail.value?.resource_scope_status === 'blocked_scope')
const isSettled = computed<boolean>(() => (detail.value?.settlement_status || '').toLowerCase() === 'settled')
const isTerminal = computed<boolean>(() => ['cancelled', 'completed'].includes(currentStatus.value))

const canIssueAction = computed<boolean>(() => {
  const allowedStatuses = new Set(['draft', 'issued', 'processing', 'waiting_receive'])
  return (
    canIssuePermission.value &&
    allowedStatuses.has(currentStatus.value) &&
    !isScopeBlocked.value &&
    !isSettled.value &&
    !isTerminal.value
  )
})

const canReceiveAction = computed<boolean>(() => {
  const allowedStatuses = new Set(['issued', 'processing', 'waiting_receive', 'waiting_inspection'])
  return (
    canReceivePermission.value &&
    allowedStatuses.has(currentStatus.value) &&
    !isScopeBlocked.value &&
    !isSettled.value &&
    !isTerminal.value
  )
})

const inspectableBatchOptions = computed<InspectableBatchOption[]>(() => {
  if (!detail.value) return []
  const inspectedByBatch = detail.value.inspections.reduce<Record<string, number>>((acc, item) => {
    const value = Number(item.inspected_qty || '0')
    acc[item.receipt_batch_no] = (acc[item.receipt_batch_no] || 0) + value
    return acc
  }, {})
  const receivedByBatch = detail.value.receipts.reduce<Record<string, number>>((acc, row) => {
    const synced = row.sync_status === 'succeeded' && !!(row.stock_entry_name || '').trim()
    if (!synced) return acc
    const value = Number(row.received_qty || '0')
    acc[row.receipt_batch_no] = (acc[row.receipt_batch_no] || 0) + value
    return acc
  }, {})
  return Object.entries(receivedByBatch)
    .map(([receipt_batch_no, received]) => {
      const inspected = inspectedByBatch[receipt_batch_no] || 0
      const remaining = received - inspected
      return { receipt_batch_no, remaining_qty: String(Number(remaining.toFixed(6))) }
    })
    .filter((row) => Number(row.remaining_qty) > 0)
    .sort((a, b) => a.receipt_batch_no.localeCompare(b.receipt_batch_no))
})

const canInspectAction = computed<boolean>(() => {
  const allowedStatuses = new Set(['waiting_inspection', 'waiting_receive'])
  return (
    canInspectPermission.value &&
    allowedStatuses.has(currentStatus.value) &&
    !isScopeBlocked.value &&
    !isSettled.value &&
    !isTerminal.value &&
    inspectableBatchOptions.value.length > 0
  )
})

const canRetryIssue = computed<boolean>(() => {
  const status = detail.value?.latest_issue_sync_status || ''
  return (
    canRetryPermission.value &&
    !isScopeBlocked.value &&
    !isSettled.value &&
    ['failed', 'dead'].includes(status) &&
    !!detail.value?.latest_issue_outbox_id &&
    !!(detail.value?.latest_issue_idempotency_key || '').trim()
  )
})

const canRetryReceipt = computed<boolean>(() => {
  const status = detail.value?.latest_receipt_sync_status || ''
  return (
    canRetryPermission.value &&
    !isScopeBlocked.value &&
    !isSettled.value &&
    ['failed', 'dead'].includes(status) &&
    !!detail.value?.latest_receipt_outbox_id &&
    !!(detail.value?.latest_receipt_idempotency_key || '').trim()
  )
})

const canShowRetryCard = computed<boolean>(() => canRetryIssue.value || canRetryReceipt.value)

const issueForm = reactive({
  idempotency_key: '',
  warehouse: '成品仓',
  material_item_code: '',
  required_qty: 0,
  issued_qty: 0,
})

const receiveForm = reactive({
  idempotency_key: '',
  receipt_warehouse: '成品仓',
  received_qty: 0,
  color: '',
  size: '',
  batch_no: '',
  uom: 'Nos',
})

const inspectForm = reactive({
  receipt_batch_no: '',
  idempotency_key: '',
  inspected_qty: 0,
  rejected_qty: 0,
  deduction_amount_per_piece: 0,
  remark: '',
})

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

const buildKey = (prefix: string): string => `${prefix}-${Date.now()}`

const resetActionForms = (): void => {
  issueForm.idempotency_key = buildKey('issue')
  receiveForm.idempotency_key = buildKey('receive')
  inspectForm.idempotency_key = buildKey('inspect')
}

const ensureOrderId = (): number => {
  if (!orderId.value || Number.isNaN(orderId.value)) {
    throw new Error('无效的外发单 ID')
  }
  return orderId.value
}

const loadDetail = async (): Promise<void> => {
  if (!canRead.value) {
    detail.value = null
    return
  }
  loading.value = true
  try {
    const id = ensureOrderId()
    const result = await fetchSubcontractOrderDetail(id)
    detail.value = result.data
    if (!inspectForm.receipt_batch_no || !inspectableBatchOptions.value.some((x) => x.receipt_batch_no === inspectForm.receipt_batch_no)) {
      inspectForm.receipt_batch_no = inspectableBatchOptions.value[0]?.receipt_batch_no || ''
    }
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    loading.value = false
  }
}

const issueMaterial = async (): Promise<void> => {
  issuing.value = true
  try {
    const id = ensureOrderId()
    const materials =
      issueForm.material_item_code.trim() && issueForm.issued_qty > 0
        ? [
            {
              material_item_code: issueForm.material_item_code.trim(),
              required_qty: issueForm.required_qty || issueForm.issued_qty,
              issued_qty: issueForm.issued_qty,
            },
          ]
        : undefined
    await issueSubcontractMaterial(id, {
      idempotency_key: issueForm.idempotency_key,
      warehouse: issueForm.warehouse,
      materials,
    })
    ElMessage.success('发料提交成功')
    issueForm.idempotency_key = buildKey('issue')
    await loadDetail()
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    issuing.value = false
  }
}

const receive = async (): Promise<void> => {
  receiving.value = true
  try {
    const id = ensureOrderId()
    await receiveSubcontract(id, {
      idempotency_key: receiveForm.idempotency_key,
      receipt_warehouse: receiveForm.receipt_warehouse,
      received_qty: receiveForm.received_qty,
      color: receiveForm.color || undefined,
      size: receiveForm.size || undefined,
      batch_no: receiveForm.batch_no || undefined,
      uom: receiveForm.uom || undefined,
    })
    ElMessage.success('回料登记成功')
    receiveForm.idempotency_key = buildKey('receive')
    await loadDetail()
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    receiving.value = false
  }
}

const inspect = async (): Promise<void> => {
  inspecting.value = true
  try {
    const id = ensureOrderId()
    await inspectSubcontract(id, {
      receipt_batch_no: inspectForm.receipt_batch_no,
      idempotency_key: inspectForm.idempotency_key,
      inspected_qty: inspectForm.inspected_qty,
      rejected_qty: inspectForm.rejected_qty,
      deduction_amount_per_piece: inspectForm.deduction_amount_per_piece,
      remark: inspectForm.remark || undefined,
    })
    ElMessage.success('验货登记成功')
    inspectForm.idempotency_key = buildKey('inspect')
    inspectForm.inspected_qty = 0
    inspectForm.rejected_qty = 0
    inspectForm.deduction_amount_per_piece = 0
    inspectForm.remark = ''
    await loadDetail()
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    inspecting.value = false
  }
}

const retrySync = async (stockAction: 'issue' | 'receipt'): Promise<void> => {
  retryingAction.value = stockAction
  try {
    const id = ensureOrderId()
    if (!detail.value) throw new Error('外发单详情未加载')
    const outboxId =
      stockAction === 'issue' ? detail.value.latest_issue_outbox_id : detail.value.latest_receipt_outbox_id
    const idempotencyKey =
      stockAction === 'issue' ? detail.value.latest_issue_idempotency_key : detail.value.latest_receipt_idempotency_key
    if (!outboxId || !idempotencyKey) {
      throw new Error('缺少重试目标标识')
    }
    await retrySubcontractStockSync(id, {
      outbox_id: outboxId,
      stock_action: stockAction,
      idempotency_key: idempotencyKey,
      reason: 'manual_retry_from_ui',
    })
    ElMessage.success('库存同步重试已提交')
    await loadDetail()
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    retryingAction.value = ''
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
  resetActionForms()
  try {
    await permissionStore.loadCurrentUser()
    await permissionStore.loadModuleActions('subcontract')
  } catch (error) {
    ElMessage.error((error as Error).message)
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

.scope-tag {
  margin-left: 8px;
}

.retry-actions {
  display: flex;
  gap: 8px;
}
</style>
