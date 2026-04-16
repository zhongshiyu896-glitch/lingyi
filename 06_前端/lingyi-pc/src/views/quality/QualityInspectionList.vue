<template>
  <div class="quality-page">
    <el-card shadow="never">
      <template #header>
        <div class="header-row">
          <span>质量检验单列表</span>
          <div class="header-actions">
            <el-button type="primary" :disabled="!canRead" @click="loadRows">查询</el-button>
            <el-button v-if="canExport" :disabled="!canRead" @click="submitExport">导出快照</el-button>
            <el-button v-if="canCreate" type="success" @click="openCreateDialog">创建检验单</el-button>
          </div>
        </div>
      </template>

      <el-form :inline="true" :model="query">
        <el-form-item label="公司">
          <el-input v-model="query.company" clearable placeholder="company" />
        </el-form-item>
        <el-form-item label="物料">
          <el-input v-model="query.item_code" clearable placeholder="item_code" />
        </el-form-item>
        <el-form-item label="供应商">
          <el-input v-model="query.supplier" clearable placeholder="supplier" />
        </el-form-item>
        <el-form-item label="来源类型">
          <el-select v-model="query.source_type" clearable style="width: 180px">
            <el-option label="来料检验" value="incoming_material" />
            <el-option label="外发收货检验" value="subcontract_receipt" />
            <el-option label="成品检验" value="finished_goods" />
            <el-option label="手工检验" value="manual" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.status" clearable style="width: 140px">
            <el-option label="草稿" value="draft" />
            <el-option label="已确认" value="confirmed" />
            <el-option label="已取消" value="cancelled" />
          </el-select>
        </el-form-item>
        <el-form-item label="开始日期">
          <el-date-picker v-model="query.from_date" type="date" value-format="YYYY-MM-DD" clearable />
        </el-form-item>
        <el-form-item label="结束日期">
          <el-date-picker v-model="query.to_date" type="date" value-format="YYYY-MM-DD" clearable />
        </el-form-item>
      </el-form>

      <el-empty v-if="!canRead" description="无质量管理查看权限" />
      <template v-else>
        <el-alert
          v-if="statistics"
          class="summary-alert"
          type="info"
          :closable="false"
          :title="`本页筛选统计：检验 ${statistics.total_count} 单，检验数量 ${formatAmount(statistics.inspected_qty)}，缺陷率 ${formatRate(statistics.defect_rate)}`"
        />

        <el-table :data="rows" border v-loading="loading">
          <el-table-column prop="inspection_no" label="检验单号" min-width="180" />
          <el-table-column prop="company" label="公司" min-width="120" />
          <el-table-column prop="item_code" label="物料" min-width="140" />
          <el-table-column prop="supplier" label="供应商" min-width="140" />
          <el-table-column label="来源" min-width="170">
            <template #default="scope">
              {{ sourceTypeLabel(scope.row.source_type) }} / {{ scope.row.source_id || '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="inspection_date" label="检验日期" width="120" />
          <el-table-column label="检验数量" width="110">
            <template #default="scope">{{ formatAmount(scope.row.inspected_qty) }}</template>
          </el-table-column>
          <el-table-column label="合格数量" width="110">
            <template #default="scope">{{ formatAmount(scope.row.accepted_qty) }}</template>
          </el-table-column>
          <el-table-column label="不合格数量" width="120">
            <template #default="scope">{{ formatAmount(scope.row.rejected_qty) }}</template>
          </el-table-column>
          <el-table-column label="结果" width="110">
            <template #default="scope">
              <el-tag :type="resultTag(scope.row.result)">{{ resultLabel(scope.row.result) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="110">
            <template #default="scope">
              <el-tag :type="statusTag(scope.row.status)">{{ statusLabel(scope.row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" fixed="right" width="100">
            <template #default="scope">
              <el-button link type="primary" @click="goDetail(scope.row.id)">详情</el-button>
            </template>
          </el-table-column>
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

    <el-dialog v-model="createDialogVisible" title="创建质量检验单" width="640px" destroy-on-close>
      <el-form :model="createForm" label-width="120px">
        <el-form-item label="公司" required>
          <el-input v-model="createForm.company" clearable placeholder="company" />
        </el-form-item>
        <el-form-item label="来源类型" required>
          <el-select v-model="createForm.source_type" style="width: 100%">
            <el-option label="来料检验" value="incoming_material" />
            <el-option label="外发收货检验" value="subcontract_receipt" />
            <el-option label="成品检验" value="finished_goods" />
            <el-option label="手工检验" value="manual" />
          </el-select>
        </el-form-item>
        <el-form-item label="来源单号">
          <el-input v-model="createForm.source_id" clearable placeholder="source_id" />
        </el-form-item>
        <el-form-item label="物料" required>
          <el-input v-model="createForm.item_code" clearable placeholder="item_code" />
        </el-form-item>
        <el-form-item label="供应商">
          <el-input v-model="createForm.supplier" clearable placeholder="supplier" />
        </el-form-item>
        <el-form-item label="仓库">
          <el-input v-model="createForm.warehouse" clearable placeholder="warehouse" />
        </el-form-item>
        <el-form-item label="检验日期" required>
          <el-date-picker v-model="createForm.inspection_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <el-form-item label="检验数量" required>
          <el-input v-model="createForm.inspected_qty" clearable placeholder="inspected_qty" />
        </el-form-item>
        <el-form-item label="合格数量" required>
          <el-input v-model="createForm.accepted_qty" clearable placeholder="accepted_qty" />
        </el-form-item>
        <el-form-item label="不合格数量" required>
          <el-input v-model="createForm.rejected_qty" clearable placeholder="rejected_qty" />
        </el-form-item>
        <el-form-item label="缺陷数量">
          <el-input v-model="createForm.defect_qty" clearable placeholder="defect_qty" />
        </el-form-item>
        <el-form-item label="结果">
          <el-select v-model="createForm.result" style="width: 100%">
            <el-option label="待定" value="pending" />
            <el-option label="合格" value="pass" />
            <el-option label="不合格" value="fail" />
            <el-option label="部分合格" value="partial" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="createForm.remark" type="textarea" :rows="3" maxlength="255" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" :disabled="!canCreate" @click="submitCreate">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  createQualityInspection,
  exportQualityInspections,
  fetchQualityInspections,
  fetchQualityStatistics,
  type QualityInspectionCreatePayload,
  type QualityInspectionListItem,
  type QualityStatisticsData,
} from '@/api/quality'
import { usePermissionStore } from '@/stores/permission'

const router = useRouter()
const permissionStore = usePermissionStore()

const loading = ref<boolean>(false)
const creating = ref<boolean>(false)
const createDialogVisible = ref<boolean>(false)
const rows = ref<QualityInspectionListItem[]>([])
const total = ref<number>(0)
const statistics = ref<QualityStatisticsData | null>(null)

const canRead = computed<boolean>(() => permissionStore.state.buttonPermissions.quality_read)
const canCreate = computed<boolean>(() => permissionStore.state.buttonPermissions.quality_create)
const canExport = computed<boolean>(() => permissionStore.state.buttonPermissions.quality_export)

const query = reactive({
  company: '',
  item_code: '',
  supplier: '',
  warehouse: '',
  source_type: '',
  source_id: '',
  status: '',
  from_date: '',
  to_date: '',
  page: 1,
  page_size: 20,
})

const today = new Date().toISOString().slice(0, 10)
const createForm = reactive({
  company: '',
  source_type: 'manual',
  source_id: '',
  item_code: '',
  supplier: '',
  warehouse: '',
  inspection_date: today,
  inspected_qty: '0',
  accepted_qty: '0',
  rejected_qty: '0',
  defect_qty: '0',
  result: 'pending',
  remark: '',
})

const clean = (value: string): string | undefined => value.trim() || undefined

const buildFilterQuery = () => ({
  company: clean(query.company),
  item_code: clean(query.item_code),
  supplier: clean(query.supplier),
  warehouse: clean(query.warehouse),
  source_type: clean(query.source_type),
  source_id: clean(query.source_id),
  status: clean(query.status),
  from_date: clean(query.from_date),
  to_date: clean(query.to_date),
})

const formatAmount = (value: string | number | null | undefined): string => {
  if (value === null || value === undefined || value === '') return '-'
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric.toFixed(2) : String(value)
}

const formatRate = (value: string | number | null | undefined): string => {
  if (value === null || value === undefined || value === '') return '-'
  const numeric = Number(value)
  return Number.isFinite(numeric) ? `${(numeric * 100).toFixed(2)}%` : String(value)
}

const sourceTypeLabel = (value: string): string => {
  if (value === 'incoming_material') return '来料检验'
  if (value === 'subcontract_receipt') return '外发收货检验'
  if (value === 'finished_goods') return '成品检验'
  if (value === 'manual') return '手工检验'
  return value || '-'
}

const resultLabel = (value: string): string => {
  if (value === 'pending') return '待定'
  if (value === 'pass') return '合格'
  if (value === 'fail') return '不合格'
  if (value === 'partial') return '部分合格'
  return value || '-'
}

const statusLabel = (value: string): string => {
  if (value === 'draft') return '草稿'
  if (value === 'confirmed') return '已确认'
  if (value === 'cancelled') return '已取消'
  return value || '-'
}

const resultTag = (value: string): 'success' | 'danger' | 'warning' | 'info' => {
  if (value === 'pass') return 'success'
  if (value === 'fail') return 'danger'
  if (value === 'partial') return 'warning'
  return 'info'
}

const statusTag = (value: string): 'success' | 'danger' | 'warning' | 'info' => {
  if (value === 'draft') return 'warning'
  if (value === 'confirmed') return 'success'
  if (value === 'cancelled') return 'danger'
  return 'info'
}

const resetRows = (): void => {
  rows.value = []
  total.value = 0
  statistics.value = null
}

const loadRows = async (): Promise<void> => {
  if (!canRead.value) {
    resetRows()
    return
  }

  loading.value = true
  try {
    const filters = buildFilterQuery()
    const result = await fetchQualityInspections({ ...filters, page: query.page, page_size: query.page_size })
    rows.value = result.data.items
    total.value = result.data.total
    const stats = await fetchQualityStatistics(filters)
    statistics.value = stats.data
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    loading.value = false
  }
}

const goDetail = (id: number): void => {
  router.push({ path: '/quality/inspections/detail', query: { id: String(id) } })
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

const openCreateDialog = (): void => {
  createDialogVisible.value = true
}

const buildCreatePayload = (): QualityInspectionCreatePayload => ({
  company: createForm.company.trim(),
  source_type: createForm.source_type,
  source_id: clean(createForm.source_id) || null,
  item_code: createForm.item_code.trim(),
  supplier: clean(createForm.supplier) || null,
  warehouse: clean(createForm.warehouse) || null,
  inspection_date: createForm.inspection_date,
  inspected_qty: createForm.inspected_qty,
  accepted_qty: createForm.accepted_qty,
  rejected_qty: createForm.rejected_qty,
  defect_qty: createForm.defect_qty,
  result: createForm.result,
  remark: clean(createForm.remark) || null,
})

const submitCreate = async (): Promise<void> => {
  if (!canCreate.value) return
  creating.value = true
  try {
    const result = await createQualityInspection(buildCreatePayload())
    ElMessage.success(`质量检验单已创建：${result.data.inspection_no}`)
    createDialogVisible.value = false
    await loadRows()
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    creating.value = false
  }
}

const submitExport = async (): Promise<void> => {
  if (!canExport.value || !canRead.value) return
  try {
    const result = await exportQualityInspections(buildFilterQuery())
    ElMessage.success(`质量导出快照已生成：${result.data.total} 行`)
  } catch (error) {
    ElMessage.error((error as Error).message)
  }
}

onMounted(async () => {
  try {
    await permissionStore.loadCurrentUser()
    await permissionStore.loadModuleActions('quality')
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
.quality-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.summary-alert {
  margin-bottom: 12px;
}

.pager {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}
</style>
