<template>
  <div class="dashboard-overview-page" data-testid="dashboard-overview-page">
    <el-card shadow="never">
      <template #header>
        <div class="header-row">
          <div class="title-wrap">
            <h2>大货管理 / 大货看板</h2>
            <span class="subtitle">报价单到工厂合同质检流程看板（只读首版）</span>
          </div>
          <div class="header-actions">
            <el-select v-model="selectedBoard" aria-label="大货看板" style="width: 170px" data-testid="dashboard-overview-board-select">
              <el-option label="大货看板" value="kanban" />
            </el-select>
            <el-button
              type="primary"
              :loading="loading"
              :disabled="!canRead"
              data-testid="dashboard-overview-search-button"
              @click="onSearch"
            >
              搜索
            </el-button>
          </div>
        </div>
      </template>

      <el-form :inline="true" :model="query" class="query-form" data-testid="dashboard-overview-filter-form">
        <el-form-item label="关键词">
          <el-input
            v-model="query.keyword"
            clearable
            placeholder="请输入"
            aria-label="请输入"
            data-testid="dashboard-overview-keyword-input"
          />
        </el-form-item>
        <el-form-item label="开始时间">
          <el-date-picker
            v-model="query.from_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="开始时间"
            clearable
            data-testid="dashboard-overview-from-date-input"
          />
        </el-form-item>
        <el-form-item label="结束时间">
          <el-date-picker
            v-model="query.to_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="结束时间"
            clearable
            data-testid="dashboard-overview-to-date-input"
          />
        </el-form-item>
        <el-form-item
          data-testid="dashboard-overview-write-guard"
          data-write-guard="true"
          data-guard-state="guarded_readonly"
        >
          <el-button data-testid="dashboard-overview-reset-button" @click="resetQuery">重置</el-button>
          <el-button data-write-guard="true" @click="guardedAction('清空')">清空</el-button>
          <el-button data-write-guard="true" @click="guardedAction('确定')">确定</el-button>
          <el-button data-write-guard="true" @click="guardedAction('标志已读')">标志已读</el-button>
          <el-button data-write-guard="true" @click="guardedAction('删除消息')">删除消息</el-button>
          <el-button data-write-guard="true" @click="guardedAction('新增消息')">新增消息</el-button>
          <el-button data-write-guard="true" @click="guardedAction('保存')">保存</el-button>
        </el-form-item>
      </el-form>

      <el-alert
        v-if="!permissionReady"
        type="info"
        :closable="false"
        title="权限信息加载中"
        show-icon
        class="state-alert"
        data-testid="dashboard-overview-permission-loading"
      />
      <el-alert
        v-else-if="!canRead"
        type="warning"
        :closable="false"
        title="当前账号无大货看板读取权限，仅展示受限界面"
        show-icon
        class="state-alert"
        data-testid="dashboard-overview-permission-state"
      />
      <el-alert
        v-if="errorMessage"
        type="error"
        :closable="false"
        :title="`大货看板数据加载失败：${errorMessage}`"
        show-icon
        class="state-alert"
        data-testid="dashboard-overview-error-state"
      />
      <el-alert
        v-if="canRead && !canWrite"
        type="info"
        :closable="false"
        title="当前仅开放只读模式，写动作按钮已受控"
        show-icon
        class="state-alert"
        data-testid="dashboard-overview-disabled-state"
      />
      <el-alert
        v-if="flowFeedback"
        type="info"
        :closable="false"
        :title="flowFeedback"
        class="state-alert"
        data-testid="dashboard-overview-flow-feedback"
      />

      <div class="home-enhanced-section" data-testid="dashboard-overview-home-section">
        <div class="section-header">
          <div class="title-wrap">
            <h3>{{ homeOverview.summary_title }}</h3>
            <span class="subtitle">首页 / 经营总览增强（P1）</span>
          </div>
          <div class="header-actions">
            <el-button :disabled="!canRead" data-testid="dashboard-overview-refresh-button" @click="refreshOverview">刷新指标</el-button>
            <el-button :disabled="!canRead" data-write-guard="true" @click="guardedAction('导出概览')">导出概览</el-button>
            <el-button :disabled="!canRead" data-write-guard="true" @click="guardedAction('新增待办')">新增待办</el-button>
          </div>
        </div>

        <el-empty v-if="homeEnhancedEmpty" description="暂无首页增强数据，请调整筛选条件后重试" />

        <template v-else>
          <div class="metrics-grid" data-testid="dashboard-overview-metrics-grid">
            <div v-for="card in homeOverview.metric_cards" :key="card.key" class="metric-card">
              <span class="metric-label">{{ card.label }}</span>
              <span class="metric-value">{{ card.value }}{{ card.unit ?? '' }}</span>
              <span class="metric-trend">{{ card.trend ?? '—' }}</span>
            </div>
          </div>

          <div class="home-summary-grid" data-testid="dashboard-overview-summary-grid">
            <el-card shadow="never" class="summary-panel">
              <template #header>
                <span>待办/预警</span>
              </template>
              <div class="todo-list">
                <div v-for="item in homeOverview.todo_items" :key="item.key" class="todo-item">
                  <span class="todo-title">{{ item.title }}</span>
                  <el-tag :type="todoStatusTag(item.status)" effect="plain">{{ item.count }}</el-tag>
                  <el-button link type="primary" @click="guardedAction(item.action_label)">{{ item.action_label }}</el-button>
                </div>
              </div>
            </el-card>

            <el-card shadow="never" class="summary-panel">
              <template #header>
                <span>经营概览</span>
              </template>
              <ul class="summary-list">
                <li v-for="line in homeOverview.business_summary" :key="line">{{ line }}</li>
              </ul>
              <ul class="warning-list">
                <li v-for="line in homeOverview.warnings" :key="line">{{ line }}</li>
              </ul>
            </el-card>
          </div>

          <el-card shadow="never" class="summary-panel">
            <template #header>
              <span>最近业务动态</span>
            </template>
            <ul class="activity-list">
              <li v-for="line in homeOverview.recent_activities" :key="line">{{ line }}</li>
            </ul>
          </el-card>

          <el-card shadow="never" class="summary-panel trend-panel">
            <template #header>
              <span>销售预测趋势</span>
            </template>
            <el-table :data="homeOverview.trend_points" border empty-text="暂无趋势数据">
              <el-table-column prop="period" label="周期" width="90" />
              <el-table-column prop="forecast_sales" label="预测销售额" min-width="120" />
              <el-table-column prop="forecast_cost" label="预测成本" min-width="120" />
              <el-table-column prop="forecast_profit" label="预测利润" min-width="120" />
            </el-table>
          </el-card>
        </template>
      </div>

      <div class="quick-filter-row" data-testid="dashboard-overview-quick-filters">
        <el-tag
          v-for="item in boardData.quick_filters"
          :key="item"
          effect="plain"
          size="large"
        >
          {{ item }}
        </el-tag>
      </div>

      <div class="flow-board" data-testid="dashboard-overview-flow-board">
        <div class="flow-row">
          <FlowNodeCard
            :node="materialNode"
            @open-route="openFlowRoute"
          />
          <span class="arrow">→</span>
          <FlowNodeCard
            :node="bulkFollowupNode"
            @open-route="openFlowRoute"
          />
        </div>
        <div class="flow-row">
          <FlowNodeCard
            :node="quoteNode"
            @open-route="openFlowRoute"
          />
          <span class="arrow">→</span>
          <FlowNodeCard
            :node="orderNode"
            @open-route="openFlowRoute"
          />
          <span class="arrow">→</span>
          <FlowNodeCard
            :node="productionOrderNode"
            @open-route="openFlowRoute"
          />
          <span class="arrow">→</span>
          <FlowNodeCard
            :node="factoryContractNode"
            @open-route="openFlowRoute"
          />
          <span class="arrow">→</span>
          <FlowNodeCard
            :node="qcNode"
            @open-route="openFlowRoute"
          />
        </div>
        <div class="flow-row">
          <FlowNodeCard
            :node="accessoryNode"
            @open-route="openFlowRoute"
          />
          <span class="arrow">→</span>
          <FlowNodeCard
            :node="costNode"
            @open-route="openFlowRoute"
          />
        </div>
      </div>

      <el-table
        :data="filteredMessages"
        border
        v-loading="loading"
        empty-text="暂无大货看板数据，请调整筛选条件后重试"
        data-testid="dashboard-overview-message-table"
      >
        <el-table-column label="图片" width="70">
          <template #default>
            <div class="image-placeholder">图</div>
          </template>
        </el-table-column>
        <el-table-column prop="order_no" label="订单号" min-width="120" />
        <el-table-column prop="customer" label="客户" min-width="110" />
        <el-table-column prop="style_no" label="款号" min-width="100" />
        <el-table-column prop="style_name" label="款名" min-width="100" />
        <el-table-column prop="ordered_qty" label="下单数量" width="90" align="right" />
        <el-table-column prop="overdue" label="超期" width="80" />
        <el-table-column prop="sun" label="日" width="56" />
        <el-table-column prop="mon" label="一" width="56" />
        <el-table-column prop="tue" label="二" width="56" />
        <el-table-column prop="wed" label="三" width="56" />
        <el-table-column prop="thu" label="四" width="56" />
        <el-table-column prop="fri" label="五" width="56" />
        <el-table-column prop="sat" label="六" width="56" />
        <el-table-column prop="title" label="标题" min-width="120" />
        <el-table-column prop="sent_at" label="发送时间" min-width="140" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="messageStatusTag(row.status)" effect="plain">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="sender" label="发送人" min-width="100" />
        <el-table-column label="详情" width="88" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" data-testid="dashboard-overview-detail-button" @click="openDetail(row)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty
        v-if="!loading && !errorMessage && filteredMessages.length === 0"
        description="暂无消息数据"
        data-testid="dashboard-overview-empty-state"
      />

      <el-drawer
        v-model="detailVisible"
        title="消息详情（只读）"
        size="480px"
        append-to-body
        data-testid="dashboard-overview-detail-drawer"
      >
        <template v-if="detailRow">
          <el-descriptions :column="1" border>
            <el-descriptions-item label="订单号">{{ detailRow.order_no }}</el-descriptions-item>
            <el-descriptions-item label="客户">{{ detailRow.customer }}</el-descriptions-item>
            <el-descriptions-item label="款号">{{ detailRow.style_no }}</el-descriptions-item>
            <el-descriptions-item label="款名">{{ detailRow.style_name }}</el-descriptions-item>
            <el-descriptions-item label="标题">{{ detailRow.title }}</el-descriptions-item>
            <el-descriptions-item label="发送时间">{{ detailRow.sent_at }}</el-descriptions-item>
            <el-descriptions-item label="发送人">{{ detailRow.sender }}</el-descriptions-item>
            <el-descriptions-item label="状态">{{ detailRow.status }}</el-descriptions-item>
          </el-descriptions>
        </template>
        <el-empty v-else description="暂无详情" />
      </el-drawer>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, defineComponent, h, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElTag, ElTooltip } from 'element-plus'
