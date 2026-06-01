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
          <h3>本地状态汇总（readback-only）</h3>
          <el-tag effect="plain" type="info">scenario_tag={{ readbackScenarioTag }}</el-tag>
        </div>
        <el-alert
          v-if="readbackError"
          type="warning"
          :closable="false"
          :title="readbackError"
          data-testid="cand006-home-readback-error"
        />
        <div v-else class="readback-summary-grid">
          <article v-for="item in readbackSummaryModules" :key="item.module_key" class="status-card">
            <span class="status-label">{{ item.module_label }}</span>
            <strong class="status-value">{{ item.record_count }}</strong>
            <small class="status-note">{{ item.source_endpoint }}</small>
          </article>
        </div>
        <div class="readback-checkpoint-row">
          <span>homepage_readback_summary_success={{ homepageReadbackSummarySuccess ? 'true' : 'false' }}</span>
          <span>workspace_redirect_readback_success={{ workspaceRedirectReadbackSuccess ? 'true' : 'false' }}</span>
          <span>write_requests_observed_count={{ readbackWriteRequestsObservedCount }}</span>
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

      <section class="status-panel" data-testid="yisuan-1to1-home-status-panel">
        <h3>任务/状态/异常</h3>
        <div class="status-grid">
          <article v-for="item in statusCards" :key="item.label" class="status-card">
            <span class="status-label">{{ item.label }}</span>
            <strong class="status-value">{{ item.value }}</strong>
            <small class="status-note">{{ item.note }}</small>
          </article>
        </div>
      </section>

      <section class="workbench-list" data-testid="yisuan-1to1-home-workbench-list">
        <h3>工作台队列</h3>
        <el-table :data="workbenchRows" border empty-text="暂无任务">
          <el-table-column prop="task" label="任务" min-width="180" />
          <el-table-column prop="owner" label="负责人" width="120" />
          <el-table-column prop="deadline" label="截止日期" width="140" />
          <el-table-column prop="priority" label="优先级" width="110" />
          <el-table-column prop="status" label="状态" width="120" />
        </el-table>
      </section>

      <section class="source-readback" data-testid="yisuan-1to1-ui-source-readback">
        <h3>UI Source Readback</h3>
        <ul>
          <li v-for="item in uiSourceReadback" :key="item">{{ item }}</li>
        </ul>
      </section>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { request } from '@/api/request'

interface NavItem {
  name: string
  path: string
}

interface NavGroup {
  title: string
  items: NavItem[]
}

interface ModuleEntry extends NavItem {
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

const router = useRouter()
const route = useRoute()
const moduleKeyword = ref('')

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
    module_count: number
    total_records: number
    readback_success_count: number
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
  checkpoints: Array<{
    checkpoint_key: string
    status: string
    final_path?: string
  }>
  workspace_redirect: {
    route: string
    final_path: string
    readback_success: boolean
  }
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
  { name: '基础资料', path: '/sales-inventory/references', desc: '款号、客户、供应商基础信息', status: '已就绪' },
  { name: 'BOM 物料开发', path: '/bom/list', desc: 'BOM 列表与明细对齐', status: '已就绪' },
  { name: '大货订单', path: '/sales-inventory/sales-orders', desc: '订单草稿与计划联动', status: '已就绪' },
  { name: '采购外协', path: '/subcontract/list?parity=material-purchase', desc: '前置单据与明细追踪', status: '已就绪' },
  { name: '库存管理', path: '/sales-inventory/stock-ledger', desc: '库存流水与仓库摘要', status: '已就绪' },
  { name: '仓库看板', path: '/warehouse', desc: '仓库概况与盘点入口', status: '对齐中' },
]

const statusCards: StatusCard[] = [
  { label: '今日待办', value: '12', note: '采购、排产、验货分发' },
  { label: '异常提醒', value: '3', note: '交期偏差与库存差异' },
  { label: '审批中', value: '7', note: '单据等待审批' },
  { label: '快捷操作', value: '5', note: '常用入口保持可达' },
]

const workbenchRows: WorkbenchRow[] = [
  { task: '销售订单交期核对', owner: '李敏', deadline: '2026-06-02', priority: '高', status: '处理中' },
  { task: '生产计划差异复核', owner: '周宁', deadline: '2026-06-03', priority: '中', status: '待处理' },
  { task: '采购明细补全', owner: '王涛', deadline: '2026-06-04', priority: '中', status: '处理中' },
  { task: '库存盘点预警回看', owner: '陈悦', deadline: '2026-06-05', priority: '低', status: '待处理' },
]

const uiSourceReadback = [
  'yisuan_incremental_capture/sidebar_modules/01_首页.png',
  'yisuan_business_shadow_capture/G0_baseline_20260518/module_entry_baseline.json',
  'task_z014b_01_a001_a006_contract_candidate_pool.json',
  'G2_FIX20/developer_allowed_reference_map.json',
  'task_z007b_17_module_entry_to_list_route_parity_evidence.json',
]

const readbackError = ref('')
const readbackSummary = ref<ReadbackSummaryResponse | null>(null)
const readbackCheckpoints = ref<ReadbackCheckpointsResponse | null>(null)

const readbackScenarioTag = computed(() => {
  const raw = Array.isArray(route.query.scenario_tag) ? route.query.scenario_tag[0] : route.query.scenario_tag
  return String(raw || '').trim() || 'REALOBJ-CAND006-READBACK-001'
})

const readbackSummaryModules = computed(() => readbackSummary.value?.modules || [])
const readbackWriteRequestsObservedCount = computed(
  () => Number(readbackSummary.value?.totals?.write_requests_observed_count ?? 0),
)
const homepageReadbackSummarySuccess = computed(() => {
  if (!readbackSummary.value) return false
  return readbackSummary.value.readback_only && readbackSummaryModules.value.length > 0
})
const workspaceRedirectReadbackSuccess = computed(() => {
  const redirect = readbackCheckpoints.value?.workspace_redirect
  if (!redirect) return false
  return redirect.final_path === '/dashboard/overview' && redirect.readback_success === true
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
  void loadReadbackSummary()
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
.module-entry-grid,
.status-panel,
.workbench-list,
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

.source-readback ul {
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
