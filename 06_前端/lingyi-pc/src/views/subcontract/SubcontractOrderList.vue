<template>
  <div class="subcontract-list-page" data-testid="subcontract-list-page">
    <el-card shadow="never" data-testid="subcontract-main-card">
      <template #header>
        <div class="header-row">
          <span>外发单列表</span>
          <div class="header-actions" data-testid="subcontract-guarded-actions">
            <el-button
              size="small"
              type="primary"
              data-action-type="write"
              data-write-guard="guarded:readonly"
              data-testid="subcontract-create-open-button"
              @click="openCreateDialog"
            >
              新建外发单
            </el-button>
            <el-button size="small" :disabled="!canRead" data-testid="subcontract-refresh-button" @click="loadOrders">
              刷新
            </el-button>
          </div>
        </div>
      </template>

      <el-alert
        type="warning"
        show-icon
        :closable="false"
        class="readonly-guard"
        data-testid="subcontract-write-guard"
        data-write-guard="guarded:readonly"
      >
        <template #title>
          <span>只读履约视图：新建外发单、导出、打印与同步写入口均保持 guarded，不发起写请求。</span>
        </template>
      </el-alert>

      <el-alert
        v-if="parityHint"
        type="info"
        show-icon
        :closable="false"
        class="parity-hint"
        data-testid="subcontract-parity-hint"
      >
        <template #title>
          <span data-testid="subcontract-parity-hint-text">当前入口：{{ parityHint.label }}（{{ parityHint.key }}）</span>
        </template>
      </el-alert>

      <el-form :inline="true" :model="query" data-testid="subcontract-filter-form">
        <el-form-item label="加工厂">
          <div data-testid="subcontract-filter-supplier">
            <el-input v-model="query.supplier" clearable placeholder="Supplier" />
          </div>
        </el-form-item>
        <el-form-item label="状态">
          <div data-testid="subcontract-filter-status">
            <el-select
              v-model="query.status"
              clearable
              placeholder="全部状态"
              aria-label="外发单状态筛选"
              style="width: 150px"
            >
              <el-option label="草稿" value="draft" />
              <el-option label="已发料" value="issued" />
              <el-option label="加工中" value="processing" />
              <el-option label="待回料" value="waiting_receive" />
              <el-option label="待验货" value="waiting_inspection" />
              <el-option label="已完成" value="completed" />
              <el-option label="已取消" value="cancelled" />
            </el-select>
          </div>
        </el-form-item>
        <el-form-item>
          <div class="query-action" data-testid="subcontract-query-btn">
            <el-button type="primary" :disabled="!canRead" @click="applyQuery">查询</el-button>
          </div>
          <div class="query-action" data-testid="subcontract-reset-btn">
            <el-button :disabled="!canRead" @click="resetQuery">重置</el-button>
          </div>
        </el-form-item>
      </el-form>

      <el-empty v-if="!canRead" description="无外发查看权限" data-testid="subcontract-permission-empty-state" />
      <template v-else>
        <el-alert
          v-if="errorMessage"
          type="error"
          :title="errorMessage"
          show-icon
          :closable="false"
          class="error-state"
          data-testid="subcontract-error-state"
        />
        <div data-testid="subcontract-table">
          <el-table :data="rows" v-loading="loading" border empty-text="暂无外发单数据">
          <el-table-column prop="subcontract_no" label="外发单号" min-width="220" />
          <el-table-column prop="company" label="公司" min-width="150" />
          <el-table-column prop="supplier" label="加工厂" min-width="160" />
          <el-table-column prop="item_code" label="款式" min-width="140" />
          <el-table-column prop="process_name" label="工序" min-width="120" />
          <el-table-column prop="planned_qty" label="计划数量" width="110" />
          <el-table-column prop="issued_qty" label="已发料" width="110" />
          <el-table-column prop="received_qty" label="已回料" width="110" />
          <el-table-column prop="inspected_qty" label="已验货" width="110" />
          <el-table-column prop="net_amount" label="净应付金额" width="120" />
          <el-table-column label="状态" min-width="180">
            <template #default="scope">
              <span data-testid="subcontract-status-tag">
                <el-tag>{{ statusLabel(scope.row.status) }}</el-tag>
              </span>
              <el-tag v-if="scope.row.resource_scope_status === 'blocked_scope'" type="danger" class="scope-tag">
                权限范围异常
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="库存同步状态" min-width="160">
            <template #default="scope">{{ syncStatusLabel(scope.row) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="120" fixed="right">
            <template #default="scope">
              <span data-testid="subcontract-detail-entry">
                <el-button link type="primary" @click="goDetail(scope.row.id)">详情</el-button>
              </span>
            </template>
          </el-table-column>
          </el-table>
        </div>

        <el-empty
          v-if="!loading && !errorMessage && rows.length === 0"
          description="暂无外发单数据"
          class="empty-state"
          data-testid="subcontract-empty-state"
        />

        <div class="pager" data-testid="subcontract-pagination">
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

    <el-dialog
      v-model="createDialogVisible"
      title="新建外发单"
      width="640px"
      destroy-on-close
      append-to-body
      data-testid="subcontract-create-dialog"
    >
      <el-form :model="createForm" label-width="120px">
        <el-form-item label="加工厂">
          <el-input v-model="createForm.supplier" data-testid="subcontract-create-supplier-input" />
        </el-form-item>
        <el-form-item label="款号">
          <el-input v-model="createForm.item_code" data-testid="subcontract-create-item-code-input" />
        </el-form-item>
        <el-form-item label="BOM ID">
          <el-input-number v-model="createForm.bom_id" :min="1" data-testid="subcontract-create-bom-id-input" />
        </el-form-item>
        <el-form-item label="工序">
          <el-input v-model="createForm.process_name" data-testid="subcontract-create-process-input" />
        </el-form-item>
        <el-form-item label="计划数量">
          <el-input-number
            v-model="createForm.planned_qty"
            :min="1"
            :step="1"
            data-testid="subcontract-create-planned-qty-input"
          />
        </el-form-item>
        <el-form-item label="销售单">
          <el-input v-model="createForm.sales_order" data-testid="subcontract-create-sales-order-input" />
        </el-form-item>
        <el-form-item label="工单">
          <el-input v-model="createForm.work_order" data-testid="subcontract-create-work-order-input" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button data-testid="subcontract-create-cancel-button" @click="createDialogVisible = false">取消</el-button>
        <el-button
          type="primary"
          :loading="createSubmitting"
          data-testid="subcontract-create-submit-button"
          @click="submitCreate"
        >
          保存
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  buildSubcontractRequestId,
  buildSubcontractScenarioTag,
  createSubcontractOrder,
  fetchSubcontractOrders,
  type SubcontractOrderListItem,
} from '@/api/subcontract'
import { usePermissionStore } from '@/stores/permission'

