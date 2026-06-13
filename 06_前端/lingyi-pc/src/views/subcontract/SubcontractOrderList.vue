<template>
  <div class="subcontract-list-page" data-testid="subcontract-order-list-page">
    <el-card shadow="never">
      <template #header>
        <div class="header-row">
          <div>
            <h2>委外订单列表</h2>
            <p class="sub-title">LOCAL_DEV_WRITE_CLOSURE，仅 development + sqlite 允许 create / issue / receive / inspect / settlement preview。</p>
          </div>
          <div class="header-actions">
            <el-button type="primary" plain :loading="loading" data-testid="subcontract-refresh-button" @click="loadRows">
              刷新列表
            </el-button>
            <el-button type="success" data-testid="subcontract-create-button" data-action-type="write" @click="openCreateDialog()">
              创建委外单
            </el-button>
          </div>
        </div>
      </template>
      <el-alert
        type="info"
        :closable="false"
        title="前端仅接入本地外发写闭环：create / issue-material / receive / inspect / settlement-preview。"
      />
      <el-alert
        class="top-alert"
        type="warning"
        :closable="false"
        title="禁止 settlement-locks、release、stock-sync/retry、internal run-once、ERPNext、worker 与 production write。"
      />
    </el-card>

    <el-card shadow="never">
      <el-form :inline="true" :model="query" @submit.prevent>
        <el-form-item label="关键字">
          <el-input v-model="query.keyword" clearable placeholder="单据号 / 供应商 / 物料 / 销售订单" style="width: 240px" />
        </el-form-item>
        <el-form-item label="供应商">
          <el-input v-model="query.supplier" clearable placeholder="supplier" style="width: 160px" />
        </el-form-item>
        <el-form-item label="公司">
          <el-input v-model="query.company" clearable placeholder="company" style="width: 140px" />
        </el-form-item>
        <el-form-item label="工序">
          <el-input v-model="query.process_name" clearable placeholder="process_name" style="width: 140px" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.status" clearable placeholder="全部" style="width: 150px">
            <el-option label="draft" value="draft" />
            <el-option label="issued" value="issued" />
            <el-option label="waiting_receive" value="waiting_receive" />
            <el-option label="waiting_inspection" value="waiting_inspection" />
            <el-option label="completed" value="completed" />
          </el-select>
        </el-form-item>
        <el-form-item label="开始日期">
          <el-date-picker v-model="query.from_date" type="date" value-format="YYYY-MM-DD" clearable />
        </el-form-item>
        <el-form-item label="结束日期">
          <el-date-picker v-model="query.to_date" type="date" value-format="YYYY-MM-DD" clearable />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" data-testid="subcontract-query-button" @click="applyQuery">查询</el-button>
          <el-button :loading="loading" data-testid="subcontract-reset-button" @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>

      <el-alert v-if="feedback" class="top-alert" :title="feedback" type="info" :closable="false" data-testid="subcontract-feedback" />
      <el-alert v-if="loadError" class="top-alert" :title="loadError" type="error" :closable="false" data-testid="subcontract-load-error" />
    </el-card>

    <el-card shadow="never">
      <template #header>
        <span>列表摘要</span>
      </template>
      <el-descriptions border :column="3">
        <el-descriptions-item label="当前页记录">{{ filteredRows.length }}</el-descriptions-item>
        <el-descriptions-item label="后端 total">{{ total }}</el-descriptions-item>
        <el-descriptions-item label="供应商数">{{ summaryView.supplierCount }}</el-descriptions-item>
        <el-descriptions-item label="计划数量">{{ formatNumber(summaryView.plannedQty) }}</el-descriptions-item>
        <el-descriptions-item label="已发料">{{ formatNumber(summaryView.issuedQty) }}</el-descriptions-item>
        <el-descriptions-item label="已回料">{{ formatNumber(summaryView.receivedQty) }}</el-descriptions-item>
        <el-descriptions-item label="已验货">{{ formatNumber(summaryView.inspectedQty) }}</el-descriptions-item>
        <el-descriptions-item label="已验收">{{ formatNumber(summaryView.acceptedQty) }}</el-descriptions-item>
        <el-descriptions-item label="待结算预览">{{ summaryView.previewReadyCount }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <el-card shadow="never">
      <el-table
        :data="filteredRows"
        border
        v-loading="loading"
        empty-text="暂无委外订单，可以直接创建一张本地委外单开始闭环验证"
        data-testid="subcontract-list-table"
      >
        <el-table-column prop="subcontract_no" label="单据号" min-width="180" />
        <el-table-column label="供应商 / 公司" min-width="180">
          <template #default="{ row }">
            <div class="stacked-cell">
              <span>{{ row.supplier }}</span>
              <span>{{ row.company || '-' }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="物料 / 工序" min-width="180">
          <template #default="{ row }">
            <div class="stacked-cell">
              <span>{{ row.item_code }}</span>
              <span>{{ row.process_name }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="计划 / 发料 / 回料 / 验货 / 验收" min-width="260">
          <template #default="{ row }">
            <div class="stacked-cell">
              <span>{{ formatNumber(row.planned_qty) }} / {{ formatNumber(row.issued_qty) }} / {{ formatNumber(row.received_qty) }}</span>
              <span>{{ formatNumber(row.inspected_qty) }} / {{ formatNumber(row.accepted_qty) }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="140">
          <template #default="{ row }">
            <el-tag :type="statusTag(row.status)">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="销售 / 工单" min-width="180">
          <template #default="{ row }">
            <div class="stacked-cell">
              <span>{{ row.sales_order || '-' }}</span>
              <span>{{ row.work_order || '-' }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" min-width="180">
          <template #default="{ row }">
            {{ row.created_at || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" fixed="right" width="200">
          <template #default="{ row }">
            <el-button link type="primary" data-testid="subcontract-detail-button" @click="openDetail(row.id)">详情</el-button>
            <el-button link type="success" data-testid="subcontract-copy-create-button" @click="openCreateDialog(row)">复制创建</el-button>
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
    </el-card>

    <el-dialog v-model="createDialogVisible" title="创建本地委外单" width="640px" destroy-on-close>
      <el-form label-width="120px">
        <el-form-item label="供应商">
          <el-input v-model="createForm.supplier" data-testid="subcontract-create-supplier" />
        </el-form-item>
        <el-form-item label="公司">
          <el-input v-model="createForm.company" data-testid="subcontract-create-company" />
        </el-form-item>
        <el-form-item label="物料编码">
          <el-input v-model="createForm.item_code" data-testid="subcontract-create-item-code" />
        </el-form-item>
        <el-form-item label="BOM ID">
          <el-input v-model="createForm.bom_id" data-testid="subcontract-create-bom-id" />
        </el-form-item>
        <el-form-item label="工序">
          <el-input v-model="createForm.process_name" data-testid="subcontract-create-process-name" />
        </el-form-item>
        <el-form-item label="计划数量">
          <el-input v-model="createForm.planned_qty" data-testid="subcontract-create-planned-qty" />
        </el-form-item>
        <el-form-item label="销售订单">
          <el-input v-model="createForm.sales_order" data-testid="subcontract-create-sales-order" />
        </el-form-item>
        <el-form-item label="销售订单行">
          <el-input v-model="createForm.sales_order_item" data-testid="subcontract-create-sales-order-item" />
        </el-form-item>
        <el-form-item label="生产计划 ID">
          <el-input v-model="createForm.production_plan_id" data-testid="subcontract-create-production-plan-id" />
        </el-form-item>
        <el-form-item label="工单">
          <el-input v-model="createForm.work_order" data-testid="subcontract-create-work-order" />
        </el-form-item>
        <el-form-item label="工票">
          <el-input v-model="createForm.job_card" data-testid="subcontract-create-job-card" />
        </el-form-item>
        <el-form-item label="scenario_tag">
          <el-input v-model="createForm.scenario_tag" />
        </el-form-item>
        <el-form-item label="request_id">
          <el-input :model-value="createRequestId" readonly />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button
          type="primary"
          :loading="createSubmitting"
          data-testid="subcontract-create-submit"
          data-action-type="write"
          @click="submitCreate"
        >
          创建并进入详情
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { NumericLike, SubcontractCreateRequestPayload, SubcontractOrderListItem } from '@/api/subcontract'
import {
  buildSubcontractRequestId,
  buildSubcontractScenarioTag,
  createSubcontractOrder,
  fetchSubcontractOrders,
} from '@/api/subcontract'

interface ListQueryState {
  keyword: string
  supplier: string
  company: string
  process_name: string
  status: string
  from_date: string
  to_date: string
  page: number
  page_size: number
}

interface CreateFormState {
  supplier: string
  company: string
  item_code: string
  bom_id: string
  planned_qty: string
  process_name: string
  sales_order: string
  sales_order_item: string
  production_plan_id: string
  work_order: string
  job_card: string
  scenario_tag: string
  idempotency_key: string
}

const router = useRouter()

const loading = ref(false)
const createSubmitting = ref(false)
const loadError = ref('')
const feedback = ref('')
const total = ref(0)
const rows = ref<SubcontractOrderListItem[]>([])
const createDialogVisible = ref(false)

const buildDefaultQuery = (): ListQueryState => ({
  keyword: '',
  supplier: '',
  company: '',
  process_name: '',
  status: '',
  from_date: '',
  to_date: '',
  page: 1,
  page_size: 20,
})

const query = reactive<ListQueryState>(buildDefaultQuery())

const buildDefaultCreateForm = (): CreateFormState => ({
  supplier: 'SUP-A',
  company: 'COMP-A',
  item_code: 'DEMO-TEE',
  bom_id: '1',
  planned_qty: '10',
  process_name: '缝制',
  sales_order: '',
  sales_order_item: '',
  production_plan_id: '',
  work_order: '',
  job_card: '',
  scenario_tag: buildSubcontractScenarioTag(),
  idempotency_key: '',
})

const createForm = reactive<CreateFormState>(buildDefaultCreateForm())

const buildNonce = (prefix: string): string => `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`

const parseNumber = (value: NumericLike | undefined | null): number => {
  const parsed = Number(value || 0)
  return Number.isFinite(parsed) ? parsed : 0
}

const formatNumber = (value: NumericLike | undefined | null, digits = 0): string => {
  return parseNumber(value).toLocaleString('zh-CN', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })
}

const statusTag = (status: string): 'info' | 'success' | 'warning' | 'danger' => {
  if (status === 'completed') return 'success'
  if (status === 'waiting_inspection' || status === 'waiting_receive') return 'warning'
  if (status === 'draft') return 'info'
  return 'danger'
}

const normalizeWorkOrderRef = (workOrder: string, productionPlanId: string): string => {
  const normalizedWorkOrder = workOrder.trim()
  if (normalizedWorkOrder) return normalizedWorkOrder
  const normalizedPlan = productionPlanId.trim()
  if (normalizedPlan) return normalizedPlan
  return 'NO-WORK-ORDER'
}

const createRequestId = computed(() => {
  const scenarioTag = createForm.scenario_tag.trim() || buildSubcontractScenarioTag()
  const plannedQty = String(createForm.planned_qty || '1').trim() || '1'
  return buildSubcontractRequestId({
    scenarioTag,
    operation: 'create',
    idempotencyKey: createForm.idempotency_key.trim() || 'pending-idempotency-key',
    sourceRef: `${scenarioTag}:create:${createForm.item_code.trim()}:${plannedQty}`,
    subcontractRef: `NEW-${createForm.item_code.trim() || 'SUBCONTRACT'}`,
    supplierRef: createForm.supplier.trim() || 'SUP-A',
    workOrderRef: normalizeWorkOrderRef(createForm.work_order, createForm.production_plan_id),
    itemCode: createForm.item_code.trim() || 'DEMO-TEE',
    statusAction: 'create',
  })
})

const filteredRows = computed(() => {
  const keyword = query.keyword.trim().toLowerCase()
  const company = query.company.trim().toLowerCase()
  const processName = query.process_name.trim().toLowerCase()

  return rows.value.filter((row) => {
    const keywordHit =
      !keyword
      || row.subcontract_no.toLowerCase().includes(keyword)
      || row.supplier.toLowerCase().includes(keyword)
      || row.item_code.toLowerCase().includes(keyword)
      || String(row.sales_order || '').toLowerCase().includes(keyword)
    const companyHit = !company || String(row.company || '').toLowerCase().includes(company)
    const processHit = !processName || row.process_name.toLowerCase().includes(processName)
    return keywordHit && companyHit && processHit
  })
})

const summary = computed(() =>
  filteredRows.value.reduce(
    (acc, row) => {
      acc.plannedQty += parseNumber(row.planned_qty)
      acc.issuedQty += parseNumber(row.issued_qty)
      acc.receivedQty += parseNumber(row.received_qty)
      acc.inspectedQty += parseNumber(row.inspected_qty)
      acc.acceptedQty += parseNumber(row.accepted_qty)
      acc.previewReadyCount += row.status === 'completed' || parseNumber(row.inspected_qty) > 0 ? 1 : 0
      acc.suppliers.add(row.supplier)
      return acc
    },
    {
      plannedQty: 0,
      issuedQty: 0,
      receivedQty: 0,
      inspectedQty: 0,
      acceptedQty: 0,
      previewReadyCount: 0,
      suppliers: new Set<string>(),
    },
  ),
)

const summaryView = computed(() => ({
  plannedQty: summary.value.plannedQty,
  issuedQty: summary.value.issuedQty,
  receivedQty: summary.value.receivedQty,
  inspectedQty: summary.value.inspectedQty,
  acceptedQty: summary.value.acceptedQty,
  previewReadyCount: summary.value.previewReadyCount,
  supplierCount: summary.value.suppliers.size,
}))

const loadRows = async (): Promise<void> => {
  loading.value = true
  loadError.value = ''
  feedback.value = ''
  try {
    const response = await fetchSubcontractOrders({
      supplier: query.supplier || undefined,
      status: query.status || undefined,
      from_date: query.from_date || undefined,
      to_date: query.to_date || undefined,
      page: query.page,
      page_size: query.page_size,
    })
    rows.value = response.data.items || []
    total.value = response.data.total || 0
  } catch (error) {
    rows.value = []
    total.value = 0
    loadError.value = (error as Error).message || '委外订单列表加载失败'
  } finally {
    loading.value = false
  }
}

const applyQuery = (): void => {
  query.page = 1
  void loadRows()
}

const resetQuery = (): void => {
  Object.assign(query, buildDefaultQuery())
  void loadRows()
}

const onPageChange = (page: number): void => {
  query.page = page
  void loadRows()
}

const onSizeChange = (pageSize: number): void => {
  query.page = 1
  query.page_size = pageSize
  void loadRows()
}

const openDetail = (orderId: number): void => {
  router.push({ path: '/subcontract/detail', query: { id: String(orderId) } })
}

const openCreateDialog = (seed?: SubcontractOrderListItem): void => {
  const nextDefaults = buildDefaultCreateForm()
  Object.assign(createForm, nextDefaults)
  createForm.idempotency_key = buildNonce('subcontract-create')
  if (seed) {
    createForm.supplier = seed.supplier
    createForm.company = String(seed.company || 'COMP-A')
    createForm.item_code = seed.item_code
    createForm.bom_id = String(seed.bom_id)
    createForm.planned_qty = String(seed.planned_qty || '10')
    createForm.process_name = seed.process_name
    createForm.sales_order = String(seed.sales_order || '')
    createForm.sales_order_item = String(seed.sales_order_item || '')
    createForm.production_plan_id = seed.production_plan_id ? String(seed.production_plan_id) : ''
    createForm.work_order = String(seed.work_order || '')
    createForm.job_card = String(seed.job_card || '')
  }
  createDialogVisible.value = true
}

const buildCreatePayload = (): SubcontractCreateRequestPayload => {
  const scenarioTag = createForm.scenario_tag.trim() || buildSubcontractScenarioTag()
  const idempotencyKey = createForm.idempotency_key.trim() || buildNonce('subcontract-create')
  const itemCode = createForm.item_code.trim()
  const plannedQty = String(createForm.planned_qty || '0').trim()
  const supplier = createForm.supplier.trim()
  const workOrderRef = normalizeWorkOrderRef(createForm.work_order, createForm.production_plan_id)
  const sourceRef = `${scenarioTag}:create:${itemCode}:${plannedQty}`
  const subcontractRef = `NEW-${Date.now()}`
  return {
    request_id: buildSubcontractRequestId({
      scenarioTag,
      operation: 'create',
      idempotencyKey,
      sourceRef,
      subcontractRef,
      supplierRef: supplier,
      workOrderRef,
      itemCode,
      statusAction: 'create',
    }),
    idempotency_key: idempotencyKey,
    scenario_tag: scenarioTag,
    source_ref: sourceRef,
    subcontract_ref: subcontractRef,
    supplier_ref: supplier,
    work_order_ref: workOrderRef,
    operation: 'create',
    item_code: itemCode,
    quantity: plannedQty,
    status_action: 'create',
    supplier,
    company: createForm.company.trim() || null,
    bom_id: Number(createForm.bom_id),
    planned_qty: plannedQty,
    process_name: createForm.process_name.trim(),
    sales_order: createForm.sales_order.trim() || null,
    sales_order_item: createForm.sales_order_item.trim() || null,
    production_plan_id: createForm.production_plan_id.trim() ? Number(createForm.production_plan_id) : null,
    work_order: createForm.work_order.trim() || null,
    job_card: createForm.job_card.trim() || null,
  }
}

const submitCreate = async (): Promise<void> => {
  createSubmitting.value = true
  try {
    const payload = buildCreatePayload()
    const response = await createSubcontractOrder(payload)
    createDialogVisible.value = false
    ElMessage.success(`已创建委外单 ${response.data.name}`)
    Object.assign(query, buildDefaultQuery())
    await loadRows()
    const createdRow = rows.value.find((row) => row.subcontract_no === response.data.name)
    if (createdRow) {
      openDetail(createdRow.id)
      return
    }
    feedback.value = `已创建 ${response.data.name}，但当前页未命中该单据，请刷新后查看。`
  } catch (error) {
    ElMessage.error((error as Error).message || '创建委外单失败')
  } finally {
    createSubmitting.value = false
  }
}

onMounted(() => {
  void loadRows()
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
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.header-row h2 {
  margin: 0;
  font-size: 18px;
}

.sub-title {
  margin: 4px 0 0;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.header-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.top-alert {
  margin-top: 12px;
}

.stacked-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
