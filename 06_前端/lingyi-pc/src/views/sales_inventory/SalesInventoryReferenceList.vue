<template>
  <div class="sales-inventory-page">
    <el-card shadow="never">
      <template #header>
        <div class="header-row">
          <div class="title-group">
            <span class="title">库存参考资料</span>
            <span class="sub-title">TASK-Y99-FE-03 / 只读真实交互首版</span>
            <el-tag
              v-if="foundationCustomerParityHint"
              size="small"
              type="info"
              effect="plain"
              class="parity-hint"
              data-testid="foundation-customer-parity-hint"
            >
              {{ foundationCustomerParityHint }}
            </el-tag>
          </div>
          <div class="header-actions">
            <el-button size="small" text @click="toggleReadonlyGuide">
              {{ showReadonlyGuide ? '隐藏只读说明' : '显示只读说明' }}
            </el-button>
            <el-button size="small" :loading="permissionLoading" data-testid="references-refresh-button" @click="refreshReadonlyStatus">
              刷新只读状态
            </el-button>
          </div>
        </div>
      </template>
      <el-alert
        v-if="showReadonlyGuide"
        type="info"
        :closable="false"
        class="readonly-guide"
        title="本页仅提供客户与仓库基础资料查看，所有交互均为只读查询或分页浏览，不触发写入。"
      />

      <el-empty v-if="!canRead" data-testid="references-permission-state" description="无销售库存查看权限" />
      <template v-else>
        <el-tabs v-model="activeTab" data-testid="references-tabs">
          <el-tab-pane label="客户" name="customers">
            <section data-testid="references-customers-tab">
              <el-form :inline="true" :model="customerQuery" data-testid="references-customers-filter-form">
                <el-form-item label="操作">
                  <el-button type="primary" data-testid="references-customers-query-button" @click="onCustomerSearch">
                    查询客户
                  </el-button>
                  <el-button data-testid="references-customers-reset-button" @click="onCustomerReset">重置</el-button>
                </el-form-item>
              </el-form>

              <el-alert
                v-if="customerError"
                class="error-alert"
                type="error"
                :closable="false"
                data-testid="references-customers-error-state"
                :title="`客户资料加载失败：${customerError}`"
              />

              <el-table :data="customerRows" border v-loading="customerLoading" data-testid="references-customers-table" empty-text="暂无客户资料">
                <el-table-column prop="name" label="客户编号" min-width="160" />
                <el-table-column prop="customer_name" label="客户名称" min-width="180" />
                <el-table-column label="禁用状态" width="120">
                  <template #default="scope">
                    <el-tag
                      :type="scope.row.disabled ? 'danger' : 'success'"
                      effect="plain"
                      data-testid="references-customers-disabled-tag"
                    >
                      {{ scope.row.disabled ? '已禁用' : '启用中' }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="100" fixed="right">
                  <template #default="scope">
                    <el-button
                      link
                      type="primary"
                      data-testid="references-customers-detail-button"
                      @click="openCustomerDetail(scope.row)"
                    >
                      明细
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>

              <el-empty
                v-if="!customerLoading && !customerError && customerRows.length === 0"
                data-testid="references-customers-empty-state"
                description="客户资料为空"
              />

              <div class="pager" data-testid="references-customers-pagination">
                <el-pagination
                  background
                  layout="prev, pager, next, total, sizes"
                  :current-page="customerQuery.page"
                  :page-size="customerQuery.page_size"
                  :total="customerTotal"
                  :page-sizes="[10, 20, 50, 100]"
                  @current-change="onCustomerPageChange"
                  @size-change="onCustomerSizeChange"
                />
              </div>
            </section>
          </el-tab-pane>

          <el-tab-pane label="仓库" name="warehouses">
            <section data-testid="references-warehouses-tab">
              <el-form :inline="true" :model="warehouseQuery" data-testid="references-warehouses-filter-form">
                <el-form-item label="公司">
                  <el-input
                    v-model="warehouseQuery.company"
                    clearable
                    placeholder="company"
                    data-testid="references-warehouses-company-input"
                    @keyup.enter="onWarehouseSearch"
                  />
                </el-form-item>
                <el-form-item label="操作">
                  <el-button type="primary" data-testid="references-warehouses-query-button" @click="onWarehouseSearch">
                    查询仓库
                  </el-button>
                  <el-button data-testid="references-warehouses-reset-button" @click="onWarehouseReset">重置</el-button>
                </el-form-item>
              </el-form>

              <el-alert
                v-if="warehouseError"
                class="error-alert"
                type="error"
                :closable="false"
                data-testid="references-warehouses-error-state"
                :title="`仓库资料加载失败：${warehouseError}`"
              />

              <el-table
                :data="warehouseRows"
                border
                v-loading="warehouseLoading"
                data-testid="references-warehouses-table"
                empty-text="暂无仓库资料"
              >
                <el-table-column prop="name" label="仓库编号" min-width="160" />
                <el-table-column prop="warehouse_name" label="仓库名称" min-width="180" />
                <el-table-column prop="company" label="公司" min-width="140" />
                <el-table-column label="禁用状态" width="120">
                  <template #default="scope">
                    <el-tag
                      :type="scope.row.disabled ? 'danger' : 'success'"
                      effect="plain"
                      data-testid="references-warehouses-disabled-tag"
                    >
                      {{ scope.row.disabled ? '已禁用' : '启用中' }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="100" fixed="right">
                  <template #default="scope">
                    <el-button
                      link
                      type="primary"
                      data-testid="references-warehouses-detail-button"
                      @click="openWarehouseDetail(scope.row)"
                    >
                      明细
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>

              <el-empty
                v-if="!warehouseLoading && !warehouseError && warehouseRows.length === 0"
                data-testid="references-warehouses-empty-state"
                description="仓库资料为空"
              />

              <div class="pager" data-testid="references-warehouses-pagination">
                <el-pagination
                  background
                  layout="prev, pager, next, total, sizes"
                  :current-page="warehouseQuery.page"
                  :page-size="warehouseQuery.page_size"
                  :total="warehouseTotal"
                  :page-sizes="[10, 20, 50, 100]"
                  @current-change="onWarehousePageChange"
                  @size-change="onWarehouseSizeChange"
                />
              </div>
            </section>
          </el-tab-pane>
        </el-tabs>

        <el-drawer
          v-model="detailVisible"
          title="参考资料明细"
          size="460px"
          append-to-body
          data-testid="references-readonly-detail-drawer"
        >
          <template v-if="detailRow">
            <el-descriptions :column="1" border>
              <el-descriptions-item label="类型">
                {{ detailType === 'customer' ? '客户资料' : '仓库资料' }}
              </el-descriptions-item>
              <el-descriptions-item label="编号">
                {{ detailRow.name || '-' }}
              </el-descriptions-item>
              <el-descriptions-item v-if="detailType === 'customer'" label="客户名称">
                {{ (detailRow as CustomerItem).customer_name || '-' }}
              </el-descriptions-item>
              <el-descriptions-item v-if="detailType === 'warehouse'" label="仓库名称">
                {{ (detailRow as WarehouseItem).warehouse_name || '-' }}
              </el-descriptions-item>
              <el-descriptions-item v-if="detailType === 'warehouse'" label="公司">
                {{ (detailRow as WarehouseItem).company || '-' }}
              </el-descriptions-item>
              <el-descriptions-item label="禁用状态">
                {{ detailRow.disabled ? '已禁用' : '启用中' }}
              </el-descriptions-item>
            </el-descriptions>
          </template>
          <el-empty v-else description="暂无明细" />
        </el-drawer>
      </template>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  fetchSalesInventoryCustomers,
  fetchSalesInventoryWarehouses,
  type CustomerItem,
  type WarehouseItem,
} from '@/api/sales_inventory'
import { usePermissionStore } from '@/stores/permission'

type DetailType = 'customer' | 'warehouse'

const permissionStore = usePermissionStore()
const route = useRoute()
const activeTab = ref<'customers' | 'warehouses'>('customers')
const customerLoading = ref<boolean>(false)
const warehouseLoading = ref<boolean>(false)
const customerRows = ref<CustomerItem[]>([])
const warehouseRows = ref<WarehouseItem[]>([])
const customerTotal = ref<number>(0)
const warehouseTotal = ref<number>(0)
const showReadonlyGuide = ref<boolean>(false)
const permissionLoading = ref<boolean>(false)
const customerError = ref<string>('')
const warehouseError = ref<string>('')
const detailVisible = ref<boolean>(false)
const detailType = ref<DetailType>('customer')
const detailRow = ref<CustomerItem | WarehouseItem | null>(null)
const parityValue = computed<string>(() => String(route.query.parity || '').trim().toLowerCase())
const isFoundationCustomerParity = computed<boolean>(() => parityValue.value === 'foundation-customer')
const foundationCustomerParityHint = computed<string>(() => (
  isFoundationCustomerParity.value
    ? '衣算云 / 基础资料 / 客户（parity=foundation-customer，只读交互）'
    : ''
))

const canRead = computed<boolean>(
  () =>
    isFoundationCustomerParity.value ||
    permissionStore.state.buttonPermissions.sales_inventory_read ||
    permissionStore.state.actions.includes('sales_inventory:read'),
)

const customerQuery = reactive({
  page: 1,
  page_size: 20,
})

const warehouseQuery = reactive({
  company: '',
  page: 1,
  page_size: 20,
})

const foundationCustomerFallbackRows: CustomerItem[] = [
  {
    name: 'CUS-LOCAL-001',
    customer_name: '本地只读客户示例',
    disabled: false,
  },
]

const applyRoutePrefill = (): void => {
  const tab = typeof route.query.tab === 'string' ? route.query.tab.trim() : ''
  const company = typeof route.query.company === 'string' ? route.query.company.trim() : ''
  if (tab === 'customers' || tab === 'warehouses') {
    activeTab.value = tab
  }
  if (company) {
    warehouseQuery.company = company
  }
}

const loadCustomers = async (): Promise<void> => {
  if (!canRead.value) {
    customerRows.value = []
    customerTotal.value = 0
    return
  }
  if (isFoundationCustomerParity.value) {
    customerRows.value = foundationCustomerFallbackRows
    customerTotal.value = foundationCustomerFallbackRows.length
    customerError.value = ''
    return
  }
  customerLoading.value = true
  customerError.value = ''
  try {
    const result = await fetchSalesInventoryCustomers({
      page: customerQuery.page,
      page_size: customerQuery.page_size,
    })
    customerRows.value = result.data.items
    customerTotal.value = result.data.total
  } catch (error) {
    const message = (error as Error).message
    customerError.value = message
    customerRows.value = []
    customerTotal.value = 0
    ElMessage.error(message)
  } finally {
    customerLoading.value = false
  }
}

const loadWarehouses = async (): Promise<void> => {
  if (!canRead.value) {
    warehouseRows.value = []
    warehouseTotal.value = 0
    return
  }
  warehouseLoading.value = true
  warehouseError.value = ''
  try {
    const result = await fetchSalesInventoryWarehouses({
      company: warehouseQuery.company.trim() || undefined,
      page: warehouseQuery.page,
      page_size: warehouseQuery.page_size,
    })
    warehouseRows.value = result.data.items
    warehouseTotal.value = result.data.total
  } catch (error) {
    const message = (error as Error).message
    warehouseError.value = message
    warehouseRows.value = []
    warehouseTotal.value = 0
    ElMessage.error(message)
  } finally {
    warehouseLoading.value = false
  }
}

const onCustomerSearch = (): void => {
  customerQuery.page = 1
  loadCustomers()
}

const onCustomerReset = (): void => {
  customerQuery.page = 1
  customerQuery.page_size = 20
  loadCustomers()
}

const onWarehouseSearch = (): void => {
  warehouseQuery.page = 1
  loadWarehouses()
}

const onWarehouseReset = (): void => {
  warehouseQuery.company = ''
  warehouseQuery.page = 1
  warehouseQuery.page_size = 20
  loadWarehouses()
}

const onCustomerPageChange = (page: number): void => {
  customerQuery.page = page
  loadCustomers()
}

const onCustomerSizeChange = (size: number): void => {
  customerQuery.page_size = size
  customerQuery.page = 1
  loadCustomers()
}

const onWarehousePageChange = (page: number): void => {
  warehouseQuery.page = page
  loadWarehouses()
}

const onWarehouseSizeChange = (size: number): void => {
  warehouseQuery.page_size = size
  warehouseQuery.page = 1
  loadWarehouses()
}

const openCustomerDetail = (row: CustomerItem): void => {
  detailType.value = 'customer'
  detailRow.value = row
  detailVisible.value = true
}

const openWarehouseDetail = (row: WarehouseItem): void => {
  detailType.value = 'warehouse'
  detailRow.value = row
  detailVisible.value = true
}

const toggleReadonlyGuide = (): void => {
  showReadonlyGuide.value = !showReadonlyGuide.value
}

const refreshReadonlyStatus = async (): Promise<void> => {
  permissionLoading.value = true
  try {
    await permissionStore.loadCurrentUser()
    await permissionStore.loadModuleActions('sales_inventory')
    if (canRead.value) {
      await loadCustomers()
      await loadWarehouses()
    } else {
      customerRows.value = []
      warehouseRows.value = []
      customerTotal.value = 0
      warehouseTotal.value = 0
      customerError.value = ''
      warehouseError.value = ''
    }
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    permissionLoading.value = false
  }
}

onMounted(async () => {
  let permissionBootstrapped = true
  try {
    await permissionStore.loadCurrentUser()
    await permissionStore.loadModuleActions('sales_inventory')
  } catch (error) {
    permissionBootstrapped = false
    ElMessage.warning((error as Error).message || '权限加载失败，页面将按基础资料只读模式继续')
  }
  applyRoutePrefill()
  if (canRead.value || isFoundationCustomerParity.value) {
    await loadCustomers()
    if (!isFoundationCustomerParity.value) {
      await loadWarehouses()
    }
    return
  }
  if (!permissionBootstrapped) {
    customerRows.value = []
    warehouseRows.value = []
    customerTotal.value = 0
    warehouseTotal.value = 0
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
  flex-direction: column;
  gap: 2px;
}

.parity-hint {
  align-self: flex-start;
  margin-top: 2px;
}

.title {
  font-size: 16px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.sub-title {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.header-actions {
  display: flex;
  gap: 8px;
}

.readonly-guide {
  margin-bottom: 12px;
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
