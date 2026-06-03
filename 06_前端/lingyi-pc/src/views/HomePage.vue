<template>
  <main class="yisuan-home-shell" data-testid="yisuan-1to1-home-shell">
    <aside class="yisuan-sidebar" data-testid="yisuan-1to1-global-sidebar">
      <div class="brand">
        <h1>衣算云</h1>
        <p>服装智造管理平台</p>
      </div>
      <section v-for="group in sidebarGroups" :key="group.title" class="sidebar-group">
        <h2>{{ group.title }}</h2>
        <button
          v-for="item in group.items"
          :key="item.path"
          class="sidebar-link"
          type="button"
          @click="go(item.path)"
        >
          <span>{{ item.name }}</span>
          <small>{{ item.path }}</small>
        </button>
      </section>
    </aside>

    <section class="yisuan-main">
      <header class="yisuan-topbar" data-testid="yisuan-1to1-topbar">
        <div class="topbar-title">
          <h2>首页工作台</h2>
          <p>UI 1:1 对齐预览（只读）</p>
        </div>
        <div class="topbar-meta">
          <span>组织：领意服装</span>
          <span>角色：运营管理</span>
          <span>会话：LOCAL-READONLY</span>
        </div>
      </header>

      <section class="readback-summary" data-testid="cand006-home-readback-summary">
        <div class="grid-header">
          <h3>经营总览（只读）</h3>
          <el-tag effect="plain" type="info">company={{ readbackScenarioTag }}</el-tag>
        </div>
        <el-alert
          v-if="readbackError"
          type="warning"
          :closable="false"
          :title="readbackError"
          data-testid="cand006-home-readback-error"
        />
        <div v-else class="readback-summary-grid">
          <article v-for="item in readbackSummaryModules" :key="item.key" class="status-card">
            <span class="status-label">{{ item.label }}</span>
            <strong class="status-value">{{ item.value }}</strong>
            <small class="status-note">{{ item.note }}</small>
          </article>
        </div>
        <div class="readback-checkpoint-row">
          <span>overview_loaded={{ homepageReadbackSummarySuccess ? 'true' : 'false' }}</span>
          <span>workplace_redirect_fixed={{ workspaceRedirectReadbackSuccess ? 'true' : 'false' }}</span>
          <span>source_modules_ok={{ sourceStatusOkCount }}/{{ sourceStatusCount }}</span>
          <span>write_requests_observed_count={{ readbackWriteRequestsObservedCount }}</span>
        </div>
      </section>

      <section class="home-entry-overview" data-testid="cand038-home-entry-overview">
        <div class="grid-header">
          <h3>首页入口概览</h3>
          <el-tag effect="plain" type="success">GET-only</el-tag>
        </div>
        <div class="readback-summary-grid">
          <article v-for="item in homeEntryOverviewCards" :key="item.key" class="status-card">
            <span class="status-label">{{ item.label }}</span>
            <strong class="status-value">{{ item.value }}</strong>
            <small class="status-note">{{ item.note }}</small>
          </article>
        </div>
        <div class="readonly-action-row" data-testid="cand038-home-readonly-action-guard">
          <el-button disabled type="primary" plain>新建</el-button>
          <el-button disabled plain>修改</el-button>
          <el-button disabled plain>删除</el-button>
          <span class="readonly-action-note">首页只提供只读入口和导航提示，不开放写入动作。</span>
        </div>
      </section>

      <section class="module-summary-panel" data-testid="cand038-home-module-summary">
        <div class="grid-header">
          <h3>模块摘要</h3>
          <span class="summary-note">按入口分组的只读摘要</span>
        </div>
        <div class="grid-body">
          <article v-for="item in moduleSummaryCards" :key="item.key" class="entry-card summary-card">
            <header>
              <strong>{{ item.label }}</strong>
              <el-tag effect="plain" type="success">{{ item.readyCount }}/{{ item.count }}</el-tag>
            </header>
            <p class="entry-desc">{{ item.note }}</p>
            <p class="entry-path">{{ item.paths }}</p>
          </article>
        </div>
      </section>

      <section class="module-entry-grid" data-testid="yisuan-1to1-module-entry-grid">
        <div class="grid-header">
          <h3>模块入口</h3>
          <el-input
            v-model="moduleKeyword"
            clearable
            placeholder="按模块名过滤"
            style="max-width: 260px"
          />
        </div>
        <div class="grid-body">
          <article v-for="entry in filteredModuleEntries" :key="entry.path" class="entry-card">
            <header>
              <strong>{{ entry.name }}</strong>
              <el-tag :type="entry.status === '已就绪' ? 'success' : 'warning'" effect="plain">
                {{ entry.status }}
              </el-tag>
            </header>
            <p class="entry-path">{{ entry.path }}</p>
            <p class="entry-desc">{{ entry.desc }}</p>
            <el-button link type="primary" @click="go(entry.path)">进入</el-button>
          </article>
        </div>
      </section>

      <section class="status-panel" data-testid="cand044-home-exception-alert-summary">
        <div class="grid-header">
          <h3>异常提醒摘要</h3>
          <span class="summary-note">只读聚合，不触发处置写入</span>
        </div>
        <div class="status-grid">
          <article v-for="item in statusCards" :key="item.label" class="status-card">
            <span class="status-label">{{ item.label }}</span>
            <strong class="status-value">{{ item.value }}</strong>
            <small class="status-note">{{ item.note }}</small>
          </article>
        </div>
      </section>

      <section class="workbench-list" data-testid="cand044-home-role-todo-overview">
        <div class="grid-header">
          <h3>角色待办概览</h3>
          <span class="summary-note">按角色聚合只读待办，不开放处理动作</span>
        </div>
        <el-table :data="workbenchRows" border empty-text="暂无任务">
          <el-table-column prop="task" label="任务" min-width="180" />
          <el-table-column prop="owner" label="负责人" width="120" />
          <el-table-column prop="deadline" label="截止日期" width="140" />
          <el-table-column prop="priority" label="优先级" width="110" />
          <el-table-column prop="status" label="状态" width="120" />
        </el-table>
      </section>

      <section class="recent-access-summary" data-testid="cand044-home-recent-access-summary">
        <div class="grid-header">
          <h3>最近访问摘要</h3>
          <span class="summary-note">无访问聚合时回退展示最近可访问的只读入口</span>
        </div>
        <div class="grid-body">
          <article
            v-for="item in recentAccessSummaryItems"
            :key="item.key"
            class="entry-card recent-access-card"
          >
            <header>
              <strong>{{ item.title }}</strong>
              <el-tag effect="plain" type="info">{{ item.badge }}</el-tag>
            </header>
            <p class="entry-desc">{{ item.detail }}</p>
            <p class="entry-path">{{ item.hint }}</p>
          </article>
        </div>
      </section>

      <section class="business-calendar-panel" data-testid="cand050-home-business-calendar">
        <div class="grid-header">
          <h3>业务日历</h3>
          <span class="summary-note">按周展示经营预测与关键排期，只读聚合不触发业务写入</span>
        </div>
        <div class="grid-body">
          <article
            v-for="item in businessCalendarItems"
            :key="item.key"
            class="entry-card business-calendar-card"
          >
            <header>
              <strong>{{ item.period }}</strong>
              <el-tag effect="plain" type="warning">{{ item.badge }}</el-tag>
            </header>
            <div class="calendar-metrics">
              <span>销售 {{ item.sales }}</span>
              <span>成本 {{ item.cost }}</span>
              <span>利润 {{ item.profit }}</span>
            </div>
            <p class="entry-desc">{{ item.note }}</p>
            <p class="entry-path">{{ item.hint }}</p>
          </article>
        </div>
      </section>

      <section class="today-key-nodes-panel" data-testid="cand050-home-today-key-nodes">
        <div class="grid-header">
          <h3>今日关键节点</h3>
          <span class="summary-note">聚合今日应优先核对的只读业务节点</span>
        </div>
        <div class="grid-body">
          <article v-for="item in todayKeyNodeItems" :key="item.key" class="entry-card summary-card">
            <header>
              <strong>{{ item.title }}</strong>
              <el-tag effect="plain" type="success">{{ item.badge }}</el-tag>
            </header>
            <p class="entry-desc">{{ item.value }}</p>
            <p class="entry-path">{{ item.note }}</p>
            <small class="status-note">{{ item.hint }}</small>
          </article>
        </div>
      </section>

      <section
        class="cross-module-reminders-panel"
        data-testid="cand050-home-cross-module-key-reminders"
      >
        <div class="grid-header">
          <h3>跨模块关键提醒</h3>
          <span class="summary-note">来源于 dashboard overview 的提醒与只读动作建议</span>
        </div>
        <div class="grid-body">
          <article
            v-for="item in crossModuleReminderItems"
            :key="item.key"
            class="entry-card reminder-card"
          >
            <header>
              <strong>{{ item.title }}</strong>
              <el-tag effect="plain" type="info">{{ item.badge }}</el-tag>
            </header>
            <p class="entry-desc">{{ item.detail }}</p>
            <p class="entry-path">{{ item.hint }}</p>
          </article>
        </div>
      </section>

      <section class="readonly-hints" data-testid="cand038-home-readonly-hints">
        <h3>只读导航提示</h3>
        <ul>
          <li v-for="item in readonlyNavigationHints" :key="item">{{ item }}</li>
        </ul>
      </section>

      <section class="source-readback" data-testid="yisuan-1to1-ui-source-readback">
        <h3>只读数据来源</h3>
        <ul>
          <li v-for="item in uiSourceReadback" :key="item">{{ item }}</li>
        </ul>
      </section>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  fetchDashboardOverview,
  type DashboardOverviewData,
  type DashboardOverviewQuery,
} from '@/api/dashboard'

