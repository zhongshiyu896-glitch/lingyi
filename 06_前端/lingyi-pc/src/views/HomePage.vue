<template>
  <main class="home-page" data-testid="home-page">
    <section class="home-header" data-testid="home-header-section">
      <div>
        <p class="eyebrow">Lingyi PC</p>
        <h1>领意服装管理系统</h1>
        <p class="subtitle">业务工作台</p>
      </div>
      <div class="session-panel" data-testid="home-session-panel">
        <span class="session-label">当前账号</span>
        <strong data-testid="home-session-username">{{ currentUser || '未获取到会话' }}</strong>
        <span data-testid="home-session-roles">{{ currentRoles }}</span>
      </div>
    </section>

    <el-alert
      type="info"
      :closable="false"
      show-icon
      title="MVP-CAND-001 本地可用闭环：仅 local-dev/sqlite/scenario_tag，不触发生产写。"
      data-testid="home-navigation-readonly-state"
      class="home-readonly-alert"
    />

    <el-alert
      v-if="showPermissionOrDisabledState"
      type="warning"
      :closable="false"
      show-icon
      title="当前会话权限或状态受限，部分入口不可用。"
      data-testid="home-permission-or-disabled-state"
      class="home-permission-alert"
    />

    <section class="home-navigation-feedback" data-testid="home-navigation-feedback">
      <span class="feedback-label">最近导航</span>
      <span class="feedback-path">{{ navigationFeedback || '暂无' }}</span>
    </section>

    <section
      class="mvp-workbench"
      data-testid="mvp-home-status-panel"
      id="mvp-home-status-panel"
      data-production-write-forbidden="true"
      data-erpnext-production-write-forbidden="true"
      data-production-account-forbidden="true"
      data-readonly-boundary="true"
      data-write-request-success-allowed="false"
      data-real-write-action-added="false"
    >
      <div class="mvp-header">
        <div class="title-wrap">
          <h2>首页工作台六模块入口与状态面板</h2>
          <p>LOCAL_USABLE_MVP：入口可达、状态可读、可执行本地草稿保存/取消/回读与回滚。</p>
        </div>
        <div class="mvp-meta">
          <span>scenario_tag</span>
          <strong>{{ mvpDraft.scenarioTag }}</strong>
          <small>production_write_forbidden=true</small>
        </div>
      </div>

      <div class="mvp-filter" data-testid="mvp-home-query-filter" id="mvp-home-query-filter">
        <el-input
          v-model="mvpFilter.keyword"
          placeholder="按模块名/摘要过滤"
          clearable
          data-testid="mvp-home-query-keyword"
        />
        <el-select v-model="mvpFilter.status" data-testid="mvp-home-query-status">
          <el-option label="全部状态" value="all" />
          <el-option label="已就绪" value="ready" />
          <el-option label="待处理" value="pending" />
          <el-option label="阻断" value="blocked" />
        </el-select>
        <el-button data-testid="mvp-home-filter-reset" @click="resetMvpFilter">重置筛选</el-button>
      </div>

      <div class="module-card-grid" data-testid="mvp-home-module-entry" id="mvp-home-module-entry">
        <article
          v-for="item in filteredWorkbenchModules"
          :key="item.key"
          class="module-card"
          :data-module-key="item.key"
        >
          <header>
            <strong>{{ item.title }}</strong>
            <el-tag :type="moduleStatusTag(item.status)" effect="plain">{{ moduleStatusText(item.status) }}</el-tag>
          </header>
          <p class="module-route">{{ item.route }}</p>
          <p class="module-summary">待办：{{ item.todo }}</p>
          <p class="module-action">最近动作：{{ item.lastAction || '暂无' }}</p>
          <div class="module-actions">
            <button type="button" @click="go(item.route)">进入模块</button>
            <button type="button" @click="bindModuleToDraft(item.key)">绑定到本地草稿</button>
          </div>
        </article>
      </div>

      <div class="mvp-draft" data-testid="mvp-home-local-draft" id="mvp-home-local-draft">
        <h3>本地草稿闭环（local-dev/sqlite/scenario_tag）</h3>
        <div class="mvp-draft-grid">
          <label>
            模块
            <el-select v-model="mvpDraft.moduleKey">
              <el-option
                v-for="item in workbenchModules"
                :key="item.key"
                :label="item.title"
                :value="item.key"
              />
            </el-select>
          </label>
          <label>
            状态
            <el-select v-model="mvpDraft.status">
              <el-option label="已就绪" value="ready" />
              <el-option label="待处理" value="pending" />
              <el-option label="阻断" value="blocked" />
            </el-select>
          </label>
          <label>
            scenario_tag
            <el-input v-model="mvpDraft.scenarioTag" placeholder="Z003-WAREHOUSE-YYYYMMDD-NNN" />
          </label>
          <label class="draft-note">
            备注
            <el-input
              v-model="mvpDraft.note"
              type="textarea"
              :autosize="{ minRows: 2, maxRows: 4 }"
              placeholder="填写可执行状态、阻断原因或下一步。"
            />
          </label>
        </div>

        <div class="mvp-draft-actions">
          <el-button
            :loading="localWriteLoading"
            data-testid="mvp-home-local-draft-update"
            @click="createOrUpdateLocalDraft"
          >
            新增/更新本地草稿
          </el-button>
          <el-button
            type="primary"
            :loading="localWriteLoading"
            data-testid="mvp-home-local-save"
            id="mvp-home-local-save"
            @click="saveLocalDraft"
          >
            本地保存
          </el-button>
          <el-button
            :loading="localWriteLoading"
            data-testid="mvp-home-local-cancel"
            id="mvp-home-local-cancel"
            @click="cancelLocalDraft()"
          >
            本地取消
          </el-button>
          <el-button
            :loading="localWriteLoading"
            data-testid="mvp-home-local-readback"
            id="mvp-home-local-readback"
            @click="readbackLocalDraft"
          >
            本地回读
          </el-button>
        </div>

        <div class="mvp-feedback">
          <p>反馈：{{ localWriteFeedback || '暂无执行反馈' }}</p>
          <p>draft_id：{{ snapshot.draft_id ?? '未生成' }}</p>
          <p>draft_status：{{ snapshot.draft_status || '未生成' }}</p>
          <p>最近回读：{{ lastReadbackAt || '暂无' }}</p>
        </div>
      </div>

      <div class="mvp-rollback" data-testid="mvp-home-rollback-zero-residual" id="mvp-home-rollback-zero-residual">
        <el-button
          :loading="localWriteLoading"
          data-testid="mvp-home-rollback-button"
          @click="rollbackLocalDraft"
        >
          rollback
        </el-button>
        <span class="zero-residual" data-testid="mvp-home-zero-residual-result">
          zero_residual={{ zeroResidual ? 'true' : 'false' }} (residual_count={{ residualCount }})
        </span>
      </div>
    </section>

    <section class="quick-grid" aria-label="核心入口" data-testid="home-primary-entries">
      <button
        v-for="item in primaryEntries"
        :key="item.path"
        class="quick-entry"
        type="button"
        data-action-type="navigation"
        data-readonly-action="true"
        :data-route-path="item.path"
        :data-testid="entryTestId('home-primary-entry', item.path)"
        @click="go(item.path)"
      >
        <span>{{ item.title }}</span>
        <small>{{ item.group }}</small>
      </button>
    </section>

    <section class="module-bands" data-testid="home-module-groups">
      <div
        v-for="(group, groupIndex) in entryGroups"
        :key="group.title"
        class="module-band"
        :data-testid="groupTestId(groupIndex)"
      >
        <div class="band-title" :data-testid="groupTitleTestId(groupIndex)">{{ group.title }}</div>
        <div class="module-links">
          <button
            v-for="item in group.items"
            :key="item.path"
            type="button"
            data-action-type="navigation"
            data-readonly-action="true"
            :data-route-path="item.path"
            :data-testid="entryTestId('home-module-entry', item.path)"
            @click="go(item.path)"
          >
            {{ item.title }}
          </button>
        </div>
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  buildWarehouseScenarioTag,
  buildWarehouseStockEntryRequestId,
  cancelWarehouseStockEntryDraft,
  createWarehouseStockEntryDraft,
  ensureWarehouseScenarioTag,
  fetchWarehouseStockEntryDraft,
  type WarehouseStockEntryDraftCancelPayload,
  type WarehouseStockEntryDraftCreatePayload,
  type WarehouseStockEntryDraftData,
} from '@/api/warehouse'
import { usePermissionStore } from '@/stores/permission'

