<template>
  <div class="subcontract-detail-page" data-testid="subcontract-detail-page">
    <el-card shadow="never" v-loading="loading" data-testid="subcontract-detail-main-card">
      <template #header>
        <div class="header-row" data-testid="subcontract-detail-header">
          <span data-testid="subcontract-detail-title">外发单详情</span>
          <el-button data-testid="subcontract-detail-back" @click="goBack">返回</el-button>
        </div>
      </template>
      <el-skeleton v-if="!permissionReady" :rows="4" animated data-testid="subcontract-detail-loading-state" />
      <el-empty
        v-else-if="!canRead"
        description="无外发查看权限"
        data-testid="subcontract-detail-permission-state"
      />
      <template v-else>
        <el-empty
          v-if="missingOrderId"
          description="请从外发单列表进入详情页"
          data-testid="subcontract-detail-missing-id-state"
        />
        <el-alert
          v-else-if="loadError"
          :title="loadError"
          type="error"
          show-icon
          :closable="false"
          data-testid="subcontract-detail-error-state"
        />
        <el-empty v-else-if="!detail" description="未找到外发单详情" data-testid="subcontract-detail-empty-state" />
        <template v-else>
          <el-descriptions :column="3" border data-testid="subcontract-detail-main-fields">
            <el-descriptions-item label="外发单号">
              <span data-testid="subcontract-detail-field-subcontract-no">{{ detail.subcontract_no }}</span>
            </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag data-testid="subcontract-detail-status-tag">{{ statusLabel(detail.status) }}</el-tag>
            <el-tag
              v-if="isScopeBlocked"
              type="danger"
              class="scope-tag"
              data-testid="subcontract-detail-scope-blocked-tag"
            >
              权限范围异常
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="公司">{{ detail.company || '-' }}</el-descriptions-item>
          <el-descriptions-item label="加工厂">{{ detail.supplier }}</el-descriptions-item>
          <el-descriptions-item label="款式">{{ detail.item_code }}</el-descriptions-item>
          <el-descriptions-item label="工序">{{ detail.process_name }}</el-descriptions-item>
          <el-descriptions-item label="计划数量">{{ detail.planned_qty }}</el-descriptions-item>
          <el-descriptions-item label="已发料">{{ detail.issued_qty }}</el-descriptions-item>
          <el-descriptions-item label="已回料">{{ detail.received_qty }}</el-descriptions-item>
          <el-descriptions-item label="已验货">{{ detail.inspected_qty }}</el-descriptions-item>
          <el-descriptions-item label="不合格数量">{{ detail.rejected_qty }}</el-descriptions-item>
          <el-descriptions-item label="合格数量">{{ detail.accepted_qty }}</el-descriptions-item>
          <el-descriptions-item label="加工单价">{{ detail.subcontract_rate }}</el-descriptions-item>
          <el-descriptions-item label="验货总金额">{{ detail.gross_amount }}</el-descriptions-item>
          <el-descriptions-item label="扣款金额">{{ detail.deduction_amount }}</el-descriptions-item>
          <el-descriptions-item label="净应付金额">{{ detail.net_amount }}</el-descriptions-item>
          <el-descriptions-item label="发料同步状态">
            <span data-testid="subcontract-detail-issue-sync-status">
              {{ stockSyncLabel(detail.latest_issue_sync_status) || '-' }}
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="回料同步状态">
            <span data-testid="subcontract-detail-receipt-sync-status">
              {{ stockSyncLabel(detail.latest_receipt_sync_status) || '-' }}
            </span>
          </el-descriptions-item>
          </el-descriptions>

          <div class="action-row" data-testid="subcontract-detail-guarded-actions">
            <el-button
              data-testid="subcontract-detail-action-issue"
              data-action-type="write"
              data-write-guard="guarded:readonly"
              @click="guardedWriteAction('发料')"
            >
              发料
            </el-button>
            <el-button
              data-testid="subcontract-detail-action-receipt"
              data-action-type="write"
              data-write-guard="guarded:readonly"
              @click="guardedWriteAction('回料')"
            >
              回料
            </el-button>
            <el-button
              data-testid="subcontract-detail-action-inspection"
              data-action-type="write"
              data-write-guard="guarded:readonly"
              @click="guardedWriteAction('验货')"
            >
              验货
            </el-button>
            <el-button
              data-testid="subcontract-detail-action-settlement"
              data-action-type="write"
              data-write-guard="guarded:readonly"
              @click="guardedWriteAction('结算')"
            >
              结算
            </el-button>
            <el-button
              data-testid="subcontract-detail-action-retry-sync"
              data-action-type="write"
              data-write-guard="guarded:readonly"
              @click="guardedWriteAction('同步重试')"
            >
              同步重试
            </el-button>
            <el-button
              data-testid="subcontract-detail-action-export"
              data-action-type="write"
              data-write-guard="guarded:readonly"
              @click="guardedWriteAction('导出')"
            >
              导出
            </el-button>
            <el-button
              data-testid="subcontract-detail-action-print"
              data-action-type="write"
              data-write-guard="guarded:readonly"
              @click="guardedWriteAction('打印')"
            >
              打印
            </el-button>
          </div>

          <el-alert
            v-if="guardedFeedback"
            :title="guardedFeedback"
            type="warning"
            :closable="false"
            show-icon
            data-testid="subcontract-detail-guarded-feedback"
          />

          <p class="permission-tip" data-testid="subcontract-detail-permission-or-disabled-state">
            当前页面为只读模式，写动作及导出/打印入口已禁用。
          </p>
        </template>
      </template>
    </el-card>

    <el-card v-if="canRead" shadow="never" data-testid="subcontract-detail-readonly-hint-card">
      <el-alert
        title="当前页面为只读履约投影基线，普通前端已冻结新建外发单、发料、回料、验货和同步重试入口。"
        type="info"
        :closable="false"
        show-icon
      />
    </el-card>

    <el-card v-if="canRead && detail" shadow="never" data-testid="subcontract-detail-receipt-section">
      <template #header><span>回料批次</span></template>
      <el-table
        :data="detail?.receipts || []"
        border
        empty-text="暂无回料批次数据"
        data-testid="subcontract-detail-receipt-table"
      >
        <el-table-column prop="receipt_batch_no" label="回料批次" min-width="160" />
        <el-table-column prop="receipt_warehouse" label="回料仓" min-width="120" />
        <el-table-column prop="received_qty" label="回料数量" width="120" />
        <el-table-column label="同步状态" width="120">
          <template #default="scope">
            <span data-testid="subcontract-detail-receipt-sync-tag">
              {{ stockSyncLabel(scope.row.sync_status) || '-' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="stock_entry_name" label="Stock Entry" min-width="180" />
      </el-table>
    </el-card>

    <el-card v-if="canRead && detail" shadow="never" data-testid="subcontract-detail-inspection-section">
      <template #header><span>验货明细</span></template>
      <el-table
        :data="detail?.inspections || []"
        border
        empty-text="暂无验货明细数据"
        data-testid="subcontract-detail-inspection-table"
      >
        <el-table-column prop="inspection_no" label="验货单号" min-width="180" />
        <el-table-column prop="receipt_batch_no" label="回料批次" min-width="160" />
        <el-table-column prop="inspected_qty" label="验货数量" width="110" />
        <el-table-column prop="accepted_qty" label="合格数量" width="110" />
        <el-table-column prop="rejected_qty" label="不合格数量" width="120" />
        <el-table-column prop="gross_amount" label="验货总金额" width="120" />
        <el-table-column prop="deduction_amount" label="扣款金额" width="120" />
        <el-table-column prop="net_amount" label="净应付金额" width="120" />
        <el-table-column prop="inspected_by" label="验货人" width="120" />
        <el-table-column prop="inspected_at" label="验货时间" min-width="180" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { fetchSubcontractOrderDetail, type SubcontractOrderDetailData } from '@/api/subcontract'
import { usePermissionStore } from '@/stores/permission'

const route = useRoute()
const router = useRouter()
const permissionStore = usePermissionStore()
const detail = ref<SubcontractOrderDetailData | null>(null)
const missingOrderId = ref<boolean>(false)
const loading = ref<boolean>(false)
const permissionReady = ref<boolean>(false)
const loadError = ref<string>('')
const guardedFeedback = ref<string>('')

const canRead = computed<boolean>(() => permissionStore.state.buttonPermissions.read)
const orderId = computed<number>(() => Number(route.query.id || '0'))
const hasValidOrderId = computed<boolean>(() => Number.isInteger(orderId.value) && orderId.value > 0)
const isScopeBlocked = computed<boolean>(() => detail.value?.resource_scope_status === 'blocked_scope')

const stockSyncLabel = (value?: string | null): string => {
  if (!value) return ''
  const labels: Record<string, string> = {
    pending: '待同步',
    processing: '同步中',
    succeeded: '已同步',
    failed: '同步失败',
    dead: '死信',
    blocked_scope: '范围阻断',
  }
  return labels[value] || value
}

const statusLabel = (value: string): string => {
  const labels: Record<string, string> = {
    draft: '草稿',
    issued: '已发料',
    processing: '加工中',
    waiting_receive: '待回料',
    waiting_inspection: '待验货',
    completed: '已完成',
    cancelled: '已取消',
  }
  return labels[value] || value
}

const loadDetail = async (): Promise<void> => {
  guardedFeedback.value = ''
  loadError.value = ''
  if (!canRead.value) {
    detail.value = null
    missingOrderId.value = false
    return
  }
  if (!hasValidOrderId.value) {
    detail.value = null
    missingOrderId.value = true
    return
  }
  missingOrderId.value = false
  loading.value = true
  try {
    const result = await fetchSubcontractOrderDetail(orderId.value)
    detail.value = result.data
  } catch (error) {
    detail.value = null
    const message = (error as Error).message || '详情加载失败'
    loadError.value = `外发单详情加载失败：${message}`
    ElMessage.error(loadError.value)
  } finally {
    loading.value = false
  }
}

const guardedWriteAction = (actionName: string): void => {
  guardedFeedback.value = `当前为只读模式，${actionName}已禁用。`
  ElMessage.warning(guardedFeedback.value)
}

const goBack = (): void => {
  router.push('/subcontract/list')
}

watch(
  () => orderId.value,
  async () => {
    await loadDetail()
  },
)

onMounted(async () => {
  try {
    await permissionStore.loadCurrentUser()
    await permissionStore.loadModuleActions('subcontract')
  } catch (error) {
    const message = (error as Error).message || '权限加载失败'
    loadError.value = message
    ElMessage.error(message)
  } finally {
    permissionReady.value = true
  }
  await loadDetail()
})
</script>

<style scoped>
.subcontract-detail-page {
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
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.permission-tip {
  margin-top: 8px;
  color: var(--el-text-color-secondary);
}

.scope-tag {
  margin-left: 8px;
}
</style>
