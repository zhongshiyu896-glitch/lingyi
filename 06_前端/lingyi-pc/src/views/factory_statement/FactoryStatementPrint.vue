<template>
  <div class="factory-statement-print-page" v-loading="loading">
    <div class="print-toolbar no-print">
      <el-button @click="goBack">返回详情</el-button>
      <el-button type="primary" :disabled="!detail" @click="printNow">打印</el-button>
    </div>

    <el-skeleton v-if="!permissionReady" :rows="4" animated />
    <el-empty v-else-if="!canRead" description="无加工厂对账单查看权限" />
    <el-empty v-else-if="missingStatementId" description="请从加工厂对账单详情页进入打印页" />
    <el-empty v-else-if="!detail && !loading" description="未找到对账单数据" />

    <div v-else-if="detail" class="print-sheet">
      <header class="print-header">
        <h1>领意服装管理系统</h1>
        <h2>加工厂对账单</h2>
      </header>

      <section class="summary-grid">
        <div><span>对账单号：</span>{{ detail.statement_no }}</div>
        <div><span>公司：</span>{{ detail.company }}</div>
        <div><span>供应商：</span>{{ detail.supplier }}</div>
        <div><span>期间：</span>{{ detail.from_date }} ~ {{ detail.to_date }}</div>
        <div><span>状态：</span>{{ statementStatusLabel(detail.statement_status) }}</div>
        <div><span>应付草稿同步：</span>{{ outboxStatusLabel(detail.payable_outbox_status) }}</div>
        <div><span>ERP 发票草稿：</span>{{ detail.purchase_invoice_name || '-' }}</div>
        <div><span>加工费：</span>{{ showText(detail.gross_amount) }}</div>
        <div><span>扣款：</span>{{ showText(detail.deduction_amount) }}</div>
        <div><span>实付金额：</span>{{ showText(detail.net_amount) }}</div>
      </section>

      <section class="print-section">
        <h3>对账明细</h3>
        <table class="print-table">
          <thead>
            <tr>
              <th>验货单号</th>
              <th>外发单号</th>
              <th>合格数量</th>
              <th>次品数量</th>
              <th>次品率</th>
              <th>加工费</th>
              <th>扣款</th>
              <th>实付</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in items" :key="item.id">
              <td>{{ item.inspection_no || '-' }}</td>
              <td>{{ item.subcontract_no || item.subcontract_id }}</td>
              <td>{{ showText(item.accepted_qty) }}</td>
              <td>{{ showText(item.rejected_qty) }}</td>
              <td>{{ showText(item.rejected_rate) }}</td>
              <td>{{ showText(item.gross_amount) }}</td>
              <td>{{ showText(item.deduction_amount) }}</td>
              <td>{{ showText(item.net_amount) }}</td>
            </tr>
            <tr v-if="items.length === 0">
              <td colspan="8" class="empty-row">暂无明细</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section class="print-section">
        <h3>操作日志</h3>
        <table class="print-table">
          <thead>
            <tr>
              <th>动作</th>
              <th>原状态</th>
              <th>新状态</th>
              <th>操作人</th>
              <th>备注</th>
              <th>时间</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(log, index) in logs" :key="`${log.action}-${index}`">
              <td>{{ log.action }}</td>
              <td>{{ log.from_status || '-' }}</td>
              <td>{{ log.to_status || '-' }}</td>
              <td>{{ log.operator }}</td>
              <td>{{ log.remark || '-' }}</td>
              <td>{{ log.operated_at }}</td>
            </tr>
            <tr v-if="logs.length === 0">
              <td colspan="6" class="empty-row">暂无日志</td>
            </tr>
          </tbody>
        </table>
      </section>

      <footer class="print-footer">
        <div>制表时间：{{ generatedAt }}</div>
        <div>打印人：{{ printUser }}</div>
      </footer>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import {
  fetchFactoryStatementDetail,
  type FactoryStatementDetailData,
  type FactoryStatementDetailItem,
  type FactoryStatementLogItem,
} from '@/api/factory_statement'
import { usePermissionStore } from '@/stores/permission'

const route = useRoute()
const router = useRouter()
const permissionStore = usePermissionStore()

const loading = ref<boolean>(false)
const detail = ref<FactoryStatementDetailData | null>(null)
const items = ref<FactoryStatementDetailItem[]>([])
const logs = ref<FactoryStatementLogItem[]>([])
const generatedAt = ref<string>('')
const missingStatementId = ref<boolean>(false)
const permissionReady = ref<boolean>(false)

const canRead = computed<boolean>(() => permissionStore.state.buttonPermissions.factory_statement_read)
const printUser = computed<string>(() => permissionStore.state.username || '-')
const statementId = computed<number>(() => Number(route.query.id || '0'))
const hasValidStatementId = computed<boolean>(() => Number.isInteger(statementId.value) && statementId.value > 0)

const showText = (value: string | number | null | undefined): string => {
  if (value === null || value === undefined || value === '') {
    return '-'
  }
  return String(value)
}

const statementStatusLabel = (status: string | null | undefined): string => {
  if (status === 'draft') {
    return '草稿'
  }
  if (status === 'confirmed') {
    return '已确认'
  }
  if (status === 'cancelled') {
    return '已取消'
  }
  if (status === 'payable_draft_created') {
    return '应付草稿已生成'
  }
  return status || '-'
}

const outboxStatusLabel = (status: string | null | undefined): string => {
  if (status === 'pending') {
    return '待同步'
  }
  if (status === 'processing') {
    return '同步中'
  }
  if (status === 'succeeded') {
    return '已生成草稿'
  }
  if (status === 'failed') {
    return '同步失败'
  }
  if (status === 'dead') {
    return '同步死信'
  }
  return '-'
}

const loadDetail = async (): Promise<void> => {
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
    generatedAt.value = new Date().toLocaleString()
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    loading.value = false
  }
}

const goBack = (): void => {
  if (!statementId.value) {
    router.push({ path: '/factory-statements/list' })
    return
  }
  router.push({ path: '/factory-statements/detail', query: { id: String(statementId.value) } })
}

const printNow = (): void => {
  if (!detail.value) {
    ElMessage.warning('暂无可打印数据')
    return
  }
  window.print()
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
.factory-statement-print-page {
  max-width: 1100px;
  margin: 0 auto;
  padding: 16px;
}

.print-toolbar {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.print-sheet {
  background: #fff;
  border: 1px solid #e4e7ed;
  padding: 20px;
}

.print-header {
  text-align: center;
  margin-bottom: 16px;
}

.print-header h1 {
  margin: 0;
  font-size: 20px;
}

.print-header h2 {
  margin: 8px 0 0;
  font-size: 18px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px 12px;
  margin-bottom: 16px;
}

.summary-grid span {
  font-weight: 600;
}

.print-section {
  margin-top: 16px;
}

.print-section h3 {
  margin: 0 0 8px;
  font-size: 15px;
}

.print-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.print-table th,
.print-table td {
  border: 1px solid #dcdfe6;
  padding: 6px;
  text-align: left;
}

.empty-row {
  text-align: center;
}

.print-footer {
  margin-top: 16px;
  display: flex;
  justify-content: space-between;
  font-size: 12px;
}

@media print {
  .no-print {
    display: none !important;
  }

  .factory-statement-print-page {
    max-width: none;
    margin: 0;
    padding: 0;
  }

  .print-sheet {
    border: none;
    padding: 0;
  }
}
</style>
