<template>
  <div class="warehouse-page">
    <el-card shadow="never">
      <template #header>
        <div class="header-row">
          <span>仓库库存台账与预警看板（只读）</span>
          <el-button type="primary" :loading="loading" @click="loadAll">查询</el-button>
        </div>
      </template>

      <el-form :inline="true" :model="query">
        <el-form-item label="公司">
          <el-input v-model="query.company" clearable placeholder="company" />
        </el-form-item>
        <el-form-item label="仓库">
          <el-input v-model="query.warehouse" clearable placeholder="warehouse" />
        </el-form-item>
        <el-form-item label="物料">
          <el-input v-model="query.item_code" clearable placeholder="item_code" />
        </el-form-item>
        <el-form-item label="开始日期">
          <el-date-picker v-model="query.from_date" type="date" value-format="YYYY-MM-DD" clearable />
        </el-form-item>
        <el-form-item label="结束日期">
          <el-date-picker v-model="query.to_date" type="date" value-format="YYYY-MM-DD" clearable />
        </el-form-item>
      </el-form>

      <el-alert
        v-if="!canRead"
        type="warning"
        :closable="false"
        show-icon
        title="无仓库查看权限，当前仅展示只读骨架"
        class="scope-alert"
      />
      <el-tabs v-model="activeTab">
        <el-tab-pane label="库存台账" name="ledger">
          <el-table :data="ledgerRows" border v-loading="loading">
            <el-table-column prop="company" label="公司" min-width="120" />
            <el-table-column prop="warehouse" label="仓库" min-width="150" />
            <el-table-column prop="item_code" label="物料" min-width="150" />
            <el-table-column prop="posting_date" label="过账日期" width="120" />
            <el-table-column prop="voucher_type" label="凭证类型" min-width="120" />
            <el-table-column prop="voucher_no" label="凭证编号" min-width="140" />
            <el-table-column label="本次数量" width="120">
              <template #default="scope">{{ formatAmount(scope.row.actual_qty) }}</template>
            </el-table-column>
            <el-table-column label="结存数量" width="120">
              <template #default="scope">{{ formatAmount(scope.row.qty_after_transaction) }}</template>
            </el-table-column>
            <el-table-column label="估值单价" width="120">
              <template #default="scope">{{ formatAmount(scope.row.valuation_rate) }}</template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="库存聚合" name="summary">
          <el-table :data="summaryRows" border v-loading="loading" :row-class-name="summaryRowClassName">
            <el-table-column prop="company" label="公司" min-width="120" />
            <el-table-column prop="warehouse" label="仓库" min-width="150" />
            <el-table-column prop="item_code" label="物料" min-width="150" />
            <el-table-column label="现有库存" width="120">
              <template #default="scope">{{ formatAmount(scope.row.actual_qty) }}</template>
            </el-table-column>
            <el-table-column label="预计库存" width="120">
              <template #default="scope">{{ formatAmount(scope.row.projected_qty) }}</template>
            </el-table-column>
            <el-table-column label="预留库存" width="120">
              <template #default="scope">{{ formatAmount(scope.row.reserved_qty) }}</template>
            </el-table-column>
            <el-table-column label="在途库存" width="120">
              <template #default="scope">{{ formatAmount(scope.row.ordered_qty) }}</template>
            </el-table-column>
            <el-table-column label="补货阈值" width="120">
              <template #default="scope">{{ formatAmount(scope.row.reorder_level) }}</template>
            </el-table-column>
            <el-table-column label="安全库存" width="120">
              <template #default="scope">{{ formatAmount(scope.row.safety_stock) }}</template>
            </el-table-column>
            <el-table-column label="阈值状态" min-width="180">
              <template #default="scope">
                <el-tag v-if="scope.row.threshold_missing" type="info" effect="plain">阈值缺失</el-tag>
                <el-tag v-if="scope.row.is_below_reorder" type="warning" effect="plain">低于补货阈值</el-tag>
                <el-tag v-if="scope.row.is_below_safety" type="danger" effect="plain">低于安全库存</el-tag>
                <span v-if="!scope.row.threshold_missing && !scope.row.is_below_reorder && !scope.row.is_below_safety">正常</span>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="库存预警" name="alerts">
          <div class="alert-filter">
            <el-radio-group v-model="query.alert_type" @change="loadAlertsOnly">
              <el-radio-button label="">全部</el-radio-button>
              <el-radio-button label="low_stock">低库存</el-radio-button>
              <el-radio-button label="below_safety">安全库存不足</el-radio-button>
              <el-radio-button label="overstock">超储</el-radio-button>
              <el-radio-button label="stale_stock">呆滞</el-radio-button>
            </el-radio-group>
          </div>
          <el-table :data="alertsRows" border v-loading="loading" :row-class-name="alertRowClassName">
            <el-table-column prop="company" label="公司" min-width="120" />
            <el-table-column prop="warehouse" label="仓库" min-width="150" />
            <el-table-column prop="item_code" label="物料" min-width="150" />
            <el-table-column prop="alert_type" label="预警类型" width="130" />
            <el-table-column label="当前库存" width="120">
              <template #default="scope">{{ formatAmount(scope.row.current_qty) }}</template>
            </el-table-column>
            <el-table-column label="阈值" width="120">
              <template #default="scope">{{ formatAmount(scope.row.threshold_qty) }}</template>
            </el-table-column>
            <el-table-column label="差值" width="120">
              <template #default="scope">{{ formatAmount(scope.row.gap_qty) }}</template>
            </el-table-column>
            <el-table-column prop="last_movement_date" label="最近异动" width="130" />
            <el-table-column prop="severity" label="严重度" width="100" />
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="成品入仓" name="finished_goods_inbound">
          <div class="inbound-meta-row">
            <el-tag type="info" effect="plain">
              强制参数：showCompleted={{ inboundMeta.show_completed_forced ? 'true' : 'false' }}
            </el-tag>
            <el-tag type="warning" effect="plain">
              分配口径：{{ inboundMeta.allocation_contract || '-' }}
            </el-tag>
            <el-button type="primary" plain :loading="inboundLoading" @click="loadInboundCandidates">刷新候选</el-button>
          </div>
          <el-alert
            class="inbound-alert"
            type="warning"
            :closable="false"
            :title="`受限入口：${inboundMeta.disabled_entry_label || '成品预约入仓 -> 创建成品入仓'}`"
            :description="inboundMeta.disabled_entry_reason || '当前入口受限，禁止直接放开'"
          />

          <el-table :data="inboundCandidates" border v-loading="inboundLoading">
            <el-table-column prop="source_id" label="来源ID" min-width="160" />
            <el-table-column prop="source_label" label="来源说明" min-width="220" />
            <el-table-column prop="item_code" label="物料" min-width="140" />
            <el-table-column label="数量" width="120">
              <template #default="scope">{{ formatAmount(scope.row.qty) }}</template>
            </el-table-column>
            <el-table-column prop="uom" label="单位" width="100" />
            <el-table-column label="状态" min-width="180">
              <template #default="scope">
                <el-tag v-if="scope.row.disabled" type="danger" effect="plain">
                  受限：{{ scope.row.disabled_reason || '不可创建' }}
                </el-tag>
                <el-tag v-else type="success" effect="plain">可创建草稿</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="150" fixed="right">
              <template #default="scope">
                <el-button
                  type="primary"
                  link
                  :disabled="scope.row.disabled || !canCreateInboundDraft"
                  :loading="inboundCreatingSourceId === scope.row.source_id"
                  @click="createInboundDraft(scope.row)"
                >
                  创建草稿
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <div class="inbound-draft-panel" v-if="inboundDraft">
            <div class="inbound-draft-header">
              <span>草稿详情 #{{ inboundDraft.id }}</span>
              <div class="inbound-draft-actions">
                <el-button size="small" @click="refreshInboundDraft">刷新详情</el-button>
                <el-button size="small" @click="refreshInboundOutbox">刷新Outbox</el-button>
                <el-button
                  size="small"
                  type="danger"
                  plain
                  :disabled="inboundDraft.status === 'cancelled' || !canCancelInboundDraft"
                  @click="cancelInboundDraft"
                >
                  取消草稿
                </el-button>
              </div>
            </div>

            <el-descriptions :column="2" border>
              <el-descriptions-item label="状态">{{ inboundDraft.status }}</el-descriptions-item>
              <el-descriptions-item label="分配模式">{{ inboundDraft.allocation_mode || '-' }}</el-descriptions-item>
              <el-descriptions-item label="严格分配失败原因">
                {{ inboundDraft.strict_failure_reason || '-' }}
              </el-descriptions-item>
              <el-descriptions-item label="showCompleted 强制">
                {{ inboundDraft.show_completed_forced === true ? 'true' : inboundDraft.show_completed_forced === false ? 'false' : '-' }}
              </el-descriptions-item>
              <el-descriptions-item label="目标仓库">{{ inboundDraft.target_warehouse || '-' }}</el-descriptions-item>
              <el-descriptions-item label="来源单号">{{ inboundDraft.source_id }}</el-descriptions-item>
            </el-descriptions>

            <el-table :data="inboundDraft.items" border class="inbound-draft-items">
              <el-table-column prop="item_code" label="物料" min-width="140" />
              <el-table-column label="数量" width="120">
                <template #default="scope">{{ formatAmount(scope.row.qty) }}</template>
              </el-table-column>
              <el-table-column prop="uom" label="单位" width="100" />
              <el-table-column prop="target_warehouse" label="目标仓库" min-width="140" />
            </el-table>

            <el-descriptions :column="2" border v-if="inboundOutbox" class="inbound-outbox">
              <el-descriptions-item label="Outbox状态">{{ inboundOutbox.status }}</el-descriptions-item>
              <el-descriptions-item label="重试次数">{{ inboundOutbox.retry_count }}</el-descriptions-item>
              <el-descriptions-item label="外部引用">{{ inboundOutbox.external_ref || '-' }}</el-descriptions-item>
              <el-descriptions-item label="错误信息">{{ inboundOutbox.error_message || '-' }}</el-descriptions-item>
            </el-descriptions>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  cancelWarehouseStockEntryDraft,
  fetchWarehouseAlerts,
  fetchWarehouseFinishedGoodsInboundCandidates,
  fetchWarehouseStockEntryDraft,
  fetchWarehouseStockLedger,
  fetchWarehouseStockEntryOutboxStatus,
  fetchWarehouseStockSummary,
  createWarehouseStockEntryDraft,
  type WarehouseAlertItem,
  type WarehouseFinishedGoodsInboundCandidateItem,
  type WarehouseFinishedGoodsInboundCandidatesData,
  type WarehouseStockLedgerItem,
  type WarehouseStockEntryDraftData,
  type WarehouseStockEntryOutboxStatusData,
  type WarehouseStockSummaryItem,
} from '@/api/warehouse'
import { usePermissionStore } from '@/stores/permission'

