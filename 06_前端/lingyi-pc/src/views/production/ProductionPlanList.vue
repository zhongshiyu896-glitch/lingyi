<template>
  <div class="production-followup-page">
    <el-card shadow="never">
      <template #header>
        <div class="header-row">
          <div class="title-group">
            <span class="title">大货跟进</span>
            <span class="sub-title">大货管理 / 大货跟进</span>
          </div>
          <el-tag type="info" effect="plain">本地首版</el-tag>
        </div>
      </template>

      <el-form :inline="true" :model="query" class="query-form">
        <el-form-item label="订单">
          <el-input
            v-model="query.sales_order"
            clearable
            placeholder="订单"
            @keyup.enter="onSearch"
          />
        </el-form-item>
        <el-form-item label="款号/款名">
          <el-input
            v-model="query.keyword"
            clearable
            placeholder="请输入"
            @keyup.enter="onSearch"
          />
        </el-form-item>
        <el-form-item label="翻单号">
          <el-input
            v-model="query.turnover_no"
            clearable
            placeholder="翻单号"
            @keyup.enter="onSearch"
          />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.status" clearable placeholder="全部状态" style="width: 160px">
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
        <el-form-item label="开始时间">
          <el-date-picker
            v-model="query.from_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="开始时间"
            clearable
          />
        </el-form-item>
        <el-form-item label="结束时间">
          <el-date-picker
            v-model="query.to_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="结束时间"
            clearable
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :disabled="!canRead" @click="onSearch">搜索</el-button>
          <el-button :disabled="!canRead" @click="onReset">重置</el-button>
        </el-form-item>
      </el-form>

      <div class="toolbar-row">
        <el-button :disabled="!canRead" @click="onSearch">筛选</el-button>
        <el-button :disabled="!canRead" @click="onClearFilters">清空</el-button>
        <el-button :disabled="!canWriteGuarded" data-action-type="write" @click="onGuardedAction('确定', true)">确定</el-button>
        <el-button :disabled="!canWriteGuarded" data-action-type="write" @click="onGuardedAction('标志已读', true)">标志已读</el-button>
        <el-button :disabled="!canWriteGuarded" data-action-type="write" @click="onGuardedAction('删除消息', true)">删除消息</el-button>
        <el-button :disabled="!canWriteGuarded" data-action-type="write" @click="onGuardedAction('新增消息', true)">新增消息</el-button>
        <el-button :disabled="!canWriteGuarded" data-action-type="write" @click="onGuardedAction('保存', true)">保存</el-button>
      </div>

      <el-alert
        v-if="lastError"
        class="error-alert"
        type="error"
        :closable="false"
        :title="`大货跟进数据加载失败：${lastError}`"
      />

      <el-empty v-if="!canRead" description="无大货跟进查看权限" />
      <template v-else>
        <el-table
          :data="rows"
          border
          v-loading="loading"
          empty-text="暂无大货跟进数据，请调整筛选条件后重试"
        >
          <el-table-column label="订单信息" min-width="260">
            <template #default="scope">
              <div class="cell-stack">
                <span class="primary-text">{{ scope.row.sales_order }}</span>
                <span class="secondary-text">款号：{{ scope.row.item_code || '-' }}</span>
                <span class="secondary-text">翻单号：{{ scope.row.sales_order_item || '-' }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="plan_no" label="生产制单" min-width="160" />
          <el-table-column label="客户信息" min-width="180">
            <template #default="scope">
              <div class="cell-stack">
                <span class="primary-text">{{ scope.row.customer || '-' }}</span>
                <span class="secondary-text">单位：{{ scope.row.company || '-' }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="预计出货" min-width="120">
            <template #default="scope">{{ scope.row.planned_start_date || '-' }}</template>
          </el-table-column>
          <el-table-column label="面辅包进度" min-width="120">
            <template #default="scope">{{ materialProgressLabel(scope.row.status) }}</template>
          </el-table-column>
          <el-table-column label="生产排期" min-width="180">
            <template #default="scope">{{ scheduleText(scope.row) }}</template>
          </el-table-column>
          <el-table-column label="工厂进度" min-width="120">
            <template #default="scope">
              <el-tag :type="statusTagType(scope.row.status)" effect="plain">
                {{ statusLabel(scope.row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="入库数" min-width="100">
            <template #default>-</template>
          </el-table-column>
          <el-table-column label="出库数" min-width="100">
            <template #default>-</template>
          </el-table-column>
          <el-table-column label="操作" fixed="right" min-width="110">
            <template #default="scope">
              <el-button link type="primary" @click="goDetail(scope.row.id)">跟进</el-button>
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
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { fetchProductionPlans, type ProductionPlanListItem } from '@/api/production'
import { usePermissionStore } from '@/stores/permission'

const router = useRouter()
const permissionStore = usePermissionStore()

const loading = ref<boolean>(false)
const rows = ref<ProductionPlanListItem[]>([])
const total = ref<number>(0)
const lastError = ref<string>('')

const canRead = computed<boolean>(() => {
  return permissionStore.state.buttonPermissions.read || permissionStore.state.actions.includes('production:read')
})
const canWriteGuarded = computed<boolean>(() => {
  return permissionStore.state.buttonPermissions.plan_create || permissionStore.state.actions.includes('production:plan_create')
})

const query = reactive({
  sales_order: '',
  keyword: '',
  turnover_no: '',
  from_date: '',
  to_date: '',
  status: '',
  page: 1,
  page_size: 20,
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
  }
  return labels[value] || value || '-'
}

const statusTagType = (value: string): 'success' | 'warning' | 'danger' | 'info' => {
  if (value === 'job_cards_synced' || value === 'work_order_created') return 'success'
  if (value === 'failed' || value === 'cancelled') return 'danger'
  if (value === 'material_checked' || value === 'work_order_pending') return 'warning'
  return 'info'
}

const materialProgressLabel = (status: string): string => {
  if (status === 'job_cards_synced' || status === 'work_order_created') return '已完成'
  if (status === 'material_checked' || status === 'work_order_pending') return '已检查'
  if (status === 'failed') return '异常待处理'
  return '待检查'
}

const scheduleText = (row: ProductionPlanListItem): string => {
  const qty = row.planned_qty ? String(row.planned_qty) : '-'
  const date = row.planned_start_date || '-'
  return `计划数 ${qty} / 开工 ${date}`
}

const resetRows = (): void => {
  rows.value = []
  total.value = 0
}

const validateDateRange = (): boolean => {
  if (!query.from_date || !query.to_date) return true
  if (query.from_date <= query.to_date) return true
  ElMessage.error('开始时间不能晚于结束时间')
  return false
}

const loadRows = async (): Promise<void> => {
  if (!canRead.value) {
    resetRows()
    lastError.value = ''
    return
  }

  loading.value = true
  lastError.value = ''
  try {
    const result = await fetchProductionPlans({
      sales_order: query.sales_order.trim() || undefined,
      keyword: query.keyword.trim() || undefined,
      turnover_no: query.turnover_no.trim() || undefined,
      from_date: query.from_date || undefined,
      to_date: query.to_date || undefined,
      status: query.status || undefined,
      page: query.page,
      page_size: query.page_size,
    })
    rows.value = result.data.items
    total.value = result.data.total
  } catch (error) {
    const message = (error as Error).message
    lastError.value = message
    resetRows()
    ElMessage.error(message)
  } finally {
    loading.value = false
  }
}

const onSearch = (): void => {
  if (!validateDateRange()) return
  query.page = 1
  void loadRows()
}

const onReset = (): void => {
  query.sales_order = ''
  query.keyword = ''
  query.turnover_no = ''
  query.from_date = ''
  query.to_date = ''
  query.status = ''
  query.page = 1
  query.page_size = 20
  void loadRows()
}

const onClearFilters = (): void => {
  query.sales_order = ''
  query.keyword = ''
  query.turnover_no = ''
  query.from_date = ''
  query.to_date = ''
  query.status = ''
}

const onGuardedAction = (actionName: string, isWrite: boolean): void => {
  if (isWrite && !canWriteGuarded.value) {
    ElMessage.warning(`无 ${actionName} 权限，当前保持禁用态`)
    return
  }
  if (isWrite) {
    ElMessage.warning(`${actionName}仅保留按钮对齐，当前本地首版未开放写入`)
    return
  }
  ElMessage.info(`${actionName}已保留入口，当前本地首版暂不执行`)
}

const goDetail = (planId: number): void => {
  router.push({ path: '/production/plans/detail', query: { id: String(planId) } })
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

onMounted(async () => {
  try {
    await permissionStore.loadCurrentUser()
    await permissionStore.loadModuleActions('production')
  } catch (error) {
    const message = (error as Error).message
    lastError.value = message
    ElMessage.error(message)
    return
  }
  if (canRead.value) {
    await loadRows()
  }
})
</script>

<style scoped>
.production-followup-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.title-group {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.title {
  font-size: 16px;
  font-weight: 600;
}

.sub-title {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.query-form {
  margin-bottom: 8px;
}

.toolbar-row {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.error-alert {
  margin-bottom: 12px;
}

.cell-stack {
  display: flex;
  flex-direction: column;
  line-height: 1.4;
}

.primary-text {
  font-weight: 500;
}

.secondary-text {
  color: var(--el-text-color-secondary);
}

.pager {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}
</style>
