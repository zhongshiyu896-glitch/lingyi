<template>
  <div class="sales-inventory-page" data-testid="sales-order-page">
    <el-card shadow="never">
      <template #header>
        <div class="header-row">
          <div class="title-group">
            <span class="title">订单</span>
            <span class="sub-title">大货管理 / 订单</span>
          </div>
          <el-tag type="info" effect="plain">本地首版</el-tag>
        </div>
      </template>

      <el-form :inline="true" :model="query" class="query-form" data-testid="sales-order-filter-form">
        <el-form-item label="订单号">
          <el-input
            v-model="query.order_no"
            clearable
            placeholder="订单号"
            data-testid="sales-order-filter-order-no"
            @keyup.enter="applyPrimaryQuery"
          />
        </el-form-item>
        <el-form-item label="关键词">
          <el-input
            v-model="query.keyword"
            clearable
            placeholder="款号/款名/客户款号"
            data-testid="sales-order-filter-keyword"
            @keyup.enter="applyPrimaryQuery"
          />
        </el-form-item>
        <el-form-item label="开始时间" data-testid="sales-order-filter-from-date">
          <el-date-picker
            v-model="query.from_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="开始时间"
            clearable
          />
        </el-form-item>
        <el-form-item label="结束时间" data-testid="sales-order-filter-to-date">
          <el-date-picker
            v-model="query.to_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="结束时间"
            clearable
          />
        </el-form-item>
        <el-form-item>
          <el-button
            data-testid="sales-order-query-button"
            type="primary"
            :disabled="!canRead"
            @click="applyPrimaryQuery"
          >
            搜索
          </el-button>
          <el-button
            data-testid="sales-order-reset-button"
            :disabled="!canRead"
            @click="resetPrimaryFilters"
          >
            重置
          </el-button>
        </el-form-item>
      </el-form>

      <div class="toolbar-row" data-testid="sales-order-toolbar">
        <el-button data-testid="sales-order-guarded-filter" @click="onUnavailableAction('筛选')">筛选</el-button>
        <el-button
          data-testid="sales-order-guarded-new"
          type="primary"
          :disabled="!canRead"
          @click="onUnavailableAction('新建')"
        >
          新建
        </el-button>
        <el-button data-testid="sales-order-guarded-place-order" :disabled="!canRead" @click="onUnavailableAction('下单')">
          下单
        </el-button>
        <el-button data-testid="sales-order-guarded-fetch" :disabled="!canRead" @click="onUnavailableAction('获取订单')">
          获取订单
        </el-button>
        <el-button data-testid="sales-order-guarded-import" :disabled="!canRead" @click="onUnavailableAction('导入')">
          导入
        </el-button>
        <el-button data-testid="sales-order-guarded-export" :disabled="!canExport" @click="onUnavailableAction('导出')">
          导出
        </el-button>
      </div>

      <el-alert
        v-if="lastError"
        data-testid="sales-order-error-state"
        class="error-alert"
        type="error"
        :closable="false"
        :title="`订单列表加载失败：${lastError}`"
      />

      <el-empty v-if="!canRead" data-testid="sales-order-permission-state" description="无销售库存查看权限" />
      <template v-else>
        <el-table
          data-testid="sales-order-table"
          :data="rows"
          border
          empty-text="暂无订单数据，请调整筛选条件后重试"
          v-loading="loading"
        >
          <el-table-column prop="name" label="订单号" min-width="170" />
          <el-table-column prop="customer" label="客户" min-width="150" />
          <el-table-column prop="company" label="单位" min-width="130" />
          <el-table-column prop="transaction_date" label="下单日期" width="120" />
          <el-table-column prop="delivery_date" label="交期" width="120" />
          <el-table-column label="状态" min-width="120">
            <template #default="scope">
              <el-tag data-testid="sales-order-status-tag" effect="plain" :type="resolveOrderStatusType(scope.row.status)">
                {{ scope.row.status || '-' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="数量/金额" min-width="130">
            <template #default="scope">{{ formatAmount(scope.row.grand_total) }}</template>
          </el-table-column>
          <el-table-column prop="currency" label="币种" width="100" />
          <el-table-column label="操作" fixed="right" min-width="230">
            <template #default="scope">
              <el-button
                data-testid="sales-order-guarded-progress"
                link
                type="primary"
                @click="onUnavailableAction('进度')"
              >
                进度
              </el-button>
              <el-button data-testid="sales-order-detail-button" link type="primary" @click="goDetail(scope.row.name)">
                详情
              </el-button>
              <el-button
                data-testid="sales-order-guarded-print"
                link
                type="primary"
                @click="onUnavailableAction('打印')"
              >
                打印
              </el-button>
              <el-button
                data-testid="sales-order-guarded-more"
                link
                type="primary"
                @click="onUnavailableAction('更多')"
              >
                更多
              </el-button>
            </template>
          </el-table-column>
        </el-table>
        <p
          v-if="!loading && rows.length === 0 && !lastError"
          data-testid="sales-order-empty-state"
          class="state-hint"
        >
          暂无订单数据，请调整筛选条件后重试
        </p>

        <div class="pager">
          <el-pagination
            data-testid="sales-order-pagination"
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

        <section class="p1-03-section" data-testid="sales-order-fulfillment-section">
          <div class="section-header">
            <div class="title-group">
              <span class="title">订单生产加工数量对照表</span>
              <span class="sub-title">P1 / TASK-Y22B-P1-03</span>
            </div>
            <el-tag type="warning" effect="plain">只读对照</el-tag>
          </div>

          <el-form :inline="true" :model="fulfillmentQuery" class="query-form" data-testid="sales-order-fulfillment-filter-form">
            <el-form-item label="款号">
              <el-input
                v-model="fulfillmentQuery.item_code"
                clearable
                placeholder="款号"
                data-testid="sales-order-fulfillment-filter-item-code"
                @keyup.enter="onFulfillmentSearch"
              />
            </el-form-item>
            <el-form-item label="款名关键词">
              <el-input
                v-model="fulfillmentQuery.item_name"
                clearable
                placeholder="款名关键词"
                data-testid="sales-order-fulfillment-filter-item-name"
                @keyup.enter="onFulfillmentSearch"
              />
            </el-form-item>
            <el-form-item label="仓库">
              <el-input
                v-model="fulfillmentQuery.warehouse"
                clearable
                placeholder="仓库"
                data-testid="sales-order-fulfillment-filter-warehouse"
                @keyup.enter="onFulfillmentSearch"
              />
            </el-form-item>
            <el-form-item>
              <el-button
                data-testid="sales-order-fulfillment-query-button"
                type="primary"
                :disabled="!canRead"
                @click="onFulfillmentSearch"
              >
                查询
              </el-button>
              <el-button
                data-testid="sales-order-fulfillment-reset-button"
                :disabled="!canRead"
                @click="onFulfillmentReset"
              >
                重置
              </el-button>
            </el-form-item>
          </el-form>

          <div class="toolbar-row" data-testid="sales-order-fulfillment-toolbar">
            <el-button
              data-testid="sales-order-fulfillment-guarded-export"
              :disabled="!canExport"
              @click="onUnavailableAction('对照导出')"
            >
              导出
            </el-button>
            <el-button
              data-testid="sales-order-fulfillment-guarded-columns"
              :disabled="!canRead"
              @click="onUnavailableAction('对照列设置')"
            >
              列设置
            </el-button>
          </div>

          <el-alert
            v-if="fulfillmentError"
            data-testid="sales-order-fulfillment-error-state"
            class="error-alert"
            type="error"
            :closable="false"
            :title="`对照表加载失败：${fulfillmentError}`"
          />

          <el-table
            data-testid="sales-order-fulfillment-table"
            :data="fulfillmentRows"
            border
            class="comparison-table"
            empty-text="暂无订单生产加工数量对照数据"
            v-loading="fulfillmentLoading"
          >
            <el-table-column prop="sales_order" label="订单号" min-width="170" />
            <el-table-column prop="item_code" label="款号" min-width="140" />
            <el-table-column prop="warehouse" label="仓库" min-width="140" />
            <el-table-column label="订单数量" min-width="120">
              <template #default="scope">{{ formatAmount(scope.row.ordered_qty) }}</template>
            </el-table-column>
            <el-table-column label="加工数量" min-width="120">
              <template #default="scope">{{ formatAmount(scope.row.actual_qty) }}</template>
            </el-table-column>
            <el-table-column label="完成率" min-width="120">
              <template #default="scope">{{ formatPercent(scope.row.fulfillment_rate) }}</template>
            </el-table-column>
            <el-table-column label="状态" min-width="130">
              <template #default="scope">
                <el-tag
                  data-testid="sales-order-fulfillment-status-tag"
                  :type="resolveFulfillmentStatus(scope.row.fulfillment_rate).type"
                  effect="plain"
                >
                  {{ resolveFulfillmentStatus(scope.row.fulfillment_rate).label }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" fixed="right" min-width="220">
              <template #default="scope">
                <el-button
                  data-testid="sales-order-fulfillment-detail-button"
                  link
                  type="primary"
                  @click="goDetail(scope.row.sales_order)"
                >
                  查看
                </el-button>
                <el-button
                  data-testid="sales-order-fulfillment-guarded-export-link"
                  link
                  type="primary"
                  @click="onUnavailableAction('对照导出')"
                >
                  导出
                </el-button>
                <el-button
                  data-testid="sales-order-fulfillment-guarded-more-link"
                  link
                  type="primary"
                  @click="onUnavailableAction('对照更多')"
                >
                  更多
                </el-button>
              </template>
            </el-table-column>
          </el-table>
          <p
            v-if="!fulfillmentLoading && fulfillmentRows.length === 0 && !fulfillmentError"
            data-testid="sales-order-fulfillment-empty-state"
            class="state-hint"
          >
            暂无订单生产加工数量对照数据
          </p>
        </section>
      </template>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  fetchSalesInventorySalesOrderDetail,
  fetchSalesInventorySalesOrderFulfillment,
  fetchSalesInventorySalesOrders,
  type SalesOrderFulfillmentItem,
  type SalesOrderListItem,
} from '@/api/sales_inventory'
import { usePermissionStore } from '@/stores/permission'

const router = useRouter()
const permissionStore = usePermissionStore()
const loading = ref<boolean>(false)
const rows = ref<SalesOrderListItem[]>([])
const total = ref<number>(0)
const lastError = ref<string>('')
const fulfillmentLoading = ref<boolean>(false)
const fulfillmentRows = ref<SalesOrderFulfillmentItem[]>([])
const fulfillmentError = ref<string>('')
const defaultPageSize = 20

const canRead = computed<boolean>(() => {
  return (
    permissionStore.state.buttonPermissions.sales_inventory_read ||
    permissionStore.state.actions.includes('sales_inventory:read')
  )
})
const canExport = computed<boolean>(() => {
  return (
    canRead.value &&
    (permissionStore.state.buttonPermissions.sales_inventory_export ||
      permissionStore.state.actions.includes('sales_inventory:export'))
  )
})

const query = reactive({
  order_no: '',
  keyword: '',
  from_date: '',
  to_date: '',
  page: 1,
  page_size: 20,
})

const fulfillmentQuery = reactive({
  item_code: '',
  item_name: '',
  warehouse: '',
})

const formatAmount = (value: string | number | null | undefined): string => {
  if (value === null || value === undefined || value === '') {
    return '-'
  }
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric.toFixed(2) : String(value)
}

const formatPercent = (value: string | number | null | undefined): string => {
  if (value === null || value === undefined || value === '') {
    return '-'
  }
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) {
    return String(value)
  }
  return `${(numeric * 100).toFixed(1)}%`
}

const resolveOrderStatusType = (status: string | null | undefined): 'success' | 'warning' | 'info' => {
  if (status === 'Completed' || status === '已完成') {
    return 'success'
  }
  if (status === 'Draft' || status === 'To Deliver and Bill' || status === '待发货') {
    return 'warning'
  }
  return 'info'
}

const resolveFulfillmentStatus = (value: string | number | null | undefined): { label: string; type: 'success' | 'warning' | 'danger' | 'info' } => {
  const numeric = Number(value)
  if (!Number.isFinite(numeric) || numeric <= 0) {
    return { label: '待加工', type: 'danger' }
  }
  if (numeric >= 1) {
    return { label: '已达成', type: 'success' }
  }
  if (numeric >= 0.6) {
    return { label: '加工中', type: 'warning' }
  }
  return { label: '偏低', type: 'info' }
}

const resetRows = (): void => {
  rows.value = []
  total.value = 0
}

const resetFulfillmentRows = (): void => {
  fulfillmentRows.value = []
}

const applyLocalOrderFilter = (items: SalesOrderListItem[]): SalesOrderListItem[] => {
  const orderNo = query.order_no.trim().toLowerCase()
  if (!orderNo) {
    return items
  }
  return items.filter((item) => String(item.name ?? '').toLowerCase().includes(orderNo))
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
    const result = await fetchSalesInventorySalesOrders({
      order_no: query.order_no.trim() || undefined,
      keyword: query.keyword.trim() || undefined,
      from_date: query.from_date || undefined,
      to_date: query.to_date || undefined,
      page: query.page,
      page_size: query.page_size,
    })
    const filteredItems = applyLocalOrderFilter(result.data.items)
    rows.value = filteredItems
    total.value = query.order_no.trim() ? filteredItems.length : result.data.total
  } catch (error) {
    const message = (error as Error).message
    lastError.value = message
    resetRows()
    ElMessage.error(message)
  } finally {
    loading.value = false
  }
}

