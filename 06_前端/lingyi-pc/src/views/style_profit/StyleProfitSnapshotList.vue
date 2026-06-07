<template>
  <div class="style-profit-list-page" data-testid="style-profit-page">
    <el-card shadow="never" data-testid="style-profit-main-section">
      <template #header>
        <div class="header-row">
          <div class="title-group">
            <span class="page-title">大货管理 / 订单款式利润预测明细表</span>
            <span class="page-subtitle">按款式、品牌与时间范围查看销售预测、成本预测与利润预测明细</span>
            <span class="parity-hint" data-testid="style-profit-parity-hint">parity: {{ parityHint }}</span>
          </div>
        </div>
      </template>

      <el-form :inline="true" :model="query" class="query-form" data-testid="style-profit-query-form">
        <el-form-item label="款式">
          <el-input v-model="query.item_code" clearable placeholder="款式" data-testid="style-profit-filter-item-code" />
        </el-form-item>
        <el-form-item label="品牌">
          <el-input v-model="query.company" clearable placeholder="请输入" data-testid="style-profit-filter-company" />
        </el-form-item>
        <el-form-item label="关键词">
          <el-input v-model="query.sales_order" clearable placeholder="请输入" data-testid="style-profit-filter-sales-order" />
        </el-form-item>
        <el-form-item label="开始时间">
          <el-date-picker
            v-model="query.from_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="开始时间"
            clearable
            data-testid="style-profit-filter-from-date"
          />
        </el-form-item>
        <el-form-item label="结束时间">
          <el-date-picker
            v-model="query.to_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="结束时间"
            clearable
            data-testid="style-profit-filter-to-date"
          />
        </el-form-item>
        <el-form-item label="状态">
          <el-select
            v-model="query.snapshot_status"
            clearable
            placeholder="全部状态"
            style="width: 140px"
            data-testid="style-profit-filter-status"
          >
            <el-option label="已完成" value="complete" />
            <el-option label="待复核" value="incomplete" />
          </el-select>
        </el-form-item>
        <el-form-item label="收入口径">
          <el-select
            v-model="archiveParams.revenue_mode"
            placeholder="收入口径"
            style="width: 140px"
            data-testid="style-profit-write-revenue-mode"
          >
            <el-option label="实际优先" value="actual_first" />
            <el-option label="仅实际" value="actual_only" />
            <el-option label="仅预估" value="estimated_only" />
          </el-select>
        </el-form-item>
        <el-form-item label="公式版本">
          <el-select
            v-model="archiveParams.formula_version"
            placeholder="公式版本"
            style="width: 160px"
            data-testid="style-profit-write-formula-version"
          >
            <el-option label="STYLE_PROFIT_V1" value="STYLE_PROFIT_V1" />
          </el-select>
        </el-form-item>

        <el-form-item class="button-group">
          <el-button type="primary" :disabled="!canRead || loading" data-testid="style-profit-filter-button" @click="loadRows">筛选</el-button>
          <el-button :disabled="!canRead || loading" data-testid="style-profit-reset-button" @click="resetQuery">重置</el-button>
          <el-button :disabled="!canRead || loading" data-testid="style-profit-search-button" @click="loadRows">搜索</el-button>
          <el-button
            type="primary"
            :disabled="true"
            :title="styleProfitGuardedReasonMap.archive"
            aria-disabled="true"
            data-testid="style-profit-archive-button"
            data-action-type="write"
            data-write-guard="readonly:style-profit-archive"
            data-guard-state="guarded_readonly"
            @click="guardedAction('留档')"
          >
            留档
          </el-button>
          <el-button :disabled="true" :title="styleProfitGuardedReasonMap.clear" aria-disabled="true" data-testid="style-profit-guarded-clear" data-action-type="write" data-write-guard="readonly:style-profit-clear" data-guard-state="guarded_readonly" @click="guardedAction('清空')">清空</el-button>
          <el-button :disabled="true" :title="styleProfitGuardedReasonMap.confirm" aria-disabled="true" data-testid="style-profit-guarded-confirm" data-action-type="write" data-write-guard="readonly:style-profit-confirm" data-guard-state="guarded_readonly" @click="guardedAction('确定')">确定</el-button>
          <el-button :disabled="true" :title="styleProfitGuardedReasonMap.export" aria-disabled="true" data-testid="style-profit-guarded-export" data-action-type="write" data-write-guard="readonly:style-profit-export" data-guard-state="guarded_readonly" @click="guardedAction('导出')">导出</el-button>
          <el-button :disabled="true" :title="styleProfitGuardedReasonMap.columnSetting" aria-disabled="true" data-testid="style-profit-guarded-column-setting" data-action-type="write" data-write-guard="readonly:style-profit-column-setting" data-guard-state="guarded_readonly" @click="guardedAction('列设置')">列设置</el-button>
          <el-button :disabled="true" :title="styleProfitGuardedReasonMap.resetColumn" aria-disabled="true" data-testid="style-profit-guarded-reset-column" data-action-type="write" data-write-guard="readonly:style-profit-reset-column" data-guard-state="guarded_readonly" @click="guardedAction('重置列')">重置列</el-button>
          <el-button :disabled="true" :title="styleProfitGuardedReasonMap.markRead" aria-disabled="true" data-testid="style-profit-guarded-mark-read" data-action-type="write" data-write-guard="readonly:style-profit-mark-read" data-guard-state="guarded_readonly" @click="guardedAction('标志已读')">标志已读</el-button>
          <el-button :disabled="true" :title="styleProfitGuardedReasonMap.deleteMsg" aria-disabled="true" data-testid="style-profit-guarded-delete-msg" data-action-type="write" data-write-guard="readonly:style-profit-delete-msg" data-guard-state="guarded_readonly" @click="guardedAction('删除消息')">删除消息</el-button>
          <el-button :disabled="true" :title="styleProfitGuardedReasonMap.addMsg" aria-disabled="true" data-testid="style-profit-guarded-add-msg" data-action-type="write" data-write-guard="readonly:style-profit-add-msg" data-guard-state="guarded_readonly" @click="guardedAction('新增消息')">新增消息</el-button>
          <el-button :disabled="true" :title="styleProfitGuardedReasonMap.save" aria-disabled="true" data-testid="style-profit-guarded-save" data-action-type="write" data-write-guard="readonly:style-profit-save" data-guard-state="guarded_readonly" @click="guardedAction('保存')">保存</el-button>
          <el-button :disabled="true" :title="styleProfitGuardedReasonMap.cancel" aria-disabled="true" data-testid="style-profit-guarded-cancel" data-action-type="write" data-write-guard="readonly:style-profit-cancel" data-guard-state="guarded_readonly" @click="guardedAction('取消')">取消</el-button>
        </el-form-item>
      </el-form>
      <el-alert
        v-if="archiveFeedback"
        type="warning"
        :title="archiveFeedback"
        :closable="false"
        show-icon
        class="feedback-alert"
        data-testid="style-profit-archive-feedback"
      />
      <p class="readonly-hint" data-testid="style-profit-readonly-hint">
        当前页面为只读验证模式，写动作入口仅保留展示并已 guarded。
      </p>
      <StyleProfitSnapshotReadonlySection
        :summary="listSnapshotReadonlySectionSummary"
        data-testid="style-profit-snapshot-readonly-section"
      />
      <StyleProfitSourceAuditReadonly
        :summary="listSourceAuditReadonlySummary"
        test-id-prefix="cand494-style-profit-source-audit"
      />
      <StyleProfitGapReadonlySection
        test-id-prefix="style-profit-gap"
        :summary="listGapReadonlySummary"
        :metric-fields="STYLE_PROFIT_GAP_LIST_METRIC_FIELDS"
      />

      <el-empty v-if="!canRead" description="无款式利润查看权限，当前展示只读端到端锚点样例" data-testid="style-profit-no-permission" />
      <template>
        <el-alert
          v-if="errorMessage"
          type="error"
          :closable="false"
          show-icon
          :title="`订单款式利润预测明细表数据加载失败：${errorMessage}`"
          class="error-alert"
          data-testid="style-profit-error-alert"
        />
        <div class="summary-grid" data-testid="style-profit-summary-grid">
          <el-card shadow="never" class="summary-card" data-testid="style-profit-summary-revenue">
            <div class="summary-label">销售预测金额</div>
            <div class="summary-value">{{ formatAmount(totalRevenueAmount) }}</div>
          </el-card>
          <el-card shadow="never" class="summary-card" data-testid="style-profit-summary-cost">
            <div class="summary-label">成本预测金额</div>
            <div class="summary-value">{{ formatAmount(totalCostAmount) }}</div>
          </el-card>
          <el-card shadow="never" class="summary-card" data-testid="style-profit-summary-profit">
            <div class="summary-label">利润预测金额</div>
            <div class="summary-value">{{ formatAmount(totalProfitAmount) }}</div>
          </el-card>
          <el-card shadow="never" class="summary-card" data-testid="style-profit-summary-rate">
            <div class="summary-label">平均利润率</div>
            <div class="summary-value">{{ formatProfitRate(avgProfitRate) }}</div>
          </el-card>
        </div>
        <div data-testid="style-profit-table">
          <el-table
            :data="rows"
            border
            v-loading="loading"
            empty-text="暂无订单款式利润预测明细数据，请调整筛选条件后重试"
            data-testid="style-profit-main-table"
          >
          <el-table-column label="图片" width="80">
            <template #default>-</template>
          </el-table-column>
          <el-table-column prop="item_code" label="款号" min-width="130" />
          <el-table-column label="款式名称" min-width="140">
            <template #default="scope">{{ scope.row.item_code || '-' }}</template>
          </el-table-column>
          <el-table-column label="设计号" min-width="130">
            <template #default="scope">{{ scope.row.sales_order || '-' }}</template>
          </el-table-column>
          <el-table-column prop="company" label="品牌" min-width="120" />
          <el-table-column label="款式类型" min-width="110">
            <template #default>-</template>
          </el-table-column>
          <el-table-column label="年份" width="90">
            <template #default>-</template>
          </el-table-column>
          <el-table-column label="设计师" min-width="110">
            <template #default>-</template>
          </el-table-column>
          <el-table-column label="纸样师" min-width="110">
            <template #default>-</template>
          </el-table-column>
          <el-table-column label="车板师" min-width="110">
            <template #default>-</template>
          </el-table-column>
          <el-table-column label="打板次数" width="100">
            <template #default>-</template>
          </el-table-column>
          <el-table-column label="版类" min-width="90">
            <template #default>-</template>
          </el-table-column>
          <el-table-column label="打板颜色" min-width="100">
            <template #default>-</template>
          </el-table-column>
          <el-table-column label="打板数量" width="100">
            <template #default>-</template>
          </el-table-column>
          <el-table-column label="下单次数" width="100">
            <template #default="scope">{{ scope.row.sales_order ? '1' : '0' }}</template>
          </el-table-column>
          <el-table-column v-for="week in weekColumns" :key="week" :label="week" width="60">
            <template #default>-</template>
          </el-table-column>
          <el-table-column label="销售预测金额" width="140">
            <template #default="scope">{{ formatAmount(scope.row.revenue_amount) }}</template>
          </el-table-column>
          <el-table-column label="成本预测金额" width="140">
            <template #default="scope">{{ formatAmount(scope.row.actual_total_cost) }}</template>
          </el-table-column>
          <el-table-column label="利润预测金额" width="140">
            <template #default="scope">{{ formatAmount(scope.row.profit_amount) }}</template>
          </el-table-column>
          <el-table-column label="利润预测率" width="130">
            <template #default="scope">{{ formatProfitRate(scope.row.profit_rate) }}</template>
          </el-table-column>
          <el-table-column label="标题" min-width="170">
            <template #default="scope">{{ scope.row.snapshot_no }}</template>
          </el-table-column>
          <el-table-column prop="created_at" label="发送时间" min-width="180" />
          <el-table-column label="状态" min-width="120">
            <template #default="scope">
              <el-tag :type="statusTagType(scope.row.snapshot_status)" data-testid="style-profit-status-tag">
                {{ statusText(scope.row.snapshot_status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="发送人" min-width="110">
            <template #default="scope">{{ scope.row.created_by || '-' }}</template>
          </el-table-column>
          <el-table-column label="操作" width="100" fixed="right">
            <template #default="scope">
              <el-button
                link
                type="primary"
                :data-testid="`style-profit-detail-${scope.row.id}`"
                @click="goDetail(scope.row.id)"
              >
                详情
              </el-button>
            </template>
          </el-table-column>
          </el-table>
        </div>

        <div class="pager" data-testid="style-profit-pager">
          <el-pagination
            background
            layout="prev, pager, next, total, sizes"
            :current-page="query.page"
            :page-size="query.page_size"
            :total="total"
            :page-sizes="[10, 20, 50, 100]"
            data-testid="style-profit-pagination"
            @current-change="onPageChange"
            @size-change="onSizeChange"
          />
        </div>
      </template>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  fetchStyleProfitSnapshots,
  type StyleProfitSnapshotListItem,
} from '@/api/style_profit'
import { usePermissionStore } from '@/stores/permission'
import StyleProfitGapReadonlySection from '@/views/style_profit/components/StyleProfitGapReadonlySection.vue'
import StyleProfitSourceAuditReadonly from '@/views/style_profit/components/StyleProfitSourceAuditReadonly.vue'
import StyleProfitSnapshotReadonlySection from '@/views/style_profit/components/StyleProfitSnapshotReadonlySection.vue'
import { buildStyleProfitListGapReadonlySummary } from '@/views/style_profit/composables/useStyleProfitGapReadonly'
import { useStyleProfitSourceAuditReadonlySection } from '@/views/style_profit/composables/useStyleProfitSourceAuditReadonly'
import {
  useStyleProfitSnapshotReadonlySection,
} from '@/views/style_profit/composables/useStyleProfitSnapshotReadonly'
import { STYLE_PROFIT_GAP_LIST_METRIC_FIELDS } from '@/views/style_profit/constants/styleProfitGapFields'
import {
  STYLE_PROFIT_READONLY_GUARD_REASON_MAP,
} from '@/views/style_profit/constants/styleProfitReadonlyFields'

const route = useRoute()
const router = useRouter()
const permissionStore = usePermissionStore()
const styleProfitGuardedReasonMap = STYLE_PROFIT_READONLY_GUARD_REASON_MAP
const GLOBAL_READONLY_GUARD_ATTR = 'data-style-profit-list-readonly-disabled'
const GLOBAL_READONLY_PREV_DISABLED_ATTR = 'data-style-profit-list-prev-disabled'
const GLOBAL_READONLY_PREV_ARIA_DISABLED_ATTR = 'data-style-profit-list-prev-aria-disabled'
const GLOBAL_READONLY_PREV_TITLE_ATTR = 'data-style-profit-list-prev-title'
const GLOBAL_READONLY_PREV_TABINDEX_ATTR = 'data-style-profit-list-prev-tabindex'
const GLOBAL_READONLY_PREV_POINTER_EVENTS_ATTR = 'data-style-profit-list-prev-pointer-events'
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
let globalStyleProfitListGuardObserver: MutationObserver | null = null
const loading = ref<boolean>(false)
const rows = ref<StyleProfitSnapshotListItem[]>([])
const total = ref<number>(0)
const errorMessage = ref<string>('')
const archiveFeedback = ref<string>('')
const weekColumns = ['日', '一', '二', '三', '四', '五', '六']

const canRead = computed<boolean>(() => permissionStore.state.buttonPermissions.read)
const parityHint = computed<string>(() => String(route.query.parity || 'style-profit'))
const readonlyFocus = computed<string>(() => String(route.query.focus || ''))
const readonlyRoutePath = computed<string>(() => route.fullPath || route.path)
const readonlyQueryStateLabel = computed<string>(() => {
  const company = query.company.trim() || 'ALL_COMPANY'
  const itemCode = query.item_code.trim() || 'ALL_ITEM'
  const salesOrder = query.sales_order.trim() || 'ALL_ORDER'
  const status = query.snapshot_status || 'ALL_STATUS'
  return `company=${company}; item_code=${itemCode}; sales_order=${salesOrder}; snapshot_status=${status}; page=${query.page}`
})
const listGapReadonlySummary = computed(() => buildStyleProfitListGapReadonlySummary(rows.value, parityHint.value))
const { styleProfitSnapshotReadonlySummary: listSnapshotReadonlySectionSummary } = useStyleProfitSnapshotReadonlySection({
  mode: 'list',
  rows,
  canRead,
  currentPath: readonlyRoutePath,
  parity: parityHint,
  focus: readonlyFocus,
  queryStateLabel: readonlyQueryStateLabel,
})
const { styleProfitSourceAuditReadonlySummary: listSourceAuditReadonlySummary } = useStyleProfitSourceAuditReadonlySection({
  mode: 'list',
  rows,
  canRead,
  parity: parityHint,
  focus: readonlyFocus,
  queryStateLabel: readonlyQueryStateLabel,
})

const query = reactive({
  company: '',
  item_code: '',
  sales_order: '',
  from_date: '',
  to_date: '',
  snapshot_status: '',
  page: 1,
  page_size: 20,
})

const archiveParams = reactive({
  revenue_mode: 'actual_first',
  formula_version: 'STYLE_PROFIT_V1',
})

const readonlyFallbackRows: StyleProfitSnapshotListItem[] = [
  {
    id: 101,
    snapshot_no: 'SP-READONLY-2026-001',
    company: 'LINGYI',
    company_full_name: '领意服装',
    item_code: 'STYLE-RO-001',
    sales_order: 'SO-RO-001',
    from_date: '2026-05-01',
    to_date: '2026-05-31',
    revenue_status: 'actual_first',
    revenue_amount: '128000',
    actual_total_cost: '86000',
    standard_total_cost: '82000',
    profit_amount: '42000',
    profit_rate: '0.3281',
    snapshot_status: 'complete',
    allocation_status: 'mapped',
    include_provisional_subcontract: false,
    formula_version: 'STYLE_PROFIT_V1',
    unresolved_count: 0,
    created_by: 'readonly',
    created_at: '2026-05-26 09:00:00',
  },
]

const applyReadonlyFallbackRows = (): void => {
  rows.value = readonlyFallbackRows
  total.value = readonlyFallbackRows.length
}

const formatAmount = (value: string | number | null | undefined): string => {
  if (value === null || value === undefined || value === '') {
    return '-'
  }
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric.toFixed(2) : String(value)
}

const formatProfitRate = (value: string | number | null | undefined): string => {
  if (value === null || value === undefined || value === '') {
    return '-'
  }
  const numeric = Number(value)
  return Number.isFinite(numeric) ? `${(numeric * 100).toFixed(2)}%` : String(value)
}

const toNumber = (value: string | number | null | undefined): number => {
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric : 0
}

const totalRevenueAmount = computed<number>(() => rows.value.reduce((sum, row) => sum + toNumber(row.revenue_amount), 0))
const totalCostAmount = computed<number>(() => rows.value.reduce((sum, row) => sum + toNumber(row.actual_total_cost), 0))
const totalProfitAmount = computed<number>(() => rows.value.reduce((sum, row) => sum + toNumber(row.profit_amount), 0))
const avgProfitRate = computed<number | null>(() => {
  if (rows.value.length === 0) {
    return null
  }
  const sum = rows.value.reduce((acc, row) => acc + toNumber(row.profit_rate ?? 0), 0)
  return sum / rows.value.length
})

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

const hasRequiredScope = (): boolean => {
  return Boolean(query.company.trim()) && Boolean(query.item_code.trim())
}

const resetRows = (): void => {
  rows.value = []
  total.value = 0
}

const resetQuery = (): void => {
  query.company = ''
  query.item_code = ''
  query.sales_order = ''
  query.from_date = ''
  query.to_date = ''
  query.snapshot_status = ''
  query.page = 1
  query.page_size = 20
  errorMessage.value = ''
  archiveFeedback.value = ''
  applyReadonlyFallbackRows()
}

const guardedAction = (action: string): void => {
  archiveFeedback.value = `${action}仅保留展示入口，当前为本地只读验证模式`
  ElMessage.info(archiveFeedback.value)
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
  globalStyleProfitListGuardObserver?.disconnect()
  globalStyleProfitListGuardObserver = null
}

const startGlobalReadonlyActionGuardObserver = (): void => {
  if (typeof document === 'undefined' || globalStyleProfitListGuardObserver) {
    return
  }

  globalStyleProfitListGuardObserver = new MutationObserver(() => {
    void applyGlobalReadonlyActionGuards()
  })
  globalStyleProfitListGuardObserver.observe(document.body, {
    childList: true,
    subtree: true,
  })
}

const loadRows = async (): Promise<void> => {
  if (!canRead.value) {
    applyReadonlyFallbackRows()
    errorMessage.value = ''
    return
  }
  if (!hasRequiredScope()) {
    ElMessage.warning('请先输入加工厂与款号/款名后再查询')
    applyReadonlyFallbackRows()
    errorMessage.value = ''
    return
  }

  errorMessage.value = ''
  loading.value = true
  try {
    const result = await fetchStyleProfitSnapshots({
      company: query.company.trim(),
      item_code: query.item_code.trim(),
      sales_order: query.sales_order.trim() || undefined,
      from_date: query.from_date || undefined,
      to_date: query.to_date || undefined,
      snapshot_status: query.snapshot_status || undefined,
      page: query.page,
      page_size: query.page_size,
    })
    rows.value = result.data.items
    total.value = result.data.total
  } catch (error) {
    const message = (error as Error).message || '未知错误'
    errorMessage.value = message
    ElMessage.error(message)
    applyReadonlyFallbackRows()
  } finally {
    loading.value = false
  }
}

const goDetail = (snapshotId: number): void => {
  router.push({ path: '/reports/style-profit/detail', query: { id: String(snapshotId), parity: parityHint.value } })
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

onMounted(async () => {
  try {
    await permissionStore.loadCurrentUser()
    await permissionStore.loadModuleActions('style_profit')
  } catch (error) {
    ElMessage.error((error as Error).message)
    return
  }
  if (canRead.value && hasRequiredScope()) {
    await loadRows()
  } else {
    applyReadonlyFallbackRows()
  }
  await applyGlobalReadonlyActionGuards()
  startGlobalReadonlyActionGuardObserver()
})

onBeforeUnmount(() => {
  stopGlobalReadonlyActionGuardObserver()
  restoreGlobalReadonlyGuardElements()
})
</script>

<style scoped>
.style-profit-list-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.header-row {
  display: flex;
  justify-content: flex-start;
  align-items: center;
}

.title-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.page-title {
  font-weight: 600;
}

.page-subtitle {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.parity-hint {
  font-size: 12px;
  color: var(--el-color-info);
}

.query-form {
  margin-bottom: 12px;
}

.button-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.error-alert {
  margin-bottom: 12px;
}

.feedback-alert {
  margin-bottom: 12px;
}

.readonly-source-panel {
  margin-bottom: 12px;
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

.readonly-hint {
  margin-top: 0;
  margin-bottom: 12px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 12px;
}

.summary-card {
  border: 1px solid var(--el-border-color-lighter);
}

.summary-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.summary-value {
  margin-top: 6px;
  font-size: 18px;
  font-weight: 600;
}

.pager {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}

.warn-text {
  color: var(--el-color-danger);
}
</style>
