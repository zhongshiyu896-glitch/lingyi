<template>
  <div class="factory-statement-detail-page" data-testid="factory-statement-detail-page">
    <FactoryStatementSourceReadonlySection
      v-if="showSourceReadonlySection"
      :summary="sourceReadonlySummary"
      data-testid="factory-statement-detail-source-readonly-section"
    />

    <FactoryStatementPayableStatusReadonly
      :summary="payableReadonlySummary"
      data-testid="factory-statement-detail-payable-readonly-section"
    />

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
          <el-tag
            :type="statusTag(detail.statement_status)"
            effect="plain"
            data-testid="factory-statement-status-tag"
          >
            单据 {{ statementStatusLabel(detail.statement_status) }}
          </el-tag>
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

        <el-card shadow="never" class="summary-card" data-testid="factory-statement-detail-summary-section">
          <template #header>
            <span>结算 / 审计摘要</span>
          </template>
          <el-descriptions :column="2" border data-testid="factory-statement-detail-summary-fields">
            <el-descriptions-item label="结算期间">
              {{ settlementSummary.periodText }}
            </el-descriptions-item>
            <el-descriptions-item label="首个外发单">
              {{ settlementSummary.primarySubcontractNo }}
            </el-descriptions-item>
            <el-descriptions-item label="首个验货单">
              {{ settlementSummary.primaryInspectionNo }}
            </el-descriptions-item>
            <el-descriptions-item label="应付草稿数">
              {{ settlementSummary.payableOutboxCount }}
            </el-descriptions-item>
            <el-descriptions-item label="创建人">
              {{ auditSummary.createdBy }}
            </el-descriptions-item>
            <el-descriptions-item label="创建时间">
              {{ auditSummary.createdAt }}
            </el-descriptions-item>
            <el-descriptions-item label="最新动作">
              {{ auditSummary.latestAction }}
            </el-descriptions-item>
            <el-descriptions-item label="最新操作人">
              {{ auditSummary.latestOperator }}
            </el-descriptions-item>
            <el-descriptions-item label="最新操作时间">
              {{ auditSummary.latestOperatedAt }}
            </el-descriptions-item>
            <el-descriptions-item label="最新备注">
              {{ auditSummary.latestRemark }}
            </el-descriptions-item>
            <el-descriptions-item label="应付错误码">
              {{ settlementSummary.payableErrorCode }}
            </el-descriptions-item>
            <el-descriptions-item label="应付错误信息">
              {{ settlementSummary.payableErrorMessage }}
            </el-descriptions-item>
          </el-descriptions>
        </el-card>
        <div class="action-row" data-testid="factory-statement-detail-actions">
          <el-button
            data-testid="factory-statement-detail-action-confirm"
            data-action-type="write"
            data-write-guard="guarded:readonly"
            disabled
          >
            确认
          </el-button>
          <el-button
            data-testid="factory-statement-detail-action-cancel"
            data-action-type="write"
            data-write-guard="guarded:readonly"
            disabled
          >
            取消
          </el-button>
          <el-button
            data-testid="factory-statement-detail-action-payable-draft"
            data-action-type="write"
            data-write-guard="guarded:readonly"
            disabled
          >
            生成应付草稿
          </el-button>
          <el-button
            data-testid="factory-statement-detail-action-print"
            data-action-type="write"
            data-write-guard="guarded:readonly"
            :data-print-route="openPrintPreviewReadonly()"
            disabled
          >
            打印
          </el-button>
          <el-button
            data-testid="factory-statement-detail-action-export"
            data-action-type="write"
            data-write-guard="guarded:readonly"
            :data-export-guard-target="exportCsvGuardTarget().name"
            disabled
          >
            导出明细 CSV
          </el-button>
        </div>

        <el-alert
          class="warn-alert"
          type="info"
          show-icon
          :closable="false"
          :title="detailGuardMessage"
          data-testid="factory-statement-detail-guarded-feedback"
        />

        <div
          data-testid="factory-statement-write-guard"
          data-action-type="write"
          data-write-guard="guarded:readonly-detail"
          data-guard-state="disabled"
        >
          <p class="state-tip" data-testid="factory-statement-detail-permission-or-disabled-state">
            当前页面仅提供只读浏览，所有写动作与导出打印动作均已禁用。
          </p>
        </div>

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
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  fetchFactoryStatementReadonlyFallbackId,
  fetchFactoryStatementReadonlyDetail,
  type FactoryStatementReadonlyRecord,
} from '@/api/factory_statement_readonly'
import { exportFactoryStatementDetailCsv } from '@/utils/factoryStatementExport'
import FactoryStatementSourceReadonlySection from '@/views/factory_statement/components/FactoryStatementSourceReadonlySection.vue'
import FactoryStatementPayableStatusReadonly from '@/views/factory_statement/components/FactoryStatementPayableStatusReadonly.vue'
import { useFactoryStatementPayableReadonly } from '@/views/factory_statement/composables/useFactoryStatementPayableReadonly'
import { useFactoryStatementSourceReadonly } from '@/views/factory_statement/composables/useFactoryStatementSourceReadonly'
import { useFactoryStatementReadonly } from '@/views/factory_statement/composables/useFactoryStatementReadonly'
import { usePermissionStore } from '@/stores/permission'