const permissionStore = usePermissionStore()
const loading = ref<boolean>(false)
const inboundLoading = ref<boolean>(false)
const activeTab = ref<'ledger' | 'summary' | 'alerts' | 'finished_goods_inbound'>('ledger')
const ledgerRows = ref<WarehouseStockLedgerItem[]>([])
const summaryRows = ref<WarehouseStockSummaryItem[]>([])
const alertsRows = ref<WarehouseAlertItem[]>([])
const inboundCandidates = ref<WarehouseFinishedGoodsInboundCandidateItem[]>([])
const inboundMeta = reactive<WarehouseFinishedGoodsInboundCandidatesData>({
  company: '',
  show_completed_forced: true,
  disabled_entry_label: '成品预约入仓 -> 创建成品入仓',
  disabled_entry_reason: '当前入口存在受限状态，需按冻结口径提示，不得直接放开',
  allocation_contract: 'strict_alloc -> zero_placeholder_fallback',
  items: [],
})
const inboundCreatingSourceId = ref<string>('')
const inboundDraft = ref<WarehouseStockEntryDraftData | null>(null)
const inboundOutbox = ref<WarehouseStockEntryOutboxStatusData | null>(null)
const canRead = computed<boolean>(() => permissionStore.state.buttonPermissions.read)
const canCreateInboundDraft = computed<boolean>(() => permissionStore.state.actions.includes('warehouse:stock_entry_draft'))
const canCancelInboundDraft = computed<boolean>(() => permissionStore.state.actions.includes('warehouse:stock_entry_cancel'))

