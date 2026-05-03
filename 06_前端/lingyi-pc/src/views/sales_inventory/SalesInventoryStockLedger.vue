<template>
  <div class="sales-inventory-page">
    <el-card shadow="never">
      <template #header>
        <div class="header-row">
          <div class="title-group">
            <span class="title">成品进销存报表</span>
            <span class="sub-title">成品进销存 / 成品进销存报表</span>
          </div>
          <el-tag type="info" effect="plain">本地首版</el-tag>
        </div>
      </template>

      <el-form :inline="true" :model="query" class="query-form">
        <el-form-item label="单号">
          <el-input v-model="query.no" clearable placeholder="单号" @keyup.enter="onSearch" />
        </el-form-item>
        <el-form-item label="款式">
          <el-input v-model="query.style" clearable placeholder="款式" @keyup.enter="onSearch" />
        </el-form-item>
        <el-form-item label="仓库">
          <el-input v-model="query.warehouse" clearable placeholder="请输入" @keyup.enter="onSearch" />
        </el-form-item>
        <el-form-item label="开始日期">
          <el-date-picker
            v-model="query.from_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="开始日期"
            clearable
          />
        </el-form-item>
        <el-form-item label="结束日期">
          <el-date-picker
            v-model="query.to_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="结束日期"
            clearable
          />
        </el-form-item>
        <el-form-item label="搜索">
          <el-input v-model="query.keyword" clearable placeholder="请输入" @keyup.enter="onSearch" />
        </el-form-item>
        <el-form-item>
          <el-button :disabled="!canRead" @click="onReset">重置</el-button>
          <el-button type="primary" :disabled="!canRead" @click="onSearch">查询</el-button>
        </el-form-item>
      </el-form>

      <div class="toolbar-row">
        <el-button :disabled="!canRead" @click="onGuardedAction('质检')">质检</el-button>
        <el-button :disabled="!canRead" @click="onReset">清空</el-button>
        <el-button :disabled="!canRead" @click="onGuardedAction('确定')">确定</el-button>
        <el-button :disabled="!canRead" @click="onGuardedAction('标志已读')">标志已读</el-button>
        <el-button :disabled="!canRead" @click="onGuardedAction('消息移除态')">消息移除态</el-button>
        <el-button :disabled="!canRead" @click="onGuardedAction('消息待补态')">消息待补态</el-button>
        <el-button :disabled="!canRead" @click="onSearch">搜索</el-button>
        <el-button :disabled="!canRead" @click="onGuardedAction('留档态')">留档态</el-button>
        <el-button :disabled="!canRead" @click="onGuardedAction('回退态')">回退态</el-button>
        <el-button :disabled="!canRead" @click="onGuardedAction('重置列')">重置列</el-button>
        <el-button :disabled="!canRead" @click="loadRows">刷新</el-button>
        <el-button :disabled="!canExport" @click="onGuardedAction('导出')">导出</el-button>
        <el-button :disabled="!canExport" @click="onGuardedAction('打印')">打印</el-button>
      </div>

      <el-alert
        v-if="lastError"
        class="error-alert"
        type="error"
        :closable="false"
        :title="`成品进销存报表加载失败：${lastError}`"
      />

      <el-empty v-if="!canRead" description="无成品进销存查看权限" />
      <template v-else>
        <div class="summary-row">
          <el-tag type="info" effect="plain">记录数：{{ total }}</el-tag>
          <el-tag type="success" effect="plain">数量合计：{{ totalQty }}</el-tag>
        </div>

        <el-table
          :data="rows"
          border
          v-loading="loading"
          empty-text="暂无成品进销存报表数据，请调整筛选条件后重试"
        >
          <el-table-column label="图片" width="80">
            <template #default="scope">
              <el-avatar v-if="scope.row.image_url" :src="scope.row.image_url" :size="32" />
              <span v-else>-</span>
            </template>
          </el-table-column>
          <el-table-column prop="processing_no" label="加工单号" min-width="130" />
          <el-table-column prop="production_order" label="生产制单" min-width="130" />
          <el-table-column prop="order_no" label="订单号" min-width="140" />
          <el-table-column prop="item_code" label="款号" min-width="120" />
          <el-table-column prop="item_name" label="款名" min-width="140" />
          <el-table-column prop="warehouse" label="仓库" min-width="120" />
          <el-table-column prop="season" label="季节" min-width="100" />
          <el-table-column prop="style_type" label="款式类型" min-width="120" />
          <el-table-column label="数量" width="110">
            <template #default="scope">{{ formatAmount(scope.row.qty) }}</template>
          </el-table-column>
          <el-table-column prop="receipt_date" label="收货日期" min-width="120" />
          <el-table-column label="操作" min-width="90" fixed="right">
            <template #default>
              <el-button link type="primary" @click="onGuardedAction('质检')">质检</el-button>
            </template>
          </el-table-column>
          <el-table-column prop="week_day_0" label="日" width="70" />
          <el-table-column prop="week_day_1" label="一" width="70" />
          <el-table-column prop="week_day_2" label="二" width="70" />
          <el-table-column prop="week_day_3" label="三" width="70" />
          <el-table-column prop="week_day_4" label="四" width="70" />
          <el-table-column prop="week_day_5" label="五" width="70" />
          <el-table-column prop="week_day_6" label="六" width="70" />
          <el-table-column prop="message_title" label="标题" min-width="120" />
          <el-table-column prop="sent_at" label="发送时间" min-width="130" />
          <el-table-column prop="message_status" label="状态" min-width="100" />
          <el-table-column prop="sender" label="发送人" min-width="110" />
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
import { ElMessage } from 'element-plus'
import {
  fetchSalesInventoryFinishedGoodsReport,
  type FinishedGoodsReportItem,
} from '@/api/sales_inventory'
import { usePermissionStore } from '@/stores/permission'

const permissionStore = usePermissionStore()
const loading = ref<boolean>(false)
const rows = ref<FinishedGoodsReportItem[]>([])
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

const totalQty = computed<string>(() => {
  const qty = rows.value.reduce((sum, row) => {
    const current = Number(row.qty ?? 0)
    return Number.isFinite(current) ? sum + current : sum
  }, 0)
  return qty.toFixed(2)
})

const query = reactive({
  no: '',
  style: '',
  warehouse: '',
  from_date: '',
  to_date: '',
  keyword: '',
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
    lastError.value = ''
    return
  }
  loading.value = true
  lastError.value = ''
  try {
    const result = await fetchSalesInventoryFinishedGoodsReport({
      no: query.no.trim() || undefined,
      style: query.style.trim() || undefined,
      warehouse: query.warehouse.trim() || undefined,
      from_date: query.from_date || undefined,
      to_date: query.to_date || undefined,
      keyword: query.keyword.trim() || undefined,
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

const onSearch = (): void => {
  query.page = 1
  void loadRows()
}

const onReset = (): void => {
  query.no = ''
  query.style = ''
  query.warehouse = ''
  query.from_date = ''
  query.to_date = ''
  query.keyword = ''
  query.page = 1
  query.page_size = 20
  void loadRows()
}

const onGuardedAction = (actionName: string): void => {
  ElMessage.warning(`${actionName}功能在本地首版保持只读，未接入真实业务副作用`)
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

.summary-row {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.pager {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}
</style>
