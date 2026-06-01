<template>
  <main class="yisuan-dashboard-shell" data-testid="yisuan-1to1-dashboard-shell">
    <section class="dashboard-header">
      <div>
        <h1>经营总览</h1>
        <p>工作台 KPI、流程状态与异常面板（UI 1:1 对齐）</p>
      </div>
      <div class="header-actions">
        <el-select v-model="query.material" clearable placeholder="物料">
          <el-option v-for="item in materialOptions" :key="item" :label="item" :value="item" />
        </el-select>
        <el-select v-model="query.warehouse" clearable placeholder="仓库">
          <el-option v-for="item in warehouseOptions" :key="item" :label="item" :value="item" />
        </el-select>
        <el-select v-model="query.flowType" clearable placeholder="流程类型">
          <el-option v-for="item in flowTypeOptions" :key="item" :label="item" :value="item" />
        </el-select>
      </div>
    </section>

    <section class="readback-summary" data-testid="cand006-dashboard-readback-summary">
      <header>
        <h2>本地对象状态汇总（readback-only）</h2>
        <el-tag effect="plain" type="info">scenario_tag={{ readbackScenarioTag }}</el-tag>
      </header>
      <el-alert
        v-if="readbackError"
        type="warning"
        :closable="false"
        :title="readbackError"
        data-testid="cand006-dashboard-readback-error"
      />
      <div v-else class="summary-grid">
        <article v-for="item in readbackSummaryModules" :key="item.module_key" class="summary-card">
          <span class="summary-label">{{ item.module_label }}</span>
          <strong class="summary-value">{{ item.record_count }}</strong>
          <small class="summary-note">{{ item.source_endpoint }}</small>
        </article>
      </div>
      <div class="summary-checkpoint-row">
        <span>dashboard_overview_readback_summary_success={{ dashboardOverviewReadbackSummarySuccess ? 'true' : 'false' }}</span>
        <span>workspace_redirect_readback_success={{ workspaceRedirectReadbackSuccess ? 'true' : 'false' }}</span>
        <span>workspace_final_path={{ workspaceFinalPath }}</span>
        <span>write_requests_observed_count={{ readbackWriteRequestsObservedCount }}</span>
      </div>
    </section>

    <section class="kpi-strip" data-testid="yisuan-1to1-dashboard-kpi-strip">
      <article v-for="item in kpis" :key="item.label" class="kpi-item">
        <span class="label">{{ item.label }}</span>
        <strong class="value">{{ item.value }}</strong>
        <small class="trend">{{ item.trend }}</small>
      </article>
    </section>

    <section class="flow-panel" data-testid="yisuan-1to1-dashboard-flow-panel">
      <header>
        <h2>流程状态</h2>
        <el-tag effect="plain">只读视图</el-tag>
      </header>
      <div class="flow-grid">
        <article v-for="node in filteredFlowNodes" :key="node.name" class="flow-card">
          <h3>{{ node.name }}</h3>
          <p>待处理：{{ node.pending }}</p>
          <p>超时：{{ node.overdue }}</p>
          <p>负责人：{{ node.owner }}</p>
        </article>
      </div>
    </section>

    <section class="dashboard-body">
      <article class="exception-list" data-testid="yisuan-1to1-dashboard-exception-list">
        <header>
          <h2>异常列表</h2>
          <el-input
            v-model="exceptionKeyword"
            clearable
            placeholder="按异常关键词过滤"
            style="max-width: 220px"
          />
        </header>
        <el-table :data="filteredExceptions" border empty-text="暂无异常">
          <el-table-column prop="code" label="编号" width="120" />
          <el-table-column prop="module" label="模块" width="140" />
          <el-table-column prop="desc" label="异常描述" min-width="220" />
          <el-table-column prop="severity" label="级别" width="120" />
          <el-table-column prop="updatedAt" label="更新时间" width="160" />
        </el-table>
      </article>

      <article class="quick-actions" data-testid="yisuan-1to1-dashboard-quick-actions">
        <h2>快捷操作</h2>
        <button type="button" @click="go('/home')">返回首页</button>
        <button type="button" @click="go('/sales-inventory/sales-orders')">查看大货订单</button>
        <button type="button" @click="go('/subcontract/list?parity=material-purchase')">查看采购外协</button>
        <button type="button" @click="go('/sales-inventory/stock-ledger')">查看库存流水</button>
        <button type="button" @click="go('/warehouse')">查看仓库看板</button>
      </article>
    </section>

    <section class="source-readback" data-testid="yisuan-1to1-ui-source-readback">
      <h2>UI Source Readback</h2>
      <ul>
        <li v-for="item in sourceReadback" :key="item">{{ item }}</li>
      </ul>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { request } from '@/api/request'

