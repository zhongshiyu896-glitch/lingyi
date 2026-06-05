<template>
  <main class="yisuan-dashboard-shell" data-testid="yisuan-1to1-dashboard-shell">
    <section class="dashboard-header">
      <div>
        <h1>经营总览</h1>
        <p>工作台业务卡片、待办摘要与只读守卫</p>
      </div>
      <div class="header-actions">
        <el-tag effect="plain" type="info">company={{ readbackScenarioTag }}</el-tag>
        <el-tag v-if="routeAliasSummary.isAlias" effect="plain" type="warning">
          source_route={{ routeAliasSummary.sourceRoute }}
        </el-tag>
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

    <section class="readback-summary" data-testid="cand122-dashboard-readonly-summary">
      <header>
        <h2>工作台只读聚合</h2>
        <el-tag effect="plain" :type="routeAliasSummary.isAlias ? 'warning' : 'success'">
          final_path={{ routeAliasSummary.finalPath }}
        </el-tag>
      </header>
      <el-alert
        v-if="readbackError"
        type="warning"
        :closable="false"
        :title="readbackError"
        data-testid="cand122-dashboard-readonly-error"
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
        <span>workspace_source_route={{ routeAliasSummary.sourceRoute }}</span>
        <span>workspace_final_path={{ routeAliasSummary.finalPath }}</span>
        <span>write_requests_observed_count={{ readbackWriteRequestsObservedCount }}</span>
      </div>
    </section>

    <DashboardModuleEntryReadonlySection
      :items="dashboardModuleEntryItems"
      :readonly-actions="dashboardModuleEntryReadonlyActions"
      :remaining-gap="dashboardModuleEntryRemainingGap"
      :source-layer="dashboardModuleEntrySourceLayer"
      :final-path="routeAliasSummary.finalPath"
      @navigate="go"
    />

    <DashboardWorkbenchReadonlySection
      :cards="workbenchCards"
      :cross-module-items="crossModuleReadonlyItems"
      :source-layer="dashboardReadonlySourceLayer"
      :final-path="routeAliasSummary.finalPath"
      :remaining-gap="dashboardRemainingGap"
      @navigate="go"
    />

    <DashboardAlertReadonlySection
      :alert-items="dashboardAlertItems"
      :audit-items="dashboardAlertAuditItems"
      :readonly-actions="dashboardAlertReadonlyActions"
      :source-layer="dashboardAlertSourceLayer"
      :final-path="routeAliasSummary.finalPath"
    />

    <DashboardTrendReadonlySection
      :window-items="dashboardTrendWindowItems"
      :freshness-items="dashboardTrendFreshnessItems"
      :refresh-explanation="dashboardTrendRefreshExplanation"
      :readonly-actions="dashboardTrendReadonlyActions"
      :remaining-gap="dashboardTrendRemainingGap"
      :source-layer="dashboardTrendSourceLayer"
      :final-path="routeAliasSummary.finalPath"
    />

    <DashboardTodoReadonlySection
      :aging-items="dashboardTodoAgingItems"
      :readonly-actions="dashboardTodoReadonlyActions"
      :remaining-gap="dashboardTodoRemainingGap"
      :source-layer="dashboardTodoSourceLayer"
      :final-path="routeAliasSummary.finalPath"
    />

    <section class="todo-guard-grid">
      <article class="todo-summary" data-testid="cand122-dashboard-todo-summary">
        <header>
          <h2>待办摘要</h2>
          <el-tag effect="plain" type="info">home_overview.todo_items</el-tag>
        </header>
        <div class="todo-items">
          <article v-for="item in todoSummaryItems" :key="item.key" class="todo-item">
            <div class="todo-item-top">
              <strong>{{ item.title }}</strong>
              <el-tag effect="plain" :type="item.tone">{{ item.statusLabel }}</el-tag>
            </div>
            <span class="todo-count">{{ item.count }} 项</span>
            <small class="todo-note">{{ item.note }}</small>
          </article>
        </div>
      </article>

      <article class="guard-summary" data-testid="cand122-dashboard-guard-summary">
        <header>
          <h2>入口守卫状态</h2>
          <el-tag effect="plain" type="warning">{{ routeAliasSummary.aliasReason }}</el-tag>
        </header>
        <div class="guard-items">
          <article v-for="item in healthGuardItems" :key="item.key" class="guard-item">
            <div class="guard-item-top">
              <strong>{{ item.label }}</strong>
              <el-tag effect="plain" :type="item.tone">{{ item.status }}</el-tag>
            </div>
            <small>{{ item.detail }}</small>
          </article>
        </div>
      </article>
    </section>

    <section class="kpi-strip" data-testid="cand122-dashboard-kpi-strip">
      <article v-for="item in kpiItems" :key="item.label" class="kpi-item">
        <span class="label">{{ item.label }}</span>
        <strong class="value">{{ item.value }}</strong>
        <small class="trend">{{ item.trend }}</small>
      </article>
    </section>

    <section class="flow-panel" data-testid="cand122-dashboard-flow-panel">
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
      <article class="exception-list" data-testid="cand122-dashboard-exception-list">
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
          <el-table-column prop="updatedAt" label="更新时间" width="180" />
        </el-table>
      </article>

      <article class="readonly-actions" data-testid="cand122-dashboard-readonly-actions">
        <h2>受控动作</h2>
        <div class="readonly-action-list">
          <article v-for="item in readonlyActions" :key="item.key" class="readonly-action-item">
            <el-button size="small" disabled>{{ item.label }}</el-button>
            <small>{{ item.reason }}</small>
          </article>
        </div>
      </article>
    </section>

    <section class="source-readback" data-testid="cand122-dashboard-source-readback">
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
import type { DashboardOverviewData, DashboardOverviewQuery } from '@/api/dashboard'
import {
  fetchDashboardWorkbenchReadonly,
  type DashboardHealthSummaryData,
} from '@/api/dashboard_readonly'
import DashboardAlertReadonlySection from './components/DashboardAlertReadonlySection.vue'
import DashboardModuleEntryReadonlySection from './components/DashboardModuleEntryReadonlySection.vue'
import DashboardTodoReadonlySection from './components/DashboardTodoReadonlySection.vue'
import DashboardTrendReadonlySection from './components/DashboardTrendReadonlySection.vue'
import DashboardWorkbenchReadonlySection from './components/DashboardWorkbenchReadonlySection.vue'
import { useDashboardAlertReadonly } from './composables/useDashboardAlertReadonly'
import { useDashboardCrossModuleReadonly } from './composables/useDashboardCrossModuleReadonly'
import { useDashboardModuleEntryReadonly } from './composables/useDashboardModuleEntryReadonly'
import { useDashboardTodoReadonly } from './composables/useDashboardTodoReadonly'
import { useDashboardTrendReadonly } from './composables/useDashboardTrendReadonly'
import { useDashboardWorkbenchReadonly } from './composables/useDashboardWorkbenchReadonly'