const route = useRoute()
const router = useRouter()
const permissionStore = usePermissionStore()
const loading = ref<boolean>(false)
const rows = ref<SubcontractOrderListItem[]>([])
const total = ref<number>(0)
const errorMessage = ref<string>('')
const createDialogVisible = ref<boolean>(false)
const createSubmitting = ref<boolean>(false)

const readonlyFallback = ref<boolean>(false)
const canRead = computed<boolean>(() => readonlyFallback.value || permissionStore.state.buttonPermissions.read)
const parityHint = computed<{ key: string; label: string } | null>(() => {
  const raw = typeof route.query.parity === 'string' ? route.query.parity.trim() : ''
  if (raw === 'material-purchase') {
    return { key: raw, label: '物料采购进度只读视图' }
  }
  if (raw === 'subcontract-order') {
    return { key: raw, label: '外发加工单只读视图' }
  }
  return null
})

const query = reactive({
  supplier: '',
  status: '',
  page: 1,
  page_size: 20,
})

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

const stockSyncLabel = (status?: string | null): string => {
  if (!status) return ''
  const labels: Record<string, string> = {
    pending: '待同步',
    processing: '同步中',
    succeeded: '已同步',
    failed: '同步失败',
    dead: '死信',
    blocked_scope: '范围阻断',
  }
  return labels[status] || status
}

const syncStatusLabel = (row: SubcontractOrderListItem): string => {
  const issue = stockSyncLabel(row.latest_issue_sync_status)
  const receipt = stockSyncLabel(row.latest_receipt_sync_status)
  if (issue && receipt) {
    return `发料:${issue} / 回料:${receipt}`
  }
  if (receipt) {
    return `回料:${receipt}`
  }
  if (issue) {
    return `发料:${issue}`
  }
  return '未入列'
}

const guardedAction = (actionLabel: string): void => {
  ElMessage.warning(`${actionLabel} 仅可在授权流程中执行，当前为只读模式`)
}

const createForm = reactive({
  supplier: '示例加工厂',
  item_code: 'DEMO-TEE',
  bom_id: 1,
  process_name: '缝制',
  planned_qty: 10,
  sales_order: '',
  sales_order_item: '',
  production_plan_id: undefined as number | undefined,
  work_order: '',
  job_card: '',
})