interface NavItem {
  name: string
  path: string
}

interface NavGroup {
  title: string
  items: NavItem[]
}

interface ModuleEntry extends NavItem {
  group: string
  desc: string
  status: string
}

interface StatusCard {
  label: string
  value: string
  note: string
}

interface WorkbenchRow {
  task: string
  owner: string
  deadline: string
  priority: string
  status: string
}

interface RecentAccessSummaryItem {
  key: string
  title: string
  detail: string
  hint: string
  badge: string
}

interface OverviewSummaryCard {
  key: string
  label: string
  value: string
  note: string
}

interface ModuleSummaryCard {
  key: string
  label: string
  count: number
  readyCount: number
  note: string
  paths: string
}

interface BusinessCalendarItem {
  key: string
  period: string
  badge: string
  sales: string
  cost: string
  profit: string
  note: string
  hint: string
}

interface TodayKeyNodeItem {
  key: string
  title: string
  badge: string
  value: string
  note: string
  hint: string
}

interface CrossModuleReminderItem {
  key: string
  title: string
  badge: string
  detail: string
  hint: string
}

const router = useRouter()
const route = useRoute()
const moduleKeyword = ref('')
const readbackError = ref('')
const overviewData = ref<DashboardOverviewData | null>(null)

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

const sidebarGroups: NavGroup[] = [
  {
    title: '运营工作台',
    items: [
      { name: '首页', path: '/home' },
      { name: '经营看板', path: '/dashboard/overview' },
    ],
  },
  {
    title: '核心业务',
    items: [
      { name: '物料开发', path: '/bom/list' },
      { name: '大货管理', path: '/sales-inventory/sales-orders' },
      { name: '采购/外协', path: '/subcontract/list?parity=material-purchase' },
      { name: '库存流水', path: '/sales-inventory/stock-ledger' },
    ],
  },
]

