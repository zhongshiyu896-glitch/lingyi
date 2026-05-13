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
        <el-form-item label="仓库">
          <el-input v-model="materialCheckForm.warehouse" placeholder="WIP Warehouse - LY" data-testid="production-plan-detail-material-check-warehouse" />
        </el-form-item>
      </el-form>
      <el-button type="primary" data-action-type="write" data-write-guard="guarded:readonly" data-testid="production-plan-detail-material-check-action" @click="runMaterialCheck">
        执行物料检查
      </el-button>
    </el-card>

    <el-card v-if="canRead && detail" shadow="never" data-testid="production-plan-detail-create-work-order-card">
      <template #header><span>create-work-order 候选入口</span></template>
      <el-alert
        type="info"
        :closable="false"
        show-icon
        title="当前为 local synthetic context + outbox-only 验证入口；sync-job-cards 继续冻结，internal worker 路径保持不变。"
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
        <el-form-item label="FG Warehouse">
          <el-input v-model="createWorkOrderForm.fg_warehouse" placeholder="FG Warehouse - LY" data-testid="production-plan-detail-create-fg-warehouse" />
        </el-form-item>
        <el-form-item label="WIP Warehouse">
          <el-input v-model="createWorkOrderForm.wip_warehouse" placeholder="WIP Warehouse - LY" data-testid="production-plan-detail-create-wip-warehouse" />
        </el-form-item>
        <el-form-item label="计划开工日">
          <el-date-picker
            v-model="createWorkOrderForm.start_date"
            type="date"
            value-format="YYYY-MM-DD"
            format="YYYY-MM-DD"
            placeholder="选择开工日期"
            data-testid="production-plan-detail-create-start-date"
          />
        </el-form-item>
        <el-form-item label="幂等键">
          <el-input v-model="createWorkOrderForm.idempotency_key" placeholder="idempotency key" data-testid="production-plan-detail-create-idempotency-key" />
        </el-form-item>
        <el-form-item label="Request ID">
          <el-input v-model="createWorkOrderForm.request_id" placeholder="request id" data-testid="production-plan-detail-create-request-id" />
        </el-form-item>
      </el-form>
      <div style="display: flex; gap: 8px" data-testid="production-plan-detail-create-work-order-actions">
        <el-button data-testid="production-plan-detail-create-work-order-reset" @click="resetCreateWorkOrderForm">重置</el-button>
        <el-button
          type="primary"
          data-action-type="write"
          data-write-guard="allowed:create-work-order-outbox-only"
          data-write-allowlist="create-work-order-outbox-only"
          data-testid="production-plan-detail-create-work-order-action"
          :loading="creatingWorkOrder"
          :disabled="creatingWorkOrder"
          @click="submitCreateWorkOrder"
        >
          创建 Work Order（候选）
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
        data-testid="production-plan-detail-permission-or-disabled-state"
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
  createProductionWorkOrder,
  fetchProductionPlanDetail,
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
const permissionReady = ref<boolean>(false)

const materialCheckForm = reactive({
  warehouse: 'WIP Warehouse - LY',
})
const createWorkOrderForm = reactive({
  fg_warehouse: 'FG Warehouse - LY',
  wip_warehouse: 'WIP Warehouse - LY',
  start_date: '',
  idempotency_key: '',
  request_id: '',
})

const canRead = computed<boolean>(() => permissionStore.state.buttonPermissions.read)
const canMaterialCheck = computed<boolean>(() => permissionStore.state.buttonPermissions.material_check)
const canWorkOrderCreate = computed<boolean>(() => permissionStore.state.buttonPermissions.work_order_create)