const openCreateDialog = (): void => {
  guardedAction('新建外发单')
}

const submitCreate = async (): Promise<void> => {
  guardedAction('保存新建外发单')
  return
  if (createSubmitting.value) return
  const supplier = createForm.supplier.trim()
  const itemCode = createForm.item_code.trim()
  const processName = createForm.process_name.trim()
  const workOrderRef = (createForm.work_order || String(createForm.production_plan_id || '')).trim() || 'NO-WORK-ORDER'
  if (!supplier || !itemCode || !processName || !createForm.bom_id || !createForm.planned_qty) {
    ElMessage.warning('请先填写完整的外发单信息')
    return
  }

  createSubmitting.value = true
  try {
    const scenarioTag = buildSubcontractScenarioTag()
    const idempotencyKey = `${scenarioTag}-CREATE-${Date.now()}`
    const sourceRef = `${scenarioTag}-SRC-CREATE`
    const subcontractRef = `${scenarioTag}-SC-NEW`
    const statusAction = 'create'
    const requestId = buildSubcontractRequestId({
      scenarioTag,
      operation: 'create',
      idempotencyKey,
      sourceRef,
      subcontractRef,
      supplierRef: supplier,
      workOrderRef,
      itemCode,
      statusAction,
    })

    const created = await createSubcontractOrder({
      request_id: requestId,
      idempotency_key: idempotencyKey,
      scenario_tag: scenarioTag,
      source_ref: sourceRef,
      subcontract_ref: subcontractRef,
      supplier_ref: supplier,
      work_order_ref: workOrderRef,
      operation: 'create',
      quantity: createForm.planned_qty,
      status_action: statusAction,
      supplier,
      item_code: itemCode,
      bom_id: createForm.bom_id,
      planned_qty: createForm.planned_qty,
      process_name: processName,
      sales_order: createForm.sales_order.trim() || null,
      sales_order_item: createForm.sales_order_item.trim() || null,
      production_plan_id: createForm.production_plan_id ?? null,
      work_order: createForm.work_order.trim() || null,
      job_card: createForm.job_card.trim() || null,
      company: '示例公司',
    })

    query.page = 1
    await loadOrders()
    const createdRowId = rows.value.find((row) => row.subcontract_no === created.data.name)?.id
    const nextOrderId = Number(createdRowId ?? 0)
    if (nextOrderId > 0) {
      goDetail(nextOrderId)
    }
    createDialogVisible.value = false
    ElMessage.success(`外发单已创建：${created.data.name}`)
  } catch (error) {
    ElMessage.error((error as Error).message || '新建外发单失败')
  } finally {
    createSubmitting.value = false
  }
}

const loadOrders = async (): Promise<void> => {
  if (!canRead.value) {
    rows.value = []
    total.value = 0
    errorMessage.value = ''
    return
  }
  loading.value = true
  errorMessage.value = ''
  try {
    const payload = await fetchSubcontractOrders(query)
    rows.value = payload.data.items
    total.value = payload.data.total
  } catch (error) {
    const message = (error as Error).message || '外发单列表加载失败'
    errorMessage.value = message
    ElMessage.error(message)
  } finally {
    loading.value = false
  }
}

const applyQuery = (): void => {
  query.page = 1
  loadOrders()
}

const resetQuery = (): void => {
  query.supplier = ''
  query.status = ''
  query.page = 1
  query.page_size = 20
  loadOrders()
}

const goDetail = (id: number): void => {
  router.push({ path: '/subcontract/detail', query: { id: String(id) } })
}

const onPageChange = (page: number): void => {
  query.page = page
  loadOrders()
}

const onSizeChange = (size: number): void => {
  query.page_size = size
  query.page = 1
  loadOrders()
}

onMounted(async () => {
  try {
    await permissionStore.loadCurrentUser()
    await permissionStore.loadModuleActions('subcontract')
    readonlyFallback.value = !permissionStore.state.buttonPermissions.read
  } catch (error) {
    readonlyFallback.value = true
    ElMessage.error((error as Error).message)
  }
  await loadOrders()
})
</script>

<style scoped>
.subcontract-list-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.header-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.query-action {
  display: inline-flex;
  margin-right: 8px;
}

.scope-tag {
  margin-left: 8px;
}

.error-state {
  margin-bottom: 12px;
}

.parity-hint {
  margin-bottom: 12px;
}

.readonly-guard {
  margin-bottom: 12px;
}

.empty-state {
  margin-top: 12px;
}

.pager {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}
</style>