interface KPIItem {
  label: string
  value: string
  trend: string
}

interface FlowNode {
  name: string
  pending: number
  overdue: number
  owner: string
  flowType: string
}

interface ExceptionItem {
  code: string
  module: string
  desc: string
  severity: string
  updatedAt: string
}

const router = useRouter()
const route = useRoute()

const query = reactive({
  material: '',
  warehouse: '',
  flowType: '',
})

const materialOptions = ['主面料', '辅料', '包材', '样衣']
const warehouseOptions = ['主仓', '裁片仓', '成品仓', '外协仓']
const flowTypeOptions = ['采购', '外协', '生产', '库存']

const kpis: KPIItem[] = [
  { label: '订单履约率', value: '96.2%', trend: '周环比 +1.4%' },
  { label: '库存周转天数', value: '28', trend: '周环比 -2' },
  { label: '采购准交率', value: '94.8%', trend: '周环比 +0.8%' },
  { label: '异常关闭率', value: '89.3%', trend: '周环比 +3.1%' },
]

const flowNodes: FlowNode[] = [
  { name: '需求分发', pending: 4, overdue: 1, owner: '运营组', flowType: '生产' },
  { name: '采购下发', pending: 7, overdue: 2, owner: '采购组', flowType: '采购' },
  { name: '外协排产', pending: 5, overdue: 1, owner: '外协组', flowType: '外协' },
  { name: '仓内调拨', pending: 3, overdue: 0, owner: '仓储组', flowType: '库存' },
]

const exceptions = ref<ExceptionItem[]>([
  { code: 'EX-2401', module: '库存', desc: '主仓与外协仓账面差异待复核', severity: '中', updatedAt: '2026-05-31 10:12' },
  { code: 'EX-2402', module: '采购', desc: '辅料交期偏差超过 2 天', severity: '高', updatedAt: '2026-05-31 09:44' },
  { code: 'EX-2403', module: '生产', desc: '工序等待物料补齐', severity: '中', updatedAt: '2026-05-30 18:26' },
  { code: 'EX-2404', module: '外协', desc: '外协回料数量待确认', severity: '低', updatedAt: '2026-05-30 16:03' },
])

const exceptionKeyword = ref('')
const readbackError = ref('')

interface ReadbackSummaryModule {
  module_key: string
  module_label: string
  source_endpoint: string
  record_count: number
}

interface ReadbackSummaryResponse {
  scenario_tag: string
  readback_only: boolean
  modules: ReadbackSummaryModule[]
  totals: {
    write_requests_observed_count: number
  }
  workspace_redirect: {
    route: string
    final_path: string
  }
}

interface ReadbackCheckpointsResponse {
  scenario_tag: string
  readback_only: boolean
  write_requests_observed_count: number
  workspace_redirect: {
    route: string
    final_path: string
    readback_success: boolean
  }
}

const readbackSummary = ref<ReadbackSummaryResponse | null>(null)
const readbackCheckpoints = ref<ReadbackCheckpointsResponse | null>(null)

const readbackScenarioTag = computed(() => {
  const raw = Array.isArray(route.query.scenario_tag) ? route.query.scenario_tag[0] : route.query.scenario_tag
  return String(raw || '').trim() || 'REALOBJ-CAND006-READBACK-001'
})

const readbackSummaryModules = computed(() => readbackSummary.value?.modules || [])
const readbackWriteRequestsObservedCount = computed(
  () => Number(readbackCheckpoints.value?.write_requests_observed_count ?? readbackSummary.value?.totals?.write_requests_observed_count ?? 0),
)
const workspaceFinalPath = computed(() => {
  return readbackCheckpoints.value?.workspace_redirect?.final_path || '/dashboard/overview'
})
const dashboardOverviewReadbackSummarySuccess = computed(() => {
  if (!readbackSummary.value) return false
  return readbackSummary.value.readback_only && readbackSummaryModules.value.length > 0
})
const workspaceRedirectReadbackSuccess = computed(() => {
  const redirect = readbackCheckpoints.value?.workspace_redirect
  if (!redirect) return false
  return redirect.readback_success === true && redirect.final_path === '/dashboard/overview'
})

