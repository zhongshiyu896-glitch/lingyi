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

      <div class="warehouse-management-section">
        <div class="management-header">
          <div class="title-wrap">
            <h3>基础资料 / 仓库管理</h3>
            <span class="subtitle">仓库目录（P1 首版，只读增强）</span>
          </div>
          <div class="management-actions">
            <el-button :disabled="!canRead" @click="applyManagementFilters">查询管理</el-button>
            <el-button :disabled="!canRead" @click="guardedAction('新增仓库')">新增仓库</el-button>
            <el-button :disabled="!canRead" @click="guardedAction('编辑仓库')">编辑仓库</el-button>
            <el-button :disabled="!canRead" @click="guardedAction('停用仓库')">停用仓库</el-button>
            <el-button :disabled="!canRead" @click="guardedAction('导出仓库目录')">导出</el-button>
          </div>
        </div>

        <el-form :inline="true" :model="query" class="management-filter-form">
          <el-form-item label="仓库关键字">
            <el-input
              v-model="query.management_keyword"
              clearable
              placeholder="仓库关键字"
              aria-label="仓库关键字"
            />
          </el-form-item>
          <el-form-item label="状态">
            <el-select
              v-model="query.management_status"
              clearable
              placeholder="状态"
              aria-label="仓库状态"
              style="width: 140px"
            >
              <el-option label="正常" value="normal" />
              <el-option label="预警" value="warning" />
              <el-option label="停用" value="disabled" />
            </el-select>
          </el-form-item>
        </el-form>

        <el-alert
          v-if="managementErrorMessage"
          type="error"
          :closable="false"
          :title="`仓库管理目录加载失败：${managementErrorMessage}`"
          class="scope-alert"
        />

        <el-empty
          v-if="managementDisplayRows.length === 0 && !managementErrorMessage"
          description="暂无仓库管理目录数据，请调整筛选条件后重试"
        />

        <el-table
          v-else
          :data="managementDisplayRows"
          border
          empty-text="暂无仓库管理目录数据"
          class="management-table"
        >
          <el-table-column prop="warehouse_code" label="仓库编码" min-width="120" />
          <el-table-column prop="warehouse_name" label="仓库名称" min-width="140" />
          <el-table-column prop="warehouse_type" label="类型" min-width="110" />
          <el-table-column prop="manager" label="负责人" min-width="110" />
          <el-table-column label="库存能力" min-width="160">
            <template #default="{ row }">
              {{ formatAmount(row.used_qty) }} / {{ formatAmount(row.capacity_qty) }}
            </template>
          </el-table-column>
          <el-table-column label="利用率" min-width="100">
            <template #default="{ row }">{{ formatPercent(row.utilization_rate) }}</template>
          </el-table-column>
          <el-table-column label="状态" min-width="100">
            <template #default="{ row }">
              <el-tag :type="managementStatusTag(row.status)" effect="plain">
                {{ managementStatusText(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" min-width="180" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="viewWarehouse(row)">查看</el-button>
              <el-button link type="warning" @click="guardedAction(`编辑仓库(${row.warehouse_code})`)">编辑</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div class="material-inventory-section">
        <div class="material-header">
          <div class="title-wrap">
            <h3>物料进销存 / 物料库存（TASK-Y22B-P1-05）</h3>
            <span class="subtitle">共享路由首版（只读语义）</span>
          </div>
          <div class="material-actions">
            <el-button :disabled="!canRead" @click="applyMaterialFilters">查询物料</el-button>
            <el-button :disabled="!canRead" @click="guardedAction('库存调拨')">调拨</el-button>
            <el-button :disabled="!canRead" @click="guardedAction('库存盘点')">盘点</el-button>
            <el-button :disabled="!canRead" @click="guardedAction('导出物料库存')">导出</el-button>
          </div>
        </div>

        <el-form :inline="true" :model="query" class="material-filter-form">
          <el-form-item label="物料关键字">
            <el-input
              v-model="query.material_keyword"
              clearable
              placeholder="物料编码/名称"
              aria-label="物料关键字"
            />
          </el-form-item>
          <el-form-item label="分类">
            <el-select
              v-model="query.material_category"
              clearable
              placeholder="分类"
              aria-label="物料分类"
              style="width: 130px"
            >
              <el-option label="面料" value="面料" />
              <el-option label="辅料" value="辅料" />
              <el-option label="包材" value="包材" />
              <el-option label="综合物料" value="综合物料" />
            </el-select>
          </el-form-item>
          <el-form-item label="仓库">
            <el-input
              v-model="query.material_warehouse"
              clearable
              placeholder="仓库"
              aria-label="物料仓库"
            />
          </el-form-item>
          <el-form-item label="库位">
            <el-input
              v-model="query.material_location"
              clearable
              placeholder="库位"
              aria-label="物料库位"
            />
          </el-form-item>
          <el-form-item label="状态">
            <el-select
              v-model="query.material_status"
              clearable
              placeholder="状态"
              aria-label="物料库存状态"
              style="width: 120px"
            >
              <el-option label="正常" value="normal" />
              <el-option label="预警" value="warning" />
              <el-option label="停用" value="disabled" />
            </el-select>
          </el-form-item>
        </el-form>

        <el-alert
          v-if="materialErrorMessage"
          type="error"
          :closable="false"
          :title="`物料库存加载失败：${materialErrorMessage}`"
          class="scope-alert"
        />

        <el-empty
          v-if="materialDisplayRows.length === 0 && !materialErrorMessage"
          description="暂无物料库存数据，请调整筛选条件后重试"
        />

        <el-table
          v-else
          :data="materialDisplayRows"
          border
          empty-text="暂无物料库存数据"
          class="material-table"
        >
          <el-table-column prop="material_code" label="物料编码" min-width="130" />
          <el-table-column prop="material_name" label="物料名称" min-width="150" />
          <el-table-column prop="material_category" label="分类" min-width="110" />
          <el-table-column prop="warehouse" label="仓库" min-width="120" />
          <el-table-column prop="location" label="库位" min-width="100" />
          <el-table-column label="库存数量" min-width="110" align="right">
            <template #default="{ row }">{{ formatAmount(row.qty) }}</template>
          </el-table-column>
          <el-table-column label="库存金额" min-width="130" align="right">
            <template #default="{ row }">{{ formatAmount(row.amount) }}</template>
          </el-table-column>
          <el-table-column label="状态" min-width="100">
            <template #default="{ row }">
              <el-tag :type="materialStatusTag(row.status)" effect="plain">
                {{ materialStatusText(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" min-width="180" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="viewMaterial(row)">查看</el-button>
              <el-button link type="warning" @click="guardedAction(`调拨物料(${row.material_code})`)">调拨</el-button>
            </template>
          </el-table-column>
        </el-table>
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
  type WarehouseMaterialInventoryItem,
  type WarehouseManagementItem,
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
const managementErrorMessage = ref<string>('')
const materialErrorMessage = ref<string>('')
const selectedRows = ref<DisplayRow[]>([])
const ledgerDialogVisible = ref<boolean>(false)

const summaryRows = ref<WarehouseStockSummaryItem[]>([])
const managementRows = ref<WarehouseManagementItem[]>([])
const materialRows = ref<WarehouseMaterialInventoryItem[]>([])
const ledgerRows = ref<WarehouseStockLedgerItem[]>([])
const orderMap = ref<Map<string, string>>(new Map())

const query = reactive({
  company: '',
  warehouse: '',
  order_no: '',
  style_keyword: '',
  management_keyword: '',
  management_status: '',
  material_keyword: '',
  material_category: '',
  material_warehouse: '',
  material_location: '',
  material_status: '',
  from_date: '',
  to_date: '',
})

const LOCAL_ERROR_TOKEN = '__error__'
const LOCAL_MANAGEMENT_ERROR_TOKEN = '__mgmt_error__'
const LOCAL_MATERIAL_ERROR_TOKEN = '__material_error__'

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

const localSeedManagementRows: WarehouseManagementItem[] = [
  {
    warehouse_code: 'WH-SAMPLE',
    warehouse_name: '样衣仓',
    warehouse_type: '样衣仓',
    manager: '仓库管理员A',
    status: 'warning',
    capacity_qty: 120,
    used_qty: 98,
    utilization_rate: 81.67,
  },
  {
    warehouse_code: 'WH-FG',
    warehouse_name: '成品仓',
    warehouse_type: '成品仓',
    manager: '仓库管理员B',
    status: 'normal',
    capacity_qty: 240,
    used_qty: 132,
    utilization_rate: 55,
  },
]

const localSeedMaterialRows: WarehouseMaterialInventoryItem[] = [
  {
    material_code: 'FAB-2408-COTTON',
    material_name: '精梳棉面料',
    material_category: '面料',
    warehouse: '原料仓',
    location: 'M-01',
    qty: 280.5,
    amount: 2412.3,
    status: 'normal',
  },
  {
    material_code: 'ACC-2408-BTN01',
    material_name: '树脂纽扣',
    material_category: '辅料',
    warehouse: '辅料仓',
    location: 'M-08',
    qty: 35.2,
    amount: 112.64,
    status: 'warning',
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

const formatPercent = (value: string | number | null | undefined): string => {
  if (value === null || value === undefined || value === '') {
    return '-'
  }
  const numeric = Number(value)
  return Number.isFinite(numeric) ? `${numeric.toFixed(2)}%` : String(value)
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

const inferMaterialCategory = (materialCode: string): string => {
  const code = materialCode.trim().toUpperCase()
  if (code.startsWith('FAB') || code.startsWith('M-') || code.includes('FABRIC')) {
    return '面料'
  }
  if (code.startsWith('ACC') || code.startsWith('TRIM') || code.startsWith('PKG')) {
    return '辅料'
  }
  if (code.startsWith('LBL') || code.startsWith('TAG')) {
    return '包材'
  }
  return '综合物料'
}

const inferMaterialLocation = (warehouse: string, index: number): string => {
  const text = warehouse.trim()
  let prefix = 'A'
  if (text.includes('样衣')) prefix = 'Y'
  else if (text.includes('成品')) prefix = 'F'
  else if (text.includes('原料') || text.includes('辅料')) prefix = 'M'
  const slot = (index % 24) + 1
  return `${prefix}-${String(slot).padStart(2, '0')}`
}

const buildMaterialRowsFromSummary = (
  rows: WarehouseStockSummaryItem[],
): WarehouseMaterialInventoryItem[] => (
  rows.map((row, index) => {
    const category = inferMaterialCategory(row.item_code)
    const qty = Number(row.actual_qty)
    const unitPrice =
      category === '面料'
        ? 8.6
        : category === '辅料'
          ? 3.2
          : category === '包材'
            ? 1.5
            : 5.0
    const status: WarehouseMaterialInventoryItem['status'] =
      row.threshold_missing ? 'disabled' : (row.is_below_safety || row.is_below_reorder ? 'warning' : 'normal')
    return {
      material_code: row.item_code,
      material_name: `物料-${row.item_code}`,
      material_category: category,
      warehouse: row.warehouse,
      location: inferMaterialLocation(row.warehouse, index),
      qty,
      amount: Number((qty * unitPrice).toFixed(2)),
      status,
    }
  })
)

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

const managementDisplayRows = computed<WarehouseManagementItem[]>(() => {
  const keyword = query.management_keyword.trim().toLowerCase()
  const status = query.management_status.trim().toLowerCase()
  return managementRows.value.filter((row) => {
    const keywordMatched =
      !keyword ||
      `${row.warehouse_code}|${row.warehouse_name}|${row.manager}|${row.warehouse_type}`.toLowerCase().includes(keyword)
    const statusMatched = !status || row.status === status
    return keywordMatched && statusMatched
  })
})

const materialDisplayRows = computed<WarehouseMaterialInventoryItem[]>(() => {
  const keyword = query.material_keyword.trim().toLowerCase()
  const category = query.material_category.trim()
  const warehouse = query.material_warehouse.trim().toLowerCase()
  const location = query.material_location.trim().toLowerCase()
  const status = query.material_status.trim().toLowerCase()

  return materialRows.value.filter((row) => {
    const keywordMatched =
      !keyword ||
      `${row.material_code}|${row.material_name}`.toLowerCase().includes(keyword)
    const categoryMatched = !category || row.material_category === category
    const warehouseMatched = !warehouse || row.warehouse.toLowerCase().includes(warehouse)
    const locationMatched = !location || row.location.toLowerCase().includes(location)
    const statusMatched = !status || row.status === status
    return keywordMatched && categoryMatched && warehouseMatched && locationMatched && statusMatched
  })
})

const managementStatusText = (value: WarehouseManagementItem['status']): string => {
  if (value === 'warning') return '预警'
  if (value === 'disabled') return '停用'
  return '正常'
}

const managementStatusTag = (value: WarehouseManagementItem['status']): 'success' | 'warning' | 'info' => {
  if (value === 'warning') return 'warning'
  if (value === 'disabled') return 'info'
  return 'success'
}

const materialStatusText = (value: WarehouseMaterialInventoryItem['status']): string => {
  if (value === 'warning') return '预警'
  if (value === 'disabled') return '停用'
  return '正常'
}

const materialStatusTag = (
  value: WarehouseMaterialInventoryItem['status'],
): 'success' | 'warning' | 'info' => {
  if (value === 'warning') return 'warning'
  if (value === 'disabled') return 'info'
  return 'success'
}

const resetQuery = (): void => {
  query.company = ''
  query.warehouse = ''
  query.order_no = ''
  query.style_keyword = ''
  query.management_keyword = ''
  query.management_status = ''
  query.material_keyword = ''
  query.material_category = ''
  query.material_warehouse = ''
  query.material_location = ''
  query.material_status = ''
  query.from_date = ''
  query.to_date = ''
  managementErrorMessage.value = ''
  materialErrorMessage.value = ''
  void loadData()
}

const loadData = async (): Promise<void> => {
  if (!canRead.value) {
    summaryRows.value = []
    managementRows.value = []
    materialRows.value = []
    ledgerRows.value = []
    orderMap.value = new Map()
    return
  }

  if (query.style_keyword.trim().toLowerCase() === LOCAL_ERROR_TOKEN) {
    errorMessage.value = '模拟错误态：成品库存查询失败，请调整筛选后重试'
    summaryRows.value = []
    managementRows.value = []
    materialRows.value = []
    ledgerRows.value = []
    orderMap.value = new Map()
    return
  }

  const normalized = normalizeQuery()
  const useLocalSeed =
    !normalized.company && !normalized.warehouse && !normalized.item_code && !normalized.from_date && !normalized.to_date
  if (useLocalSeed) {
    errorMessage.value = ''
    managementErrorMessage.value = ''
    materialErrorMessage.value = ''
    summaryRows.value = localSeedSummaryRows
    managementRows.value = localSeedManagementRows
    materialRows.value = localSeedMaterialRows
    ledgerRows.value = localSeedLedgerRows
    orderMap.value = buildOrderMap(localSeedLedgerRows)
    selectedRows.value = []
    return
  }

  loading.value = true
  errorMessage.value = ''
  managementErrorMessage.value = ''
  materialErrorMessage.value = ''
  try {
    const [summaryResult, ledgerResult] = await Promise.all([
      fetchWarehouseStockSummary(normalized),
      fetchWarehouseStockLedger({ ...normalized, page: 1, page_size: 200 }),
    ])
    summaryRows.value = summaryResult.data.items
    managementRows.value = summaryResult.data.warehouse_management ?? localSeedManagementRows
    materialRows.value =
      summaryResult.data.material_inventory && summaryResult.data.material_inventory.length > 0
        ? summaryResult.data.material_inventory
        : buildMaterialRowsFromSummary(summaryResult.data.items)
    ledgerRows.value = ledgerResult.data.items
    orderMap.value = buildOrderMap(ledgerResult.data.items)
  } catch (error) {
    const message = (error as Error).message || '请求失败'
    errorMessage.value = message
    managementErrorMessage.value = message
    materialErrorMessage.value = message
    managementRows.value = []
    materialRows.value = []
    ElMessage.error(message)
  } finally {
    loading.value = false
  }
}

const applyManagementFilters = (): void => {
  if (!canRead.value) {
    ElMessage.warning('当前账号无仓库管理目录读取权限')
    return
  }
  if (query.management_keyword.trim().toLowerCase() === LOCAL_MANAGEMENT_ERROR_TOKEN) {
    managementErrorMessage.value = '模拟错误态：仓库管理目录查询失败，请调整筛选后重试'
    managementRows.value = []
    return
  }
  managementErrorMessage.value = ''
}

const applyMaterialFilters = (): void => {
  if (!canRead.value) {
    ElMessage.warning('当前账号无物料库存读取权限')
    return
  }
  if (query.material_keyword.trim().toLowerCase() === LOCAL_MATERIAL_ERROR_TOKEN) {
    materialErrorMessage.value = '模拟错误态：物料库存查询失败，请调整筛选后重试'
    materialRows.value = []
    return
  }
  materialErrorMessage.value = ''
}

const guardedAction = (actionName: string): void => {
  ElMessage.warning(`${actionName} 为受控动作，本地首版保持只读`)
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

const viewWarehouse = (row: WarehouseManagementItem): void => {
  ElMessage.info(`仓库详情（只读）：${row.warehouse_name}`)
}

const viewMaterial = (row: WarehouseMaterialInventoryItem): void => {
  ElMessage.info(`物料详情（只读）：${row.material_name}`)
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

.warehouse-management-section {
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 12px;
  margin-bottom: 12px;
  background: #fafafa;
}

.management-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}

.management-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.management-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.management-filter-form {
  margin-bottom: 8px;
}

.management-table {
  margin-top: 8px;
}

.material-inventory-section {
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 12px;
  margin-bottom: 12px;
  background: #f7fbff;
}

.material-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}

.material-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.material-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.material-filter-form {
  margin-bottom: 8px;
}

.material-table {
  margin-top: 8px;
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
