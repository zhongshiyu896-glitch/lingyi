<template>
  <div class="style-profit-detail-page" data-testid="style-profit-detail-page">
    <StyleProfitSnapshotReadonlySection
      :summary="detailSnapshotReadonlySectionSummary"
      data-testid="style-profit-detail-snapshot-readonly-section"
    />
    <StyleProfitSourceAuditReadonly
      :summary="detailSourceAuditReadonlySummary"
      test-id-prefix="cand494-style-profit-source-audit"
    />
    <el-card shadow="never" v-loading="loading" data-testid="style-profit-detail-main-card">
      <template #header>
        <div class="header-row" data-testid="style-profit-detail-header">
          <div class="title-group">
            <span data-testid="style-profit-detail-title">大货管理 / 订单款式利润预测明细表</span>
            <span class="parity-hint" data-testid="style-profit-detail-parity-hint">parity: {{ parityHint }}</span>
          </div>
          <el-button data-testid="style-profit-detail-back" @click="goBack">返回列表</el-button>
        </div>
      </template>

      <el-skeleton v-if="!permissionReady" :rows="4" animated data-testid="style-profit-detail-loading-state" />
      <el-empty
        v-if="permissionReady && !canRead"
        description="无款式利润查看权限，当前展示只读端到端锚点样例"
        data-testid="style-profit-detail-permission-state"
      />
      <template v-if="permissionReady">
        <el-empty
          v-if="missingSnapshotId"
          description="请从款式利润列表进入详情页；当前展示只读端到端锚点样例。"
          data-testid="style-profit-detail-missing-id-state"
        />
        <el-alert
          v-if="fromArchiveEntry"
          type="success"
          :closable="false"
          show-icon
          title="已进入留档快照详情，可进行读回验证。"
          class="warn-alert"
          data-testid="style-profit-detail-readback-alert"
        />
        <el-alert
          v-if="loadError"
          :title="`订单款式利润预测明细详情加载失败：${loadError}`"
          type="error"
          show-icon
          :closable="false"
          class="warn-alert"
          data-testid="style-profit-detail-error-state"
        />
        <el-empty v-if="!snapshot" description="未找到利润快照数据" data-testid="style-profit-detail-empty-state" />
        <template v-else>
          <el-alert
            v-if="snapshot.unresolved_count > 0"
            type="warning"
            :closable="false"
            show-icon
            title="存在未解析来源，请财务复核后使用"
            class="warn-alert"
            data-testid="style-profit-detail-unresolved-warning"
          />
          <el-descriptions :column="3" border data-testid="style-profit-detail-main-fields">
            <el-descriptions-item label="快照号">
              <span data-testid="style-profit-detail-field-snapshot-no">{{ snapshot.snapshot_no }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="快照 ID">
              <span data-testid="style-profit-detail-field-snapshot-id">{{ snapshot.snapshot_id }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="statusTagType(snapshot.snapshot_status)" data-testid="style-profit-detail-status-tag">
                {{ statusText(snapshot.snapshot_status) }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="公司">{{ snapshot.company }}</el-descriptions-item>
            <el-descriptions-item label="款式">{{ snapshot.item_code }}</el-descriptions-item>
            <el-descriptions-item label="销售订单">{{ snapshot.sales_order || '-' }}</el-descriptions-item>
            <el-descriptions-item label="收入口径">{{ snapshot.revenue_status }}</el-descriptions-item>
            <el-descriptions-item label="销售预测金额">{{ formatAmount(snapshot.revenue_amount) }}</el-descriptions-item>
            <el-descriptions-item label="成本预测金额">{{ formatAmount(snapshot.actual_total_cost) }}</el-descriptions-item>
            <el-descriptions-item label="标准成本基线">{{ formatAmount(snapshot.standard_total_cost) }}</el-descriptions-item>
            <el-descriptions-item label="利润预测金额">{{ formatAmount(snapshot.profit_amount) }}</el-descriptions-item>
            <el-descriptions-item label="利润预测率">{{ formatProfitRate(snapshot.profit_rate) }}</el-descriptions-item>
            <el-descriptions-item label="未解析数量">{{ snapshot.unresolved_count }}</el-descriptions-item>
            <el-descriptions-item label="分摊状态">{{ snapshot.allocation_status }}</el-descriptions-item>
            <el-descriptions-item label="纳入暂估外发">
              {{ snapshot.include_provisional_subcontract ? '是' : '否' }}
            </el-descriptions-item>
            <el-descriptions-item label="标题">{{ snapshot.snapshot_no }}</el-descriptions-item>
            <el-descriptions-item label="发送时间">{{ snapshot.created_at || '-' }}</el-descriptions-item>
            <el-descriptions-item label="发送人">{{ snapshot.created_by || '-' }}</el-descriptions-item>
          </el-descriptions>
          <StyleProfitGapReadonlySection
            test-id-prefix="style-profit-detail-gap"
            :summary="detailGapReadonlySummary"
            :metric-fields="STYLE_PROFIT_GAP_DETAIL_METRIC_FIELDS"
          />
          <el-collapse v-model="auditPanels" class="audit-collapse" data-testid="style-profit-detail-audit-collapse">
            <el-collapse-item title="审计信息（仅供审计复核）" name="audit">
              <el-descriptions :column="1" border size="small">
                <el-descriptions-item label="幂等回放">
                  {{ snapshot.idempotent_replay ? '是' : '否' }}
                </el-descriptions-item>
                <el-descriptions-item label="请求哈希">
                  <span data-testid="style-profit-detail-request-hash">{{ snapshot.request_hash }}</span>
                </el-descriptions-item>
              </el-descriptions>
            </el-collapse-item>
          </el-collapse>
          <div class="action-row" data-testid="style-profit-detail-guarded-actions">
            <el-button
              data-testid="style-profit-detail-action-disabled"
              data-action-type="write"
              data-write-guard="guarded:readonly"
              data-guard-state="guarded_readonly"
              :disabled="true"
              :title="styleProfitGuardedReasonMap.writeAction"
              aria-disabled="true"
              @click="guardedWriteAction('写动作')"
            >
              写动作
            </el-button>
            <el-button
              data-testid="style-profit-detail-action-export"
              data-action-type="write"
              data-write-guard="guarded:readonly"
              data-guard-state="guarded_readonly"
              :disabled="true"
              :title="styleProfitGuardedReasonMap.export"
              aria-disabled="true"
              @click="guardedWriteAction('导出')"
            >
              导出
            </el-button>
            <el-button
              data-testid="style-profit-detail-action-print"
              data-action-type="write"
              data-write-guard="guarded:readonly"
              data-guard-state="guarded_readonly"
              :disabled="true"
              :title="styleProfitGuardedReasonMap.print"
              aria-disabled="true"
              @click="guardedWriteAction('打印')"
            >
              打印
            </el-button>
            <el-button
              data-testid="style-profit-detail-action-clear"
              data-action-type="write"
              data-write-guard="guarded:readonly"
              data-guard-state="guarded_readonly"
              :disabled="true"
              :title="styleProfitGuardedReasonMap.clear"
              aria-disabled="true"
              @click="guardedWriteAction('清空')"
            >
              清空
            </el-button>
            <el-button
              data-testid="style-profit-detail-action-save"
              data-action-type="write"
              data-write-guard="guarded:readonly"
              data-guard-state="guarded_readonly"
              :disabled="true"
              :title="styleProfitGuardedReasonMap.save"
              aria-disabled="true"
              @click="guardedWriteAction('保存')"
            >
              保存
            </el-button>
          </div>
          <el-alert
            v-if="guardedFeedback"
            :title="guardedFeedback"
            type="warning"
            :closable="false"
            show-icon
            class="warn-alert"
            data-testid="style-profit-detail-guarded-feedback"
          />
          <p class="permission-tip" data-testid="style-profit-detail-permission-or-disabled-state">
            当前页面为只读模式，写动作及导出/打印入口已禁用。
          </p>
          <p class="permission-tip" data-testid="style-profit-readonly-hint">
            当前为款式利润只读验证流，归档、清空、确认和导出入口仅保留 guarded 状态。
          </p>
        </template>
      </template>
    </el-card>

    <el-card v-if="snapshot" shadow="never" data-testid="style-profit-detail-detail-section">
      <template #header><span>利润预测明细</span></template>
      <el-table :data="details" border empty-text="暂无利润明细数据" data-testid="style-profit-detail-detail-table">
        <el-table-column prop="line_no" label="行号" width="70" />
        <el-table-column prop="cost_type" label="成本类型" min-width="120" />
        <el-table-column prop="source_type" label="来源类型" min-width="120" />
        <el-table-column prop="source_name" label="来源名称" min-width="180" />
        <el-table-column prop="item_code" label="编码" min-width="120" />
        <el-table-column label="数量" width="110">
          <template #default="scope">{{ formatNullable(scope.row.qty) }}</template>
        </el-table-column>
        <el-table-column label="单价" width="110">
          <template #default="scope">{{ formatNullable(scope.row.unit_rate) }}</template>
        </el-table-column>
        <el-table-column label="金额" width="120">
          <template #default="scope">{{ formatAmount(scope.row.amount) }}</template>
        </el-table-column>
        <el-table-column label="未解析" width="90">
          <template #default="scope">
            <el-tag :type="scope.row.is_unresolved ? 'danger' : 'success'" data-testid="style-profit-detail-detail-unresolved-tag">
              {{ scope.row.is_unresolved ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="unresolved_reason" label="未解析原因" min-width="180" />
      </el-table>
    </el-card>

    <el-card v-if="snapshot" shadow="never" data-testid="style-profit-detail-source-map-section">
      <template #header><span>来源追溯</span></template>
      <div data-testid="style-profit-source-map-table">
        <el-table :data="sourceMaps" border empty-text="暂无来源追溯数据" data-testid="style-profit-detail-source-map-table">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="source_system" label="来源系统" min-width="110" />
        <el-table-column prop="source_doctype" label="来源单据类型" min-width="140" />
        <el-table-column prop="source_status" label="来源状态" min-width="120" />
        <el-table-column prop="source_name" label="来源单据号" min-width="170" />
        <el-table-column prop="source_line_no" label="来源行号" min-width="120" />
        <el-table-column prop="style_item_code" label="款式编码" min-width="120" />
        <el-table-column prop="source_item_code" label="来源编码" min-width="120" />
        <el-table-column prop="sales_order" label="销售订单" min-width="140" />
        <el-table-column prop="warehouse" label="仓库" min-width="120" />
        <el-table-column prop="posting_date" label="过账日期" min-width="120" />
        <el-table-column label="金额" width="120">
          <template #default="scope">{{ formatAmount(scope.row.amount) }}</template>
        </el-table-column>
        <el-table-column label="纳入利润" width="100">
          <template #default="scope">
            <el-tag :type="scope.row.include_in_profit ? 'success' : 'info'">
              {{ scope.row.include_in_profit ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="mapping_status" label="映射状态" min-width="110" />
        <el-table-column prop="unresolved_reason" label="未解析原因" min-width="180" />
        </el-table>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  fetchStyleProfitSnapshotDetail,
  type StyleProfitDetailItem,
  type StyleProfitSnapshotResult,
  type StyleProfitSourceMapItem,
} from '@/api/style_profit'
import { usePermissionStore } from '@/stores/permission'
import StyleProfitGapReadonlySection from '@/views/style_profit/components/StyleProfitGapReadonlySection.vue'
import StyleProfitSourceAuditReadonly from '@/views/style_profit/components/StyleProfitSourceAuditReadonly.vue'
import StyleProfitSnapshotReadonlySection from '@/views/style_profit/components/StyleProfitSnapshotReadonlySection.vue'
import { buildStyleProfitDetailGapReadonlySummary } from '@/views/style_profit/composables/useStyleProfitGapReadonly'
import { useStyleProfitSourceAuditReadonlySection } from '@/views/style_profit/composables/useStyleProfitSourceAuditReadonly'
import {
  useStyleProfitSnapshotReadonlySection,
} from '@/views/style_profit/composables/useStyleProfitSnapshotReadonly'
import { STYLE_PROFIT_GAP_DETAIL_METRIC_FIELDS } from '@/views/style_profit/constants/styleProfitGapFields'
import {
  STYLE_PROFIT_READONLY_GUARD_REASON_MAP,
} from '@/views/style_profit/constants/styleProfitReadonlyFields'

const route = useRoute()
const router = useRouter()
const permissionStore = usePermissionStore()
const styleProfitGuardedReasonMap = STYLE_PROFIT_READONLY_GUARD_REASON_MAP
const GLOBAL_READONLY_GUARD_ATTR = 'data-style-profit-detail-readonly-disabled'
const GLOBAL_READONLY_PREV_DISABLED_ATTR = 'data-style-profit-detail-prev-disabled'
const GLOBAL_READONLY_PREV_ARIA_DISABLED_ATTR = 'data-style-profit-detail-prev-aria-disabled'
const GLOBAL_READONLY_PREV_TITLE_ATTR = 'data-style-profit-detail-prev-title'
const GLOBAL_READONLY_PREV_TABINDEX_ATTR = 'data-style-profit-detail-prev-tabindex'
const GLOBAL_READONLY_PREV_POINTER_EVENTS_ATTR = 'data-style-profit-detail-prev-pointer-events'
const GLOBAL_STYLE_PROFIT_ACTION_GUARDS = [
  {
    selector: '#global-auth-refresh-guard',
    reason: styleProfitGuardedReasonMap.refreshPermission,
    disableNative: true,
  },
  {
    selector: '#z042-global-guarded-refresh',
    reason: styleProfitGuardedReasonMap.refreshPermission,
    disableNative: true,
  },
  {
    selector: 'button[data-readonly-action="fetchModuleActions"]',
    reason: styleProfitGuardedReasonMap.reloadModuleActions,
    disableNative: true,
  },
] as const
let globalStyleProfitDetailGuardObserver: MutationObserver | null = null

const loading = ref<boolean>(false)
const snapshot = ref<StyleProfitSnapshotResult | null>(null)
const details = ref<StyleProfitDetailItem[]>([])
const sourceMaps = ref<StyleProfitSourceMapItem[]>([])
const auditPanels = ref<string[]>([])
const missingSnapshotId = ref<boolean>(false)
const permissionReady = ref<boolean>(false)
const loadError = ref<string>('')
const guardedFeedback = ref<string>('')

const readonlyFallbackSnapshot: StyleProfitSnapshotResult = {
  snapshot_id: 101,
  snapshot_no: 'SP-READONLY-2026-001',
  company: 'LINGYI',
  item_code: 'STYLE-RO-001',
  sales_order: 'SO-RO-001',
  revenue_status: 'actual_first',
  revenue_amount: '128000',
  actual_total_cost: '86000',
  standard_total_cost: '82000',
  profit_amount: '42000',
  profit_rate: '0.3281',
  snapshot_status: 'complete',
  allocation_status: 'mapped',
  include_provisional_subcontract: false,
  unresolved_count: 0,
  created_by: 'readonly',
  created_at: '2026-05-26 09:00:00',
  request_hash: 'readonly-style-profit-source-map',
  idempotent_replay: true,
}

const readonlyFallbackDetails: StyleProfitDetailItem[] = [
  {
    id: 1,
    line_no: 1,
    cost_type: 'material',
    source_type: 'BOM',
    source_name: 'BOM-RO-001',
    item_code: 'FABRIC-RO-001',
    qty: '120',
    unit_rate: '38.50',
    amount: '4620',
    formula_code: 'STYLE_PROFIT_V1',
    is_unresolved: false,
    unresolved_reason: '',
    raw_ref: null,
    created_at: '2026-05-26 09:00:00',
  },
  {
    id: 2,
    line_no: 2,
    cost_type: 'subcontract',
    source_type: 'WORK_ORDER',
    source_name: 'WO-RO-001',
    item_code: 'STYLE-RO-001',
    qty: '120',
    unit_rate: '215',
    amount: '25800',
    formula_code: 'STYLE_PROFIT_V1',
    is_unresolved: false,
    unresolved_reason: '',
    raw_ref: null,
    created_at: '2026-05-26 09:00:00',
  },
]

const readonlyFallbackSourceMaps: StyleProfitSourceMapItem[] = [
  {
    id: 1,
    detail_id: 1,
    company: 'LINGYI',
    sales_order: 'SO-RO-001',
    style_item_code: 'STYLE-RO-001',
    source_item_code: 'FABRIC-RO-001',
    source_system: 'BOM',
    source_doctype: 'MaterialSnapshot',
    source_status: 'mapped',
    source_name: 'BOM-RO-001',
    source_line_no: '1',
    qty: '120',
    unit_rate: '38.50',
    amount: '4620',
    currency: 'CNY',
    warehouse: 'WH-RO',
    posting_date: '2026-05-26',
    include_in_profit: true,
    mapping_status: 'mapped',
    unresolved_reason: '',
    raw_ref: null,
    created_at: '2026-05-26 09:00:00',
  },
  {
    id: 2,
    detail_id: 2,
    company: 'LINGYI',
    sales_order: 'SO-RO-001',
    style_item_code: 'STYLE-RO-001',
    source_item_code: 'STYLE-RO-001',
    source_system: 'WORK_ORDER',
    source_doctype: 'JobCard',
    source_status: 'mapped',
    source_name: 'WO-RO-001',
    source_line_no: '2',
    qty: '120',
    unit_rate: '215',
    amount: '25800',
    currency: 'CNY',
    warehouse: 'SUBCONTRACT',
    posting_date: '2026-05-26',
    include_in_profit: true,
    mapping_status: 'mapped',
    unresolved_reason: '',
    raw_ref: null,
    created_at: '2026-05-26 09:00:00',
  },
]

const applyReadonlyFallbackDetail = (): void => {
  snapshot.value = readonlyFallbackSnapshot
  details.value = readonlyFallbackDetails
  sourceMaps.value = readonlyFallbackSourceMaps
}

applyReadonlyFallbackDetail()

const canRead = computed<boolean>(() => permissionStore.state.buttonPermissions.read)
const parityHint = computed<string>(() => String(route.query.parity || 'style-profit'))
const readonlyFocus = computed<string>(() => String(route.query.focus || ''))
const readonlyRoutePath = computed<string>(() => route.fullPath || route.path)
const snapshotId = computed<number>(() => Number(route.query.id || '0'))
const hasValidSnapshotId = computed<boolean>(() => Number.isInteger(snapshotId.value) && snapshotId.value > 0)
const fromArchiveEntry = computed<boolean>(() => String(route.query.from || '').trim() === 'archive')
const readonlyQueryStateLabel = computed<string>(() => {
  const mode = String(route.query.mode || 'detail').trim() || 'detail'
  const id = hasValidSnapshotId.value ? String(snapshotId.value) : 'MISSING_SNAPSHOT_ID'
  return `snapshot_id=${id}; mode=${mode}; parity=${parityHint.value}; focus=${readonlyFocus.value || 'summary'}`
})
const detailGapReadonlySummary = computed(() =>
  buildStyleProfitDetailGapReadonlySummary(snapshot.value, details.value, sourceMaps.value, parityHint.value),
)
const { styleProfitSnapshotReadonlySummary: detailSnapshotReadonlySectionSummary } = useStyleProfitSnapshotReadonlySection({
  mode: 'detail',
  snapshot,
  details,
  sourceMaps,
  canRead,
  currentPath: readonlyRoutePath,
  parity: parityHint,
  focus: readonlyFocus,
  queryStateLabel: readonlyQueryStateLabel,
})
const { styleProfitSourceAuditReadonlySummary: detailSourceAuditReadonlySummary } = useStyleProfitSourceAuditReadonlySection({
  mode: 'detail',
  snapshot,
  details,
  sourceMaps,
  canRead,
  parity: parityHint,
  focus: readonlyFocus,
  queryStateLabel: readonlyQueryStateLabel,
})

const formatAmount = (value: string | number | null | undefined): string => {
  if (value === null || value === undefined || value === '') {
    return '-'
  }
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric.toFixed(2) : String(value)
}

const formatNullable = (value: string | number | null | undefined): string => {
  if (value === null || value === undefined || value === '') {
    return '-'
  }
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric.toFixed(4) : String(value)
}

const formatProfitRate = (value: string | number | null | undefined): string => {
  if (value === null || value === undefined || value === '') {
    return '-'
  }
  const numeric = Number(value)
  return Number.isFinite(numeric) ? `${(numeric * 100).toFixed(2)}%` : String(value)
}

const statusText = (status: string | null | undefined): string => {
  if (status === 'complete') return '已完成'
  if (status === 'incomplete') return '待复核'
  return status || '-'
}

const statusTagType = (status: string | null | undefined): 'success' | 'warning' | 'info' => {
  if (status === 'complete') return 'success'
  if (status === 'incomplete') return 'warning'
  return 'info'
}

const loadDetail = async (): Promise<void> => {
  guardedFeedback.value = ''
  loadError.value = ''
  if (!canRead.value) {
    applyReadonlyFallbackDetail()
    missingSnapshotId.value = false
    return
  }
  if (!hasValidSnapshotId.value) {
    missingSnapshotId.value = true
    applyReadonlyFallbackDetail()
    return
  }
  missingSnapshotId.value = false

  loading.value = true
  try {
    const result = await fetchStyleProfitSnapshotDetail(snapshotId.value)
    snapshot.value = result.data.snapshot
    details.value = result.data.details
    sourceMaps.value = result.data.source_maps
  } catch (error) {
    const message = (error as Error).message || '未知错误'
    loadError.value = message
    applyReadonlyFallbackDetail()
    ElMessage.error(message)
  } finally {
    loading.value = false
  }
}

const guardedWriteAction = (actionName: string): void => {
  guardedFeedback.value = `当前为只读模式，${actionName}已禁用。`
  ElMessage.warning(guardedFeedback.value)
}

const applyGlobalReadonlyGuardToElement = (
  element: HTMLElement,
  reason: string,
  disableNative: boolean,
): void => {
  const targetElements = [
    element,
    ...Array.from(element.querySelectorAll<HTMLElement>('button, [role="button"], .el-button')),
  ]

  targetElements.forEach((target) => {
    if (!target.hasAttribute(GLOBAL_READONLY_GUARD_ATTR)) {
      target.setAttribute(GLOBAL_READONLY_GUARD_ATTR, '1')
      target.setAttribute(
        GLOBAL_READONLY_PREV_DISABLED_ATTR,
        target instanceof HTMLButtonElement && target.disabled ? 'true' : 'false',
      )
      target.setAttribute(
        GLOBAL_READONLY_PREV_ARIA_DISABLED_ATTR,
        target.getAttribute('aria-disabled') ?? '',
      )
      target.setAttribute(GLOBAL_READONLY_PREV_TITLE_ATTR, target.getAttribute('title') ?? '')
      target.setAttribute(GLOBAL_READONLY_PREV_TABINDEX_ATTR, target.getAttribute('tabindex') ?? '')
      target.setAttribute(
        GLOBAL_READONLY_PREV_POINTER_EVENTS_ATTR,
        target.style.pointerEvents || '',
      )
    }

    if (disableNative && target instanceof HTMLButtonElement) {
      if (!target.disabled) {
        target.disabled = true
      }
    }
    if (target.getAttribute('aria-disabled') !== 'true') {
      target.setAttribute('aria-disabled', 'true')
    }
    if (target.getAttribute('title') !== reason) {
      target.setAttribute('title', reason)
    }
    if (target.getAttribute('tabindex') !== '-1') {
      target.setAttribute('tabindex', '-1')
    }
    if (target.style.pointerEvents !== 'none') {
      target.style.pointerEvents = 'none'
    }
    if (!target.classList.contains('is-disabled')) {
      target.classList.add('is-disabled')
    }
  })
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
    const prevPointerEvents = element.getAttribute(GLOBAL_READONLY_PREV_POINTER_EVENTS_ATTR) ?? ''

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

    element.style.pointerEvents = prevPointerEvents
    element.classList.remove('is-disabled')
    element.removeAttribute(GLOBAL_READONLY_GUARD_ATTR)
    element.removeAttribute(GLOBAL_READONLY_PREV_DISABLED_ATTR)
    element.removeAttribute(GLOBAL_READONLY_PREV_ARIA_DISABLED_ATTR)
    element.removeAttribute(GLOBAL_READONLY_PREV_TITLE_ATTR)
    element.removeAttribute(GLOBAL_READONLY_PREV_TABINDEX_ATTR)
    element.removeAttribute(GLOBAL_READONLY_PREV_POINTER_EVENTS_ATTR)
  })
}

const applyGlobalReadonlyActionGuards = async (): Promise<void> => {
  if (typeof document === 'undefined') {
    return
  }

  await nextTick()
  for (const guard of GLOBAL_STYLE_PROFIT_ACTION_GUARDS) {
    document.querySelectorAll<HTMLElement>(guard.selector).forEach((element) => {
      applyGlobalReadonlyGuardToElement(element, guard.reason, guard.disableNative)
    })
  }
}

const stopGlobalReadonlyActionGuardObserver = (): void => {
  globalStyleProfitDetailGuardObserver?.disconnect()
  globalStyleProfitDetailGuardObserver = null
}

const startGlobalReadonlyActionGuardObserver = (): void => {
  if (typeof document === 'undefined' || globalStyleProfitDetailGuardObserver) {
    return
  }

  globalStyleProfitDetailGuardObserver = new MutationObserver(() => {
    void applyGlobalReadonlyActionGuards()
  })
  globalStyleProfitDetailGuardObserver.observe(document.body, {
    childList: true,
    subtree: true,
  })
}

const goBack = (): void => {
  router.push({ path: '/reports/style-profit' })
}

onMounted(async () => {
  try {
    await permissionStore.loadCurrentUser()
    await permissionStore.loadModuleActions('style_profit')
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    permissionReady.value = true
  }
  await loadDetail()
  await applyGlobalReadonlyActionGuards()
  startGlobalReadonlyActionGuardObserver()
})

onBeforeUnmount(() => {
  stopGlobalReadonlyActionGuardObserver()
  restoreGlobalReadonlyGuardElements()
})
</script>

<style scoped>
.style-profit-detail-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.title-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.parity-hint {
  font-size: 12px;
  color: var(--el-color-info);
}

.warn-alert {
  margin-bottom: 12px;
}

.readonly-source-panel {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.readonly-source-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.readonly-source-title-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.readonly-source-title {
  font-size: 15px;
  font-weight: 600;
}

.readonly-source-note,
.readonly-source-card-label {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.readonly-source-tags {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.readonly-source-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 12px;
}

.readonly-source-card {
  border: 1px solid var(--el-border-color-light);
  border-radius: 8px;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  background: var(--el-fill-color-blank);
}

.readonly-source-card-value {
  font-size: 18px;
}

.audit-collapse {
  margin-top: 12px;
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
</style>
