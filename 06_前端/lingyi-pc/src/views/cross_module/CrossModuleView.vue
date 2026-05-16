<template>
  <div class="cross-module-page" data-testid="cross-module-work-order-section">
    <el-card shadow="never">
      <template #header>
        <div class="header-row">
          <span>跨模块只读视图</span>
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
        title="本页仅展示跨模块链路事实，交互仅限输入查询条件、切换标签与返回，不会触发写入。"
      />

      <el-empty
        v-if="!canRead"
        data-testid="cross-module-permission-disabled-state"
        description="无跨模块只读查看权限（需销售库存读取与质量读取）"
      />
      <template v-else>
        <el-tabs v-model="activeTab" data-testid="cross-module-tabs">
          <el-tab-pane label="生产-库存-质量" name="work_order">
            <div data-testid="cross-module-work-order-tab">
              <el-form :inline="true" :model="workOrderQuery" data-testid="cross-module-work-order-form">
                <el-form-item label="工单" data-testid="cross-module-work-order-id-field">
                  <el-input
                    v-model="workOrderQuery.work_order_id"
                    clearable
                    placeholder="work_order_id"
                    data-testid="cross-module-work-order-id-input"
                  />
                </el-form-item>
                <el-form-item label="公司" data-testid="cross-module-work-order-company-field">
                  <el-input
                    v-model="workOrderQuery.company"
                    clearable
                    placeholder="company"
                    data-testid="cross-module-work-order-company-input"
                  />
                </el-form-item>
                <el-form-item label="操作" data-testid="cross-module-work-order-action-field">
                  <el-button type="primary" data-testid="cross-module-work-order-query-button" @click="loadWorkOrderTrail">
                    查询链路
                  </el-button>
                </el-form-item>
              </el-form>

              <el-alert
                v-if="workOrderGuardMessage"
                data-testid="cross-module-work-order-guarded-state"
                type="warning"
                :closable="false"
                :title="workOrderGuardMessage"
                style="margin-bottom: 12px"
              />

              <el-alert
                v-if="workOrderErrorMessage"
                data-testid="cross-module-work-order-error-state"
                type="error"
                :closable="false"
                :title="workOrderErrorMessage"
                style="margin-bottom: 12px"
              />

              <el-descriptions v-if="workOrderTrail" :column="4" border class="summary-block" data-testid="cross-module-work-order-summary">
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
              <el-table
                :data="workOrderTrail?.stock_entries || []"
                border
                v-loading="workOrderLoading"
                data-testid="cross-module-work-order-stock-table"
                empty-text="暂无库存流水事实，请调整筛选条件后重试"
              >
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
              <el-table
                :data="workOrderTrail?.quality_inspections || []"
                border
                v-loading="workOrderLoading"
                data-testid="cross-module-work-order-quality-table"
                empty-text="暂无质量检验事实，请调整筛选条件后重试"
              >
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

              <el-empty
                v-if="workOrderShowEmptyState"
                data-testid="cross-module-work-order-empty-state"
                description="暂无工单链路事实，请调整筛选条件后重试"
              />
            </div>
          </el-tab-pane>

          <el-tab-pane label="销售-库存-质量" name="sales_order">
            <div data-testid="cross-module-sales-order-tab">
              <el-form :inline="true" :model="salesOrderQuery" data-testid="cross-module-sales-order-form">
                <el-form-item label="销售单" data-testid="cross-module-sales-order-id-field">
                  <el-input
                    v-model="salesOrderQuery.sales_order_id"
                    clearable
                    placeholder="sales_order_id"
                    data-testid="cross-module-sales-order-id-input"
                  />
                </el-form-item>
                <el-form-item label="公司" data-testid="cross-module-sales-order-company-field">
                  <el-input
                    v-model="salesOrderQuery.company"
                    clearable
                    placeholder="company"
                    data-testid="cross-module-sales-order-company-input"
                  />
                </el-form-item>
                <el-form-item label="操作" data-testid="cross-module-sales-order-action-field">
                  <el-button type="primary" data-testid="cross-module-sales-order-query-button" @click="loadSalesOrderTrail">
                    查询链路
                  </el-button>
                </el-form-item>
              </el-form>

              <el-alert
                v-if="salesOrderGuardMessage"
                data-testid="cross-module-sales-order-guarded-state"
                type="warning"
                :closable="false"
                :title="salesOrderGuardMessage"
                style="margin-bottom: 12px"
              />

              <el-alert
                v-if="salesOrderErrorMessage"
                data-testid="cross-module-sales-order-error-state"
                type="error"
                :closable="false"
                :title="salesOrderErrorMessage"
                style="margin-bottom: 12px"
              />

              <el-descriptions v-if="salesOrderTrail" :column="4" border class="summary-block" data-testid="cross-module-sales-order-summary">
                <el-descriptions-item label="销售单">{{ salesOrderTrail.sales_order.sales_order_id }}</el-descriptions-item>
                <el-descriptions-item label="客户">{{ salesOrderTrail.sales_order.customer || '-' }}</el-descriptions-item>
                <el-descriptions-item label="订单数量">{{ formatAmount(salesOrderTrail.summary.ordered_qty) }}</el-descriptions-item>
                <el-descriptions-item label="出库数量">{{ formatAmount(salesOrderTrail.summary.delivered_qty) }}</el-descriptions-item>
                <el-descriptions-item label="质检单数">{{ salesOrderTrail.summary.quality_inspection_count }}</el-descriptions-item>
                <el-descriptions-item label="缺陷数量">{{ formatAmount(salesOrderTrail.summary.defect_qty) }}</el-descriptions-item>
              </el-descriptions>

              <h3 class="section-title">交付/出库事实</h3>
              <el-table
                :data="salesOrderTrail?.delivery_notes || []"
                border
                v-loading="salesOrderLoading"
                data-testid="cross-module-sales-order-delivery-table"
                empty-text="暂无交付出库事实，请调整筛选条件后重试"
              >
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
              <el-table
                :data="salesOrderTrail?.quality_inspections || []"
                border
                v-loading="salesOrderLoading"
                data-testid="cross-module-sales-order-quality-table"
                empty-text="暂无质量检验事实，请调整筛选条件后重试"
              >
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

              <el-empty
                v-if="salesOrderShowEmptyState"
                data-testid="cross-module-sales-order-empty-state"
                description="暂无销售链路事实，请调整筛选条件后重试"
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
  fetchSalesOrderTrail,
  fetchWorkOrderTrail,
  type CrossModuleSalesOrderTrailData,
  type CrossModuleWorkOrderTrailData,
} from '@/api/cross_module'
import { fetchModuleActions } from '@/api/auth'
import { usePermissionStore } from '@/stores/permission'

