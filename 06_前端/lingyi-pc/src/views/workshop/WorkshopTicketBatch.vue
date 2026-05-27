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
          data-readonly-boundary="true"
          data-testid="workshop-ticket-batch-submit-button"
          data-write-guard="guarded:workshop-ticket-batch-readonly"
          data-write-request-success-allowed="false"
          data-real-write-action-added="false"
          data-write-allowlist="readonly-preview-only"
          data-guard-state="guarded-readonly"
          @click="submitBatch"
        >
          批量导入只读预览
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
            ? '当前账号具备页面可见权限，但 Z038 只读边界已拦截批量写入。'
            : '当前账号无批量导入权限，写动作已保持只读 guard。'
        }}
      </p>

      <div class="z042-readonly-grid" data-testid="z042-batch-readonly-boundary">
        <section
          class="z042-readonly-section"
          data-readonly-boundary="true"
          data-testid="z042-batch-parse-summary"
        >
          <h3>JSON 解析摘要</h3>
          <p>
            {{
              parseSummary
                ? `本地解析 ${parseSummary.total} 行，可预览 ${parseSummary.valid} 行，失败 ${parseSummary.invalid} 行。`
                : '等待本地解析；解析结果只用于预览，不会提交批量导入写请求。'
            }}
          </p>
          <p class="z042-meta">
            request_id={{ readonlyRequestId }} / scenario_tag={{ readonlyScenarioTag }}
          </p>
        </section>

        <section
          class="z042-readonly-section"
          data-readonly-boundary="true"
          data-testid="z042-batch-failure-explanation"
        >
          <h3>失败原因分组</h3>
          <ul v-if="failureReasonGroups.length > 0" class="z042-failure-list">
            <li v-for="group in failureReasonGroups" :key="group.code">
              {{ group.code }}：{{ group.count }} 条，示例 {{ group.sample }}
            </li>
          </ul>
          <p v-else>
            暂无失败明细；若存在缺字段、反冲缺原因或 scenario_tag 不一致，将按原因分组展示。
          </p>
        </section>

        <section
          class="z042-readonly-section"
          data-action-type="write"
          data-guard-state="guarded-readonly"
          data-readonly-boundary="true"
          data-testid="z042-batch-retry-guard"
          data-write-guard="guarded:z042-batch-failure-retry-readonly"
          data-write-request-success-allowed="false"
        >
          <h3>失败重试只读 guard</h3>
          <p>
            批量导入、解析后提交与失败重试均保持 guarded/readonly；页面仅记录 request_id 与 scenario_tag，未开放真实写成功路径。
          </p>
        </section>
      </div>

      <div class="z043-readonly-grid" data-testid="z043-batch-template-field-guard">
        <section
          class="z043-readonly-section"
          data-readonly-boundary="true"
          data-testid="z043-batch-template-sample"
        >
          <h3>JSON 模板示例</h3>
          <pre>{{ z043TemplateSample }}</pre>
          <p>模板仅用于本地粘贴与字段对照，不会触发批量导入写请求。</p>
        </section>

        <section
          class="z043-readonly-section"
          data-readonly-boundary="true"
          data-testid="z043-batch-field-error-locator"
        >
          <h3>字段级失败定位</h3>
          <ul class="z043-locator-list">
            <li v-for="item in z043FieldLocatorRows" :key="item.field">
              {{ item.field }}：{{ item.status }}，{{ item.reason }}
            </li>
          </ul>
        </section>

        <section
          class="z043-readonly-section"
          data-action-type="write"
          data-guard-state="guarded-readonly"
          data-readonly-boundary="true"
          data-testid="z043-batch-retry-preconditions"
          data-write-guard="guarded:z043-batch-retry-preconditions-readonly"
          data-write-request-success-allowed="false"
          data-real-write-action-added="false"
        >
          <h3>重试前置条件</h3>
          <ul class="z043-locator-list">
            <li v-for="item in z043RetryPreconditions" :key="item">
              {{ item }}
            </li>
          </ul>
        </section>

        <section
          class="z043-readonly-section"
          data-readonly-boundary="true"
          data-testid="z043-batch-readonly-request-context"
          data-write-request-success-allowed="false"
          data-real-write-action-added="false"
        >
          <h3>readonly request context</h3>
          <p>request_id={{ readonlyRequestId }}</p>
          <p>scenario_tag={{ readonlyScenarioTag }}</p>
          <p>批量导入、解析后提交与失败重试均只记录 guard trace，不形成真实写成功。</p>
        </section>
      </div>

      <div class="z044-readonly-grid" data-testid="z044-batch-field-diff-retry-lock">
        <section
          class="z044-readonly-section"
          data-readonly-boundary="true"
          data-testid="z044-batch-template-version-readback"
        >
          <h3>模板版本 readback</h3>
          <dl class="z044-readback-list">
            <div v-for="item in z044TemplateVersionReadback" :key="item.label">
              <dt>{{ item.label }}</dt>
              <dd>{{ item.value }}</dd>
            </div>
          </dl>
        </section>

        <section
          class="z044-readonly-section"
          data-readonly-boundary="true"
          data-testid="z044-batch-field-diff-sample"
        >
          <h3>字段差异样例</h3>
          <ul class="z044-locator-list">
            <li v-for="item in z044FieldDiffSamples" :key="item.field">
              {{ item.field }}：{{ item.expected }} / {{ item.actual }}，{{ item.readback }}
            </li>
          </ul>
        </section>

        <section
          class="z044-readonly-section"
          data-readonly-boundary="true"
          data-testid="z044-batch-failed-row-locator"
        >
          <h3>失败行定位</h3>
          <ul class="z044-locator-list">
            <li v-for="item in z044FailedRowLocatorRows" :key="`${item.row}-${item.field}`">
              第 {{ item.row }} 行 {{ item.field }}：{{ item.reason }}
            </li>
          </ul>
        </section>

        <section
          class="z044-readonly-section"
          data-action-type="write"
          data-guard-state="guarded-readonly"
          data-readonly-boundary="true"
          data-testid="z044-batch-retry-lock-reason"
          data-write-guard="guarded:z044-batch-retry-lock-readonly"
          data-write-request-success-allowed="false"
          data-real-write-action-added="false"
        >
          <h3>失败重试锁定原因</h3>
          <p>失败重试必须保留 request_id 与 scenario_tag，只读锁定后不发起重试写请求。</p>
        </section>

        <section
          class="z044-readonly-section"
          data-readonly-boundary="true"
          data-testid="z044-batch-readonly-request-context"
          data-write-request-success-allowed="false"
          data-real-write-action-added="false"
        >
          <h3>request_id / scenario_tag 风险说明</h3>
          <p>request_id={{ readonlyRequestId }}</p>
          <p>scenario_tag={{ readonlyScenarioTag }}</p>
          <p>readonly fallback risk：auth 401 只记录为只读风险，不代表权限通过或写成功。</p>
        </section>

        <section
          class="z044-readonly-section"
          data-action-type="write"
          data-guard-state="guarded-readonly"
          data-readonly-boundary="true"
          data-testid="z044-batch-import-write-guard"
          data-write-guard="guarded:z044-batch-import-readonly"
          data-write-request-success-allowed="false"
          data-real-write-action-added="false"
        >
          <h3>批量导入 guarded/readonly</h3>
          <p>批量导入入口只展示本地预览，write_requests_observed_count 必须保持 0。</p>
        </section>

        <section
          class="z044-readonly-section"
          data-action-type="write"
          data-guard-state="guarded-readonly"
          data-readonly-boundary="true"
          data-testid="z044-batch-parse-submit-guard"
          data-write-guard="guarded:z044-batch-parse-submit-readonly"
          data-write-request-success-allowed="false"
          data-real-write-action-added="false"
        >
          <h3>解析后提交 guarded/readonly</h3>
          <p>解析后提交只保留字段差异 readback，不形成真实写请求成功。</p>
        </section>

        <section
          class="z044-readonly-section"
          data-action-type="write"
          data-guard-state="guarded-readonly"
          data-readonly-boundary="true"
          data-testid="z044-batch-write-success-blocker"
          data-write-guard="guarded:z044-batch-write-success-blocker"
          data-write-request-success-allowed="false"
          data-real-write-action-added="false"
        >
          <h3>写成功阻断</h3>
          <p>批量导入、解析后提交、失败重试均不得形成真实写请求成功。</p>
        </section>
      </div>

      <el-alert
        v-if="batchReceipt"
        type="info"
        :closable="false"
        show-icon
        data-testid="workshop-ticket-batch-receipt"
        :title="`只读预览：可提交 ${batchReceipt.success_count} 条，失败 ${batchReceipt.failed_count} 条；未发送批量导入请求。`"
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

      <div v-if="validationRows.length > 0" class="failed-actions">
        <el-button
          data-action-type="write"
          data-readonly-boundary="true"
          data-testid="workshop-ticket-batch-failed-retry-guarded-button"
          data-write-guard="guarded:workshop-ticket-batch-failed-retry-readonly"
          data-write-request-success-allowed="false"
          data-real-write-action-added="false"
          @click="showRetryGuard"
        >
          导入失败重试入口
        </el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  buildWorkshopTicketRequestId,
  ensureWorkshopTicketScenarioTag,
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
const readonlyScenarioTag = 'Z003-WORKSHOP-TICKET-20260527-042'
const readonlyRequestId = buildWorkshopTicketRequestId({
  scenarioTag: readonlyScenarioTag,
  operation: 'batch',
  idempotencyKey: 'Z042-BATCH-READONLY',
  sourceRef: 'Z042-BATCH-READONLY',
  ticketKey: 'Z042-BATCH-READONLY',
  jobCard: 'Z042-BATCH-READONLY',
  employeeOrOperator: 'readonly-operator',
  batchNo: 'Z042-BATCH-GUARD',
})

