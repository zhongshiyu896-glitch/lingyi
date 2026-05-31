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
            <el-button type="primary" plain @click="goProductionPlan">查看生产计划</el-button>
          </div>
        </div>
      </template>

      <el-alert type="info" :closable="false" class="scope-alert">
        <template #title>当前页面用于 UI 对齐与信息回读，不触发订单写入或排产写入。</template>
      </el-alert>

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
  </div>
</template>

<script setup lang="ts">
import { computed, reactive } from 'vue'
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
</style>
