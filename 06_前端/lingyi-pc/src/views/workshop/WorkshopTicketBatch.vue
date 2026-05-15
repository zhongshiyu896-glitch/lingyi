<template>
  <div class="workshop-ticket-batch" data-testid="workshop-ticket-batch-page">
    <el-card shadow="never" data-testid="workshop-ticket-batch-card">
      <template #header>
        <div class="header-row" data-testid="workshop-ticket-batch-header">
          <span data-testid="workshop-ticket-batch-title">工票批量导入</span>
          <el-button data-testid="workshop-ticket-batch-back-button" @click="goList">返回列表</el-button>
        </div>
      </template>

      <el-alert
        type="info"
        :closable="false"
        show-icon
        data-testid="workshop-ticket-batch-info"
        title="请粘贴 JSON 数组，每行对象包含 ticket_key/job_card/employee/process_name/qty/work_date 等字段。"
      />

      <el-input
        v-model="rawJson"
        class="json-editor"
        data-testid="workshop-ticket-batch-json-input"
        type="textarea"
        :rows="16"
        placeholder='[
  {"operation_type":"register","ticket_key":"BATCH-001","job_card":"JC-001","employee":"EMP-001","process_name":"sew","qty":10,"work_date":"2026-04-12","source":"import"}
]'
      />

      <div class="actions" data-testid="workshop-ticket-batch-actions">
        <el-button
          data-testid="workshop-ticket-batch-parse-button"
          @click="parsePayload(true)"
        >
          解析预览
        </el-button>
        <el-button
          type="primary"
          :disabled="submitting"
          :loading="submitting"
          data-action-type="write"
          data-testid="workshop-ticket-batch-submit-button"
          data-write-guard="allowed:workshop-ticket-batch-local-only"
          data-write-allowlist="workshop-ticket-batch"
          :data-guard-state="canBatch ? 'allowlist-local-dev' : 'guarded-no-permission'"
          @click="submitBatch"
        >
          开始导入
        </el-button>
      </div>

      <el-alert
        v-if="validationHint"
        type="warning"
        :closable="false"
        show-icon
        data-testid="workshop-ticket-batch-validation-hint"
        :title="validationHint"
      />
      <el-alert
        v-if="guardedFeedback"
        type="warning"
        :closable="false"
        show-icon
        data-testid="workshop-ticket-batch-guarded-feedback"
        :title="guardedFeedback"
      />

      <p class="permission-tip" data-testid="workshop-ticket-batch-permission-or-disabled-state">
        {{
          canBatch
            ? '当前页面允许本地测试库批量导入，受 scenario_tag 与 local-dev 门禁约束。'
            : '当前账号无批量导入权限，写动作已禁用。'
        }}
      </p>

      <el-alert
        v-if="batchReceipt"
        type="success"
        :closable="false"
        show-icon
        data-testid="workshop-ticket-batch-receipt"
        :title="`导入完成：成功 ${batchReceipt.success_count} 条，失败 ${batchReceipt.failed_count} 条`"
      />
      <el-alert
        v-if="readbackHint"
        type="info"
        :closable="false"
        show-icon
        data-testid="workshop-ticket-batch-readback-hint"
        :title="readbackHint"
      />

      <el-descriptions v-if="parseSummary" :column="3" border data-testid="workshop-ticket-batch-readonly-preview">
        <el-descriptions-item label="总行数">{{ parseSummary.total }}</el-descriptions-item>
        <el-descriptions-item label="可预览">{{ parseSummary.valid }}</el-descriptions-item>
        <el-descriptions-item label="校验失败">{{ parseSummary.invalid }}</el-descriptions-item>
      </el-descriptions>

      <el-table
        v-if="previewRows.length > 0"
        :data="previewRows"
        border
        empty-text="暂无预览"
        style="margin-top: 12px"
        data-testid="workshop-ticket-batch-preview-table"
      >
        <el-table-column prop="row_index" label="行号" width="80" />
        <el-table-column prop="operation_type" label="类型" width="100" />
        <el-table-column prop="ticket_key" label="ticket_key" min-width="140" />
        <el-table-column prop="job_card" label="job_card" min-width="140" />
        <el-table-column prop="employee" label="employee" min-width="120" />
        <el-table-column prop="qty" label="qty" width="100" />
      </el-table>

      <el-table
        v-if="validationRows.length > 0"
        :data="validationRows"
        border
        empty-text="暂无失败明细"
        style="margin-top: 12px"
        data-testid="workshop-ticket-batch-failed-items-table"
      >
        <el-table-column prop="row_index" label="行号" width="90" />
        <el-table-column prop="ticket_key" label="ticket_key" min-width="150" />
        <el-table-column prop="code" label="结果码" min-width="180" />
        <el-table-column prop="message" label="校验说明" min-width="220" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  batchWorkshopTickets,
  buildWorkshopTicketRequestId,
  ensureWorkshopTicketScenarioTag,
  fetchWorkshopTickets,
  type WorkshopTicketBatchItemPayload,
  type WorkshopTicketBatchPayload,
} from '@/api/workshop'
import { usePermissionStore } from '@/stores/permission'