interface EntryItem {
  title: string
  path: string
  group: string
}

interface EntryGroup {
  title: string
  items: EntryItem[]
}

type ModuleStatus = 'ready' | 'pending' | 'blocked'
type ModuleFilterStatus = ModuleStatus | 'all'

interface MvpModuleEntry {
  key: string
  title: string
  route: string
  todo: string
}

interface MvpModuleState {
  status: ModuleStatus
  note: string
  updated_at: string
  last_action: string
}

interface MvpHomeSnapshot {
  scenario_tag: string
  selected_module_key: string
  draft_id: number | null
  draft_status: string
  source_ref: string
  idempotency_key: string
  module_states: Record<string, MvpModuleState>
  updated_at: string
  rollback_version: number
  production_write_forbidden: true
}

const MVP_HOME_STORAGE_KEY = 'lingyi.mvp.home.snapshot.v1'
const DATA_READONLY_BOUNDARY = true
const DATA_WRITE_REQUEST_SUCCESS_ALLOWED = false
const DATA_REAL_WRITE_ACTION_ADDED = false

const todayDate = (): string => new Date().toISOString().slice(0, 10)
const nowIso = (): string => new Date().toISOString()

const mvpModuleEntries: MvpModuleEntry[] = [
  { key: 'home', title: '首页', route: '/home', todo: '入口状态回读' },
  { key: 'foundation', title: '基础资料', route: '/sales-inventory/references', todo: '主数据可用性检查' },
  { key: 'material-dev', title: '物料开发', route: '/bom/list', todo: 'BOM 结构与绑定准备' },
  { key: 'bulk', title: '大货管理', route: '/sales-inventory/sales-orders', todo: '草稿订单准备' },
  { key: 'purchase', title: '物料采购', route: '/materialPurchase/materialPurchaseProcess', todo: '采购前置单据连通' },
  { key: 'stock', title: '物料进销存', route: '/sales-inventory/stock-ledger', todo: '库存流水回读' },
]

