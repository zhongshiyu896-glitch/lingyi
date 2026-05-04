<template>
  <div class="factory-statement-list-page">
    <el-card shadow="never">
      <template #header>
        <div class="header-row">
          <span>加工厂对账单列表</span>
          <el-button
            type="primary"
            :disabled="!canCreateAction"
            data-action-type="write"
            data-write-guard="permission:factory_statement_create+handler"
            :data-guard-state="canCreateAction ? 'enabled' : 'disabled'"
            @click="openCreateDialog"
          >
            创建对账单
          </el-button>
        </div>
      </template>

      <el-alert
        type="info"
        :closable="false"
        show-icon
        title="款式打板下单对账表（TASK-Y22B-P1-02）"
        description="本页补齐只读语义映射；创建/确认/取消/应付草稿/导出等写动作仅保留 guarded 语义，不触发真实写请求。"
        class="reconciliation-alert"
      />

      <el-form :inline="true" :model="query">
        <el-form-item label="供应商">
          <el-input v-model="query.supplier" clearable placeholder="请输入供应商" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.statement_status" clearable placeholder="请选择状态" style="width: 160px">
            <el-option label="草稿" value="draft" />
            <el-option label="已确认" value="confirmed" />
            <el-option label="已取消" value="cancelled" />
            <el-option label="应付草稿已生成" value="payable_draft_created" />
          </el-select>
        </el-form-item>
        <el-form-item label="开始日期">
          <el-date-picker
            v-model="query.from_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="请选择开始日期"
            clearable
          />
        </el-form-item>
        <el-form-item label="结束日期">
          <el-date-picker
            v-model="query.to_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="请选择结束日期"
            clearable
          />
        </el-form-item>
        <el-form-item label="操作">
          <el-button type="primary" :disabled="!canRead" @click="loadRows">查询</el-button>
        </el-form-item>
      </el-form>

      <el-form :inline="true" :model="sampleQuery" class="sample-filter-form">
        <el-form-item label="打板单号">
          <el-input v-model="sampleQuery.sample_order_no" clearable placeholder="请输入打板单号" />
        </el-form-item>
        <el-form-item label="款号">
          <el-input v-model="sampleQuery.style_code" clearable placeholder="请输入款号" />
        </el-form-item>
        <el-form-item label="工厂">
          <el-input v-model="sampleQuery.factory_name" clearable placeholder="请输入工厂" />
        </el-form-item>
        <el-form-item label="下单时间">
          <el-date-picker
            v-model="sampleQuery.ordered_date_range"
            type="daterange"
            value-format="YYYY-MM-DD"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            clearable
          />
        </el-form-item>
        <el-form-item label="金额区间">
          <el-input-number
            v-model="sampleQuery.min_amount"
            :precision="2"
            :controls="false"
            placeholder="最小金额"
            style="width: 130px"
          />
          <span class="range-sep">~</span>
          <el-input-number
            v-model="sampleQuery.max_amount"
            :precision="2"
            :controls="false"
            placeholder="最大金额"
            style="width: 130px"
          />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="sampleQuery.status" clearable placeholder="请选择状态" style="width: 160px">
            <el-option label="草稿" value="draft" />
            <el-option label="已确认" value="confirmed" />
            <el-option label="已取消" value="cancelled" />
            <el-option label="应付草稿已生成" value="payable_draft_created" />
          </el-select>
        </el-form-item>
        <el-form-item label="操作">
          <el-button type="primary" :disabled="!canRead" @click="applySampleFilters">筛选</el-button>
          <el-button :disabled="!canRead" @click="resetSampleFilters">重置</el-button>
        </el-form-item>
      </el-form>

      <el-alert v-if="readError" type="error" :closable="false" show-icon :title="readError" class="error-alert" />
      <el-empty v-if="!canRead" description="无加工厂对账单查看权限" />
      <template v-else>
        <el-table :data="displayRows" border v-loading="loading" empty-text="暂无款式打板下单对账数据">
          <el-table-column prop="sample_order_no" label="打板单号" min-width="180" />
          <el-table-column prop="style_code" label="款号" min-width="140" />
          <el-table-column prop="factory_name" label="工厂" min-width="140" />
          <el-table-column prop="ordered_at" label="下单时间" min-width="180" />
          <el-table-column label="下单金额" width="130">
            <template #default="scope">{{ formatAmount(scope.row.order_amount) }}</template>
          </el-table-column>
          <el-table-column prop="statement_no" label="对账单号" min-width="180" />
          <el-table-column prop="company" label="公司" min-width="140" />
          <el-table-column prop="supplier" label="供应商" min-width="140" />
          <el-table-column label="期间" min-width="200">
            <template #default="scope">
              {{ scope.row.from_date }} ~ {{ scope.row.to_date }}
            </template>
          </el-table-column>
          <el-table-column label="数量" width="110">
            <template #default="scope">{{ scope.row.source_count }}</template>
          </el-table-column>
          <el-table-column label="加工费" width="130">
            <template #default="scope">{{ formatAmount(scope.row.gross_amount) }}</template>
          </el-table-column>
          <el-table-column label="扣款" width="130">
            <template #default="scope">{{ formatAmount(scope.row.deduction_amount) }}</template>
          </el-table-column>
          <el-table-column label="实付金额" width="130">
            <template #default="scope">{{ formatAmount(scope.row.net_amount) }}</template>
          </el-table-column>
          <el-table-column label="状态" min-width="150">
            <template #default="scope">
              <el-tag :type="statusTag(scope.row.statement_status)">
                {{ statementStatusLabel(scope.row.statement_status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="应付草稿同步" min-width="140">
            <template #default="scope">
              {{ outboxStatusLabel(scope.row.payable_outbox_status) }}
            </template>
          </el-table-column>
          <el-table-column label="ERP 发票草稿" min-width="180">
            <template #default="scope">
              {{ scope.row.purchase_invoice_name || '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="创建时间" min-width="180" />
          <el-table-column label="操作" fixed="right" width="340">
            <template #default="scope">
              <el-button link type="primary" @click="goDetail(scope.row.id)">查看</el-button>
              <el-button link type="primary" @click="goPrint(scope.row.id)">打印</el-button>
              <el-button
                link
                type="info"
                data-action-type="write"
                data-write-guard="readonly:export"
                data-guard-state="disabled"
                @click="showGuardedAction('导出')"
              >
                导出
              </el-button>
              <el-button
                link
                type="warning"
                data-action-type="write"
                data-write-guard="readonly:payable-draft"
                data-guard-state="disabled"
                @click="showGuardedAction('生成应付')"
              >
                生成应付
              </el-button>
              <el-button
                link
                type="success"
                data-action-type="write"
                data-write-guard="readonly:confirm"
                data-guard-state="disabled"
                @click="showGuardedAction('确认')"
              >
                确认
              </el-button>
              <el-button
                link
                type="danger"
                data-action-type="write"
                data-write-guard="readonly:cancel"
                data-guard-state="disabled"
                @click="showGuardedAction('取消')"
              >
                取消
              </el-button>
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

    <el-dialog v-model="createVisible" title="创建加工厂对账单" width="680px">
        <el-form :model="createForm" label-width="120px">
          <el-form-item label="公司">
          <el-input v-model="createForm.company" placeholder="请输入公司名称" />
          </el-form-item>
          <el-form-item label="供应商">
          <el-input v-model="createForm.supplier" placeholder="请输入供应商名称" />
          </el-form-item>
          <el-form-item label="开始日期">
            <el-date-picker
              v-model="createForm.from_date"
              type="date"
              value-format="YYYY-MM-DD"
            placeholder="请选择开始日期"
              style="width: 100%"
            />
          </el-form-item>
        <el-form-item label="结束日期">
          <el-date-picker
              v-model="createForm.to_date"
              type="date"
              value-format="YYYY-MM-DD"
            placeholder="请选择结束日期"
              style="width: 100%"
            />
          </el-form-item>
          <el-form-item label="幂等键">
          <el-input v-model="createForm.idempotency_key" placeholder="请输入幂等键" />
          </el-form-item>
        </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" :disabled="!canSubmitCreate" @click="submitCreateStatement">
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
  createFactoryStatement,
  fetchFactoryStatements,
  type FactoryStatementCreatePayload,
  type FactoryStatementListItem,
} from '@/api/factory_statement'
import { usePermissionStore } from '@/stores/permission'

const router = useRouter()
const permissionStore = usePermissionStore()

const loading = ref<boolean>(false)
const creating = ref<boolean>(false)
const createVisible = ref<boolean>(false)
const readError = ref<string>('')
const rows = ref<FactoryStatementListItem[]>([])
const total = ref<number>(0)

const P1_READONLY_MODE = true
const readonlyWriteHint = '当前为只读对账视图，已禁用写动作'

interface SampleOrderReconciliationRow extends FactoryStatementListItem {
  sample_order_no: string
  style_code: string
  factory_name: string
  ordered_at: string
  order_amount: number | null
}

const canRead = computed<boolean>(() => permissionStore.state.buttonPermissions.factory_statement_read)
const canCreate = computed<boolean>(() => permissionStore.state.buttonPermissions.factory_statement_create)
const canCreateAction = computed<boolean>(() => canCreate.value && !P1_READONLY_MODE)

const query = reactive({
  supplier: '',
  statement_status: '',
  from_date: '',
  to_date: '',
  page: 1,
  page_size: 20,
})

const sampleQuery = reactive({
  sample_order_no: '',
  style_code: '',
  factory_name: '',
  ordered_date_range: [] as string[],
  min_amount: undefined as number | undefined,
  max_amount: undefined as number | undefined,
  status: '',
})

const createForm = reactive({
  company: '',
  supplier: '',
  from_date: '',
  to_date: '',
  idempotency_key: '',
})

const normalizedCreateForm = computed(() => ({
  company: createForm.company.trim(),
  supplier: createForm.supplier.trim(),
  from_date: createForm.from_date || '',
  to_date: createForm.to_date || '',
  idempotency_key: createForm.idempotency_key.trim(),
}))

const createFormValidationError = computed<string | null>(() => {
  if (!normalizedCreateForm.value.company) {
    return '公司不能为空'
  }
  if (!normalizedCreateForm.value.supplier) {
    return '供应商不能为空'
  }
  if (!normalizedCreateForm.value.from_date) {
    return '开始日期不能为空'
  }
  if (!normalizedCreateForm.value.to_date) {
    return '结束日期不能为空'
  }
  if (normalizedCreateForm.value.from_date > normalizedCreateForm.value.to_date) {
    return '开始日期不能晚于结束日期'
  }
  if (!normalizedCreateForm.value.idempotency_key) {
    return '幂等键不能为空'
  }
  return null
})

const canSubmitCreate = computed<boolean>(() => canCreate.value && !createFormValidationError.value)

const normalizeText = (value: string | null | undefined): string => (value || '').trim().toLowerCase()

const normalizeDate = (value: string | null | undefined): string => {
  if (!value) {
    return ''
  }
  const raw = String(value)
  if (raw.includes('T')) {
    return raw.slice(0, 10)
  }
  if (raw.includes(' ')) {
    return raw.slice(0, 10)
  }
  return raw.slice(0, 10)
}

const toNumeric = (value: string | number | null | undefined): number | null => {
  if (value === null || value === undefined || value === '') {
    return null
  }
  const n = Number(value)
  return Number.isFinite(n) ? n : null
}

const toSampleRow = (row: FactoryStatementListItem): SampleOrderReconciliationRow => ({
  ...row,
  sample_order_no: row.statement_no || '-',
  style_code: row.purchase_invoice_name || '-',
  factory_name: row.supplier || '-',
  ordered_at: normalizeDate(row.created_at) || '-',
  order_amount: toNumeric(row.net_amount),
})

const withinRange = (value: string, from: string, to: string): boolean => {
  if (!value) {
    return false
  }
  if (from && value < from) {
    return false
  }
  if (to && value > to) {
    return false
  }
  return true
}

const displayRows = computed<SampleOrderReconciliationRow[]>(() => {
  const sampleOrderNeedle = normalizeText(sampleQuery.sample_order_no)
  const styleNeedle = normalizeText(sampleQuery.style_code)
  const factoryNeedle = normalizeText(sampleQuery.factory_name)
  const statusNeedle = normalizeText(sampleQuery.status)
  const from = sampleQuery.ordered_date_range[0] || ''
  const to = sampleQuery.ordered_date_range[1] || ''

  return rows.value
    .map((row) => toSampleRow(row))
    .filter((row) => {
      if (sampleOrderNeedle && !normalizeText(row.sample_order_no).includes(sampleOrderNeedle)) {
        return false
      }
      if (styleNeedle && !normalizeText(row.style_code).includes(styleNeedle)) {
        return false
      }
      if (factoryNeedle && !normalizeText(row.factory_name).includes(factoryNeedle)) {
        return false
      }
      if (statusNeedle && normalizeText(row.statement_status) !== statusNeedle) {
        return false
      }
      if ((from || to) && !withinRange(normalizeDate(row.ordered_at), from, to)) {
        return false
      }

      const amount = row.order_amount
      if (sampleQuery.min_amount !== undefined && sampleQuery.min_amount !== null) {
        if (amount === null || amount < sampleQuery.min_amount) {
          return false
        }
      }
      if (sampleQuery.max_amount !== undefined && sampleQuery.max_amount !== null) {
        if (amount === null || amount > sampleQuery.max_amount) {
          return false
        }
      }
      return true
    })
})

const formatAmount = (value: string | number | null | undefined): string => {
  if (value === null || value === undefined || value === '') {
    return '-'
  }
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric.toFixed(2) : String(value)
}

const statementStatusLabel = (status: string | null | undefined): string => {
  if (status === 'draft') {
    return '草稿'
  }
  if (status === 'confirmed') {
    return '已确认'
  }
  if (status === 'cancelled') {
    return '已取消'
  }
  if (status === 'payable_draft_created') {
    return '应付草稿已生成'
  }
  return status || '-'
}

const outboxStatusLabel = (status: string | null | undefined): string => {
  if (status === 'pending') {
    return '待同步'
  }
  if (status === 'processing') {
    return '同步中'
  }
  if (status === 'succeeded') {
    return '已生成草稿'
  }
  if (status === 'failed') {
    return '同步失败'
  }
  if (status === 'dead') {
    return '同步死信'
  }
  return '-'
}

const statusTag = (status: string | null | undefined): 'warning' | 'success' | 'danger' | 'info' => {
  if (status === 'draft') {
    return 'warning'
  }
  if (status === 'confirmed') {
    return 'success'
  }
  if (status === 'cancelled') {
    return 'danger'
  }
  return 'info'
}

const buildIdempotencyKey = (prefix: string): string => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return `${prefix}-${crypto.randomUUID()}`
  }
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

const openCreateDialog = (): void => {
  if (P1_READONLY_MODE) {
    ElMessage.warning(readonlyWriteHint)
    return
  }
  if (!canCreate.value) {
    ElMessage.error('无创建对账单权限')
    return
  }
  createForm.company = ''
  createForm.supplier = query.supplier.trim()
  createForm.from_date = query.from_date || ''
  createForm.to_date = query.to_date || ''
  createForm.idempotency_key = buildIdempotencyKey('factory-statement-create')
  createVisible.value = true
}

const submitCreateStatement = async (): Promise<void> => {
  if (P1_READONLY_MODE) {
    ElMessage.warning(readonlyWriteHint)
    return
  }
  if (!canCreate.value) {
    ElMessage.error('无创建对账单权限')
    return
  }
  const validationError = createFormValidationError.value
  if (validationError) {
    ElMessage.error(validationError)
    return
  }

  const payload: FactoryStatementCreatePayload = {
    company: normalizedCreateForm.value.company,
    supplier: normalizedCreateForm.value.supplier,
    from_date: normalizedCreateForm.value.from_date,
    to_date: normalizedCreateForm.value.to_date,
    idempotency_key: normalizedCreateForm.value.idempotency_key,
  }

  creating.value = true
  try {
    const result = await createFactoryStatement(payload)
    ElMessage.success(`创建成功：${result.data.statement_no}`)
    createVisible.value = false
    createForm.idempotency_key = buildIdempotencyKey('factory-statement-create')
    await loadRows()
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    creating.value = false
  }
}

const resetRows = (): void => {
  rows.value = []
  total.value = 0
  readError.value = ''
}

const applySampleFilters = (): void => {
  if (!canRead.value) {
    return
  }
}

const resetSampleFilters = (): void => {
  sampleQuery.sample_order_no = ''
  sampleQuery.style_code = ''
  sampleQuery.factory_name = ''
  sampleQuery.ordered_date_range = []
  sampleQuery.min_amount = undefined
  sampleQuery.max_amount = undefined
  sampleQuery.status = ''
}

const loadRows = async (): Promise<void> => {
  if (!canRead.value) {
    resetRows()
    return
  }

  loading.value = true
  readError.value = ''
  try {
    const result = await fetchFactoryStatements({
      supplier: query.supplier.trim() || undefined,
      statement_status: query.statement_status || undefined,
      from_date: query.from_date || undefined,
      to_date: query.to_date || undefined,
      page: query.page,
      page_size: query.page_size,
    })
    rows.value = result.data.items
    total.value = result.data.total
  } catch (error) {
    const message = (error as Error).message
    readError.value = message
    ElMessage.error(message)
  } finally {
    loading.value = false
  }
}

const goDetail = (statementId: number): void => {
  router.push({ path: '/factory-statements/detail', query: { id: String(statementId) } })
}

const goPrint = (statementId: number): void => {
  router.push({ path: '/factory-statements/print', query: { id: String(statementId) } })
}

const showGuardedAction = (actionLabel: string): void => {
  ElMessage.warning(`${actionLabel}已禁用：${readonlyWriteHint}`)
}

const onPageChange = (page: number): void => {
  query.page = page
  loadRows()
}

const onSizeChange = (size: number): void => {
  query.page_size = size
  query.page = 1
  loadRows()
}

onMounted(async () => {
  try {
    await permissionStore.loadCurrentUser()
    await permissionStore.loadModuleActions('factory_statement')
  } catch (error) {
    ElMessage.error((error as Error).message)
    return
  }
  if (canRead.value) {
    await loadRows()
  }
})
</script>

<style scoped>
.factory-statement-list-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.reconciliation-alert {
  margin-bottom: 12px;
}

.sample-filter-form {
  margin-top: 8px;
}

.range-sep {
  margin: 0 8px;
  color: #6b7280;
}

.error-alert {
  margin-bottom: 12px;
}

.pager {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}
</style>