const router = useRouter()
const permissionStore = usePermissionStore()
const rawJson = ref<string>('')
const submitting = ref<boolean>(false)
const guardedFeedback = ref<string>('')
const validationHint = ref<string>('')
const readbackHint = ref<string>('')
const batchReceipt = ref<{
  success_count: number
  failed_count: number
} | null>(null)
const parseSummary = ref<{ total: number; valid: number; invalid: number } | null>(null)
const previewRows = ref<Array<{
  row_index: number
  operation_type: string
  ticket_key: string
  job_card: string
  employee: string
  qty: number
}>>([])
const validationRows = ref<Array<{
  row_index: number
  ticket_key: string
  code: string
  message: string
}>>([])

const canBatch = computed<boolean>(() => permissionStore.state.buttonPermissions.ticket_batch)
const SCENARIO_PATTERN = /(Z003-WORKSHOP-TICKET-\d{8}-\d{3})/

const resetParseState = (): void => {
  parseSummary.value = null
  previewRows.value = []
  validationRows.value = []
  batchReceipt.value = null
  readbackHint.value = ''
}

const parsePayload = (notify: boolean): boolean => {
  guardedFeedback.value = ''
  validationHint.value = ''
  resetParseState()

  let rows: Array<Record<string, unknown>> = []
  try {
    const parsed = JSON.parse(rawJson.value || '[]')
    if (!Array.isArray(parsed)) {
      throw new Error('导入内容必须是 JSON 数组')
    }
    rows = parsed
  } catch (error) {
    validationHint.value = `JSON 解析失败：${(error as Error).message}`
    if (notify) ElMessage.error(validationHint.value)
    return false
  }
  if (rows.length === 0) {
    validationHint.value = '请先输入导入数据（非空 JSON 数组）'
    if (notify) ElMessage.warning(validationHint.value)
    return false
  }

  const preview: Array<{
    row_index: number
    operation_type: string
    ticket_key: string
    job_card: string
    employee: string
    qty: number
  }> = []
  const invalids: Array<{ row_index: number; ticket_key: string; code: string; message: string }> = []
  const requiredFields = ['ticket_key', 'job_card', 'employee', 'process_name', 'qty', 'work_date']

  rows.forEach((row, idx) => {
    const rowIndex = idx + 1
    const opType = typeof row.operation_type === 'string' && row.operation_type.trim() ? row.operation_type : 'register'
    const missing: string[] = requiredFields.filter((field) => {
      const value = row[field]
      if (value === null || value === undefined) return true
      if (typeof value === 'string' && value.trim().length === 0) return true
      return false
    })
    if (opType === 'reversal') {
      if (row.original_ticket_id === null || row.original_ticket_id === undefined || Number(row.original_ticket_id) <= 0) {
        missing.push('original_ticket_id')
      }
      if (!row.reason || String(row.reason).trim().length === 0) {
        missing.push('reason')
      }
    }
    if (missing.length > 0) {
      invalids.push({
        row_index: rowIndex,
        ticket_key: String(row.ticket_key || '-'),
        code: 'LOCAL_VALIDATION_MISSING_FIELDS',
        message: `缺少字段：${missing.join(', ')}`,
      })
      return
    }
    preview.push({
      row_index: rowIndex,
      operation_type: opType,
      ticket_key: String(row.ticket_key),
      job_card: String(row.job_card),
      employee: String(row.employee),
      qty: Number(row.qty ?? 0),
    })
  })

  validationRows.value = invalids
  previewRows.value = preview
  parseSummary.value = { total: rows.length, valid: preview.length, invalid: invalids.length }

  if (invalids.length > 0) {
    validationHint.value = `检测到 ${invalids.length} 条校验失败记录，请先修正后再尝试只读预览。`
    if (notify) ElMessage.warning(validationHint.value)
    return false
  }
  if (notify) {
    ElMessage.success(`解析完成：共 ${rows.length} 条，当前均可只读预览。`)
  }
  return true
}

const extractScenarioTag = (value: string): string | null => {
  const matched = value.match(SCENARIO_PATTERN)
  return matched ? matched[1] : null
}

const withScenarioCarrier = (value: string, tag: string, fallbackSuffix: string): string => {
  const normalized = value.trim()
  if (normalized && extractScenarioTag(normalized) === tag) return normalized
  return `${tag}-${fallbackSuffix}`
}

