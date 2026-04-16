<template>
  <div class="quality-detail-page">
    <el-card shadow="never" v-loading="loading">
      <template #header>
        <div class="header-row">
          <span>质量检验单详情</span>
          <el-button @click="backToList">返回列表</el-button>
        </div>
      </template>

      <el-empty v-if="!canRead" description="无质量管理查看权限" />
      <el-empty v-else-if="!inspectionId" description="缺少质量检验单 ID" />
      <template v-else>
        <el-empty v-if="!detail" description="未找到质量检验单" />
        <template v-else>
          <el-descriptions :column="3" border>
            <el-descriptions-item label="检验单号">{{ detail.inspection_no }}</el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="statusTag(detail.status)">{{ statusLabel(detail.status) }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="结果">
              <el-tag :type="resultTag(detail.result)">{{ resultLabel(detail.result) }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="公司">{{ detail.company }}</el-descriptions-item>
            <el-descriptions-item label="物料">{{ detail.item_code }}</el-descriptions-item>
            <el-descriptions-item label="供应商">{{ detail.supplier || '-' }}</el-descriptions-item>
            <el-descriptions-item label="来源类型">{{ sourceTypeLabel(detail.source_type) }}</el-descriptions-item>
            <el-descriptions-item label="来源单号">{{ detail.source_id || '-' }}</el-descriptions-item>
            <el-descriptions-item label="仓库">{{ detail.warehouse || '-' }}</el-descriptions-item>
            <el-descriptions-item label="检验日期">{{ detail.inspection_date }}</el-descriptions-item>
            <el-descriptions-item label="检验数量">{{ formatAmount(detail.inspected_qty) }}</el-descriptions-item>
            <el-descriptions-item label="合格数量">{{ formatAmount(detail.accepted_qty) }}</el-descriptions-item>
            <el-descriptions-item label="不合格数量">{{ formatAmount(detail.rejected_qty) }}</el-descriptions-item>
            <el-descriptions-item label="缺陷数量">{{ formatAmount(detail.defect_qty) }}</el-descriptions-item>
            <el-descriptions-item label="缺陷率">{{ formatRate(detail.defect_rate) }}</el-descriptions-item>
            <el-descriptions-item label="备注">{{ detail.remark || '-' }}</el-descriptions-item>
          </el-descriptions>

          <div class="action-row">
            <el-button v-if="canUpdate" type="primary" :loading="updating" @click="openUpdateDialog">
              更新检验结果
            </el-button>
            <el-button v-if="canConfirm" type="success" :loading="confirming" @click="openConfirmDialog">
              确认检验单
            </el-button>
            <el-button v-if="canCancel" type="danger" :loading="cancelling" @click="openCancelDialog">
              取消检验单
            </el-button>
          </div>
        </template>
      </template>
    </el-card>

    <el-card shadow="never">
      <template #header>
        <span>检验明细</span>
      </template>
      <el-table :data="detail?.items || []" border>
        <el-table-column prop="line_no" label="行号" width="70" />
        <el-table-column prop="item_code" label="物料" min-width="140" />
        <el-table-column label="抽样数量" width="110">
          <template #default="scope">{{ formatAmount(scope.row.sample_qty) }}</template>
        </el-table-column>
        <el-table-column label="合格数量" width="110">
          <template #default="scope">{{ formatAmount(scope.row.accepted_qty) }}</template>
        </el-table-column>
        <el-table-column label="不合格数量" width="120">
          <template #default="scope">{{ formatAmount(scope.row.rejected_qty) }}</template>
        </el-table-column>
        <el-table-column label="缺陷数量" width="110">
          <template #default="scope">{{ formatAmount(scope.row.defect_qty) }}</template>
        </el-table-column>
        <el-table-column label="结果" width="110">
          <template #default="scope">{{ resultLabel(scope.row.result) }}</template>
        </el-table-column>
        <el-table-column prop="remark" label="备注" min-width="160" />
      </el-table>
    </el-card>

    <el-card shadow="never">
      <template #header>
        <span>缺陷记录</span>
      </template>
      <el-table :data="detail?.defects || []" border>
        <el-table-column prop="defect_code" label="缺陷编码" min-width="120" />
        <el-table-column prop="defect_name" label="缺陷名称" min-width="160" />
        <el-table-column label="缺陷数量" width="110">
          <template #default="scope">{{ formatAmount(scope.row.defect_qty) }}</template>
        </el-table-column>
        <el-table-column prop="severity" label="严重度" width="110" />
        <el-table-column prop="remark" label="备注" min-width="160" />
      </el-table>
    </el-card>

    <el-card shadow="never">
      <template #header>
        <span>操作日志</span>
      </template>
      <el-table :data="detail?.logs || []" border>
        <el-table-column prop="action" label="动作" min-width="120" />
        <el-table-column prop="from_status" label="原状态" min-width="120" />
        <el-table-column prop="to_status" label="新状态" min-width="120" />
        <el-table-column prop="operator" label="操作人" min-width="120" />
        <el-table-column prop="remark" label="备注" min-width="180" />
        <el-table-column prop="operated_at" label="时间" min-width="180" />
      </el-table>
    </el-card>

    <el-dialog v-model="updateDialogVisible" title="更新检验结果" width="520px" destroy-on-close>
      <el-form :model="updateForm" label-width="120px">
        <el-form-item label="合格数量">
          <el-input v-model="updateForm.accepted_qty" clearable />
        </el-form-item>
        <el-form-item label="不合格数量">
          <el-input v-model="updateForm.rejected_qty" clearable />
        </el-form-item>
        <el-form-item label="缺陷数量">
          <el-input v-model="updateForm.defect_qty" clearable />
        </el-form-item>
        <el-form-item label="结果">
          <el-select v-model="updateForm.result" style="width: 100%">
            <el-option label="待定" value="pending" />
            <el-option label="合格" value="pass" />
            <el-option label="不合格" value="fail" />
            <el-option label="部分合格" value="partial" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="updateForm.remark" type="textarea" :rows="3" maxlength="255" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="updateDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="updating" :disabled="!canUpdate" @click="submitUpdate">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="confirmDialogVisible" title="确认检验单" width="480px" destroy-on-close>
      <el-form :model="confirmForm" label-width="120px">
        <el-form-item label="备注">
          <el-input v-model="confirmForm.remark" type="textarea" :rows="3" maxlength="200" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="confirmDialogVisible = false">取消</el-button>
        <el-button type="success" :loading="confirming" :disabled="!canConfirm" @click="submitConfirm">确认</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="cancelDialogVisible" title="取消检验单" width="480px" destroy-on-close>
      <el-form :model="cancelForm" label-width="120px">
        <el-form-item label="取消原因">
          <el-input v-model="cancelForm.reason" type="textarea" :rows="3" maxlength="200" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="cancelDialogVisible = false">返回</el-button>
        <el-button type="danger" :loading="cancelling" :disabled="!canCancel" @click="submitCancel">确认取消</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  cancelQualityInspection,
  confirmQualityInspection,
  fetchQualityInspectionDetail,
  updateQualityInspection,
  type QualityInspectionDetailData,
} from '@/api/quality'
import { usePermissionStore } from '@/stores/permission'

const route = useRoute()
const router = useRouter()
const permissionStore = usePermissionStore()

const loading = ref<boolean>(false)
const updating = ref<boolean>(false)
const confirming = ref<boolean>(false)
const cancelling = ref<boolean>(false)
const detail = ref<QualityInspectionDetailData | null>(null)

const updateDialogVisible = ref<boolean>(false)
const confirmDialogVisible = ref<boolean>(false)
const cancelDialogVisible = ref<boolean>(false)

const updateForm = ref({ accepted_qty: '0', rejected_qty: '0', defect_qty: '0', result: 'pending', remark: '' })
const confirmForm = ref({ remark: '' })
const cancelForm = ref({ reason: '' })

const inspectionId = computed<number>(() => Number(route.query.id || '0'))
const canRead = computed<boolean>(() => permissionStore.state.buttonPermissions.quality_read)
const canUpdatePermission = computed<boolean>(() => permissionStore.state.buttonPermissions.quality_update)
const canConfirmPermission = computed<boolean>(() => permissionStore.state.buttonPermissions.quality_confirm)
const canCancelPermission = computed<boolean>(() => permissionStore.state.buttonPermissions.quality_cancel)
const isDraft = computed<boolean>(() => detail.value?.status === 'draft')
const isCancellable = computed<boolean>(() => detail.value?.status === 'draft' || detail.value?.status === 'confirmed')
const canUpdate = computed<boolean>(() => canUpdatePermission.value && isDraft.value)
const canConfirm = computed<boolean>(() => canConfirmPermission.value && isDraft.value)
const canCancel = computed<boolean>(() => canCancelPermission.value && isCancellable.value)

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

const loadDetail = async (): Promise<void> => {
  if (!canRead.value || !inspectionId.value) {
    detail.value = null
    return
  }
  loading.value = true
  try {
    const result = await fetchQualityInspectionDetail(inspectionId.value)
    detail.value = result.data
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    loading.value = false
  }
}

const openUpdateDialog = (): void => {
  if (!detail.value) return
  updateForm.value = {
    accepted_qty: String(detail.value.accepted_qty ?? '0'),
    rejected_qty: String(detail.value.rejected_qty ?? '0'),
    defect_qty: String(detail.value.defect_qty ?? '0'),
    result: detail.value.result || 'pending',
    remark: detail.value.remark || '',
  }
  updateDialogVisible.value = true
}

const openConfirmDialog = (): void => {
  confirmForm.value = { remark: '' }
  confirmDialogVisible.value = true
}

const openCancelDialog = (): void => {
  cancelForm.value = { reason: '' }
  cancelDialogVisible.value = true
}

const submitUpdate = async (): Promise<void> => {
  if (!canUpdate.value || !detail.value) return
  updating.value = true
  try {
    await updateQualityInspection(detail.value.id, {
      accepted_qty: updateForm.value.accepted_qty,
      rejected_qty: updateForm.value.rejected_qty,
      defect_qty: updateForm.value.defect_qty,
      result: updateForm.value.result,
      remark: updateForm.value.remark.trim() || null,
    })
    ElMessage.success('质量检验单已更新')
    updateDialogVisible.value = false
    await loadDetail()
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    updating.value = false
  }
}

const submitConfirm = async (): Promise<void> => {
  if (!canConfirm.value || !detail.value) return
  confirming.value = true
  try {
    await confirmQualityInspection(detail.value.id, { remark: confirmForm.value.remark.trim() || null })
    ElMessage.success('质量检验单已确认')
    confirmDialogVisible.value = false
    await loadDetail()
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    confirming.value = false
  }
}

const submitCancel = async (): Promise<void> => {
  if (!canCancel.value || !detail.value) return
  cancelling.value = true
  try {
    await cancelQualityInspection(detail.value.id, { reason: cancelForm.value.reason.trim() || null })
    ElMessage.success('质量检验单已取消')
    cancelDialogVisible.value = false
    await loadDetail()
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    cancelling.value = false
  }
}

const backToList = (): void => {
  router.push({ path: '/quality/inspections' })
}

onMounted(async () => {
  try {
    await permissionStore.loadCurrentUser()
    await permissionStore.loadModuleActions('quality')
  } catch (error) {
    ElMessage.error((error as Error).message)
    return
  }
  await loadDetail()
})
</script>

<style scoped>
.quality-detail-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.action-row {
  margin-top: 16px;
  display: flex;
  gap: 8px;
}
</style>