const loadFulfillmentRows = async (): Promise<void> => {
  if (!canRead.value) {
    resetFulfillmentRows()
    fulfillmentError.value = ''
    return
  }

  fulfillmentLoading.value = true
  fulfillmentError.value = ''
  try {
    const result = await fetchSalesInventorySalesOrderFulfillment({
      item_code: fulfillmentQuery.item_code.trim() || undefined,
      item_name: fulfillmentQuery.item_name.trim() || undefined,
      warehouse: fulfillmentQuery.warehouse.trim() || undefined,
    })
    fulfillmentRows.value = result.data.items
  } catch (error) {
    const message = (error as Error).message
    fulfillmentError.value = message
    resetFulfillmentRows()
    ElMessage.error(message)
  } finally {
    fulfillmentLoading.value = false
  }
}

const applyPrimaryQuery = (): void => {
  query.page = 1
  void loadRows()
  void loadFulfillmentRows()
}

const resetPrimaryFilters = (): void => {
  query.order_no = ''
  query.keyword = ''
  query.from_date = ''
  query.to_date = ''
  query.page = 1
  query.page_size = defaultPageSize
  fulfillmentQuery.item_code = ''
  fulfillmentQuery.item_name = ''
  fulfillmentQuery.warehouse = ''
  void loadRows()
  void loadFulfillmentRows()
}

