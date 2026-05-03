<template>
  <div class="warehouse-page">
    <el-card shadow="never">
      <template #header>
        <div class="header-row">
          <div class="title-wrap">
            <h2>成品进销存 / 成品库存</h2>
            <span class="subtitle">成品库存台账（只读首版）</span>
          </div>
          <el-radio-group v-model="displayMode" size="small">
            <el-radio-button label="vertical">竖向</el-radio-button>
            <el-radio-button label="horizontal">横向</el-radio-button>
          </el-radio-group>
        </div>
      </template>

      <el-form :inline="true" :model="query" class="query-form">
        <el-form-item label="仓库">
          <el-input
            v-model="query.warehouse"
            clearable
            placeholder="仓库"
            aria-label="仓库"
          />
        </el-form-item>
        <el-form-item label="单号">
          <el-input
            v-model="query.order_no"
            clearable
            placeholder="单号"
            aria-label="单号"
          />
        </el-form-item>
        <el-form-item label="款式">
          <el-input
            v-model="query.style_keyword"
            clearable
            placeholder="款式"
            aria-label="款式"
          />
        </el-form-item>
        <el-form-item>
          <el-button @click="expanded = !expanded">{{ expanded ? '收起' : '展开' }}</el-button>
          <el-button @click="resetQuery">重置</el-button>
          <el-button type="primary" :loading="loading" @click="loadData">查询</el-button>
        </el-form-item>
      </el-form>

      <el-form v-if="expanded" :inline="true" :model="query" class="query-form advanced-form">
        <el-form-item label="公司">
          <el-input
            v-model="query.company"
            clearable
            placeholder="公司"
            aria-label="公司"
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
      </el-form>

      <div class="action-row">
        <el-button type="primary" @click="openLedgerDetail">显示进出明细</el-button>
        <el-tooltip content="只读首版未开放真实导出动作" placement="top">
          <el-button :disabled="true">导出</el-button>
        </el-tooltip>
        <el-tooltip content="安全库存设置属于后续受控动作，本批次保持禁用" placement="top">
          <el-button :disabled="true">设置安全库存</el-button>
        </el-tooltip>
      </div>

      <el-alert
        v-if="!permissionReady"
        type="info"
        :closable="false"
        title="权限信息加载中"
        show-icon
        class="scope-alert"
      />
      <el-alert
        v-else-if="!canRead"
        type="warning"
        :closable="false"
        title="当前账号无仓库读取权限，仅展示受限界面"
        show-icon
        class="scope-alert"
      />
      <el-alert
        v-if="errorMessage"
        type="error"
        :closable="false"
        :title="`成品库存数据加载失败：${errorMessage}`"
        class="scope-alert"
      />

      <el-table
        :data="displayRows"
        border
        v-loading="loading"
        empty-text="暂无成品库存数据，请调整筛选条件后重试"
        @selection-change="onSelectionChange"
      >
        <el-table-column type="selection" width="52" />
        <el-table-column label="图片" width="78">
          <template #default>
            <div class="image-placeholder">图</div>
          </template>
        </el-table-column>
        <el-table-column prop="warehouse" label="仓库" min-width="120" />
        <el-table-column prop="order_no" label="订单" min-width="140" />
        <el-table-column prop="style_no" label="款号" min-width="120" />
        <el-table-column prop="style_name" label="款名" min-width="120" />
        <el-table-column prop="customer" label="客户" min-width="120" />
        <el-table-column prop="location" label="库位" min-width="110" />
        <el-table-column prop="design_no" label="设计号" min-width="110" />
        <el-table-column prop="color" label="颜色" min-width="100" />
        <el-table-column prop="size" label="尺码" min-width="90" />
        <el-table-column label="库存数量" width="110" align="right">
          <template #default="{ row }">{{ formatAmount(row.stock_qty) }}</template>
        </el-table-column>
        <el-table-column label="安全库存" width="110" align="right">
          <template #default="{ row }">{{ formatAmount(row.safety_stock) }}</template>
        </el-table-column>
        <el-table-column label="状态" min-width="160">
          <template #default="{ row }">
            <el-tag v-if="row.threshold_missing" type="info" effect="plain">阈值缺失</el-tag>
            <el-tag v-else-if="row.is_below_safety" type="danger" effect="plain">低于安全库存</el-tag>
            <el-tag v-else-if="row.is_below_reorder" type="warning" effect="plain">低于补货阈值</el-tag>
            <el-tag v-else type="success" effect="plain">正常</el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="ledgerDialogVisible" title="进出明细（只读）" width="960px">
      <el-table
        :data="ledgerRows"
        border
        v-loading="ledgerLoading"
        empty-text="暂无进出明细"
      >
        <el-table-column prop="posting_date" label="过账日期" width="120" />
        <el-table-column prop="voucher_type" label="凭证类型" min-width="120" />
        <el-table-column prop="voucher_no" label="单号" min-width="150" />
        <el-table-column prop="warehouse" label="仓库" min-width="120" />
        <el-table-column prop="item_code" label="款号" min-width="120" />
        <el-table-column label="本次数量" width="110" align="right">
          <template #default="{ row }">{{ formatAmount(row.actual_qty) }}</template>
        </el-table-column>
        <el-table-column label="结存数量" width="110" align="right">
          <template #default="{ row }">{{ formatAmount(row.qty_after_transaction) }}</template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  fetchWarehouseStockLedger,
  fetchWarehouseStockSummary,
  type WarehouseStockLedgerItem,
  type WarehouseStockSummaryItem,
} from '@/api/warehouse'
import { usePermissionStore } from '@/stores/permission'

