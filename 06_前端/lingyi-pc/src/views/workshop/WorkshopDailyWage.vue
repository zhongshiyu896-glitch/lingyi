<template>
  <div class="workshop-daily-wage" data-testid="workshop-daily-wage-page">
    <el-card shadow="never" data-testid="workshop-daily-wage-main-section">
      <template #header>
        <div class="header-row">
          <span>员工日薪统计</span>
          <el-button
            data-testid="workshop-daily-wage-back-to-ticket-list"
            data-action-type="navigation"
            data-readonly-action="true"
            data-route-path="/workshop/tickets"
            @click="goList"
          >
            返回工票列表
          </el-button>
        </div>
      </template>

      <el-form :inline="true" :model="query" data-testid="workshop-daily-wage-filter-form">
        <el-form-item label="员工">
          <div data-testid="workshop-daily-wage-filter-employee">
            <el-input v-model="query.employee" clearable placeholder="Employee" />
          </div>
        </el-form-item>
        <el-form-item label="工序">
          <div data-testid="workshop-daily-wage-filter-process-name">
            <el-input v-model="query.process_name" clearable placeholder="Process" />
          </div>
        </el-form-item>
        <el-form-item label="款式">
          <div data-testid="workshop-daily-wage-filter-item-code">
            <el-input v-model="query.item_code" clearable placeholder="Item Code" />
          </div>
        </el-form-item>
        <el-form-item label="日期从">
          <div data-testid="workshop-daily-wage-filter-from-date">
            <el-date-picker
              v-model="query.from_date"
              type="date"
              value-format="YYYY-MM-DD"
              placeholder="选择开始日期"
              aria-label="日薪开始日期"
            />
          </div>
        </el-form-item>
        <el-form-item label="到">
          <div data-testid="workshop-daily-wage-filter-to-date">
            <el-date-picker
              v-model="query.to_date"
              type="date"
              value-format="YYYY-MM-DD"
              placeholder="选择结束日期"
              aria-label="日薪结束日期"
            />
          </div>
        </el-form-item>
        <el-form-item label="操作">
          <div class="query-action" data-testid="workshop-daily-wage-query-btn">
            <el-button type="primary" :disabled="!canRead" @click="applyPrimaryQuery">查询</el-button>
          </div>
          <div class="query-action" data-testid="workshop-daily-wage-reset-btn">
            <el-button :disabled="!canRead" @click="resetPrimaryFilters">重置</el-button>
          </div>
        </el-form-item>
      </el-form>

      <el-alert
        style="margin-bottom: 12px"
        type="info"
        :closable="false"
        show-icon
        title="当前页面为只读验证模式（parity=workshop-ticket-wage）"
        data-testid="workshop-daily-wage-parity-hint"
      />

      <section
        class="cross-route-readonly"
        data-testid="workshop-ticket-wage-cross-route-guard"
        data-route-source="/workshop/daily-wages"
        data-reused-source="Z036-CAND-004:b5e6ce57b28ef7d2ca4d2b58502049c2b7a5ae45"
        data-readonly-boundary="true"
        data-write-request-success-allowed="false"
        data-real-write-action-added="false"
        data-guard-state="guarded_readonly"
      >
        <div class="cross-route-readonly__main">
          <strong>三路由只读一致性</strong>
          <span>工票查询 / 日薪统计 / 工价档案共享只读边界，当前来源：/workshop/daily-wages。</span>
        </div>
        <div class="cross-route-readonly__meta">
          <span>日薪筛选、合计与导出/生成/同步入口仅做只读可见验收。</span>
          <span>复用 Z036-CAND-004 clean product path，禁止真实写请求成功。</span>
        </div>
        <div class="cross-route-readonly__guards" data-testid="workshop-ticket-wage-guarded-entry-list">
          <el-tag type="info" effect="plain">工票登记 guarded</el-tag>
          <el-tag type="info" effect="plain">批量导入 guarded</el-tag>
          <el-tag type="info" effect="plain">Job Card 同步重试 guarded</el-tag>
          <el-tag data-testid="workshop-daily-wage-guarded-actions" type="info" effect="plain">
            日薪导出 guarded
          </el-tag>
          <el-tag type="info" effect="plain">生成/同步日薪 guarded</el-tag>
          <el-tag type="info" effect="plain">新增/停用工价 guarded</el-tag>
        </div>
      </section>

      <el-skeleton v-if="!permissionReady" :rows="4" animated />
      <el-empty
        v-else-if="!canRead"
        description="无日薪查看权限"
        data-testid="workshop-daily-wage-no-permission"
      />
      <template v-else>
        <el-alert
          v-if="errorMessage"
          style="margin-bottom: 12px"
          type="error"
          :closable="false"
          show-icon
          :title="errorMessage"
          data-testid="workshop-daily-wage-error-state"
        />
        <el-alert
          style="margin-bottom: 12px"
          type="success"
          :closable="false"
          show-icon
          :title="`当前查询工资合计：${totalAmount}`"
          data-testid="workshop-daily-wage-total-amount"
        />
        <div class="guarded-actions" data-testid="workshop-daily-wage-guarded-actions">
          <span
            hidden
            data-testid="workshop-write-guard"
            data-guard-state="guarded_readonly"
            data-write-guard="readonly:workshop-daily-wage-actions"
          />
          <el-button
            data-action-type="write"
            data-write-guard="readonly:workshop-daily-wage-export"
            data-guard-state="guarded_readonly"
            @click="guardedWriteAction('导出日薪')"
          >
            导出
          </el-button>
          <el-button
            data-action-type="write"
            data-write-guard="readonly:workshop-daily-wage-generate"
            data-guard-state="guarded_readonly"
            @click="guardedWriteAction('生成日薪')"
          >
            生成
          </el-button>
          <el-button
            data-action-type="write"
            data-write-guard="readonly:workshop-daily-wage-sync"
            data-guard-state="guarded_readonly"
            @click="guardedWriteAction('同步日薪')"
          >
            同步
          </el-button>
        </div>

        <div data-testid="workshop-daily-wage-table">
          <el-table :data="rows" v-loading="loading" border empty-text="暂无日薪统计记录">
            <el-table-column prop="employee" label="员工" min-width="120" />
            <el-table-column prop="work_date" label="日期" min-width="120" />
            <el-table-column prop="process_name" label="工序" min-width="120" />
            <el-table-column prop="item_code" label="款式" min-width="120" />
            <el-table-column prop="register_qty" label="登记数量" min-width="110" />
            <el-table-column prop="reversal_qty" label="撤销数量" min-width="110" />
            <el-table-column prop="net_qty" label="净数量" min-width="110" />
            <el-table-column prop="wage_amount" label="工资金额" min-width="120" />
          </el-table>
        </div>

        <el-empty
          v-if="!loading && !errorMessage && rows.length === 0"
          description="暂无日薪统计记录"
          class="empty-state"
          data-testid="workshop-daily-wage-empty-state"
        />

        <div class="pager" data-testid="workshop-daily-wage-pagination">
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
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { fetchWorkshopDailyWages, type WorkshopDailyWageRow } from '@/api/workshop'
import { usePermissionStore } from '@/stores/permission'

