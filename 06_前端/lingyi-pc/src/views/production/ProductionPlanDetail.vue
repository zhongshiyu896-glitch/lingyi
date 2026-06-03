<template>
  <div class="production-plan-detail-page" data-testid="production-plan-detail-page">
    <el-card shadow="never" v-loading="loading" data-testid="production-plan-detail-main-card">
      <template #header>
        <div class="header-row" data-testid="production-plan-detail-header">
          <span data-testid="production-plan-detail-title">生产计划详情</span>
          <el-button data-testid="production-plan-detail-back" @click="goBack">返回</el-button>
        </div>
      </template>

      <el-skeleton v-if="!permissionReady" :rows="4" animated data-testid="production-plan-detail-loading" />
      <el-empty
        v-else-if="!canRead"
        description="无生产计划查看权限"
        data-testid="production-plan-detail-permission-state"
      />

      <template v-else>
        <el-empty v-if="missingPlanId" description="请从生产计划列表进入详情页" data-testid="production-plan-detail-missing-id-state" />
        <el-descriptions v-else-if="detail" :column="3" border data-testid="production-plan-detail-main-fields">
          <el-descriptions-item label="计划单号"><span data-testid="production-plan-detail-field-plan-no">{{ detail.plan_no }}</span></el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag data-testid="production-plan-detail-status-tag">{{ statusLabel(detail.status) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="公司"><span data-testid="production-plan-detail-field-company">{{ detail.company }}</span></el-descriptions-item>
          <el-descriptions-item label="销售单">{{ detail.sales_order }}</el-descriptions-item>
          <el-descriptions-item label="销售单行">{{ detail.sales_order_item }}</el-descriptions-item>
          <el-descriptions-item label="客户">{{ detail.customer || '-' }}</el-descriptions-item>
          <el-descriptions-item label="款式"><span data-testid="production-plan-detail-field-item-code">{{ detail.item_code }}</span></el-descriptions-item>
          <el-descriptions-item label="BOM ID">{{ detail.bom_id }}</el-descriptions-item>
          <el-descriptions-item label="BOM 版本">{{ detail.bom_version || '-' }}</el-descriptions-item>
          <el-descriptions-item label="计划数量">{{ detail.planned_qty }}</el-descriptions-item>
          <el-descriptions-item label="计划开工日">{{ detail.planned_start_date || '-' }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ detail.created_at }}</el-descriptions-item>
        </el-descriptions>
        <el-alert
          v-else-if="loadError"
          type="error"
          :closable="false"
          show-icon
          :title="loadError"
          data-testid="production-plan-detail-error-state"
        />
        <el-empty v-else description="暂无生产计划详情数据" data-testid="production-plan-detail-empty-state" />
      </template>
    </el-card>

    <el-alert
      v-if="guardedFeedback"
      type="warning"
      :closable="false"
      show-icon
      :title="guardedFeedback"
      data-testid="production-plan-detail-guarded-feedback"
    />

    <el-card v-if="canRead && detail" shadow="never" data-testid="production-plan-detail-work-order-mapping">
      <template #header><span>Work Order 映射</span></template>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="Work Order"><span data-testid="production-plan-detail-work-order">{{ currentWorkOrder || '-' }}</span></el-descriptions-item>
        <el-descriptions-item label="同步状态">{{ workOrderSyncStatusLabel }}</el-descriptions-item>
        <el-descriptions-item label="ERP Docstatus">{{ detail?.erpnext_docstatus ?? '-' }}</el-descriptions-item>
        <el-descriptions-item label="ERP 状态">{{ detail?.erpnext_status || '-' }}</el-descriptions-item>
        <el-descriptions-item label="最新错误码">{{ detail?.latest_work_order_outbox?.error_code || '-' }}</el-descriptions-item>
        <el-descriptions-item label="最近同步时间">{{ detail?.last_synced_at || '-' }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <el-card v-if="canRead && detail" shadow="never" data-testid="production-plan-detail-material-check-card">
      <template #header><span>物料检查</span></template>
      <el-alert
        v-if="materialCheckGuardReason"
        type="warning"
        :closable="false"
        show-icon
        :title="materialCheckGuardReason"
        style="margin-bottom: 12px"
      />
      <el-form :model="materialCheckForm" label-width="140px" data-testid="production-plan-detail-material-check-form">
        <el-form-item label="Scenario Tag">
          <el-input v-model="scenarioTag" readonly data-testid="production-plan-detail-material-check-scenario-tag" />
        </el-form-item>
        <el-form-item label="仓库">
          <el-input
            v-model="materialCheckForm.warehouse"
            placeholder="WIP Warehouse - LY"
            :readonly="readOnlyDetailMode"
            data-testid="production-plan-detail-material-check-warehouse"
          />
        </el-form-item>
        <el-form-item label="幂等键">
          <el-input
            v-model="materialCheckForm.idempotency_key"
            placeholder="idempotency key"
            :readonly="readOnlyDetailMode"
            data-testid="production-plan-detail-material-check-idempotency-key"
          />
        </el-form-item>
        <el-form-item label="Request ID">
          <el-input
            v-model="materialCheckForm.request_id"
            placeholder="request id"
            :readonly="readOnlyDetailMode"
            data-testid="production-plan-detail-material-check-request-id"
          />
        </el-form-item>
      </el-form>
      <div style="display: flex; gap: 8px" data-testid="production-plan-detail-material-check-actions">
        <el-button
          data-testid="production-plan-detail-material-check-reset"
          :disabled="readOnlyDetailMode"
          @click="resetMaterialCheckForm"
        >
          重置
        </el-button>
        <el-button
          type="primary"
          data-action-type="write"
          data-write-guard="readonly:material-check"
          data-testid="production-plan-detail-material-check-action"
          :loading="runningMaterialCheck"
          :disabled="readOnlyDetailMode || runningMaterialCheck || Boolean(materialCheckGuardReason)"
          @click="runMaterialCheck"
        >
          执行物料检查
        </el-button>
      </div>
    </el-card>

    <el-card v-if="canRead && detail" shadow="never" data-testid="production-plan-detail-create-work-order-card">
      <template #header><span>create-work-order 候选入口</span></template>
      <el-alert
        type="info"
        :closable="false"
        show-icon
        title="当前为 local synthetic context：create-work-order 与 sync-job-cards 仅走 local-only 受控写入口，internal worker 路径保持禁用。"
        data-testid="production-plan-detail-local-context-mode"
        style="margin-bottom: 12px"
      />
      <el-alert
        v-if="createWorkOrderGuardReason"
        type="warning"
        :closable="false"
        show-icon
        :title="createWorkOrderGuardReason"
        style="margin-bottom: 12px"
      />
      <el-form :model="createWorkOrderForm" label-width="140px" data-testid="production-plan-detail-create-work-order-form">
        <el-form-item label="Scenario Tag">
          <el-input v-model="scenarioTag" readonly data-testid="production-plan-detail-create-scenario-tag" />
        </el-form-item>
        <el-form-item label="FG Warehouse">
          <el-input
            v-model="createWorkOrderForm.fg_warehouse"
            placeholder="FG Warehouse - LY"
            :readonly="readOnlyDetailMode"
            data-testid="production-plan-detail-create-fg-warehouse"
          />
        </el-form-item>
        <el-form-item label="WIP Warehouse">
          <el-input
            v-model="createWorkOrderForm.wip_warehouse"
            placeholder="WIP Warehouse - LY"
            :readonly="readOnlyDetailMode"
            data-testid="production-plan-detail-create-wip-warehouse"
          />
        </el-form-item>
        <el-form-item label="计划开工日">
          <el-date-picker
            v-model="createWorkOrderForm.start_date"
            type="date"
            value-format="YYYY-MM-DD"
            format="YYYY-MM-DD"
            placeholder="选择开工日期"
            :disabled="readOnlyDetailMode"
            data-testid="production-plan-detail-create-start-date"
          />
        </el-form-item>
        <el-form-item label="幂等键">
          <el-input
            v-model="createWorkOrderForm.idempotency_key"
            placeholder="idempotency key"
            :readonly="readOnlyDetailMode"
            data-testid="production-plan-detail-create-idempotency-key"
          />
        </el-form-item>
        <el-form-item label="Request ID">
          <el-input
            v-model="createWorkOrderForm.request_id"
            placeholder="request id"
            :readonly="readOnlyDetailMode"
            data-testid="production-plan-detail-create-request-id"
          />
        </el-form-item>
      </el-form>
      <div style="display: flex; gap: 8px" data-testid="production-plan-detail-create-work-order-actions">
        <el-button
          data-testid="production-plan-detail-create-work-order-reset"
          :disabled="readOnlyDetailMode"
          @click="resetCreateWorkOrderForm"
        >
          重置
        </el-button>
        <el-button
          type="primary"
          data-action-type="write"
          data-write-guard="readonly:create-work-order-outbox-only"
          data-write-allowlist="create-work-order-outbox-only"
          data-testid="production-plan-detail-create-work-order-action"
          :loading="creatingWorkOrder"
          :disabled="readOnlyDetailMode || creatingWorkOrder || Boolean(createWorkOrderGuardReason)"
          @click="submitCreateWorkOrder"
        >
          创建 Work Order（候选）
        </el-button>
      </div>
    </el-card>

    <el-card v-if="canRead && detail" shadow="never" data-testid="production-plan-detail-sync-job-cards-card">
      <template #header><span>sync-job-cards 主入口</span></template>
      <el-alert
        v-if="syncJobCardsGuardReason"
        type="warning"
        :closable="false"
        show-icon
        :title="syncJobCardsGuardReason"
        style="margin-bottom: 12px"
      />
      <el-form :model="syncJobCardsForm" label-width="140px" data-testid="production-plan-detail-sync-job-cards-form">
        <el-form-item label="Scenario Tag">
          <el-input v-model="scenarioTag" readonly data-testid="production-plan-detail-sync-scenario-tag" />
        </el-form-item>
        <el-form-item label="Work Order">
          <el-input :model-value="currentWorkOrder || '-'" readonly data-testid="production-plan-detail-sync-work-order" />
        </el-form-item>
        <el-form-item label="幂等键">
          <el-input
            v-model="syncJobCardsForm.idempotency_key"
            placeholder="idempotency key"
            :readonly="readOnlyDetailMode"
            data-testid="production-plan-detail-sync-idempotency-key"
          />
        </el-form-item>
        <el-form-item label="Request ID">
          <el-input
            v-model="syncJobCardsForm.request_id"
            placeholder="request id"
            :readonly="readOnlyDetailMode"
            data-testid="production-plan-detail-sync-request-id"
          />
        </el-form-item>
        <el-form-item label="Source Ref">
          <el-input
            v-model="syncJobCardsForm.source_ref"
            placeholder="scenario|company|plan_id|plan_no_or_work_order|item_code|operation"
            :readonly="readOnlyDetailMode"
            data-testid="production-plan-detail-sync-source-ref"
          />
        </el-form-item>
      </el-form>
      <div style="display: flex; gap: 8px" data-testid="production-plan-detail-sync-job-cards-actions">
        <el-button
          data-testid="production-plan-detail-sync-job-cards-reset"
          :disabled="readOnlyDetailMode"
          @click="resetSyncJobCardsForm"
        >
          重置
        </el-button>
        <el-button
          type="primary"
          data-action-type="write"
          data-write-guard="readonly:sync-job-cards-local-only"
          data-write-allowlist="sync-job-cards"
          data-testid="production-plan-detail-sync-job-cards-action"
          :loading="syncingJobCards"
          :disabled="readOnlyDetailMode || syncingJobCards || Boolean(syncJobCardsGuardReason)"
          @click="submitSyncJobCards"
        >
          执行 sync-job-cards
        </el-button>
      </div>
    </el-card>

    <el-card v-if="canRead && detail" shadow="never" data-testid="production-plan-detail-write-entry-status">
      <template #header><span>写入口状态</span></template>
      <el-alert
        type="warning"
        :closable="false"
        show-icon
        :title="writeEntryFrozenMessage"
        data-readonly-mode="true"
        data-write-guard="readonly:production-plan-detail"
        data-testid="production-plan-detail-permission-or-disabled-state"
      />
      <el-alert
        type="info"
        :closable="false"
        show-icon
        title="本页仅用于生产计划详情只读核验；物料检查、Work Order 创建与工序卡同步入口均已禁用。"
        data-testid="production-plan-detail-readonly-state"
      />
    </el-card>

    <el-card v-if="canRead && detail" shadow="never" data-testid="production-plan-detail-material-snapshot-card">
      <template #header><span>物料检查快照</span></template>
      <el-alert
        type="info"
        :closable="false"
        show-icon
        title="可用库存为后端快照；未接库存实时快照前仅作参考。"
      />
      <el-table
        :data="detail?.material_snapshots || []"
        border
        style="margin-top: 12px"
        empty-text="暂无物料检查快照"
        data-testid="production-plan-detail-material-snapshot-table"
      >
        <el-table-column prop="material_item_code" label="物料编码" min-width="160" />
        <el-table-column prop="qty_per_piece" label="单件用量" width="110" />
        <el-table-column prop="loss_rate" label="损耗率" width="100" />
        <el-table-column prop="required_qty" label="需求数量" width="110" />
        <el-table-column prop="warehouse" label="仓库" min-width="140" />
        <el-table-column prop="available_qty" label="可用库存" width="110" />
        <el-table-column prop="shortage_qty" label="缺口数量" width="110" />
        <el-table-column label="检查时间" min-width="170">
          <template #default="scope">{{ scope.row.checked_at || '-' }}</template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card v-if="canRead && detail" shadow="never" data-testid="production-plan-detail-job-card-mapping">
      <template #header><span>Job Card 映射</span></template>
      <el-table
        :data="detail?.job_cards || []"
        border
        empty-text="暂无 Job Card 映射数据"
        data-testid="production-plan-detail-job-card-table"
      >
        <el-table-column prop="job_card" label="Job Card" min-width="180" />
        <el-table-column label="Work Order" min-width="180">
          <template #default>{{ currentWorkOrder || '-' }}</template>
        </el-table-column>
        <el-table-column prop="operation" label="工序" min-width="150" />
        <el-table-column prop="operation_sequence" label="工序序号" width="100" />
        <el-table-column prop="expected_qty" label="应生产数量" width="120" />
        <el-table-column prop="completed_qty" label="已完成数量" width="120" />
        <el-table-column prop="erpnext_status" label="ERP 状态" min-width="120" />
        <el-table-column prop="synced_at" label="同步时间" min-width="180" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  checkProductionMaterials,
  createProductionWorkOrder,
  fetchProductionPlans,
  fetchProductionPlanDetail,
  syncProductionJobCards,
  type ProductionPlanDetailData,
} from '@/api/production'
import { usePermissionStore } from '@/stores/permission'

const route = useRoute()
const router = useRouter()
const permissionStore = usePermissionStore()

const detail = ref<ProductionPlanDetailData | null>(null)
const missingPlanId = ref<boolean>(false)
const loadError = ref<string>('')
const guardedFeedback = ref<string>('')
const loading = ref<boolean>(false)
const creatingWorkOrder = ref<boolean>(false)
const syncingJobCards = ref<boolean>(false)
const runningMaterialCheck = ref<boolean>(false)
const permissionReady = ref<boolean>(false)
const scenarioTag = ref<string>('')
const fallbackPlanId = ref<number | null>(null)
const PRODUCTION_LOCAL_DETAIL_FROZEN_REASON =
  '受控写门禁：当前为 local-only 可用切片，create-work-order 与 sync-job-cards 保持冻结。'

const materialCheckForm = reactive({
  warehouse: 'WIP Warehouse - LY',
  idempotency_key: '',
  request_id: '',
})
const createWorkOrderForm = reactive({
  fg_warehouse: 'FG Warehouse - LY',
  wip_warehouse: 'WIP Warehouse - LY',
  start_date: '',
  idempotency_key: '',
  request_id: '',
})
const syncJobCardsForm = reactive({
  idempotency_key: '',
  request_id: '',
  source_ref: '',
})

const canRead = computed<boolean>(() => permissionStore.state.buttonPermissions.read)
const canMaterialCheck = computed<boolean>(() => permissionStore.state.buttonPermissions.material_check)
const canWorkOrderCreate = computed<boolean>(() => permissionStore.state.buttonPermissions.work_order_create)
const canJobCardSync = computed<boolean>(() => permissionStore.state.buttonPermissions.job_card_sync)
const readOnlyDetailMode = computed<boolean>(() => true)

const parsePositiveInteger = (value: unknown): number => {
  const raw = Array.isArray(value) ? value[0] : value
  const parsed = Number(raw || '0')
  return Number.isInteger(parsed) && parsed > 0 ? parsed : 0
}

const parseStringQuery = (value: unknown): string => {
  const raw = Array.isArray(value) ? value[0] : value
  return typeof raw === 'string' ? raw.trim() : ''
}

const routePlanId = computed<number>(() => parsePositiveInteger(route.query.id))
const hasValidPlanId = computed<boolean>(() => routePlanId.value > 0)
const status = computed<string>(() => detail.value?.status || '')
const currentWorkOrder = computed<string>(
  () => detail.value?.work_order || detail.value?.latest_work_order_outbox?.erpnext_work_order || '',
)
const workOrderSyncStatusLabel = computed<string>(() =>
  syncStatusLabel(detail.value?.sync_status || detail.value?.latest_work_order_outbox?.status || null),
)
const writeEntryFrozenMessage = computed<string>(
  () =>
    detail.value?.write_entry_frozen_reason ||
    '当前生产计划详情处于只读验收模式；物料检查、Work Order 创建与工序卡同步入口保持禁用。',
)
const normalizedCreateWorkOrderForm = computed(() => ({
  fg_warehouse: createWorkOrderForm.fg_warehouse.trim(),
  wip_warehouse: createWorkOrderForm.wip_warehouse.trim(),
  start_date: createWorkOrderForm.start_date.trim(),
  idempotency_key: createWorkOrderForm.idempotency_key.trim(),
  request_id: createWorkOrderForm.request_id.trim(),
}))
const normalizedMaterialCheckForm = computed(() => ({
  warehouse: materialCheckForm.warehouse.trim(),
  idempotency_key: materialCheckForm.idempotency_key.trim(),
  request_id: materialCheckForm.request_id.trim(),
}))
const normalizedSyncJobCardsForm = computed(() => ({
  idempotency_key: syncJobCardsForm.idempotency_key.trim(),
  request_id: syncJobCardsForm.request_id.trim(),
  source_ref: syncJobCardsForm.source_ref.trim(),
}))
const createWorkOrderValidationError = computed<string | null>(() => {
  if (!normalizedCreateWorkOrderForm.value.fg_warehouse) {
    return 'fg_warehouse 不能为空'
  }
  if (!normalizedCreateWorkOrderForm.value.wip_warehouse) {
    return 'wip_warehouse 不能为空'
  }
  if (!normalizedCreateWorkOrderForm.value.start_date) {
    return 'start_date 不能为空'
  }
  if (!normalizedCreateWorkOrderForm.value.idempotency_key) {
    return 'idempotency_key 不能为空'
  }
  if (!normalizedCreateWorkOrderForm.value.request_id) {
    return 'request_id 不能为空'
  }
  return null
})
const materialCheckValidationError = computed<string | null>(() => {
  if (!normalizedMaterialCheckForm.value.warehouse) {
    return 'warehouse 不能为空'
  }
  if (!normalizedMaterialCheckForm.value.idempotency_key) {
    return 'idempotency_key 不能为空'
  }
  if (!normalizedMaterialCheckForm.value.request_id) {
    return 'request_id 不能为空'
  }
  return null
})
const syncJobCardsValidationError = computed<string | null>(() => {
  if (!currentWorkOrder.value) {
    return '当前无可同步的 Work Order'
  }
  if (!normalizedSyncJobCardsForm.value.idempotency_key) {
    return 'idempotency_key 不能为空'
  }
  if (!normalizedSyncJobCardsForm.value.request_id) {
    return 'request_id 不能为空'
  }
  if (!normalizedSyncJobCardsForm.value.source_ref) {
    return 'source_ref 不能为空'
  }
  return null
})
const createWorkOrderGuardReason = computed<string>(() => {
  if (readOnlyDetailMode.value) {
    return writeEntryFrozenMessage.value
  }
  if (!canWorkOrderCreate.value) {
    return '无创建工单权限'
  }
  if (!detail.value) {
    return '生产计划详情不存在'
  }
  return createWorkOrderValidationError.value || ''
})
const syncJobCardsGuardReason = computed<string>(() => {
  if (readOnlyDetailMode.value) {
    return writeEntryFrozenMessage.value
  }
  if (!canJobCardSync.value) {
    return '无同步工序卡权限'
  }
  if (!detail.value) {
    return '生产计划详情不存在'
  }
  return syncJobCardsValidationError.value || ''
})

const MATERIAL_CHECK_ALLOWED_STATUSES = new Set<string>([
  'planned',
  'material_checked',
  'work_order_pending',
  'work_order_created',
])

const isMaterialCheckStatusAllowed = computed<boolean>(() => MATERIAL_CHECK_ALLOWED_STATUSES.has(status.value))
const materialCheckGuardReason = computed<string>(() => {
  if (readOnlyDetailMode.value) {
    return writeEntryFrozenMessage.value
  }
  if (!canMaterialCheck.value) {
    return '无物料检查权限'
  }
  if (!isMaterialCheckStatusAllowed.value) {
    return '当前状态不允许执行物料检查'
  }
  if (materialCheckValidationError.value) {
    return materialCheckValidationError.value
  }
  return ''
})

const statusLabel = (value: string): string => {
  const labels: Record<string, string> = {
    draft: '草稿',
    planned: '已计划',
    material_checked: '已物料检查',
    work_order_pending: '工单待同步',
    work_order_created: '已创建工单',
    job_cards_synced: '工序卡已同步',
    cancelled: '已取消',
    failed: '失败',
    pending: '待同步',
    processing: '同步中',
    succeeded: '已同步',
    dead: '死信',
    blocked_scope: '范围阻断',
  }
  return labels[value] || value
}

const syncStatusLabel = (value?: string | null): string => {
  if (!value) return '-'
  const labels: Record<string, string> = {
    pending: '待同步',
    processing: '同步中',
    succeeded: '已同步',
    failed: '失败待重试',
    dead: '死信',
    blocked_scope: '范围阻断',
  }
  return labels[value] || value
}

const buildScenarioTag = (): string => {
  const now = new Date()
  const yyyy = String(now.getFullYear())
  const mm = String(now.getMonth() + 1).padStart(2, '0')
  const dd = String(now.getDate()).padStart(2, '0')
  const seq = String(Math.floor(Math.random() * 1000)).padStart(3, '0')
  return `Z003-PROD-PLAN-DETAIL-${yyyy}${mm}${dd}-${seq}`
}

const ensureScenarioTag = (): string => {
  const value = scenarioTag.value.trim()
  if (value) return value
  scenarioTag.value = buildScenarioTag()
  return scenarioTag.value
}

const buildCarrierIdempotencyKey = (operationCode: string): string => {
  const tag = ensureScenarioTag()
  const random = Math.random().toString(36).slice(2, 10).toUpperCase()
  return `${tag}-ID-${operationCode}-${random}`.slice(0, 64)
}

const buildCarrierRequestId = (operationCode: string): string => {
  const tag = ensureScenarioTag()
  const random = Math.random().toString(36).slice(2, 8).toUpperCase()
  return `${tag}-RQ-${operationCode}-${random}`.slice(0, 64)
}

const buildSyntheticDetail = (): ProductionPlanDetailData => {
  const today = new Date().toISOString()
  return {
    id: routePlanId.value || 900001,
    plan_no: parseStringQuery(route.query.plan_no) || 'PP-LOCAL-260601',
    company: parseStringQuery(route.query.company) || 'LY-LOCAL-TEST',
    sales_order: parseStringQuery(route.query.sales_order) || 'SO-LOCAL-260601',
    sales_order_item: 'SOI-LOCAL-260601',
    customer: parseStringQuery(route.query.customer) || '本地样例客户',
    item_code: parseStringQuery(route.query.item_code) || 'ITEM-A',
    bom_id: parsePositiveInteger(route.query.bom_id) || 101,
    bom_version: 'vlocal',
    planned_qty: parseStringQuery(route.query.planned_qty) || '180',
    planned_start_date: parseStringQuery(route.query.planned_start_date) || '2026-06-03',
    status: parseStringQuery(route.query.status) || 'planned',
    work_order: null,
    erpnext_docstatus: null,
    erpnext_status: null,
    sync_status: 'blocked_scope',
    last_synced_at: null,
    latest_work_order_outbox: null,
    write_entry_frozen: true,
    write_entry_frozen_reason: PRODUCTION_LOCAL_DETAIL_FROZEN_REASON,
    material_snapshots: [
      {
        material_item_code: 'MAT-A',
        warehouse: 'WIP Warehouse - LY',
        qty_per_piece: '1.500000',
        loss_rate: '0.100000',
        required_qty: '297.000000',
        available_qty: '0.000000',
        shortage_qty: '297.000000',
        checked_at: null,
      },
    ],
    job_cards: [],
    created_at: today,
    updated_at: today,
  }
}

const guardedWriteAction = (actionLabel: string, reason = '当前为只读模式，已禁用写入操作'): void => {
  const message = `${actionLabel}：${reason}`
  guardedFeedback.value = message
  ElMessage.warning(message)
}

const resetMaterialCheckForm = (): void => {
  materialCheckForm.warehouse = 'WIP Warehouse - LY'
  materialCheckForm.idempotency_key = buildCarrierIdempotencyKey('MC')
  materialCheckForm.request_id = buildCarrierRequestId('MC')
}

const resetCreateWorkOrderForm = (): void => {
  createWorkOrderForm.fg_warehouse = 'FG Warehouse - LY'
  createWorkOrderForm.wip_warehouse = 'WIP Warehouse - LY'
  createWorkOrderForm.start_date = ''
  createWorkOrderForm.idempotency_key = buildCarrierIdempotencyKey('CWO')
  createWorkOrderForm.request_id = buildCarrierRequestId('CWO')
}

const buildSyncSourceRef = (workOrder: string): string => {
  const scenario = ensureScenarioTag()
  const company = detail.value?.company || ''
  const planIdToken = detail.value ? String(detail.value.id) : ''
  const planMarker = workOrder || detail.value?.plan_no || ''
  const itemCode = detail.value?.item_code || ''
  return [scenario, company, planIdToken, planMarker, itemCode, 'sync_job_cards'].join('|')
}

const resetSyncJobCardsForm = (): void => {
  const workOrder = currentWorkOrder.value
  syncJobCardsForm.idempotency_key = buildCarrierIdempotencyKey('SJC')
  syncJobCardsForm.request_id = buildCarrierRequestId('SJC')
  syncJobCardsForm.source_ref = buildSyncSourceRef(workOrder)
}

const ensurePlanId = (): number => {
  const targetPlanId = hasValidPlanId.value ? routePlanId.value : fallbackPlanId.value || 0
  if (!targetPlanId || Number.isNaN(targetPlanId)) {
    throw new Error('无效的生产计划 ID')
  }
  return targetPlanId
}

const loadDetail = async (): Promise<void> => {
  if (!canRead.value) {
    detail.value = null
    loadError.value = ''
    missingPlanId.value = false
    return
  }
  missingPlanId.value = false
  loadError.value = ''
  loading.value = true
  try {
    if (parseStringQuery(route.query.synthetic) === '1') {
      detail.value = buildSyntheticDetail()
      guardedFeedback.value = '当前展示 synthetic detail，只用于 local-only 可用切片。'
      return
    }
    if (!hasValidPlanId.value) {
      const firstPlanResponse = await fetchProductionPlans({ page: 1, page_size: 1 })
      fallbackPlanId.value = firstPlanResponse.data.items[0]?.id || null
    } else {
      fallbackPlanId.value = routePlanId.value
    }
    if (!fallbackPlanId.value) {
      detail.value = buildSyntheticDetail()
      guardedFeedback.value = '未读取到本地生产计划记录，已回退到 synthetic detail。'
      return
    }
    const result = await fetchProductionPlanDetail(ensurePlanId())
    detail.value = result.data
    guardedFeedback.value = hasValidPlanId.value ? '' : '未提供计划 ID，已回退到首条本地生产计划详情。'
    loadError.value = ''
  } catch (error) {
    const message = (error as Error).message || '加载生产计划详情失败'
    detail.value = buildSyntheticDetail()
    loadError.value = ''
    guardedFeedback.value = `加载详情失败，已回退到 synthetic detail：${message}`
  } finally {
    loading.value = false
  }
}

const runMaterialCheck = async (): Promise<void> => {
  if (readOnlyDetailMode.value) {
    guardedWriteAction('执行物料检查', writeEntryFrozenMessage.value)
    return
  }
  if (!canMaterialCheck.value) {
    guardedWriteAction('执行物料检查', '无物料检查权限')
    return
  }
  if (!isMaterialCheckStatusAllowed.value) {
    guardedWriteAction('执行物料检查', '当前状态不允许执行物料检查')
    return
  }
  if (materialCheckValidationError.value) {
    guardedWriteAction('执行物料检查', materialCheckValidationError.value)
    return
  }
  if (!detail.value) {
    guardedWriteAction('执行物料检查', '生产计划详情不存在')
    return
  }
  try {
    runningMaterialCheck.value = true
    await checkProductionMaterials(
      ensurePlanId(),
      {
        warehouse: normalizedMaterialCheckForm.value.warehouse,
        idempotency_key: normalizedMaterialCheckForm.value.idempotency_key,
        scenario_tag: ensureScenarioTag(),
        operation: 'material_check',
        plan_id: ensurePlanId(),
        sales_order: detail.value.sales_order,
        sales_order_item: detail.value.sales_order_item,
        item_code: detail.value.item_code,
        bom_id: Number(detail.value.bom_id),
        request_id: normalizedMaterialCheckForm.value.request_id,
      },
      normalizedMaterialCheckForm.value.request_id,
    )
    guardedFeedback.value = ''
    ElMessage.success('物料检查已写入并回读')
    await loadDetail()
  } catch (error) {
    const message = (error as Error).message || '执行物料检查失败'
    guardedWriteAction('执行物料检查', message)
  } finally {
    runningMaterialCheck.value = false
  }
}

const submitCreateWorkOrder = async (): Promise<void> => {
  if (readOnlyDetailMode.value) {
    guardedWriteAction('创建 Work Order', writeEntryFrozenMessage.value)
    return
  }
  if (!canWorkOrderCreate.value) {
    guardedWriteAction('创建 Work Order', '无创建工单权限')
    return
  }
  if (!detail.value) {
    guardedWriteAction('创建 Work Order', '生产计划详情不存在')
    return
  }
  const validationError = createWorkOrderValidationError.value
  if (validationError) {
    guardedWriteAction('创建 Work Order', validationError)
    return
  }
  try {
    creatingWorkOrder.value = true
    await createProductionWorkOrder(
      ensurePlanId(),
      {
        fg_warehouse: normalizedCreateWorkOrderForm.value.fg_warehouse,
        wip_warehouse: normalizedCreateWorkOrderForm.value.wip_warehouse,
        start_date: normalizedCreateWorkOrderForm.value.start_date,
        idempotency_key: normalizedCreateWorkOrderForm.value.idempotency_key,
        scenario_tag: ensureScenarioTag(),
        operation: 'create_work_order',
        plan_id: ensurePlanId(),
        sales_order: detail.value.sales_order,
        sales_order_item: detail.value.sales_order_item,
        item_code: detail.value.item_code,
        bom_id: Number(detail.value.bom_id),
        request_id: normalizedCreateWorkOrderForm.value.request_id,
      },
      normalizedCreateWorkOrderForm.value.request_id,
    )
    guardedFeedback.value = ''
    ElMessage.success('create-work-order 已写入本地 outbox')
    await loadDetail()
    resetSyncJobCardsForm()
  } catch (error) {
    const message = (error as Error).message || '创建 Work Order 失败'
    guardedWriteAction('创建 Work Order', message)
  } finally {
    creatingWorkOrder.value = false
  }
}

const submitSyncJobCards = async (): Promise<void> => {
  if (readOnlyDetailMode.value) {
    guardedWriteAction('执行 sync-job-cards', writeEntryFrozenMessage.value)
    return
  }
  if (!canJobCardSync.value) {
    guardedWriteAction('执行 sync-job-cards', '无同步工序卡权限')
    return
  }
  if (!detail.value) {
    guardedWriteAction('执行 sync-job-cards', '生产计划详情不存在')
    return
  }
  const workOrder = currentWorkOrder.value
  if (!workOrder) {
    guardedWriteAction('执行 sync-job-cards', '当前无可同步的 Work Order')
    return
  }
  const validationError = syncJobCardsValidationError.value
  if (validationError) {
    guardedWriteAction('执行 sync-job-cards', validationError)
    return
  }

  try {
    syncingJobCards.value = true
    await syncProductionJobCards(
      workOrder,
      {
        idempotency_key: normalizedSyncJobCardsForm.value.idempotency_key,
        scenario_tag: ensureScenarioTag(),
        operation: 'sync_job_cards',
        plan_id: ensurePlanId(),
        plan_no_or_work_order: workOrder,
        company: detail.value.company,
        item_code: detail.value.item_code,
        source_ref: normalizedSyncJobCardsForm.value.source_ref,
        request_id: normalizedSyncJobCardsForm.value.request_id,
      },
      normalizedSyncJobCardsForm.value.request_id,
    )
    guardedFeedback.value = ''
    ElMessage.success('sync-job-cards 已完成并回读')
    await loadDetail()
    resetSyncJobCardsForm()
  } catch (error) {
    const message = (error as Error).message || '执行 sync-job-cards 失败'
    guardedWriteAction('执行 sync-job-cards', message)
  } finally {
    syncingJobCards.value = false
  }
}

const goBack = (): void => {
  router.push('/production/plans')
}

watch(
  () => route.fullPath,
  async () => {
    fallbackPlanId.value = null
    await loadDetail()
  },
)

onMounted(async () => {
  try {
    await permissionStore.loadCurrentUser()
    await permissionStore.loadModuleActions('production')
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    permissionReady.value = true
  }
  scenarioTag.value = String(route.query.scenario || '').trim() || buildScenarioTag()
  resetMaterialCheckForm()
  resetCreateWorkOrderForm()
  await loadDetail()
  resetSyncJobCardsForm()
})

watch(
  () => detail.value,
  (current) => {
    if (!current) {
      return
    }
    const currentSourceRef = normalizedSyncJobCardsForm.value.source_ref
    if (!currentSourceRef) {
      resetSyncJobCardsForm()
      return
    }
    const parts = currentSourceRef.split('|')
    if (parts.length !== 6) {
      syncJobCardsForm.source_ref = buildSyncSourceRef(currentWorkOrder.value)
      return
    }
    const marker = currentWorkOrder.value || current.plan_no
    if (marker && parts[3] !== marker) {
      syncJobCardsForm.source_ref = buildSyncSourceRef(currentWorkOrder.value)
    }
  },
  { deep: false },
)
</script>

<style scoped>
.production-plan-detail-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
