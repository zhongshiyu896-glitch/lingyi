<template>
  <div class="sales-inventory-page">
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

      <el-form :inline="true" :model="query" class="query-form">
        <el-form-item label="订单号">
          <el-input
            v-model="query.order_no"
            clearable
            placeholder="订单号"
            @keyup.enter="onSearch"
          />
        </el-form-item>
        <el-form-item label="关键词">
          <el-input
            v-model="query.keyword"
            clearable
            placeholder="款号/款名/客户款号"
            @keyup.enter="onSearch"
          />
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
        <el-button @click="onUnavailableAction('筛选')">筛选</el-button>
        <el-button type="primary" :disabled="!canRead" @click="onUnavailableAction('新建')">新建</el-button>
        <el-button :disabled="!canRead" @click="onUnavailableAction('下单')">下单</el-button>
        <el-button :disabled="!canRead" @click="onUnavailableAction('获取订单')">获取订单</el-button>
        <el-button :disabled="!canRead" @click="onUnavailableAction('导入')">导入</el-button>
        <el-button :disabled="!canExport" @click="onUnavailableAction('导出')">导出</el-button>
      </div>

      <el-alert
        v-if="lastError"
        class="error-alert"
        type="error"
        :closable="false"
        :title="`订单列表加载失败：${lastError}`"
      />

      <el-empty v-if="!canRead" description="无销售库存查看权限" />
      <template v-else>
        <el-table
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
          <el-table-column prop="status" label="状态" min-width="120" />
          <el-table-column label="数量/金额" min-width="130">
            <template #default="scope">{{ formatAmount(scope.row.grand_total) }}</template>
          </el-table-column>
          <el-table-column prop="currency" label="币种" width="100" />
          <el-table-column label="操作" fixed="right" min-width="230">
            <template #default="scope">
              <el-button link type="primary" @click="onUnavailableAction('进度')">进度</el-button>
              <el-button link type="primary" @click="goDetail(scope.row.name)">详情</el-button>
              <el-button link type="primary" @click="onUnavailableAction('打印')">打印</el-button>
              <el-button link type="primary" @click="onUnavailableAction('更多')">更多</el-button>
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
import {
  fetchSalesInventorySalesOrders,
  type SalesOrderListItem,
} from '@/api/sales_inventory'
import { usePermissionStore } from '@/stores/permission'

const router = useRouter()
const permissionStore = usePermissionStore()
const loading = ref<boolean>(false)
const rows = ref<SalesOrderListItem[]>([])
const total = ref<number>(0)
const lastError = ref<string>('')

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

const formatAmount = (value: string | number | null | undefined): string => {
  if (value === null || value === undefined || value === '') {
    return '-'
  }
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric.toFixed(2) : String(value)
}

const resetRows = (): void => {
  rows.value = []
  total.value = 0
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

const onSearch = (): void => {
  query.page = 1
  void loadRows()
}

const onReset = (): void => {
  query.order_no = ''
  query.keyword = ''
  query.from_date = ''
  query.to_date = ''
  query.page = 1
  query.page_size = 20
  void loadRows()
}

const onUnavailableAction = (actionName: string): void => {
  ElMessage.warning(`${actionName}功能在本地首版暂未接入，仅保留按钮与状态对齐`)
}

const goDetail = (name: string): void => {
  router.push({ path: '/sales-inventory/sales-orders/detail', query: { name } })
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
</style>
