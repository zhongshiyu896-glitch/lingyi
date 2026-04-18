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

    <el-card v-if="canRead" shadow="never">
      <template #header><span>写入口状态</span></template>
      <el-alert
        type="warning"
        :closable="false"
        show-icon
        title="当前阶段已冻结 create-work-order / sync-job-cards；仅保留本地生产计划草稿与只读工单工序投影。"
      />
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
  fetchProductionPlanDetail,
  type ProductionPlanDetailData,
} from '@/api/production'
import { usePermissionStore } from '@/stores/permission'

const route = useRoute()
const router = useRouter()
const permissionStore = usePermissionStore()

const detail = ref<ProductionPlanDetailData | null>(null)
const loading = ref<boolean>(false)
const checkingMaterials = ref<boolean>(false)

const materialCheckForm = reactive({
  warehouse: 'WIP Warehouse - LY',
})

const canRead = computed<boolean>(() => permissionStore.state.buttonPermissions.read)
const canMaterialCheck = computed<boolean>(() => permissionStore.state.buttonPermissions.material_check)

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

const loadDetail = async (): Promise<void> => {
  if (!canRead.value) {
    detail.value = null
    return
  }
  loading.value = true
  try {
    const result = await fetchProductionPlanDetail(ensurePlanId())
    detail.value = result.data
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
</style>