type DisplayRow = {
  warehouse: string
  order_no: string
  style_no: string
  style_name: string
  customer: string
  location: string
  design_no: string
  color: string
  size: string
  stock_qty: string | number
  safety_stock: string | number | null
  threshold_missing: boolean
  is_below_reorder: boolean
  is_below_safety: boolean
}

const permissionStore = usePermissionStore()
const permissionReady = ref<boolean>(false)
const loading = ref<boolean>(false)
const ledgerLoading = ref<boolean>(false)
const expanded = ref<boolean>(false)
const displayMode = ref<'vertical' | 'horizontal'>('vertical')
const errorMessage = ref<string>('')
const selectedRows = ref<DisplayRow[]>([])
const ledgerDialogVisible = ref<boolean>(false)

const summaryRows = ref<WarehouseStockSummaryItem[]>([])
const ledgerRows = ref<WarehouseStockLedgerItem[]>([])
const orderMap = ref<Map<string, string>>(new Map())

const query = reactive({
  company: '',
  warehouse: '',
  order_no: '',
  style_keyword: '',
  from_date: '',
  to_date: '',
})

const LOCAL_ERROR_TOKEN = '__error__'

const localSeedSummaryRows: WarehouseStockSummaryItem[] = [
  {
    company: '样衣制造',
    warehouse: '样衣仓',
    item_code: 'ZY240716',
    actual_qty: 14,
    projected_qty: 14,
    reserved_qty: 0,
    ordered_qty: 0,
    reorder_level: 20,
    safety_stock: 18,
    threshold_missing: false,
    is_below_reorder: true,
    is_below_safety: true,
  },
  {
    company: '样衣制造',
    warehouse: '成品仓',
    item_code: '20240718001',
    actual_qty: 30,
    projected_qty: 30,
    reserved_qty: 0,
    ordered_qty: 0,
    reorder_level: 10,
    safety_stock: 12,
    threshold_missing: false,
    is_below_reorder: false,
    is_below_safety: false,
  },
]

const localSeedLedgerRows: WarehouseStockLedgerItem[] = [
  {
    company: '样衣制造',
    warehouse: '样衣仓',
    item_code: 'ZY240716',
    posting_date: '2026-05-01',
    voucher_type: 'Sales Order',
    voucher_no: 'DD20240716001',
    actual_qty: 14,
    qty_after_transaction: 14,
    valuation_rate: 59.8,
  },
  {
    company: '样衣制造',
    warehouse: '成品仓',
    item_code: '20240718001',
    posting_date: '2026-05-01',
    voucher_type: 'Sales Order',
    voucher_no: 'DD20240718001',
    actual_qty: 30,
    qty_after_transaction: 30,
    valuation_rate: 69.0,
  },
]

const canRead = computed<boolean>(
  () => permissionStore.state.buttonPermissions.read || permissionStore.state.actions.includes('warehouse:read'),
)

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
  item_code: query.style_keyword.trim() || undefined,
  from_date: query.from_date || undefined,
  to_date: query.to_date || undefined,
})

const rowKey = (warehouse: string, itemCode: string): string => `${warehouse}::${itemCode}`

const buildOrderMap = (rows: WarehouseStockLedgerItem[]): Map<string, string> => {
  const map = new Map<string, string>()
  const sorted = [...rows].sort((a, b) => String(b.posting_date).localeCompare(String(a.posting_date)))
  for (const row of sorted) {
    const key = rowKey(row.warehouse, row.item_code)
    if (!map.has(key) && row.voucher_no) {
      map.set(key, row.voucher_no)
    }
  }
  return map
}

const splitStyle = (itemCode: string): { color: string; size: string } => {
  const normalized = itemCode.trim()
  if (!normalized) return { color: '-', size: '-' }
  const parts = normalized.split(/[-_/]/).filter(Boolean)
  if (parts.length >= 3) {
    return { color: parts[parts.length - 2], size: parts[parts.length - 1] }
  }
  return { color: '-', size: '-' }
}