const submitBatch = async (): Promise<void> => {
  const ok = parsePayload(true)
  if (!ok) return

  if (!canBatch.value) {
    guardedFeedback.value = '当前账号无工票批量导入权限，写动作已禁用。'
    ElMessage.warning(guardedFeedback.value)
    return
  }

  let payloadRows: Array<Record<string, unknown>> = []
  try {
    const parsed = JSON.parse(rawJson.value || '[]')
    if (!Array.isArray(parsed)) throw new Error('导入内容必须是 JSON 数组')
    payloadRows = parsed
  } catch (error) {
    guardedFeedback.value = `JSON 解析失败：${(error as Error).message}`
    ElMessage.error(guardedFeedback.value)
    return
  }

  if (payloadRows.length === 0) {
    guardedFeedback.value = '请先输入导入数据（非空 JSON 数组）'
    ElMessage.warning(guardedFeedback.value)
    return
  }

  const scenarioTags = payloadRows
    .map((row) => [extractScenarioTag(String(row.ticket_key || '')), extractScenarioTag(String(row.source_ref || '')), extractScenarioTag(String(row.scenario_tag || ''))])
    .flat()
    .filter((tag): tag is string => Boolean(tag))

  const scenarioTag = ensureWorkshopTicketScenarioTag(scenarioTags[0] || '')
  if (scenarioTags.length > 0 && !scenarioTags.every((tag) => tag === scenarioTag)) {
    guardedFeedback.value = 'scenario_tag 载体不一致，已阻断提交。'
    ElMessage.warning(guardedFeedback.value)
    return
  }

  submitting.value = true
  guardedFeedback.value = ''
  readbackHint.value = ''
  try {
    const batchNo = `${scenarioTag}-BATCH-001`
    const normalizedRows: WorkshopTicketBatchItemPayload[] = payloadRows.map((row, index) => {
      const operationType = String(row.operation_type || row.operation || 'register').trim().toLowerCase() === 'reversal' ? 'reversal' : 'register'
      const jobCard = String(row.job_card || '').trim()
      const employee = String(row.employee || '').trim()
      const ticketKey = withScenarioCarrier(String(row.ticket_key || '').trim(), scenarioTag, `TK-${String(index + 1).padStart(3, '0')}`)
      const sourceRef = withScenarioCarrier(String(row.source_ref || '').trim(), scenarioTag, `SRC-${String(index + 1).padStart(3, '0')}`)
      return {
        scenario_tag: scenarioTag,
        idempotency_key: ticketKey,
        source_ref: sourceRef,
        operation: operationType,
        operator_id: employee || undefined,
        batch_no: batchNo,
        operation_type: operationType,
        ticket_key: ticketKey,
        job_card: jobCard,
        item_code: typeof row.item_code === 'string' ? row.item_code : undefined,
        employee,
        process_name: String(row.process_name || '').trim(),
        color: typeof row.color === 'string' ? row.color : undefined,
        size: typeof row.size === 'string' ? row.size : undefined,
        qty: Number(row.qty || 0),
        work_date: String(row.work_date || ''),
        source: typeof row.source === 'string' && row.source.trim() ? row.source.trim() : 'import',
        original_ticket_id: row.original_ticket_id ? Number(row.original_ticket_id) : undefined,
        reason: typeof row.reason === 'string' ? row.reason.trim() : undefined,
      }
    })
    const firstRow = normalizedRows[0]
    const topTicketKey = withScenarioCarrier(firstRow.ticket_key, scenarioTag, 'TK-BATCH')
    const topSourceRef = withScenarioCarrier(firstRow.source_ref, scenarioTag, 'SRC-BATCH')
    const requestId = buildWorkshopTicketRequestId({
      scenarioTag,
      operation: 'batch',
      idempotencyKey: topTicketKey,
      sourceRef: topSourceRef,
      ticketKey: topTicketKey,
      jobCard: firstRow.job_card,
      employeeOrOperator: firstRow.employee || firstRow.operator_id || 'operator-local',
      batchNo,
    })
    const payload: WorkshopTicketBatchPayload = {
      scenario_tag: scenarioTag,
      idempotency_key: topTicketKey,
      source_ref: topSourceRef,
      operation: 'batch',
      operator_id: firstRow.employee || undefined,
      batch_no: batchNo,
      ticket_key: topTicketKey,
      job_card: firstRow.job_card,
      employee: firstRow.employee || undefined,
      tickets: normalizedRows,
    }
    const response = await batchWorkshopTickets(payload, { requestId })
    const data = response.data
    batchReceipt.value = {
      success_count: data.success_count,
      failed_count: data.failed_count,
    }
    validationRows.value = data.failed_items.map((item) => ({
      row_index: item.row_index,
      ticket_key: item.ticket_key,
      code: item.error_code || item.code,
      message: item.message,
    }))
    ElMessage.success(`导入完成：成功 ${data.success_count} 条，失败 ${data.failed_count} 条`)

    const readback = await fetchWorkshopTickets({ page: 1, page_size: 20 })
    readbackHint.value = `回读完成：当前可见 ${readback.data.items.length} 条，total=${readback.data.total}`
  } catch (error) {
    guardedFeedback.value = (error as Error).message || '批量导入失败'
    ElMessage.error(guardedFeedback.value)
  } finally {
    submitting.value = false
  }
}

const goList = (): void => {
  void router.push('/workshop/tickets')
}

onMounted(async () => {
  try {
    await permissionStore.loadCurrentUser()
    await permissionStore.loadModuleActions('workshop')
  } catch (error) {
    ElMessage.error((error as Error).message)
  }
})
</script>

<style scoped>
.workshop-ticket-batch {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.json-editor {
  margin-top: 12px;
}

.actions {
  margin-top: 12px;
  display: flex;
  gap: 8px;
}

.permission-tip {
  margin-top: 12px;
  color: var(--el-text-color-secondary);
}
</style>