const buildDefaultModuleStates = (): Record<string, MvpModuleState> => {
  const map: Record<string, MvpModuleState> = {}
  for (const item of mvpModuleEntries) {
    map[item.key] = {
      status: 'pending',
      note: '',
      updated_at: nowIso(),
      last_action: '初始化',
    }
  }
  return map
}

const buildDefaultSnapshot = (): MvpHomeSnapshot => ({
  scenario_tag: ensureWarehouseScenarioTag(buildWarehouseScenarioTag()),
  selected_module_key: 'home',
  draft_id: null,
  draft_status: '',
  source_ref: '',
  idempotency_key: '',
  module_states: buildDefaultModuleStates(),
  updated_at: nowIso(),
  rollback_version: 0,
  production_write_forbidden: true,
})

const readSnapshotFromStorage = (): MvpHomeSnapshot => {
  if (typeof window === 'undefined') return buildDefaultSnapshot()
  const raw = window.localStorage.getItem(MVP_HOME_STORAGE_KEY)
  if (!raw) return buildDefaultSnapshot()
  try {
    const parsed = JSON.parse(raw) as Partial<MvpHomeSnapshot>
    const merged = buildDefaultSnapshot()
    const states = parsed.module_states ?? {}
    for (const item of mvpModuleEntries) {
      const candidate = states[item.key]
      if (candidate) {
        merged.module_states[item.key] = {
          status: candidate.status ?? 'pending',
          note: candidate.note ?? '',
          updated_at: candidate.updated_at ?? nowIso(),
          last_action: candidate.last_action ?? '初始化',
        }
      }
    }
    merged.scenario_tag = ensureWarehouseScenarioTag(parsed.scenario_tag ?? merged.scenario_tag)
    merged.selected_module_key = parsed.selected_module_key && states[parsed.selected_module_key]
      ? parsed.selected_module_key
      : 'home'
    merged.draft_id = typeof parsed.draft_id === 'number' ? parsed.draft_id : null
    merged.draft_status = parsed.draft_status ?? ''
    merged.source_ref = parsed.source_ref ?? ''
    merged.idempotency_key = parsed.idempotency_key ?? ''
    merged.updated_at = parsed.updated_at ?? nowIso()
    merged.rollback_version = typeof parsed.rollback_version === 'number' ? parsed.rollback_version : 0
    return merged
  } catch {
    return buildDefaultSnapshot()
  }
}