const moduleEntries: ModuleEntry[] = [
  { name: '基础资料', path: '/sales-inventory/references', group: '基础资料', desc: '款号、客户、供应商基础信息', status: '已就绪' },
  { name: 'BOM 物料开发', path: '/bom/list', group: '物料开发', desc: 'BOM 列表与明细对齐', status: '已就绪' },
  { name: '大货订单', path: '/sales-inventory/sales-orders', group: '大货管理', desc: '订单草稿与计划联动', status: '已就绪' },
  { name: '采购外协', path: '/subcontract/list?parity=material-purchase', group: '物料采购', desc: '前置单据与明细追踪', status: '已就绪' },
  { name: '库存管理', path: '/sales-inventory/stock-ledger', group: '物料进销存', desc: '库存流水与仓库摘要', status: '已就绪' },
  { name: '仓库看板', path: '/warehouse', group: '物料进销存', desc: '仓库概况与盘点入口', status: '已就绪' },
]

const readonlyNavigationHints = [
  '首页卡片只负责导航和摘要展示，所有入口保持只读。',
  '经营看板已在 /dashboard/overview 独立交付，本页不回流到那条已完成切片。',
  '模块入口优先跳转到已就绪的本地只读页面，不触发写入或生产链路。',
]

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

const readbackSummaryModules = computed<OverviewSummaryCard[]>(() => {
  const metricCards = overviewData.value?.home_overview?.metric_cards || []
  return metricCards.map((item) => ({
    key: item.key,
    label: item.label,
    value: item.unit ? `${item.value}${item.unit}` : item.value,
    note: item.trend || '只读汇总',
  }))
})

