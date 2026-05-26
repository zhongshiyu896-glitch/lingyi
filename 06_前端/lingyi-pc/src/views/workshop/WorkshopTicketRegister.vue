<template>
  <div class="workshop-ticket-register" data-testid="workshop-ticket-register-page">
    <el-card shadow="never" data-testid="workshop-ticket-register-card">
      <template #header>
        <div class="header-row" data-testid="workshop-ticket-register-header">
          <span data-testid="workshop-ticket-register-title">工票登记 / 撤销</span>
          <el-button data-testid="workshop-ticket-register-back-button" @click="goList">返回列表</el-button>
        </div>
      </template>

      <el-tabs v-model="mode" data-testid="workshop-ticket-register-tabs">
        <el-tab-pane name="register">
          <template #label>
            <span data-testid="workshop-ticket-register-tab-register">登记工票</span>
          </template>
        </el-tab-pane>
        <el-tab-pane name="reversal">
          <template #label>
            <span data-testid="workshop-ticket-register-tab-reversal">撤销工票</span>
          </template>
        </el-tab-pane>
      </el-tabs>

      <el-form label-width="120px" :model="form" data-testid="workshop-ticket-register-form">
        <el-form-item label="幂等键 ticket_key" data-testid="workshop-ticket-register-field-ticket-key">
          <el-input v-model="form.ticket_key" placeholder="扫码值或业务唯一键" data-testid="workshop-ticket-register-input-ticket-key" />
        </el-form-item>
        <el-form-item label="Job Card" data-testid="workshop-ticket-register-field-job-card">
          <el-input v-model="form.job_card" placeholder="请输入 Job Card" data-testid="workshop-ticket-register-input-job-card" />
        </el-form-item>
        <el-form-item label="员工" data-testid="workshop-ticket-register-field-employee">
          <el-input v-model="form.employee" placeholder="请输入员工编码或姓名" data-testid="workshop-ticket-register-input-employee" />
        </el-form-item>
        <el-form-item label="工序" data-testid="workshop-ticket-register-field-process">
          <el-input v-model="form.process_name" placeholder="请输入工序名称" data-testid="workshop-ticket-register-input-process" />
        </el-form-item>
        <el-form-item label="颜色/尺码" data-testid="workshop-ticket-register-field-color-size">
          <div class="inline-fields">
            <el-input v-model="form.color" placeholder="Color" data-testid="workshop-ticket-register-input-color" />
            <el-input v-model="form.size" placeholder="Size" data-testid="workshop-ticket-register-input-size" />
          </div>
        </el-form-item>
        <el-form-item label="数量" data-testid="workshop-ticket-register-field-qty">
          <el-input-number
            v-model="form.qty"
            :min="0.000001"
            :step="1"
            aria-label="工票数量"
            data-testid="workshop-ticket-register-input-qty"
          />
        </el-form-item>
        <el-form-item label="工作日期" data-testid="workshop-ticket-register-field-work-date">
          <el-date-picker
            v-model="form.work_date"
            value-format="YYYY-MM-DD"
            type="date"
            placeholder="请选择工作日期"
            aria-label="工作日期"
            data-testid="workshop-ticket-register-input-work-date"
          />
        </el-form-item>

        <template v-if="mode === 'register'">
          <el-form-item label="来源" data-testid="workshop-ticket-register-field-source">
            <el-select
              v-model="form.source"
              placeholder="请选择来源"
              style="width: 160px"
              aria-label="工票来源"
              data-testid="workshop-ticket-register-input-source"
            >
              <el-option label="manual" value="manual" />
              <el-option label="pda" value="pda" />
              <el-option label="mes" value="mes" />
              <el-option label="import" value="import" />
            </el-select>
          </el-form-item>
          <el-form-item label="来源单号" data-testid="workshop-ticket-register-field-source-ref">
            <el-input v-model="form.source_ref" placeholder="请输入来源单号（需包含 scenario_tag）" data-testid="workshop-ticket-register-input-source-ref" />
          </el-form-item>
        </template>

        <template v-else>
          <el-form-item label="原工票ID" data-testid="workshop-ticket-register-field-original-ticket-id">
            <el-input-number
              v-model="form.original_ticket_id"
              :min="1"
              aria-label="原工票ID"
              data-testid="workshop-ticket-register-input-original-ticket-id"
            />
          </el-form-item>
          <el-form-item label="撤销原因" data-testid="workshop-ticket-register-field-reason">
            <el-input v-model="form.reason" placeholder="请输入撤销原因" data-testid="workshop-ticket-register-input-reason" />
          </el-form-item>
        </template>

        <el-form-item label="操作" data-testid="workshop-ticket-register-actions">
          <el-button
            type="primary"
            :disabled="submitting"
            :loading="submitting"
            data-action-type="write"
            data-testid="workshop-ticket-register-submit-button"
            :data-write-guard="mode === 'register' ? 'guarded:workshop-ticket-register-readonly' : 'guarded:workshop-ticket-reversal-readonly'"
            :data-write-allowlist="mode === 'register' ? 'workshop-ticket-register' : 'workshop-ticket-reversal'"
            data-guard-state="readonly-no-write"
            data-readonly-boundary="true"
            data-write-request-success-allowed="false"
            @click="submit"
          >
            {{ mode === 'register' ? '提交登记（只读预览）' : '提交撤销（只读预览）' }}
          </el-button>
        </el-form-item>
      </el-form>

      <el-alert
        type="warning"
        data-testid="workshop-ticket-register-validation-hint"
        :closable="false"
        show-icon
        :title="validationHint || '只读校验提示：提交登记需 ticket_key、job_card、employee、process_name、work_date、source_ref；提交撤销需 original_ticket_id 与 reason。'"
      />
      <el-alert
        v-if="guardedFeedback"
        type="warning"
        data-testid="workshop-ticket-register-guarded-feedback"
        :closable="false"
        show-icon
        :title="guardedFeedback"
      />
      <p class="permission-tip" data-testid="workshop-ticket-register-permission-or-disabled-state">
        {{
          activePermission
            ? '当前页面处于只读治理模式：登记/撤销仅生成本地 request_id 与 scenario_tag 预览，不提交写请求。'
            : '当前账号无提交权限；页面仍保持只读预览，登记/撤销写动作已被 guard 拦截。'
        }}
      </p>
    </el-card>

    <el-card shadow="never" data-testid="workshop-ticket-register-readonly-draft-preview">
      <template #header>
        <span>本地写入草稿预览</span>
      </template>
      <el-descriptions :column="2" border size="small">
        <el-descriptions-item label="模式">{{ mode === 'register' ? '登记工票' : '撤销工票' }}</el-descriptions-item>
        <el-descriptions-item label="ticket_key">{{ readonlyDraft.ticket_key || '-' }}</el-descriptions-item>
        <el-descriptions-item label="job_card">{{ readonlyDraft.job_card || '-' }}</el-descriptions-item>
        <el-descriptions-item label="employee">{{ readonlyDraft.employee || '-' }}</el-descriptions-item>
        <el-descriptions-item label="process_name">{{ readonlyDraft.process_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="work_date">{{ readonlyDraft.work_date || '-' }}</el-descriptions-item>
        <el-descriptions-item label="qty">{{ readonlyDraft.qty }}</el-descriptions-item>
        <el-descriptions-item label="source/reason">
          {{ mode === 'register' ? (readonlyDraft.source || '-') : (readonlyDraft.reason || '-') }}
        </el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  buildWorkshopTicketRequestId,
  ensureWorkshopTicketScenarioTag,
} from '@/api/workshop'
import { usePermissionStore } from '@/stores/permission'

const router = useRouter()
const permissionStore = usePermissionStore()
const SCENARIO_PATTERN = /(Z003-WORKSHOP-TICKET-\d{8}-\d{3})/
const mode = ref<'register' | 'reversal'>('register')
const submitting = ref<boolean>(false)
const guardedFeedback = ref<string>('')
const validationHint = ref<string>('')

const form = reactive({
  ticket_key: '',
  job_card: '',
  employee: '',
  process_name: '',
  color: '',
  size: '',
  qty: 1,
  work_date: '',
  source: 'manual',
  source_ref: '',
  original_ticket_id: undefined as number | undefined,
  reason: '',
})

const canRegister = computed<boolean>(() => permissionStore.state.buttonPermissions.ticket_register)
const canReversal = computed<boolean>(() => permissionStore.state.buttonPermissions.ticket_reversal)
const activePermission = computed<boolean>(() => (mode.value === 'register' ? canRegister.value : canReversal.value))
const requiredFieldErrors = computed<string[]>(() => {
  const missing: string[] = []
  if (!form.ticket_key) missing.push('ticket_key')
  if (!form.job_card) missing.push('job_card')
  if (!form.employee) missing.push('employee')
  if (!form.process_name) missing.push('process_name')
  if (!form.work_date) missing.push('work_date')
  if (mode.value === 'register' && !form.source_ref) missing.push('source_ref')
  if (mode.value === 'reversal' && !form.original_ticket_id) missing.push('original_ticket_id')
  if (mode.value === 'reversal' && !form.reason) missing.push('reason')
  return missing
})
const readonlyDraft = computed(() => ({
  ticket_key: form.ticket_key.trim(),
  job_card: form.job_card.trim(),
  employee: form.employee.trim(),
  process_name: form.process_name.trim(),
  color: form.color.trim(),
  size: form.size.trim(),
  qty: form.qty,
  work_date: form.work_date,
  source: form.source,
  source_ref: form.source_ref.trim(),
  original_ticket_id: form.original_ticket_id,
  reason: form.reason.trim(),
}))

const extractScenarioTag = (value: string): string | null => {
  const matched = value.match(SCENARIO_PATTERN)
  return matched ? matched[1] : null
}

const resolveScenarioTag = (): string => {
  const carriers = [form.ticket_key, form.source_ref, form.reason]
  for (const carrier of carriers) {
    const tag = extractScenarioTag(carrier)
    if (tag) return ensureWorkshopTicketScenarioTag(tag)
  }
  return ensureWorkshopTicketScenarioTag('')
}

const withScenarioCarrier = (value: string, tag: string, fallbackSuffix: string): string => {
  const normalized = value.trim()
  if (normalized && extractScenarioTag(normalized) === tag) return normalized
  return `${tag}-${fallbackSuffix}`
}

const submit = async (): Promise<void> => {
  guardedFeedback.value = ''
  validationHint.value = ''
  if (requiredFieldErrors.value.length > 0) {
    validationHint.value = `请完整填写关键字段：${requiredFieldErrors.value.join(', ')}`
    ElMessage.warning(validationHint.value)
    return
  }
  const scenarioTag = resolveScenarioTag()
  const operatorId = form.employee.trim() || 'operator-local'
  const batchNo = `${scenarioTag}-BATCH-001`
  const ticketKey = withScenarioCarrier(form.ticket_key, scenarioTag, mode.value === 'register' ? 'TK-REG' : 'TK-REV')
  const sourceRef = withScenarioCarrier(form.source_ref, scenarioTag, mode.value === 'register' ? 'SRC-REG' : 'SRC-REV')
  const idempotencyKey = ticketKey
  const requestId = buildWorkshopTicketRequestId({
    scenarioTag,
    operation: mode.value,
    idempotencyKey,
    sourceRef,
    ticketKey,
    jobCard: form.job_card.trim(),
    employeeOrOperator: operatorId,
    batchNo,
  })
  form.ticket_key = ticketKey
  form.source_ref = sourceRef
  if (mode.value === 'register') {
    form.source_ref = sourceRef
  }

  submitting.value = true
  try {
    guardedFeedback.value = `只读治理已拦截${mode.value === 'register' ? '登记' : '撤销'}写请求；已生成本地 request_id=${requestId}，未调用登记/撤销 API。`
    ElMessage.warning('只读治理模式：写请求未发送')
  } catch (error) {
    guardedFeedback.value = `只读 guard 生成失败（fail-closed）：${(error as Error).message}`
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
.workshop-ticket-register {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.inline-fields {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  width: 100%;
}

.permission-tip {
  margin-top: 12px;
  color: var(--el-text-color-secondary);
}
</style>
