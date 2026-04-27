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
              编辑草稿
            </el-button>
            <el-button v-if="canUpdate" type="warning" :loading="defecting" @click="openDefectDialog">
              录入缺陷
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
      <el-table :data="detail?.items || []" border empty-text="暂无检验明细">
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
      <el-table :data="detail?.defects || []" border empty-text="暂无缺陷记录">
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
      <el-table :data="detail?.logs || []" border empty-text="暂无操作日志">
        <el-table-column prop="action" label="动作" min-width="120" />
        <el-table-column prop="from_status" label="原状态" min-width="120" />
        <el-table-column prop="to_status" label="新状态" min-width="120" />
        <el-table-column prop="operator" label="操作人" min-width="120" />
        <el-table-column prop="remark" label="备注" min-width="180" />
        <el-table-column prop="operated_at" label="时间" min-width="180" />
      </el-table>
    </el-card>

    <el-dialog v-model="updateDialogVisible" title="编辑草稿" width="520px" destroy-on-close>
      <el-form :model="updateForm" label-width="120px">
        <el-form-item label="合格数量">
          <el-input v-model="updateForm.accepted_qty" clearable placeholder="请输入合格数量" />
        </el-form-item>
        <el-form-item label="不合格数量">
          <el-input v-model="updateForm.rejected_qty" clearable placeholder="请输入不合格数量" />
        </el-form-item>
        <el-form-item label="缺陷数量">
          <el-input v-model="updateForm.defect_qty" clearable placeholder="请输入缺陷数量" />
        </el-form-item>
        <el-form-item label="结果">
          <el-select v-model="updateForm.result" placeholder="请选择结果" style="width: 100%">
            <el-option label="待定" value="pending" />
            <el-option label="合格" value="pass" />
            <el-option label="不合格" value="fail" />
            <el-option label="部分合格" value="partial" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input
            v-model="updateForm.remark"
            type="textarea"
            :rows="3"
            maxlength="255"
            show-word-limit
            placeholder="请输入备注"
            aria-label="检验更新备注"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="updateDialogVisible = false">取消</el-button>
        <el-button
          type="primary"
          :loading="updating"
          :disabled="!canUpdate"
          aria-label="保存检验更新"
          @click="submitUpdate"
        >
          保存
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="defectDialogVisible" title="录入缺陷" width="520px" destroy-on-close>
      <el-form :model="defectForm" label-width="120px">
        <el-form-item label="缺陷编码" required>
          <el-input v-model="defectForm.defect_code" clearable placeholder="请输入缺陷编码" />
        </el-form-item>
        <el-form-item label="缺陷名称" required>
          <el-input v-model="defectForm.defect_name" clearable placeholder="请输入缺陷名称" />
        </el-form-item>
        <el-form-item label="缺陷数量" required>
          <el-input v-model="defectForm.defect_qty" clearable placeholder="请输入缺陷数量" />
        </el-form-item>
        <el-form-item label="严重度">
          <el-select
            v-model="defectForm.severity"
            placeholder="请选择严重度"
            style="width: 100%"
            aria-label="缺陷严重度"
          >
            <el-option label="轻微" value="minor" />
            <el-option label="一般" value="major" />
            <el-option label="严重" value="critical" />
          </el-select>
        </el-form-item>
        <el-form-item label="明细行号">
          <el-input v-model="defectForm.item_line_no" clearable placeholder="可选，填 1/2/3 ..." />
        </el-form-item>
        <el-form-item label="备注">
          <el-input
            v-model="defectForm.remark"
            type="textarea"
            :rows="3"
            maxlength="255"
            show-word-limit
            placeholder="请输入备注"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="defectDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="defecting" :disabled="!canUpdate" @click="submitDefect">提交</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="confirmDialogVisible" title="确认检验单" width="480px" destroy-on-close>
      <el-form label-width="120px">
        <el-form-item label="确认备注">
          <el-input
            v-model="confirmRemark"
            type="textarea"
            :rows="3"
            maxlength="200"
            show-word-limit
            placeholder="请输入确认备注"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="confirmDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="confirming" :disabled="!canConfirm" @click="submitConfirm">确认</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="cancelDialogVisible" title="取消检验单" width="480px" destroy-on-close>
      <el-form label-width="120px">
        <el-form-item label="取消原因">
          <el-input
            v-model="cancelReason"
            type="textarea"
            :rows="3"
            maxlength="200"
            show-word-limit
            placeholder="请输入取消原因"
          />
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
  addDefectRecord,
  cancelQualityInspection,
  confirmQualityInspection,
  fetchQualityInspectionDetail,
  updateDraftInspection,
  type QualityInspectionDetailData,
} from '@/api/quality'
import { usePermissionStore } from '@/stores/permission'

