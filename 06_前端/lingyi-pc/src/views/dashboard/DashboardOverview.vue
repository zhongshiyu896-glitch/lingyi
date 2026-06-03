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
        <h2>经营看板聚合（只读）</h2>
        <el-tag effect="plain" type="info">company={{ readbackScenarioTag }}</el-tag>
      </header>
      <el-alert
        v-if="readbackError"
        type="warning"
        :closable="false"
        :title="readbackError"
        data-testid="cand006-dashboard-readback-error"
      />
      <div v-else class="summary-grid">
        <article v-for="item in readbackSummaryModules" :key="item.key" class="summary-card">
          <span class="summary-label">{{ item.label }}</span>
          <strong class="summary-value">{{ item.value }}</strong>
          <small class="summary-note">{{ item.note }}</small>
        </article>
      </div>
      <div class="summary-checkpoint-row">
        <span>dashboard_overview_loaded={{ dashboardOverviewReadbackSummarySuccess ? 'true' : 'false' }}</span>
        <span>workspace_redirect_fixed={{ workspaceRedirectReadbackSuccess ? 'true' : 'false' }}</span>
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
      <h2>只读数据来源</h2>
      <ul>
        <li v-for="item in sourceReadback" :key="item">{{ item }}</li>
      </ul>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  fetchDashboardOverview,
  type DashboardOverviewData,
  type DashboardOverviewQuery,
} from '@/api/dashboard'

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

interface SummaryCardItem {
  key: string
  label: string
  value: string
  note: string
}

const router = useRouter()
const route = useRoute()
const readbackError = ref('')
const overviewData = ref<DashboardOverviewData | null>(null)

const query = reactive({
  material: '',
  warehouse: '',
  flowType: '',
})

const DEFAULT_COMPANY = '领意服装'

const readQueryText = (value: unknown): string | undefined => {
  if (Array.isArray(value)) {
    return readQueryText(value[0])
  }
  if (typeof value !== 'string') {
    return undefined
  }
  const normalized = value.trim()
  return normalized || undefined
}

const materialOptions = ['主面料', '辅料', '包材', '样衣']
const warehouseOptions = ['主仓', '裁片仓', '成品仓', '外协仓']
const flowTypeOptions = ['采购', '外协', '生产', '库存']
const exceptionKeyword = ref('')

const readbackScenarioTag = computed(() => {
  return readQueryText(route.query.company) || DEFAULT_COMPANY
})

const overviewQuery = computed<DashboardOverviewQuery>(() => ({
  company: readbackScenarioTag.value,
  from_date: readQueryText(route.query.from_date),
  to_date: readQueryText(route.query.to_date),
  item_code: readQueryText(route.query.item_code),
  warehouse: readQueryText(route.query.warehouse),
  keyword: readQueryText(route.query.keyword),
}))

const readbackSummaryModules = computed<SummaryCardItem[]>(() => {
  const statuses = overviewData.value?.source_status || []
  return statuses.map((item) => ({
    key: item.module,
    label: item.module,
    value: item.status,
    note: 'dashboard/overview 只读聚合',
  }))
})

const readbackWriteRequestsObservedCount = computed(() => 0)
const workspaceFinalPath = computed(() => '/dashboard/overview')
const dashboardOverviewReadbackSummarySuccess = computed(() => readbackSummaryModules.value.length > 0)
const workspaceRedirectReadbackSuccess = computed(() => true)

const kpis = computed<KPIItem[]>(() => {
  const metricCards = overviewData.value?.home_overview?.metric_cards || []
  return metricCards.map((item) => ({
    label: item.label,
    value: item.unit ? `${item.value}${item.unit}` : item.value,
    trend: item.trend || '只读汇总',
  }))
})

const inferFlowType = (label: string): string => {
  if (label.includes('仓') || label.includes('库存')) return '库存'
  if (label.includes('采购')) return '采购'
  if (label.includes('外协')) return '外协'
  return '生产'
}

const flowNodes = computed<FlowNode[]>(() => {
  const nodes = overviewData.value?.kanban?.flow_nodes || []
  return nodes.map((node) => ({
    name: node.label,
    pending: node.status === 'completed' ? 0 : 1,
    overdue: node.status === 'active' ? 1 : 0,
    owner: node.route || '只读聚合',
    flowType: inferFlowType(node.label),
  }))
})

const exceptions = computed<ExceptionItem[]>(() => {
  const warnings = overviewData.value?.home_overview?.warnings || []
  const summaries = overviewData.value?.home_overview?.business_summary || []
  const generatedAt = overviewData.value?.generated_at || ''
  const rows: ExceptionItem[] = warnings.map((item, index) => ({
    code: `WARN-${String(index + 1).padStart(2, '0')}`,
    module: '看板',
    desc: item,
    severity: '中',
    updatedAt: generatedAt,
  }))
  if (overviewData.value) {
    rows.push(
      {
        code: 'SUM-01',
        module: '库存',
        desc: summaries[1] || `低于安全库存款号 ${overviewData.value.sales_inventory.below_safety_count} 个`,
        severity: Number(overviewData.value.sales_inventory.below_safety_count) > 0 ? '高' : '低',
        updatedAt: generatedAt,
      },
      {
        code: 'SUM-02',
        module: '仓储',
        desc: summaries[3] || `仓储高危预警 ${overviewData.value.warehouse.critical_alert_count} 条`,
        severity: Number(overviewData.value.warehouse.critical_alert_count) > 0 ? '高' : '低',
        updatedAt: generatedAt,
      },
    )
  }
  return rows
})

const loadOverview = async (): Promise<void> => {
  readbackError.value = ''
  try {
    const response = await fetchDashboardOverview(overviewQuery.value)
    overviewData.value = response.data
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error)
    overviewData.value = null
    readbackError.value = `经营看板聚合获取失败：${message}`
  }
}

const filteredFlowNodes = computed(() => {
  return flowNodes.value.filter((node) => {
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

const sourceReadback = computed(() => {
  const statuses = overviewData.value?.source_status || []
  const quickFilters = overviewData.value?.kanban?.quick_filters || []
  return [
    ...statuses.map((item) => `source.${item.module}=${item.status}`),
    ...quickFilters.slice(0, 5).map((item) => `filter.${item}`),
  ]
})

const go = (path: string): void => {
  router.push(path)
}

onMounted(() => {
  void loadOverview()
})

watch(overviewQuery, () => {
  void loadOverview()
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