const loadReadbackSummary = async (): Promise<void> => {
  const scenarioTag = readbackScenarioTag.value
  readbackError.value = ''
  try {
    const [summaryResp, checkpointsResp] = await Promise.all([
      request<ReadbackSummaryResponse>(
        `/api/local-dev/dashboard/status-summary?scenario_tag=${encodeURIComponent(scenarioTag)}`,
      ),
      request<ReadbackCheckpointsResponse>(
        `/api/local-dev/dashboard/checkpoints?scenario_tag=${encodeURIComponent(scenarioTag)}`,
      ),
    ])
    readbackSummary.value = summaryResp.data
    readbackCheckpoints.value = checkpointsResp.data
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error)
    readbackError.value = `readback summary 获取失败：${message}`
  }
}

const filteredFlowNodes = computed(() => {
  return flowNodes.filter((node) => {
    const flowMatch = !query.flowType || node.flowType === query.flowType
    const materialMatch = !query.material || node.name.includes(query.material.slice(0, 1))
    const warehouseMatch = !query.warehouse || node.name.includes('仓') || query.warehouse !== ''
    return flowMatch && materialMatch && warehouseMatch
  })
})

const filteredExceptions = computed(() => {
  const keyword = exceptionKeyword.value.trim()
  if (!keyword) {
    return exceptions.value
  }
  return exceptions.value.filter((item) => {
    return item.code.includes(keyword) || item.module.includes(keyword) || item.desc.includes(keyword)
  })
})

const sourceReadback = [
  'yisuan_incremental_capture/sidebar_modules/01_首页.png',
  'G0_baseline_20260518/module_entry_baseline.json',
  'task_z014b_01_a001_a006_contract_candidate_pool.json',
  'G2_FIX20/developer_allowed_reference_map.json',
  'task_z007b_17_module_entry_to_list_route_parity_evidence.json',
]

const go = (path: string): void => {
  router.push(path)
}

onMounted(() => {
  void loadReadbackSummary()
})
</script>

<style scoped>
.yisuan-dashboard-shell {
  min-height: 100%;
  background: #f3f4f6;
  padding: 16px;
  color: #1f2937;
  display: grid;
  gap: 14px;
}

.dashboard-header {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 14px;
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-end;
}

.dashboard-header h1 {
  margin: 0;
  font-size: 22px;
}

.dashboard-header p {
  margin: 6px 0 0;
  color: #6b7280;
}

.header-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.readback-summary {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 14px;
}

.readback-summary > header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.readback-summary h2 {
  margin: 0;
  font-size: 16px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 10px;
}

.summary-card {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 10px;
}

.summary-label {
  display: block;
  color: #6b7280;
  font-size: 12px;
}

.summary-value {
  display: block;
  margin-top: 6px;
  font-size: 20px;
}

.summary-note {
  display: block;
  margin-top: 6px;
  color: #6b7280;
  font-size: 12px;
}

.summary-checkpoint-row {
  margin-top: 10px;
  display: flex;
  gap: 14px;
  flex-wrap: wrap;
  color: #4b5563;
  font-size: 12px;
}

.kpi-strip {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 10px;
}

.kpi-item {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 12px;
}

.kpi-item .label {
  display: block;
  font-size: 12px;
  color: #6b7280;
}

.kpi-item .value {
  display: block;
  margin-top: 6px;
  font-size: 22px;
}

.kpi-item .trend {
  display: block;
  margin-top: 6px;
  color: #6b7280;
  font-size: 12px;
}

.flow-panel {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 14px;
}

.flow-panel > header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.flow-panel h2 {
  margin: 0;
  font-size: 16px;
}

.flow-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 10px;
}

.flow-card {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 10px;
}

.flow-card h3 {
  margin: 0 0 8px;
  font-size: 14px;
}

.flow-card p {
  margin: 0 0 4px;
  font-size: 13px;
}

.dashboard-body {
  display: grid;
  grid-template-columns: 1fr 280px;
  gap: 12px;
}

.exception-list,
.quick-actions,
.source-readback {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 14px;
}

.exception-list > header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.exception-list h2,
.quick-actions h2,
.source-readback h2 {
  margin: 0;
  font-size: 16px;
}

.quick-actions {
  display: grid;
  gap: 8px;
  align-content: start;
}

.quick-actions button {
  text-align: left;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  background: #fff;
  padding: 8px 10px;
  cursor: pointer;
}

.source-readback ul {
  margin: 10px 0 0;
  padding-left: 18px;
  font-size: 13px;
  color: #4b5563;
}

@media (max-width: 1100px) {
  .dashboard-body {
    grid-template-columns: 1fr;
  }
}
</style>
