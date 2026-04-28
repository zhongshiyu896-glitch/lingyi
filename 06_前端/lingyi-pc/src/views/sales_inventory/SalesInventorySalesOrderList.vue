<template>
  <div class="sales-inventory-page">
    <el-card shadow="never">
      <template #header>
        <div class="header-row">
          <span>销售订单只读列表</span>
        </div>
      </template>

      <el-form :inline="true" :model="query">
        <el-form-item label="公司">
          <el-input v-model="query.company" clearable placeholder="company" />
        </el-form-item>
        <el-form-item label="客户">
          <el-input v-model="query.customer" clearable placeholder="customer" />
        </el-form-item>
        <el-form-item label="物料">
          <el-input v-model="query.item_code" clearable placeholder="item_code" />
        </el-form-item>
        <el-form-item label="物料名称">
          <el-input v-model="query.item_name" clearable placeholder="item_name" />
        </el-form-item>
        <el-form-item label="开始日期">
          <el-date-picker
            v-model="query.from_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="from_date"
            clearable
          />
        </el-form-item>
        <el-form-item label="结束日期">
          <el-date-picker
            v-model="query.to_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="to_date"
            clearable
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :disabled="!canRead" @click="loadRows">查询</el-button>
        </el-form-item>
      </el-form>

      <el-empty v-if="!canRead" description="无销售库存查看权限" />
      <template v-else>
        <el-table :data="rows" border empty-text="暂无销售订单数据" v-loading="loading">
          <el-table-column prop="name" label="销售订单" min-width="180" />
          <el-table-column prop="company" label="公司" min-width="130" />
          <el-table-column prop="customer" label="客户" min-width="150" />
          <el-table-column prop="transaction_date" label="订单日期" width="120" />
          <el-table-column prop="delivery_date" label="交付日期" width="120" />
          <el-table-column prop="status" label="状态" min-width="120" />
          <el-table-column prop="docstatus" label="docstatus" width="110" />
          <el-table-column label="总额" width="130">
            <template #default="scope">{{ formatAmount(scope.row.grand_total) }}</template>
          </el-table-column>
          <el-table-column prop="currency" label="币种" width="100" />
          <el-table-column label="查看" fixed="right" width="100">
            <template #default="scope">
              <el-button link type="primary" @click="goDetail(scope.row.name)">详情</el-button>
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

const canRead = computed<boolean>(() => permissionStore.state.buttonPermissions.sales_inventory_read)

const query = reactive({
  company: '',
  customer: '',
  item_code: '',
  item_name: '',
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

const loadRows = async (): Promise<void> => {
  if (!canRead.value) {
    resetRows()
    return
  }

  loading.value = true
  try {
    const result = await fetchSalesInventorySalesOrders({
      company: query.company.trim() || undefined,
      customer: query.customer.trim() || undefined,
      item_code: query.item_code.trim() || undefined,
      item_name: query.item_name.trim() || undefined,
      from_date: query.from_date || undefined,
      to_date: query.to_date || undefined,
      page: query.page,
      page_size: query.page_size,
    })
    rows.value = result.data.items
    total.value = result.data.total
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    loading.value = false
  }
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

.pager {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}
</style>
