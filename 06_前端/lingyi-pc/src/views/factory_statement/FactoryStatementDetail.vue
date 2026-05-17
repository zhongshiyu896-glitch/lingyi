<template>
  <div class="factory-statement-detail-page" data-testid="factory-statement-detail-page">
    <el-card shadow="never" v-loading="loading" data-testid="factory-statement-detail-main-card">
      <template #header>
        <div class="header-row" data-testid="factory-statement-detail-header">
          <span data-testid="factory-statement-detail-title">加工厂对账单详情</span>
          <el-button data-testid="factory-statement-detail-back" @click="goBack">返回列表</el-button>
        </div>
      </template>

      <el-skeleton v-if="!permissionReady" :rows="4" animated data-testid="factory-statement-detail-loading-state" />
      <el-empty
        v-else-if="!canRead"
        description="无加工厂对账单查看权限"
        data-testid="factory-statement-detail-permission-state"
      />
      <el-empty
        v-else-if="missingStatementId"
        description="请从加工厂对账单列表进入详情页"
        data-testid="factory-statement-detail-missing-id-state"
      />
      <el-alert
        v-else-if="loadError"
        :title="loadError"
        type="error"
        show-icon
        :closable="false"
        data-testid="factory-statement-detail-error-state"
      />
      <template v-else-if="detail">
        <el-descriptions :column="3" border data-testid="factory-statement-detail-main-fields">
          <el-descriptions-item label="对账单号">
            <span data-testid="factory-statement-detail-field-statement-no">{{ detail.statement_no }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="statusTag(detail.statement_status)" data-testid="factory-statement-detail-status-tag">
              {{ statementStatusLabel(detail.statement_status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="供应商">
            <span data-testid="factory-statement-detail-field-supplier">{{ detail.supplier }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="公司">{{ detail.company }}</el-descriptions-item>
          <el-descriptions-item label="期间">{{ detail.from_date }} ~ {{ detail.to_date }}</el-descriptions-item>
          <el-descriptions-item label="来源条数">{{ detail.source_count }}</el-descriptions-item>
          <el-descriptions-item label="加工费">{{ formatAmount(detail.gross_amount) }}</el-descriptions-item>
          <el-descriptions-item label="扣款">{{ formatAmount(detail.deduction_amount) }}</el-descriptions-item>
          <el-descriptions-item label="实付金额">{{ formatAmount(detail.net_amount) }}</el-descriptions-item>
          <el-descriptions-item label="验货总数">{{ formatAmount(detail.inspected_qty) }}</el-descriptions-item>
          <el-descriptions-item label="次品总数">{{ formatAmount(detail.rejected_qty) }}</el-descriptions-item>
          <el-descriptions-item label="次品率">{{ formatRate(detail.rejected_rate) }}</el-descriptions-item>
        </el-descriptions>

        <div class="detail-kpi-grid" data-testid="factory-statement-detail-kpi-grid">
          <div class="detail-kpi-card" data-testid="factory-statement-detail-kpi-items">
            <span class="kpi-label">对账明细行</span>
            <strong class="kpi-value">{{ detailKpis.itemCount }}</strong>
            <small class="kpi-subtext">用于复核加工费拆分</small>
          </div>
          <div class="detail-kpi-card" data-testid="factory-statement-detail-kpi-logs">
            <span class="kpi-label">操作日志行</span>
            <strong class="kpi-value">{{ detailKpis.logCount }}</strong>
            <small class="kpi-subtext">状态变更追踪</small>
          </div>
          <div class="detail-kpi-card" data-testid="factory-statement-detail-kpi-defect-rate">
            <span class="kpi-label">次品率</span>
            <strong class="kpi-value">{{ detailKpis.rejectedRate }}</strong>
            <small class="kpi-subtext">质量风险观察</small>
          </div>
          <div class="detail-kpi-card" data-testid="factory-statement-detail-kpi-payable-readiness">
            <span class="kpi-label">应付同步态</span>
            <strong class="kpi-value">{{ detailKpis.payableSyncState }}</strong>
            <small class="kpi-subtext">仅支持只读跟踪</small>
          </div>
        </div>

        <div class="detail-status-strip" data-testid="factory-statement-detail-status-strip">
          <el-tag :type="statusTag(detail.statement_status)" effect="plain">单据 {{ statementStatusLabel(detail.statement_status) }}</el-tag>
          <el-tag :type="hasActivePayableOutbox ? 'warning' : 'success'" effect="plain">
            Outbox {{ hasActivePayableOutbox ? '同步中/待同步' : '已闭合' }}
          </el-tag>
          <el-tag :type="summaryMissing ? 'danger' : 'info'" effect="plain">
            摘要{{ summaryMissing ? '缺失' : '完整' }}
          </el-tag>
          <el-tag type="info" effect="plain">模式 只读</el-tag>
        </div>

        <el-card shadow="never" class="outbox-card" data-testid="factory-statement-detail-outbox-section">
          <template #header>
            <span>应付 / Outbox 同步状态</span>
          </template>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="应付草稿同步">
              <span data-testid="factory-statement-detail-outbox-status">
                {{ outboxStatusLabel(effectiveOutboxStatus) }}
              </span>
            </el-descriptions-item>
            <el-descriptions-item label="ERP 发票草稿">
              <span data-testid="factory-statement-detail-purchase-invoice">{{ detail.purchase_invoice_name || '-' }}</span>
            </el-descriptions-item>
          </el-descriptions>
          <el-alert
            v-if="summaryMissing"
            class="warn-alert"
            type="warning"
            show-icon
            :closable="false"
            title="应付摘要缺失，相关操作按 fail-closed 策略禁用。"
          />
          <el-alert
            v-if="hasActivePayableOutbox"
            class="warn-alert"
            type="warning"
            show-icon
            :closable="false"
            title="当前存在应付草稿同步流程，详情页仅支持只读浏览。"
          />
        </el-card>

        <div class="action-row" data-testid="factory-statement-detail-actions">
          <el-button
            data-testid="factory-statement-detail-action-confirm"
            data-action-type="write"
            data-write-guard="guarded:readonly"
            @click="guardedWriteAction('确认')"
          >
            确认
          </el-button>
          <el-button
            data-testid="factory-statement-detail-action-cancel"
            data-action-type="write"
            data-write-guard="guarded:readonly"
            @click="guardedWriteAction('取消')"
          >
            取消
          </el-button>
          <el-button
            data-testid="factory-statement-detail-action-payable-draft"
            data-action-type="write"
            data-write-guard="guarded:readonly"
            @click="guardedWriteAction('生成应付草稿')"
          >
            生成应付草稿
          </el-button>
          <el-button
            data-testid="factory-statement-detail-action-print"
            data-action-type="write"
            data-write-guard="guarded:readonly"
            @click="guardedWriteAction('打印')"
          >
            打印
          </el-button>
          <el-button
            data-testid="factory-statement-detail-action-export"
            data-action-type="write"
            data-write-guard="guarded:readonly"
            @click="guardedWriteAction('导出明细 CSV')"
          >
            导出明细 CSV
          </el-button>
        </div>

        <el-alert
          v-if="guardedFeedback"
          class="warn-alert"
          type="info"
          show-icon
          :closable="false"
          :title="guardedFeedback"
          data-testid="factory-statement-detail-guarded-feedback"
        />

        <p class="state-tip" data-testid="factory-statement-detail-permission-or-disabled-state">
          当前页面仅提供只读浏览，所有写动作与导出打印动作均已禁用。
        </p>

        <el-empty
          v-if="showEmptyState"
          description="暂无可展示的对账明细或操作日志"
          data-testid="factory-statement-detail-empty-state"
        />
      </template>
      <el-empty v-else description="未找到对账单数据" data-testid="factory-statement-detail-empty-state" />
    </el-card>

    <el-card v-if="canRead && detail" shadow="never" data-testid="factory-statement-detail-items-section">
      <template #header>
        <span>对账明细</span>
      </template>
      <el-table :data="items" border empty-text="暂无对账明细数据" data-testid="factory-statement-detail-items-table">
        <el-table-column prop="line_no" label="行号" width="70" />
        <el-table-column prop="inspection_no" label="验货单号" min-width="150" />
        <el-table-column prop="subcontract_no" label="外发单号" min-width="150" />
        <el-table-column prop="item_code" label="款式" min-width="120" />
        <el-table-column label="验货数量" width="110">
          <template #default="scope">{{ formatAmount(scope.row.inspected_qty) }}</template>
        </el-table-column>
        <el-table-column label="次品数量" width="110">
          <template #default="scope">{{ formatAmount(scope.row.rejected_qty) }}</template>
        </el-table-column>
        <el-table-column label="合格数量" width="110">
          <template #default="scope">{{ formatAmount(scope.row.accepted_qty) }}</template>
        </el-table-column>
        <el-table-column label="加工费" width="130">
          <template #default="scope">{{ formatAmount(scope.row.gross_amount) }}</template>
        </el-table-column>
        <el-table-column label="扣款" width="130">
          <template #default="scope">{{ formatAmount(scope.row.deduction_amount) }}</template>
        </el-table-column>
        <el-table-column label="实付" width="130">
          <template #default="scope">{{ formatAmount(scope.row.net_amount) }}</template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card v-if="canRead && detail" shadow="never" data-testid="factory-statement-detail-logs-section">
      <template #header>
        <span>操作日志</span>
      </template>
      <el-table :data="logs" border empty-text="暂无操作日志数据" data-testid="factory-statement-detail-logs-table">
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
import {
  fetchFactoryStatementDetail,
  type FactoryStatementDetailData,
  type FactoryStatementDetailItem,
  type FactoryStatementLogItem,
} from '@/api/factory_statement'
import { exportFactoryStatementDetailCsv } from '@/utils/factoryStatementExport'
import { usePermissionStore } from '@/stores/permission'

const ACTIVE_PAYABLE_OUTBOX_STATUS = new Set(['pending', 'processing', 'succeeded'])

const route = useRoute()
const router = useRouter()
const permissionStore = usePermissionStore()
const readonlyPrintRoute = '/factory-statements/print'
const readonlyExportAnchor = exportFactoryStatementDetailCsv

const loading = ref<boolean>(false)
const detailLoaded = ref<boolean>(false)
const detail = ref<FactoryStatementDetailData | null>(null)
const items = ref<FactoryStatementDetailItem[]>([])
const logs = ref<FactoryStatementLogItem[]>([])
const missingStatementId = ref<boolean>(false)
const permissionReady = ref<boolean>(false)
const loadError = ref<string>('')
const guardedFeedback = ref<string>('')

const canRead = computed<boolean>(() => permissionStore.state.buttonPermissions.factory_statement_read)
const statementId = computed<number>(() => Number(route.query.id || '0'))
const hasValidStatementId = computed<boolean>(() => Number.isInteger(statementId.value) && statementId.value > 0)

const hasActivePayableOutbox = computed<boolean>(() => {
  return !hasPayableSummary.value || ACTIVE_PAYABLE_OUTBOX_STATUS.has(effectiveOutboxStatus.value)
})

const hasPayableSummary = computed<boolean>(
  () => detail.value?.payable_outbox_status !== undefined && detail.value?.purchase_invoice_name !== undefined,
)

const summaryMissing = computed<boolean>(() => Boolean(detail.value) && !hasPayableSummary.value)

const effectiveOutboxStatus = computed<string>(() => {
  if (!hasPayableSummary.value) {
    return '__unknown__'
  }
  const directStatus = detail.value?.payable_outbox_status
  if (directStatus) {
    return directStatus
  }
  return ''
})

const showEmptyState = computed<boolean>(
  () => detailLoaded.value && !!detail.value && items.value.length === 0 && logs.value.length === 0,
)

const detailKpis = computed(() => {
  const rejectedRate = formatRate(detail.value?.rejected_rate)
  const payableSyncState = hasActivePayableOutbox.value ? '同步中/待同步' : '已闭合'
  return {
    itemCount: items.value.length,
    logCount: logs.value.length,
    rejectedRate,
    payableSyncState,
  }
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

const statementStatusLabel = (status: string | null | undefined): string => {
  if (status === 'draft') return '草稿'
  if (status === 'confirmed') return '已确认'
  if (status === 'cancelled') return '已取消'
  if (status === 'payable_draft_created') return '应付草稿已生成'
  return status || '-'
}

const outboxStatusLabel = (status: string | null | undefined): string => {
  if (status === 'pending') return '待同步'
  if (status === 'processing') return '同步中'
  if (status === 'succeeded') return '已生成草稿'
  if (status === 'failed') return '同步失败'
  if (status === 'dead') return '同步死信'
  if (status === '__unknown__') return '摘要缺失'
  return status || '-'
}

const statusTag = (status: string | null | undefined): 'warning' | 'success' | 'danger' | 'info' => {
  if (status === 'draft') return 'warning'
  if (status === 'confirmed') return 'success'
  if (status === 'cancelled') return 'danger'
  return 'info'
}

const goBack = (): void => {
  router.push({ path: '/factory-statements/list' })
}

const guardedWriteAction = (actionName: string): void => {
  if (actionName === '打印') {
    guardedFeedback.value = `打印已禁用：请仅在只读打印页查看（${readonlyPrintRoute}）`
    ElMessage.warning(guardedFeedback.value)
    return
  }
  if (actionName === '导出明细 CSV') {
    const exportName = readonlyExportAnchor.name || 'exportFactoryStatementDetailCsv'
    guardedFeedback.value = `导出已禁用：${exportName} 在当前详情页只读模式下不执行`
    ElMessage.warning(guardedFeedback.value)
    return
  }
  guardedFeedback.value = `${actionName}已禁用：详情页当前为只读模式`
  ElMessage.warning(guardedFeedback.value)
}

const loadDetail = async (): Promise<void> => {
  loadError.value = ''
  detailLoaded.value = false

  if (!canRead.value) {
    detail.value = null
    items.value = []
    logs.value = []
    missingStatementId.value = false
    return
  }
  if (!hasValidStatementId.value) {
    detail.value = null
    items.value = []
    logs.value = []
    missingStatementId.value = true
    return
  }

  missingStatementId.value = false
  loading.value = true
  try {
    const result = await fetchFactoryStatementDetail(statementId.value)
    detail.value = result.data
    items.value = result.data.items || []
    logs.value = result.data.logs || []
    detailLoaded.value = true
  } catch (error) {
    detail.value = null
    items.value = []
    logs.value = []
    loadError.value = (error as Error).message || '加载对账详情失败'
    ElMessage.error(loadError.value)
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  try {
    await permissionStore.loadCurrentUser()
    await permissionStore.loadModuleActions('factory_statement')
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    permissionReady.value = true
  }
  await loadDetail()
})
</script>

<style scoped>
.factory-statement-detail-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.warn-alert {
  margin-top: 12px;
}

.action-row {
  margin-top: 12px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.outbox-card {
  margin-top: 12px;
}

.detail-kpi-grid {
  margin-top: 12px;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 8px;
}

.detail-kpi-card {
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 10px 12px;
  background: #fafbfc;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.detail-status-strip {
  margin-top: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.kpi-label {
  color: #6b7280;
  font-size: 12px;
}

.kpi-value {
  color: #111827;
  font-size: 18px;
  line-height: 1.2;
}

.kpi-subtext {
  color: #9ca3af;
  font-size: 11px;
}

.state-tip {
  margin-top: 12px;
  margin-bottom: 0;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}
</style>
