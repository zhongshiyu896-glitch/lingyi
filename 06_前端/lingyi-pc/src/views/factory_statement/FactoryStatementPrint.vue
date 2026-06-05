<template>
  <div class="factory-statement-print-page" v-loading="loading" data-testid="factory-statement-print-page">
    <div class="print-toolbar no-print" data-testid="factory-statement-print-toolbar">
      <el-button data-testid="factory-statement-print-back-button" @click="goBack">返回详情</el-button>
      <el-button
        type="primary"
        data-testid="factory-statement-print-guarded-print-button"
        data-write-guard="guarded:readonly-print"
        disabled
      >
        打印
      </el-button>
      <el-button data-write-guard="guarded:readonly-print" disabled>
        确认
      </el-button>
      <el-button data-write-guard="guarded:readonly-print" disabled>
        取消
      </el-button>
      <el-button data-write-guard="guarded:readonly-print" disabled>
        导出
      </el-button>
    </div>
    <p
      class="readonly-tip no-print"
      data-testid="factory-statement-write-guard"
      data-action-type="write"
      data-write-guard="guarded:readonly-print"
      data-guard-state="disabled"
    >
      打印、导出、确认、取消与应付草稿入口保持只读 guard。
    </p>

    <el-skeleton v-if="!permissionReady" :rows="4" animated />
    <el-empty
      v-else-if="!canRead"
      description="无加工厂对账单查看权限"
      data-testid="factory-statement-print-no-permission-state"
    />
    <el-empty
      v-else-if="missingStatementId"
      description="请从加工厂对账单详情页进入打印页"
      data-testid="factory-statement-print-missing-id-state"
    />
    <el-alert
      v-else-if="loadError"
      :title="`打印预览数据加载失败：${loadError}`"
      type="error"
      show-icon
      :closable="false"
      data-testid="factory-statement-print-error-alert"
    />
    <el-empty
      v-else-if="!detail && !loading"
      description="未找到对账单数据"
      data-testid="factory-statement-print-empty-state"
    />

    <div v-else-if="detail" class="print-sheet" data-testid="factory-statement-print-sheet">
      <header class="print-header">
        <h1>领意服装管理系统</h1>
        <h2>加工厂对账单</h2>
      </header>

      <section class="summary-grid" data-testid="factory-statement-print-summary-grid">
        <div><span>对账单号：</span>{{ detail.statement_no }}</div>
        <div><span>公司：</span>{{ detail.company }}</div>
        <div><span>供应商：</span>{{ detail.supplier }}</div>
        <div><span>期间：</span>{{ detail.from_date }} ~ {{ detail.to_date }}</div>
        <div data-testid="factory-statement-print-status-text">
          <span>状态：</span>
          <el-tag type="info" size="small" data-testid="factory-statement-print-status-tag">
            {{ statementStatusLabel(detail.statement_status) }}
          </el-tag>
        </div>
        <div data-testid="factory-statement-print-outbox-status">
          <span>应付草稿同步：</span>
          <el-tag type="warning" size="small" data-testid="factory-statement-print-outbox-status-tag">
            {{ outboxStatusLabel(detail.payable_outbox_status) }}
          </el-tag>
        </div>
        <div><span>ERP 发票草稿：</span>{{ detail.purchase_invoice_name || '-' }}</div>
        <div><span>加工费：</span>{{ showText(detail.gross_amount) }}</div>
        <div><span>扣款：</span>{{ showText(detail.deduction_amount) }}</div>
        <div><span>实付金额：</span>{{ showText(detail.net_amount) }}</div>
      </section>

      <section class="print-kpi-strip" data-testid="factory-statement-print-kpi-strip">
        <article class="print-kpi-card">
          <span class="kpi-label">来源条数</span>
          <strong class="kpi-value">{{ showText(detail.source_count) }}</strong>
        </article>
        <article class="print-kpi-card">
          <span class="kpi-label">验货总数</span>
          <strong class="kpi-value">{{ showText(detail.inspected_qty) }}</strong>
        </article>
        <article class="print-kpi-card">
          <span class="kpi-label">次品总数</span>
          <strong class="kpi-value">{{ showText(detail.rejected_qty) }}</strong>
        </article>
        <article class="print-kpi-card">
          <span class="kpi-label">次品率</span>
          <strong class="kpi-value">{{ showText(detail.rejected_rate) }}</strong>
        </article>
      </section>

      <section class="readonly-summary-grid" data-testid="factory-statement-print-readonly-summary">
        <div><span>首个外发单：</span>{{ printSummary.primarySubcontractNo }}</div>
        <div><span>首个验货单：</span>{{ printSummary.primaryInspectionNo }}</div>
        <div><span>创建人：</span>{{ printSummary.createdBy }}</div>
        <div><span>最新动作：</span>{{ printSummary.latestAction }}</div>
        <div><span>最新操作时间：</span>{{ printSummary.latestOperatedAt }}</div>
        <div><span>应付发票草稿：</span>{{ printSummary.payableInvoice }}</div>
      </section>

      <FactoryStatementPayableStatusReadonly
        :summary="payableReadonlySummary"
        data-testid="factory-statement-print-payable-readonly-section"
      />

      <el-alert
        type="warning"
        :title="printGuardMessage"
        :closable="false"
        show-icon
        class="guarded-alert"
        data-testid="factory-statement-print-guarded-feedback"
      />
      <p class="readonly-tip" data-testid="factory-statement-print-permission-or-disabled-state">
        当前页面为只读打印预览模式，打印/导出/确认/取消/应付草稿动作已禁用。
      </p>

      <section class="print-section">
        <h3>对账明细</h3>
        <table class="print-table" data-testid="factory-statement-print-detail-table">
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
        <table class="print-table" data-testid="factory-statement-print-logs-table">
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

      <footer class="print-footer" data-testid="factory-statement-print-footer">
        <div>
          制表时间：
          <span data-testid="factory-statement-print-generated-at">{{ generatedAt }}</span>
        </div>
        <div>
          打印人：
          <span data-testid="factory-statement-print-user">{{ printUser }}</span>
        </div>
      </footer>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import {
  fetchFactoryStatementReadonlyDetail,
  type FactoryStatementReadonlyRecord,
} from '@/api/factory_statement_readonly'
import FactoryStatementPayableStatusReadonly from '@/views/factory_statement/components/FactoryStatementPayableStatusReadonly.vue'
import { useFactoryStatementPayableReadonly } from '@/views/factory_statement/composables/useFactoryStatementPayableReadonly'
import { useFactoryStatementReadonly } from '@/views/factory_statement/composables/useFactoryStatementReadonly'
import { usePermissionStore } from '@/stores/permission'