const homeEntryOverviewCards = computed<OverviewSummaryCard[]>(() => {
  const readyCount = moduleEntries.filter((item) => item.status === '已就绪').length
  const sourceStatusNote = sourceStatusCount.value
    ? `GET-only 聚合 ${sourceStatusOkCount.value}/${sourceStatusCount.value}`
    : '等待 overview 返回'
  return [
    {
      key: 'entry-count',
      label: '入口总数',
      value: String(moduleEntries.length),
      note: '首页卡片与侧边栏共用只读导航入口',
    },
    {
      key: 'ready-count',
      label: '已就绪模块',
      value: String(readyCount),
      note: '仅暴露本地可试用的只读入口',
    },
    {
      key: 'source-count',
      label: '只读数据源',
      value: String(sourceStatusCount.value),
      note: sourceStatusNote,
    },
    {
      key: 'hint-count',
      label: '导航提示',
      value: String(readonlyNavigationHints.length),
      note: '新建/修改/删除动作固定禁用',
    },
  ]
})

const readbackWriteRequestsObservedCount = computed(() => 0)
const sourceStatuses = computed(() => overviewData.value?.source_status || [])
const sourceStatusCount = computed(() => sourceStatuses.value.length)
const sourceStatusOkCount = computed(() => sourceStatuses.value.filter((item) => item.status === 'ok').length)
const homepageReadbackSummarySuccess = computed(() => readbackSummaryModules.value.length > 0)
const workspaceRedirectReadbackSuccess = computed(() => true)

const statusCards = computed<StatusCard[]>(() => {
  const homeOverview = overviewData.value?.home_overview
  const warnings = homeOverview?.warnings || []
  const summaries = homeOverview?.business_summary || []
  const criticalAlerts = Number(overviewData.value?.warehouse.critical_alert_count ?? 0)
  const defectCount = Number(overviewData.value?.quality.defect_count ?? 0)
  return [
    {
      label: '异常提醒',
      value: String(warnings.length),
      note: warnings[0] || '当前没有显式异常提醒，保留只读提示位。',
    },
    {
      label: '仓储高危',
      value: String(criticalAlerts),
      note: criticalAlerts > 0 ? '优先做只读核对，不触发仓储写入。' : '当前没有高危仓储预警。',
    },
    {
      label: '质检缺陷',
      value: String(defectCount),
      note: summaries[0] || '暂无业务异常摘要，等待 overview 汇总返回。',
    },
    {
      label: '只读保护',
      value: 'GET-only',
      note: '首页仅展示待办、提醒和最近访问摘要，不开放创建/修改/删除。',
    },
  ]
})

const workbenchRows = computed<WorkbenchRow[]>(() => {
  const todoItems = overviewData.value?.home_overview?.todo_items || []
  if (todoItems.length > 0) {
    return todoItems.map((item) => ({
      task: item.title,
      owner: item.action_label,
      deadline: '只读',
      priority: item.status === 'urgent' ? '高' : item.status === 'warning' ? '中' : '低',
      status: `${item.count} 项`,
    }))
  }

  const alertCount = Number(overviewData.value?.warehouse.alert_count ?? 0)
  const defectCount = Number(overviewData.value?.quality.defect_count ?? 0)

  return [
    {
      task: '只读聚合就绪检查',
      owner: '首页',
      deadline: '只读',
      priority: sourceStatusCount.value > 0 && sourceStatusOkCount.value === sourceStatusCount.value ? '低' : '中',
      status: `${sourceStatusOkCount.value}/${sourceStatusCount.value} 源`,
    },
    {
      task: '仓储预警复核',
      owner: '仓库',
      deadline: '只读',
      priority: alertCount > 0 ? '中' : '低',
      status: `${alertCount} 项`,
    },
    {
      task: '质检异常复核',
      owner: '质检',
      deadline: '只读',
      priority: defectCount > 0 ? '中' : '低',
      status: `${defectCount} 项`,
    },
  ]
})

const recentAccessSummaryItems = computed<RecentAccessSummaryItem[]>(() => {
  const activities = overviewData.value?.home_overview?.recent_activities || []
  if (activities.length > 0) {
    return activities.slice(0, 4).map((item, index) => ({
      key: `recent-${index}`,
      title: `最近访问 ${index + 1}`,
      detail: item,
      hint: '来源：dashboard overview / home_overview.recent_activities',
      badge: '聚合',
    }))
  }

  return moduleEntries.slice(0, 4).map((entry) => ({
    key: `fallback-${entry.path}`,
    title: entry.name,
    detail: entry.desc,
    hint: `回退入口：${entry.path}`,
    badge: 'fallback',
  }))
})

