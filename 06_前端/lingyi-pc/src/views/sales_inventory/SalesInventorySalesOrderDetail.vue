<template>
  <div class="sales-inventory-page">
    <el-card shadow="never">
      <template #header>
        <div class="header-row">
          <span>销售订单只读详情</span>
          <el-button @click="backToList">返回列表</el-button>
        </div>
      </template>

      <el-empty v-if="!canRead" description="无销售库存查看权限" />
      <el-empty v-else-if="!orderName" description="缺少销售订单编号" />
      <template v-else>
        <el-descriptions v-if="detail" :column="3" border>
          <el-descriptions-item label="销售订单">{{ detail.name }}</el-descriptions-item>
          <el-descriptions-item label="公司">{{ detail.company }}</el-descriptions-item>
          <el-descriptions-item label="客户">{{ detail.customer || '-' }}</el-descriptions-item>
          <el-descriptions-item label="订单日期">{{ detail.transaction_date || '-' }}</el-descriptions-item>
          <el-descriptions-item label="交付日期">{{ detail.delivery_date || '-' }}</el-descriptions-item>
          <el-descriptions-item label="状态">{{ detail.status || '-' }}</el-descriptions-item>
          <el-descriptions-item label="docstatus">{{ detail.docstatus }}</el-descriptions-item>
          <el-descriptions-item label="总额">{{ formatAmount(detail.grand_total) }}</el-descriptions-item>
          <el-descriptions-item label="币种">{{ detail.currency || '-' }}</el-descriptions-item>
        </el-descriptions>

        <el-table
          class="detail-table"
          :data="detail?.items || []"
          border
          empty-text="暂无销售订单明细"
          v-loading="loading"
        >
          <el-table-column prop="item_code" label="物料" min-width="150" />
          <el-table-column prop="item_name" label="物料名称" min-width="180" />
          <el-table-column label="数量" width="120">
            <template #default="scope">{{ formatAmount(scope.row.qty) }}</template>
          </el-table-column>
          <el-table-column label="已交付数量" width="130">
            <template #default="scope">{{ formatAmount(scope.row.delivered_qty) }}</template>
          </el-table-column>
          <el-table-column label="单价" width="120">
            <template #default="scope">{{ formatAmount(scope.row.rate) }}</template>
          </el-table-column>
          <el-table-column label="金额" width="130">
            <template #default="scope">{{ formatAmount(scope.row.amount) }}</template>
          </el-table-column>
          <el-table-column prop="warehouse" label="仓库" min-width="150" />
          <el-table-column prop="delivery_date" label="交付日期" width="120" />
        </el-table>
      </template>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  fetchSalesInventorySalesOrderDetail,
  type SalesOrderDetailData,
} from '@/api/sales_inventory'
import { usePermissionStore } from '@/stores/permission'

const route = useRoute()
const router = useRouter()
const permissionStore = usePermissionStore()
const loading = ref<boolean>(false)
const detail = ref<SalesOrderDetailData | null>(null)

const canRead = computed<boolean>(() => permissionStore.state.buttonPermissions.sales_inventory_read)
const orderName = computed<string>(() => String(route.query.name || '').trim())

const formatAmount = (value: string | number | null | undefined): string => {
  if (value === null || value === undefined || value === '') {
    return '-'
  }
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric.toFixed(2) : String(value)
}

const loadDetail = async (): Promise<void> => {
  if (!canRead.value || !orderName.value) {
    detail.value = null
    return
  }

  loading.value = true
  try {
    const result = await fetchSalesInventorySalesOrderDetail(orderName.value)
    detail.value = result.data
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    loading.value = false
  }
}

const backToList = (): void => {
  router.push({ path: '/sales-inventory/sales-orders' })
}

onMounted(async () => {
  try {
    await permissionStore.loadCurrentUser()
    await permissionStore.loadModuleActions('sales_inventory')
  } catch (error) {
    ElMessage.error((error as Error).message)
    return
  }
  await loadDetail()
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

.detail-table {
  margin-top: 16px;
}
</style>
