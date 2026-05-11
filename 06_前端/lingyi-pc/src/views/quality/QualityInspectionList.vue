<template>
  <div class="quality-page" data-testid="quality-inspection-page">
    <el-card shadow="never">
      <template #header>
        <div class="header-row">
          <span>质量检验单列表</span>
          <div class="header-actions">
            <el-button
              type="primary"
              :disabled="!canRead"
              data-testid="quality-query-button"
              @click="applyPrimaryQuery"
            >
              查询
            </el-button>
            <el-button
              :disabled="!canRead"
              data-testid="quality-reset-button"
              @click="resetPrimaryFilters"
            >
              重置
            </el-button>
            <el-button
              v-if="canExport"
              :disabled="!canRead"
              data-testid="quality-export-snapshot-button"
              @click="showGuardedAction('导出快照')"
            >
              导出快照
            </el-button>
            <el-button
              v-if="canExport"
              :disabled="!canRead"
              data-testid="quality-export-xlsx-button"
              @click="showGuardedAction('导出 Excel')"
            >
              导出 Excel
            </el-button>
            <el-button
              v-if="canExport"
              :disabled="!canRead"
              data-testid="quality-export-pdf-button"
              @click="showGuardedAction('导出 PDF')"
            >
              导出 PDF
            </el-button>
            <el-button
              v-if="canCreate"
              type="success"
              data-testid="quality-create-button"
              data-action-type="write"
              data-write-guard="guarded:readonly_mode"
              data-guard-state="guarded"
              @click="openCreateDialog"
            >
              创建检验单
            </el-button>
          </div>
        </div>
      </template>

      <el-form :inline="true" :model="query" data-testid="quality-filter-form">
        <el-form-item label="公司">
          <el-input v-model="query.company" clearable placeholder="company" data-testid="quality-filter-company" />
        </el-form-item>
        <el-form-item label="物料">
          <el-input v-model="query.item_code" clearable placeholder="item_code" data-testid="quality-filter-item-code" />
        </el-form-item>
        <el-form-item label="供应商">
          <el-input v-model="query.supplier" clearable placeholder="supplier" data-testid="quality-filter-supplier" />
        </el-form-item>
        <el-form-item label="来源类型">
          <el-select
            v-model="query.source_type"
            clearable
            placeholder="全部来源类型"
            style="width: 180px"
            data-testid="quality-filter-source-type"
          >
            <el-option label="来料检验" value="incoming_material" />
            <el-option label="外发收货检验" value="subcontract_receipt" />
            <el-option label="成品检验" value="finished_goods" />
            <el-option label="手工检验" value="manual" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select
            v-model="query.status"
            clearable
            placeholder="全部状态"
            style="width: 140px"
            data-testid="quality-filter-status"
          >
            <el-option label="草稿" value="draft" />
            <el-option label="已确认" value="confirmed" />
            <el-option label="已取消" value="cancelled" />
          </el-select>
        </el-form-item>
        <el-form-item label="开始日期">
          <el-date-picker
            v-model="query.from_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="开始日期"
            clearable
            data-testid="quality-filter-from-date"
          />
        </el-form-item>
        <el-form-item label="结束日期">
          <el-date-picker
            v-model="query.to_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="结束日期"
            clearable
            data-testid="quality-filter-to-date"
          />
        </el-form-item>
      </el-form>

      <el-skeleton v-if="!permissionReady" :rows="4" animated data-testid="quality-permission-loading" />
      <el-empty v-else-if="!canRead" description="无质量管理查看权限" data-testid="quality-permission-state" />
      <el-tabs v-else v-model="activeTab">
        <el-tab-pane label="检验列表" name="list">
          <el-alert
            v-if="statistics"
            class="summary-alert"
            data-testid="quality-statistics-alert"
            type="info"
            :closable="false"
            :title="`本页筛选统计：检验 ${statistics.total_count} 单，检验数量 ${formatAmount(statistics.total_inspected_qty)}，缺陷率 ${formatRate(statistics.overall_defect_rate)}`"
          />
          <el-alert
            v-if="listError"
            class="summary-alert"
            data-testid="quality-error-state"
            type="error"
            :closable="false"
            :title="listError"
          />

          <el-table
            :data="rows"
            border
            v-loading="loading"
            empty-text="暂无检验单数据，请调整筛选条件后重试"
            data-testid="quality-list-table"
          >
            <el-table-column prop="inspection_no" label="检验单号" min-width="180" />
            <el-table-column prop="company" label="公司" min-width="120" />
            <el-table-column prop="item_code" label="物料" min-width="140" />
            <el-table-column prop="supplier" label="供应商" min-width="140" />
            <el-table-column label="来源" min-width="170">
              <template #default="scope">
                {{ sourceTypeLabel(scope.row.source_type) }} / {{ scope.row.source_id || '-' }}
              </template>
            </el-table-column>
            <el-table-column prop="inspection_date" label="检验日期" width="120" />
            <el-table-column label="检验数量" width="110">
              <template #default="scope">{{ formatAmount(scope.row.inspected_qty) }}</template>
            </el-table-column>
            <el-table-column label="合格数量" width="110">
              <template #default="scope">{{ formatAmount(scope.row.accepted_qty) }}</template>
            </el-table-column>
            <el-table-column label="不合格数量" width="120">
              <template #default="scope">{{ formatAmount(scope.row.rejected_qty) }}</template>
            </el-table-column>
            <el-table-column label="结果" width="110">
              <template #default="scope">
                <el-tag :type="resultTag(scope.row.result)" data-testid="quality-result-tag">{{ resultLabel(scope.row.result) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="110">
              <template #default="scope">
                <el-tag :type="statusTag(scope.row.status)" data-testid="quality-status-tag">{{ statusLabel(scope.row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" fixed="right" width="230">
              <template #default="scope">
                <el-button link type="primary" data-testid="quality-detail-button" @click="goDetail(scope.row.id)">详情</el-button>
                <el-button
                  v-if="canExport"
                  link
                  type="success"
                  data-testid="quality-row-export-xlsx-button"
                  @click="showGuardedAction('导出 Excel')"
                >
                  Excel
                </el-button>
                <el-button
                  v-if="canExport"
                  link
                  type="warning"
                  data-testid="quality-row-export-pdf-button"
                  @click="showGuardedAction('导出 PDF')"
                >
                  PDF
                </el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-empty
            v-if="!loading && rows.length === 0"
            description="暂无检验单数据，请调整筛选条件后重试"
            data-testid="quality-empty-state"
          />

          <div class="pager" data-testid="quality-pagination">
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
        </el-tab-pane>

        <el-tab-pane label="统计分析" name="statistics">
          <el-empty v-if="!statistics" description="暂无统计数据" />
          <template v-else>
            <div class="stat-cards">
              <el-card shadow="never" data-testid="quality-stat-card-total-count">
                <div class="stat-label">检验单总数</div>
                <div class="stat-value">{{ statistics.total_count }}</div>
              </el-card>
              <el-card shadow="never" data-testid="quality-stat-card-inspected">
                <div class="stat-label">检验数量</div>
                <div class="stat-value">{{ formatAmount(statistics.total_inspected_qty) }}</div>
              </el-card>
              <el-card shadow="never" data-testid="quality-stat-card-rejected">
                <div class="stat-label">不合格数量</div>
                <div class="stat-value">{{ formatAmount(statistics.total_rejected_qty) }}</div>
              </el-card>
              <el-card shadow="never" data-testid="quality-stat-card-defect-rate">
                <div class="stat-label">总体缺陷率</div>
                <div class="stat-value">{{ formatRate(statistics.overall_defect_rate) }}</div>
              </el-card>
            </div>

            <div class="stats-section">
              <h4>按供应商聚合</h4>
              <el-table :data="statistics.by_supplier" border empty-text="暂无供应商统计，请调整筛选条件后重试">
                <el-table-column prop="label" label="供应商" min-width="180" />
                <el-table-column prop="count" label="检验单数" width="100" />
                <el-table-column label="检验数量" width="120">
                  <template #default="scope">{{ formatAmount(scope.row.total_inspected_qty) }}</template>
                </el-table-column>
                <el-table-column label="不合格数量" width="120">
                  <template #default="scope">{{ formatAmount(scope.row.total_rejected_qty) }}</template>
                </el-table-column>
                <el-table-column label="缺陷率" width="120">
                  <template #default="scope">{{ formatRate(scope.row.defect_rate) }}</template>
                </el-table-column>
              </el-table>
            </div>

            <div class="stats-section">
              <h4>按物料聚合</h4>
              <el-table :data="statistics.by_item_code" border empty-text="暂无物料统计，请调整筛选条件后重试">
                <el-table-column prop="label" label="物料" min-width="180" />
                <el-table-column prop="count" label="检验单数" width="100" />
                <el-table-column label="检验数量" width="120">
                  <template #default="scope">{{ formatAmount(scope.row.total_inspected_qty) }}</template>
                </el-table-column>
                <el-table-column label="不合格数量" width="120">
                  <template #default="scope">{{ formatAmount(scope.row.total_rejected_qty) }}</template>
                </el-table-column>
                <el-table-column label="缺陷率" width="120">
                  <template #default="scope">{{ formatRate(scope.row.defect_rate) }}</template>
                </el-table-column>
              </el-table>
            </div>

            <div class="stats-section">
              <h4>按仓库聚合</h4>
              <el-table :data="statistics.by_warehouse" border empty-text="暂无仓库统计，请调整筛选条件后重试">
                <el-table-column prop="label" label="仓库" min-width="180" />
                <el-table-column prop="count" label="检验单数" width="100" />
                <el-table-column label="检验数量" width="120">
                  <template #default="scope">{{ formatAmount(scope.row.total_inspected_qty) }}</template>
                </el-table-column>
                <el-table-column label="不合格数量" width="120">
                  <template #default="scope">{{ formatAmount(scope.row.total_rejected_qty) }}</template>
                </el-table-column>
                <el-table-column label="缺陷率" width="120">
                  <template #default="scope">{{ formatRate(scope.row.defect_rate) }}</template>
                </el-table-column>
              </el-table>
            </div>

            <div class="stats-grid">
              <el-card shadow="never">
                <template #header>Top 缺陷供应商</template>
                <el-table :data="statistics.top_defective_suppliers" border empty-text="暂无缺陷供应商数据，请调整筛选条件后重试">
                  <el-table-column prop="label" label="供应商" min-width="140" />
                  <el-table-column label="缺陷率" width="120">
                    <template #default="scope">{{ formatRate(scope.row.defect_rate) }}</template>
                  </el-table-column>
                </el-table>
              </el-card>
              <el-card shadow="never">
                <template #header>Top 缺陷物料</template>
                <el-table :data="statistics.top_defective_items" border empty-text="暂无缺陷物料数据，请调整筛选条件后重试">
                  <el-table-column prop="label" label="物料" min-width="140" />
                  <el-table-column label="缺陷率" width="120">
                    <template #default="scope">{{ formatRate(scope.row.defect_rate) }}</template>
                  </el-table-column>
                </el-table>
              </el-card>
            </div>

            <div class="stats-section">
              <div class="trend-header">
                <h4>趋势统计</h4>
                <el-radio-group v-model="trendPeriod" @change="loadTrend">
                  <el-radio-button label="monthly">按月</el-radio-button>
                  <el-radio-button label="weekly">按周</el-radio-button>
                </el-radio-group>
              </div>
              <el-table :data="statisticsTrend?.points || []" border empty-text="暂无趋势数据，请调整筛选条件后重试">
                <el-table-column prop="period_key" label="周期" width="120" />
                <el-table-column prop="inspection_count" label="检验单数" width="100" />
                <el-table-column label="检验数量" width="120">
                  <template #default="scope">{{ formatAmount(scope.row.total_inspected_qty) }}</template>
                </el-table-column>
                <el-table-column label="不合格数量" width="120">
                  <template #default="scope">{{ formatAmount(scope.row.total_rejected_qty) }}</template>
                </el-table-column>
                <el-table-column label="缺陷率" width="120">
                  <template #default="scope">{{ formatRate(scope.row.defect_rate) }}</template>
                </el-table-column>
                <el-table-column label="不合格率" width="120">
                  <template #default="scope">{{ formatRate(scope.row.rejected_rate) }}</template>
                </el-table-column>
              </el-table>
            </div>
          </template>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <el-dialog
      v-model="createDialogVisible"
      title="创建质量检验单"
      width="560px"
      destroy-on-close
      data-testid="quality-create-guard-dialog"
    >
      <el-alert
        type="warning"
        :closable="false"
        title="当前任务为只读交互阶段，创建检验单动作已禁用。"
        data-testid="quality-create-guard-message"
      />
      <template #footer>
        <el-button data-testid="quality-create-guard-cancel" @click="createDialogVisible = false">关闭</el-button>
        <el-button
          type="primary"
          :disabled="!canCreate"
          data-testid="quality-create-guard-submit"
          data-action-type="write"
          data-write-guard="guarded:readonly_mode"
          data-guard-state="guarded"
          @click="submitCreate"
        >
          提交
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
  fetchQualityInspectionDetail,
  fetchQualityInspections,
  fetchQualityStatistics,
  fetchQualityStatisticsTrend,
  type QualityInspectionListItem,
  type QualityStatisticsData,
  type QualityStatisticsTrendData,
} from '@/api/quality'
import { usePermissionStore } from '@/stores/permission'

const router = useRouter()
const permissionStore = usePermissionStore()

const loading = ref<boolean>(false)
const createDialogVisible = ref<boolean>(false)
const permissionReady = ref<boolean>(false)
const activeTab = ref<'list' | 'statistics'>('list')
const trendPeriod = ref<'monthly' | 'weekly'>('monthly')
const rows = ref<QualityInspectionListItem[]>([])
const total = ref<number>(0)
const statistics = ref<QualityStatisticsData | null>(null)
const statisticsTrend = ref<QualityStatisticsTrendData | null>(null)
const listError = ref<string>('')

const canRead = computed<boolean>(() => permissionStore.state.buttonPermissions.quality_read)
const canCreate = computed<boolean>(() => permissionStore.state.buttonPermissions.quality_create)
const canExport = computed<boolean>(() => permissionStore.state.buttonPermissions.quality_export)

const query = reactive({
  company: '',
  item_code: '',
  supplier: '',
  warehouse: '',
  source_type: '',
  source_id: '',
  status: '',
  from_date: '',
  to_date: '',
  page: 1,
  page_size: 20,
})

const clean = (value: string): string | undefined => value.trim() || undefined

const buildFilterQuery = () => ({
  company: clean(query.company),
  item_code: clean(query.item_code),
  supplier: clean(query.supplier),
  warehouse: clean(query.warehouse),
  source_type: clean(query.source_type),
  source_id: clean(query.source_id),
  status: clean(query.status),
  from_date: clean(query.from_date),
  to_date: clean(query.to_date),
})

const formatAmount = (value: string | number | null | undefined): string => {
  if (value === null || value === undefined || value === '') return '-'
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric.toFixed(2) : String(value)
}

const formatRate = (value: string | number | null | undefined): string => {
  if (value === null || value === undefined || value === '') return '-'
  const numeric = Number(value)
  return Number.isFinite(numeric) ? `${(numeric * 100).toFixed(2)}%` : String(value)
}

const sourceTypeLabel = (value: string): string => {
  if (value === 'incoming_material') return '来料检验'
  if (value === 'subcontract_receipt') return '外发收货检验'
  if (value === 'finished_goods') return '成品检验'
  if (value === 'manual') return '手工检验'
  return value || '-'
}

const resultLabel = (value: string): string => {
  if (value === 'pending') return '待定'
  if (value === 'pass') return '合格'
  if (value === 'fail') return '不合格'
  if (value === 'partial') return '部分合格'
  return value || '-'
}

const statusLabel = (value: string): string => {
  if (value === 'draft') return '草稿'
  if (value === 'confirmed') return '已确认'
  if (value === 'cancelled') return '已取消'
  return value || '-'
}

const resultTag = (value: string): 'success' | 'danger' | 'warning' | 'info' => {
  if (value === 'pass') return 'success'
  if (value === 'fail') return 'danger'
  if (value === 'partial') return 'warning'
  return 'info'
}

const statusTag = (value: string): 'success' | 'danger' | 'warning' | 'info' => {
  if (value === 'draft') return 'warning'
  if (value === 'confirmed') return 'success'
  if (value === 'cancelled') return 'danger'
  return 'info'
}

const resetRows = (): void => {
  rows.value = []
  total.value = 0
  statistics.value = null
  statisticsTrend.value = null
  listError.value = ''
}

const loadTrend = async (): Promise<void> => {
  if (!canRead.value) {
    statisticsTrend.value = null
    return
  }
  const trend = await fetchQualityStatisticsTrend(trendPeriod.value, buildFilterQuery())
  statisticsTrend.value = trend.data
}

const loadRows = async (): Promise<void> => {
  if (!canRead.value) {
    resetRows()
    return
  }

  loading.value = true
  listError.value = ''
  try {
    const filters = buildFilterQuery()
    const result = await fetchQualityInspections({ ...filters, page: query.page, page_size: query.page_size })
    rows.value = result.data.items
    total.value = result.data.total
    const stats = await fetchQualityStatistics(filters)
    statistics.value = stats.data
    const trend = await fetchQualityStatisticsTrend(trendPeriod.value, filters)
    statisticsTrend.value = trend.data
  } catch (error) {
    const message = (error as Error).message
    listError.value = message
    ElMessage.error(message)
    rows.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

const applyPrimaryQuery = (): void => {
  if (!canRead.value) {
    return
  }
  query.page = 1
  void loadRows()
}

const resetPrimaryFilters = (): void => {
  query.company = ''
  query.item_code = ''
  query.supplier = ''
  query.warehouse = ''
  query.source_type = ''
  query.source_id = ''
  query.status = ''
  query.from_date = ''
  query.to_date = ''
  query.page = 1
  query.page_size = 20
  if (!canRead.value) {
    resetRows()
    return
  }
  void loadRows()
}

const showGuardedAction = (actionName: string): void => {
  ElMessage.warning(`${actionName}在当前只读交互阶段已禁用`)
}

const openCreateDialog = (): void => {
  if (!canCreate.value) {
    ElMessage.error('无创建检验单权限')
    return
  }
  createDialogVisible.value = true
}

const submitCreate = (): void => {
  showGuardedAction('创建检验单')
}

const goDetail = async (id: number): Promise<void> => {
  if (!canRead.value) {
    return
  }
  try {
    await fetchQualityInspectionDetail(id)
    await router.push({ path: '/quality/inspections/detail', query: { id: String(id) } })
  } catch (error) {
    const message = (error as Error).message
    ElMessage.error(message)
    listError.value = message
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

onMounted(async () => {
  try {
    await permissionStore.loadCurrentUser()
    await permissionStore.loadModuleActions('quality')
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    permissionReady.value = true
  }
  if (canRead.value) {
    await loadRows()
  }
})
</script>

<style scoped>
.quality-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.summary-alert {
  margin-bottom: 12px;
}

.pager {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}

.stat-cards {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 12px;
}

.stat-label {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.stat-value {
  margin-top: 6px;
  font-size: 20px;
  font-weight: 600;
}

.stats-section {
  margin-top: 16px;
}

.stats-grid {
  margin-top: 16px;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.trend-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
</style>
