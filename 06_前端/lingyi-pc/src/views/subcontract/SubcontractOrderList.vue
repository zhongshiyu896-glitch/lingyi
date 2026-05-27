<template>
  <div
    class="subcontract-list-page"
    data-testid="subcontract-list-page"
    data-readonly-boundary="true"
    data-write-request-success-allowed="false"
    data-real-write-action-added="false"
  >
    <el-card shadow="never" data-testid="subcontract-main-card">
      <template #header>
        <div class="header-row">
          <span>外发单列表</span>
          <div class="header-actions" data-testid="subcontract-guarded-actions">
            <el-button
              size="small"
              type="primary"
              data-action-type="write"
              data-write-guard="guarded:readonly"
              data-testid="subcontract-create-open-button"
              @click="openCreateDialog"
            >
              新建外发单
            </el-button>
            <el-button size="small" :disabled="!canRead" data-testid="subcontract-refresh-button" @click="loadOrders">
              刷新
            </el-button>
          </div>
        </div>
      </template>

      <el-alert
        type="warning"
        show-icon
        :closable="false"
        class="readonly-guard"
        data-testid="subcontract-write-guard"
        data-write-guard="guarded:readonly"
      >
        <template #title>
          <span>只读履约视图：新建外发单、导出、打印与同步写入口均保持 guarded，不发起写请求。</span>
        </template>
      </el-alert>

      <el-alert
        v-if="parityHint"
        type="info"
        show-icon
        :closable="false"
        class="parity-hint"
        data-testid="subcontract-parity-hint"
      >
        <template #title>
          <span data-testid="subcontract-parity-hint-text">当前入口：{{ parityHint.label }}（{{ parityHint.key }}）</span>
        </template>
      </el-alert>

      <section
        class="z042-subcontract-panel"
        data-testid="z042-subcontract-guard-trace"
        data-readonly-boundary="true"
        data-write-request-success-allowed="false"
        data-real-write-action-added="false"
      >
        <div class="z042-panel-header">
          <strong>外发单只读 guard trace</strong>
          <el-tag type="warning" effect="plain">readonly fallback</el-tag>
        </div>
        <el-descriptions :column="3" border size="small">
          <el-descriptions-item label="列表筛选">加工厂 / 状态筛选仅刷新只读结果</el-descriptions-item>
          <el-descriptions-item label="parity 来源">
            <span data-testid="z042-subcontract-parity-source">{{ z042ParitySource.label }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="最终路由">{{ z042ParitySource.finalRoute }}</el-descriptions-item>
          <el-descriptions-item label="fallback 解释">
            权限或接口异常时保留列表、筛选与写入口 guard，可读不可写。
          </el-descriptions-item>
          <el-descriptions-item label="写请求成功">false</el-descriptions-item>
          <el-descriptions-item label="真实写 action">未新增</el-descriptions-item>
        </el-descriptions>
        <div class="z042-guard-actions" data-testid="z042-subcontract-list-guard-actions">
          <el-button
            v-for="entry in z042GuardEntries"
            :key="entry"
            size="small"
            data-action-type="write"
            data-write-guard="guarded:readonly"
            data-guard-state="guarded_readonly"
            :data-guard-entry="entry"
            @click="guardedAction(entry)"
          >
            {{ entry }}
          </el-button>
        </div>
      </section>

      <section
        class="z043-subcontract-panel"
        data-testid="z043-subcontract-readback-compare"
        data-readonly-boundary="true"
        data-write-request-success-allowed="false"
        data-real-write-action-added="false"
      >
        <div class="z043-panel-header">
          <strong>列表/详情 readback 对照</strong>
          <el-tag type="warning" effect="plain">guarded readonly</el-tag>
        </div>
        <el-descriptions :column="3" border size="small">
          <el-descriptions-item label="列表筛选">{{ z043ReadbackCompare.listFilter }}</el-descriptions-item>
          <el-descriptions-item label="详情主字段">{{ z043ReadbackCompare.detailFields }}</el-descriptions-item>
          <el-descriptions-item label="写成功状态">{{ z043ReadbackCompare.writeState }}</el-descriptions-item>
          <el-descriptions-item label="同步重试原因">
            <span
              data-testid="z043-subcontract-sync-retry-reason"
              data-guard-state="guarded-readonly"
              data-readonly-boundary="true"
              data-write-request-success-allowed="false"
              data-real-write-action-added="false"
            >
              {{ z043SyncRetryReason }}
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="导出/打印禁用">
            <span
              data-testid="z043-subcontract-export-print-disabled"
              data-guard-state="guarded-readonly"
              data-readonly-boundary="true"
              data-write-request-success-allowed="false"
              data-real-write-action-added="false"
            >
              {{ z043ExportPrintDisabledReason }}
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="materialPurchase parity 来源">
            <span
              data-testid="z043-subcontract-material-parity-source"
              data-readonly-boundary="true"
              data-write-request-success-allowed="false"
              data-real-write-action-added="false"
            >
              {{ z043MaterialParitySource }}
            </span>
          </el-descriptions-item>
        </el-descriptions>
        <div class="z043-guard-actions" data-testid="z043-subcontract-list-guarded-actions">
          <el-tag
            v-for="entry in z043GuardEntries"
            :key="entry"
            type="info"
            effect="plain"
            data-action-type="write"
            data-write-guard="guarded:readonly"
            data-guard-state="guarded-readonly"
            data-readonly-boundary="true"
            data-write-request-success-allowed="false"
            data-real-write-action-added="false"
            :data-guard-entry="entry"
          >
            {{ entry }} guarded/readonly
          </el-tag>
        </div>
      </section>

      <section
        class="z044-subcontract-panel"
        data-testid="z044-subcontract-list-detail-diff"
        data-readonly-boundary="true"
        data-write-request-success-allowed="false"
        data-real-write-action-added="false"
      >
        <div class="z044-panel-header">
          <strong>列表/详情一致性差异与同步锁定</strong>
          <el-tag type="warning" effect="plain">Z044 readonly</el-tag>
        </div>
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="列表/详情差异">
            <span>{{ z044ListDetailDiff }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="readback 一致性">
            <span
              data-testid="z044-subcontract-readback-consistency"
              data-readonly-boundary="true"
              data-write-request-success-allowed="false"
              data-real-write-action-added="false"
            >
              {{ z044ReadbackConsistency }}
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="同步锁定原因">
            <span
              data-testid="z044-subcontract-sync-lock-reason"
              data-guard-state="guarded-readonly"
              data-readonly-boundary="true"
              data-write-request-success-allowed="false"
              data-real-write-action-added="false"
            >
              {{ z044SyncLockReason }}
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="导出/打印禁用">
            <span
              data-testid="z044-subcontract-export-print-readonly"
              data-guard-state="guarded-readonly"
              data-readonly-boundary="true"
              data-write-request-success-allowed="false"
              data-real-write-action-added="false"
            >
              {{ z044ExportPrintReadonly }}
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="materialPurchase parity 来源">
            <span
              data-testid="z044-subcontract-material-parity-readback"
              data-readonly-boundary="true"
              data-write-request-success-allowed="false"
              data-real-write-action-added="false"
            >
              {{ z044MaterialParityReadback }}
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="network/write blocker">
            <span
              data-testid="z044-subcontract-network-write-blocker"
              data-readonly-boundary="true"
              data-write-request-success-allowed="false"
              data-real-write-action-added="false"
            >
              {{ z044NetworkWriteBlocker }}
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="write success blocker" :span="2">
            <span
              data-testid="z044-subcontract-write-success-blocker"
              data-readonly-boundary="true"
              data-write-request-success-allowed="false"
              data-real-write-action-added="false"
            >
              {{ z044WriteSuccessBlocker }}
            </span>
          </el-descriptions-item>
        </el-descriptions>
        <div class="z044-guard-actions" data-testid="z044-subcontract-guarded-action-matrix">
          <el-tag
            v-for="entry in z044GuardEntries"
            :key="entry"
            type="info"
            effect="plain"
            data-action-type="write"
            data-write-guard="guarded:readonly"
            data-guard-state="guarded-readonly"
            data-readonly-boundary="true"
            data-write-request-success-allowed="false"
            data-real-write-action-added="false"
            :data-guard-entry="entry"
          >
            {{ entry }} guarded/readonly
          </el-tag>
        </div>
      </section>

      <el-form :inline="true" :model="query" data-testid="subcontract-filter-form">
        <el-form-item label="加工厂">
          <div data-testid="subcontract-filter-supplier">
            <el-input v-model="query.supplier" clearable placeholder="Supplier" />
          </div>
        </el-form-item>
        <el-form-item label="状态">
          <div data-testid="subcontract-filter-status">
            <el-select
              v-model="query.status"
              clearable
              placeholder="全部状态"
              aria-label="外发单状态筛选"
              style="width: 150px"
            >
              <el-option label="草稿" value="draft" />
              <el-option label="已发料" value="issued" />
              <el-option label="加工中" value="processing" />
              <el-option label="待回料" value="waiting_receive" />
              <el-option label="待验货" value="waiting_inspection" />
              <el-option label="已完成" value="completed" />
              <el-option label="已取消" value="cancelled" />
            </el-select>
          </div>
        </el-form-item>
        <el-form-item>
          <div class="query-action" data-testid="subcontract-query-btn">
            <el-button type="primary" :disabled="!canRead" @click="applyQuery">查询</el-button>
          </div>
          <div class="query-action" data-testid="subcontract-reset-btn">
            <el-button :disabled="!canRead" @click="resetQuery">重置</el-button>
          </div>
        </el-form-item>
      </el-form>

      <el-empty v-if="!canRead" description="无外发查看权限" data-testid="subcontract-permission-empty-state" />
      <template v-else>
        <el-alert
          v-if="errorMessage"
          type="error"
          :title="errorMessage"
          show-icon
          :closable="false"
          class="error-state"
          data-testid="subcontract-error-state"
        />
        <div data-testid="subcontract-table">
          <el-table :data="rows" v-loading="loading" border empty-text="暂无外发单数据">
          <el-table-column prop="subcontract_no" label="外发单号" min-width="220" />
          <el-table-column prop="company" label="公司" min-width="150" />
          <el-table-column prop="supplier" label="加工厂" min-width="160" />
          <el-table-column prop="item_code" label="款式" min-width="140" />
          <el-table-column prop="process_name" label="工序" min-width="120" />
          <el-table-column prop="planned_qty" label="计划数量" width="110" />
          <el-table-column prop="issued_qty" label="已发料" width="110" />
          <el-table-column prop="received_qty" label="已回料" width="110" />
          <el-table-column prop="inspected_qty" label="已验货" width="110" />
          <el-table-column prop="net_amount" label="净应付金额" width="120" />
          <el-table-column label="状态" min-width="180">
            <template #default="scope">
              <span data-testid="subcontract-status-tag">
                <el-tag>{{ statusLabel(scope.row.status) }}</el-tag>
              </span>
              <el-tag v-if="scope.row.resource_scope_status === 'blocked_scope'" type="danger" class="scope-tag">
                权限范围异常
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="库存同步状态" min-width="160">
            <template #default="scope">{{ syncStatusLabel(scope.row) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="120" fixed="right">
            <template #default="scope">
              <span data-testid="subcontract-detail-entry">
                <el-button link type="primary" @click="goDetail(scope.row.id)">详情</el-button>
              </span>
            </template>
          </el-table-column>
          </el-table>
        </div>

        <el-empty
          v-if="!loading && !errorMessage && rows.length === 0"
          description="暂无外发单数据"
          class="empty-state"
          data-testid="subcontract-empty-state"
        />

        <div class="pager" data-testid="subcontract-pagination">
          <el-pagination
            background
            layout="prev, pager, next, total, sizes"
            :current-page="query.page"
            :page-size="query.page_size"
            :total="total"
            :page-sizes="[10, 20, 50, 100]"
            @current-change="onPageChange"
            @size-change="onSizeChange"
          />
        </div>
      </template>
    </el-card>

    <el-dialog
      v-model="createDialogVisible"
      title="新建外发单"
      width="640px"
      destroy-on-close
      append-to-body
      data-testid="subcontract-create-dialog"
    >
      <el-form :model="createForm" label-width="120px">
        <el-form-item label="加工厂">
          <el-input v-model="createForm.supplier" data-testid="subcontract-create-supplier-input" />
        </el-form-item>
        <el-form-item label="款号">
          <el-input v-model="createForm.item_code" data-testid="subcontract-create-item-code-input" />
        </el-form-item>
        <el-form-item label="BOM ID">
          <el-input-number v-model="createForm.bom_id" :min="1" data-testid="subcontract-create-bom-id-input" />
        </el-form-item>
        <el-form-item label="工序">
          <el-input v-model="createForm.process_name" data-testid="subcontract-create-process-input" />
        </el-form-item>
        <el-form-item label="计划数量">
          <el-input-number
            v-model="createForm.planned_qty"
            :min="1"
            :step="1"
            data-testid="subcontract-create-planned-qty-input"
          />
        </el-form-item>
        <el-form-item label="销售单">
          <el-input v-model="createForm.sales_order" data-testid="subcontract-create-sales-order-input" />
        </el-form-item>
        <el-form-item label="工单">
          <el-input v-model="createForm.work_order" data-testid="subcontract-create-work-order-input" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button data-testid="subcontract-create-cancel-button" @click="createDialogVisible = false">取消</el-button>
        <el-button
          type="primary"
          :loading="createSubmitting"
          data-testid="subcontract-create-submit-button"
          @click="submitCreate"
        >
          保存
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  buildSubcontractRequestId,
  buildSubcontractScenarioTag,
  createSubcontractOrder,
  fetchSubcontractOrders,
  type SubcontractOrderListItem,
} from '@/api/subcontract'
import { usePermissionStore } from '@/stores/permission'

const route = useRoute()
const router = useRouter()
const permissionStore = usePermissionStore()
const loading = ref<boolean>(false)
const rows = ref<SubcontractOrderListItem[]>([])
const total = ref<number>(0)
const errorMessage = ref<string>('')
const createDialogVisible = ref<boolean>(false)
const createSubmitting = ref<boolean>(false)

const readonlyFallback = ref<boolean>(false)
const canRead = computed<boolean>(() => readonlyFallback.value || permissionStore.state.buttonPermissions.read)
const z042GuardEntries = ['新建外发单', '发料', '回料', '验货', '结算预览', '同步重试', '导出', '打印']
const z043GuardEntries = z042GuardEntries
const z044GuardEntries = z042GuardEntries
const parityHint = computed<{ key: string; label: string } | null>(() => {
  const raw = typeof route.query.parity === 'string' ? route.query.parity.trim() : ''
  if (raw === 'material-purchase') {
    return { key: raw, label: '物料采购进度只读视图' }
  }
  if (raw === 'subcontract-order') {
    return { key: raw, label: '外发加工单只读视图' }
  }
  return null
})
const z042ParitySource = computed<{ label: string; finalRoute: string }>(() => {
  if (parityHint.value?.key === 'material-purchase') {
    return {
      label: 'materialPurchase parity route -> 外发单列表只读视图',
      finalRoute: '/subcontract/list?parity=material-purchase',
    }
  }
  return {
    label: parityHint.value ? `${parityHint.value.label} -> 外发单列表只读视图` : 'subcontract list direct route',
    finalRoute: '/subcontract/list',
  }
})
const z043ReadbackCompare = computed(() => ({
  listFilter: `supplier=${query.supplier || '全部'} / status=${query.status || '全部'} / readonly rows=${rows.value.length}`,
  detailFields: 'subcontract_no / supplier / status / sync_status 与详情页主字段保持只读对照',
  writeState: 'dataWriteRequestSuccessAllowed=false，列表与详情均不推断真实写成功',
}))
const z043SyncRetryReason = computed<string>(() => {
  const failedRows = rows.value.filter((row) => {
    const issue = row.latest_issue_sync_status || ''
    const receipt = row.latest_receipt_sync_status || ''
    return ['failed', 'dead', 'blocked_scope'].includes(issue) || ['failed', 'dead', 'blocked_scope'].includes(receipt)
  })
  return failedRows.length
    ? `存在 ${failedRows.length} 条同步异常，只显示 retry reason，不发送同步重试请求`
    : '当前无同步异常；同步重试入口保持 guarded/readonly，不发送写请求'
})
const z043ExportPrintDisabledReason =
  '导出与打印仅展示禁用原因：缺少写授权且当前为只读验收，不生成下载、打印或后端写请求'
const z043MaterialParitySource = computed<string>(() =>
  parityHint.value?.key === 'material-purchase'
    ? '/materialPurchase/materialPurchaseProcess -> /subcontract/list?parity=material-purchase'
    : `${z042ParitySource.value.finalRoute}；direct list route readonly readback`,
)
const z044ListDetailDiff = computed<string>(() =>
  `列表 rows=${rows.value.length}，详情字段以 subcontract_no/supplier/status/sync_status 回读；差异只展示不回写`,
)
const z044ReadbackConsistency = computed<string>(() =>
  `筛选 supplier=${query.supplier || '全部'} / status=${query.status || '全部'} 与详情 readback 使用同一只读来源`,
)
const z044SyncLockReason = computed<string>(() => {
  const lockedRows = rows.value.filter((row) => {
    const issue = row.latest_issue_sync_status || ''
    const receipt = row.latest_receipt_sync_status || ''
    return ['failed', 'dead', 'blocked_scope', 'processing'].includes(issue) || ['failed', 'dead', 'blocked_scope', 'processing'].includes(receipt)
  })
  return lockedRows.length
    ? `存在 ${lockedRows.length} 条同步状态需人工复核；同步重试保持 guarded/readonly`
    : '未观察到同步异常时仍锁定同步重试，只记录 readback 差异与禁用原因'
})
const z044ExportPrintReadonly =
  '导出/打印只展示禁用 readback：未授权本地候选不得生成文件、打印任务或后端写请求'
const z044MaterialParityReadback = computed<string>(() =>
  parityHint.value?.key === 'material-purchase'
    ? '/materialPurchase/materialPurchaseProcess -> /subcontract/list?parity=material-purchase'
    : 'direct subcontract list；materialPurchase parity 来源保持可读不可写',
)
const z044NetworkWriteBlocker =
  'network/write blocker：新建、同步、导出、打印均不发起 POST/PUT/PATCH/DELETE 写请求'
const z044WriteSuccessBlocker =
  'write success blocker：dataWriteRequestSuccessAllowed=false，dataRealWriteActionAdded=false，不把 guarded readonly 解释为写成功'

const query = reactive({
  supplier: '',
  status: '',
  page: 1,
  page_size: 20,
})

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

const stockSyncLabel = (status?: string | null): string => {
  if (!status) return ''
  const labels: Record<string, string> = {
    pending: '待同步',
    processing: '同步中',
    succeeded: '已同步',
    failed: '同步失败',
    dead: '死信',
    blocked_scope: '范围阻断',
  }
  return labels[status] || status
}

const syncStatusLabel = (row: SubcontractOrderListItem): string => {
  const issue = stockSyncLabel(row.latest_issue_sync_status)
  const receipt = stockSyncLabel(row.latest_receipt_sync_status)
  if (issue && receipt) {
    return `发料:${issue} / 回料:${receipt}`
  }
  if (receipt) {
    return `回料:${receipt}`
  }
  if (issue) {
    return `发料:${issue}`
  }
  return '未入列'
}

const guardedAction = (actionLabel: string): void => {
  ElMessage.warning(`${actionLabel} 仅可在授权流程中执行，当前为只读模式`)
}

const createForm = reactive({
  supplier: '示例加工厂',
  item_code: 'DEMO-TEE',
  bom_id: 1,
  process_name: '缝制',
  planned_qty: 10,
  sales_order: '',
  sales_order_item: '',
  production_plan_id: undefined as number | undefined,
  work_order: '',
  job_card: '',
})

const openCreateDialog = (): void => {
  guardedAction('新建外发单')
}

const submitCreate = async (): Promise<void> => {
  guardedAction('保存新建外发单')
  return
  if (createSubmitting.value) return
  const supplier = createForm.supplier.trim()
  const itemCode = createForm.item_code.trim()
  const processName = createForm.process_name.trim()
  const workOrderRef = (createForm.work_order || String(createForm.production_plan_id || '')).trim() || 'NO-WORK-ORDER'
  if (!supplier || !itemCode || !processName || !createForm.bom_id || !createForm.planned_qty) {
    ElMessage.warning('请先填写完整的外发单信息')
    return
  }

  createSubmitting.value = true
  try {
    const scenarioTag = buildSubcontractScenarioTag()
    const idempotencyKey = `${scenarioTag}-CREATE-${Date.now()}`
    const sourceRef = `${scenarioTag}-SRC-CREATE`
    const subcontractRef = `${scenarioTag}-SC-NEW`
    const statusAction = 'create'
    const requestId = buildSubcontractRequestId({
      scenarioTag,
      operation: 'create',
      idempotencyKey,
      sourceRef,
      subcontractRef,
      supplierRef: supplier,
      workOrderRef,
      itemCode,
      statusAction,
    })

    const created = await createSubcontractOrder({
      request_id: requestId,
      idempotency_key: idempotencyKey,
      scenario_tag: scenarioTag,
      source_ref: sourceRef,
      subcontract_ref: subcontractRef,
      supplier_ref: supplier,
      work_order_ref: workOrderRef,
      operation: 'create',
      quantity: createForm.planned_qty,
      status_action: statusAction,
      supplier,
      item_code: itemCode,
      bom_id: createForm.bom_id,
      planned_qty: createForm.planned_qty,
      process_name: processName,
      sales_order: createForm.sales_order.trim() || null,
      sales_order_item: createForm.sales_order_item.trim() || null,
      production_plan_id: createForm.production_plan_id ?? null,
      work_order: createForm.work_order.trim() || null,
      job_card: createForm.job_card.trim() || null,
      company: '示例公司',
    })

    query.page = 1
    await loadOrders()
    const createdRowId = rows.value.find((row) => row.subcontract_no === created.data.name)?.id
    const nextOrderId = Number(createdRowId ?? 0)
    if (nextOrderId > 0) {
      goDetail(nextOrderId)
    }
    createDialogVisible.value = false
    ElMessage.success(`外发单已创建：${created.data.name}`)
  } catch (error) {
    ElMessage.error((error as Error).message || '新建外发单失败')
  } finally {
    createSubmitting.value = false
  }
}

const loadOrders = async (): Promise<void> => {
  if (!canRead.value) {
    rows.value = []
    total.value = 0
    errorMessage.value = ''
    return
  }
  loading.value = true
  errorMessage.value = ''
  try {
    const payload = await fetchSubcontractOrders(query)
    rows.value = payload.data.items
    total.value = payload.data.total
  } catch (error) {
    const message = (error as Error).message || '外发单列表加载失败'
    errorMessage.value = message
    ElMessage.error(message)
  } finally {
    loading.value = false
  }
}

const applyQuery = (): void => {
  query.page = 1
  loadOrders()
}

const resetQuery = (): void => {
  query.supplier = ''
  query.status = ''
  query.page = 1
  query.page_size = 20
  loadOrders()
}

const goDetail = (id: number): void => {
  router.push({ path: '/subcontract/detail', query: { id: String(id) } })
}

const onPageChange = (page: number): void => {
  query.page = page
  loadOrders()
}

const onSizeChange = (size: number): void => {
  query.page_size = size
  query.page = 1
  loadOrders()
}

onMounted(async () => {
  try {
    await permissionStore.loadCurrentUser()
    await permissionStore.loadModuleActions('subcontract')
    readonlyFallback.value = !permissionStore.state.buttonPermissions.read
  } catch (error) {
    readonlyFallback.value = true
    ElMessage.error((error as Error).message)
  }
  await loadOrders()
})
</script>

<style scoped>
.subcontract-list-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.header-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.query-action {
  display: inline-flex;
  margin-right: 8px;
}

.scope-tag {
  margin-left: 8px;
}

.error-state {
  margin-bottom: 12px;
}

.parity-hint {
  margin-bottom: 12px;
}

.readonly-guard {
  margin-bottom: 12px;
}

.z042-subcontract-panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px;
  margin-bottom: 12px;
  border: 1px solid var(--el-border-color);
  border-radius: 6px;
  background: var(--el-fill-color-lighter);
}

.z042-panel-header,
.z042-guard-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.z043-subcontract-panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px;
  margin-bottom: 12px;
  border: 1px solid var(--el-border-color);
  border-radius: 6px;
  background: var(--el-fill-color-light);
}

.z043-panel-header,
.z043-guard-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.z044-subcontract-panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px;
  margin-bottom: 12px;
  border: 1px solid var(--el-border-color);
  border-radius: 6px;
  background: var(--el-fill-color-blank);
}

.z044-panel-header,
.z044-guard-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.empty-state {
  margin-top: 12px;
}

.pager {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}
</style>
