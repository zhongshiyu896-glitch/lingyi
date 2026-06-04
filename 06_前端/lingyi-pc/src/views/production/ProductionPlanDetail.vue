<template>
  <div class="production-plan-detail-page" data-testid="production-plan-detail-page">
    <el-card shadow="never" v-loading="loading" data-testid="production-plan-detail-main-card">
      <template #header>
        <div class="header-row" data-testid="production-plan-detail-header">
          <span data-testid="production-plan-detail-title">生产计划详情</span>
          <el-button data-testid="production-plan-detail-back" @click="goBack">返回</el-button>
        </div>
      </template>

      <el-skeleton v-if="!permissionReady" :rows="4" animated data-testid="production-plan-detail-loading" />
      <el-empty
        v-else-if="!canRead"
        description="无生产计划查看权限"
        data-testid="production-plan-detail-permission-state"
      />

      <template v-else>
        <el-descriptions v-if="detail" :column="3" border data-testid="production-plan-detail-main-fields">
          <el-descriptions-item label="计划单号">
            <span data-testid="production-plan-detail-field-plan-no">{{ detail.plan_no }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag data-testid="production-plan-detail-status-tag">{{ statusLabel(detail.status) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="公司">
            <span data-testid="production-plan-detail-field-company">{{ detail.company }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="销售单">{{ detail.sales_order }}</el-descriptions-item>
          <el-descriptions-item label="销售单行">{{ detail.sales_order_item }}</el-descriptions-item>
          <el-descriptions-item label="客户">{{ detail.customer || '-' }}</el-descriptions-item>
          <el-descriptions-item label="款式">
            <span data-testid="production-plan-detail-field-item-code">{{ detail.item_code }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="BOM ID">{{ detail.bom_id }}</el-descriptions-item>
          <el-descriptions-item label="BOM 版本">{{ detail.bom_version || '-' }}</el-descriptions-item>
          <el-descriptions-item label="计划数量">{{ detail.planned_qty }}</el-descriptions-item>
          <el-descriptions-item label="计划开工日">{{ detail.planned_start_date || '-' }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ detail.created_at }}</el-descriptions-item>
        </el-descriptions>
        <el-alert
          v-else-if="loadError"
          type="error"
          :closable="false"
          show-icon
          :title="loadError"
          data-testid="production-plan-detail-error-state"
        />
        <el-empty v-else description="暂无生产计划详情数据" data-testid="production-plan-detail-empty-state" />
      </template>
    </el-card>

    <el-alert
      v-if="guardedFeedback"
      type="warning"
      :closable="false"
      show-icon
      :title="guardedFeedback"
      data-testid="production-plan-detail-guarded-feedback"
    />

    <el-card v-if="canRead && detail" shadow="never" data-testid="production-plan-detail-write-entry-status">
      <template #header><span>只读边界</span></template>
      <el-alert
        type="warning"
        :closable="false"
        show-icon
        :title="writeEntryFrozenMessage"
        data-readonly-mode="true"
        data-write-guard="readonly:production-plan-detail"
        data-testid="production-plan-detail-permission-or-disabled-state"
      />
      <el-alert
        type="info"
        :closable="false"
        show-icon
        title="本页仅用于生产计划详情只读核验；物料检查、Work Order 创建、工序卡同步、outbox、worker 与 ERPNext production 入口均不在本切片中。"
        data-testid="production-plan-detail-readonly-state"
      />
    </el-card>

    <el-card v-if="canRead && detail" shadow="never" data-testid="production-plan-detail-readback-summary-card">
      <template #header>
        <div class="header-row">
          <span>计划摘要 / 数量矩阵</span>
          <el-tag type="warning">readonly snapshot</el-tag>
        </div>
      </template>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="当前入口">{{ parityRouteLabel(parityTag) }}</el-descriptions-item>
        <el-descriptions-item label="计划状态">{{ statusLabel(detail.status) }}</el-descriptions-item>
        <el-descriptions-item label="计划数量">{{ detail.planned_qty }}</el-descriptions-item>
        <el-descriptions-item label="数量矩阵摘要">{{ quantityMatrixSummary }}</el-descriptions-item>
        <el-descriptions-item label="工序卡应生产总数">{{ expectedQtySummary }}</el-descriptions-item>
        <el-descriptions-item label="工序卡已完成总数">{{ completedQtySummary }}</el-descriptions-item>
        <el-descriptions-item label="物料缺口总数">{{ materialShortageSummary }}</el-descriptions-item>
        <el-descriptions-item label="只读 guard">create-work-order / sync-job-cards disabled</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <el-card v-if="canRead && detail" shadow="never" data-testid="production-plan-detail-work-order-mapping">
      <template #header><span>Work Order 映射</span></template>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="Work Order">
          <span data-testid="production-plan-detail-work-order">{{ currentWorkOrder || '-' }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="同步状态">{{ workOrderSyncStatusLabel }}</el-descriptions-item>
        <el-descriptions-item label="ERP Docstatus">{{ detail.erpnext_docstatus ?? '-' }}</el-descriptions-item>
        <el-descriptions-item label="ERP 状态">{{ detail.erpnext_status || '-' }}</el-descriptions-item>
        <el-descriptions-item label="最新错误码">{{ detail.latest_work_order_outbox?.error_code || '-' }}</el-descriptions-item>
        <el-descriptions-item label="最近同步时间">{{ detail.last_synced_at || '-' }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <el-card v-if="canRead && detail" shadow="never" data-testid="production-plan-detail-material-snapshot-card">
      <template #header><span>物料检查快照</span></template>
      <el-alert
        type="info"
        :closable="false"
        show-icon
        title="当前为本地只读快照；未接库存实时链路前仅作观察，不触发任何物料检查写入。"
      />
      <el-table
        :data="detail.material_snapshots || []"
        border
        style="margin-top: 12px"
        empty-text="暂无物料检查快照"
        data-testid="production-plan-detail-material-snapshot-table"
      >
        <el-table-column prop="material_item_code" label="物料编码" min-width="160" />
        <el-table-column prop="qty_per_piece" label="单件用量" width="110" />
        <el-table-column prop="loss_rate" label="损耗率" width="100" />
        <el-table-column prop="required_qty" label="需求数量" width="110" />
        <el-table-column prop="warehouse" label="仓库" min-width="140" />
        <el-table-column prop="available_qty" label="可用库存" width="110" />
        <el-table-column prop="shortage_qty" label="缺口数量" width="110" />
        <el-table-column label="检查时间" min-width="170">
          <template #default="scope">{{ scope.row.checked_at || '-' }}</template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card v-if="canRead && detail" shadow="never" data-testid="production-plan-detail-job-card-mapping">
      <template #header><span>Job Card 映射</span></template>
      <el-table
        :data="detail.job_cards || []"
        border
        empty-text="暂无 Job Card 映射数据"
        data-testid="production-plan-detail-job-card-table"
      >
        <el-table-column prop="job_card" label="Job Card" min-width="180" />
        <el-table-column label="Work Order" min-width="180">
          <template #default>{{ currentWorkOrder || '-' }}</template>
        </el-table-column>
        <el-table-column prop="operation" label="工序" min-width="150" />
        <el-table-column prop="operation_sequence" label="工序序号" width="100" />
        <el-table-column prop="expected_qty" label="应生产数量" width="120" />
        <el-table-column prop="completed_qty" label="已完成数量" width="120" />
        <el-table-column prop="erpnext_status" label="ERP 状态" min-width="120" />
        <el-table-column prop="synced_at" label="同步时间" min-width="180" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { fetchProductionPlanDetail, fetchProductionPlans, type ProductionPlanDetailData } from '@/api/production'
import { usePermissionStore } from '@/stores/permission'
import { useProductionPlanReadback } from './composables/useProductionPlanReadback'

const route = useRoute()
const router = useRouter()
const permissionStore = usePermissionStore()
const { parseQueryString, parityRouteLabel, statusLabel } = useProductionPlanReadback()

const detail = ref<ProductionPlanDetailData | null>(null)
const loadError = ref('')
const guardedFeedback = ref('')
const loading = ref(false)
const permissionReady = ref(false)
const fallbackPlanId = ref<number | null>(null)

const PRODUCTION_LOCAL_DETAIL_FROZEN_REASON =
  '受控写门禁：当前切片仅开放生产计划 list/detail 只读查询，work order push、outbox、worker 与 ERPNext production 链路保持冻结。'

const canRead = computed<boolean>(() => permissionStore.state.buttonPermissions.read)

const parsePositiveInteger = (value: unknown): number => {
  const raw = Array.isArray(value) ? value[0] : value
  const parsed = Number(raw || '0')
  return Number.isInteger(parsed) && parsed > 0 ? parsed : 0
}

const parseStringQuery = (value: unknown): string => parseQueryString(value)

const routePlanId = computed<number>(() => parsePositiveInteger(route.query.id))
const hasValidPlanId = computed<boolean>(() => routePlanId.value > 0)
const parityTag = computed<string>(() => parseStringQuery(route.query.parity))
const currentWorkOrder = computed<string>(
  () => detail.value?.work_order || detail.value?.latest_work_order_outbox?.erpnext_work_order || '',
)
const workOrderSyncStatusLabel = computed<string>(() =>
  syncStatusLabel(detail.value?.sync_status || detail.value?.latest_work_order_outbox?.status || null),
)
const writeEntryFrozenMessage = computed<string>(
  () =>
    detail.value?.write_entry_frozen_reason ||
    '当前生产计划详情处于只读验收模式；任何写入口均不在本切片内。',
)

const syncStatusLabel = (value?: string | null): string => {
  if (!value) return '-'
  const labels: Record<string, string> = {
    pending: '待同步',
    processing: '同步中',
    succeeded: '已同步',
    failed: '失败待重试',
    dead: '死信',
    blocked_scope: '范围阻断',
  }
  return labels[value] || value
}

const numericSum = (values: Array<string | number | null | undefined>): string =>
  values
    .reduce<number>((sum, value) => sum + Number(value || 0), 0)
    .toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 2 })

const expectedQtySummary = computed<string>(() => numericSum((detail.value?.job_cards || []).map((item) => item.expected_qty)))
const completedQtySummary = computed<string>(() =>
  numericSum((detail.value?.job_cards || []).map((item) => item.completed_qty)),
)
const materialShortageSummary = computed<string>(() =>
  numericSum((detail.value?.material_snapshots || []).map((item) => item.shortage_qty)),
)
const quantityMatrixSummary = computed<string>(() => {
  if (!detail.value) return '-'
  if (detail.value.job_cards.length) return `${detail.value.job_cards.length} 条工序卡回读`
  if (detail.value.material_snapshots.length) return `${detail.value.material_snapshots.length} 条物料快照回读`
  return '暂无数量矩阵，仅展示只读占位摘要'
})

const buildSyntheticDetail = (): ProductionPlanDetailData => {
  const today = new Date().toISOString()
  return {
    id: routePlanId.value || 900001,
    plan_no: parseStringQuery(route.query.plan_no) || 'PP-LOCAL-260601',
    company: parseStringQuery(route.query.company) || 'LY-LOCAL-TEST',
    sales_order: parseStringQuery(route.query.sales_order) || 'SO-LOCAL-260601',
    sales_order_item: 'SOI-LOCAL-260601',
    customer: parseStringQuery(route.query.customer) || '本地样例客户',
    item_code: parseStringQuery(route.query.item_code) || 'ITEM-A',
    bom_id: parsePositiveInteger(route.query.bom_id) || 101,
    bom_version: 'vlocal',
    planned_qty: parseStringQuery(route.query.planned_qty) || '180',
    planned_start_date: parseStringQuery(route.query.planned_start_date) || '2026-06-03',
    status: parseStringQuery(route.query.status) || 'planned',
    work_order: null,
    erpnext_docstatus: null,
    erpnext_status: null,
    sync_status: 'blocked_scope',
    last_synced_at: null,
    latest_work_order_outbox: null,
    write_entry_frozen: true,
    write_entry_frozen_reason: PRODUCTION_LOCAL_DETAIL_FROZEN_REASON,
    material_snapshots: [
      {
        material_item_code: 'MAT-A',
        warehouse: 'WIP Warehouse - LY',
        qty_per_piece: '1.500000',
        loss_rate: '0.100000',
        required_qty: '297.000000',
        available_qty: '0.000000',
        shortage_qty: '297.000000',
        checked_at: null,
      },
    ],
    job_cards: [],
    created_at: today,
    updated_at: today,
  }
}

const ensurePlanId = (): number => {
  const targetPlanId = hasValidPlanId.value ? routePlanId.value : fallbackPlanId.value || 0
  if (!targetPlanId || Number.isNaN(targetPlanId)) {
    throw new Error('无效的生产计划 ID')
  }
  return targetPlanId
}

const loadDetail = async (): Promise<void> => {
  if (!canRead.value) {
    detail.value = null
    loadError.value = ''
    guardedFeedback.value = ''
    return
  }

  loadError.value = ''
  loading.value = true
  try {
    if (parseStringQuery(route.query.synthetic) === '1') {
      detail.value = buildSyntheticDetail()
      guardedFeedback.value = '当前展示 synthetic detail，只用于 local-only 可用切片。'
      return
    }

    if (!hasValidPlanId.value) {
      const firstPlanResponse = await fetchProductionPlans({ page: 1, page_size: 1 })
      fallbackPlanId.value = firstPlanResponse.data.items[0]?.id || null
    } else {
      fallbackPlanId.value = routePlanId.value
    }

    if (!fallbackPlanId.value) {
      detail.value = buildSyntheticDetail()
      guardedFeedback.value = '未读取到本地生产计划记录，已回退到 synthetic detail。'
      return
    }

    const result = await fetchProductionPlanDetail(ensurePlanId())
    detail.value = result.data
    guardedFeedback.value = hasValidPlanId.value ? '' : '未提供计划 ID，已回退到首条本地生产计划详情。'
  } catch (error) {
    const message = (error as Error).message || '加载生产计划详情失败'
    detail.value = buildSyntheticDetail()
    guardedFeedback.value = `加载详情失败，已回退到 synthetic detail：${message}`
  } finally {
    loading.value = false
  }
}

const goBack = (): void => {
  router.push({
    path: '/production/plans',
    query: parityTag.value ? { parity: parityTag.value } : undefined,
  })
}

watch(
  () => route.fullPath,
  async () => {
    fallbackPlanId.value = null
    await loadDetail()
  },
)

onMounted(async () => {
  try {
    await permissionStore.loadCurrentUser()
    await permissionStore.loadModuleActions('production')
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    permissionReady.value = true
  }
  await loadDetail()
})
</script>

<style scoped>
.production-plan-detail-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