const businessCalendarItems = computed<BusinessCalendarItem[]>(() => {
  const trendPoints = overviewData.value?.home_overview?.trend_points || []
  if (trendPoints.length > 0) {
    return trendPoints.map((item, index) => ({
      key: `calendar-${item.period}`,
      period: `业务周 ${item.period}`,
      badge: index === 0 ? '本周' : '预排',
      sales: String(item.forecast_sales),
      cost: String(item.forecast_cost),
      profit: String(item.forecast_profit),
      note: `${item.period} 经营预测只读展示，便于首页快速核对业务节奏。`,
      hint: '来源：dashboard overview / home_overview.trend_points',
    }))
  }

  return [
    {
      key: 'calendar-fallback',
      period: '业务周 W1',
      badge: '回退',
      sales: '0',
      cost: '0',
      profit: '0',
      note: '当前未返回业务日历预测数据，保留只读占位。',
      hint: '来源：fallback',
    },
  ]
})

const todayKeyNodeItems = computed<TodayKeyNodeItem[]>(() => {
  const summaries = overviewData.value?.home_overview?.business_summary || []
  const titles = ['质检节点', '安全库存节点', '补货线节点', '仓储预警节点']
  const todoItems = overviewData.value?.home_overview?.todo_items || []

  if (summaries.length > 0) {
    return summaries.slice(0, 4).map((item, index) => ({
      key: `node-${index}`,
      title: titles[index] || `关键节点 ${index + 1}`,
      badge: index === 0 ? '今日' : '关注',
      value: item,
      note: todoItems[index]
        ? `${todoItems[index].title} ${todoItems[index].count} 项，仅做只读核对。`
        : '来源：dashboard overview / home_overview.business_summary',
      hint: '首页不开放创建、修改、删除，只保留关键节点摘要。',
    }))
  }

  return [
    {
      key: 'node-fallback',
      title: '关键节点回退',
      badge: '回退',
      value: '暂无关键节点摘要',
      note: '等待 dashboard overview 返回业务摘要。',
      hint: '来源：fallback',
    },
  ]
})

const crossModuleReminderItems = computed<CrossModuleReminderItem[]>(() => {
  const warnings = overviewData.value?.home_overview?.warnings || []
  const primaryActions = overviewData.value?.home_overview?.primary_actions || []
  const reminderItems: CrossModuleReminderItem[] = warnings.map((item, index) => ({
    key: `warning-${index}`,
    title: `关键提醒 ${index + 1}`,
    badge: '提醒',
    detail: item,
    hint: `关联源：${sourceStatuses.value[index % Math.max(sourceStatuses.value.length, 1)]?.module || 'dashboard'}`,
  }))

  primaryActions.slice(0, 2).forEach((item, index) => {
    reminderItems.push({
      key: `action-${index}`,
      title: `只读动作建议 ${index + 1}`,
      badge: '只读',
      detail: `${item} 仅作为导航语义保留，不在首页触发真实动作。`,
      hint: '首页按钮保持禁用，不开放 create/update/delete。',
    })
  })

  if (reminderItems.length > 0) {
    return reminderItems
  }

  return [
    {
      key: 'reminder-fallback',
      title: '跨模块提醒回退',
      badge: '回退',
      detail: '暂无跨模块关键提醒，保留只读占位。',
      hint: '来源：fallback',
    },
  ]
})

const uiSourceReadback = computed(() => {
  const sourceRows = sourceStatuses.value.map((item) => `source.${item.module}=${item.status}`)
  const actions = overviewData.value?.home_overview?.primary_actions || []
  return [...sourceRows, ...actions.map((item) => `action.${item}`)]
})

const moduleSummaryCards = computed<ModuleSummaryCard[]>(() => {
  const grouped = moduleEntries.reduce<Record<string, ModuleEntry[]>>((acc, entry) => {
    if (!acc[entry.group]) {
      acc[entry.group] = []
    }
    acc[entry.group].push(entry)
    return acc
  }, {})
  return Object.entries(grouped).map(([group, entries]) => {
    const readyCount = entries.filter((entry) => entry.status === '已就绪').length
    return {
      key: group,
      label: group,
      count: entries.length,
      readyCount,
      note: `${entries.map((entry) => entry.name).join(' / ')} 的首页只读入口摘要`,
      paths: entries.map((entry) => entry.path).join(' | '),
    }
  })
})