const permissionStore = usePermissionStore()
const activeTab = ref<'work_order' | 'sales_order'>('work_order')
const workOrderLoading = ref<boolean>(false)
const salesOrderLoading = ref<boolean>(false)
const workOrderTrail = ref<CrossModuleWorkOrderTrailData | null>(null)
const salesOrderTrail = ref<CrossModuleSalesOrderTrailData | null>(null)
const workOrderGuardMessage = ref<string>('')
const workOrderErrorMessage = ref<string>('')
const workOrderQueried = ref<boolean>(false)
const salesOrderGuardMessage = ref<string>('')
const salesOrderErrorMessage = ref<string>('')
const salesOrderQueried = ref<boolean>(false)
const showReadonlyGuide = ref<boolean>(false)
const permissionLoading = ref<boolean>(false)
const salesInventoryReadAllowed = ref<boolean>(false)
const qualityReadAllowed = ref<boolean>(false)

const workOrderQuery = reactive({
  work_order_id: '',
  company: '',
})

const salesOrderQuery = reactive({
  sales_order_id: '',
  company: '',
})

const canRead = computed<boolean>(() => salesInventoryReadAllowed.value && qualityReadAllowed.value)
const workOrderShowEmptyState = computed<boolean>(
  () => workOrderQueried.value && !workOrderLoading.value && !workOrderErrorMessage.value && !workOrderTrail.value,
)
const salesOrderShowEmptyState = computed<boolean>(
  () => salesOrderQueried.value && !salesOrderLoading.value && !salesOrderErrorMessage.value && !salesOrderTrail.value,
)

