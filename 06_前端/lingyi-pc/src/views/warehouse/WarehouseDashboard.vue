<template>
  <div class="warehouse-page">
    <el-card shadow="never">
      <template #header>
        <div class="header-row">
          <span>仓库库存台账与预警看板（只读）</span>
          <el-button type="primary" :loading="loading" @click="loadAll">查询</el-button>
        </div>
      </template>

      <el-form :inline="true" :model="query">
        <el-form-item label="公司">
          <el-input v-model="query.company" clearable placeholder="company" />
        </el-form-item>
        <el-form-item label="仓库">
          <el-input v-model="query.warehouse" clearable placeholder="warehouse" />
        </el-form-item>
        <el-form-item label="物料">
          <el-input v-model="query.item_code" clearable placeholder="item_code" />
        </el-form-item>
        <el-form-item label="开始日期">
          <el-date-picker v-model="query.from_date" type="date" value-format="YYYY-MM-DD" clearable />
        </el-form-item>
        <el-form-item label="结束日期">
          <el-date-picker v-model="query.to_date" type="date" value-format="YYYY-MM-DD" clearable />
        </el-form-item>
      </el-form>

      <el-tabs v-model="activeTab">
        <el-tab-pane label="库存台账" name="ledger">
          <el-table :data="ledgerRows" border v-loading="loading">
            <el-table-column prop="company" label="公司" min-width="120" />
            <el-table-column prop="warehouse" label="仓库" min-width="150" />
            <el-table-column prop="item_code" label="物料" min-width="150" />
            <el-table-column prop="posting_date" label="过账日期" width="120" />
            <el-table-column prop="voucher_type" label="凭证类型" min-width="120" />
            <el-table-column prop="voucher_no" label="凭证编号" min-width="140" />
            <el-table-column label="本次数量" width="120">
              <template #default="scope">{{ formatAmount(scope.row.actual_qty) }}</template>
            </el-table-column>
            <el-table-column label="结存数量" width="120">
              <template #default="scope">{{ formatAmount(scope.row.qty_after_transaction) }}</template>
            </el-table-column>
            <el-table-column label="估值单价" width="120">
              <template #default="scope">{{ formatAmount(scope.row.valuation_rate) }}</template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="库存聚合" name="summary">
          <el-table :data="summaryRows" border v-loading="loading" :row-class-name="summaryRowClassName">
            <el-table-column prop="company" label="公司" min-width="120" />
            <el-table-column prop="warehouse" label="仓库" min-width="150" />
            <el-table-column prop="item_code" label="物料" min-width="150" />
            <el-table-column label="现有库存" width="120">
              <template #default="scope">{{ formatAmount(scope.row.actual_qty) }}</template>
            </el-table-column>
            <el-table-column label="预计库存" width="120">
              <template #default="scope">{{ formatAmount(scope.row.projected_qty) }}</template>
            </el-table-column>
            <el-table-column label="预留库存" width="120">
              <template #default="scope">{{ formatAmount(scope.row.reserved_qty) }}</template>
            </el-table-column>
            <el-table-column label="在途库存" width="120">
              <template #default="scope">{{ formatAmount(scope.row.ordered_qty) }}</template>
            </el-table-column>
            <el-table-column label="补货阈值" width="120">
              <template #default="scope">{{ formatAmount(scope.row.reorder_level) }}</template>
            </el-table-column>
            <el-table-column label="安全库存" width="120">
              <template #default="scope">{{ formatAmount(scope.row.safety_stock) }}</template>
            </el-table-column>
            <el-table-column label="阈值状态" min-width="180">
              <template #default="scope">
                <el-tag v-if="scope.row.threshold_missing" type="info" effect="plain">阈值缺失</el-tag>
                <el-tag v-if="scope.row.is_below_reorder" type="warning" effect="plain">低于补货阈值</el-tag>
                <el-tag v-if="scope.row.is_below_safety" type="danger" effect="plain">低于安全库存</el-tag>
                <span v-if="!scope.row.threshold_missing && !scope.row.is_below_reorder && !scope.row.is_below_safety">正常</span>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="库存预警" name="alerts">
          <div class="alert-filter">
            <el-radio-group v-model="query.alert_type" @change="loadAlertsOnly">
              <el-radio-button label="">全部</el-radio-button>
              <el-radio-button label="low_stock">低库存</el-radio-button>
              <el-radio-button label="below_safety">安全库存不足</el-radio-button>
              <el-radio-button label="overstock">超储</el-radio-button>
              <el-radio-button label="stale_stock">呆滞</el-radio-button>
            </el-radio-group>
          </div>
          <el-table :data="alertsRows" border v-loading="loading" :row-class-name="alertRowClassName">
            <el-table-column prop="company" label="公司" min-width="120" />
            <el-table-column prop="warehouse" label="仓库" min-width="150" />
            <el-table-column prop="item_code" label="物料" min-width="150" />
            <el-table-column prop="alert_type" label="预警类型" width="130" />
            <el-table-column label="当前库存" width="120">
              <template #default="scope">{{ formatAmount(scope.row.current_qty) }}</template>
            </el-table-column>
            <el-table-column label="阈值" width="120">
              <template #default="scope">{{ formatAmount(scope.row.threshold_qty) }}</template>
            </el-table-column>
            <el-table-column label="差值" width="120">
              <template #default="scope">{{ formatAmount(scope.row.gap_qty) }}</template>
            </el-table-column>
            <el-table-column prop="last_movement_date" label="最近异动" width="130" />
            <el-table-column prop="severity" label="严重度" width="100" />
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  fetchWarehouseAlerts,
  fetchWarehouseStockLedger,
  fetchWarehouseStockSummary,
  type WarehouseAlertItem,
  type WarehouseStockLedgerItem,
  type WarehouseStockSummaryItem,
} from '@/api/warehouse'