const failureReasonGroups = computed<Array<{ code: string; count: number; sample: string }>>(() => {
  const groups = new Map<string, { code: string; count: number; sample: string }>()
  validationRows.value.forEach((row) => {
    const current = groups.get(row.code)
    if (current) {
      current.count += 1
      return
    }
    groups.set(row.code, {
      code: row.code,
      count: 1,
      sample: row.message,
    })
  })
  return Array.from(groups.values())
})

const z043TemplateSample = JSON.stringify([
  {
    operation_type: 'register',
    ticket_key: 'Z043-WORKSHOP-TICKET-20260527-001-TK',
    job_card: 'JC-Z043-001',
    employee: 'EMP-001',
    process_name: 'sew',
    qty: 10,
    work_date: '2026-05-27',
    scenario_tag: 'Z043-WORKSHOP-TICKET-20260527-001',
    source_ref: 'Z043-WORKSHOP-TICKET-20260527-001-SRC',
  },
], null, 2)

const z043FieldLocatorRows = computed<Array<{ field: string; status: string; reason: string }>>(() => {
  if (validationRows.value.length > 0) {
    return validationRows.value.flatMap((row) => {
      const fields = row.message.replace('缺少字段：', '').split(',').map((field) => field.trim()).filter(Boolean)
      return fields.map((field) => ({
        field,
        status: `第 ${row.row_index} 行需修正`,
        reason: `${row.ticket_key} 只读定位：${row.code}`,
      }))
    })
  }
  return [
    { field: 'ticket_key', status: '待本地解析', reason: '用于定位工票唯一键' },
    { field: 'job_card', status: '待本地解析', reason: '用于定位生产工单' },
    { field: 'scenario_tag', status: '待本地解析', reason: '用于只读 request context 校验' },
  ]
})

