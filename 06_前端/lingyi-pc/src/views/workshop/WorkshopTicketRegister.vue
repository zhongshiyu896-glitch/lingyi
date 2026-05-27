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
            data-guard-state="guarded-readonly"
            data-readonly-boundary="true"
            data-write-request-success-allowed="false"
            data-real-write-action-added="false"
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

      <div class="z042-register-grid" data-testid="z042-register-readonly-boundary">
        <section
          class="z042-register-section"
          data-readonly-boundary="true"
          data-testid="z042-register-draft-change-summary"
        >
          <h3>草稿变更摘要</h3>
          <ul class="z042-register-list">
            <li v-for="item in draftChangeSummary" :key="item.label">
              <span>{{ item.label }}</span>
              <strong>{{ item.value }}</strong>
              <em>{{ item.state }}</em>
            </li>
          </ul>
          <p class="z042-register-meta">
            request_id={{ readonlyRequestId }} / scenario_tag={{ readonlyScenarioTag }}
          </p>
        </section>

        <section
          class="z042-register-section"
          data-readonly-boundary="true"
          data-testid="z042-register-cancel-readonly-reason"
          data-write-guard="guarded:z042-register-cancel-readonly"
          data-write-request-success-allowed="false"
          data-real-write-action-added="false"
          data-guard-state="guarded-readonly"
        >
          <h3>撤销原因提示</h3>
          <p>{{ cancelReasonHint }}</p>
          <div class="z042-register-guards">
            <el-tag
              data-guard-entry="提交登记"
              data-guard-state="guarded-readonly"
              data-write-request-success-allowed="false"
              effect="plain"
              type="info"
            >
              提交登记 guarded/readonly
            </el-tag>
            <el-tag
              data-guard-entry="提交撤销"
              data-guard-state="guarded-readonly"
              data-write-request-success-allowed="false"
              effect="plain"
              type="warning"
            >
              提交撤销 guarded/readonly
            </el-tag>
          </div>
        </section>

        <section
          class="z042-register-section"
          data-readonly-boundary="true"
          data-testid="z042-register-return-route-guard"
          data-write-guard="guarded:z042-register-return-route-readonly"
          data-write-request-success-allowed="false"
          data-real-write-action-added="false"
          data-guard-state="guarded-readonly"
        >
          <h3>返回工票查询来源</h3>
          <p>{{ returnRouteExplanation }}</p>
          <el-button
            plain
            type="warning"
            data-guard-entry="只读降级确认"
            data-guard-state="guarded-readonly"
            data-readonly-boundary="true"
            data-write-request-success-allowed="false"
            data-real-write-action-added="false"
            @click="confirmReadonlyDowngrade"
          >
            只读降级确认（不写入）
          </el-button>
        </section>
      </div>

      <div class="z043-register-grid" data-testid="z043-register-readonly-boundary">
        <section
          class="z043-register-section"
          data-readonly-boundary="true"
          data-testid="z043-register-field-diff-summary"
        >
          <h3>字段级草稿差异</h3>
          <ul class="z043-register-list">
            <li v-for="item in z043FieldDiffSummary" :key="item.field">
              <span>{{ item.field }}</span>
              <strong>{{ item.current }}</strong>
              <em>{{ item.diff }}</em>
            </li>
          </ul>
        </section>

        <section
          class="z043-register-section"
          data-readonly-boundary="true"
          data-testid="z043-register-cancel-preview"
        >
          <h3>撤销预览摘要</h3>
          <p>{{ z043CancelPreviewSummary }}</p>
        </section>

        <section
          class="z043-register-section"
          data-readonly-boundary="true"
          data-testid="z043-register-readonly-confirm-chain"
          data-write-guard="guarded:z043-register-readonly-confirm-chain"
          data-write-request-success-allowed="false"
          data-real-write-action-added="false"
          data-guard-state="guarded-readonly"
        >
          <h3>只读确认链路</h3>
          <p>{{ z043ReadonlyConfirmChain }}</p>
          <div class="z043-register-guards">
            <el-tag
              v-for="entry in z043GuardedEntries"
              :key="entry"
              data-readonly-boundary="true"
              :data-guard-entry="entry"
              data-guard-state="guarded-readonly"
              data-write-request-success-allowed="false"
              data-real-write-action-added="false"
              effect="plain"
              type="info"
            >
              {{ entry }} guarded/readonly
            </el-tag>
          </div>
        </section>

        <section
          class="z043-register-section"
          data-readonly-boundary="true"
          data-testid="z043-register-return-source-readback"
        >
          <h3>返回查询来源</h3>
          <p>{{ z043ReturnSourceReadback }}</p>
        </section>
      </div>

      <div class="z044-register-grid" data-testid="z044-register-readonly-boundary">
        <section
          class="z044-register-section"
          data-readonly-boundary="true"
          data-testid="z044-register-draft-readback-chain"
        >
          <h3>草稿回读链路</h3>
          <p>{{ z044DraftReadbackChain }}</p>
        </section>

        <section
          class="z044-register-section"
          data-readonly-boundary="true"
          data-testid="z044-register-field-impact-matrix"
        >
          <h3>字段差异影响面</h3>
          <ul class="z044-register-list">
            <li v-for="item in z044FieldImpactMatrix" :key="item.field">
              <span>{{ item.field }}</span>
              <strong>{{ item.impact }}</strong>
              <em>{{ item.guard }}</em>
            </li>
          </ul>
        </section>

        <section
          class="z044-register-section"
          data-readonly-boundary="true"
          data-testid="z044-register-cancel-impact-preview"
        >
          <h3>撤销影响预览</h3>
          <p>{{ z044CancelImpactPreview }}</p>
        </section>

        <section
          class="z044-register-section"
          data-readonly-boundary="true"
          data-testid="z044-register-return-source-readback"
        >
          <h3>返回查询来源</h3>
          <p>{{ z044ReturnSourceReadback }}</p>
        </section>

        <section
          class="z044-register-section"
          data-readonly-boundary="true"
          data-testid="z044-register-readonly-confirm-gate"
          data-write-guard="guarded:z044-register-readonly-confirm-gate"
          data-write-request-success-allowed="false"
          data-real-write-action-added="false"
          data-guard-state="guarded-readonly"
        >
          <h3>只读确认 gate</h3>
          <p>{{ z044ReadonlyConfirmGate }}</p>
          <el-button
            plain
            type="warning"
            data-guard-entry="只读降级确认"
            data-guard-state="guarded-readonly"
            data-readonly-boundary="true"
            data-write-request-success-allowed="false"
            data-real-write-action-added="false"
            @click="confirmReadonlyDowngrade"
          >
            只读降级确认 guarded/readonly
          </el-button>
        </section>

        <section
          class="z044-register-section"
          data-readonly-boundary="true"
          data-testid="z044-register-submit-write-guard"
          data-write-guard="guarded:z044-register-submit-write-guard"
          data-write-request-success-allowed="false"
          data-real-write-action-added="false"
          data-guard-state="guarded-readonly"
        >
          <h3>提交登记 write guard</h3>
          <p>{{ z044SubmitWriteGuard }}</p>
          <el-tag
            data-guard-entry="提交登记"
            data-guard-state="guarded-readonly"
            data-write-request-success-allowed="false"
            effect="plain"
            type="info"
          >
            提交登记 guarded/readonly
          </el-tag>
        </section>

        <section
          class="z044-register-section"
          data-readonly-boundary="true"
          data-testid="z044-register-cancel-write-guard"
          data-write-guard="guarded:z044-register-cancel-write-guard"
          data-write-request-success-allowed="false"
          data-real-write-action-added="false"
          data-guard-state="guarded-readonly"
        >
          <h3>提交撤销 write guard</h3>
          <p>{{ z044CancelWriteGuard }}</p>
          <el-tag
            data-guard-entry="提交撤销"
            data-guard-state="guarded-readonly"
            data-write-request-success-allowed="false"
            effect="plain"
            type="warning"
          >
            提交撤销 guarded/readonly
          </el-tag>
        </section>

        <section
          class="z044-register-section"
          data-readonly-boundary="true"
          data-testid="z044-register-write-success-blocker"
          data-write-guard="guarded:z044-register-write-success-blocker"
          data-write-request-success-allowed="false"
          data-real-write-action-added="false"
          data-guard-state="guarded-readonly"
        >
          <h3>写成功阻断说明</h3>
          <p>{{ z044WriteSuccessBlocker }}</p>
        </section>
      </div>
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
const readonlyScenarioTag = computed<string>(() => resolveScenarioTag())
const readonlyRequestId = computed<string>(() => {
  const ticketKey = withScenarioCarrier(
    form.ticket_key,
    readonlyScenarioTag.value,
    mode.value === 'register' ? 'TK-REG' : 'TK-REV',
  )
  const sourceRef = withScenarioCarrier(
    form.source_ref,
    readonlyScenarioTag.value,
    mode.value === 'register' ? 'SRC-REG' : 'SRC-REV',
  )
  return buildWorkshopTicketRequestId({
    scenarioTag: readonlyScenarioTag.value,
    operation: mode.value,
    idempotencyKey: ticketKey,
    sourceRef,
    ticketKey,
    jobCard: form.job_card.trim() || 'job-card-draft',
    employeeOrOperator: form.employee.trim() || 'operator-local',
    batchNo: `${readonlyScenarioTag.value}-REGISTER-DRAFT`,
  })
})
const draftChangeSummary = computed(() => [
  {
    label: '登记/撤销模式',
    value: mode.value === 'register' ? '登记工票' : '撤销工票',
    state: 'local preview',
  },
  {
    label: '关键草稿字段',
    value: [readonlyDraft.value.ticket_key, readonlyDraft.value.job_card, readonlyDraft.value.employee]
      .filter(Boolean)
      .join(' / ') || '未填写',
    state: requiredFieldErrors.value.length === 0 ? 'ready for guard' : 'waiting for local validation',
  },
  {
    label: '来源或撤销原因',
    value: mode.value === 'register'
      ? (readonlyDraft.value.source_ref || '未填写来源单号')
      : (readonlyDraft.value.reason || '未填写撤销原因'),
    state: 'readonly only',
  },
])
const cancelReasonHint = computed<string>(() => (
  mode.value === 'reversal'
    ? `撤销原因将仅用于本地预览：${readonlyDraft.value.reason || '待填写'}；提交撤销已保持只读 guard。`
    : '切换至撤销工票后需填写原工票 ID 与撤销原因；撤销提交不会形成真实写请求成功。'
))
const returnRouteExplanation = computed<string>(() => (
  `返回列表固定指向 /workshop/tickets；来源 request_id=${readonlyRequestId.value} 仅用于只读追踪。`
))
const z043GuardedEntries = ['提交登记', '提交撤销', '只读降级确认']
const z043FieldDiffSummary = computed(() => [
  {
    field: 'ticket_key',
    current: readonlyDraft.value.ticket_key || '未填写',
    diff: readonlyDraft.value.ticket_key ? '本地草稿存在值' : '等待扫码或业务唯一键',
  },
  {
    field: 'job_card / employee',
    current: [readonlyDraft.value.job_card, readonlyDraft.value.employee].filter(Boolean).join(' / ') || '未填写',
    diff: requiredFieldErrors.value.some((field) => ['job_card', 'employee'].includes(field))
      ? '关键登记字段缺失'
      : '关键登记字段已满足本地校验',
  },
  {
    field: mode.value === 'register' ? 'source_ref' : 'reason',
    current: mode.value === 'register'
      ? (readonlyDraft.value.source_ref || '未填写')
      : (readonlyDraft.value.reason || '未填写'),
    diff: mode.value === 'register' ? '返回查询来源只读记录' : '撤销预览原因只读记录',
  },
])
const z043CancelPreviewSummary = computed<string>(() => (
  mode.value === 'reversal'
    ? `撤销预览仅本地展示：original_ticket_id=${readonlyDraft.value.original_ticket_id || '待填写'}，reason=${readonlyDraft.value.reason || '待填写'}。提交撤销仍被 guarded/readonly 拦截。`
    : '当前为登记模式；切换撤销后将展示 original_ticket_id、reason 与 request_id 预览，不会发送撤销写请求。'
))
const z043ReadonlyConfirmChain = computed<string>(() => (
  `确认链路：${mode.value === 'register' ? '提交登记' : '提交撤销'} -> 只读降级确认 -> request_id=${readonlyRequestId.value}，全程 dataWriteRequestSuccessAllowed=false。`
))
const z043ReturnSourceReadback = computed<string>(() => (
  `返回查询来源固定记录为 /workshop/tickets，scenario_tag=${readonlyScenarioTag.value}，来源单号=${readonlyDraft.value.source_ref || '未填写'}，只读 readback 不触发真实写成功。`
))
const z044DraftReadbackChain = computed<string>(() => (
  `草稿回读链路：${mode.value === 'register' ? '登记草稿' : '撤销草稿'} -> 本地字段校验 -> request_id=${readonlyRequestId.value} -> 只读确认 gate；不调用登记/撤销 API。`
))
const z044FieldImpactMatrix = computed(() => [
  {
    field: 'ticket_key',
    impact: readonlyDraft.value.ticket_key ? '用于本地幂等键 readback' : '缺失时阻断提交登记预览',
    guard: '只读差异影响，不写入',
  },
  {
    field: 'job_card / employee / process_name',
    impact: requiredFieldErrors.value.some((field) => ['job_card', 'employee', 'process_name'].includes(field))
      ? '关键登记字段缺失，进入只读确认前置提示'
      : '关键登记字段已满足本地草稿回读',
    guard: '提交登记 guarded/readonly',
  },
  {
    field: mode.value === 'register' ? 'source_ref' : 'original_ticket_id / reason',
    impact: mode.value === 'register'
      ? `返回查询来源=${readonlyDraft.value.source_ref || '未填写'}`
      : `撤销影响预览=${readonlyDraft.value.original_ticket_id || '待填写'} / ${readonlyDraft.value.reason || '待填写'}`,
    guard: mode.value === 'register' ? '提交登记 guarded/readonly' : '提交撤销 guarded/readonly',
  },
])
const z044CancelImpactPreview = computed<string>(() => (
  mode.value === 'reversal'
    ? `撤销影响预览仅本地展示：original_ticket_id=${readonlyDraft.value.original_ticket_id || '待填写'}，reason=${readonlyDraft.value.reason || '待填写'}，不会形成撤销写成功。`
    : '当前为登记模式；撤销影响面保持只读待命，切换撤销后回读 original_ticket_id、reason 与 request_id。'
))
const z044ReturnSourceReadback = computed<string>(() => (
  `返回查询来源固定为 /workshop/tickets，来源=${readonlyDraft.value.source || 'manual'}，source_ref=${readonlyDraft.value.source_ref || '未填写'}，scenario_tag=${readonlyScenarioTag.value}。`
))
const z044ReadonlyConfirmGate = computed<string>(() => (
  `只读确认 gate：${mode.value === 'register' ? '提交登记' : '提交撤销'} -> 只读降级确认 -> write_request_success_allowed=false。`
))
const z044SubmitWriteGuard = computed<string>(() => (
  `提交登记被 guarded/readonly 拦截：request_id=${readonlyRequestId.value}，dataRealWriteActionAdded=false。`
))
const z044CancelWriteGuard = computed<string>(() => (
  `提交撤销被 guarded/readonly 拦截：original_ticket_id=${readonlyDraft.value.original_ticket_id || '待填写'}，dataWriteRequestSuccessAllowed=false。`
))
const z044WriteSuccessBlocker = computed<string>(() => (
  '写成功阻断：提交登记、提交撤销、只读降级确认均只生成本地提示，write_request_success_observed 必须保持 false。'
))

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

