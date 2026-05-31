<template>
  <div class="sales-order-detail-page" data-testid="yisuan-1to1-sales-order-detail-shell">
    <el-card shadow="never">
      <template #header>
        <div class="header-row">
          <div>
            <h2>销售订单详情</h2>
            <p class="sub-title">衣算云 UI 1:1 对齐（只读态）</p>
          </div>
          <div class="header-actions">
            <el-button @click="goList">返回列表</el-button>
            <el-button type="warning" plain @click="openPopupOnly">数量矩阵 popup-only</el-button>
            <el-button type="primary" plain @click="goProductionPlan">查看生产计划</el-button>
          </div>
        </div>
      </template>

      <el-alert type="info" :closable="false" class="scope-alert">
        <template #title>当前页面用于 UI 对齐与信息回读，不触发订单写入或排产写入。</template>
      </el-alert>

      <section class="source-readback" data-testid="yisuan-1to1-ui-source-readback">
        <el-tag type="success">contract_source_readback_present=true</el-tag>
        <el-tag type="primary">covered_contract_ids=A002,A006</el-tag>
        <el-tag type="warning">A006_popup_only_boundary=true</el-tag>
        <el-tag type="danger">A006_blocked_unknown_claimed_as_confirmed=false</el-tag>
        <el-tag type="info">real_business_object_created=false</el-tag>
        <el-tag type="info">linked_calculation_enabled=false</el-tag>
      </section>

      <section class="header-summary" data-testid="yisuan-1to1-sales-order-header-summary">
        <el-descriptions :column="4" border>
          <el-descriptions-item label="订单号">{{ detail.orderNo }}</el-descriptions-item>
          <el-descriptions-item label="客户">{{ detail.customerName }}</el-descriptions-item>
          <el-descriptions-item label="款号">{{ detail.styleCode }}</el-descriptions-item>
          <el-descriptions-item label="业务员">{{ detail.owner }}</el-descriptions-item>
          <el-descriptions-item label="下单日期">{{ detail.orderDate }}</el-descriptions-item>
          <el-descriptions-item label="交期">{{ detail.deliveryDate }}</el-descriptions-item>
          <el-descriptions-item label="订单状态">
            <el-tag type="warning" effect="plain">{{ detail.orderStatus }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="生产状态">
            <el-tag type="success" effect="plain">{{ detail.productionStatus }}</el-tag>
          </el-descriptions-item>
        </el-descriptions>
      </section>
    </el-card>

    <el-card shadow="never" data-testid="yisuan-1to1-sales-order-quantity-matrix">
      <template #header>
        <div class="card-title">数量矩阵</div>
      </template>
      <el-table :data="matrixRows" border>
        <el-table-column prop="color" label="颜色" min-width="110" />
        <el-table-column prop="size" label="尺码" min-width="90" />
        <el-table-column prop="orderedQty" label="订单数量" min-width="120" />
        <el-table-column prop="allocatedQty" label="已分配" min-width="100" />
        <el-table-column prop="plannedQty" label="已排产" min-width="100" />
        <el-table-column label="差异" min-width="100">
          <template #default="{ row }">
            <span>{{ row.orderedQty - row.plannedQty }}</span>
          </template>
        </el-table-column>
      </el-table>
      <div class="matrix-delta">
        总订单数量：{{ matrixSummary.orderedQty }}，已排产：{{ matrixSummary.plannedQty }}，差异：{{ matrixSummary.deltaQty }}
      </div>
    </el-card>

    <el-card shadow="never" data-testid="yisuan-1to1-sales-order-progress-panel">
      <template #header>
        <div class="card-title">订单进度与异常</div>
      </template>
      <div class="progress-grid">
        <el-card v-for="stage in progressStages" :key="stage.name" shadow="never" class="progress-card">
          <div class="stage-head">
            <span>{{ stage.name }}</span>
            <el-tag :type="stage.type" effect="plain">{{ stage.status }}</el-tag>
          </div>
          <p>{{ stage.note }}</p>
        </el-card>
      </div>
      <el-alert
        v-if="detail.exceptionHint"
        class="exception-tip"
        type="warning"
        :closable="false"
        :title="detail.exceptionHint"
      />
    </el-card>

    <el-card shadow="never" class="contract-card">
      <template #header>
        <div class="contract-header">
          <span>合同字段与规则回读（A002/A006）</span>
          <el-tag type="danger" effect="plain">blocked / source_unknown / pending_confirmation / not_claimed</el-tag>
        </div>
      </template>

      <el-table :data="contractFieldRows" border stripe class="contract-field-table" data-testid="yisuan-contract-fields-observation">
        <el-table-column prop="field" label="字段" min-width="170" />
        <el-table-column prop="contract" label="合同来源" min-width="130" />
        <el-table-column prop="status" label="状态" min-width="170" />
        <el-table-column prop="evidence" label="页面策略" min-width="260" />
      </el-table>

      <div class="contract-block" data-testid="yisuan-contract-validation-rules">
        <h4>validation_rules</h4>
        <ul>
          <li v-for="rule in blockedUnknownRules" :key="`blocked-${rule}`">
            {{ rule }} => blocked / source_unknown / pending_confirmation / not_claimed
          </li>
        </ul>
      </div>

      <div class="contract-block" data-testid="yisuan-contract-status-rules">
        <h4>status_rules</h4>
        <div class="tag-row">
          <el-tag v-for="state in statusLabels" :key="`status-${state}`" type="info" effect="light">{{ state }}</el-tag>
          <el-tag type="warning" effect="light">popup_only</el-tag>
          <el-tag type="danger" effect="light">not_claimed</el-tag>
        </div>
      </div>

      <div class="contract-block" data-testid="yisuan-contract-readonly-readback-rules">
        <h4>readonly/readback rules</h4>
        <ul>
          <li v-for="rule in explicitNonClaimRules" :key="rule">{{ rule }}</li>
        </ul>
      </div>
    </el-card>

    <el-dialog
      v-model="popupOnlyVisible"
      width="640px"
      title="数量矩阵 popup-only（仅本地回写）"
      destroy-on-close
      append-to-body
    >
      <el-alert type="warning" :closable="false" class="popup-tip">
        <template #title>
          popup_only：仅允许弹窗内本地矩阵回写，禁止外推为主订单保存、订单创建或任意 confirmed 业务动作。
        </template>
      </el-alert>

      <el-form inline>
        <el-form-item label="颜色">
          <el-select v-model="popupDraft.color" style="width: 160px">
            <el-option label="米白" value="米白" />
            <el-option label="烟灰" value="烟灰" />
          </el-select>
        </el-form-item>
        <el-form-item label="尺码">
          <el-select v-model="popupDraft.size" style="width: 120px">
            <el-option label="S" value="S" />
            <el-option label="M" value="M" />
            <el-option label="L" value="L" />
            <el-option label="XL" value="XL" />
          </el-select>
        </el-form-item>
        <el-form-item label="数量">
          <el-input-number v-model="popupDraft.quantity" :min="0" :max="9999" />
        </el-form-item>
      </el-form>

      <p class="popup-readback">
        已冻结：A006_popup_only_boundary=true / popup_only_real_action_triggered=false / A006_blocked_unknown_fields_claimed_as_confirmed=false
      </p>

      <template #footer>
        <el-button @click="popupOnlyVisible = false">取消</el-button>
        <el-button type="primary" @click="applyPopupOnly">保存(S)（仅本地矩阵回写）</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

interface MatrixRow {
  color: string
  size: string
  orderedQty: number
  allocatedQty: number
  plannedQty: number
}

const router = useRouter()
const route = useRoute()

const detail = reactive({
  orderNo: String(Array.isArray(route.query.order_no) ? route.query.order_no[0] : route.query.order_no || 'SO-YS-260601'),
  customerName: String(
    Array.isArray(route.query.customer_name) ? route.query.customer_name[0] : route.query.customer_name || '青禾服饰',
  ),
  styleCode: String(Array.isArray(route.query.style_code) ? route.query.style_code[0] : route.query.style_code || 'JK-2410'),
  owner: '陈林',
  orderDate: '2026-05-25',
  deliveryDate: '2026-06-12',
  orderStatus: '待交期确认',
  productionStatus: '样前齐料',
  exceptionHint: '主面料到仓偏晚，需在 06-05 前完成二次确认。',
})

const matrixRows = reactive<MatrixRow[]>([
  { color: '米白', size: 'S', orderedQty: 200, allocatedQty: 160, plannedQty: 120 },
  { color: '米白', size: 'M', orderedQty: 300, allocatedQty: 260, plannedQty: 210 },
  { color: '烟灰', size: 'L', orderedQty: 420, allocatedQty: 330, plannedQty: 280 },
  { color: '烟灰', size: 'XL', orderedQty: 360, allocatedQty: 280, plannedQty: 240 },
])

const matrixSummary = computed(() => {
  const orderedQty = matrixRows.reduce((sum, row) => sum + row.orderedQty, 0)
  const plannedQty = matrixRows.reduce((sum, row) => sum + row.plannedQty, 0)
  return {
    orderedQty,
    plannedQty,
    deltaQty: orderedQty - plannedQty,
  }
})

const progressStages = [
  { name: '下单评审', status: '完成', note: '版单与工艺要求已确认。', type: 'success' as const },
  { name: '齐料跟进', status: '进行中', note: '面料 1 批预计 06-03 到仓。', type: 'warning' as const },
  { name: '排产锁定', status: '待执行', note: '需等待辅料校验后释放排产。', type: 'info' as const },
]

type ContractFieldRow = {
  field: string
  contract: string
  status: string
  evidence: string
}

const contractFieldRows: ContractFieldRow[] = [
  { field: '订单', contract: 'A006', status: 'VERIFIED', evidence: '主信息区展示' },
  { field: '客户', contract: 'A006', status: 'VERIFIED', evidence: '主信息区展示' },
  { field: '下单日期', contract: 'A006', status: 'VERIFIED', evidence: '主信息区展示' },
  { field: '汇率/币种', contract: 'A006', status: 'VERIFIED', evidence: '主信息区展示' },
  { field: '款号/颜色/尺码/单价', contract: 'A006', status: 'PARTIAL pending_confirmation', evidence: '仅 UI 壳层展示，不宣称 confirmed' },
  { field: '数量矩阵', contract: 'A002+A006', status: 'VERIFIED popup_only', evidence: '弹窗保存(S)仅本地回写' },
  { field: '主订单保存/提交审核', contract: 'A006', status: 'BLOCKED not_claimed', evidence: '显示 blocked，不提供真实动作' },
  { field: '生产/BOM/库存/财务联动', contract: 'A006', status: 'UNKNOWN source_unknown', evidence: '仅壳层标注，禁止升级为 confirmed' },
]

const blockedUnknownRules = [
  '主订单保存',
  '订单详情回读动作',
  '生产制单',
  '加工单',
  'BOM',
  '工序',
  '库存',
  '财务',
  '提交/审核/删除/作废',
  '生成生产/采购/加工单',
]

const statusLabels = ['VERIFIED', 'PARTIAL', 'UNKNOWN', 'NO-GO', 'BLOCKED']

const explicitNonClaimRules = [
  'UI 静态证据不等同业务算法 1:1',
  'mainOrderSaveClicked=false',
  'orderCreated=false',
  'orderNumberGenerated=false',
  'popup_only_real_action_triggered=false',
  'A006_blocked_unknown_fields_claimed_as_confirmed=false',
]

const popupOnlyVisible = ref(false)

const popupDraft = reactive({
  color: '米白',
  size: 'M',
  quantity: 2,
})

const openPopupOnly = (): void => {
  popupOnlyVisible.value = true
}

const applyPopupOnly = (): void => {
  const row = matrixRows.find((item) => item.color === popupDraft.color && item.size === popupDraft.size)
  if (row) row.plannedQty = popupDraft.quantity
  popupOnlyVisible.value = false
}

const goList = (): void => {
  router.push('/sales-inventory/sales-orders')
}

const goProductionPlan = (): void => {
  router.push({
    path: '/production/plans',
    query: {
      order_no: detail.orderNo,
      style_code: detail.styleCode,
      parity: 'sales-order-ui-parity',
    },
  })
}
</script>

<style scoped>
.sales-order-detail-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.header-row h2 {
  margin: 0;
  font-size: 18px;
  line-height: 1.4;
}

.sub-title {
  margin: 2px 0 0;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.scope-alert {
  margin-bottom: 12px;
}

.source-readback {
  margin-bottom: 10px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.header-summary {
  margin-top: 2px;
}

.card-title {
  font-weight: 600;
}

.matrix-delta {
  margin-top: 12px;
  color: var(--el-text-color-regular);
}

.progress-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.progress-card {
  border: 1px solid var(--el-border-color-lighter);
}

.stage-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.progress-card p {
  margin: 0;
  color: var(--el-text-color-secondary);
  font-size: 13px;
  line-height: 1.4;
}

.exception-tip {
  margin-top: 12px;
}

.contract-card {
  border: 1px solid var(--el-border-color-lighter);
}

.contract-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.contract-field-table {
  margin-bottom: 12px;
}

.contract-block {
  margin-top: 10px;
}

.contract-block h4 {
  margin: 0 0 8px;
  font-size: 13px;
}

.contract-block ul {
  margin: 0;
  padding-left: 18px;
  color: var(--el-text-color-secondary);
  line-height: 1.5;
}

.tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.popup-tip {
  margin-bottom: 12px;
}

.popup-readback {
  margin: 0;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 1.5;
}
</style>
