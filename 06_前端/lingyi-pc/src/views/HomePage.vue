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
      title="首页导航为只读演示；写动作入口统一禁用或拦截。"
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
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
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

const router = useRouter()
const permissionStore = usePermissionStore()
const currentUser = ref<string>('')
const roles = ref<string[]>([])
const navigationFeedback = ref<string>('')

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
    title: '衣算云入口映射（只读）',
    items: [
      { title: '衣算云首页', path: '/dashboard/workplace', group: '衣算云入口映射（只读）' },
      { title: '基础资料/客户', path: '/foundation/customer', group: '衣算云入口映射（只读）' },
      { title: '基础资料/供应商', path: '/foundation/supplier', group: '衣算云入口映射（只读）' },
      { title: '基础资料/加工厂', path: '/foundation/factory', group: '衣算云入口映射（只读）' },
      { title: '物料开发/面料', path: '/material/materialFabric', group: '衣算云入口映射（只读）' },
      { title: '商品企划/物料小样', path: '/goodsPlan/materialSamples', group: '衣算云入口映射（只读）' },
      { title: '设计打样/样板单', path: '/sample/sampleListV2', group: '衣算云入口映射（只读）' },
      { title: '大货管理/订单', path: '/production/productOrder', group: '衣算云入口映射（只读）' },
      { title: '物料采购/采购流程', path: '/materialPurchase/materialPurchaseProcess', group: '衣算云入口映射（只读）' },
      { title: '库存/物料库存', path: '/materialStock/materialTypeStock', group: '衣算云入口映射（只读）' },
      { title: '库存/成品库存', path: '/productStock/productStockList', group: '衣算云入口映射（只读）' },
      { title: '财务/客户应收', path: '/financial/financialReport/customerReconciliationReport', group: '衣算云入口映射（只读）' },
      { title: '报表/加工成品库存', path: '/reportManage/collaborationReport/factoryProductStockReport', group: '衣算云入口映射（只读）' },
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
  entryGroups[0].items[0],
  entryGroups[0].items[1],
  entryGroups[2].items[0],
  entryGroups[3].items[1],
])

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

onMounted(async () => {
  if (typeof window !== 'undefined') {
    navigationFeedback.value = window.sessionStorage.getItem('lingyi.home.last_nav_path') || ''
  }
  try {
    await permissionStore.loadCurrentUser()
    currentUser.value = permissionStore.state.username || '访客会话'
    roles.value = permissionStore.state.roles
  } catch {
    currentUser.value = '未获取到会话'
    roles.value = []
  }
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
.home-navigation-feedback {
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