const router = useRouter()
const permissionStore = usePermissionStore()
const loading = ref<boolean>(false)
const permissionReady = ref<boolean>(false)
const rows = ref<WorkshopDailyWageRow[]>([])
const total = ref<number>(0)
const totalAmount = ref<string | number>('0')
const errorMessage = ref<string>('')

const query = reactive({
  employee: '',
  from_date: '',
  to_date: '',
  process_name: '',
  item_code: '',
  page: 1,
  page_size: 20,
})

const canRead = computed<boolean>(() => permissionStore.state.buttonPermissions.wage_read)

const guardedWriteAction = (label: string): void => {
  ElMessage.warning(`${label} 仅可在授权流程中执行，当前为只读模式`)
}

const loadRows = async (): Promise<void> => {
  if (!canRead.value) {
    rows.value = []
    total.value = 0
    totalAmount.value = '0'
    errorMessage.value = ''
    return
  }
  loading.value = true
  errorMessage.value = ''
  try {
    const result = await fetchWorkshopDailyWages(query)
    rows.value = result.data.items
    total.value = result.data.total
    totalAmount.value = result.data.total_amount
  } catch (error) {
    const message = (error as Error).message || '日薪统计加载失败'
    errorMessage.value = message
    ElMessage.error(message)
  } finally {
    loading.value = false
  }
}

const applyPrimaryQuery = (): void => {
  query.page = 1
  loadRows()
}

const resetPrimaryFilters = (): void => {
  query.employee = ''
  query.process_name = ''
  query.item_code = ''
  query.from_date = ''
  query.to_date = ''
  query.page = 1
  query.page_size = 20
  loadRows()
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

const goList = (): void => {
  void router.push('/workshop/tickets')
}

onMounted(async () => {
  try {
    await permissionStore.loadCurrentUser()
    await permissionStore.loadModuleActions('workshop')
  } catch (error) {
    ElMessage.warning((error as Error).message)
  } finally {
    permissionReady.value = true
  }
  await loadRows()
})
</script>

<style scoped>
.workshop-daily-wage {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.query-action {
  display: inline-flex;
  margin-right: 8px;
}

.guarded-actions {
  display: flex;
  gap: 8px;
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
