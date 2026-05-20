<template>
  <div class="sales-inventory-page" data-testid="sales-order-detail-page">
    <el-card shadow="never" v-loading="loading" data-testid="sales-order-detail-card">
      <template #header>
        <div class="header-row" data-testid="sales-order-detail-header">
          <span data-testid="sales-order-detail-title">销售订单只读详情</span>
          <el-button data-testid="sales-order-detail-back" @click="backToList">返回列表</el-button>
        </div>
      </template>

      <el-alert
        v-if="guardedFeedback"
        :title="guardedFeedback"
        type="warning"
        :closable="false"
        show-icon
        data-testid="sales-order-detail-guarded-feedback"
      />

      <el-empty
        v-if="!canRead"
        description="无销售库存查看权限"
        data-testid="sales-order-detail-permission-state"
      />
      <el-empty
        v-else-if="!orderName"
        description="缺少销售订单编号"
        data-testid="sales-order-detail-missing-name-state"
      />
      <template v-else>
        <el-alert
          v-if="loadError"
          :title="loadError"
          type="error"
          show-icon
          :closable="false"
          data-testid="sales-order-detail-error-state"
        />
        <el-empty
          v-else-if="!detail"
          description="未找到销售订单详情"
          data-testid="sales-order-detail-empty-state"
        />
        <template v-else>
          <el-descriptions :column="3" border data-testid="sales-order-detail-main-fields">
            <el-descriptions-item label="销售订单">
              <span data-testid="sales-order-detail-field-name">{{ detail.name }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="公司">
              <span data-testid="sales-order-detail-field-company">{{ detail.company }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="客户">
              <span data-testid="sales-order-detail-field-customer">{{ detail.customer || '-' }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="订单日期">
              <span data-testid="sales-order-detail-field-transaction-date">{{ detail.transaction_date || '-' }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="交付日期">
              <span data-testid="sales-order-detail-field-delivery-date">{{ detail.delivery_date || '-' }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag
                effect="plain"
                :type="statusTagType(detail.status)"
                data-testid="sales-order-detail-status-tag"
              >
                {{ detail.status || '-' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="docstatus">
              <el-tag
                effect="plain"
                :type="docstatusTagType(detail.docstatus)"
                data-testid="sales-order-detail-docstatus-tag"
              >
                {{ docstatusLabel(detail.docstatus) }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="总额">
              <span data-testid="sales-order-detail-field-grand-total">{{ formatAmount(detail.grand_total) }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="币种">
              <span data-testid="sales-order-detail-field-currency">{{ detail.currency || '-' }}</span>
            </el-descriptions-item>
          </el-descriptions>

          <div class="action-row" data-testid="sales-order-detail-guarded-actions">
            <el-button
              type="primary"
              data-testid="sales-order-detail-action-place-order"
              data-action-type="write"
              data-write-guard="guarded:readonly"
              @click="guardedWriteAction('提交审核')"
            >
              提交审核
            </el-button>
            <el-button
              data-testid="sales-order-detail-action-export"
              data-action-type="write"
              data-write-guard="guarded:readonly"
              @click="guardedWriteAction('导出订单')"
            >
              导出订单
            </el-button>
            <el-button
              data-testid="sales-order-detail-action-print"
              data-action-type="write"
              data-write-guard="guarded:readonly"
              @click="guardedWriteAction('打印单据')"
            >
              打印单据
            </el-button>
          </div>
          <p class="permission-tip" data-testid="sales-order-detail-permission-disabled-state">
            当前详情页为只读模式，写动作已禁用。
          </p>

          <el-table
            class="detail-table"
            :data="detail.items || []"
            border
            empty-text="暂无销售订单明细"
            data-testid="sales-order-detail-items-table"
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

          <el-divider />

          <section class="fulfillment-section" data-testid="sales-order-detail-fulfillment-section">
            <div class="fulfillment-header">
              <span>履约只读信息</span>
              <el-button
                data-testid="sales-order-detail-fulfillment-refresh"
                :disabled="!canRead"
                @click="loadFulfillment"
              >
                刷新履约
              </el-button>
            </div>

            <el-alert
              v-if="fulfillmentError"
              class="error-alert"
              :title="fulfillmentError"
              type="error"
              :closable="false"
              data-testid="sales-order-detail-fulfillment-error-state"
            />

            <el-table
              :data="fulfillmentRows"
              border
              empty-text="暂无履约对照数据"
              v-loading="fulfillmentLoading"
              data-testid="sales-order-detail-fulfillment-table"
            >
              <el-table-column prop="sales_order" label="订单号" min-width="160" />
              <el-table-column prop="item_code" label="款号" min-width="140" />
              <el-table-column prop="warehouse" label="仓库" min-width="140" />
              <el-table-column label="订单数量" width="120">
                <template #default="scope">{{ formatAmount(scope.row.ordered_qty) }}</template>
              </el-table-column>
              <el-table-column label="库存数量" width="120">
                <template #default="scope">{{ formatAmount(scope.row.actual_qty) }}</template>
              </el-table-column>
              <el-table-column label="完成率" width="120">
                <template #default="scope">{{ formatPercent(scope.row.fulfillment_rate) }}</template>
              </el-table-column>
            </el-table>
          </section>
        </template>
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
  fetchSalesInventorySalesOrderFulfillment,
  type SalesOrderDetailData,
  type SalesOrderFulfillmentItem,
} from '@/api/sales_inventory'
import { usePermissionStore } from '@/stores/permission'

const route = useRoute()
const router = useRouter()
const permissionStore = usePermissionStore()
const loading = ref<boolean>(false)
const detail = ref<SalesOrderDetailData | null>(null)
const loadError = ref<string>('')
const guardedFeedback = ref<string>('')
const fulfillmentLoading = ref<boolean>(false)
const fulfillmentRows = ref<SalesOrderFulfillmentItem[]>([])
const fulfillmentError = ref<string>('')

const paritySource = computed<string>(() => String(route.query.parity || '').trim())
const parityReadonlyMode = computed<boolean>(() => paritySource.value === 'production-order')
const canRead = computed<boolean>(
  () => parityReadonlyMode.value || permissionStore.state.buttonPermissions.sales_inventory_read,
)
const orderName = computed<string>(() => String(route.query.name || '').trim())

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
  return `${(numeric * 100).toFixed(2)}%`
}

const docstatusLabel = (docstatus: number): string => {
  if (docstatus === 0) return '草稿'
  if (docstatus === 1) return '状态1'
  if (docstatus === 2) return '状态2'
  return String(docstatus)
}

const docstatusTagType = (docstatus: number): 'info' | 'success' | 'danger' => {
  if (docstatus === 1) return 'success'
  if (docstatus === 2) return 'danger'
  return 'info'
}

const statusTagType = (status?: string | null): 'success' | 'warning' | 'info' => {
  if (!status) return 'info'
  if (status.includes('完成') || status.includes('Closed')) return 'success'
  if (status.includes('进行') || status.includes('To Deliver')) return 'warning'
  return 'info'
}

const loadDetail = async (): Promise<void> => {
  guardedFeedback.value = ''
  loadError.value = ''
  fulfillmentRows.value = []
  fulfillmentError.value = ''
  if (!canRead.value || !orderName.value) {
    detail.value = null
    return
  }

  loading.value = true
  try {
    const result = await fetchSalesInventorySalesOrderDetail(orderName.value)
    detail.value = result.data
    await loadFulfillment()
  } catch (error) {
    detail.value = null
    const message = (error as Error).message || '详情加载失败'
    loadError.value = `订单详情加载失败：${message}`
    ElMessage.error(loadError.value)
  } finally {
    loading.value = false
  }
}

const loadFulfillment = async (): Promise<void> => {
  fulfillmentError.value = ''
  fulfillmentRows.value = []
  if (!canRead.value || !detail.value) {
    return
  }
  const firstItemCode = detail.value.items?.[0]?.item_code || ''
  const query = {
    company: detail.value.company || undefined,
    item_code: firstItemCode || undefined,
  }
  fulfillmentLoading.value = true
  try {
    const result = await fetchSalesInventorySalesOrderFulfillment(query)
    const items = Array.isArray(result.data?.items) ? result.data.items : []
    fulfillmentRows.value = items.filter((row) => row.sales_order === detail.value?.name)
  } catch (error) {
    const message = (error as Error).message || '履约信息加载失败'
    fulfillmentError.value = `履约信息加载失败：${message}`
    ElMessage.error(fulfillmentError.value)
  } finally {
    fulfillmentLoading.value = false
  }
}

const guardedWriteAction = (actionName: string): void => {
  guardedFeedback.value = `当前为只读模式，${actionName}已禁用。`
  ElMessage.warning(guardedFeedback.value)
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

.action-row {
  margin-top: 16px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.permission-tip {
  margin: 12px 0;
  color: #909399;
  font-size: 12px;
}

.fulfillment-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.fulfillment-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.error-alert {
  margin: 8px 0;
}
</style>
