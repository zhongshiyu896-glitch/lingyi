<template>
  <div class="cross-module-page">
    <el-card shadow="never">
      <template #header>
        <div class="header-row">
          <span>跨模块只读视图</span>
        </div>
      </template>

      <el-empty v-if="!canRead" description="无跨模块只读查看权限（需销售库存读取与质量读取）" />
      <template v-else>
        <el-tabs v-model="activeTab">
          <el-tab-pane label="生产-库存-质量" name="work_order">
            <el-form :inline="true" :model="workOrderQuery">
              <el-form-item label="工单">
                <el-input v-model="workOrderQuery.work_order_id" clearable placeholder="work_order_id" />
              </el-form-item>
              <el-form-item label="公司">
                <el-input v-model="workOrderQuery.company" clearable placeholder="company" />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" @click="loadWorkOrderTrail">查询链路</el-button>
              </el-form-item>
            </el-form>

            <el-descriptions v-if="workOrderTrail" :column="4" border class="summary-block">
              <el-descriptions-item label="工单">{{ workOrderTrail.work_order.work_order_id }}</el-descriptions-item>
              <el-descriptions-item label="产成品">{{ workOrderTrail.work_order.production_item || '-' }}</el-descriptions-item>
              <el-descriptions-item label="投料汇总">{{ formatAmount(workOrderTrail.summary.material_issue_qty) }}</el-descriptions-item>
              <el-descriptions-item label="产出汇总">{{ formatAmount(workOrderTrail.summary.output_qty) }}</el-descriptions-item>
              <el-descriptions-item label="合格数量">{{ formatAmount(workOrderTrail.summary.accepted_qty) }}</el-descriptions-item>
              <el-descriptions-item label="不合格数量">{{ formatAmount(workOrderTrail.summary.rejected_qty) }}</el-descriptions-item>
              <el-descriptions-item label="缺陷数量">{{ formatAmount(workOrderTrail.summary.defect_qty) }}</el-descriptions-item>
              <el-descriptions-item label="质检单数">{{ workOrderTrail.summary.quality_inspection_count }}</el-descriptions-item>
            </el-descriptions>

            <h3 class="section-title">库存流水事实</h3>
            <el-table :data="workOrderTrail?.stock_entries || []" border v-loading="workOrderLoading">
              <el-table-column prop="voucher_no" label="凭证号" min-width="180" />
              <el-table-column prop="voucher_type" label="凭证类型" min-width="120" />
              <el-table-column prop="company" label="公司" min-width="120" />
              <el-table-column prop="item_code" label="物料" min-width="130" />
              <el-table-column prop="warehouse" label="仓库" min-width="150" />
              <el-table-column prop="posting_date" label="日期" width="120" />
              <el-table-column prop="posting_time" label="时间" width="120" />
              <el-table-column label="变动数量" width="120">
                <template #default="scope">{{ formatAmount(scope.row.actual_qty) }}</template>
              </el-table-column>
            </el-table>

            <h3 class="section-title">质量检验事实</h3>
            <el-table :data="workOrderTrail?.quality_inspections || []" border v-loading="workOrderLoading">
              <el-table-column prop="inspection_no" label="检验单号" min-width="170" />
              <el-table-column prop="inspection_date" label="检验日期" width="120" />
              <el-table-column prop="item_code" label="物料" min-width="130" />
              <el-table-column prop="warehouse" label="仓库" min-width="140" />
              <el-table-column prop="status" label="状态" width="100" />
              <el-table-column prop="result" label="结果" width="100" />
              <el-table-column label="合格数量" width="120">
                <template #default="scope">{{ formatAmount(scope.row.accepted_qty) }}</template>
              </el-table-column>
              <el-table-column label="不合格数量" width="120">
                <template #default="scope">{{ formatAmount(scope.row.rejected_qty) }}</template>
              </el-table-column>
              <el-table-column label="缺陷数量" width="120">
                <template #default="scope">{{ formatAmount(scope.row.defect_qty) }}</template>
              </el-table-column>
            </el-table>
          </el-tab-pane>

          <el-tab-pane label="销售-库存-质量" name="sales_order">
            <el-form :inline="true" :model="salesOrderQuery">
              <el-form-item label="销售单">
                <el-input v-model="salesOrderQuery.sales_order_id" clearable placeholder="sales_order_id" />
              </el-form-item>
              <el-form-item label="公司">
                <el-input v-model="salesOrderQuery.company" clearable placeholder="company" />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" @click="loadSalesOrderTrail">查询链路</el-button>
              </el-form-item>
            </el-form>

            <el-descriptions v-if="salesOrderTrail" :column="4" border class="summary-block">
              <el-descriptions-item label="销售单">{{ salesOrderTrail.sales_order.sales_order_id }}</el-descriptions-item>
              <el-descriptions-item label="客户">{{ salesOrderTrail.sales_order.customer || '-' }}</el-descriptions-item>
              <el-descriptions-item label="订单数量">{{ formatAmount(salesOrderTrail.summary.ordered_qty) }}</el-descriptions-item>
              <el-descriptions-item label="出库数量">{{ formatAmount(salesOrderTrail.summary.delivered_qty) }}</el-descriptions-item>
              <el-descriptions-item label="质检单数">{{ salesOrderTrail.summary.quality_inspection_count }}</el-descriptions-item>
              <el-descriptions-item label="缺陷数量">{{ formatAmount(salesOrderTrail.summary.defect_qty) }}</el-descriptions-item>
            </el-descriptions>

            <h3 class="section-title">交付/出库事实</h3>
            <el-table :data="salesOrderTrail?.delivery_notes || []" border v-loading="salesOrderLoading">
              <el-table-column prop="delivery_note" label="交付单号" min-width="180" />
              <el-table-column prop="company" label="公司" min-width="120" />
              <el-table-column prop="item_code" label="物料" min-width="130" />
              <el-table-column prop="warehouse" label="仓库" min-width="150" />
              <el-table-column prop="posting_date" label="日期" width="120" />
              <el-table-column prop="posting_time" label="时间" width="120" />
              <el-table-column label="交付数量" width="120">
                <template #default="scope">{{ formatAmount(scope.row.delivered_qty) }}</template>
              </el-table-column>
            </el-table>

            <h3 class="section-title">质量检验事实</h3>
            <el-table :data="salesOrderTrail?.quality_inspections || []" border v-loading="salesOrderLoading">
              <el-table-column prop="inspection_no" label="检验单号" min-width="170" />
              <el-table-column prop="inspection_date" label="检验日期" width="120" />
              <el-table-column prop="item_code" label="物料" min-width="130" />
              <el-table-column prop="warehouse" label="仓库" min-width="140" />
              <el-table-column prop="status" label="状态" width="100" />
              <el-table-column prop="result" label="结果" width="100" />
              <el-table-column label="缺陷数量" width="120">
                <template #default="scope">{{ formatAmount(scope.row.defect_qty) }}</template>
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
  fetchSalesOrderTrail,
  fetchWorkOrderTrail,
  type CrossModuleSalesOrderTrailData,
  type CrossModuleWorkOrderTrailData,
} from '@/api/cross_module'
import { usePermissionStore } from '@/stores/permission'