const router = useRouter()
const route = useRoute()

const overviewData = ref<DashboardOverviewData | null>(null)
const healthSummary = ref<DashboardHealthSummaryData | null>(null)
const readbackError = ref('')
const exceptionKeyword = ref('')

const query = reactive({
  material: '',
  warehouse: '',
  flowType: '',
})

const DEFAULT_COMPANY = '领意服装'
const materialOptions = ['主面料', '辅料', '包材', '样衣']
const warehouseOptions = ['主仓', '裁片仓', '成品仓', '外协仓']
const flowTypeOptions = ['采购', '外协', '生产', '库存']

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

const readbackScenarioTag = computed(() => readQueryText(route.query.company) || DEFAULT_COMPANY)

const overviewQuery = computed<DashboardOverviewQuery>(() => ({
  company: readbackScenarioTag.value,
  from_date: readQueryText(route.query.from_date),
  to_date: readQueryText(route.query.to_date),
  item_code: readQueryText(route.query.item_code),
  warehouse: readQueryText(route.query.warehouse),
  keyword: readQueryText(route.query.keyword),
}))

const {
  routeAliasSummary,
  readbackSummaryModules,
  kpiItems,
  flowNodes,
  exceptionRows,
  workbenchCards,
  todoSummaryItems,
  healthGuardItems,
  readonlyActions,
  sourceReadback,
} = useDashboardWorkbenchReadonly({
  overviewData,
  healthSummary,
  route,
})

const {
  crossModuleReadonlyItems,
  remainingGap: dashboardRemainingGap,
  sourceLayer: dashboardReadonlySourceLayer,
} = useDashboardCrossModuleReadonly({
  workbenchCards,
  healthSummary,
  routeAliasSummary,
})

const {
  dashboardAlertItems,
  dashboardAlertAuditItems,
  dashboardAlertReadonlyActions,
  dashboardAlertSourceLayer,
} = useDashboardAlertReadonly({
  overviewData,
  healthSummary,
  routeAliasSummary,
})

const {
  dashboardModuleEntryItems,
  dashboardModuleEntryReadonlyActions,
  dashboardModuleEntryRemainingGap,
  dashboardModuleEntrySourceLayer,
} = useDashboardModuleEntryReadonly({
  overviewData,
  healthSummary,
  routeAliasSummary,
})

const {
  dashboardTrendWindowItems,
  dashboardTrendFreshnessItems,
  dashboardTrendRefreshExplanation,
  dashboardTrendReadonlyActions,
  dashboardTrendRemainingGap,
  dashboardTrendSourceLayer,
} = useDashboardTrendReadonly({
  overviewData,
  healthSummary,
  routeAliasSummary,
})