const onFulfillmentSearch = (): void => {
  void loadFulfillmentRows()
}

const onFulfillmentReset = (): void => {
  fulfillmentQuery.item_code = ''
  fulfillmentQuery.item_name = ''
  fulfillmentQuery.warehouse = ''
  void loadFulfillmentRows()
}

const onUnavailableAction = (actionName: string): void => {
  ElMessage.warning(`${actionName}功能在本地首版暂未接入，仅保留按钮与状态对齐`)
}

const goDetail = async (name: string): Promise<void> => {
  if (!name) {
    ElMessage.warning('缺少订单编号，无法打开详情')
    return
  }
  try {
    await fetchSalesInventorySalesOrderDetail(name)
  } catch (error) {
    // 详情页仍可继续打开，由详情页承接只读错误提示。
    ElMessage.warning((error as Error).message || '详情数据加载失败')
  } finally {
    void router.push({ path: '/sales-inventory/sales-orders/detail', query: { name } })
  }
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
    await permissionStore.loadModuleActions('sales_inventory')
  } catch (error) {
    ElMessage.error((error as Error).message)
    return
  }
  if (canRead.value) {
    await loadRows()
    await loadFulfillmentRows()
  }
})
</script>

<style scoped>
.sales-inventory-page {
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

.pager {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}

.p1-03-section {
  margin-top: 8px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.state-hint {
  margin-top: 8px;
  color: var(--el-text-color-secondary);
}
</style>