const confirmReadonlyDowngrade = (): void => {
  guardedFeedback.value = `只读降级确认已记录为本地提示：request_id=${readonlyRequestId.value}，未发送登记/撤销写请求。`
  ElMessage.warning(guardedFeedback.value)
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

.z042-register-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-top: 14px;
}

.z042-register-section {
  min-height: 150px;
  padding: 12px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 6px;
  background: var(--el-fill-color-lighter);
}

.z042-register-section h3 {
  margin: 0 0 8px;
  font-size: 14px;
}

.z042-register-section p {
  margin: 0;
  color: var(--el-text-color-secondary);
  line-height: 1.6;
}

.z042-register-list {
  display: grid;
  gap: 6px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.z042-register-list li {
  display: grid;
  grid-template-columns: 88px minmax(0, 1fr);
  gap: 4px 8px;
  font-size: 12px;
}

.z042-register-list strong,
.z042-register-list em {
  min-width: 0;
  overflow-wrap: anywhere;
}

.z042-register-list em {
  grid-column: 2;
  color: var(--el-text-color-secondary);
  font-style: normal;
}

.z042-register-meta {
  margin-top: 8px !important;
  font-size: 12px;
  overflow-wrap: anywhere;
}

.z042-register-guards {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
}

.z043-register-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-top: 14px;
}