const z043RetryPreconditions = [
  '批量导入：必须先完成本地 JSON 解析摘要，入口保持 guarded/readonly。',
  '解析后提交：字段定位无缺失后仍仅生成只读预览，不发起写请求。',
  '失败重试：必须带 request_id 与 scenario_tag 说明，重试入口保持只读 guard。',
]

const z044TemplateVersionReadback = [
  { label: '模板版本', value: 'Z044-BATCH-TEMPLATE-V1 readonly readback' },
  { label: '模板来源', value: 'Z043 committed batch template path' },
  { label: '锁定策略', value: '批量导入、解析后提交、失败重试均保持 guarded/readonly' },
]

const z044FieldDiffSamples = [
  {
    field: 'qty',
    expected: 'number > 0',
    actual: 'string 或空值',
    readback: '只读显示字段差异，不提交修正写请求',
  },
  {
    field: 'scenario_tag',
    expected: readonlyScenarioTag,
    actual: '缺失或与 request_id 不一致',
    readback: '触发只读风险说明与失败重试锁定',
  },
  {
    field: 'source_ref',
    expected: '带 Z044 batch 来源',
    actual: '未携带来源',
    readback: '保留字段差异样例用于人工核对',
  },
]

const z044FailedRowLocatorRows = computed<Array<{ row: number; field: string; reason: string }>>(() => {
  if (validationRows.value.length > 0) {
    return validationRows.value.flatMap((row) => {
      const fields = row.message.replace('缺少字段：', '').split(',').map((field) => field.trim()).filter(Boolean)
      return fields.map((field) => ({
        row: row.row_index,
        field,
        reason: `${row.code} 已锁定失败重试，只允许 readonly readback`,
      }))
    })
  }
  return [
    { row: 1, field: 'qty', reason: '字段类型或数量为空时仅展示差异样例' },
    { row: 1, field: 'scenario_tag', reason: 'request_id/scenario_tag 不一致时锁定失败重试' },
    { row: 2, field: 'source_ref', reason: '来源缺失时仅记录只读风险说明' },
  ]
})

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

