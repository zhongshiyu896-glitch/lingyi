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

        <el-divider />

        <div class="material-cost-section">
          <div class="title-group">
            <span class="title">大货成本物料明细表</span>
            <span class="sub-title">大货管理 / 大货成本物料明细（P1）</span>
          </div>

          <el-form :inline="true" :model="materialQuery" class="query-form">
            <el-form-item label="订单">
              <el-input
                v-model="materialQuery.sales_order"
                clearable
                placeholder="订单"
                @keyup.enter="onMaterialSearch"
              />
            </el-form-item>
            <el-form-item label="物料编码">
              <el-input
                v-model="materialQuery.material_item_code"
                clearable
                placeholder="物料编码"
                @keyup.enter="onMaterialSearch"
              />
            </el-form-item>
            <el-form-item label="供应商">
              <el-input
                v-model="materialQuery.supplier"
                clearable
                placeholder="供应商"
                @keyup.enter="onMaterialSearch"
              />
            </el-form-item>
            <el-form-item label="关键字">
              <el-input
                v-model="materialQuery.keyword"
                clearable
                placeholder="款号/客户/制单号"
                @keyup.enter="onMaterialSearch"
              />
            </el-form-item>
            <el-form-item label="状态">
              <el-select v-model="materialQuery.status" clearable placeholder="全部状态" style="width: 160px">
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
                v-model="materialQuery.from_date"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="开始时间"
                clearable
              />
            </el-form-item>
            <el-form-item label="结束时间">
              <el-date-picker
                v-model="materialQuery.to_date"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="结束时间"
                clearable
              />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :disabled="!canRead" @click="onMaterialSearch">搜索</el-button>
              <el-button :disabled="!canRead" @click="onMaterialReset">重置</el-button>
              <el-button :disabled="!canRead" @click="onMaterialRefresh">刷新</el-button>
            </el-form-item>
          </el-form>

          <div class="toolbar-row">
            <el-button :disabled="!canRead" @click="onMaterialSearch">筛选</el-button>
            <el-button :disabled="!canRead" @click="onMaterialClearFilters">清空</el-button>
            <el-button :disabled="!canRead" @click="onGuardedAction('导出明细', false)">导出</el-button>
            <el-button :disabled="!canRead" @click="onGuardedAction('列设置', false)">列设置</el-button>
          </div>

          <el-alert
            v-if="materialError"
            class="error-alert"
            type="error"
            :closable="false"
            :title="`成本物料明细加载失败：${materialError}`"
          />

          <el-table
            :data="materialRows"
            border
            v-loading="materialLoading"
            empty-text="暂无成本物料明细数据，请先完成物料检查或调整筛选条件"
          >
            <el-table-column prop="plan_no" label="生产制单" min-width="160" />
            <el-table-column label="订单信息" min-width="220">
              <template #default="scope">
                <div class="cell-stack">
                  <span class="primary-text">{{ scope.row.sales_order }}</span>
                  <span class="secondary-text">翻单号：{{ scope.row.sales_order_item || '-' }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="item_code" label="款号" min-width="140" />
            <el-table-column prop="material_item_code" label="物料编码" min-width="180" />
            <el-table-column label="供应商" min-width="140">
              <template #default="scope">{{ scope.row.supplier || '-' }}</template>
            </el-table-column>
            <el-table-column prop="qty_per_piece" label="单件用量" min-width="100" />
            <el-table-column prop="loss_rate" label="损耗率" min-width="90" />
            <el-table-column prop="required_qty" label="需求数量" min-width="100" />
            <el-table-column prop="estimated_unit_price" label="估算单价(元)" min-width="120" />
            <el-table-column prop="estimated_material_cost" label="估算成本(元)" min-width="120" />
            <el-table-column label="状态" min-width="120">
              <template #default="scope">
                <el-tag :type="statusTagType(scope.row.status)" effect="plain">
                  {{ statusLabel(scope.row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="检查时间" min-width="180">
              <template #default="scope">{{ scope.row.checked_at || '-' }}</template>
            </el-table-column>
            <el-table-column label="操作" fixed="right" min-width="170">
              <template #default="scope">
                <el-button link type="primary" @click="goDetail(scope.row.plan_id)">查看</el-button>
                <el-button link @click="onGuardedAction('导出明细', false)">导出</el-button>
              </template>
            </el-table-column>
          </el-table>

          <div class="pager">
            <el-pagination
              background
              layout="prev, pager, next, total, sizes"
              :current-page="materialQuery.page"
              :page-size="materialQuery.page_size"
              :total="materialTotal"
              :page-sizes="[10, 20, 50, 100]"
              @current-change="onMaterialPageChange"
              @size-change="onMaterialSizeChange"
            />
          </div>
        </div>

        <el-divider />

        <div class="sales-forecast-section">
          <div class="title-group">
            <span class="title">大货销售预测明细表</span>
            <span class="sub-title">大货管理 / 大货销售预测明细（P1）</span>
          </div>

          <el-form :inline="true" :model="salesForecastQuery" class="query-form">
            <el-form-item label="订单">
              <el-input
                v-model="salesForecastQuery.sales_order"
                clearable
                placeholder="订单"
                @keyup.enter="onSalesForecastSearch"
              />
            </el-form-item>
            <el-form-item label="款号">
              <el-input
                v-model="salesForecastQuery.item_code"
                clearable
                placeholder="款号"
                @keyup.enter="onSalesForecastSearch"
              />
            </el-form-item>
            <el-form-item label="客户">
              <el-input
                v-model="salesForecastQuery.customer"
                clearable
                placeholder="客户"
                @keyup.enter="onSalesForecastSearch"
              />
            </el-form-item>
            <el-form-item label="关键字">
              <el-input
                v-model="salesForecastQuery.keyword"
                clearable
                placeholder="制单号/翻单号/款号"
                @keyup.enter="onSalesForecastSearch"
              />
            </el-form-item>
            <el-form-item label="状态">
              <el-select v-model="salesForecastQuery.status" clearable placeholder="全部状态" style="width: 160px">
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
                v-model="salesForecastQuery.from_date"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="开始时间"
                clearable
              />
            </el-form-item>
            <el-form-item label="结束时间">
              <el-date-picker
                v-model="salesForecastQuery.to_date"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="结束时间"
                clearable
              />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :disabled="!canRead" @click="onSalesForecastSearch">搜索</el-button>
              <el-button :disabled="!canRead" @click="onSalesForecastReset">重置</el-button>
              <el-button :disabled="!canRead" @click="onSalesForecastRefresh">刷新</el-button>
            </el-form-item>
          </el-form>

          <div class="toolbar-row">
            <el-button :disabled="!canRead" @click="onSalesForecastSearch">筛选</el-button>
            <el-button :disabled="!canRead" @click="onSalesForecastClearFilters">清空</el-button>
            <el-button :disabled="!canRead" @click="onGuardedAction('导出销售预测', false)">导出</el-button>
            <el-button :disabled="!canRead" @click="onGuardedAction('销售预测列设置', false)">列设置</el-button>
          </div>

          <el-alert
            v-if="salesForecastError"
            class="error-alert"
            type="error"
            :closable="false"
            :title="`销售预测明细加载失败：${salesForecastError}`"
          />

          <el-table
            :data="salesForecastRows"
            border
            v-loading="salesForecastLoading"
            empty-text="暂无销售预测明细数据，请调整筛选条件后重试"
          >
            <el-table-column prop="plan_no" label="生产制单" min-width="160" />
            <el-table-column label="订单信息" min-width="220">
              <template #default="scope">
                <div class="cell-stack">
                  <span class="primary-text">{{ scope.row.sales_order }}</span>
                  <span class="secondary-text">翻单号：{{ scope.row.sales_order_item || '-' }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="item_code" label="款号" min-width="140" />
            <el-table-column label="客户" min-width="160">
              <template #default="scope">{{ scope.row.customer || '-' }}</template>
            </el-table-column>
            <el-table-column prop="forecast_qty" label="预测数量" min-width="110" />
            <el-table-column prop="forecast_unit_price" label="预测单价(元)" min-width="120" />
            <el-table-column prop="forecast_amount" label="预测金额(元)" min-width="130" />
            <el-table-column label="交期" min-width="120">
              <template #default="scope">{{ scope.row.delivery_date || '-' }}</template>
            </el-table-column>
            <el-table-column label="状态" min-width="120">
              <template #default="scope">
                <el-tag :type="statusTagType(scope.row.status)" effect="plain">
                  {{ statusLabel(scope.row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="检查时间" min-width="180">
              <template #default="scope">{{ scope.row.checked_at || '-' }}</template>
            </el-table-column>
            <el-table-column label="操作" fixed="right" min-width="170">
              <template #default="scope">
                <el-button link type="primary" @click="goDetail(scope.row.plan_id)">查看</el-button>
                <el-button link @click="onGuardedAction('导出销售预测', false)">导出</el-button>
              </template>
            </el-table-column>
          </el-table>

          <div class="pager">
            <el-pagination
              background
              layout="prev, pager, next, total, sizes"
              :current-page="salesForecastQuery.page"
              :page-size="salesForecastQuery.page_size"
              :total="salesForecastTotal"
              :page-sizes="[10, 20, 50, 100]"
              @current-change="onSalesForecastPageChange"
              @size-change="onSalesForecastSizeChange"
            />
          </div>
        </div>
      </template>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  fetchProductionMaterialCostDetails,
  fetchProductionPlans,
  type ProductionMaterialCostListItem,
  type ProductionPlanListItem,
  fetchProductionSalesForecastDetails,
  type ProductionSalesForecastListItem,
} from '@/api/production'
import { usePermissionStore } from '@/stores/permission'

const router = useRouter()
const permissionStore = usePermissionStore()

const loading = ref<boolean>(false)
const rows = ref<ProductionPlanListItem[]>([])
const total = ref<number>(0)
const lastError = ref<string>('')
const materialLoading = ref<boolean>(false)
const materialRows = ref<ProductionMaterialCostListItem[]>([])
const materialTotal = ref<number>(0)
const materialError = ref<string>('')
const salesForecastLoading = ref<boolean>(false)
const salesForecastRows = ref<ProductionSalesForecastListItem[]>([])
const salesForecastTotal = ref<number>(0)
const salesForecastError = ref<string>('')

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

const materialQuery = reactive({
  sales_order: '',
  keyword: '',
  turnover_no: '',
  material_item_code: '',
  supplier: '',
  from_date: '',
  to_date: '',
  status: '',
  page: 1,
  page_size: 20,
})

const salesForecastQuery = reactive({
  sales_order: '',
  keyword: '',
  turnover_no: '',
  item_code: '',
  customer: '',
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

const validateMaterialDateRange = (): boolean => {
  if (!materialQuery.from_date || !materialQuery.to_date) return true
  if (materialQuery.from_date <= materialQuery.to_date) return true
  ElMessage.error('开始时间不能晚于结束时间')
  return false
}

const validateSalesForecastDateRange = (): boolean => {
  if (!salesForecastQuery.from_date || !salesForecastQuery.to_date) return true
  if (salesForecastQuery.from_date <= salesForecastQuery.to_date) return true
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

const resetMaterialRows = (): void => {
  materialRows.value = []
  materialTotal.value = 0
}

const resetSalesForecastRows = (): void => {
  salesForecastRows.value = []
  salesForecastTotal.value = 0
}

const loadMaterialRows = async (): Promise<void> => {
  if (!canRead.value) {
    resetMaterialRows()
    materialError.value = ''
    return
  }

  materialLoading.value = true
  materialError.value = ''
  try {
    const result = await fetchProductionMaterialCostDetails({
      sales_order: materialQuery.sales_order.trim() || undefined,
      keyword: materialQuery.keyword.trim() || undefined,
      turnover_no: materialQuery.turnover_no.trim() || undefined,
      material_item_code: materialQuery.material_item_code.trim() || undefined,
      supplier: materialQuery.supplier.trim() || undefined,
      from_date: materialQuery.from_date || undefined,
      to_date: materialQuery.to_date || undefined,
      status: materialQuery.status || undefined,
      page: materialQuery.page,
      page_size: materialQuery.page_size,
    })
    materialRows.value = result.data.items
    materialTotal.value = result.data.total
  } catch (error) {
    const message = (error as Error).message
    materialError.value = message
    resetMaterialRows()
    ElMessage.error(message)
  } finally {
    materialLoading.value = false
  }
}

const loadSalesForecastRows = async (): Promise<void> => {
  if (!canRead.value) {
    resetSalesForecastRows()
    salesForecastError.value = ''
    return
  }

  salesForecastLoading.value = true
  salesForecastError.value = ''
  try {
    const result = await fetchProductionSalesForecastDetails({
      sales_order: salesForecastQuery.sales_order.trim() || undefined,
      keyword: salesForecastQuery.keyword.trim() || undefined,
      turnover_no: salesForecastQuery.turnover_no.trim() || undefined,
      item_code: salesForecastQuery.item_code.trim() || undefined,
      customer: salesForecastQuery.customer.trim() || undefined,
      from_date: salesForecastQuery.from_date || undefined,
      to_date: salesForecastQuery.to_date || undefined,
      status: salesForecastQuery.status || undefined,
      page: salesForecastQuery.page,
      page_size: salesForecastQuery.page_size,
    })
    salesForecastRows.value = result.data.items
    salesForecastTotal.value = result.data.total
  } catch (error) {
    const message = (error as Error).message
    salesForecastError.value = message
    resetSalesForecastRows()
    ElMessage.error(message)
  } finally {
    salesForecastLoading.value = false
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

const onMaterialSearch = (): void => {
  if (!validateMaterialDateRange()) return
  materialQuery.page = 1
  void loadMaterialRows()
}

const onMaterialReset = (): void => {
  materialQuery.sales_order = ''
  materialQuery.keyword = ''
  materialQuery.turnover_no = ''
  materialQuery.material_item_code = ''
  materialQuery.supplier = ''
  materialQuery.from_date = ''
  materialQuery.to_date = ''
  materialQuery.status = ''
  materialQuery.page = 1
  materialQuery.page_size = 20
  void loadMaterialRows()
}

const onMaterialRefresh = (): void => {
  void loadMaterialRows()
}

const onMaterialClearFilters = (): void => {
  materialQuery.sales_order = ''
  materialQuery.keyword = ''
  materialQuery.turnover_no = ''
  materialQuery.material_item_code = ''
  materialQuery.supplier = ''
  materialQuery.from_date = ''
  materialQuery.to_date = ''
  materialQuery.status = ''
}

const onSalesForecastSearch = (): void => {
  if (!validateSalesForecastDateRange()) return
  salesForecastQuery.page = 1
  void loadSalesForecastRows()
}

const onSalesForecastReset = (): void => {
  salesForecastQuery.sales_order = ''
  salesForecastQuery.keyword = ''
  salesForecastQuery.turnover_no = ''
  salesForecastQuery.item_code = ''
  salesForecastQuery.customer = ''
  salesForecastQuery.from_date = ''
  salesForecastQuery.to_date = ''
  salesForecastQuery.status = ''
  salesForecastQuery.page = 1
  salesForecastQuery.page_size = 20
  void loadSalesForecastRows()
}

const onSalesForecastRefresh = (): void => {
  void loadSalesForecastRows()
}

const onSalesForecastClearFilters = (): void => {
  salesForecastQuery.sales_order = ''
  salesForecastQuery.keyword = ''
  salesForecastQuery.turnover_no = ''
  salesForecastQuery.item_code = ''
  salesForecastQuery.customer = ''
  salesForecastQuery.from_date = ''
  salesForecastQuery.to_date = ''
  salesForecastQuery.status = ''
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

const onMaterialPageChange = (page: number): void => {
  materialQuery.page = page
  void loadMaterialRows()
}

const onMaterialSizeChange = (size: number): void => {
  materialQuery.page_size = size
  materialQuery.page = 1
  void loadMaterialRows()
}

const onSalesForecastPageChange = (page: number): void => {
  salesForecastQuery.page = page
  void loadSalesForecastRows()
}

const onSalesForecastSizeChange = (size: number): void => {
  salesForecastQuery.page_size = size
  salesForecastQuery.page = 1
  void loadSalesForecastRows()
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
    await loadMaterialRows()
    await loadSalesForecastRows()
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

.material-cost-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.sales-forecast-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
</style>