.z043-register-section {
  min-height: 156px;
  padding: 12px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 6px;
  background: var(--el-fill-color-blank);
}

.z043-register-section h3 {
  margin: 0 0 8px;
  font-size: 14px;
}

.z043-register-section p {
  margin: 0;
  color: var(--el-text-color-secondary);
  line-height: 1.6;
  overflow-wrap: anywhere;
}

.z043-register-list {
  display: grid;
  gap: 6px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.z043-register-list li {
  display: grid;
  grid-template-columns: 92px minmax(0, 1fr);
  gap: 4px 8px;
  font-size: 12px;
}

.z043-register-list strong,
.z043-register-list em {
  min-width: 0;
  overflow-wrap: anywhere;
}

.z043-register-list em {
  grid-column: 2;
  color: var(--el-text-color-secondary);
  font-style: normal;
}

.z043-register-guards {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
}

.z044-register-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-top: 14px;
}

.z044-register-section {
  min-height: 156px;
  padding: 12px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 6px;
  background: var(--el-fill-color-lighter);
}

.z044-register-section h3 {
  margin: 0 0 8px;
  font-size: 14px;
}

.z044-register-section p {
  margin: 0 0 10px;
  color: var(--el-text-color-secondary);
  line-height: 1.6;
  overflow-wrap: anywhere;
}

.z044-register-list {
  display: grid;
  gap: 6px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.z044-register-list li {
  display: grid;
  grid-template-columns: 92px minmax(0, 1fr);
  gap: 4px 8px;
  font-size: 12px;
}

.z044-register-list strong,
.z044-register-list em {
  min-width: 0;
  overflow-wrap: anywhere;
}

.z044-register-list em {
  grid-column: 2;
  color: var(--el-text-color-secondary);
  font-style: normal;
}

@media (max-width: 960px) {
  .z042-register-grid,
  .z043-register-grid,
  .z044-register-grid {
    grid-template-columns: 1fr;
  }
}
</style>