const planId = computed<number>(() => Number(route.query.id || '0'))
const hasValidPlanId = computed<boolean>(() => Number.isInteger(planId.value) && planId.value > 0)
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
    '当前仅冻结 sync-job-cards；create-work-order 走本地 outbox 候选入口，internal worker 路径保持不变。',
)
const normalizedCreateWorkOrderForm = computed(() => ({
  fg_warehouse: createWorkOrderForm.fg_warehouse.trim(),
  wip_warehouse: createWorkOrderForm.wip_warehouse.trim(),
  start_date: createWorkOrderForm.start_date.trim(),
  idempotency_key: createWorkOrderForm.idempotency_key.trim(),
  request_id: createWorkOrderForm.request_id.trim(),
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
const createWorkOrderGuardReason = computed<string>(() => {
  if (!canWorkOrderCreate.value) {
    return '无创建工单权限'
  }
  if (!detail.value) {
    return '生产计划详情不存在'
  }
  return createWorkOrderValidationError.value || ''
})

const MATERIAL_CHECK_ALLOWED_STATUSES = new Set<string>([
  'planned',
  'material_checked',
  'work_order_pending',
  'work_order_created',
])

const isMaterialCheckStatusAllowed = computed<boolean>(() => MATERIAL_CHECK_ALLOWED_STATUSES.has(status.value))
const normalizedMaterialCheckWarehouse = computed<string>(() => materialCheckForm.warehouse.trim())
const isMaterialCheckFormValid = computed<boolean>(() => normalizedMaterialCheckWarehouse.value.length > 0)

const materialCheckGuardReason = computed<string>(() => {
  if (!canMaterialCheck.value) {
    return '无物料检查权限'
  }
  if (!isMaterialCheckStatusAllowed.value) {
    return '当前状态不允许执行物料检查'
  }
  if (!isMaterialCheckFormValid.value) {
    return '仓库不能为空'
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

const buildIdempotencyKey = (prefix: string): string => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return `${prefix}-${crypto.randomUUID()}`
  }
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

const buildRequestId = (prefix: string): string => {
  const compact = prefix.replace(/[^A-Za-z0-9_.-]/g, '-').slice(0, 40)
  const random = Math.random().toString(36).slice(2, 10)
  return `${compact}-${Date.now()}-${random}`.slice(0, 64)
}

const guardedWriteAction = (actionLabel: string, reason = '当前为只读模式，已禁用写入操作'): void => {
  const message = `${actionLabel}：${reason}`
  guardedFeedback.value = message
  ElMessage.warning(message)
}

const resetCreateWorkOrderForm = (): void => {
  createWorkOrderForm.fg_warehouse = 'FG Warehouse - LY'
  createWorkOrderForm.wip_warehouse = 'WIP Warehouse - LY'
  createWorkOrderForm.start_date = ''
  createWorkOrderForm.idempotency_key = buildIdempotencyKey('production-create-work-order')
  createWorkOrderForm.request_id = buildRequestId('production-create-work-order')
}

const ensurePlanId = (): number => {
  if (!planId.value || Number.isNaN(planId.value)) {
    throw new Error('无效的生产计划 ID')
  }
  return planId.value
}

const loadDetail = async (): Promise<void> => {
  if (!canRead.value) {
    detail.value = null
    loadError.value = ''
    missingPlanId.value = false
    return
  }
  if (!hasValidPlanId.value) {
    detail.value = null
    loadError.value = ''
    missingPlanId.value = true
    return
  }
  missingPlanId.value = false
  loadError.value = ''
  loading.value = true
  try {
    const result = await fetchProductionPlanDetail(ensurePlanId())
    detail.value = result.data
    loadError.value = ''
  } catch (error) {
    const message = (error as Error).message || '加载生产计划详情失败'
    detail.value = null
    loadError.value = message
    ElMessage.error(message)
  } finally {
    loading.value = false
  }
}

const runMaterialCheck = (): void => {
  if (!canMaterialCheck.value) {
    guardedWriteAction('执行物料检查', '无物料检查权限')
    return
  }
  if (!isMaterialCheckStatusAllowed.value) {
    guardedWriteAction('执行物料检查', '当前状态不允许执行物料检查')
    return
  }
  if (!isMaterialCheckFormValid.value) {
    guardedWriteAction('执行物料检查', '仓库不能为空')
    return
  }
  guardedWriteAction('执行物料检查')
}

const submitCreateWorkOrder = async (): Promise<void> => {
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
      },
      normalizedCreateWorkOrderForm.value.request_id,
    )
    guardedFeedback.value = ''
    ElMessage.success('create-work-order 已写入本地 outbox')
    await loadDetail()
  } catch (error) {
    const message = (error as Error).message || '创建 Work Order 失败'
    guardedWriteAction('创建 Work Order', message)
  } finally {
    creatingWorkOrder.value = false
  }
}

const goBack = (): void => {
  router.push('/production/plans')
}

watch(
  () => planId.value,
  async () => {
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
  resetCreateWorkOrderForm()
  await loadDetail()
})
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