const showRetryGuard = (): void => {
  guardedFeedback.value = `失败重试只读 guard 生效：request_id=${readonlyRequestId}，scenario_tag=${readonlyScenarioTag}，未开放写请求。`
  ElMessage.warning(guardedFeedback.value)
}

const submitBatch = (): void => {
  const ok = parsePayload(true)
  if (!ok) return

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
    const firstRow = payloadRows[0]
    const topTicketKey = withScenarioCarrier(String(firstRow.ticket_key || '').trim(), scenarioTag, 'TK-BATCH')
    const topSourceRef = withScenarioCarrier(String(firstRow.source_ref || '').trim(), scenarioTag, 'SRC-BATCH')
    const jobCard = String(firstRow.job_card || '').trim()
    const employee = String(firstRow.employee || '').trim()
    const requestId = buildWorkshopTicketRequestId({
      scenarioTag,
      operation: 'batch',
      idempotencyKey: topTicketKey,
      sourceRef: topSourceRef,
      ticketKey: topTicketKey,
      jobCard,
      employeeOrOperator: employee || 'operator-readonly',
      batchNo,
    })
    batchReceipt.value = {
      success_count: previewRows.value.length,
      failed_count: validationRows.value.length,
    }
    readbackHint.value = `只读边界已拦截批量导入，request_id=${requestId}，scenario_tag=${scenarioTag}，未发起 /api/workshop/tickets/batch 写请求。`
    guardedFeedback.value = canBatch.value
      ? 'Z038 只读边界生效：批量导入入口仅展示预览，不提交写请求。'
      : '当前账号无批量导入权限，且 Z038 只读边界已拦截写请求。'
    ElMessage.warning(guardedFeedback.value)
  } catch (error) {
    guardedFeedback.value = (error as Error).message || '只读预览失败'
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

.failed-actions {
  margin-top: 12px;
}

.permission-tip {
  margin-top: 12px;
  color: var(--el-text-color-secondary);
}

.z042-readonly-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-top: 12px;
}

.z042-readonly-section {
  min-height: 124px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 6px;
  padding: 12px;
  background: var(--el-fill-color-lighter);
}

.z042-readonly-section h3 {
  margin: 0 0 8px;
  font-size: 15px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.z042-readonly-section p {
  margin: 0;
  line-height: 1.55;
  color: var(--el-text-color-regular);
}

.z042-meta {
  margin-top: 8px !important;
  font-family: var(--el-font-family);
  word-break: break-all;
}

.z042-failure-list {
  margin: 0;
  padding-left: 18px;
  color: var(--el-text-color-regular);
}

.z043-readonly-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-top: 12px;
}

.z043-readonly-section {
  min-height: 150px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 6px;
  padding: 12px;
  background: var(--el-fill-color-blank);
}

.z043-readonly-section h3 {
  margin: 0 0 8px;
  font-size: 15px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.z043-readonly-section p {
  margin: 0 0 6px;
  line-height: 1.55;
  color: var(--el-text-color-regular);
  word-break: break-all;
}

.z043-readonly-section pre {
  max-height: 180px;
  overflow: auto;
  margin: 0 0 8px;
  padding: 10px;
  border-radius: 4px;
  background: var(--el-fill-color-lighter);
  color: var(--el-text-color-primary);
  white-space: pre-wrap;
  word-break: break-word;
}

.z043-locator-list {
  margin: 0;
  padding-left: 18px;
  color: var(--el-text-color-regular);
}

.z044-readonly-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-top: 12px;
}

.z044-readonly-section {
  min-height: 142px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 6px;
  padding: 12px;
  background: var(--el-fill-color-lighter);
}

.z044-readonly-section h3 {
  margin: 0 0 8px;
  font-size: 15px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.z044-readonly-section p {
  margin: 0 0 6px;
  line-height: 1.55;
  color: var(--el-text-color-regular);
  word-break: break-all;
}

.z044-readback-list {
  margin: 0;
}

.z044-readback-list div {
  display: grid;
  grid-template-columns: 92px minmax(0, 1fr);
  gap: 8px;
  margin-bottom: 6px;
}

.z044-readback-list dt {
  color: var(--el-text-color-secondary);
}

.z044-readback-list dd {
  margin: 0;
  color: var(--el-text-color-regular);
  word-break: break-all;
}

.z044-locator-list {
  margin: 0;
  padding-left: 18px;
  color: var(--el-text-color-regular);
}

@media (max-width: 960px) {
  .z042-readonly-grid {
    grid-template-columns: 1fr;
  }

  .z043-readonly-grid {
    grid-template-columns: 1fr;
  }

  .z044-readonly-grid {
    grid-template-columns: 1fr;
  }
}
</style>
