<template>
  <div class="workshop-ticket-list">
    <el-card shadow="never">
      <template #header>
        <div class="header-row">
          <span>车间工票查询</span>
          <div class="header-actions">
            <el-button
              v-if="canRegister"
              type="primary"
              data-action-type="write"
              data-write-guard="permission:ticket_register(v-if)+handler"
              data-guard-state="visible_when_allowed"
              @click="goRegister"
            >
              工票登记
            </el-button>
            <el-button
              v-if="canBatch"
              data-action-type="write"
              data-write-guard="permission:ticket_batch(v-if)+handler"
              data-guard-state="visible_when_allowed"
              @click="goBatch"
            >
              批量导入
            </el-button>
            <el-button v-if="canWageRead" @click="goDailyWage">日薪统计</el-button>
            <el-button v-if="canWageRateRead" @click="goWageRate">工价档案</el-button>
          </div>
        </div>
      </template>

      <el-form :inline="true" :model="query">
        <el-form-item label="员工">
          <el-input v-model="query.employee" clearable placeholder="Employee" />
        </el-form-item>
        <el-form-item label="工序卡">
          <el-input v-model="query.job_card" clearable placeholder="Job Card" />
        </el-form-item>
        <el-form-item label="款式">
          <el-input v-model="query.item_code" clearable placeholder="Item Code" />
        </el-form-item>
        <el-form-item label="工序">
          <el-input v-model="query.process_name" clearable placeholder="Process" />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="query.operation_type" clearable style="width: 140px">
            <el-option label="登记" value="register" />
            <el-option label="撤销" value="reversal" />
          </el-select>
        </el-form-item>
        <el-form-item label="日期从">
          <el-date-picker v-model="query.from_date" value-format="YYYY-MM-DD" type="date" />
        </el-form-item>
        <el-form-item label="到">
          <el-date-picker v-model="query.to_date" value-format="YYYY-MM-DD" type="date" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :disabled="!canRead" @click="loadTickets">查询</el-button>
        </el-form-item>
      </el-form>

      <el-empty v-if="!canRead" description="无工票查看权限" />
      <template v-else>
        <el-table :data="rows" v-loading="loading" border>
          <el-table-column prop="ticket_no" label="工票号" min-width="180" />
          <el-table-column prop="job_card" label="工序卡" min-width="120" />
          <el-table-column prop="employee" label="员工" min-width="120" />
          <el-table-column prop="item_code" label="款式" min-width="120" />
          <el-table-column prop="process_name" label="工序" min-width="120" />
          <el-table-column prop="operation_type" label="类型" width="100" />
          <el-table-column prop="qty" label="数量" width="110" />
          <el-table-column prop="unit_wage" label="单价" width="110" />
          <el-table-column prop="wage_amount" label="工资" width="110" />
          <el-table-column prop="sync_status" label="同步状态" width="110" />
          <el-table-column label="操作" width="220" fixed="right">
            <template #default="scope">
              <el-button link type="primary" @click="openSummary(scope.row.job_card)">汇总</el-button>
              <el-button
                v-if="canSync"
                link
                type="success"
                :disabled="syncingJobCard === scope.row.job_card"
                @click="retrySync(scope.row.job_card)"
              >
                重试同步
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

    <el-dialog v-model="summaryVisible" title="Job Card 汇总" width="520px">
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
  retryWorkshopJobCardSync,
  type WorkshopJobCardSummaryData,
  type WorkshopTicketRow,
} from '@/api/workshop'
import { usePermissionStore } from '@/stores/permission'

const router = useRouter()
const permissionStore = usePermissionStore()
const loading = ref<boolean>(false)
const rows = ref<WorkshopTicketRow[]>([])
const total = ref<number>(0)
const summaryVisible = ref<boolean>(false)
const summary = ref<WorkshopJobCardSummaryData | null>(null)
const syncingJobCard = ref<string>('')

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

const loadTickets = async (): Promise<void> => {
  if (!canRead.value) {
    rows.value = []
    total.value = 0
    return
  }
  loading.value = true
  try {
    const result = await fetchWorkshopTickets(query)
    rows.value = result.data.items
    total.value = result.data.total
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    loading.value = false
  }
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
  syncingJobCard.value = jobCard
  try {
    await retryWorkshopJobCardSync(jobCard)
    ElMessage.success('同步重试已提交')
    await loadTickets()
    if (summaryVisible.value && summary.value?.job_card === jobCard) {
      await openSummary(jobCard)
    }
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    syncingJobCard.value = ''
  }
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
  if (!canRegister.value) {
    ElMessage.warning('无工票登记权限')
    return
  }
  void router.push('/workshop/tickets/register')
}
const goBatch = (): void => {
  if (!canBatch.value) {
    ElMessage.warning('无工票批量导入权限')
    return
  }
  void router.push('/workshop/tickets/batch')
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

.pager {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}
</style>