const query = reactive({
  company: '',
  warehouse: '',
  item_code: '',
  from_date: '',
  to_date: '',
  page: 1,
  page_size: 50,
  alert_type: '',
})

const formatAmount = (value: string | number | null | undefined): string => {
  if (value === null || value === undefined || value === '') {
    return '-'
  }
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric.toFixed(2) : String(value)
}

const normalizeQuery = () => ({
  company: query.company.trim() || undefined,
  warehouse: query.warehouse.trim() || undefined,
  item_code: query.item_code.trim() || undefined,
  from_date: query.from_date || undefined,
  to_date: query.to_date || undefined,
})

const loadAll = async (): Promise<void> => {
  if (!canRead.value) {
    ledgerRows.value = []
    summaryRows.value = []
    alertsRows.value = []
    inboundCandidates.value = []
    return
  }
  loading.value = true
  try {
    const normalized = normalizeQuery()
    const [ledgerResult, summaryResult, alertsResult] = await Promise.all([
      fetchWarehouseStockLedger({
        ...normalized,
        page: query.page,
        page_size: query.page_size,
      }),
      fetchWarehouseStockSummary(normalized),
      fetchWarehouseAlerts({ ...normalized, alert_type: query.alert_type as '' | 'low_stock' | 'below_safety' | 'overstock' | 'stale_stock' }),
    ])
    ledgerRows.value = ledgerResult.data.items
    summaryRows.value = summaryResult.data.items
    alertsRows.value = alertsResult.data.items
    if (normalized.company) {
      await loadInboundCandidates(true)
    }
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    loading.value = false
  }
}

