<template>
  <div class="operation-wage-rate" data-testid="wage-rates-page">
    <el-card shadow="never">
      <template #header>
        <div class="header-row">
          <span>工价档案</span>
          <div class="header-actions">
            <el-button
              data-testid="wage-rates-back-to-tickets"
              data-action-type="navigation"
              data-readonly-action="true"
              data-route-path="/workshop/tickets"
              @click="goList"
            >
              返回工票列表
            </el-button>
            <el-button
              data-testid="wage-rates-create-action"
              type="primary"
              :disabled="!canManage"
              @click="openCreateDialog"
            >
              新增工价
            </el-button>
          </div>
        </div>
      </template>

      <el-form :inline="true" :model="query" data-testid="wage-rates-filter-form">
        <el-form-item label="款式">
          <el-input
            v-model="query.item_code"
            clearable
            placeholder="Item Code，空表示通用工价"
            data-testid="wage-rates-filter-item-code"
          />
        </el-form-item>
        <el-form-item label="公司">
          <el-input
            v-model="query.company"
            clearable
            placeholder="Company"
            data-testid="wage-rates-filter-company"
          />
        </el-form-item>
        <el-form-item label="类型">
          <el-select
            v-model="query.rate_scope"
            clearable
            style="width: 140px"
            placeholder="选择类型"
            aria-label="工价类型"
            data-testid="wage-rates-filter-rate-scope"
          >
            <el-option label="全部" value="" />
            <el-option label="款式专属" value="specific" />
            <el-option label="通用工价" value="global" />
          </el-select>
        </el-form-item>
        <el-form-item label="工序">
          <el-input
            v-model="query.process_name"
            clearable
            placeholder="Process"
            data-testid="wage-rates-filter-process-name"
          />
        </el-form-item>
        <el-form-item label="状态">
          <el-select
            v-model="query.status"
            clearable
            style="width: 140px"
            placeholder="选择状态"
            aria-label="工价状态"
            data-testid="wage-rates-filter-status"
          >
            <el-option label="active" value="active" />
            <el-option label="inactive" value="inactive" />
          </el-select>
        </el-form-item>
        <el-form-item label="操作">
          <el-button
            data-testid="wage-rates-query-button"
            type="primary"
            :disabled="!canRead"
            @click="applyPrimaryQuery"
          >
            查询
          </el-button>
          <el-button
            data-testid="wage-rates-reset-button"
            :disabled="!canRead"
            @click="resetPrimaryFilters"
          >
            重置
          </el-button>
        </el-form-item>
      </el-form>

      <el-empty v-if="!canRead" data-testid="wage-rates-permission-state" description="无工价查看权限" />
      <template v-else>
        <el-alert
          v-if="errorMessage"
          data-testid="wage-rates-error-state"
          type="error"
          show-icon
          :closable="false"
          :title="errorMessage"
        />
        <el-table
          data-testid="wage-rates-table"
          :data="rows"
          v-loading="loading"
          border
          empty-text="暂无工价记录"
        >
          <el-table-column prop="id" label="ID" width="80" />
          <el-table-column label="类型" width="110">
            <template #default="scope">
              <el-tag
                data-testid="wage-rates-scope-tag"
                :type="scope.row.is_global ? 'warning' : 'primary'"
              >
                {{ scope.row.is_global ? '通用' : '款式专属' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="款式" min-width="140">
            <template #default="scope">
              {{ scope.row.item_code || '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="company" label="公司" min-width="120" />
          <el-table-column prop="process_name" label="工序" min-width="120" />
          <el-table-column prop="wage_rate" label="计件单价" min-width="120" />
          <el-table-column prop="effective_from" label="生效开始" min-width="120" />
          <el-table-column prop="effective_to" label="生效结束" min-width="120" />
          <el-table-column label="状态" width="110">
            <template #default="scope">
              <el-tag data-testid="wage-rates-status-tag" :type="statusTagType(scope.row.status)">
                {{ scope.row.status || 'unknown' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="created_by" label="创建人" min-width="120" />
          <el-table-column label="操作" width="130" fixed="right">
            <template #default="scope">
              <el-button
                data-testid="wage-rates-deactivate-action"
                link
                type="danger"
                :disabled="!canManage || scope.row.status !== 'active' || (scope.row.is_global && !canManageAll)"
                @click="onDeactivate(scope.row)"
              >
                停用
              </el-button>
            </template>
          </el-table-column>
        </el-table>
        <p
          v-if="!loading && rows.length === 0 && !errorMessage"
          data-testid="wage-rates-empty-state"
          class="state-hint"
        >
          暂无工价记录
        </p>

        <div class="pager">
          <el-pagination
            data-testid="wage-rates-pagination"
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
      title="新增工价"
      width="560px"
      destroy-on-close
      data-testid="wage-rates-create-dialog"
    >
      <el-form label-width="120px" data-testid="wage-rates-create-form">
        <el-form-item label="款式">
          <el-input
            v-model="createForm.item_code"
            clearable
            placeholder="为空时按通用工价处理"
            data-testid="wage-rates-create-item-code"
          />
        </el-form-item>
        <el-form-item label="公司">
          <el-input
            v-model="createForm.company"
            clearable
            placeholder="Company"
            data-testid="wage-rates-create-company"
          />
        </el-form-item>
        <el-form-item label="工序">
          <el-input
            v-model="createForm.process_name"
            clearable
            placeholder="Process Name"
            data-testid="wage-rates-create-process-name"
          />
        </el-form-item>
        <el-form-item label="计件单价">
          <el-input
            v-model="createForm.wage_rate"
            clearable
            placeholder="例如 1.25"
            data-testid="wage-rates-create-wage-rate"
          />
        </el-form-item>
        <el-form-item label="生效开始">
          <el-date-picker
            v-model="createForm.effective_from"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="选择开始日期"
            aria-label="工价生效开始日期"
            data-testid="wage-rates-create-effective-from"
          />
        </el-form-item>
        <el-form-item label="生效结束">
          <el-date-picker
            v-model="createForm.effective_to"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="可为空"
            aria-label="工价生效结束日期"
            data-testid="wage-rates-create-effective-to"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button
          type="primary"
          :loading="createSubmitting"
          data-testid="wage-rates-create-submit"
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
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createWorkshopWageRate,
  deactivateWorkshopWageRate,
  fetchWorkshopWageRates,
  type WorkshopWageRateDeactivatePayload,
  type WorkshopWageRateRow,
} from '@/api/workshop'
import { usePermissionStore } from '@/stores/permission'

const router = useRouter()
const permissionStore = usePermissionStore()
const defaultPageSize = 20
const WRITE_EVENT_STORAGE_KEY = 'ly_workshop_wage_last_write_v1'
const REQUEST_ID_REGEX = /^[A-Za-z0-9_.-]{1,64}$/
const loading = ref<boolean>(false)
const rows = ref<WorkshopWageRateRow[]>([])
const total = ref<number>(0)
const errorMessage = ref<string>('')
const createDialogVisible = ref<boolean>(false)
const createSubmitting = ref<boolean>(false)

const query = reactive({
  item_code: '',
  company: '',
  rate_scope: '',
  process_name: '',
  status: '',
  page: 1,
  page_size: defaultPageSize,
})

const createForm = reactive({
  item_code: '',
  company: 'LY-LOCAL-TEST',
  process_name: '',
  wage_rate: '',
  effective_from: '',
  effective_to: '',
})

const canRead = computed<boolean>(() => permissionStore.state.buttonPermissions.wage_rate_read)
const canReadAll = computed<boolean>(() => permissionStore.state.buttonPermissions.wage_rate_read_all)
const canManage = computed<boolean>(() => permissionStore.state.buttonPermissions.wage_rate_manage)
const canManageAll = computed<boolean>(() => permissionStore.state.buttonPermissions.wage_rate_manage_all)

const normalizeText = (value: string): string => value.trim()

const normalizeDateCode = (value: string): string => value.replace(/-/g, '')

const hash4 = (value: string): string => {
  let hash = 2166136261
  for (let i = 0; i < value.length; i += 1) {
    hash ^= value.charCodeAt(i)
    hash = Math.imul(hash, 16777619) >>> 0
  }
  return hash.toString(16).toUpperCase().padStart(8, '0').slice(-4)
}

const scenarioDate = (): string => {
  const now = new Date()
  const y = now.getFullYear().toString()
  const m = String(now.getMonth() + 1).padStart(2, '0')
  const d = String(now.getDate()).padStart(2, '0')
  return `${y}${m}${d}`
}

const buildScenarioTag = (): string => {
  const seq = String(Math.floor(Math.random() * 900) + 100)
  return `Z002-WORKSHOP-WAGE-${scenarioDate()}-${seq}`
}

const buildRequestId = (
  scenarioTag: string,
  company: string,
  processName: string,
  itemScope: string,
  effectiveFrom: string,
): string => {
  const requestId = `${scenarioTag}-RW-C${hash4(company)}-P${hash4(processName)}-I${hash4(itemScope)}-D${normalizeDateCode(effectiveFrom)}`
  if (!REQUEST_ID_REGEX.test(requestId)) {
    throw new Error('request_id 生成失败：格式不合法')
  }
  return requestId
}

const saveLastWriteEvent = (payload: Record<string, unknown>): void => {
  localStorage.setItem(
    WRITE_EVENT_STORAGE_KEY,
    JSON.stringify({
      ...payload,
      updated_at: new Date().toISOString(),
    }),
  )
}

const buildWageRateQuery = (): {
  item_code?: string
  company?: string
  is_global?: boolean
  process_name?: string
  status?: string
  page: number
  page_size: number
} => ({
  item_code: query.item_code || undefined,
  company: query.company || undefined,
  is_global:
    query.rate_scope === 'global' ? true : query.rate_scope === 'specific' ? false : undefined,
  process_name: query.process_name || undefined,
  status: query.status || undefined,
  page: query.page,
  page_size: query.page_size,
})

const loadRows = async (): Promise<void> => {
  if (!canRead.value) {
    rows.value = []
    total.value = 0
    errorMessage.value = ''
    return
  }
  if (query.rate_scope === 'global' && !canReadAll.value) {
    rows.value = []
    total.value = 0
    errorMessage.value = ''
    ElMessage.warning('无通用工价查看权限')
    return
  }
  loading.value = true
  errorMessage.value = ''
  try {
    const result = await fetchWorkshopWageRates(buildWageRateQuery())
    rows.value = result.data.items
    total.value = result.data.total
  } catch (error) {
    const message = (error as Error).message || '工价档案加载失败'
    rows.value = []
    total.value = 0
    errorMessage.value = message
    ElMessage.error(message)
  } finally {
    loading.value = false
  }
}

const statusTagType = (status: string): 'success' | 'info' | 'warning' => {
  if (status === 'active') {
    return 'success'
  }
  if (status === 'inactive') {
    return 'info'
  }
  return 'warning'
}

const applyPrimaryQuery = (): void => {
  query.page = 1
  void loadRows()
}

const resetPrimaryFilters = (): void => {
  query.item_code = ''
  query.company = ''
  query.rate_scope = ''
  query.process_name = ''
  query.status = ''
  query.page = 1
  query.page_size = defaultPageSize
  void loadRows()
}

const openCreateDialog = (): void => {
  if (!canManage.value) {
    ElMessage.warning('无工价维护权限')
    return
  }
  createDialogVisible.value = true
}

const submitCreate = async (): Promise<void> => {
  if (!canManage.value) {
    ElMessage.warning('无工价维护权限')
    return
  }
  const company = normalizeText(createForm.company)
  const processName = normalizeText(createForm.process_name)
  const itemCode = normalizeText(createForm.item_code)
  const wageRate = Number(createForm.wage_rate)
  const effectiveFrom = normalizeText(createForm.effective_from)
  const effectiveTo = normalizeText(createForm.effective_to)

  if (!company) {
    ElMessage.warning('company 不能为空')
    return
  }
  if (!processName) {
    ElMessage.warning('process_name 不能为空')
    return
  }
  if (!Number.isFinite(wageRate) || wageRate < 0) {
    ElMessage.warning('wage_rate 必须为非负数')
    return
  }
  if (!effectiveFrom) {
    ElMessage.warning('effective_from 不能为空')
    return
  }

  const scenarioTag = buildScenarioTag()
  const itemScope = itemCode || 'GLOBAL'
  const requestId = buildRequestId(scenarioTag, company, processName, itemScope, effectiveFrom)
  const idempotencyKey = `IDM-${scenarioTag}-CREATE-${Date.now().toString(36).toUpperCase()}`
  const sourceRef = `SRC-${scenarioTag}-CREATE`

  createSubmitting.value = true
  try {
    const result = await createWorkshopWageRate(
      {
        item_code: itemCode || undefined,
        company,
        process_name: processName,
        wage_rate: wageRate,
        effective_from: effectiveFrom,
        effective_to: effectiveTo || undefined,
        scenario_tag: scenarioTag,
        idempotency_key: idempotencyKey,
        source_ref: sourceRef,
      },
      { requestId },
    )
    saveLastWriteEvent({
      action: 'create',
      scenario_tag: scenarioTag,
      request_id: requestId,
      company,
      process_name: processName,
      item_scope: itemScope,
      wage_rate: wageRate,
      effective_from: effectiveFrom,
      effective_to: effectiveTo || null,
      rate_id: result.data.id,
    })
    ElMessage.success(`新增成功，ID=${result.data.id}`)
    createDialogVisible.value = false
    createForm.item_code = ''
    createForm.process_name = ''
    createForm.wage_rate = ''
    createForm.effective_from = ''
    createForm.effective_to = ''
    await loadRows()
  } catch (error) {
    ElMessage.error((error as Error).message || '新增工价失败')
  } finally {
    createSubmitting.value = false
  }
}

const onDeactivate = async (row: WorkshopWageRateRow): Promise<void> => {
  if (!canManage.value || row.status !== 'active' || (row.is_global && !canManageAll.value)) {
    ElMessage.warning('当前记录不可停用或无权限')
    return
  }
  try {
    const reasonInput = await ElMessageBox.prompt('请输入停用原因（将自动携带 scenario_tag）', '停用工价', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      inputPattern: /\S+/,
      inputErrorMessage: '停用原因不能为空',
    })
    const scenarioTag = buildScenarioTag()
    const company = normalizeText(row.company || 'GLOBAL')
    const processName = normalizeText(row.process_name)
    const itemScope = normalizeText(row.item_code || 'GLOBAL')
    const effectiveFrom = normalizeText(row.effective_from)
    const requestId = buildRequestId(scenarioTag, company, processName, itemScope, effectiveFrom)
    const idempotencyKey = `IDM-${scenarioTag}-DEACT-${row.id}`
    const sourceRef = `SRC-${scenarioTag}-DEACT-${row.id}`
    const reason = `${normalizeText(reasonInput.value)}|${scenarioTag}`
    const payload: WorkshopWageRateDeactivatePayload = {
      reason,
      scenario_tag: scenarioTag,
      idempotency_key: idempotencyKey,
      source_ref: sourceRef,
      company: row.company || undefined,
      process_name: row.process_name,
      item_code: row.item_code || undefined,
      wage_rate: Number(row.wage_rate),
      effective_from: row.effective_from,
      effective_to: row.effective_to || undefined,
      rate_id: row.id,
    }
    const result = await deactivateWorkshopWageRate(row.id, payload, { requestId })
    saveLastWriteEvent({
      action: 'deactivate',
      scenario_tag: scenarioTag,
      request_id: requestId,
      company: row.company || 'GLOBAL',
      process_name: row.process_name,
      item_scope: row.item_code || 'GLOBAL',
      wage_rate: row.wage_rate,
      effective_from: row.effective_from,
      effective_to: row.effective_to || null,
      rate_id: row.id,
      reason,
      status: result.data.status,
    })
    ElMessage.success(`停用成功，ID=${row.id}`)
    await loadRows()
  } catch (error) {
    if (error === 'cancel' || error === 'close') {
      return
    }
    const typed = error as { message?: string }
    ElMessage.error(typed.message || '停用工价失败')
  }
}

const onPageChange = (page: number): void => {
  query.page = page
  void loadRows()
}

const onSizeChange = (size: number): void => {
  query.page_size = size
  query.page = 1
  void loadRows()
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
  await loadRows()
})
</script>

<style scoped>
.operation-wage-rate {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.pager {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}

.state-hint {
  margin-top: 8px;
  color: var(--el-text-color-secondary);
}
</style>
