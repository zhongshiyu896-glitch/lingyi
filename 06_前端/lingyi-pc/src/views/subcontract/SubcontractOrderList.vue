<template>
  <div class="subcontract-list-page" data-testid="yisuan-1to1-subcontract-list-shell">
    <el-card shadow="never">
      <template #header>
        <div class="header-row">
          <div>
            <h2>委外订单列表（本地可试用）</h2>
            <p class="sub-title">local-dev only / read-only usable slice / no inventory or purchase release</p>
          </div>
          <div class="header-actions">
            <el-button type="primary" plain :loading="loading" @click="loadRows">刷新列表</el-button>
          </div>
        </div>
      </template>
      <el-alert
        type="warning"
        :closable="false"
        title="仅允许 local-dev/test_data 展示；禁止触发真实收货、入库、库存影响、worker 推送或 ERPNext 生命周期。"
      />
      <el-alert
        v-if="isMaterialPurchaseParity"
        class="parity-alert"
        type="info"
        :closable="false"
        data-testid="realobj-subcontract-parity-alert"
        title="materialPurchase final_path: /materialPurchase/materialPurchaseProcess -> /subcontract/list?parity=material-purchase"
      />
    </el-card>

    <el-card shadow="never" data-testid="yisuan-1to1-subcontract-list-filter-panel">
      <el-form :inline="true" @submit.prevent>
        <el-form-item label="关键字">
          <el-input v-model="query.keyword" clearable placeholder="单据号 / 供应商 / 物料 / 销售订单" style="width: 240px" />
        </el-form-item>
        <el-form-item label="供应商">
          <el-input v-model="query.supplier" clearable placeholder="供应商 / 加工厂" style="width: 180px" />
        </el-form-item>
        <el-form-item label="公司">
          <el-input v-model="query.company" clearable placeholder="公司" style="width: 150px" />
        </el-form-item>
        <el-form-item label="工序">
          <el-input v-model="query.process_name" clearable placeholder="工序" style="width: 150px" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.status" clearable placeholder="全部" style="width: 150px">
            <el-option label="draft" value="draft" />
            <el-option label="issued" value="issued" />
            <el-option label="processing" value="processing" />
            <el-option label="waiting_receive" value="waiting_receive" />
            <el-option label="waiting_inspection" value="waiting_inspection" />
            <el-option label="completed" value="completed" />
          </el-select>
        </el-form-item>
        <el-form-item label="单据日期">
          <el-date-picker
            v-model="query.from_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="开始日期"
            style="width: 150px"
          />
        </el-form-item>
        <el-form-item label="-">
          <el-date-picker
            v-model="query.to_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="结束日期"
            style="width: 150px"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="applyQuery">查询</el-button>
          <el-button :loading="loading" @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>

      <el-alert v-if="feedback" :title="feedback" type="info" :closable="false" class="feedback" />
    </el-card>

    <el-card shadow="never" data-testid="yisuan-1to1-subcontract-list-summary">
      <template #header>
        <div class="summary-header">
          <span>列表摘要与只读动作</span>
          <div class="readonly-actions">
            <el-tooltip v-for="action in readonlyGuardActions" :key="action.label" :content="action.reason" placement="top">
              <span>
                <el-button disabled>{{ action.label }}</el-button>
              </span>
            </el-tooltip>
          </div>
        </div>
      </template>
      <el-descriptions border :column="3">
        <el-descriptions-item label="筛选结果">{{ summary.filteredCount }}</el-descriptions-item>
        <el-descriptions-item label="供应商数">{{ summary.supplierCount }}</el-descriptions-item>
        <el-descriptions-item label="计划数量">{{ formatNumber(summary.plannedQty) }}</el-descriptions-item>
        <el-descriptions-item label="已发料">{{ formatNumber(summary.issuedQty) }}</el-descriptions-item>
        <el-descriptions-item label="已回料">{{ formatNumber(summary.receivedQty) }}</el-descriptions-item>
        <el-descriptions-item label="已验收">{{ formatNumber(summary.acceptedQty) }}</el-descriptions-item>
        <el-descriptions-item label="加工中">{{ summary.processingCount }}</el-descriptions-item>
        <el-descriptions-item label="待收货">{{ summary.waitingReceiveCount }}</el-descriptions-item>
        <el-descriptions-item label="待验货">{{ summary.waitingInspectionCount }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <el-card shadow="never">
      <el-table
        :data="rows"
        border
        v-loading="loading"
        empty-text="暂无委外订单，已保留本地可试用入口"
        data-testid="yisuan-1to1-subcontract-list-table"
      >
        <el-table-column label="单据号 / 销售订单" min-width="220">
          <template #default="{ row }">
            <div class="stacked-cell">
              <strong>{{ row.subcontract_no }}</strong>
              <span>SO {{ row.sales_order || '-' }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="供应商 / 公司" min-width="200">
          <template #default="{ row }">
            <div class="stacked-cell">
              <span>{{ row.supplier }}</span>
              <span>{{ row.company || '-' }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="物料 / 工序" min-width="180">
          <template #default="{ row }">
            <div class="stacked-cell">
              <span>{{ row.item_code }}</span>
              <span>{{ row.process_name }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="交期参考" min-width="120">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="进度摘要" min-width="240">
          <template #default="{ row }">
            <div class="stacked-cell">
              <el-tag :type="progressStageType(row)" effect="plain">{{ progressStageLabel(row) }}</el-tag>
              <span>计划 / 发料 / 回料 / 验收：{{ row.planned_qty }} / {{ row.issued_qty }} / {{ row.received_qty }} / {{ row.accepted_qty }}</span>
              <span>计划 {{ row.production_plan_id || '-' }} / 工单 {{ row.work_order || '-' }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="状态标签" min-width="220">
          <template #default="{ row }">
            <div class="tag-stack">
              <el-tag :type="statusType(row.status)">{{ statusLabel(row.status) }}</el-tag>
              <el-tag :type="resourceScopeType(row.resource_scope_status)" effect="plain">
                {{ resourceScopeLabel(row.resource_scope_status) }}
              </el-tag>
              <el-tag
                v-if="row.profit_scope_status"
                :type="profitScopeType(row.profit_scope_status)"
                effect="plain"
              >
                {{ profitScopeLabel(row.profit_scope_status) }}
              </el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <div class="stacked-cell">
              <el-button link type="primary" @click="openDetail(row.id)">查看详情</el-button>
              <el-button link disabled>收货已冻结</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card shadow="never" data-testid="realobj-subcontract-readback-evidence">
      <template #header>
        <span>本地可试用边界</span>
      </template>
      <el-descriptions border :column="2">
        <el-descriptions-item label="final_path">{{ finalPath }}</el-descriptions-item>
        <el-descriptions-item label="parity">{{ parityToken || '-' }}</el-descriptions-item>
        <el-descriptions-item label="local_dev_only">true</el-descriptions-item>
        <el-descriptions-item label="receipt_release">false</el-descriptions-item>
        <el-descriptions-item label="inventory_effect_release">false</el-descriptions-item>
        <el-descriptions-item label="stock_worker_push">false</el-descriptions-item>
        <el-descriptions-item label="erpnext_production">false</el-descriptions-item>
        <el-descriptions-item label="real_purchase_account">false</el-descriptions-item>
        <el-descriptions-item label="row_count">{{ rows.length }}</el-descriptions-item>
        <el-descriptions-item label="fallback_snapshot_used">{{ fallbackSnapshotUsed ? 'true' : 'false' }}</el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { SubcontractOrderListItem } from '@/api/subcontract'
import {
  buildDefaultSubcontractReadonlyQuery,
  buildSubcontractReadonlySummary,
  fetchSubcontractOrdersReadback,
  filterSubcontractRows,
  hasSubcontractReadonlyFilters,
} from '@/api/subcontract_readback'
import { useSubcontractReadonly } from './composables/useSubcontractReadonly'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const rows = ref<SubcontractOrderListItem[]>([])
const feedback = ref('')
const fallbackSnapshotUsed = ref(false)

const query = reactive(buildDefaultSubcontractReadonlyQuery())

const {
  formatDateTime,
  formatNumber,
  profitScopeLabel,
  profitScopeType,
  progressStageLabel,
  progressStageType,
  readonlyGuardActions,
  resourceScopeLabel,
  resourceScopeType,
  statusLabel,
  statusType,
} = useSubcontractReadonly()

const parityToken = computed(() => {
  const raw = route.query.parity
  if (Array.isArray(raw)) return String(raw[0] || '').trim()
  return String(raw || '').trim()
})

const isMaterialPurchaseParity = computed(() => parityToken.value === 'material-purchase')

const finalPath = computed(() =>
  isMaterialPurchaseParity.value ? '/subcontract/list?parity=material-purchase' : '/subcontract/list',
)

const summary = computed(() => buildSubcontractReadonlySummary(rows.value))

const buildSyntheticRows = (): SubcontractOrderListItem[] => {
  const supplier = isMaterialPurchaseParity.value ? '本地演示供应商' : '本地演示外协厂'
  return [
    {
      id: 900601,
      subcontract_no: 'SC-LOCAL-USABLE-001',
      supplier,
      item_code: 'ITEM-A',
      company: 'COMP-A',
      bom_id: 1,
      process_name: '外发裁剪',
      planned_qty: '120',
      subcontract_rate: '0.65',
      issued_qty: '90',
      received_qty: '56',
      inspected_qty: '56',
      rejected_qty: '3',
      accepted_qty: '53',
      gross_amount: '6800',
      deduction_amount: '180',
      net_amount: '6620',
      status: 'processing',
      resource_scope_status: 'ready',
      profit_scope_status: 'resolved',
      profit_scope_error_code: '',
      sales_order: isMaterialPurchaseParity.value ? 'SO-LOCAL-001' : 'SO-LOCAL-TRACE',
      sales_order_item: isMaterialPurchaseParity.value ? 'SO-LOCAL-001-1' : 'SO-LOCAL-TRACE-1',
      latest_issue_outbox_id: null,
      latest_issue_sync_status: null,
      latest_issue_stock_entry_name: null,
      latest_issue_idempotency_key: null,
      latest_issue_error_code: null,
      latest_receipt_outbox_id: null,
      latest_receipt_sync_status: null,
      latest_receipt_stock_entry_name: null,
      latest_receipt_idempotency_key: null,
      latest_receipt_error_code: null,
      production_plan_id: isMaterialPurchaseParity.value ? 3001 : 3002,
      work_order: isMaterialPurchaseParity.value ? 'WO-LOCAL-3001' : 'WO-LOCAL-3002',
      job_card: isMaterialPurchaseParity.value ? 'JC-LOCAL-3001' : 'JC-LOCAL-3002',
      created_at: new Date().toISOString(),
    },
  ]
}

const loadRows = async (): Promise<void> => {
  loading.value = true
  feedback.value = ''
  fallbackSnapshotUsed.value = false
  try {
    const response = await fetchSubcontractOrdersReadback(query)
    const serverRows = response.data.items || []
    const sourceRows = serverRows.length > 0 ? serverRows : buildSyntheticRows()
    rows.value = filterSubcontractRows(sourceRows, query)

    if (serverRows.length === 0) {
      fallbackSnapshotUsed.value = true
      feedback.value = '未读取到本地委外单，已回退 synthetic snapshot 保持入口可试用。'
      return
    }

    if (rows.value.length === 0 && hasSubcontractReadonlyFilters(query)) {
      feedback.value = '当前筛选未命中委外订单，未触发任何收货、入库或库存影响动作。'
    }
  } catch (error) {
    rows.value = filterSubcontractRows(buildSyntheticRows(), query)
    fallbackSnapshotUsed.value = true
    feedback.value = (error as Error).message || '委外订单列表 API 不可用，已回退 synthetic snapshot。'
  } finally {
    loading.value = false
  }
}

const applyQuery = (): void => {
  query.page = 1
  void loadRows()
}

const resetQuery = (): void => {
  Object.assign(query, buildDefaultSubcontractReadonlyQuery())
  void loadRows()
}

const openDetail = (orderId: number): void => {
  router.push({
    path: '/subcontract/detail',
    query: {
      id: String(orderId),
      parity: parityToken.value || undefined,
    },
  })
}

onMounted(() => {
  void loadRows()
})
</script>

<style scoped>
.subcontract-list-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.header-row,
.summary-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.header-row h2 {
  margin: 0;
  font-size: 18px;
}

.sub-title {
  margin: 2px 0 0;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.header-actions,
.readonly-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.parity-alert,
.feedback {
  margin-top: 12px;
}

.stacked-cell,
.tag-stack {
  display: flex;
  flex-direction: column;
  gap: 4px;
  line-height: 1.4;
}

.tag-stack {
  align-items: flex-start;
}
</style>