const route = useRoute()
const router = useRouter()
const permissionStore = usePermissionStore()

const loading = ref<boolean>(false)
const updating = ref<boolean>(false)
const defecting = ref<boolean>(false)
const confirming = ref<boolean>(false)
const cancelling = ref<boolean>(false)
const detail = ref<QualityInspectionDetailData | null>(null)

const updateDialogVisible = ref<boolean>(false)
const defectDialogVisible = ref<boolean>(false)
const confirmDialogVisible = ref<boolean>(false)
const cancelDialogVisible = ref<boolean>(false)

const updateForm = ref({ accepted_qty: '0', rejected_qty: '0', defect_qty: '0', result: 'pending', remark: '' })
const defectForm = ref({ defect_code: '', defect_name: '', defect_qty: '0', severity: 'minor', item_line_no: '', remark: '' })
const confirmRemark = ref<string>('')
const cancelReason = ref<string>('')

const inspectionId = computed<number>(() => Number(route.query.id || '0'))
const canRead = computed<boolean>(() => permissionStore.state.buttonPermissions.quality_read)
const canUpdatePermission = computed<boolean>(() => permissionStore.state.buttonPermissions.quality_update)
const canConfirmPermission = computed<boolean>(() => permissionStore.state.buttonPermissions.quality_confirm)
const canCancelPermission = computed<boolean>(() => permissionStore.state.buttonPermissions.quality_cancel)
const canUpdate = computed<boolean>(() => canUpdatePermission.value && detail.value?.status === 'draft')
const canConfirm = computed<boolean>(() => canConfirmPermission.value && detail.value?.status === 'draft')
const canCancel = computed<boolean>(() => canCancelPermission.value && detail.value?.status === 'confirmed')

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

const submitUpdate = async (): Promise<void> => {
  if (!canUpdate.value || !detail.value) return
  updating.value = true
  try {
    await updateDraftInspection(detail.value.id, {
      accepted_qty: updateForm.value.accepted_qty,
      rejected_qty: updateForm.value.rejected_qty,
      defect_qty: updateForm.value.defect_qty,
      result: updateForm.value.result,
      remark: updateForm.value.remark.trim() || null,
    })
    ElMessage.success('草稿质检单已更新')
    updateDialogVisible.value = false
    await loadDetail()
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    updating.value = false
  }
}

const openDefectDialog = (): void => {
  defectForm.value = { defect_code: '', defect_name: '', defect_qty: '0', severity: 'minor', item_line_no: '', remark: '' }
  defectDialogVisible.value = true
}

const openConfirmDialog = (): void => {
  confirmRemark.value = ''
  confirmDialogVisible.value = true
}

const openCancelDialog = (): void => {
  cancelReason.value = ''
  cancelDialogVisible.value = true
}

const submitDefect = async (): Promise<void> => {
  if (!canUpdate.value || !detail.value) return
  defecting.value = true
  try {
    await addDefectRecord(detail.value.id, {
      defects: [
        {
          defect_code: defectForm.value.defect_code.trim(),
          defect_name: defectForm.value.defect_name.trim(),
          defect_qty: defectForm.value.defect_qty,
          severity: defectForm.value.severity,
          item_line_no: defectForm.value.item_line_no.trim() ? Number(defectForm.value.item_line_no.trim()) : null,
          remark: defectForm.value.remark.trim() || null,
        },
      ],
    })
    ElMessage.success('缺陷已录入')
    defectDialogVisible.value = false
    await loadDetail()
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    defecting.value = false
  }
}

const submitConfirm = async (): Promise<void> => {
  if (!canConfirm.value || !detail.value) return
  confirming.value = true
  try {
    await confirmQualityInspection(detail.value.id, confirmRemark.value.trim() || null)
    ElMessage.success('检验单已确认')
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
    await cancelQualityInspection(detail.value.id, { reason: cancelReason.value.trim() || null })
    ElMessage.success('检验单已取消')
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