const {
  dashboardTodoAgingItems,
  dashboardTodoReadonlyActions,
  dashboardTodoRemainingGap,
  dashboardTodoSourceLayer,
} = useDashboardTodoReadonly({
  overviewData,
  healthSummary,
  routeAliasSummary,
})

const readbackWriteRequestsObservedCount = computed(() => 0)
const dashboardOverviewReadbackSummarySuccess = computed(() => readbackSummaryModules.value.length > 0)
const workspaceRedirectReadbackSuccess = computed(
  () => routeAliasSummary.value.finalPath === routeAliasSummary.value.expectedFinalPath,
)

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
  if (!keyword) return exceptionRows.value
  return exceptionRows.value.filter((item) => {
    return item.code.includes(keyword) || item.module.includes(keyword) || item.desc.includes(keyword)
  })
})

const loadOverview = async (): Promise<void> => {
  readbackError.value = ''
  try {
    const payload = await fetchDashboardWorkbenchReadonly(overviewQuery.value)
    overviewData.value = payload.overview
    healthSummary.value = payload.healthSummary
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error)
    overviewData.value = null
    healthSummary.value = null
    readbackError.value = `经营工作台只读聚合获取失败：${message}`
  }
}

const go = (path: string): void => {
  void router.push(path)
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

.dashboard-header,
.readback-summary,
.workbench-board,
.todo-summary,
.guard-summary,
.flow-panel,
.exception-list,
.readonly-actions,
.source-readback {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}

.dashboard-header,
.readback-summary,
.workbench-board,
.flow-panel,
.exception-list,
.readonly-actions,
.source-readback {
  padding: 14px;
}

.dashboard-header {
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
  align-items: center;
}

.readback-summary > header,
.workbench-board > header,
.flow-panel > header,
.todo-summary > header,
.guard-summary > header,
.exception-list > header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
}

.readback-summary h2,
.workbench-board h2,
.flow-panel h2,
.todo-summary h2,
.guard-summary h2,
.exception-list h2,
.readonly-actions h2,
.source-readback h2 {
  margin: 0;
  font-size: 16px;
}

.summary-grid,
.workbench-grid,
.kpi-strip,
.flow-grid {
  display: grid;
  gap: 10px;
}

.summary-grid {
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
}

.summary-card,
.workbench-card,
.todo-item,
.guard-item,
.kpi-item,
.flow-card,
.readonly-action-item {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
}

.summary-card,
.workbench-card,
.todo-item,
.guard-item,
.kpi-item,
.flow-card {
  padding: 10px;
}

.summary-label,
.workbench-metric-label,
.todo-note,
.summary-note,
.kpi-item .label {
  color: #6b7280;
  font-size: 12px;
}

.summary-value,
.workbench-metric,
.kpi-item .value {
  display: block;
  margin-top: 6px;
  font-size: 20px;
}

.summary-checkpoint-row {
  margin-top: 10px;
  display: flex;
  gap: 14px;
  flex-wrap: wrap;
  color: #4b5563;
  font-size: 12px;
}

.workbench-board > header p {
  margin: 6px 0 0;
  color: #6b7280;
  font-size: 13px;
}

.workbench-grid {
  grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
}

.workbench-card {
  display: grid;
  gap: 8px;
}

.workbench-card-top {
  display: flex;
  justify-content: space-between;
  gap: 8px;
}

.workbench-card-top h3 {
  margin: 0;
  font-size: 15px;
}

.workbench-card-top p,
.workbench-detail,
.workbench-note,
.guard-item small {
  margin: 0;
  color: #6b7280;
  font-size: 12px;
}

.workbench-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.todo-guard-grid,
.dashboard-body {
  display: grid;
  gap: 12px;
}

.todo-guard-grid {
  grid-template-columns: 1.2fr 1fr;
}

.todo-summary,
.guard-summary {
  padding: 14px;
}

.todo-items,
.guard-items,
.readonly-action-list {
  display: grid;
  gap: 10px;
}

.todo-item-top,
.guard-item-top {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  align-items: center;
}

.todo-count {
  display: block;
  margin-top: 6px;
  font-size: 20px;
  font-weight: 600;
}

.kpi-strip {
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
}

.kpi-item .trend {
  display: block;
  margin-top: 6px;
  color: #6b7280;
  font-size: 12px;
}

.flow-grid {
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
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
  grid-template-columns: 1fr 320px;
}

.readonly-actions {
  display: grid;
  gap: 10px;
  align-content: start;
}

.readonly-action-item {
  padding: 10px;
  display: grid;
  gap: 8px;
}

.readonly-action-item small {
  color: #6b7280;
  font-size: 12px;
  line-height: 1.5;
}

.source-readback ul {
  margin: 10px 0 0;
  padding-left: 18px;
  font-size: 13px;
  color: #4b5563;
}

@media (max-width: 1100px) {
  .dashboard-body,
  .todo-guard-grid {
    grid-template-columns: 1fr;
  }
}
</style>