import { useRouter } from 'vue-router'
import {
  fetchDashboardOverview,
  type DashboardHomeOverviewData,
  type DashboardKanbanData,
  type DashboardKanbanFlowNode,
  type DashboardKanbanMessageRow,
  type DashboardOverviewData,
} from '@/api/dashboard'
import { usePermissionStore } from '@/stores/permission'

const LOCAL_ERROR_TOKEN = '__error__'
const permissionStore = usePermissionStore()
const router = useRouter()

const permissionReady = ref<boolean>(false)
const loading = ref<boolean>(false)
const selectedBoard = ref<'kanban'>('kanban')
const overview = ref<DashboardOverviewData | null>(null)
const errorMessage = ref<string>('')
const flowFeedback = ref<string>('')
const detailVisible = ref<boolean>(false)
const detailRow = ref<DashboardKanbanMessageRow | null>(null)

const query = reactive({
  company: '样衣制造',
  keyword: '',
  from_date: '',
  to_date: '',
})

const localSeedBoard: DashboardKanbanData = {
  board_name: '大货看板',
  quick_filters: ['物料类型', '物料单位', '客户画像', '加工厂画像', '供应商画像', '样板单', '设计打样', '跟进模板', '大货看板'],
  flow_nodes: [
    { key: 'quote', label: '报价单', status: 'completed', route: '/sales-inventory/sales-orders' },
    { key: 'order', label: '订单', status: 'active', route: '/sales-inventory/sales-orders' },
    { key: 'production_order', label: '生产制单', status: 'active', route: '/production/plans' },
    { key: 'material', label: '面料', status: 'normal', route: '/production/plans' },
    { key: 'bulk_followup', label: '大货跟进', status: 'active', route: '/production/plans' },
    { key: 'factory_contract', label: '工厂合同', status: 'normal', route: '/subcontract/list' },
    { key: 'qc', label: '工厂合同质检', status: 'normal', route: '/quality/inspections' },
    { key: 'accessory', label: '辅料/包材', status: 'normal', route: '/production/plans' },
    { key: 'cost', label: '大货成本核算', status: 'normal', route: '/reports/style-profit' },
  ],
  flow_links: [
    { from_key: 'quote', to_key: 'order' },
    { from_key: 'order', to_key: 'production_order' },
    { from_key: 'production_order', to_key: 'factory_contract' },
    { from_key: 'factory_contract', to_key: 'qc' },
    { from_key: 'material', to_key: 'bulk_followup' },
    { from_key: 'accessory', to_key: 'cost' },
  ],
  messages: [
    {
      order_no: 'SO-240601-001',
      customer: '华东客户A',
      style_no: 'L-1001',
      style_name: '春夏T恤',
      ordered_qty: 1200,
      overdue: '否',
      sun: '',
      mon: '',
      tue: '',
      wed: '',
      thu: '',
      fri: '',
      sat: '',
      title: '订单已下发',
      sent_at: '2026-05-03 09:30',
      status: '已读',
      sender: '跟单员A',
    },
    {
      order_no: 'SO-240601-002',
      customer: '华南客户B',
      style_no: 'D-2030',
      style_name: '连衣裙',
      ordered_qty: 860,
      overdue: '是',
      sun: '',
      mon: '',
      tue: '',
      wed: '',
      thu: '',
      fri: '',
      sat: '',
      title: '请确认面料到仓',
      sent_at: '2026-05-03 10:15',
      status: '待处理',
      sender: '跟单员B',
    },
  ],
}