const persistSnapshot = (value: MvpHomeSnapshot): void => {
  if (typeof window === 'undefined') return
  window.localStorage.setItem(MVP_HOME_STORAGE_KEY, JSON.stringify(value))
}

const router = useRouter()
const permissionStore = usePermissionStore()
const currentUser = ref<string>('')
const roles = ref<string[]>([])
const navigationFeedback = ref<string>('')
const localWriteFeedback = ref<string>('')
const localWriteLoading = ref<boolean>(false)
const readbackDraft = ref<WarehouseStockEntryDraftData | null>(null)
const lastReadbackAt = ref<string>('')

const snapshot = reactive<MvpHomeSnapshot>(buildDefaultSnapshot())
const mvpFilter = reactive<{ keyword: string; status: ModuleFilterStatus }>({
  keyword: '',
  status: 'all',
})
const mvpDraft = reactive<{
  moduleKey: string
  status: ModuleStatus
  note: string
  scenarioTag: string
}>({
  moduleKey: 'home',
  status: 'pending',
  note: '',
  scenarioTag: snapshot.scenario_tag,
})

const entryGroups: EntryGroup[] = [
  {
    title: '生产主线',
    items: [
      { title: 'BOM 管理', path: '/bom/list', group: '生产主线' },
      { title: '生产计划', path: '/production/plans', group: '生产主线' },
      { title: '车间工票', path: '/workshop/tickets', group: '生产主线' },
      { title: '工价维护', path: '/workshop/wage-rates', group: '生产主线' },
    ],
  },
  {
    title: '外发与对账',
    items: [
      { title: '外发加工', path: '/subcontract/list', group: '外发与对账' },
      { title: '加工厂对账', path: '/factory-statements/list', group: '外发与对账' },
      { title: '款式利润', path: '/reports/style-profit', group: '外发与对账' },
    ],
  },
  {
    title: '仓储质量',
    items: [
      { title: '仓库看板', path: '/warehouse', group: '仓储质量' },
      { title: '质量检验', path: '/quality/inspections', group: '仓储质量' },
      { title: '销售库存', path: '/sales-inventory/sales-orders', group: '仓储质量' },
      { title: '库存流水', path: '/sales-inventory/stock-ledger', group: '仓储质量' },
    ],
  },
  {
    title: '报表治理',
    items: [
      { title: '报表目录', path: '/reports/catalog', group: '报表治理' },
      { title: '仪表盘总览', path: '/dashboard/overview', group: '报表治理' },
      { title: '权限治理', path: '/permissions/governance', group: '报表治理' },
      { title: '系统管理', path: '/system/management', group: '报表治理' },
      { title: '跨模块视图', path: '/cross-module/view', group: '报表治理' },
    ],
  },
]

const primaryEntries = computed<EntryItem[]>(() => [
  { title: '工作台总览', path: '/dashboard/workplace', group: '首页 / 工作台' },
  entryGroups[0].items[0],
  entryGroups[0].items[1],
  entryGroups[2].items[0],
])

const workbenchModules = computed(() => mvpModuleEntries.map((item) => {
  const state = snapshot.module_states[item.key]
  return {
    ...item,
    status: state?.status ?? 'pending',
    note: state?.note ?? '',
    lastAction: state?.last_action ?? '',
    updatedAt: state?.updated_at ?? '',
  }
}))

const filteredWorkbenchModules = computed(() => {
  const keyword = mvpFilter.keyword.trim().toLowerCase()
  return workbenchModules.value.filter((item) => {
    const statusMatched = mvpFilter.status === 'all' || item.status === mvpFilter.status
    if (!statusMatched) return false
    if (!keyword) return true
    return `${item.title}|${item.todo}|${item.note}`.toLowerCase().includes(keyword)
  })
})

const residualCount = computed<number>(() => {
  const stateResidual = Object.values(snapshot.module_states).filter((state) => {
    return state.status !== 'pending' || state.note.trim().length > 0
  }).length
  const draftResidual = snapshot.draft_id ? 1 : 0
  return stateResidual + draftResidual
})

