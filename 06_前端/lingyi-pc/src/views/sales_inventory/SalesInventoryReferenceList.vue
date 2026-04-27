<template>
  <div class="sales-inventory-page">
    <el-card shadow="never">
      <template #header>
        <div class="header-row">
          <span>销售库存基础资料只读</span>
          <div class="header-actions">
            <el-button size="small" text @click="toggleReadonlyGuide">
              {{ showReadonlyGuide ? '隐藏只读说明' : '显示只读说明' }}
            </el-button>
            <el-button size="small" :loading="permissionLoading" @click="refreshReadonlyStatus">刷新只读状态</el-button>
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

      <el-empty v-if="!canRead" description="无销售库存查看权限" />
      <template v-else>
        <el-tabs v-model="activeTab">
          <el-tab-pane label="客户" name="customers">
            <el-form :inline="true" :model="customerQuery">
              <el-form-item label="操作">
                <el-button type="primary" @click="loadCustomers">查询客户</el-button>
              </el-form-item>
            </el-form>
            <el-table :data="customerRows" border v-loading="customerLoading" empty-text="暂无客户资料">
              <el-table-column prop="name" label="客户编号" min-width="160" />
              <el-table-column prop="customer_name" label="客户名称" min-width="180" />
              <el-table-column label="禁用" width="100">
                <template #default="scope">{{ scope.row.disabled ? '是' : '否' }}</template>
              </el-table-column>
            </el-table>
            <div class="pager">
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
          </el-tab-pane>

          <el-tab-pane label="仓库" name="warehouses">
            <el-form :inline="true" :model="warehouseQuery">
              <el-form-item label="公司">
                <el-input v-model="warehouseQuery.company" clearable placeholder="company" />
              </el-form-item>
              <el-form-item label="操作">
                <el-button type="primary" @click="loadWarehouses">查询仓库</el-button>
              </el-form-item>
            </el-form>
            <el-table :data="warehouseRows" border v-loading="warehouseLoading" empty-text="暂无仓库资料">
              <el-table-column prop="name" label="仓库编号" min-width="160" />
              <el-table-column prop="warehouse_name" label="仓库名称" min-width="180" />
              <el-table-column prop="company" label="公司" min-width="140" />
              <el-table-column label="禁用" width="100">
                <template #default="scope">{{ scope.row.disabled ? '是' : '否' }}</template>
              </el-table-column>
            </el-table>
            <div class="pager">
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
  fetchSalesInventoryCustomers,
  fetchSalesInventoryWarehouses,
  type CustomerItem,
  type WarehouseItem,
} from '@/api/sales_inventory'
import { usePermissionStore } from '@/stores/permission'

const permissionStore = usePermissionStore()
const activeTab = ref<'customers' | 'warehouses'>('customers')
const customerLoading = ref<boolean>(false)
const warehouseLoading = ref<boolean>(false)
const customerRows = ref<CustomerItem[]>([])
const warehouseRows = ref<WarehouseItem[]>([])
const customerTotal = ref<number>(0)
const warehouseTotal = ref<number>(0)
const showReadonlyGuide = ref<boolean>(false)
const permissionLoading = ref<boolean>(false)

const canRead = computed<boolean>(() => permissionStore.state.buttonPermissions.sales_inventory_read)

const customerQuery = reactive({
  page: 1,
  page_size: 20,
})

const warehouseQuery = reactive({
  company: '',
  page: 1,
  page_size: 20,
})

const loadCustomers = async (): Promise<void> => {
  if (!canRead.value) {
    customerRows.value = []
    customerTotal.value = 0
    return
  }
  customerLoading.value = true
  try {
    const result = await fetchSalesInventoryCustomers({
      page: customerQuery.page,
      page_size: customerQuery.page_size,
    })
    customerRows.value = result.data.items
    customerTotal.value = result.data.total
  } catch (error) {
    ElMessage.error((error as Error).message)
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
  try {
    const result = await fetchSalesInventoryWarehouses({
      company: warehouseQuery.company.trim() || undefined,
      page: warehouseQuery.page,
      page_size: warehouseQuery.page_size,
    })
    warehouseRows.value = result.data.items
    warehouseTotal.value = result.data.total
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    warehouseLoading.value = false
  }
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
    }
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    permissionLoading.value = false
  }
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
    await loadCustomers()
    await loadWarehouses()
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

.header-actions {
  display: flex;
  gap: 8px;
}

.readonly-guide {
  margin-bottom: 12px;
}

.pager {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}
</style>
