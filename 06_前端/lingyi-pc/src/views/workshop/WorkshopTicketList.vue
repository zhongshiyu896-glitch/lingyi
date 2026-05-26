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
        title="当前页面为只读验证模式（parity=workshop-ticket-wage）"
        class="parity-hint"
        data-testid="workshop-ticket-parity-hint"
      />

      <section
        class="cross-route-readonly"
        data-testid="workshop-ticket-wage-cross-route-guard"
        data-route-source="/workshop/tickets"
        data-reused-source="Z036-CAND-004:b5e6ce57b28ef7d2ca4d2b58502049c2b7a5ae45"
        data-readonly-boundary="true"
        data-write-request-success-allowed="false"
        data-real-write-action-added="false"
        data-guard-state="guarded_readonly"
      >
        <div class="cross-route-readonly__main">
          <strong>三路由只读一致性</strong>
          <span>工票查询 / 日薪统计 / 工价档案共享只读边界，当前来源：/workshop/tickets。</span>
        </div>
        <div class="cross-route-readonly__meta">
          <span>筛选、汇总弹层与同步重试仅做只读可见验收。</span>
          <span>复用 Z036-CAND-004 clean product path，禁止真实写请求成功。</span>
        </div>
        <div class="cross-route-readonly__guards" data-testid="workshop-ticket-wage-guarded-entry-list">
          <el-tag type="info" effect="plain">工票登记 guarded</el-tag>
          <el-tag type="info" effect="plain">批量导入 guarded</el-tag>
          <el-tag type="info" effect="plain">Job Card 同步重试 guarded</el-tag>
          <el-tag data-testid="workshop-ticket-summary-dialog" type="info" effect="plain">
            汇总弹层只读预览
          </el-tag>
          <el-tag type="info" effect="plain">日薪导出 guarded</el-tag>
          <el-tag type="info" effect="plain">生成/同步日薪 guarded</el-tag>
          <el-tag type="info" effect="plain">新增/停用工价 guarded</el-tag>
        </div>
      </section>

      <el-empty v-if="!canRead" description="无工票查看权限" data-testid="workshop-ticket-no-permission" />
      <template v-else>
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
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  fetchWorkshopJobCardSummary,
  fetchWorkshopTickets,
  type WorkshopJobCardSummaryData,
  type WorkshopTicketRow,
} from '@/api/workshop'
import { usePermissionStore } from '@/stores/permission'

const router = useRouter()
const permissionStore = usePermissionStore()
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

.cross-route-readonly {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
  padding: 12px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 6px;
  background: var(--el-fill-color-lighter);
  color: var(--el-text-color-regular);
}

.cross-route-readonly__main,
.cross-route-readonly__meta,
.cross-route-readonly__guards {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.cross-route-readonly__meta {
  color: var(--el-text-color-secondary);
  font-size: 13px;
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
