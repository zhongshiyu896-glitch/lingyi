<template>
  <div class="production-plan-detail-page">
    <el-card shadow="never" v-loading="loading">
      <template #header>
        <div class="header-row">
          <span>生产计划详情</span>
          <el-button @click="goBack">返回</el-button>
        </div>
      </template>

      <el-empty v-if="!canRead" description="无生产计划查看权限" />

      <template v-else>
        <el-descriptions v-if="detail" :column="3" border>
          <el-descriptions-item label="计划单号">{{ detail.plan_no }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag>{{ statusLabel(detail.status) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="公司">{{ detail.company }}</el-descriptions-item>
          <el-descriptions-item label="销售单">{{ detail.sales_order }}</el-descriptions-item>
          <el-descriptions-item label="销售单行">{{ detail.sales_order_item }}</el-descriptions-item>
          <el-descriptions-item label="客户">{{ detail.customer || '-' }}</el-descriptions-item>
          <el-descriptions-item label="款式">{{ detail.item_code }}</el-descriptions-item>
          <el-descriptions-item label="BOM ID">{{ detail.bom_id }}</el-descriptions-item>
          <el-descriptions-item label="BOM 版本">{{ detail.bom_version || '-' }}</el-descriptions-item>
          <el-descriptions-item label="计划数量">{{ detail.planned_qty }}</el-descriptions-item>
          <el-descriptions-item label="计划开工日">{{ detail.planned_start_date || '-' }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ detail.created_at }}</el-descriptions-item>
        </el-descriptions>
      </template>
    </el-card>

    <el-card v-if="canRead" shadow="never">
      <template #header><span>Work Order 映射</span></template>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="Work Order">{{ currentWorkOrder || '-' }}</el-descriptions-item>
        <el-descriptions-item label="同步状态">{{ workOrderSyncStatusLabel }}</el-descriptions-item>
        <el-descriptions-item label="ERP Docstatus">{{ detail?.erpnext_docstatus ?? '-' }}</el-descriptions-item>
        <el-descriptions-item label="ERP 状态">{{ detail?.erpnext_status || '-' }}</el-descriptions-item>
        <el-descriptions-item label="最新错误码">{{ detail?.latest_work_order_outbox?.error_code || '-' }}</el-descriptions-item>
        <el-descriptions-item label="最近同步时间">{{ detail?.last_synced_at || '-' }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <el-card v-if="canMaterialCheckAction" shadow="never">
      <template #header><span>物料检查</span></template>
      <el-form :model="materialCheckForm" label-width="140px">
        <el-form-item label="仓库">
          <el-input v-model="materialCheckForm.warehouse" placeholder="WIP Warehouse - LY" />
        </el-form-item>
      </el-form>
      <el-button type="primary" :loading="checkingMaterials" @click="runMaterialCheck">执行物料检查</el-button>
    </el-card>

    <el-card v-if="canCreateWorkOrderAction" shadow="never">
      <template #header><span>创建 Work Order 同步任务</span></template>
      <el-form :model="createWorkOrderForm" label-width="150px">
        <el-form-item label="成品仓（fg_warehouse）">
          <el-input v-model="createWorkOrderForm.fg_warehouse" placeholder="Finished Goods - LY" />
        </el-form-item>
        <el-form-item label="在制仓（wip_warehouse）">
          <el-input v-model="createWorkOrderForm.wip_warehouse" placeholder="Work In Progress - LY" />
        </el-form-item>
        <el-form-item label="开始日期">
          <el-date-picker
            v-model="createWorkOrderForm.start_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="选择开始日期"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="幂等键">
          <el-input v-model="createWorkOrderForm.idempotency_key" />
        </el-form-item>
      </el-form>
      <el-button type="primary" :loading="creatingWorkOrder" @click="createWorkOrderOutbox">创建同步任务</el-button>
    </el-card>

    <el-card v-if="canSyncJobCardsAction" shadow="never">
      <template #header><span>同步 Job Card</span></template>
      <el-descriptions :column="1" border>
        <el-descriptions-item label="目标 Work Order">{{ currentWorkOrder }}</el-descriptions-item>
      </el-descriptions>
      <div class="sync-action">
        <el-button type="success" :loading="syncingJobCards" @click="syncJobCards">同步 Job Card</el-button>
      </div>
    </el-card>

    <el-card v-if="canRead" shadow="never">
      <template #header><span>物料检查快照</span></template>
      <el-alert
        type="info"
        :closable="false"
        show-icon
        title="可用库存为后端快照；未接库存实时快照前仅作参考。"
      />
      <el-table :data="detail?.material_snapshots || []" border style="margin-top: 12px">
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

    <el-card v-if="canRead" shadow="never">
      <template #header><span>Job Card 映射</span></template>
      <el-table :data="detail?.job_cards || []" border>
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
  fetchProductionPlanDetail,
  syncProductionJobCards,
  type ProductionPlanDetailData,
} from '@/api/production'
import { usePermissionStore } from '@/stores/permission'

const route = useRoute()
const router = useRouter()
const permissionStore = usePermissionStore()

const detail = ref<ProductionPlanDetailData | null>(null)
const loading = ref<boolean>(false)
const checkingMaterials = ref<boolean>(false)
const creatingWorkOrder = ref<boolean>(false)
const syncingJobCards = ref<boolean>(false)

const materialCheckForm = reactive({
  warehouse: 'WIP Warehouse - LY',
})

const createWorkOrderForm = reactive({
  fg_warehouse: 'Finished Goods - LY',
  wip_warehouse: 'Work In Progress - LY',
  start_date: '',
  idempotency_key: '',
})

const canRead = computed<boolean>(() => permissionStore.state.buttonPermissions.read)
const canMaterialCheck = computed<boolean>(() => permissionStore.state.buttonPermissions.material_check)
const canWorkOrderCreate = computed<boolean>(() => permissionStore.state.buttonPermissions.work_order_create)
const canJobCardSync = computed<boolean>(() => permissionStore.state.buttonPermissions.job_card_sync)

const planId = computed<number>(() => Number(route.query.id || '0'))
const status = computed<string>(() => detail.value?.status || '')
const currentWorkOrder = computed<string>(
  () => detail.value?.work_order || detail.value?.latest_work_order_outbox?.erpnext_work_order || '',
)
const workOrderSyncStatusLabel = computed<string>(() =>
  syncStatusLabel(detail.value?.sync_status || detail.value?.latest_work_order_outbox?.status || null),
)

const canMaterialCheckAction = computed<boolean>(() => {
  const allowed = new Set(['planned', 'material_checked', 'work_order_pending', 'work_order_created'])
  return canMaterialCheck.value && allowed.has(status.value)
})

const canCreateWorkOrderAction = computed<boolean>(() => {
  const allowed = new Set(['planned', 'material_checked', 'work_order_pending', 'work_order_created'])
  return canWorkOrderCreate.value && allowed.has(status.value)
})

const canSyncJobCardsAction = computed<boolean>(() => {
  return canJobCardSync.value && !!currentWorkOrder.value
})

const buildIdempotencyKey = (prefix: string): string => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return `${prefix}-${crypto.randomUUID()}`
  }
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

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

const ensurePlanId = (): number => {
  if (!planId.value || Number.isNaN(planId.value)) {
    throw new Error('无效的生产计划 ID')
  }
  return planId.value
}

const resetWorkOrderIdempotency = (): void => {
  createWorkOrderForm.idempotency_key = buildIdempotencyKey('work-order')
}

const applyDefaultWorkOrderStartDate = (): void => {
  if (createWorkOrderForm.start_date) {
    return
  }
  createWorkOrderForm.start_date = detail.value?.planned_start_date || new Date().toISOString().slice(0, 10)
}

const loadDetail = async (): Promise<void> => {
  if (!canRead.value) {
    detail.value = null
    return
  }
  loading.value = true
  try {
    const result = await fetchProductionPlanDetail(ensurePlanId())
    detail.value = result.data
    applyDefaultWorkOrderStartDate()
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    loading.value = false
  }
}

const runMaterialCheck = async (): Promise<void> => {
  checkingMaterials.value = true
  try {
    await checkProductionMaterials(ensurePlanId(), {
      warehouse: materialCheckForm.warehouse,
    })
    ElMessage.success('物料检查完成')
    await loadDetail()
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    checkingMaterials.value = false
  }
}

const createWorkOrderOutbox = async (): Promise<void> => {
  creatingWorkOrder.value = true
  try {
    const result = await createProductionWorkOrder(ensurePlanId(), {
      fg_warehouse: createWorkOrderForm.fg_warehouse,
      wip_warehouse: createWorkOrderForm.wip_warehouse,
      start_date: createWorkOrderForm.start_date,
      idempotency_key: createWorkOrderForm.idempotency_key,
    })
    if (['pending', 'processing'].includes(result.data.sync_status)) {
      ElMessage.success('Work Order 已进入同步队列')
    } else {
      ElMessage.success('Work Order 同步任务创建成功')
    }
    resetWorkOrderIdempotency()
    await loadDetail()
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    creatingWorkOrder.value = false
  }
}

const syncJobCards = async (): Promise<void> => {
  if (!currentWorkOrder.value) {
    ElMessage.error('当前无可同步 Work Order')
    return
  }
  syncingJobCards.value = true
  try {
    await syncProductionJobCards(currentWorkOrder.value)
    ElMessage.success('Job Card 同步完成')
    await loadDetail()
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    syncingJobCards.value = false
  }
}

const goBack = (): void => {
  router.push('/production/plans')
}

watch(
  () => planId.value,
  async () => {
    createWorkOrderForm.start_date = ''
    await loadDetail()
  },
)

onMounted(async () => {
  resetWorkOrderIdempotency()
  createWorkOrderForm.start_date = ''
  try {
    await permissionStore.loadCurrentUser()
    await permissionStore.loadModuleActions('production')
  } catch (error) {
    ElMessage.error((error as Error).message)
  }
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

.sync-action {
  margin-top: 12px;
}
</style>
