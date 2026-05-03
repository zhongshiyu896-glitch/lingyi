<template>
  <div class="style-profit-list-page">
    <el-card shadow="never">
      <template #header>
        <div class="header-row">
          <div class="title-group">
            <span class="page-title">财务管理 / 成品销售利润明细表</span>
            <span class="page-subtitle">按加工厂、款号与业务单据查询利润快照</span>
          </div>
        </div>
      </template>

      <el-form :inline="true" :model="query" class="query-form">
        <el-form-item label="加工厂">
          <el-input v-model="query.company" clearable placeholder="请输入" />
        </el-form-item>
        <el-form-item label="款号/款名">
          <el-input v-model="query.item_code" clearable placeholder="请输入" />
        </el-form-item>
        <el-form-item label="业务单据">
          <el-input v-model="query.sales_order" clearable placeholder="请输入" />
        </el-form-item>
        <el-form-item label="开始日期">
          <el-date-picker
            v-model="query.from_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="开始日期"
            clearable
          />
        </el-form-item>
        <el-form-item label="结束日期">
          <el-date-picker
            v-model="query.to_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="结束日期"
            clearable
          />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.snapshot_status" clearable placeholder="全部状态" style="width: 140px">
            <el-option label="已完成" value="complete" />
            <el-option label="待复核" value="incomplete" />
          </el-select>
        </el-form-item>

        <el-form-item class="button-group">
          <el-button type="primary" :disabled="!canRead || loading" @click="loadRows">查询</el-button>
          <el-button :disabled="!canRead || loading" @click="resetQuery">重置</el-button>
          <el-button :disabled="!canRead || loading" @click="loadRows">搜索</el-button>
          <el-button :disabled="!canRead || loading" @click="guardedAction('清空')">清空</el-button>
          <el-button :disabled="!canRead || loading" @click="guardedAction('确定')">确定</el-button>
          <el-button :disabled="!canRead || loading" @click="guardedAction('导出')">导出</el-button>
          <el-button :disabled="!canRead || loading" @click="guardedAction('列设置')">列设置</el-button>
          <el-button :disabled="!canRead || loading" @click="guardedAction('重置列')">重置列</el-button>
          <el-button :disabled="!canRead || loading" @click="guardedAction('标志已读')">标志已读</el-button>
          <el-button :disabled="!canRead || loading" @click="guardedAction('删除消息')">删除消息</el-button>
          <el-button :disabled="!canRead || loading" @click="guardedAction('新增消息')">新增消息</el-button>
          <el-button :disabled="!canRead || loading" @click="guardedAction('保存')">保存</el-button>
          <el-button :disabled="!canRead || loading" @click="guardedAction('取消')">取消</el-button>
        </el-form-item>
      </el-form>

      <el-empty v-if="!canRead" description="无款式利润查看权限" />
      <template v-else>
        <el-alert
          v-if="errorMessage"
          type="error"
          :closable="false"
          show-icon
          :title="`成品销售利润明细表数据加载失败：${errorMessage}`"
          class="error-alert"
        />
        <el-table :data="rows" border v-loading="loading" empty-text="暂无成品销售利润明细数据，请调整筛选条件后重试">
          <el-table-column prop="company" label="加工厂" min-width="120" />
          <el-table-column label="加工厂全称" min-width="150">
            <template #default="scope">{{ scope.row.company_full_name || scope.row.company || '-' }}</template>
          </el-table-column>
          <el-table-column label="业务单据" min-width="170">
            <template #default="scope">{{ scope.row.sales_order || scope.row.snapshot_no }}</template>
          </el-table-column>
          <el-table-column label="业务日期" min-width="120">
            <template #default="scope">{{ scope.row.from_date || '-' }}</template>
          </el-table-column>
          <el-table-column prop="revenue_status" label="业务类型" min-width="100" />
          <el-table-column label="应付金额" width="130">
            <template #default="scope">{{ formatAmount(scope.row.actual_total_cost) }}</template>
          </el-table-column>
          <el-table-column label="实付金额" width="130">
            <template #default="scope">{{ formatAmount(scope.row.standard_total_cost) }}</template>
          </el-table-column>
          <el-table-column label="应收金额" width="130">
            <template #default="scope">{{ formatAmount(scope.row.revenue_amount) }}</template>
          </el-table-column>
          <el-table-column label="未付金额" width="130">
            <template #default="scope">{{ formatAmount(scope.row.profit_amount) }}</template>
          </el-table-column>
          <el-table-column label="利润率" width="110">
            <template #default="scope">{{ formatProfitRate(scope.row.profit_rate) }}</template>
          </el-table-column>
          <el-table-column label="备注" min-width="180">
            <template #default="scope">
              <span>分摊状态：{{ scope.row.allocation_status || '-' }}</span>
              <span v-if="scope.row.unresolved_count > 0" class="warn-text">；未解析 {{ scope.row.unresolved_count }}</span>
            </template>
          </el-table-column>
          <el-table-column v-for="week in weekColumns" :key="week" :label="week" width="60">
            <template #default>-</template>
          </el-table-column>
          <el-table-column label="标题" min-width="170">
            <template #default="scope">{{ scope.row.snapshot_no }}</template>
          </el-table-column>
          <el-table-column prop="created_at" label="发送时间" min-width="180" />
          <el-table-column label="状态" min-width="120">
            <template #default="scope">
              <el-tag :type="statusTagType(scope.row.snapshot_status)">
                {{ statusText(scope.row.snapshot_status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="发送人" min-width="110">
            <template #default="scope">{{ scope.row.created_by || '-' }}</template>
          </el-table-column>
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
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { fetchStyleProfitSnapshots, type StyleProfitSnapshotListItem } from '@/api/style_profit'
import { usePermissionStore } from '@/stores/permission'

const router = useRouter()
const permissionStore = usePermissionStore()
const loading = ref<boolean>(false)
const rows = ref<StyleProfitSnapshotListItem[]>([])
const total = ref<number>(0)
const errorMessage = ref<string>('')
const weekColumns = ['日', '一', '二', '三', '四', '五', '六']

const canRead = computed<boolean>(() => permissionStore.state.buttonPermissions.read)

const query = reactive({
  company: '',
  item_code: '',
  sales_order: '',
  from_date: '',
  to_date: '',
  snapshot_status: '',
  page: 1,
  page_size: 20,
})

const formatAmount = (value: string | number | null | undefined): string => {
  if (value === null || value === undefined || value === '') {
    return '-'
  }
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric.toFixed(2) : String(value)
}

const formatProfitRate = (value: string | number | null | undefined): string => {
  if (value === null || value === undefined || value === '') {
    return '-'
  }
  const numeric = Number(value)
  return Number.isFinite(numeric) ? `${(numeric * 100).toFixed(2)}%` : String(value)
}

const statusText = (status: string | null | undefined): string => {
  if (status === 'complete') return '已完成'
  if (status === 'incomplete') return '待复核'
  return status || '-'
}

const statusTagType = (status: string | null | undefined): 'success' | 'warning' | 'info' => {
  if (status === 'complete') return 'success'
  if (status === 'incomplete') return 'warning'
  return 'info'
}

const hasRequiredScope = (): boolean => {
  return Boolean(query.company.trim()) && Boolean(query.item_code.trim())
}

const resetRows = (): void => {
  rows.value = []
  total.value = 0
}

const resetQuery = (): void => {
  query.company = ''
  query.item_code = ''
  query.sales_order = ''
  query.from_date = ''
  query.to_date = ''
  query.snapshot_status = ''
  query.page = 1
  query.page_size = 20
  errorMessage.value = ''
  resetRows()
}

const guardedAction = (action: string): void => {
  ElMessage.info(`${action}仅保留展示入口，当前为本地只读验证模式`)
}

const loadRows = async (): Promise<void> => {
  if (!canRead.value) {
    resetRows()
    errorMessage.value = ''
    return
  }
  if (!hasRequiredScope()) {
    ElMessage.warning('请先输入加工厂与款号/款名后再查询')
    resetRows()
    errorMessage.value = ''
    return
  }

  errorMessage.value = ''
  loading.value = true
  try {
    const result = await fetchStyleProfitSnapshots({
      company: query.company.trim(),
      item_code: query.item_code.trim(),
      sales_order: query.sales_order.trim() || undefined,
      from_date: query.from_date || undefined,
      to_date: query.to_date || undefined,
      snapshot_status: query.snapshot_status || undefined,
      page: query.page,
      page_size: query.page_size,
    })
    rows.value = result.data.items
    total.value = result.data.total
  } catch (error) {
    const message = (error as Error).message || '未知错误'
    errorMessage.value = message
    ElMessage.error(message)
    resetRows()
  } finally {
    loading.value = false
  }
}

const goDetail = (snapshotId: number): void => {
  router.push({ path: '/reports/style-profit/detail', query: { id: String(snapshotId) } })
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
    await permissionStore.loadModuleActions('style_profit')
  } catch (error) {
    ElMessage.error((error as Error).message)
    return
  }
  if (canRead.value && hasRequiredScope()) {
    await loadRows()
  }
})
</script>

<style scoped>
.style-profit-list-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.header-row {
  display: flex;
  justify-content: flex-start;
  align-items: center;
}

.title-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.page-title {
  font-weight: 600;
}

.page-subtitle {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.query-form {
  margin-bottom: 12px;
}

.button-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.error-alert {
  margin-bottom: 12px;
}

.pager {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}

.warn-text {
  color: var(--el-color-danger);
}
</style>