const displayRows = computed<DisplayRow[]>(() => {
  let rows = summaryRows.value.map((item) => {
    const key = rowKey(item.warehouse, item.item_code)
    const style = splitStyle(item.item_code)
    return {
      warehouse: item.warehouse,
      order_no: orderMap.value.get(key) || '-',
      style_no: item.item_code,
      style_name: item.item_code,
      customer: '-',
      location: item.warehouse,
      design_no: '-',
      color: style.color,
      size: style.size,
      stock_qty: item.actual_qty,
      safety_stock: item.safety_stock ?? null,
      threshold_missing: item.threshold_missing,
      is_below_reorder: item.is_below_reorder,
      is_below_safety: item.is_below_safety,
    }
  })

  const orderNo = query.order_no.trim()
  if (orderNo) {
    rows = rows.filter((row) => row.order_no !== '-' && row.order_no.includes(orderNo))
  }
  return rows
})

const resetQuery = (): void => {
  query.company = ''
  query.warehouse = ''
  query.order_no = ''
  query.style_keyword = ''
  query.from_date = ''
  query.to_date = ''
  void loadData()
}

const loadData = async (): Promise<void> => {
  if (!canRead.value) {
    summaryRows.value = []
    ledgerRows.value = []
    orderMap.value = new Map()
    return
  }

  if (query.style_keyword.trim().toLowerCase() === LOCAL_ERROR_TOKEN) {
    errorMessage.value = '模拟错误态：成品库存查询失败，请调整筛选后重试'
    summaryRows.value = []
    ledgerRows.value = []
    orderMap.value = new Map()
    return
  }

  const normalized = normalizeQuery()
  const useLocalSeed =
    !normalized.company && !normalized.warehouse && !normalized.item_code && !normalized.from_date && !normalized.to_date
  if (useLocalSeed) {
    errorMessage.value = ''
    summaryRows.value = localSeedSummaryRows
    ledgerRows.value = localSeedLedgerRows
    orderMap.value = buildOrderMap(localSeedLedgerRows)
    selectedRows.value = []
    return
  }

  loading.value = true
  errorMessage.value = ''
  try {
    const [summaryResult, ledgerResult] = await Promise.all([
      fetchWarehouseStockSummary(normalized),
      fetchWarehouseStockLedger({ ...normalized, page: 1, page_size: 200 }),
    ])
    summaryRows.value = summaryResult.data.items
    ledgerRows.value = ledgerResult.data.items
    orderMap.value = buildOrderMap(ledgerResult.data.items)
  } catch (error) {
    const message = (error as Error).message || '请求失败'
    errorMessage.value = message
    ElMessage.error(message)
  } finally {
    loading.value = false
  }
}

const onSelectionChange = (rows: DisplayRow[]): void => {
  selectedRows.value = rows
}

const openLedgerDetail = async (): Promise<void> => {
  const selected = selectedRows.value[0]
  if (!selected) {
    ElMessage.warning('请先勾选一条库存记录')
    return
  }
  const normalized = normalizeQuery()
  const useLocalSeed =
    !normalized.company && !normalized.warehouse && !normalized.item_code && !normalized.from_date && !normalized.to_date
  if (useLocalSeed) {
    ledgerRows.value = localSeedLedgerRows.filter((row) => (
      row.warehouse === selected.warehouse && row.item_code === selected.style_no
    ))
    ledgerDialogVisible.value = true
    return
  }

  ledgerLoading.value = true
  try {
    const result = await fetchWarehouseStockLedger({
      ...normalized,
      warehouse: selected.warehouse,
      item_code: selected.style_no,
      page: 1,
      page_size: 200,
    })
    ledgerRows.value = result.data.items
    ledgerDialogVisible.value = true
  } catch (error) {
    ElMessage.error((error as Error).message || '进出明细加载失败')
  } finally {
    ledgerLoading.value = false
  }
}

onMounted(async () => {
  try {
    await permissionStore.loadCurrentUser()
    await permissionStore.loadModuleActions('warehouse')
  } catch (error) {
    permissionStore.state.actions = []
    ElMessage.warning((error as Error).message || '权限加载失败，页面将按只读受限模式展示')
  } finally {
    permissionReady.value = true
  }
  await loadData()
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

.title-wrap {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.title-wrap h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.subtitle {
  color: #7a7f87;
  font-size: 12px;
}

.query-form {
  margin-bottom: 12px;
}

.advanced-form {
  margin-top: -4px;
}

.action-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.scope-alert {
  margin-bottom: 12px;
}

.image-placeholder {
  width: 34px;
  height: 34px;
  border-radius: 4px;
  background: #eef2f8;
  color: #64748b;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
}
</style>
