<template>
  <div class="workshop-ticket-list" data-testid="workshop-ticket-list-page">
    <el-card shadow="never" data-testid="workshop-ticket-main-section">
      <template #header>
        <div class="header-row">
          <span>车间工票查询</span>
          <div class="header-actions" data-testid="workshop-ticket-guarded-actions">
            <span
              hidden
              data-testid="workshop-write-guard"
              data-guard-state="guarded_readonly"
              data-write-guard="readonly:workshop-ticket-actions"
            />
            <el-button
              v-if="canRegister"
              type="primary"
              data-action-type="write"
              data-write-guard="readonly:workshop-ticket-register"
              data-write-allowlist="workshop-ticket-register"
              data-guard-state="guarded_readonly"
              :disabled="true"
              :title="guardedActionMap['ticket-register'].reason"
              aria-disabled="true"
              @click="goRegister"
            >
              工票登记
            </el-button>
            <el-button
              v-if="canBatch"
              data-action-type="write"
              data-write-guard="readonly:workshop-ticket-batch"
              data-write-allowlist="workshop-ticket-batch"
              data-guard-state="guarded_readonly"
              :disabled="true"
              :title="guardedActionMap['ticket-batch'].reason"
              aria-disabled="true"
              @click="goBatch"
            >
              批量导入
            </el-button>
            <el-button v-if="canWageRead" @click="goDailyWage">日薪统计</el-button>
            <el-button v-if="canWageRateRead" @click="goWageRate">工价档案</el-button>
          </div>
        </div>
      </template>

      <el-form :inline="true" :model="query" data-testid="workshop-ticket-filter-form">
        <el-form-item label="员工">
          <div data-testid="workshop-ticket-filter-employee">
            <el-input v-model="query.employee" clearable placeholder="Employee" />
          </div>
        </el-form-item>
        <el-form-item label="工序卡">
          <div data-testid="workshop-ticket-filter-job-card">
            <el-input v-model="query.job_card" clearable placeholder="Job Card" />
          </div>
        </el-form-item>
        <el-form-item label="款式">
          <div data-testid="workshop-ticket-filter-item-code">
            <el-input v-model="query.item_code" clearable placeholder="Item Code" />
          </div>
        </el-form-item>
        <el-form-item label="工序">
          <div data-testid="workshop-ticket-filter-process-name">
            <el-input v-model="query.process_name" clearable placeholder="Process" />
          </div>
        </el-form-item>
        <el-form-item label="类型">
          <div data-testid="workshop-ticket-filter-operation-type">
            <el-select
              v-model="query.operation_type"
              clearable
              style="width: 140px"
              placeholder="选择工票类型"
              aria-label="工票类型"
            >
              <el-option label="登记" value="register" />
              <el-option label="撤销" value="reversal" />
            </el-select>
          </div>
        </el-form-item>
        <el-form-item label="日期从">
          <div data-testid="workshop-ticket-filter-from-date">
            <el-date-picker
              v-model="query.from_date"
              value-format="YYYY-MM-DD"
              type="date"
              placeholder="选择开始日期"
              aria-label="工票开始日期"
            />
          </div>
        </el-form-item>
        <el-form-item label="到">
          <div data-testid="workshop-ticket-filter-to-date">
            <el-date-picker
              v-model="query.to_date"
              value-format="YYYY-MM-DD"
              type="date"
              placeholder="选择结束日期"
              aria-label="工票结束日期"
            />
          </div>
        </el-form-item>
        <el-form-item label="操作">
          <div class="query-action" data-testid="workshop-ticket-query-btn">
            <el-button type="primary" :disabled="!canRead" @click="applyPrimaryQuery">查询</el-button>
          </div>
          <div class="query-action" data-testid="workshop-ticket-reset-btn">
            <el-button :disabled="!canRead" @click="resetPrimaryFilters">重置</el-button>
          </div>
        </el-form-item>
      </el-form>

      <el-alert
        type="info"
        :closable="false"
        show-icon
        :title="parityHintTitle"
        class="parity-hint"
        data-testid="workshop-ticket-parity-hint"
      />

      <el-empty v-if="!canRead" description="无工票查看权限" data-testid="workshop-ticket-no-permission" />
      <template v-else>
        <WorkshopTicketJobCardReadonlySection :summary="workshopTicketJobCardReadonlySummary" />
        <WorkshopTicketDiagnosticReadonlySection :summary="diagnosticReadonlySummary" />
        <el-alert
          v-if="errorMessage"
          type="error"
          :title="errorMessage"
          show-icon
          :closable="false"
          class="error-state"
          data-testid="workshop-ticket-error-state"
        />
        <div data-testid="workshop-ticket-table">
          <el-table :data="rows" v-loading="loading" border empty-text="暂无工票记录">
          <el-table-column prop="ticket_no" label="工票号" min-width="180" />
          <el-table-column prop="job_card" label="工序卡" min-width="120" />
          <el-table-column prop="employee" label="员工" min-width="120" />
          <el-table-column prop="item_code" label="款式" min-width="120" />
          <el-table-column prop="process_name" label="工序" min-width="120" />
          <el-table-column label="类型" width="100">
            <template #default="scope">
              <span data-testid="workshop-ticket-status-tag">{{ operationTypeLabel(scope.row.operation_type) }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="qty" label="数量" width="110" />
          <el-table-column prop="unit_wage" label="单价" width="110" />
          <el-table-column prop="wage_amount" label="工资" width="110" />
          <el-table-column label="同步状态" width="120">
            <template #default="scope">
              <span data-testid="workshop-ticket-sync-status">{{ syncStatusLabel(scope.row.sync_status) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="220" fixed="right">
            <template #default="scope">
              <span data-testid="workshop-ticket-summary-entry">
                <el-button link type="primary" @click="openSummary(scope.row.job_card)">汇总</el-button>
              </span>
              <el-button
                v-if="canSync"
                link
                type="success"
                data-write-guard="readonly:job-card-sync-retry"
                data-guard-state="guarded_readonly"
                :disabled="true"
                :title="guardedActionMap['job-card-sync-retry'].reason"
                aria-disabled="true"
                @click="retrySync(scope.row.job_card)"
              >
                重试同步
              </el-button>
            </template>
          </el-table-column>
          </el-table>
        </div>

        <el-empty
          v-if="!loading && !errorMessage && rows.length === 0"
          description="暂无工票记录"
          class="empty-state"
          data-testid="workshop-ticket-empty-state"
        />

        <div class="pager" data-testid="workshop-ticket-pagination">
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

    <el-dialog v-model="summaryVisible" title="Job Card 汇总" width="520px" data-testid="workshop-ticket-summary-dialog">
      <div data-testid="workshop-ticket-summary-panel">
        <el-descriptions v-if="summary" :column="2" border>
          <el-descriptions-item label="工序卡">{{ summary.job_card }}</el-descriptions-item>
          <el-descriptions-item label="同步状态">{{ summary.sync_status }}</el-descriptions-item>
          <el-descriptions-item label="Outbox 状态">{{ summary.outbox_status }}</el-descriptions-item>
          <el-descriptions-item label="最后同步时间">{{ summary.last_sync_at || '-' }}</el-descriptions-item>
          <el-descriptions-item label="登记数量">{{ summary.register_qty }}</el-descriptions-item>
          <el-descriptions-item label="撤销数量">{{ summary.reversal_qty }}</el-descriptions-item>
          <el-descriptions-item label="净完成数量">{{ summary.net_qty }}</el-descriptions-item>
          <el-descriptions-item label="最近错误码">{{ summary.last_error_code || '-' }}</el-descriptions-item>
          <el-descriptions-item label="最近错误信息">{{ summary.last_error_message || '-' }}</el-descriptions-item>
        </el-descriptions>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  fetchWorkshopJobCardSummary,
  fetchWorkshopTickets,
  type WorkshopJobCardSummaryData,
  type WorkshopTicketRow,
} from '@/api/workshop'
import { usePermissionStore } from '@/stores/permission'
import WorkshopTicketJobCardReadonlySection from './components/WorkshopTicketJobCardReadonlySection.vue'
import WorkshopTicketDiagnosticReadonlySection from './components/WorkshopTicketDiagnosticReadonlySection.vue'
import { useWorkshopTicketJobCardReadonly } from './composables/useWorkshopTicketJobCardReadonly'
import { useWorkshopTicketDiagnosticReadonly } from './composables/useWorkshopTicketDiagnosticReadonly'
import { WORKSHOP_TICKET_DIAGNOSTIC_READONLY_ACTIONS } from './constants/workshopTicketDiagnosticFields'
import { WORKSHOP_TICKET_JOB_CARD_READONLY_GUARDED_ACTIONS } from './constants/workshopTicketJobCardReadonlyFields'

const route = useRoute()
const router = useRouter()
const permissionStore = usePermissionStore()
const guardedActionMap = Object.fromEntries(
  WORKSHOP_TICKET_DIAGNOSTIC_READONLY_ACTIONS.map((action) => [action.key, action])
)
const GLOBAL_READONLY_GUARD_ATTR = 'data-workshop-ticket-list-readonly-disabled'
const GLOBAL_READONLY_PREV_DISABLED_ATTR = 'data-workshop-ticket-list-prev-disabled'
const GLOBAL_READONLY_PREV_ARIA_DISABLED_ATTR = 'data-workshop-ticket-list-prev-aria-disabled'
const GLOBAL_READONLY_PREV_TITLE_ATTR = 'data-workshop-ticket-list-prev-title'
const GLOBAL_READONLY_PREV_TABINDEX_ATTR = 'data-workshop-ticket-list-prev-tabindex'
const GLOBAL_WORKSHOP_TICKET_JOB_CARD_ACTION_GUARDS = [
  {
    selector: '#global-auth-refresh-guard',
    reason: WORKSHOP_TICKET_JOB_CARD_READONLY_GUARDED_ACTIONS.find((action) => action.key === 'refresh-permission')?.reason
      || 'job-card-readonly boundary keeps permission refresh non-executable on WorkshopTicketList.',
    disableNative: true,
  },
  {
    selector: '#z042-global-guarded-refresh',
    reason: WORKSHOP_TICKET_JOB_CARD_READONLY_GUARDED_ACTIONS.find((action) => action.key === 'refresh-permission')?.reason
      || 'job-card-readonly boundary keeps permission refresh non-executable on WorkshopTicketList.',
    disableNative: false,
  },
  {
    selector: 'button[data-readonly-action="fetchModuleActions"]',
    reason: WORKSHOP_TICKET_JOB_CARD_READONLY_GUARDED_ACTIONS.find((action) => action.key === 'reload-module-actions')?.reason
      || 'job-card-readonly boundary keeps module action reload non-executable on WorkshopTicketList.',
    disableNative: true,
  },
] as const
let globalWorkshopTicketListGuardObserver: MutationObserver | null = null
const loading = ref<boolean>(false)
const rows = ref<WorkshopTicketRow[]>([])
const total = ref<number>(0)
const errorMessage = ref<string>('')
const summaryVisible = ref<boolean>(false)
const summary = ref<WorkshopJobCardSummaryData | null>(null)

const query = reactive({
  employee: '',
  job_card: '',
  item_code: '',
  process_name: '',
  operation_type: '',
  from_date: '',
  to_date: '',
  page: 1,
  page_size: 20,
})

const canRead = computed<boolean>(() => permissionStore.state.buttonPermissions.read)
const canRegister = computed<boolean>(() => permissionStore.state.buttonPermissions.ticket_register)
const canBatch = computed<boolean>(() => permissionStore.state.buttonPermissions.ticket_batch)
const canWageRead = computed<boolean>(() => permissionStore.state.buttonPermissions.wage_read)
const canWageRateRead = computed<boolean>(() => permissionStore.state.buttonPermissions.wage_rate_read)
const canSync = computed<boolean>(() => permissionStore.state.buttonPermissions.job_card_sync)
const jobCardReadonlyParity = computed<string>(() => String(route.query.parity || ''))
const jobCardReadonlyFocus = computed<string>(() => String(route.query.focus || ''))
const jobCardReadonlyRoutePath = computed<string>(() => route.fullPath || route.path)
const jobCardReadonlyQueryStateLabel = computed<string>(() => {
  const jobCard = query.job_card.trim() || 'ALL_JOB_CARD'
  const employee = query.employee.trim() || 'ALL_EMPLOYEE'
  const itemCode = query.item_code.trim() || 'ALL_ITEM'
  const processName = query.process_name.trim() || 'ALL_PROCESS'
  const operationType = query.operation_type || 'ALL_OPERATION'
  return `job_card=${jobCard}; employee=${employee}; item=${itemCode}; process=${processName}; operation=${operationType}; page=${query.page}`
})

const diagnosticReadonlySummary = useWorkshopTicketDiagnosticReadonly({
  rows,
  canRead,
  currentPath: computed(() =>
    route.query.tab === 'diagnostic' ? '/workshop/tickets?tab=diagnostic' : route.path || '/workshop/tickets'
  ),
})
const { workshopTicketJobCardReadonlySummary } = useWorkshopTicketJobCardReadonly({
  rows,
  canRead,
  currentPath: jobCardReadonlyRoutePath,
  parity: jobCardReadonlyParity,
  focus: jobCardReadonlyFocus,
  queryStateLabel: jobCardReadonlyQueryStateLabel,
})
const parityHintTitle = computed<string>(() => {
  if (route.query.tab === 'job-card-readonly') {
    return '当前页面为只读验证模式（parity=workshop-ticket-job-card-readonly）'
  }
  if (route.query.tab === 'diagnostic') {
    return '当前页面为只读验证模式（parity=workshop-ticket-diagnostic）'
  }
  return '当前页面为只读验证模式（workshop-ticket readonly slices）'
})

const operationTypeLabel = (value: string): string => {
  const labels: Record<string, string> = {
    register: '登记',
    reversal: '撤销',
  }
  return labels[value] || value || '-'
}

const syncStatusLabel = (value: string): string => {
  const labels: Record<string, string> = {
    pending: '待同步',
    processing: '同步中',
    succeeded: '已同步',
    failed: '同步失败',
    dead: '死信',
    blocked_scope: '范围阻断',
  }
  return labels[value] || value || '-'
}

const guardedWriteAction = (label: string): void => {
  ElMessage.warning(`${label} 仅可在授权流程中执行，当前为只读模式`)
}

const applyGlobalReadonlyGuardToElement = (
  element: HTMLElement,
  reason: string,
  disableNative: boolean,
): void => {
  if (!element.hasAttribute(GLOBAL_READONLY_GUARD_ATTR)) {
    element.setAttribute(GLOBAL_READONLY_GUARD_ATTR, '1')
    element.setAttribute(
      GLOBAL_READONLY_PREV_DISABLED_ATTR,
      element instanceof HTMLButtonElement && element.disabled ? 'true' : 'false',
    )
    element.setAttribute(
      GLOBAL_READONLY_PREV_ARIA_DISABLED_ATTR,
      element.getAttribute('aria-disabled') ?? '',
    )
    element.setAttribute(GLOBAL_READONLY_PREV_TITLE_ATTR, element.getAttribute('title') ?? '')
    element.setAttribute(GLOBAL_READONLY_PREV_TABINDEX_ATTR, element.getAttribute('tabindex') ?? '')
  }

  if (disableNative && element instanceof HTMLButtonElement) {
    element.disabled = true
  }
  element.setAttribute('aria-disabled', 'true')
  element.setAttribute('title', reason)
  element.setAttribute('tabindex', '-1')
  element.classList.add('is-disabled')
}

const restoreGlobalReadonlyGuardElements = (): void => {
  if (typeof document === 'undefined') {
    return
  }

  document.querySelectorAll<HTMLElement>(`[${GLOBAL_READONLY_GUARD_ATTR}="1"]`).forEach((element) => {
    const prevDisabled = element.getAttribute(GLOBAL_READONLY_PREV_DISABLED_ATTR) === 'true'
    const prevAriaDisabled = element.getAttribute(GLOBAL_READONLY_PREV_ARIA_DISABLED_ATTR) ?? ''
    const prevTitle = element.getAttribute(GLOBAL_READONLY_PREV_TITLE_ATTR) ?? ''
    const prevTabIndex = element.getAttribute(GLOBAL_READONLY_PREV_TABINDEX_ATTR) ?? ''

    if (element instanceof HTMLButtonElement) {
      element.disabled = prevDisabled
    }

    if (prevAriaDisabled) {
      element.setAttribute('aria-disabled', prevAriaDisabled)
    } else {
      element.removeAttribute('aria-disabled')
    }

    if (prevTitle) {
      element.setAttribute('title', prevTitle)
    } else {
      element.removeAttribute('title')
    }

    if (prevTabIndex) {
      element.setAttribute('tabindex', prevTabIndex)
    } else {
      element.removeAttribute('tabindex')
    }

    element.classList.remove('is-disabled')
    element.removeAttribute(GLOBAL_READONLY_GUARD_ATTR)
    element.removeAttribute(GLOBAL_READONLY_PREV_DISABLED_ATTR)
    element.removeAttribute(GLOBAL_READONLY_PREV_ARIA_DISABLED_ATTR)
    element.removeAttribute(GLOBAL_READONLY_PREV_TITLE_ATTR)
    element.removeAttribute(GLOBAL_READONLY_PREV_TABINDEX_ATTR)
  })
}

const applyGlobalReadonlyActionGuards = async (): Promise<void> => {
  if (typeof document === 'undefined') {
    return
  }

  await nextTick()
  for (const guard of GLOBAL_WORKSHOP_TICKET_JOB_CARD_ACTION_GUARDS) {
    document.querySelectorAll<HTMLElement>(guard.selector).forEach((element) => {
      applyGlobalReadonlyGuardToElement(element, guard.reason, guard.disableNative)
    })
  }
}

const stopGlobalReadonlyActionGuardObserver = (): void => {
  globalWorkshopTicketListGuardObserver?.disconnect()
  globalWorkshopTicketListGuardObserver = null
}

const startGlobalReadonlyActionGuardObserver = (): void => {
  if (typeof document === 'undefined' || globalWorkshopTicketListGuardObserver) {
    return
  }

  globalWorkshopTicketListGuardObserver = new MutationObserver(() => {
    void applyGlobalReadonlyActionGuards()
  })
  globalWorkshopTicketListGuardObserver.observe(document.body, {
    childList: true,
    subtree: true,
    attributes: true,
    attributeFilter: ['class', 'disabled', 'aria-disabled', 'title', 'tabindex'],
  })
}

const loadTickets = async (): Promise<void> => {
  if (!canRead.value) {
    rows.value = []
    total.value = 0
    errorMessage.value = ''
    return
  }
  loading.value = true
  errorMessage.value = ''
  try {
    const result = await fetchWorkshopTickets(query)
    rows.value = result.data.items
    total.value = result.data.total
  } catch (error) {
    const message = (error as Error).message || '工票列表加载失败'
    errorMessage.value = message
    ElMessage.error(message)
  } finally {
    loading.value = false
  }
}

const applyPrimaryQuery = (): void => {
  query.page = 1
  loadTickets()
}

const resetPrimaryFilters = (): void => {
  query.employee = ''
  query.job_card = ''
  query.item_code = ''
  query.process_name = ''
  query.operation_type = ''
  query.from_date = ''
  query.to_date = ''
  query.page = 1
  query.page_size = 20
  loadTickets()
}

const openSummary = async (jobCard: string): Promise<void> => {
  try {
    const result = await fetchWorkshopJobCardSummary(jobCard)
    summary.value = result.data
    summaryVisible.value = true
  } catch (error) {
    ElMessage.error((error as Error).message)
  }
}

const retrySync = async (jobCard: string): Promise<void> => {
  guardedWriteAction(`重试同步（${jobCard}）`)
}

const onPageChange = (page: number): void => {
  query.page = page
  loadTickets()
}

const onSizeChange = (size: number): void => {
  query.page_size = size
  query.page = 1
  loadTickets()
}

const goRegister = (): void => {
  guardedWriteAction('工票登记')
}
const goBatch = (): void => {
  guardedWriteAction('批量导入')
}
const goDailyWage = (): void => {
  void router.push('/workshop/daily-wages')
}
const goWageRate = (): void => {
  void router.push('/workshop/wage-rates')
}

onMounted(async () => {
  try {
    await permissionStore.loadCurrentUser()
    await permissionStore.loadModuleActions('workshop')
  } catch (error) {
    ElMessage.error((error as Error).message)
  }
  await loadTickets()
  await applyGlobalReadonlyActionGuards()
  startGlobalReadonlyActionGuardObserver()
})

onBeforeUnmount(() => {
  stopGlobalReadonlyActionGuardObserver()
  restoreGlobalReadonlyGuardElements()
})
</script>

<style scoped>
.workshop-ticket-list {
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

.query-action {
  display: inline-flex;
  margin-right: 8px;
}

.error-state {
  margin-bottom: 12px;
}

.parity-hint {
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
