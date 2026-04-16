<template>
  <div class="sales-inventory-page">
    <el-card shadow="never">
      <template #header>
        <div class="header-row">
          <span>库存汇总与流水只读</span>
        </div>
      </template>

      <el-form :inline="true" :model="query">
        <el-form-item label="物料" required>
          <el-input v-model="query.item_code" clearable placeholder="item_code" />
        </el-form-item>
        <el-form-item label="公司">
          <el-input v-model="query.company" clearable placeholder="company" />
        </el-form-item>
        <el-form-item label="仓库">
          <el-input v-model="query.warehouse" clearable placeholder="warehouse" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :disabled="!canRead" @click="loadRows">查询</el-button>
        </el-form-item>
      </el-form>

      <el-empty v-if="!canRead" description="无销售库存查看权限" />
      <template v-else>
        <el-alert
          v-if="summaryDroppedCount > 0 || ledgerDroppedCount > 0"
          class="scope-alert"
          type="warning"
          :closable="false"
          show-icon
          :title="`有 ${summaryDroppedCount + ledgerDroppedCount} 行因权限范围未展示`"
        />

        <h3>库存汇总</h3>
        <el-table :data="summaryRows" border v-loading="summaryLoading">
          <el-table-column prop="company" label="公司" min-width="130" />
          <el-table-column prop="item_code" label="物料" min-width="150" />
          <el-table-column prop="warehouse" label="仓库" min-width="160" />
          <el-table-column label="结存数量" width="130">
            <template #default="scope">{{ formatAmount(scope.row.balance_qty) }}</template>
          </el-table-column>
          <el-table-column prop="latest_posting_date" label="最近日期" width="120" />
          <el-table-column prop="latest_posting_time" label="最近时间" width="120" />
        </el-table>

        <h3 class="section-title">库存流水</h3>
        <el-table :data="ledgerRows" border v-loading="ledgerLoading">
          <el-table-column prop="posting_date" label="日期" width="120" />
          <el-table-column prop="posting_time" label="时间" width="120" />
          <el-table-column prop="company" label="公司" min-width="130" />
          <el-table-column prop="item_code" label="物料" min-width="150" />
          <el-table-column prop="warehouse" label="仓库" min-width="160" />
          <el-table-column label="本次数量" width="130">
            <template #default="scope">{{ formatAmount(scope.row.actual_qty) }}</template>
          </el-table-column>
          <el-table-column label="结存数量" width="130">
            <template #default="scope">{{ formatAmount(scope.row.qty_after_transaction) }}</template>
          </el-table-column>
          <el-table-column prop="voucher_type" label="凭证类型" min-width="140" />
          <el-table-column prop="voucher_no" label="凭证编号" min-width="160" />
        </el-table>

        <div class="pager">
          <el-pagination
            background
            layout="prev, pager, next, total, sizes"
            :current-page="query.page"
            :page-size="query.page_size"
            :total="ledgerTotal"
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
import { ElMessage } from 'element-plus'
import {
  fetchSalesInventoryStockLedger,
  fetchSalesInventoryStockSummary,
  type StockLedgerItem,
  type StockSummaryItem,
} from '@/api/sales_inventory'
import { usePermissionStore } from '@/stores/permission'

const permissionStore = usePermissionStore()
const summaryLoading = ref<boolean>(false)
const ledgerLoading = ref<boolean>(false)
const summaryRows = ref<StockSummaryItem[]>([])
const ledgerRows = ref<StockLedgerItem[]>([])
const ledgerTotal = ref<number>(0)
const summaryDroppedCount = ref<number>(0)
const ledgerDroppedCount = ref<number>(0)

const canRead = computed<boolean>(() => permissionStore.state.buttonPermissions.sales_inventory_read)

const query = reactive({
  item_code: '',
  company: '',
  warehouse: '',
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
  summaryRows.value = []
  ledgerRows.value = []
  ledgerTotal.value = 0
  summaryDroppedCount.value = 0
  ledgerDroppedCount.value = 0
}

const hasItemCode = (): boolean => Boolean(query.item_code.trim())

const loadRows = async (): Promise<void> => {
  if (!canRead.value) {
    resetRows()
    return
  }
  if (!hasItemCode()) {
    ElMessage.warning('item_code 不能为空')
    resetRows()
    return
  }

  summaryLoading.value = true
  ledgerLoading.value = true
  try {
    const itemCode = query.item_code.trim()
    const [summaryResult, ledgerResult] = await Promise.all([
      fetchSalesInventoryStockSummary(itemCode, {
        company: query.company.trim() || undefined,
        warehouse: query.warehouse.trim() || undefined,
      }),
      fetchSalesInventoryStockLedger(itemCode, {
        company: query.company.trim() || undefined,
        warehouse: query.warehouse.trim() || undefined,
        page: query.page,
        page_size: query.page_size,
      }),
    ])
    summaryRows.value = summaryResult.data.items
    summaryDroppedCount.value = summaryResult.data.dropped_count
    ledgerRows.value = ledgerResult.data.items
    ledgerTotal.value = ledgerResult.data.total
    ledgerDroppedCount.value = ledgerResult.data.dropped_count
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    summaryLoading.value = false
    ledgerLoading.value = false
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

.scope-alert {
  margin-bottom: 12px;
}

.section-title {
  margin-top: 18px;
}

.pager {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}
</style>