const loadAlertsOnly = async (): Promise<void> => {
  if (!canRead.value) {
    alertsRows.value = []
    return
  }
  loading.value = true
  try {
    const normalized = normalizeQuery()
    const alertsResult = await fetchWarehouseAlerts({
      ...normalized,
      alert_type: query.alert_type as '' | 'low_stock' | 'below_safety' | 'overstock' | 'stale_stock',
    })
    alertsRows.value = alertsResult.data.items
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    loading.value = false
  }
}

const loadInboundCandidates = async (silent = false): Promise<void> => {
  if (!canRead.value) {
    inboundCandidates.value = []
    return
  }
  const company = query.company.trim()
  if (!company) {
    if (!silent) {
      ElMessage.warning('请先填写公司后再查询成品入仓候选')
    }
    inboundCandidates.value = []
    return
  }
  inboundLoading.value = true
  try {
    const result = await fetchWarehouseFinishedGoodsInboundCandidates({
      company,
      item_code: query.item_code.trim() || undefined,
    })
    inboundMeta.company = result.data.company || company
    inboundMeta.show_completed_forced = result.data.show_completed_forced
    inboundMeta.disabled_entry_label = result.data.disabled_entry_label
    inboundMeta.disabled_entry_reason = result.data.disabled_entry_reason
    inboundMeta.allocation_contract = result.data.allocation_contract
    inboundCandidates.value = result.data.items
  } catch (error) {
    if (!silent) {
      ElMessage.error((error as Error).message)
    }
  } finally {
    inboundLoading.value = false
  }
}