const route = useRoute()
const router = useRouter()
const permissionStore = usePermissionStore()

const loading = ref<boolean>(false)
const detailLoaded = ref<boolean>(false)
const readonlyRecord = ref<FactoryStatementReadonlyRecord | null>(null)
const missingStatementId = ref<boolean>(false)
const permissionReady = ref<boolean>(false)
const loadError = ref<string>('')
const GLOBAL_READONLY_GUARD_ATTR = 'data-factory-statement-payable-readonly-disabled'
const GLOBAL_READONLY_PREV_DISABLED_ATTR = 'data-factory-statement-payable-prev-disabled'
const GLOBAL_READONLY_PREV_ARIA_DISABLED_ATTR = 'data-factory-statement-payable-prev-aria-disabled'
const GLOBAL_READONLY_PREV_TITLE_ATTR = 'data-factory-statement-payable-prev-title'
const GLOBAL_READONLY_PREV_TABINDEX_ATTR = 'data-factory-statement-payable-prev-tabindex'
const FACTORY_STATEMENT_PRINT_ROUTE = '/factory-statements/print'
const ACTIVE_PAYABLE_OUTBOX_STATUS = new Set(['pending', 'processing', 'succeeded'])
const GLOBAL_FACTORY_STATEMENT_ACTION_GUARDS = [
  {
    selector: '#global-auth-refresh-guard',
    reason: 'payable-readonly boundary keeps permission refresh non-executable on FactoryStatementDetail.',
    disableNative: true,
  },
  {
    selector: '#z042-global-guarded-refresh',
    reason: 'payable-readonly boundary keeps permission refresh non-executable on FactoryStatementDetail.',
    disableNative: false,
  },
  {
    selector: 'button[data-readonly-action="fetchModuleActions"]',
    reason: 'payable-readonly boundary keeps module action reload non-executable on FactoryStatementDetail.',
    disableNative: true,
  },
] as const
let globalFactoryStatementGuardObserver: MutationObserver | null = null