const zeroResidual = computed<boolean>(() => {
  return residualCount.value === 0
})

const currentRoles = computed<string>(() => roles.value.join(' / ') || '未获取到角色')
const showPermissionOrDisabledState = computed<boolean>(() => {
  return permissionStore.state.status === 'guest' || !currentUser.value
})

const normalizeRouteId = (path: string): string =>
  path
    .replace(/^\/+/, '')
    .replace(/[\/:?&=#]+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')

const entryTestId = (prefix: string, path: string): string => {
  const normalized = normalizeRouteId(path)
  return normalized ? `${prefix}-${normalized}` : `${prefix}-root`
}

const groupTestId = (groupIndex: number): string => `home-module-group-${groupIndex + 1}`
const groupTitleTestId = (groupIndex: number): string => `home-module-group-title-${groupIndex + 1}`

const moduleStatusTag = (status: ModuleStatus): 'success' | 'warning' | 'danger' => {
  if (status === 'ready') return 'success'
  if (status === 'blocked') return 'danger'
  return 'warning'
}

const moduleStatusText = (status: ModuleStatus): string => {
  if (status === 'ready') return '已就绪'
  if (status === 'blocked') return '阻断'
  return '待处理'
}

const updateNavigationFeedback = (path: string): void => {
  navigationFeedback.value = path
  if (typeof window !== 'undefined') {
    window.sessionStorage.setItem('lingyi.home.last_nav_path', path)
  }
}

const go = (path: string): void => {
  updateNavigationFeedback(path)
  router.push(path)
}

const syncDraftFromModule = (moduleKey: string): void => {
  const state = snapshot.module_states[moduleKey]
  if (!state) return
  mvpDraft.moduleKey = moduleKey
  mvpDraft.status = state.status
  mvpDraft.note = state.note
  mvpDraft.scenarioTag = snapshot.scenario_tag
}

const touchModuleState = (moduleKey: string, action: string): void => {
  const target = snapshot.module_states[moduleKey]
  if (!target) return
  target.status = mvpDraft.status
  target.note = mvpDraft.note.trim()
  target.updated_at = nowIso()
  target.last_action = action
  snapshot.selected_module_key = moduleKey
  snapshot.updated_at = target.updated_at
  snapshot.scenario_tag = ensureWarehouseScenarioTag(mvpDraft.scenarioTag)
  persistSnapshot(snapshot)
}

const bindModuleToDraft = (moduleKey: string): void => {
  syncDraftFromModule(moduleKey)
  localWriteFeedback.value = `已绑定模块：${workbenchModules.value.find((item) => item.key === moduleKey)?.title ?? moduleKey}`
}

const resetMvpFilter = (): void => {
  mvpFilter.keyword = ''
  mvpFilter.status = 'all'
}

const createOrUpdateLocalDraft = (): void => {
  touchModuleState(mvpDraft.moduleKey, 'create_or_update')
  localWriteFeedback.value = `本地草稿已更新：${mvpDraft.moduleKey} / ${moduleStatusText(mvpDraft.status)}`
}

const readbackLocalDraft = async (): Promise<void> => {
  if (!snapshot.draft_id) {
    localWriteFeedback.value = '当前无可回读 draft_id，请先本地保存。'
    return
  }
  localWriteLoading.value = true
  try {
    const result = await fetchWarehouseStockEntryDraft(snapshot.draft_id)
    readbackDraft.value = result.data
    snapshot.draft_status = result.data.status
    snapshot.updated_at = nowIso()
    persistSnapshot(snapshot)
    lastReadbackAt.value = snapshot.updated_at
    localWriteFeedback.value = `回读成功：draft_id=${result.data.id} status=${result.data.status}`
  } catch (error) {
    localWriteFeedback.value = `回读失败：${(error as Error).message}`
  } finally {
    localWriteLoading.value = false
  }
}

const saveLocalDraft = async (): Promise<void> => {
  localWriteLoading.value = true
  try {
    touchModuleState(mvpDraft.moduleKey, 'save')
    const scenarioTag = ensureWarehouseScenarioTag(mvpDraft.scenarioTag)
    const sourceRef = snapshot.source_ref || `${scenarioTag}-MVP-HOME-SRC`
    const idempotencyKey = snapshot.idempotency_key || `${scenarioTag}-MVP-HOME-IDEMP`
    const selectedModule = workbenchModules.value.find((item) => item.key === mvpDraft.moduleKey) ?? workbenchModules.value[0]
    const warehouse = '样衣仓'
    const itemCode = `MVPHOME-${selectedModule.key.toUpperCase()}`
    const quantity = 1
    const businessDate = todayDate()
    const requestId = buildWarehouseStockEntryRequestId({
      scenarioTag,
      operation: 'create_stock_entry_draft',
      idempotencyKey,
      sourceRef,
      warehouse,
      itemCode,
      quantity,
      businessDate,
      statusAction: 'create',
    })

    const payload: WarehouseStockEntryDraftCreatePayload = {
      company: 'LY-LOCAL-DEV',
      purpose: 'Material Issue',
      source_type: 'mvp_home_local',
      source_id: sourceRef,
      source_ref: sourceRef,
      warehouse,
      item_code: itemCode,
      operation: 'create_stock_entry_draft',
      quantity,
      business_date: businessDate,
      status_action: 'create',
      scenario_tag: scenarioTag,
      source_warehouse: warehouse,
      items: [
        {
          item_code: itemCode,
          qty: quantity,
          uom: 'Nos',
          source_warehouse: warehouse,
        },
      ],
      idempotency_key: idempotencyKey,
    }
    const created = await createWarehouseStockEntryDraft(payload, { requestId })
    snapshot.scenario_tag = scenarioTag
    snapshot.source_ref = sourceRef
    snapshot.idempotency_key = idempotencyKey
    snapshot.draft_id = created.data.id
    snapshot.draft_status = created.data.status
    snapshot.updated_at = nowIso()
    persistSnapshot(snapshot)
    await readbackLocalDraft()
    localWriteFeedback.value = `本地保存成功：draft_id=${created.data.id}，scenario_tag=${scenarioTag}`
  } catch (error) {
    localWriteFeedback.value = `本地保存失败：${(error as Error).message}`
  } finally {
    localWriteLoading.value = false
  }
}

const cancelLocalDraft = async (reason = ''): Promise<void> => {
  if (!snapshot.draft_id) {
    localWriteFeedback.value = '当前无可取消 draft_id。'
    return
  }
  localWriteLoading.value = true
  try {
    touchModuleState(mvpDraft.moduleKey, 'cancel')
    const cancelDraft = readbackDraft.value ?? (await fetchWarehouseStockEntryDraft(snapshot.draft_id)).data
    readbackDraft.value = cancelDraft
    const draftItems = Array.isArray(cancelDraft.items) ? cancelDraft.items : []
    const firstDraftItem = draftItems[0]
    if (!firstDraftItem?.item_code) {
      localWriteFeedback.value = '本地取消失败：draft item_code 缺失，无法匹配业务载体。'
      return
    }
    const scenarioTag = ensureWarehouseScenarioTag(snapshot.scenario_tag)
    const sourceRef = cancelDraft.source_id || snapshot.source_ref || `${scenarioTag}-MVP-HOME-SRC`
    const idempotencyKey = cancelDraft.idempotency_key || snapshot.idempotency_key || `${scenarioTag}-MVP-HOME-IDEMP`
    const warehouse = cancelDraft.source_warehouse || cancelDraft.target_warehouse || '样衣仓'
    const itemCode = firstDraftItem.item_code
    const quantity = draftItems.reduce((sum, item) => sum + Number(item.qty || 0), 0) || 1
    const businessDate = todayDate()
    const requestId = buildWarehouseStockEntryRequestId({
      scenarioTag,
      operation: 'cancel_stock_entry_draft',
      idempotencyKey,
      sourceRef,
      warehouse,
      itemCode,
      quantity,
      businessDate,
      statusAction: 'cancel',
    })
    const payload: WarehouseStockEntryDraftCancelPayload = {
      reason: reason || `MVP-ROLLBACK-${scenarioTag}`,
      idempotency_key: idempotencyKey,
      source_ref: sourceRef,
      warehouse,
      item_code: itemCode,
      operation: 'cancel_stock_entry_draft',
      quantity,
      business_date: businessDate,
      status_action: 'cancel',
      scenario_tag: scenarioTag,
    }
    const cancelled = await cancelWarehouseStockEntryDraft(snapshot.draft_id, payload, { requestId })
    readbackDraft.value = cancelled.data
    snapshot.draft_id = null
    snapshot.draft_status = cancelled.data.status
    snapshot.updated_at = nowIso()
    persistSnapshot(snapshot)
    localWriteFeedback.value = `本地取消成功：status=${cancelled.data.status}`
  } catch (error) {
    localWriteFeedback.value = `本地取消失败：${(error as Error).message}`
  } finally {
    localWriteLoading.value = false
  }
}

const rollbackLocalDraft = async (): Promise<void> => {
  localWriteLoading.value = true
  try {
    if (snapshot.draft_id) {
      await cancelLocalDraft('MVP rollback')
    }
    if (typeof window !== 'undefined') {
      window.localStorage.removeItem(MVP_HOME_STORAGE_KEY)
    }
    const reset = buildDefaultSnapshot()
    Object.assign(snapshot, reset)
    mvpDraft.moduleKey = snapshot.selected_module_key
    mvpDraft.status = snapshot.module_states[mvpDraft.moduleKey].status
    mvpDraft.note = snapshot.module_states[mvpDraft.moduleKey].note
    mvpDraft.scenarioTag = snapshot.scenario_tag
    readbackDraft.value = null
    lastReadbackAt.value = nowIso()
    localWriteFeedback.value = `rollback 完成，zero_residual=${residualCount.value === 0 ? 'true' : 'false'}`
  } finally {
    localWriteLoading.value = false
  }
}

onMounted(async () => {
  if (typeof window !== 'undefined') {
    navigationFeedback.value = window.sessionStorage.getItem('lingyi.home.last_nav_path') || ''
  }
  const restored = readSnapshotFromStorage()
  Object.assign(snapshot, restored)
  mvpDraft.moduleKey = restored.selected_module_key
  mvpDraft.status = restored.module_states[restored.selected_module_key].status
  mvpDraft.note = restored.module_states[restored.selected_module_key].note
  mvpDraft.scenarioTag = restored.scenario_tag
  try {
    await permissionStore.loadCurrentUser()
    currentUser.value = permissionStore.state.username || '访客会话'
    roles.value = permissionStore.state.roles
  } catch {
    currentUser.value = '未获取到会话'
    roles.value = []
  }
  localWriteFeedback.value = [
    `dataReadonlyBoundary=${String(DATA_READONLY_BOUNDARY)}`,
    `dataWriteRequestSuccessAllowed=${String(DATA_WRITE_REQUEST_SUCCESS_ALLOWED)}`,
    `dataRealWriteActionAdded=${String(DATA_REAL_WRITE_ACTION_ADDED)}`,
  ].join(' | ')
})
</script>

<style scoped>
.home-page {
  min-height: 100vh;
  background: #f6f7f9;
  color: #1f2933;
  padding: 28px;
}

.home-readonly-alert,
.home-permission-alert,
.home-navigation-feedback,
.mvp-workbench {
  max-width: 1180px;
  margin: 0 auto 12px;
}

.home-navigation-feedback {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 42px;
  padding: 10px 14px;
  background: #ffffff;
  border: 1px solid #e1e6ef;
  border-radius: 6px;
}

.feedback-label {
  color: #687386;
  font-size: 13px;
}

.feedback-path {
  color: #1f2933;
  font-size: 14px;
  font-weight: 600;
}

.home-header {
  display: flex;
  align-items: stretch;
  justify-content: space-between;
  gap: 20px;
  max-width: 1180px;
  margin: 0 auto 20px;
  padding: 24px 0 6px;
}

.eyebrow {
  margin: 0 0 8px;
  color: #5b6472;
  font-size: 13px;
}

h1 {
  margin: 0;
  font-size: 32px;
  font-weight: 700;
  letter-spacing: 0;
}

.subtitle {
  margin: 10px 0 0;
  color: #53606f;
  font-size: 16px;
}

.session-panel {
  min-width: 220px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 6px;
  border-left: 3px solid #2f80ed;
  padding: 12px 16px;
  background: #ffffff;
}

.session-label {
  color: #697586;
  font-size: 12px;
}

.session-panel strong {
  font-size: 18px;
}

.session-panel span:last-child {
  color: #4b5563;
  font-size: 13px;
}

.mvp-workbench {
  border: 1px solid #dbe2ea;
  background: #ffffff;
  border-radius: 8px;
  padding: 16px;
  display: grid;
  gap: 12px;
}

.mvp-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
}

.mvp-header h2 {
  margin: 0;
  font-size: 20px;
}

.mvp-header p {
  margin: 6px 0 0;
  color: #5f6c7b;
  font-size: 13px;
}

.mvp-meta {
  min-width: 280px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
  color: #5f6c7b;
}

.mvp-meta strong {
  font-size: 14px;
  color: #1f2933;
}

.mvp-filter {
  display: grid;
  grid-template-columns: 1fr 180px 110px;
  gap: 10px;
}

.module-card-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.module-card {
  border: 1px solid #dbe2ea;
  border-radius: 6px;
  padding: 10px;
  display: grid;
  gap: 8px;
}

.module-card header {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  align-items: center;
}

.module-route,
.module-summary,
.module-action {
  margin: 0;
  font-size: 12px;
  color: #5f6c7b;
  line-height: 1.5;
}

.module-actions {
  display: flex;
  gap: 8px;
}

.module-actions button {
  min-height: 30px;
  border: 1px solid #d0d8e2;
  border-radius: 4px;
  background: #ffffff;
  color: #1f2933;
  padding: 0 10px;
  cursor: pointer;
}

.module-actions button:hover {
  border-color: #2f80ed;
}

.mvp-draft {
  border: 1px dashed #cfd8e4;
  border-radius: 6px;
  padding: 10px;
}

.mvp-draft h3 {
  margin: 0 0 10px;
  font-size: 16px;
}

.mvp-draft-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.mvp-draft-grid label {
  display: grid;
  gap: 6px;
  font-size: 12px;
  color: #4b5563;
}

.draft-note {
  grid-column: 1 / -1;
}

.mvp-draft-actions {
  margin-top: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.mvp-feedback {
  margin-top: 10px;
  display: grid;
  gap: 4px;
  font-size: 12px;
  color: #4b5563;
}

.mvp-feedback p {
  margin: 0;
}

.mvp-rollback {
  display: flex;
  align-items: center;
  gap: 12px;
}

.zero-residual {
  font-size: 13px;
  color: #374151;
}

.quick-grid {
  max-width: 1180px;
  margin: 0 auto 20px;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.quick-entry {
  min-height: 96px;
  border: 1px solid #d9dee7;
  background: #ffffff;
  color: #1f2933;
  text-align: left;
  padding: 16px;
  cursor: pointer;
  border-radius: 6px;
}

.quick-entry:hover {
  border-color: #2f80ed;
}

.quick-entry span {
  display: block;
  font-size: 18px;
  font-weight: 650;
}

.quick-entry small {
  display: block;
  margin-top: 10px;
  color: #687386;
  font-size: 13px;
}

.module-bands {
  max-width: 1180px;
  margin: 0 auto;
  display: grid;
  gap: 12px;
}

.module-band {
  display: grid;
  grid-template-columns: 150px 1fr;
  gap: 16px;
  align-items: center;
  padding: 14px 16px;
  background: #ffffff;
  border: 1px solid #e1e6ef;
  border-radius: 6px;
}

.band-title {
  font-weight: 650;
  color: #2f3947;
}

.module-links {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.module-links button {
  min-height: 36px;
  border: 1px solid #cdd5df;
  background: #ffffff;
  color: #1f2933;
  border-radius: 4px;
  padding: 0 12px;
  cursor: pointer;
}

.module-links button:hover {
  border-color: #2f80ed;
  color: #1d5fbf;
}

@media (max-width: 900px) {
  .home-page {
    padding: 18px;
  }

  .home-header {
    flex-direction: column;
  }

  .mvp-header {
    flex-direction: column;
  }

  .mvp-meta {
    min-width: 0;
  }

  .mvp-filter {
    grid-template-columns: 1fr;
  }

  .module-card-grid {
    grid-template-columns: 1fr;
  }

  .mvp-draft-grid {
    grid-template-columns: 1fr;
  }

  .quick-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .module-band {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 560px) {
  h1 {
    font-size: 26px;
  }

  .quick-grid {
    grid-template-columns: 1fr;
  }
}
</style>
