<template>
  <div class="quality-detail-page" data-testid="quality-inspection-detail-page">
    <el-card shadow="never" v-loading="loading" data-testid="quality-inspection-detail-card">
      <template #header>
        <div class="header-row" data-testid="quality-inspection-detail-header">
          <span data-testid="quality-inspection-detail-title">质量检验单详情</span>
          <el-button data-testid="quality-inspection-detail-back" @click="backToList">返回列表</el-button>
        </div>
      </template>

      <el-alert
        v-if="guardedFeedback"
        :title="guardedFeedback"
        type="warning"
        :closable="false"
        show-icon
        data-testid="quality-inspection-detail-guarded-feedback"
      />

      <el-empty
        v-if="!canRead"
        description="无质量管理查看权限"
        data-testid="quality-inspection-detail-permission-state"
      />
      <el-empty
        v-else-if="!inspectionId"
        description="缺少质量检验单 ID"
        data-testid="quality-inspection-detail-missing-id-state"
      />
      <template v-else>
        <el-alert
          v-if="loadError"
          :title="loadError"
          type="error"
          show-icon
          :closable="false"
          data-testid="quality-inspection-detail-error-state"
        />
        <el-empty
          v-else-if="!detail"
          description="未找到质量检验单"
          data-testid="quality-inspection-detail-empty-state"
        />
        <template v-else>
          <el-descriptions :column="3" border data-testid="quality-inspection-detail-main-fields">
            <el-descriptions-item label="检验单号">
              <span data-testid="quality-inspection-detail-field-inspection-no">{{ detail.inspection_no }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="statusTag(detail.status)" data-testid="quality-inspection-detail-status-tag">
                {{ statusLabel(detail.status) }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="结果">
              <el-tag :type="resultTag(detail.result)" data-testid="quality-inspection-detail-result-tag">
                {{ resultLabel(detail.result) }}
              </el-tag>
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

          <div class="action-row" data-testid="quality-inspection-detail-guarded-actions">
            <el-button
              v-if="canUpdate"
              type="primary"
              :disabled="!canUpdate"
              data-testid="quality-inspection-detail-action-edit"
              data-action-type="write"
              data-write-guard="guarded:readonly"
              @click="submitUpdate"
            >
              编辑草稿
            </el-button>
            <el-button
              v-if="canUpdate"
              type="warning"
              :disabled="!canUpdate"
              data-testid="quality-inspection-detail-action-defect"
              data-action-type="write"
              data-write-guard="guarded:readonly"
              @click="submitDefect"
            >
              录入缺陷
            </el-button>
            <el-button
              v-if="canConfirm"
              type="success"
              :disabled="!canConfirm"
              data-testid="quality-inspection-detail-action-confirm"
              data-action-type="write"
              data-write-guard="guarded:readonly"
              @click="submitConfirm"
            >
              确认检验单
            </el-button>
            <el-button
              v-if="canCancel"
              type="danger"
              :disabled="!canCancel"
              data-testid="quality-inspection-detail-action-cancel"
              data-action-type="write"
              data-write-guard="guarded:readonly"
              @click="submitCancel"
            >
              取消检验单
            </el-button>
          </div>
          <p class="permission-tip" data-testid="quality-inspection-detail-permission-disabled-state">
            {{ permissionStateText }}
          </p>
        </template>
      </template>
    </el-card>

    <el-card v-if="detail" shadow="never" data-testid="quality-inspection-detail-items-section">
      <template #header>
        <span>检验明细</span>
      </template>
      <el-table
        :data="detail.items || []"
        border
        empty-text="暂无检验明细"
        data-testid="quality-inspection-detail-items-table"
      >
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

    <el-card v-if="detail" shadow="never" data-testid="quality-inspection-detail-defects-section">
      <template #header>
        <span>缺陷记录</span>
      </template>
      <el-table
        :data="detail.defects || []"
        border
        empty-text="暂无缺陷记录"
        data-testid="quality-inspection-detail-defects-table"
      >
        <el-table-column prop="defect_code" label="缺陷编码" min-width="120" />
        <el-table-column prop="defect_name" label="缺陷名称" min-width="160" />
        <el-table-column label="缺陷数量" width="110">
          <template #default="scope">{{ formatAmount(scope.row.defect_qty) }}</template>
        </el-table-column>
        <el-table-column prop="severity" label="严重度" width="110" />
        <el-table-column prop="remark" label="备注" min-width="160" />
      </el-table>
    </el-card>

    <el-card v-if="detail" shadow="never" data-testid="quality-inspection-detail-logs-section">
      <template #header>
        <span>操作日志</span>
      </template>
      <el-table
        :data="detail.logs || []"
        border
        empty-text="暂无操作日志"
        data-testid="quality-inspection-detail-logs-table"
      >
        <el-table-column prop="action" label="动作" min-width="120" />
        <el-table-column prop="from_status" label="原状态" min-width="120" />
        <el-table-column prop="to_status" label="新状态" min-width="120" />
        <el-table-column prop="operator" label="操作人" min-width="120" />
        <el-table-column prop="remark" label="备注" min-width="180" />
        <el-table-column prop="operated_at" label="时间" min-width="180" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { fetchQualityInspectionDetail, type QualityInspectionDetailData } from '@/api/quality'
import { usePermissionStore } from '@/stores/permission'

const route = useRoute()
const router = useRouter()
const permissionStore = usePermissionStore()

const loading = ref<boolean>(false)
const detail = ref<QualityInspectionDetailData | null>(null)
const loadError = ref<string>('')
const guardedFeedback = ref<string>('')

const inspectionId = computed<number>(() => Number(route.query.id || '0'))
const canRead = computed<boolean>(() => permissionStore.state.buttonPermissions.quality_read)
const canUpdatePermission = computed<boolean>(() => permissionStore.state.buttonPermissions.quality_update)
const canConfirmPermission = computed<boolean>(() => permissionStore.state.buttonPermissions.quality_confirm)
const canCancelPermission = computed<boolean>(() => permissionStore.state.buttonPermissions.quality_cancel)

const canUpdate = computed<boolean>(() => canUpdatePermission.value && detail.value?.status === 'draft')
const canConfirm = computed<boolean>(() => canConfirmPermission.value && detail.value?.status === 'draft')
const canCancel = computed<boolean>(() => canCancelPermission.value && detail.value?.status === 'confirmed')

const permissionStateText = computed<string>(() => {
  if (!canRead.value) return '当前账号缺少质量检验详情读取权限。'
  if (!canUpdate.value && !canConfirm.value && !canCancel.value) {
    return '写操作入口已禁用（权限或状态不满足）。'
  }
  return '写操作入口处于受控只读模式。'
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

const loadDetail = async (): Promise<void> => {
  guardedFeedback.value = ''
  loadError.value = ''
  if (!canRead.value || !inspectionId.value) {
    detail.value = null
    return
  }
  loading.value = true
  try {
    const result = await fetchQualityInspectionDetail(inspectionId.value)
    detail.value = result.data
  } catch (error) {
    detail.value = null
    const message = (error as Error).message || '详情加载失败'
    loadError.value = `检验详情加载失败：${message}`
    ElMessage.error(loadError.value)
  } finally {
    loading.value = false
  }
}

const guardedWriteAction = (actionName: string): void => {
  if (!detail.value) return
  guardedFeedback.value = `当前为只读模式，${actionName}已禁用。`
  ElMessage.warning(guardedFeedback.value)
}

const submitUpdate = (): void => guardedWriteAction('编辑草稿')
const submitDefect = (): void => guardedWriteAction('录入缺陷')
const submitConfirm = (): void => guardedWriteAction('确认检验单')
const submitCancel = (): void => guardedWriteAction('取消检验单')

const backToList = (): void => {
  router.push({ path: '/quality/inspections' })
}

onMounted(async () => {
  try {
    await permissionStore.loadCurrentUser()
    await permissionStore.loadModuleActions('quality')
  } catch (error) {
    loadError.value = (error as Error).message || '权限加载失败'
    ElMessage.error(loadError.value)
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
  flex-wrap: wrap;
  gap: 8px;
}

.permission-tip {
  margin: 12px 0 0;
  color: #909399;
  font-size: 12px;
}
</style>