const createInboundDraft = async (candidate: WarehouseFinishedGoodsInboundCandidateItem): Promise<void> => {
  if (!canCreateInboundDraft.value) {
    ElMessage.warning('当前账号无 warehouse:stock_entry_draft 权限')
    return
  }

  const company = query.company.trim()
  const targetWarehouse = query.warehouse.trim()
  if (!company) {
    ElMessage.error('company 不能为空')
    return
  }
  if (!targetWarehouse) {
    ElMessage.error('请先填写目标仓库（warehouse）')
    return
  }

  inboundCreatingSourceId.value = candidate.source_id
  try {
    const result = await createWarehouseStockEntryDraft({
      company,
      purpose: 'Material Receipt',
      source_type: 'finished_goods_inbound',
      source_id: candidate.source_id,
      finished_goods_source_id: candidate.source_id,
      target_warehouse: targetWarehouse,
      idempotency_key: `fg-${candidate.source_id}-${Date.now()}`,
      items: [
        {
          item_code: candidate.item_code,
          qty: candidate.qty,
          uom: candidate.uom,
          target_warehouse: targetWarehouse,
        },
      ],
    })
    inboundDraft.value = result.data
    inboundOutbox.value = result.data.outbox || null
    ElMessage.success('成品入仓草稿创建成功（仅本地草稿+outbox）')
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    inboundCreatingSourceId.value = ''
  }
}

const refreshInboundDraft = async (): Promise<void> => {
  if (!inboundDraft.value) return
  try {
    const result = await fetchWarehouseStockEntryDraft(inboundDraft.value.id)
    inboundDraft.value = result.data
  } catch (error) {
    ElMessage.error((error as Error).message)
  }
}

const refreshInboundOutbox = async (): Promise<void> => {
  if (!inboundDraft.value) return
  try {
    const result = await fetchWarehouseStockEntryOutboxStatus(inboundDraft.value.id)
    inboundOutbox.value = result.data
  } catch (error) {
    ElMessage.error((error as Error).message)
  }
}

const cancelInboundDraft = async (): Promise<void> => {
  if (!inboundDraft.value) return
  if (!canCancelInboundDraft.value) {
    ElMessage.warning('当前账号无 warehouse:stock_entry_cancel 权限')
    return
  }
  try {
    const result = await cancelWarehouseStockEntryDraft(inboundDraft.value.id, '成品入仓页手动取消')
    inboundDraft.value = result.data
    inboundOutbox.value = result.data.outbox || inboundOutbox.value
    ElMessage.success('草稿已取消')
  } catch (error) {
    ElMessage.error((error as Error).message)
  }
}

const summaryRowClassName = ({ row }: { row: WarehouseStockSummaryItem }): string => {
  if (row.is_below_reorder || row.is_below_safety) {
    return 'warning-row'
  }
  return ''
}

const alertRowClassName = ({ row }: { row: WarehouseAlertItem }): string => {
  if (row.severity === 'high') {
    return 'danger-row'
  }
  if (row.severity === 'medium') {
    return 'warning-row'
  }
  return ''
}

onMounted(async () => {
  try {
    await permissionStore.loadCurrentUser()
    await permissionStore.loadModuleActions('warehouse')
  } catch (error) {
    permissionStore.state.actions = []
    ElMessage.warning((error as Error).message || '权限加载失败，写操作已关闭')
  }
  await loadAll()
})
</script>

<style scoped>
.warehouse-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.alert-filter {
  margin-bottom: 12px;
}

.scope-alert {
  margin-bottom: 12px;
}

.inbound-meta-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.inbound-alert {
  margin-bottom: 12px;
}

.inbound-draft-panel {
  margin-top: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.inbound-draft-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.inbound-draft-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.inbound-draft-items {
  margin-top: 8px;
}

.inbound-outbox {
  margin-top: 8px;
}

:deep(.warning-row > td) {
  background-color: #fff7e6;
}

:deep(.danger-row > td) {
  background-color: #fff1f0;
}
</style>