const loading = ref<boolean>(false)
const activeTab = ref<'ledger' | 'summary' | 'alerts'>('ledger')
const ledgerRows = ref<WarehouseStockLedgerItem[]>([])
const summaryRows = ref<WarehouseStockSummaryItem[]>([])
const alertsRows = ref<WarehouseAlertItem[]>([])

const query = reactive({
  company: '',
  warehouse: '',
  item_code: '',
  from_date: '',
  to_date: '',
  page: 1,
  page_size: 50,
  alert_type: '',
})

const formatAmount = (value: string | number | null | undefined): string => {
  if (value === null || value === undefined || value === '') {
    return '-'
  }
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric.toFixed(2) : String(value)
}

const normalizeQuery = () => ({
  company: query.company.trim() || undefined,
  warehouse: query.warehouse.trim() || undefined,
  item_code: query.item_code.trim() || undefined,
  from_date: query.from_date || undefined,
  to_date: query.to_date || undefined,
})

const loadAll = async (): Promise<void> => {
  loading.value = true
  try {
    const normalized = normalizeQuery()
    const [ledgerResult, summaryResult, alertsResult] = await Promise.all([
      fetchWarehouseStockLedger({
        ...normalized,
        page: query.page,
        page_size: query.page_size,
      }),
      fetchWarehouseStockSummary(normalized),
      fetchWarehouseAlerts({ ...normalized, alert_type: query.alert_type as '' | 'low_stock' | 'below_safety' | 'overstock' | 'stale_stock' }),
    ])
    ledgerRows.value = ledgerResult.data.items
    summaryRows.value = summaryResult.data.items
    alertsRows.value = alertsResult.data.items
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    loading.value = false
  }
}

const loadAlertsOnly = async (): Promise<void> => {
  loading.value = true
  try {
    const normalized = normalizeQuery()
    const alertsResult = await fetchWarehouseAlerts({
      ...normalized,
      alert_type: query.alert_type as '' | 'low_stock' | 'below_safety' | 'overstock' | 'stale_stock',
    })
    alertsRows.value = alertsResult.data.items
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    loading.value = false
  }
}

const summaryRowClassName = ({ row }: { row: WarehouseStockSummaryItem }): string => {
  if (row.is_below_reorder || row.is_below_safety) {
    return 'warning-row'
  }
  return ''
}

const alertRowClassName = ({ row }: { row: WarehouseAlertItem }): string => {
  if (row.severity === 'high') {
    return 'danger-row'
  }
  if (row.severity === 'medium') {
    return 'warning-row'
  }
  return ''
}

onMounted(() => {
  loadAll()
})
</script>

<style scoped>
.warehouse-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.alert-filter {
  margin-bottom: 12px;
}

:deep(.warning-row > td) {
  background-color: #fff7e6;
}

:deep(.danger-row > td) {
  background-color: #fff1f0;
}
</style>