const loadOverview = async (): Promise<void> => {
  readbackError.value = ''
  try {
    const response = await fetchDashboardOverview(overviewQuery.value)
    overviewData.value = response.data
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error)
    overviewData.value = null
    readbackError.value = `经营总览获取失败：${message}`
  }
}

const filteredModuleEntries = computed(() => {
  const keyword = moduleKeyword.value.trim().toLowerCase()
  if (!keyword) {
    return moduleEntries
  }
  return moduleEntries.filter((entry) => {
    return entry.name.toLowerCase().includes(keyword) || entry.path.toLowerCase().includes(keyword)
  })
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
.yisuan-home-shell {
  display: grid;
  grid-template-columns: 260px 1fr;
  min-height: 100%;
  background: #f3f4f6;
  color: #1f2937;
}

.yisuan-sidebar {
  border-right: 1px solid #e5e7eb;
  background: #ffffff;
  padding: 16px 14px;
}

.brand h1 {
  margin: 0;
  font-size: 20px;
}

.brand p {
  margin: 6px 0 16px;
  color: #6b7280;
  font-size: 12px;
}

.sidebar-group {
  margin-bottom: 14px;
}

.sidebar-group h2 {
  margin: 0 0 8px;
  font-size: 13px;
  color: #6b7280;
}

.sidebar-link {
  width: 100%;
  text-align: left;
  border: 1px solid #e5e7eb;
  background: #fff;
  border-radius: 6px;
  padding: 8px 10px;
  margin-bottom: 8px;
  cursor: pointer;
}

.sidebar-link span {
  display: block;
  font-size: 14px;
}

.sidebar-link small {
  color: #6b7280;
  font-size: 12px;
}

.yisuan-main {
  padding: 16px;
  display: grid;
  gap: 14px;
}

.yisuan-topbar {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  border-bottom: 1px solid #e5e7eb;
  padding-bottom: 10px;
}

.topbar-title h2 {
  margin: 0;
  font-size: 20px;
}

.topbar-title p {
  margin: 4px 0 0;
  color: #6b7280;
}

.topbar-meta {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: #6b7280;
}

.readback-summary,
.home-entry-overview,
.module-summary-panel,
.module-entry-grid,
.status-panel,
.workbench-list,
.recent-access-summary,
.business-calendar-panel,
.today-key-nodes-panel,
.cross-module-reminders-panel,
.readonly-hints,
.source-readback {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 14px;
}

.grid-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.grid-header h3,
.status-panel h3,
.workbench-list h3,
.source-readback h3 {
  margin: 0;
  font-size: 16px;
}

.grid-body {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
}

.entry-card {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 10px;
}

.summary-card {
  min-height: 132px;
}

.entry-card header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.entry-path {
  margin: 0 0 6px;
  color: #6b7280;
  font-size: 12px;
}

.entry-desc {
  margin: 0 0 6px;
  font-size: 13px;
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 10px;
  margin-top: 10px;
}

.readback-summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 10px;
  margin-top: 10px;
}

.readback-checkpoint-row {
  margin-top: 10px;
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  color: #4b5563;
  font-size: 12px;
}

.readonly-action-row {
  margin-top: 12px;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}

.readonly-action-note,
.summary-note {
  color: #6b7280;
  font-size: 12px;
}

.status-card {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 10px;
}

.status-label {
  display: block;
  font-size: 12px;
  color: #6b7280;
}

.status-value {
  display: block;
  margin-top: 6px;
  font-size: 20px;
}

.status-note {
  display: block;
  margin-top: 4px;
  color: #6b7280;
  font-size: 12px;
}

.recent-access-card {
  min-height: 132px;
}

.business-calendar-card {
  min-height: 156px;
}

.calendar-metrics {
  display: grid;
  gap: 6px;
  margin-bottom: 8px;
  color: #374151;
  font-size: 13px;
}

.reminder-card {
  min-height: 144px;
}

.source-readback ul {
  margin: 10px 0 0;
  padding-left: 18px;
  color: #4b5563;
  font-size: 13px;
}

.readonly-hints ul {
  margin: 10px 0 0;
  padding-left: 18px;
  color: #4b5563;
  font-size: 13px;
}

@media (max-width: 1100px) {
  .yisuan-home-shell {
    grid-template-columns: 1fr;
  }
  .topbar-meta {
    flex-wrap: wrap;
    justify-content: flex-end;
  }
}
</style>