const localSeedHomeOverview: DashboardHomeOverviewData = {
  summary_title: '首页经营总览（P1）',
  metric_cards: [
    { key: 'inspection_count', label: '质检单量', value: '0', unit: '单', trend: '等待数据加载' },
    { key: 'inventory_qty', label: '库存总量', value: '0', unit: '件', trend: '等待数据加载' },
    { key: 'quality_pass_rate', label: '质检通过率', value: '0', unit: '%', trend: '等待数据加载' },
    { key: 'warehouse_alerts', label: '仓储预警', value: '0', unit: '条', trend: '等待数据加载' },
  ],
  todo_items: [
    { key: 'pending_messages', title: '待处理动态', count: 0, status: 'normal', action_label: '查看动态' },
    { key: 'overdue_orders', title: '超期订单', count: 0, status: 'normal', action_label: '查看跟进' },
    { key: 'warehouse_warning', title: '仓储预警', count: 0, status: 'normal', action_label: '查看仓储' },
  ],
  warnings: ['写入类动作在本地首版保持受控，不触发真实提交。', '导出/下载/打印在本页仅提供语义按钮。'],
  business_summary: ['质检通过率 0%', '低于安全库存款号 0 个', '低于补货线款号 0 个', '仓储高危预警 0 条'],
  recent_activities: ['暂无业务动态'],
  trend_points: [
    { period: 'W1', forecast_sales: 0, forecast_cost: 0, forecast_profit: 0 },
    { period: 'W2', forecast_sales: 0, forecast_cost: 0, forecast_profit: 0 },
    { period: 'W3', forecast_sales: 0, forecast_cost: 0, forecast_profit: 0 },
    { period: 'W4', forecast_sales: 0, forecast_cost: 0, forecast_profit: 0 },
  ],
  primary_actions: ['查看动态', '刷新指标', '导出概览'],
}