const permissionStore = usePermissionStore()
const activeTab = ref<'work_order' | 'sales_order'>('work_order')
const workOrderLoading = ref<boolean>(false)
const salesOrderLoading = ref<boolean>(false)
const workOrderTrail = ref<CrossModuleWorkOrderTrailData | null>(null)
const salesOrderTrail = ref<CrossModuleSalesOrderTrailData | null>(null)

const workOrderQuery = reactive({
  work_order_id: '',
  company: '',
})

const salesOrderQuery = reactive({
  sales_order_id: '',
  company: '',
})

const canRead = computed<boolean>(
  () => permissionStore.state.buttonPermissions.sales_inventory_read && permissionStore.state.buttonPermissions.quality_read,
)

const formatAmount = (value: string | number | null | undefined): string => {
  if (value === null || value === undefined || value === '') {
    return '-'
  }
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric.toFixed(2) : String(value)
}

const loadWorkOrderTrail = async (): Promise<void> => {
  if (!workOrderQuery.work_order_id.trim()) {
    ElMessage.warning('work_order_id 不能为空')
    return
  }
  workOrderLoading.value = true
  try {
    const response = await fetchWorkOrderTrail(workOrderQuery.work_order_id.trim(), {
      company: workOrderQuery.company.trim() || undefined,
    })
    workOrderTrail.value = response.data
  } catch (error) {
    ElMessage.error((error as Error).message)
    workOrderTrail.value = null
  } finally {
    workOrderLoading.value = false
  }
}

const loadSalesOrderTrail = async (): Promise<void> => {
  if (!salesOrderQuery.sales_order_id.trim()) {
    ElMessage.warning('sales_order_id 不能为空')
    return
  }
  salesOrderLoading.value = true
  try {
    const response = await fetchSalesOrderTrail(salesOrderQuery.sales_order_id.trim(), {
      company: salesOrderQuery.company.trim() || undefined,
    })
    salesOrderTrail.value = response.data
  } catch (error) {
    ElMessage.error((error as Error).message)
    salesOrderTrail.value = null
  } finally {
    salesOrderLoading.value = false
  }
}

onMounted(async () => {
  try {
    await permissionStore.loadCurrentUser()
    await Promise.all([permissionStore.loadModuleActions('sales_inventory'), permissionStore.loadModuleActions('quality')])
  } catch (error) {
    ElMessage.error((error as Error).message)
  }
})
</script>

<style scoped>
.cross-module-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.summary-block {
  margin-bottom: 12px;
}

.section-title {
  margin-top: 18px;
}
</style>