const route = useRoute()
const router = useRouter()
const permissionStore = usePermissionStore()

const loading = ref<boolean>(false)
const readonlyRecord = ref<FactoryStatementReadonlyRecord | null>(null)
const generatedAt = ref<string>('')
const missingStatementId = ref<boolean>(false)
const permissionReady = ref<boolean>(false)
const loadError = ref<string>('')

const parityValue = computed<string>(() => String(route.query.parity || '').trim().toLowerCase())
const isReadonlyParity = computed<boolean>(() => (
  parityValue.value === 'foundation-supplier' || parityValue.value === 'foundation-factory'
))
const preservedReadonlyQuery = computed<Record<string, string>>(() => {
  const query: Record<string, string> = {}
  if (parityValue.value) {
    query.parity = parityValue.value
  }
  return query
})
const canRead = computed<boolean>(() => isReadonlyParity.value || permissionStore.state.buttonPermissions.factory_statement_read)
const printUser = computed<string>(() => permissionStore.state.username || '-')
const statementId = computed<number>(() => Number(route.query.id || '0'))
const hasValidStatementId = computed<boolean>(() => Number.isInteger(statementId.value) && statementId.value > 0)
const detail = computed(() => readonlyRecord.value?.raw || null)
const items = computed(() => readonlyRecord.value?.items || [])
const logs = computed(() => readonlyRecord.value?.logs || [])
const {
  outboxStatusLabel,
  printGuardMessage,
  printSummary,
  showText,
  statementStatusLabel,
} = useFactoryStatementReadonly(readonlyRecord)
const { payableReadonlySummary } = useFactoryStatementPayableReadonly({
  recordSource: readonlyRecord,
  parity: parityValue,
  context: 'print',
})

const loadDetail = async (): Promise<void> => {
  loadError.value = ''
  if (!canRead.value) {
    readonlyRecord.value = null
    generatedAt.value = ''
    missingStatementId.value = false
    return
  }
  if (!hasValidStatementId.value) {
    readonlyRecord.value = null
    generatedAt.value = ''
    missingStatementId.value = true
    return
  }
  missingStatementId.value = false

  loading.value = true
  try {
    const result = await fetchFactoryStatementReadonlyDetail(statementId.value)
    const payload = result.data
    if (!payload) {
      readonlyRecord.value = null
      generatedAt.value = ''
      return
    }
    readonlyRecord.value = payload
    generatedAt.value = new Date().toLocaleString()
  } catch (error) {
    const message = (error as Error).message || '未知错误'
    loadError.value = message
    readonlyRecord.value = null
    generatedAt.value = ''
    ElMessage.error(message)
  } finally {
    loading.value = false
  }
}

const goBack = (): void => {
  if (!statementId.value) {
    router.push({ path: '/factory-statements/list', query: { ...preservedReadonlyQuery.value } })
    return
  }
  router.push({
    path: '/factory-statements/detail',
    query: {
      ...preservedReadonlyQuery.value,
      id: String(statementId.value),
    },
  })
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

.print-kpi-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
  margin-bottom: 12px;
}

.readonly-summary-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px 12px;
  margin-bottom: 12px;
}

.print-kpi-card {
  border: 1px solid #dbe3ef;
  border-radius: 6px;
  padding: 8px 10px;
  background: #f8fbff;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.kpi-label {
  color: #526071;
  font-size: 12px;
}

.kpi-value {
  color: #111827;
  font-size: 16px;
  line-height: 1.2;
}

.print-section {
  margin-top: 16px;
}

.guarded-alert {
  margin-top: 12px;
}

.readonly-tip {
  margin-top: 8px;
  color: var(--el-text-color-secondary);
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

  .print-kpi-card {
    background: #fff;
  }
}
</style>