const canRead = computed<boolean>(() => permissionStore.state.actions.includes('dashboard:read'))
const canWrite = computed<boolean>(() => permissionStore.state.actions.includes('dashboard:write'))

const boardData = computed<DashboardKanbanData>(() => overview.value?.kanban ?? localSeedBoard)
const homeOverview = computed<DashboardHomeOverviewData>(() => overview.value?.home_overview ?? localSeedHomeOverview)
const homeEnhancedEmpty = computed<boolean>(() => query.keyword.trim() === '__home_empty__')

const resolveNode = (
  key: string,
  label: string,
  fallbackRoute: string | null = null,
): DashboardKanbanFlowNode => {
  const matched = boardData.value.flow_nodes.find((node) => node.key === key)
  return matched ?? { key, label, status: 'normal', route: fallbackRoute }
}

const quoteNode = computed<DashboardKanbanFlowNode>(() =>
  resolveNode('quote', '报价单', '/sales-inventory/sales-orders'),
)
const orderNode = computed<DashboardKanbanFlowNode>(() =>
  resolveNode('order', '订单', '/sales-inventory/sales-orders'),
)
const productionOrderNode = computed<DashboardKanbanFlowNode>(() =>
  resolveNode('production_order', '生产制单', '/production/plans'),
)
const materialNode = computed<DashboardKanbanFlowNode>(() =>
  resolveNode('material', '面料', '/production/plans'),
)
const bulkFollowupNode = computed<DashboardKanbanFlowNode>(() =>
  resolveNode('bulk_followup', '大货跟进', '/production/plans'),
)
const factoryContractNode = computed<DashboardKanbanFlowNode>(() =>
  resolveNode('factory_contract', '工厂合同', '/subcontract/list'),
)
const qcNode = computed<DashboardKanbanFlowNode>(() =>
  resolveNode('qc', '工厂合同质检', '/quality/inspections'),
)
const accessoryNode = computed<DashboardKanbanFlowNode>(() =>
  resolveNode('accessory', '辅料/包材', '/production/plans'),
)
const costNode = computed<DashboardKanbanFlowNode>(() =>
  resolveNode('cost', '大货成本核算', '/reports/style-profit'),
)