const formatAmount = (value: string | number | null | undefined): string => {
  if (value === null || value === undefined || value === '') {
    return '-'
  }
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric.toFixed(2) : String(value)
}

const loadWorkOrderTrail = async (): Promise<void> => {
  const workOrderId = workOrderQuery.work_order_id.trim()
  if (!workOrderId) {
    workOrderGuardMessage.value = 'work_order_id 不能为空'
    workOrderErrorMessage.value = ''
    workOrderTrail.value = null
    workOrderQueried.value = false
    ElMessage.warning(workOrderGuardMessage.value)
    return
  }
  workOrderGuardMessage.value = ''
  workOrderErrorMessage.value = ''
  workOrderQueried.value = true
  workOrderLoading.value = true
  try {
    const response = await fetchWorkOrderTrail(workOrderId, {
      company: workOrderQuery.company.trim() || undefined,
    })
    workOrderTrail.value = response.data
  } catch (error) {
    const message = error instanceof Error ? error.message : '工单链路加载失败'
    ElMessage.error(message)
    workOrderErrorMessage.value = message
    workOrderTrail.value = null
  } finally {
    workOrderLoading.value = false
  }
}

const loadSalesOrderTrail = async (): Promise<void> => {
  const salesOrderId = salesOrderQuery.sales_order_id.trim()
  if (!salesOrderId) {
    salesOrderGuardMessage.value = 'sales_order_id 不能为空'
    salesOrderErrorMessage.value = ''
    salesOrderTrail.value = null
    salesOrderQueried.value = false
    ElMessage.warning(salesOrderGuardMessage.value)
    return
  }
  salesOrderGuardMessage.value = ''
  salesOrderErrorMessage.value = ''
  salesOrderQueried.value = true
  salesOrderLoading.value = true
  try {
    const response = await fetchSalesOrderTrail(salesOrderId, {
      company: salesOrderQuery.company.trim() || undefined,
    })
    salesOrderTrail.value = response.data
  } catch (error) {
    const message = error instanceof Error ? error.message : '销售链路加载失败'
    ElMessage.error(message)
    salesOrderErrorMessage.value = message
    salesOrderTrail.value = null
  } finally {
    salesOrderLoading.value = false
  }
}

const toggleReadonlyGuide = (): void => {
  showReadonlyGuide.value = !showReadonlyGuide.value
}

const resolveModuleReadAllowed = (
  moduleName: string,
  payload: {
    actions?: string[]
    button_permissions?: Record<string, unknown>
  },
): boolean => {
  const actionKey = `${moduleName}:read`
  const actions = Array.isArray(payload.actions) ? payload.actions : []
  if (actions.includes(actionKey)) return true

  const buttonPermissions = payload.button_permissions || {}
  const readFlagByModule = buttonPermissions[`${moduleName}_read`]
  if (typeof readFlagByModule === 'boolean' && readFlagByModule) return true
  const genericRead = buttonPermissions.read
  return typeof genericRead === 'boolean' ? genericRead : false
}

const loadReadonlyPermissions = async (): Promise<void> => {
  const [salesResult, qualityResult] = await Promise.all([
    fetchModuleActions({ module: 'sales_inventory' }),
    fetchModuleActions({ module: 'quality' }),
  ])
  salesInventoryReadAllowed.value = resolveModuleReadAllowed('sales_inventory', salesResult.data)
  qualityReadAllowed.value = resolveModuleReadAllowed('quality', qualityResult.data)
}

const refreshReadonlyStatus = async (): Promise<void> => {
  permissionLoading.value = true
  try {
    await permissionStore.loadCurrentUser()
    await loadReadonlyPermissions()
    if (!canRead.value) {
      workOrderTrail.value = null
      salesOrderTrail.value = null
      workOrderGuardMessage.value = ''
      workOrderErrorMessage.value = ''
      workOrderQueried.value = false
      salesOrderGuardMessage.value = ''
      salesOrderErrorMessage.value = ''
      salesOrderQueried.value = false
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
    await loadReadonlyPermissions()
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

.header-actions {
  display: flex;
  gap: 8px;
}

.readonly-guide {
  margin-bottom: 12px;
}

.summary-block {
  margin-bottom: 12px;
}

.section-title {
  margin-top: 18px;
}
</style>
