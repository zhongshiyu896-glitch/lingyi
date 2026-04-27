<template>
  <div class="sales-inventory-page">
    <el-card shadow="never">
      <template #header>
        <div class="header-row">
          <span>库存汇总与流水只读</span>
        </div>
      </template>

      <el-form :inline="true" :model="query">
        <el-form-item label="物料">
          <el-input v-model="query.item_code" clearable placeholder="item_code" />
        </el-form-item>
        <el-form-item label="公司">
          <el-input v-model="query.company" clearable placeholder="company" />
        </el-form-item>
        <el-form-item label="仓库">
          <el-input v-model="query.warehouse" clearable placeholder="warehouse" />
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
      </el-form>

      <el-empty v-if="!canRead" description="无销售库存查看权限" />
      <template v-else>
        <el-tabs v-model="activeTab">
          <el-tab-pane label="库存流水" name="ledger">
            <div class="action-row">
              <el-button type="primary" @click="loadRows">查询库存流水</el-button>
            </div>
            <el-alert
              v-if="summaryDroppedCount > 0 || ledgerDroppedCount > 0"
              class="scope-alert"
              type="warning"
              :closable="false"
              show-icon
              :title="`有 ${summaryDroppedCount + ledgerDroppedCount} 行因权限范围未展示`"
            />

            <h3>库存汇总</h3>
            <el-table :data="summaryRows" border v-loading="summaryLoading" empty-text="暂无库存汇总数据，请调整筛选条件后重试">
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
            <el-table :data="ledgerRows" border v-loading="ledgerLoading" empty-text="暂无库存流水数据，请调整筛选条件后重试">
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
          </el-tab-pane>

          <el-tab-pane label="统计分析" name="analysis">
            <div class="action-row">
              <el-button type="primary" @click="loadAnalysis">查询统计分析</el-button>
            </div>

            <h3>库存聚合（按物料+仓库）</h3>
            <el-table
              :data="aggregationRows"
              border
              v-loading="aggregationLoading"
              :row-class-name="aggregationRowClassName"
              empty-text="暂无库存聚合数据，请调整筛选条件后重试"
            >
              <el-table-column prop="item_code" label="物料" min-width="150" />
              <el-table-column prop="warehouse" label="仓库" min-width="160" />
              <el-table-column label="现有库存" width="120">
                <template #default="scope">{{ formatAmount(scope.row.actual_qty) }}</template>
              </el-table-column>
              <el-table-column label="已订购量" width="120">
                <template #default="scope">{{ formatAmount(scope.row.ordered_qty) }}</template>
              </el-table-column>
              <el-table-column label="请购量" width="120">
                <template #default="scope">{{ formatAmount(scope.row.indented_qty) }}</template>
              </el-table-column>
              <el-table-column label="安全库存" width="120">
                <template #default="scope">{{ formatAmount(scope.row.safety_stock) }}</template>
              </el-table-column>
              <el-table-column label="补货阈值" width="120">
                <template #default="scope">{{ formatAmount(scope.row.reorder_level) }}</template>
              </el-table-column>
              <el-table-column label="预警" min-width="160">
                <template #default="scope">
                  <el-tag v-if="scope.row.is_below_safety" type="danger" effect="plain">低于安全库存</el-tag>
                  <el-tag v-if="scope.row.is_below_reorder" type="warning" effect="plain">低于补货阈值</el-tag>
                  <span v-if="!scope.row.is_below_safety && !scope.row.is_below_reorder">正常</span>
                </template>
              </el-table-column>
            </el-table>

            <h3 class="section-title">销售订单满足率</h3>
            <el-table :data="fulfillmentRows" border v-loading="fulfillmentLoading" empty-text="暂无满足率数据，请调整筛选条件后重试">
              <el-table-column prop="sales_order" label="销售订单" min-width="170" />
              <el-table-column prop="item_code" label="物料" min-width="150" />
              <el-table-column prop="warehouse" label="仓库" min-width="160" />
              <el-table-column label="需求数量" width="120">
                <template #default="scope">{{ formatAmount(scope.row.ordered_qty) }}</template>
              </el-table-column>
              <el-table-column label="可用数量" width="120">
                <template #default="scope">{{ formatAmount(scope.row.actual_qty) }}</template>
              </el-table-column>
              <el-table-column label="满足率" width="120">
                <template #default="scope">
                  <el-text :type="toNumber(scope.row.fulfillment_rate) < 1 ? 'danger' : 'success'">
                    {{ formatRate(scope.row.fulfillment_rate) }}
                  </el-text>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>
        </el-tabs>
      </template>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  fetchSalesInventoryAggregation,
  fetchSalesInventorySalesOrderFulfillment,
  fetchSalesInventoryStockLedger,
  fetchSalesInventoryStockSummary,
  type SalesInventoryAggregationItem,
  type SalesOrderFulfillmentItem,
  type StockLedgerItem,
  type StockSummaryItem,
} from '@/api/sales_inventory'
import { usePermissionStore } from '@/stores/permission'