const filteredMessages = computed<DashboardKanbanMessageRow[]>(() => {
  const keyword = query.keyword.trim().toLowerCase()
  if (!keyword || keyword === LOCAL_ERROR_TOKEN) {
    return boardData.value.messages
  }
  return boardData.value.messages.filter((row) => {
    const source = `${row.order_no}|${row.customer}|${row.style_no}|${row.style_name}|${row.title}`.toLowerCase()
    return source.includes(keyword)
  })
})

const messageStatusTag = (value: string): 'success' | 'warning' | 'info' => {
  if (value === '已读') return 'success'
  if (value === '待处理') return 'warning'
  return 'info'
}

const todoStatusTag = (value: string): 'success' | 'warning' | 'danger' | 'info' => {
  if (value === 'urgent') return 'danger'
  if (value === 'warning') return 'warning'
  if (value === 'normal') return 'success'
  return 'info'
}

const guardedAction = (actionName: string): void => {
  flowFeedback.value = `${actionName} 为受控动作，仅反馈不执行写入`
  ElMessage.warning(`${actionName} 为受控动作，本地首版保持只读`)
}

const resetQuery = async (): Promise<void> => {
  query.keyword = ''
  query.from_date = ''
  query.to_date = ''
  errorMessage.value = ''
  flowFeedback.value = '筛选条件已重置，已执行只读刷新'
  await loadOverview('reset')
}

const onSearch = async (): Promise<void> => {
  flowFeedback.value = '已执行搜索请求'
  await loadOverview('search')
}

const refreshOverview = async (): Promise<void> => {
  flowFeedback.value = '已刷新经营指标'
  await loadOverview('refresh')
}

const loadOverview = async (_source: 'search' | 'reset' | 'refresh' | 'mounted' = 'search'): Promise<void> => {
  if (!canRead.value) {
    ElMessage.warning('当前账号无大货看板读取权限')
    return
  }
  if (query.keyword.trim() === LOCAL_ERROR_TOKEN) {
    errorMessage.value = '本地模拟错误：请移除 __error__ 关键字后重试'
    return
  }
  loading.value = true
  try {
    const result = await fetchDashboardOverview({
      company: query.company,
      keyword: query.keyword.trim() || undefined,
      from_date: query.from_date || undefined,
      to_date: query.to_date || undefined,
    })
    overview.value = result.data
    errorMessage.value = ''
  } catch (error) {
    errorMessage.value = (error as Error).message
  } finally {
    loading.value = false
  }
}

const openFlowRoute = async (route: string | null | undefined): Promise<void> => {
  if (!route) {
    flowFeedback.value = '流程节点无可跳转页面，已受控'
    guardedAction('流程入口')
    return
  }
  flowFeedback.value = `流程节点只读跳转：${route}`
  const from = router.currentRoute.value.fullPath
  try {
    await router.push(route)
  } catch {
    // ignored: keep local fallback below
  }
  if (router.currentRoute.value.fullPath === from) {
    await router.push({
      path: '/dashboard/overview',
      query: {
        flow_entry: route,
        nonce: String(Date.now()),
      },
    })
  }
}