const parityValue = computed<string>(() => String(route.query.parity || '').trim().toLowerCase())
const tabValue = computed<string>(() => String(route.query.tab || '').trim().toLowerCase())
const focusValue = computed<string>(() => String(route.query.focus || '').trim().toLowerCase())
const modeValue = computed<string>(() => String(route.query.mode || '').trim().toLowerCase())
const isSourceReadonlyTab = computed<boolean>(() => (
  tabValue.value === 'source-readonly' || tabValue.value === 'source-parity'
))
const isSourceReadonlyMode = computed<boolean>(() => (
  parityValue.value === 'factory-statement'
  && (
    modeValue.value === 'readonly-source'
    || modeValue.value === 'readonly-lineage'
    || focusValue.value === 'statement-source'
  )
))
const isPayableReadonlyMode = computed<boolean>(() => (
  parityValue.value === 'factory-statement'
  && (
    modeValue.value === 'readonly-payable-status'
    || tabValue.value === 'payable-status-readonly'
    || focusValue.value === 'payable-source'
  )
))
const isReadonlyParity = computed<boolean>(() => (
  parityValue.value === 'foundation-supplier'
  || parityValue.value === 'foundation-factory'
  || isSourceReadonlyMode.value
  || isPayableReadonlyMode.value
))
const preservedReadonlyQuery = computed<Record<string, string>>(() => {
  const query: Record<string, string> = {}
  if (isSourceReadonlyMode.value || isSourceReadonlyTab.value) {
    query.parity = 'factory-statement'
    query.tab = 'source-readonly'
    query.mode = 'readonly-source'
    query.focus = 'statement-source'
    return query
  }
  if (isPayableReadonlyMode.value) {
    query.parity = 'factory-statement'
    query.tab = 'payable-status-readonly'
    query.mode = 'readonly-payable-status'
    query.focus = 'payable-source'
    return query
  }
  if (parityValue.value) {
    query.parity = parityValue.value
  }
  if (tabValue.value) {
    query.tab = tabValue.value
  } else if (modeValue.value === 'readonly-lineage') {
    query.tab = 'source-parity'
  }
  if (focusValue.value) {
    query.focus = focusValue.value
  }
  if (modeValue.value) {
    query.mode = modeValue.value
  }
  return query
})
const canRead = computed<boolean>(() => isReadonlyParity.value || permissionStore.state.buttonPermissions.factory_statement_read)
const statementId = computed<number>(() => Number(route.query.id || '0'))
const hasValidStatementId = computed<boolean>(() => Number.isInteger(statementId.value) && statementId.value > 0)
const shouldUseReadonlyFallbackId = computed<boolean>(() => !hasValidStatementId.value)
const detail = computed(() => readonlyRecord.value?.raw || null)
const items = computed(() => readonlyRecord.value?.items || [])
const logs = computed(() => readonlyRecord.value?.logs || [])
const {
  auditSummary,
  detailGuardMessage,
  detailKpis,
  formatAmount,
  formatRate,
  outboxStatusLabel,
  settlementSummary,
  statementStatusLabel,
  statusTag,
} = useFactoryStatementReadonly(readonlyRecord)
const hasPayableSummary = computed<boolean>(
  () => detail.value?.payable_outbox_status !== undefined && detail.value?.purchase_invoice_name !== undefined,
)
const summaryMissing = computed<boolean>(() => Boolean(detail.value) && !hasPayableSummary.value)
const effectiveOutboxStatus = computed<string>(() => {
  if (!hasPayableSummary.value) {
    return '__unknown__'
  }
  return detail.value?.payable_outbox_status || ''
})
const hasActivePayableOutbox = computed<boolean>(() => (
  !hasPayableSummary.value || ACTIVE_PAYABLE_OUTBOX_STATUS.has(effectiveOutboxStatus.value)
))
const { payableReadonlySummary } = useFactoryStatementPayableReadonly({
  recordSource: readonlyRecord,
  parity: parityValue,
  context: 'detail',
  tab: tabValue,
  mode: modeValue,
  focus: focusValue,
})
const { sourceReadonlySummary } = useFactoryStatementSourceReadonly({
  context: 'detail',
  detailRecord: readonlyRecord,
  parity: parityValue,
  mode: modeValue,
  focus: focusValue,
})

const showEmptyState = computed<boolean>(
  () => detailLoaded.value && !!detail.value && items.value.length === 0 && logs.value.length === 0,
)
const showSourceReadonlySection = computed<boolean>(() => (
  isSourceReadonlyMode.value || modeValue.value === 'readonly-lineage' || tabValue.value === 'source-parity'
))
const openPrintPreviewReadonly = (): string => {
  if (!detail.value?.statement_id) {
    return FACTORY_STATEMENT_PRINT_ROUTE
  }
  const query = new URLSearchParams({
    ...preservedReadonlyQuery.value,
    id: String(detail.value.statement_id),
  })
  return `${FACTORY_STATEMENT_PRINT_ROUTE}?${query.toString()}`
}
const exportCsvGuardTarget = (): typeof exportFactoryStatementDetailCsv => exportFactoryStatementDetailCsv

const syncReadonlyGuardAttribute = (element: HTMLElement, attribute: string, value: string): void => {
  if (element.getAttribute(attribute) !== value) {
    element.setAttribute(attribute, value)
  }
}

const applyGlobalReadonlyGuardToElement = (
  element: HTMLElement,
  reason: string,
  disableNative: boolean,
): void => {
  if (!element.hasAttribute(GLOBAL_READONLY_GUARD_ATTR)) {
    element.setAttribute(GLOBAL_READONLY_GUARD_ATTR, '1')
    element.setAttribute(
      GLOBAL_READONLY_PREV_DISABLED_ATTR,
      element instanceof HTMLButtonElement && element.disabled ? 'true' : 'false',
    )
    element.setAttribute(
      GLOBAL_READONLY_PREV_ARIA_DISABLED_ATTR,
      element.getAttribute('aria-disabled') ?? '',
    )
    element.setAttribute(GLOBAL_READONLY_PREV_TITLE_ATTR, element.getAttribute('title') ?? '')
    element.setAttribute(GLOBAL_READONLY_PREV_TABINDEX_ATTR, element.getAttribute('tabindex') ?? '')
  }

  if (disableNative && element instanceof HTMLButtonElement && !element.disabled) {
    element.disabled = true
  }
  syncReadonlyGuardAttribute(element, 'aria-disabled', 'true')
  syncReadonlyGuardAttribute(element, 'title', reason)
  syncReadonlyGuardAttribute(element, 'tabindex', '-1')
  if (!element.classList.contains('is-disabled')) {
    element.classList.add('is-disabled')
  }
}

