<template>
  <div class="style-profit-list-page" data-testid="style-profit-page">
    <el-card shadow="never" data-testid="style-profit-main-section">
      <template #header>
        <div class="header-row">
          <div class="title-group">
            <span class="page-title">大货管理 / 订单款式利润预测明细表</span>
            <span class="page-subtitle">按款式、品牌与时间范围查看销售预测、成本预测与利润预测明细</span>
          </div>
        </div>
      </template>

      <el-form :inline="true" :model="query" class="query-form" data-testid="style-profit-query-form">
        <el-form-item label="款式">
          <el-input v-model="query.item_code" clearable placeholder="款式" data-testid="style-profit-filter-item-code" />
        </el-form-item>
        <el-form-item label="品牌">
          <el-input v-model="query.company" clearable placeholder="请输入" data-testid="style-profit-filter-company" />
        </el-form-item>
        <el-form-item label="关键词">
          <el-input v-model="query.sales_order" clearable placeholder="请输入" data-testid="style-profit-filter-sales-order" />
        </el-form-item>
        <el-form-item label="开始时间">
          <el-date-picker
            v-model="query.from_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="开始时间"
            clearable
            data-testid="style-profit-filter-from-date"
          />
        </el-form-item>
        <el-form-item label="结束时间">
          <el-date-picker
            v-model="query.to_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="结束时间"
            clearable
            data-testid="style-profit-filter-to-date"
          />
        </el-form-item>
        <el-form-item label="状态">
          <el-select
            v-model="query.snapshot_status"
            clearable
            placeholder="全部状态"
            style="width: 140px"
            data-testid="style-profit-filter-status"
          >
            <el-option label="已完成" value="complete" />
            <el-option label="待复核" value="incomplete" />
          </el-select>
        </el-form-item>

        <el-form-item class="button-group">
          <el-button type="primary" :disabled="!canRead || loading" data-testid="style-profit-filter-button" @click="loadRows">筛选</el-button>
          <el-button :disabled="!canRead || loading" data-testid="style-profit-reset-button" @click="resetQuery">重置</el-button>
          <el-button :disabled="!canRead || loading" data-testid="style-profit-search-button" @click="loadRows">搜索</el-button>
          <el-button :disabled="!canRead || loading" data-testid="style-profit-guarded-clear" @click="guardedAction('清空')">清空</el-button>
          <el-button :disabled="!canRead || loading" data-testid="style-profit-guarded-confirm" @click="guardedAction('确定')">确定</el-button>
          <el-button :disabled="!canRead || loading" data-testid="style-profit-guarded-export" @click="guardedAction('导出')">导出</el-button>
          <el-button :disabled="!canRead || loading" data-testid="style-profit-guarded-column-setting" @click="guardedAction('列设置')">列设置</el-button>
          <el-button :disabled="!canRead || loading" data-testid="style-profit-guarded-reset-column" @click="guardedAction('重置列')">重置列</el-button>
          <el-button :disabled="!canRead || loading" data-testid="style-profit-guarded-mark-read" @click="guardedAction('标志已读')">标志已读</el-button>
          <el-button :disabled="!canRead || loading" data-testid="style-profit-guarded-delete-msg" @click="guardedAction('删除消息')">删除消息</el-button>
          <el-button :disabled="!canRead || loading" data-testid="style-profit-guarded-add-msg" @click="guardedAction('新增消息')">新增消息</el-button>
          <el-button :disabled="!canRead || loading" data-testid="style-profit-guarded-save" @click="guardedAction('保存')">保存</el-button>
          <el-button :disabled="!canRead || loading" data-testid="style-profit-guarded-cancel" @click="guardedAction('取消')">取消</el-button>
        </el-form-item>
      </el-form>

      <el-empty v-if="!canRead" description="无款式利润查看权限" data-testid="style-profit-no-permission" />
      <template v-else>
        <el-alert
          v-if="errorMessage"
          type="error"
          :closable="false"
          show-icon
          :title="`订单款式利润预测明细表数据加载失败：${errorMessage}`"
          class="error-alert"
          data-testid="style-profit-error-alert"
        />
        <div class="summary-grid" v-if="rows.length > 0" data-testid="style-profit-summary-grid">
          <el-card shadow="never" class="summary-card" data-testid="style-profit-summary-revenue">
            <div class="summary-label">销售预测金额</div>
            <div class="summary-value">{{ formatAmount(totalRevenueAmount) }}</div>
          </el-card>
          <el-card shadow="never" class="summary-card" data-testid="style-profit-summary-cost">
            <div class="summary-label">成本预测金额</div>
            <div class="summary-value">{{ formatAmount(totalCostAmount) }}</div>
          </el-card>
          <el-card shadow="never" class="summary-card" data-testid="style-profit-summary-profit">
            <div class="summary-label">利润预测金额</div>
            <div class="summary-value">{{ formatAmount(totalProfitAmount) }}</div>
          </el-card>
          <el-card shadow="never" class="summary-card" data-testid="style-profit-summary-rate">
            <div class="summary-label">平均利润率</div>
            <div class="summary-value">{{ formatProfitRate(avgProfitRate) }}</div>
          </el-card>
        </div>
        <el-table
          :data="rows"
          border
          v-loading="loading"
          empty-text="暂无订单款式利润预测明细数据，请调整筛选条件后重试"
          data-testid="style-profit-main-table"
        >
          <el-table-column label="图片" width="80">
            <template #default>-</template>
          </el-table-column>
          <el-table-column prop="item_code" label="款号" min-width="130" />
          <el-table-column label="款式名称" min-width="140">
            <template #default="scope">{{ scope.row.item_code || '-' }}</template>
          </el-table-column>
          <el-table-column label="设计号" min-width="130">
            <template #default="scope">{{ scope.row.sales_order || '-' }}</template>
          </el-table-column>
          <el-table-column prop="company" label="品牌" min-width="120" />
          <el-table-column label="款式类型" min-width="110">
            <template #default>-</template>
          </el-table-column>
          <el-table-column label="年份" width="90">
            <template #default>-</template>
          </el-table-column>
          <el-table-column label="设计师" min-width="110">
            <template #default>-</template>
          </el-table-column>
          <el-table-column label="纸样师" min-width="110">
            <template #default>-</template>
          </el-table-column>
          <el-table-column label="车板师" min-width="110">
            <template #default>-</template>
          </el-table-column>
          <el-table-column label="打板次数" width="100">
            <template #default>-</template>
          </el-table-column>
          <el-table-column label="版类" min-width="90">
            <template #default>-</template>
          </el-table-column>
          <el-table-column label="打板颜色" min-width="100">
            <template #default>-</template>
          </el-table-column>
          <el-table-column label="打板数量" width="100">
            <template #default>-</template>
          </el-table-column>
          <el-table-column label="下单次数" width="100">
            <template #default="scope">{{ scope.row.sales_order ? '1' : '0' }}</template>
          </el-table-column>
          <el-table-column v-for="week in weekColumns" :key="week" :label="week" width="60">
            <template #default>-</template>
          </el-table-column>
          <el-table-column label="销售预测金额" width="140">
            <template #default="scope">{{ formatAmount(scope.row.revenue_amount) }}</template>
          </el-table-column>
          <el-table-column label="成本预测金额" width="140">
            <template #default="scope">{{ formatAmount(scope.row.actual_total_cost) }}</template>
          </el-table-column>
          <el-table-column label="利润预测金额" width="140">
            <template #default="scope">{{ formatAmount(scope.row.profit_amount) }}</template>
          </el-table-column>
          <el-table-column label="利润预测率" width="130">
            <template #default="scope">{{ formatProfitRate(scope.row.profit_rate) }}</template>
          </el-table-column>
          <el-table-column label="标题" min-width="170">
            <template #default="scope">{{ scope.row.snapshot_no }}</template>
          </el-table-column>
          <el-table-column prop="created_at" label="发送时间" min-width="180" />
          <el-table-column label="状态" min-width="120">
            <template #default="scope">
              <el-tag :type="statusTagType(scope.row.snapshot_status)" data-testid="style-profit-status-tag">
                {{ statusText(scope.row.snapshot_status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="发送人" min-width="110">
            <template #default="scope">{{ scope.row.created_by || '-' }}</template>
          </el-table-column>
          <el-table-column label="操作" width="100" fixed="right">
            <template #default="scope">
              <el-button
                link
                type="primary"
                :data-testid="`style-profit-detail-${scope.row.id}`"
                @click="goDetail(scope.row.id)"
              >
                详情
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <div class="pager" data-testid="style-profit-pager">
          <el-pagination
            background
            layout="prev, pager, next, total, sizes"
            :current-page="query.page"
            :page-size="query.page_size"
            :total="total"
            :page-sizes="[10, 20, 50, 100]"
            data-testid="style-profit-pagination"
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

const toNumber = (value: string | number | null | undefined): number => {
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric : 0
}

const totalRevenueAmount = computed<number>(() => rows.value.reduce((sum, row) => sum + toNumber(row.revenue_amount), 0))
const totalCostAmount = computed<number>(() => rows.value.reduce((sum, row) => sum + toNumber(row.actual_total_cost), 0))
const totalProfitAmount = computed<number>(() => rows.value.reduce((sum, row) => sum + toNumber(row.profit_amount), 0))
const avgProfitRate = computed<number | null>(() => {
  if (rows.value.length === 0) {
    return null
  }
  const sum = rows.value.reduce((acc, row) => acc + toNumber(row.profit_rate ?? 0), 0)
  return sum / rows.value.length
})

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

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 12px;
}

.summary-card {
  border: 1px solid var(--el-border-color-lighter);
}

.summary-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.summary-value {
  margin-top: 6px;
  font-size: 18px;
  font-weight: 600;
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
