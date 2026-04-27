<template>
  <div class="production-plan-list-page">
    <el-card shadow="never">
      <template #header>
        <div class="header-row">
          <span>生产计划列表</span>
          <el-button
            type="primary"
            :disabled="!canPlanCreate"
            data-action-type="write"
            data-write-guard="permission:plan_create+handler"
            :data-guard-state="canPlanCreate ? 'enabled' : 'disabled'"
            @click="openCreateDialog"
          >
            新建生产计划
          </el-button>
        </div>
      </template>

      <el-form :inline="true" :model="query">
        <el-form-item label="销售单">
          <el-input v-model="query.sales_order" clearable placeholder="SO-0001" />
        </el-form-item>
        <el-form-item label="款式">
          <el-input v-model="query.item_code" clearable placeholder="ITEM-001" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.status" clearable placeholder="全部状态" style="width: 180px">
            <el-option label="草稿" value="draft" />
            <el-option label="已计划" value="planned" />
            <el-option label="已物料检查" value="material_checked" />
            <el-option label="工单待同步" value="work_order_pending" />
            <el-option label="已创建工单" value="work_order_created" />
            <el-option label="工序卡已同步" value="job_cards_synced" />
            <el-option label="已取消" value="cancelled" />
            <el-option label="失败" value="failed" />
          </el-select>
        </el-form-item>
        <el-form-item label="操作">
          <el-button type="primary" :disabled="!canRead" @click="loadPlans">查询</el-button>
        </el-form-item>
      </el-form>

      <el-empty v-if="!canRead" description="无生产计划查看权限" />
      <template v-else>
        <el-table :data="rows" v-loading="loading" border empty-text="暂无生产计划数据">
          <el-table-column prop="plan_no" label="计划单号" min-width="180" />
          <el-table-column prop="company" label="公司" min-width="140" />
          <el-table-column prop="sales_order" label="销售单" min-width="160" />
          <el-table-column prop="sales_order_item" label="销售单行" min-width="160" />
          <el-table-column prop="item_code" label="款式" min-width="140" />
          <el-table-column prop="bom_id" label="BOM ID" width="100" />
          <el-table-column prop="planned_qty" label="计划数量" width="120" />
          <el-table-column label="计划开工日" min-width="120">
            <template #default="scope">{{ scope.row.planned_start_date || '-' }}</template>
          </el-table-column>
          <el-table-column label="状态" min-width="140">
            <template #default="scope">
              <el-tag>{{ statusLabel(scope.row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="Work Order" min-width="180">
            <template #default="scope">{{ scope.row.latest_work_order_outbox?.erpnext_work_order || '-' }}</template>
          </el-table-column>
          <el-table-column label="库存同步状态" min-width="140">
            <template #default="scope">{{ syncStatusLabel(scope.row.latest_work_order_outbox?.status) }}</template>
          </el-table-column>
          <el-table-column prop="created_at" label="创建时间" min-width="180" />
          <el-table-column label="操作" width="100" fixed="right">
            <template #default="scope">
              <el-button link type="primary" @click="goDetail(scope.row.id)">详情</el-button>
            </template>
          </el-table-column>
        </el-table>

        <div class="pager">
          <el-pagination
            background
            layout="prev, pager, next, total, sizes"
            :current-page="query.page"
            :page-size="query.page_size"
            :total="total"
            :page-sizes="[10, 20, 50, 100]"
            @current-change="onPageChange"
            @size-change="onSizeChange"
          />
        </div>
      </template>
    </el-card>

    <el-dialog v-model="createVisible" title="新建生产计划" width="640px">
      <el-form :model="createForm" label-width="130px">
        <el-form-item label="销售单">
          <el-input v-model="createForm.sales_order" placeholder="销售单号" />
        </el-form-item>
        <el-form-item label="销售单行（可选）">
          <el-input v-model="createForm.sales_order_item" placeholder="销售单行号（可选）" />
        </el-form-item>
        <el-form-item label="款式编码">
          <el-input v-model="createForm.item_code" placeholder="款式编码" />
        </el-form-item>
        <el-form-item label="BOM ID（可选）">
          <el-input-number v-model="createForm.bom_id" aria-label="BOM ID（可选）" :min="1" />
        </el-form-item>
        <el-form-item label="计划数量">
          <el-input-number v-model="createForm.planned_qty" aria-label="计划数量" :min="0.000001" :step="1" />
        </el-form-item>
        <el-form-item label="计划开工日（可选）">
          <el-date-picker
            v-model="createForm.planned_start_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="选择日期"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="幂等键">
          <el-input v-model="createForm.idempotency_key" placeholder="幂等键" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button
          type="primary"
          :loading="creating"
          :disabled="!canCreateAction"
          data-action-type="write"
          data-write-guard="permission:plan_create+form_valid+handler"
          :data-guard-state="canCreateAction ? 'enabled' : 'disabled'"
          @click="createPlan"
        >
          创建
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  createProductionPlan,
  fetchProductionPlans,
  type ProductionPlanCreatePayload,
  type ProductionPlanListItem,
} from '@/api/production'
import { usePermissionStore } from '@/stores/permission'

const router = useRouter()
const permissionStore = usePermissionStore()

const loading = ref<boolean>(false)
const creating = ref<boolean>(false)
const createVisible = ref<boolean>(false)
const rows = ref<ProductionPlanListItem[]>([])
const total = ref<number>(0)

const canRead = computed<boolean>(() => permissionStore.state.buttonPermissions.read)
const canPlanCreate = computed<boolean>(() => permissionStore.state.buttonPermissions.plan_create)

const query = reactive({
  sales_order: '',
  item_code: '',
  status: '',
  page: 1,
  page_size: 20,
})

const createForm = reactive({
  sales_order: '',
  sales_order_item: '',
  item_code: '',
  bom_id: undefined as number | undefined,
  planned_qty: 1,
  planned_start_date: '',
  idempotency_key: '',
})

const normalizedCreateForm = computed(() => ({
  sales_order: createForm.sales_order.trim(),
  sales_order_item: createForm.sales_order_item.trim(),
  item_code: createForm.item_code.trim(),
  planned_qty: Number(createForm.planned_qty || 0),
  planned_start_date: createForm.planned_start_date || undefined,
  idempotency_key: createForm.idempotency_key.trim(),
}))

const createFormValidationError = computed<string | null>(() => {
  if (!normalizedCreateForm.value.sales_order) {
    return '销售单不能为空'
  }
  if (!normalizedCreateForm.value.item_code) {
    return '款式编码不能为空'
  }
  if (!normalizedCreateForm.value.idempotency_key) {
    return '幂等键不能为空'
  }
  if (!(normalizedCreateForm.value.planned_qty > 0)) {
    return '计划数量必须大于 0'
  }
  return null
})

const canCreateAction = computed<boolean>(() => canPlanCreate.value && !createFormValidationError.value)

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

const loadPlans = async (): Promise<void> => {
  if (!canRead.value) {
    rows.value = []
    total.value = 0
    return
  }
  loading.value = true
  try {
    const result = await fetchProductionPlans({
      sales_order: query.sales_order || undefined,
      item_code: query.item_code || undefined,
      status: query.status || undefined,
      page: query.page,
      page_size: query.page_size,
    })
    rows.value = result.data.items
    total.value = result.data.total
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    loading.value = false
  }
}

const openCreateDialog = (): void => {
  if (!canPlanCreate.value) {
    ElMessage.error('无新建生产计划权限')
    return
  }
  createForm.sales_order = ''
  createForm.sales_order_item = ''
  createForm.item_code = ''
  createForm.bom_id = undefined
  createForm.planned_qty = 1
  createForm.planned_start_date = ''
  createForm.idempotency_key = buildIdempotencyKey('plan')
  createVisible.value = true
}

const createPlan = async (): Promise<void> => {
  if (!canPlanCreate.value) {
    ElMessage.error('无新建生产计划权限')
    return
  }

  const validationError = createFormValidationError.value
  if (validationError) {
    ElMessage.error(validationError)
    return
  }

  const payload: ProductionPlanCreatePayload = {
    sales_order: normalizedCreateForm.value.sales_order,
    sales_order_item: normalizedCreateForm.value.sales_order_item || undefined,
    item_code: normalizedCreateForm.value.item_code,
    bom_id: createForm.bom_id,
    planned_qty: normalizedCreateForm.value.planned_qty,
    planned_start_date: normalizedCreateForm.value.planned_start_date,
    idempotency_key: normalizedCreateForm.value.idempotency_key,
  }

  creating.value = true
  try {
    await createProductionPlan(payload)
    ElMessage.success('生产计划创建成功')
    createForm.idempotency_key = buildIdempotencyKey('plan')
    createVisible.value = false
    await loadPlans()
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    creating.value = false
  }
}

const goDetail = (planId: number): void => {
  router.push({ path: '/production/plans/detail', query: { id: String(planId) } })
}

const onPageChange = (page: number): void => {
  query.page = page
  loadPlans()
}

const onSizeChange = (size: number): void => {
  query.page_size = size
  query.page = 1
  loadPlans()
}

onMounted(async () => {
  try {
    await permissionStore.loadCurrentUser()
    await permissionStore.loadModuleActions('production')
  } catch (error) {
    ElMessage.error((error as Error).message)
  }
  await loadPlans()
})
</script>

<style scoped>
.production-plan-list-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.pager {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}
</style>