const restoreGlobalReadonlyGuardElements = (): void => {
  if (typeof document === 'undefined') {
    return
  }

  document.querySelectorAll<HTMLElement>(`[${GLOBAL_READONLY_GUARD_ATTR}="1"]`).forEach((element) => {
    const prevDisabled = element.getAttribute(GLOBAL_READONLY_PREV_DISABLED_ATTR) === 'true'
    const prevAriaDisabled = element.getAttribute(GLOBAL_READONLY_PREV_ARIA_DISABLED_ATTR) ?? ''
    const prevTitle = element.getAttribute(GLOBAL_READONLY_PREV_TITLE_ATTR) ?? ''
    const prevTabIndex = element.getAttribute(GLOBAL_READONLY_PREV_TABINDEX_ATTR) ?? ''

    if (element instanceof HTMLButtonElement) {
      element.disabled = prevDisabled
    }

    if (prevAriaDisabled) {
      element.setAttribute('aria-disabled', prevAriaDisabled)
    } else {
      element.removeAttribute('aria-disabled')
    }

    if (prevTitle) {
      element.setAttribute('title', prevTitle)
    } else {
      element.removeAttribute('title')
    }

    if (prevTabIndex) {
      element.setAttribute('tabindex', prevTabIndex)
    } else {
      element.removeAttribute('tabindex')
    }

    element.classList.remove('is-disabled')
    element.removeAttribute(GLOBAL_READONLY_GUARD_ATTR)
    element.removeAttribute(GLOBAL_READONLY_PREV_DISABLED_ATTR)
    element.removeAttribute(GLOBAL_READONLY_PREV_ARIA_DISABLED_ATTR)
    element.removeAttribute(GLOBAL_READONLY_PREV_TITLE_ATTR)
    element.removeAttribute(GLOBAL_READONLY_PREV_TABINDEX_ATTR)
  })
}

const applyGlobalReadonlyActionGuards = async (): Promise<void> => {
  if (typeof document === 'undefined') {
    return
  }

  await nextTick()
  for (const guard of GLOBAL_FACTORY_STATEMENT_ACTION_GUARDS) {
    document.querySelectorAll<HTMLElement>(guard.selector).forEach((element) => {
      applyGlobalReadonlyGuardToElement(element, guard.reason, guard.disableNative)
    })
  }
}

const stopGlobalReadonlyActionGuardObserver = (): void => {
  globalFactoryStatementGuardObserver?.disconnect()
  globalFactoryStatementGuardObserver = null
}

const startGlobalReadonlyActionGuardObserver = (): void => {
  if (typeof document === 'undefined' || globalFactoryStatementGuardObserver) {
    return
  }

  globalFactoryStatementGuardObserver = new MutationObserver(() => {
    void applyGlobalReadonlyActionGuards()
  })
  globalFactoryStatementGuardObserver.observe(document.body, {
    childList: true,
    subtree: true,
  })
}

const goBack = (): void => {
  if (isSourceReadonlyMode.value || isSourceReadonlyTab.value) {
    router.push({
      path: '/factory-statements/list',
      query: {
        parity: 'factory-statement',
        tab: 'source-readonly',
      },
    })
    return
  }
  router.push({ path: '/factory-statements/list', query: { ...preservedReadonlyQuery.value } })
}

const loadDetail = async (): Promise<void> => {
  loadError.value = ''
  detailLoaded.value = false

  if (!canRead.value) {
    readonlyRecord.value = null
    missingStatementId.value = false
    return
  }
  if (!shouldUseReadonlyFallbackId.value && !isSourceReadonlyMode.value && modeValue.value !== 'readonly-lineage') {
    readonlyRecord.value = null
    missingStatementId.value = true
    return
  }

  missingStatementId.value = false
  loading.value = true
  try {
    let targetStatementId = statementId.value
    if (!hasValidStatementId.value) {
      const fallbackIdResult = await fetchFactoryStatementReadonlyFallbackId()
      if (!fallbackIdResult.data) {
        readonlyRecord.value = null
        missingStatementId.value = true
        detailLoaded.value = true
        return
      }
      targetStatementId = fallbackIdResult.data
    }
    const result = await fetchFactoryStatementReadonlyDetail(targetStatementId)
    readonlyRecord.value = result.data
    detailLoaded.value = true
  } catch (error) {
    readonlyRecord.value = null
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
  startGlobalReadonlyActionGuardObserver()
  await applyGlobalReadonlyActionGuards()
})

onBeforeUnmount(() => {
  stopGlobalReadonlyActionGuardObserver()
  restoreGlobalReadonlyGuardElements()
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

.summary-card {
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