const openDetail = async (row: DashboardKanbanMessageRow): Promise<void> => {
  if (!canRead.value) {
    ElMessage.warning('当前账号无详情读取权限')
    return
  }
  detailRow.value = row
  detailVisible.value = true
  flowFeedback.value = `已打开只读详情：${row.order_no}`
}

onMounted(async () => {
  try {
    await permissionStore.loadCurrentUser()
    await permissionStore.loadModuleActions('dashboard')
  } catch (error) {
    errorMessage.value = (error as Error).message
  } finally {
    permissionReady.value = true
  }
})

const FlowNodeCard = defineComponent({
  name: 'FlowNodeCard',
  props: {
    node: {
      type: Object as () => DashboardKanbanFlowNode,
      required: true,
    },
  },
  emits: ['open-route'],
  setup(props, { emit }) {
    const statusText = computed<string>(() => {
      if (props.node.status === 'completed') return '已完成'
      if (props.node.status === 'active') return '进行中'
      return '待处理'
    })
    const statusType = computed<'success' | 'warning' | 'info'>(() => {
      if (props.node.status === 'completed') return 'success'
      if (props.node.status === 'active') return 'warning'
      return 'info'
    })

    return () =>
      h('div', { class: ['flow-node', `flow-node--${props.node.status}`] }, [
        h(ElTag, { type: statusType.value, effect: 'plain', size: 'small' }, () => statusText.value),
        h('div', { class: 'flow-node__label' }, props.node.label),
        props.node.route
          ? h(
              ElTooltip,
              { content: '进入该流程页面', placement: 'top' },
              () =>
                h(
                  'button',
                  {
                    class: 'flow-node__link',
                    onClick: () => emit('open-route', props.node.route),
                  },
                  '进入',
                ),
            )
          : h(
              ElTooltip,
              { content: '当前节点无可跳转页面', placement: 'top' },
              () =>
                h(
                  'button',
                  {
                    class: ['flow-node__link', 'is-disabled'],
                    type: 'button',
                    disabled: true,
                  },
                  '进入',
                ),
            ),
      ])
  },
})
</script>

<style scoped>
.dashboard-overview-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.title-wrap h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.subtitle {
  display: inline-block;
  margin-top: 4px;
  color: #6b7280;
  font-size: 13px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.query-form {
  margin-bottom: 8px;
}

.state-alert {
  margin-bottom: 10px;
}

.home-enhanced-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 12px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
}

.section-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.metric-card {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #ffffff;
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.metric-label {
  color: #6b7280;
  font-size: 12px;
}

.metric-value {
  font-size: 20px;
  font-weight: 600;
  color: #111827;
}

.metric-trend {
  color: #64748b;
  font-size: 12px;
}

.home-summary-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.summary-panel {
  border-radius: 8px;
}

.todo-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.todo-item {
  display: grid;
  grid-template-columns: 1fr auto auto;
  gap: 8px;
  align-items: center;
}

.todo-title {
  color: #374151;
  font-size: 13px;
}

.summary-list,
.warning-list,
.activity-list {
  margin: 0;
  padding-left: 18px;
  color: #374151;
  font-size: 13px;
  display: grid;
  gap: 6px;
}

.warning-list {
  margin-top: 10px;
}

.trend-panel :deep(.el-table) {
  margin-top: 2px;
}

.quick-filter-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.flow-board {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 12px;
  margin-bottom: 12px;
  background: #f8fafc;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}

.flow-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.arrow {
  color: #9ca3af;
  font-size: 16px;
  line-height: 1;
}

.flow-node {
  width: 136px;
  min-height: 86px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  background: #fff;
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: flex-start;
}

.flow-node--active {
  border-color: #f59e0b;
}

.flow-node--completed {
  border-color: #16a34a;
}

.flow-node__label {
  font-size: 14px;
  font-weight: 500;
}

.flow-node__link {
  font-size: 12px;
  color: #2563eb;
  background: transparent;
  border: none;
  padding: 0;
  cursor: pointer;
}

.flow-node__link.is-disabled {
  color: #9ca3af;
  cursor: not-allowed;
}

.image-placeholder {
  width: 34px;
  height: 34px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #64748b;
  background: #f1f5f9;
  font-size: 12px;
}
</style>