const permissionStore = usePermissionStore()
const activeTab = ref<'ledger' | 'analysis'>('ledger')
const summaryLoading = ref<boolean>(false)
const ledgerLoading = ref<boolean>(false)
const aggregationLoading = ref<boolean>(false)
const fulfillmentLoading = ref<boolean>(false)
const summaryRows = ref<StockSummaryItem[]>([])
const ledgerRows = ref<StockLedgerItem[]>([])
const aggregationRows = ref<SalesInventoryAggregationItem[]>([])
const fulfillmentRows = ref<SalesOrderFulfillmentItem[]>([])
const ledgerTotal = ref<number>(0)
const summaryDroppedCount = ref<number>(0)
const ledgerDroppedCount = ref<number>(0)

const canRead = computed<boolean>(() => permissionStore.state.buttonPermissions.sales_inventory_read)

const query = reactive({
  item_code: '',
  company: '',
  warehouse: '',
  from_date: '',
  to_date: '',
  page: 1,
  page_size: 20,
})

const toNumber = (value: string | number | null | undefined): number => {
  if (value === null || value === undefined || value === '') {
    return 0
  }
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric : 0
}

const formatAmount = (value: string | number | null | undefined): string => {
  if (value === null || value === undefined || value === '') {
    return '-'
  }
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric.toFixed(2) : String(value)
}

const formatRate = (value: string | number | null | undefined): string => {
  const numeric = toNumber(value)
  return `${(numeric * 100).toFixed(2)}%`
}

const resetLedgerRows = (): void => {
  summaryRows.value = []
  ledgerRows.value = []
  ledgerTotal.value = 0
  summaryDroppedCount.value = 0
  ledgerDroppedCount.value = 0
}

const hasItemCode = (): boolean => Boolean(query.item_code.trim())

const loadRows = async (): Promise<void> => {
  if (!canRead.value) {
    resetLedgerRows()
    return
  }
  if (!hasItemCode()) {
    ElMessage.warning('item_code 不能为空')
    resetLedgerRows()
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
        from_date: query.from_date || undefined,
        to_date: query.to_date || undefined,
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

const loadAnalysis = async (): Promise<void> => {
  if (!canRead.value) {
    aggregationRows.value = []
    fulfillmentRows.value = []
    return
  }

  aggregationLoading.value = true
  fulfillmentLoading.value = true
  try {
    const [aggregationResult, fulfillmentResult] = await Promise.all([
      fetchSalesInventoryAggregation({
        company: query.company.trim() || undefined,
        item_code: query.item_code.trim() || undefined,
        warehouse: query.warehouse.trim() || undefined,
      }),
      fetchSalesInventorySalesOrderFulfillment({
        company: query.company.trim() || undefined,
        item_code: query.item_code.trim() || undefined,
        warehouse: query.warehouse.trim() || undefined,
      }),
    ])
    aggregationRows.value = aggregationResult.data.items
    fulfillmentRows.value = fulfillmentResult.data.items
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    aggregationLoading.value = false
    fulfillmentLoading.value = false
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

const aggregationRowClassName = ({ row }: { row: SalesInventoryAggregationItem }): string => {
  if (row.is_below_safety || row.is_below_reorder) {
    return 'warning-row'
  }
  return ''
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

.action-row {
  margin-bottom: 12px;
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

:deep(.warning-row > td) {
  background-color: #fff7e6;
}
</style>
