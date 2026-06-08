<template>
  <div class="reference-page" data-testid="cand532-reference-shell">
    <el-card shadow="never">
      <template #header>
        <div class="header-row" data-testid="cand532-reference-toolbar">
          <div class="title-group">
            <span class="title">{{ pageTitle }}</span>
            <span class="sub-title">NEXT-CAND-532 / sales inventory stock-source guard readonly</span>
          </div>
          <div class="header-actions">
            <div class="header-tags">
              <el-tag size="small" type="success" effect="plain">local-dev only</el-tag>
              <el-tag size="small" type="info" effect="plain">{{ sourceTagLabel }}</el-tag>
              <el-tag
                v-if="readonlyParityHint"
                size="small"
                type="warning"
                effect="plain"
              >
                {{ readonlyParityHint }}
              </el-tag>
            </div>
            <div class="guarded-actions" data-testid="cand532-reference-guarded-actions">
              <el-button
                disabled
                data-action-type="write"
                data-guard-state="disabled"
              >
                客户维护
              </el-button>
              <el-button
                disabled
                data-action-type="write"
                data-guard-state="disabled"
              >
                供应商维护
              </el-button>
              <el-button
                disabled
                data-action-type="write"
                data-guard-state="disabled"
              >
                导入引用
              </el-button>
            </div>
          </div>
        </div>
      </template>

      <el-alert
        type="info"
        :closable="false"
        title="当前切片仅提供 stock-source guard / source-status 只读核对，不开放客户/供应商维护、导入、导出、库存写入、ERPNext 或后台修复。"
        class="scope-alert"
      />

      <section class="summary-grid" data-testid="cand532-reference-summary">
        <el-card shadow="never" class="summary-card">
          <span class="summary-label">当前档案数</span>
          <strong class="summary-value">{{ filteredRows.length }}</strong>
        </el-card>
        <el-card shadow="never" class="summary-card">
          <span class="summary-label">启用档案</span>
          <strong class="summary-value">{{ activeCount }}</strong>
        </el-card>
        <el-card shadow="never" class="summary-card">
          <span class="summary-label">停用档案</span>
          <strong class="summary-value">{{ inactiveCount }}</strong>
        </el-card>
        <el-card shadow="never" class="summary-card">
          <span class="summary-label">当前入口</span>
          <strong class="summary-value">{{ parityScopeLabel }}</strong>
        </el-card>
      </section>

      <el-tabs
        v-model="activeTab"
        class="reference-tabs"
        data-testid="cand532-reference-tabs"
        @tab-change="handleTabChange"
      >
        <el-tab-pane label="客户引用档案" name="customers" />
        <el-tab-pane label="供应商引用档案" name="suppliers" />
      </el-tabs>

      <section class="filter-panel" data-testid="cand532-reference-filter">
        <el-form :inline="true" :model="query">
          <el-form-item label="关键字">
            <el-input
              v-model="query.keyword"
              clearable
              :placeholder="keywordPlaceholder"
              style="width: 260px"
            />
          </el-form-item>
          <el-form-item label="状态">
            <el-select v-model="query.status" clearable placeholder="全部" style="width: 140px">
              <el-option label="全部" value="" />
              <el-option label="active" value="active" />
              <el-option label="inactive" value="inactive" />
            </el-select>
          </el-form-item>
          <el-form-item label="来源">
            <el-select v-model="query.source" clearable placeholder="全部" style="width: 160px">
              <el-option label="全部" value="" />
              <el-option label="erpnext" value="erpnext" />
              <el-option label="local-fallback" value="local-fallback" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="loading" @click="refreshReferences(true)">刷新</el-button>
            <el-button @click="resetQuery">重置</el-button>
          </el-form-item>
        </el-form>
      </section>

      <section class="readonly-readback" data-testid="cand532-reference-readonly-notes">
        <el-descriptions border :column="2">
          <el-descriptions-item label="route_scope">/sales-inventory/references</el-descriptions-item>
          <el-descriptions-item label="parity_route">{{ parityScopeLabel }}</el-descriptions-item>
          <el-descriptions-item label="active_tab">{{ activeTabLabel }}</el-descriptions-item>
          <el-descriptions-item label="data_source">{{ sourceTagLabel }}</el-descriptions-item>
          <el-descriptions-item label="last_loaded_at">{{ lastLoadedAt || '-' }}</el-descriptions-item>
          <el-descriptions-item label="write_chain">customer-supplier write / import / export / stock-write disabled</el-descriptions-item>
        </el-descriptions>
      </section>

      <SalesInventoryStockSourceGuardReadonly :summary="stockSourceGuardReadonlySummary" />

      <section class="table-panel" data-testid="cand532-reference-table">
        <el-table
          :data="filteredRows"
          border
          v-loading="loading"
          :empty-text="emptyText"
        >
          <el-table-column prop="code" label="引用编码" min-width="180" />
          <el-table-column prop="name" label="引用名称" min-width="220" />
          <el-table-column label="引用类型" width="120">
            <template #default="{ row }">
              <el-tag :type="row.referenceType === 'customers' ? 'primary' : 'warning'" effect="plain">
                {{ row.referenceType === 'customers' ? '客户' : '供应商' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="120">
            <template #default="{ row }">
              <el-tag :type="row.status === 'active' ? 'success' : 'info'" effect="plain">
                {{ row.status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="数据源" min-width="200">
            <template #default="{ row }">
              <div class="row-tags">
                <el-tag :type="row.source === 'erpnext' ? 'success' : 'warning'" effect="plain">
                  {{ row.source }}
                </el-tag>
                <el-tag
                  :type="row.sourceValidationState === 'verified' ? 'success' : row.sourceValidationState === 'fallback' ? 'warning' : 'danger'"
                  effect="plain"
                >
                  {{ row.readonlySourceTag }}
                </el-tag>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="parityScope" label="入口来源" min-width="180" />
          <el-table-column label="缺失来源提示" min-width="220">
            <template #default="{ row }">
              <span>{{ row.missingSourcePrompt || '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="动作" width="140" align="center">
            <template #default>
              <el-button
                text
                disabled
                data-action-type="write"
                data-guard-state="disabled"
              >
                维护
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </section>

      <el-empty
        v-if="!loading && filteredRows.length === 0"
        :description="emptyText"
        data-testid="cand532-reference-empty"
      />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  filterReferenceRows,
  loadSalesInventoryReferenceRows,
  resolveReferenceTab,
  type SalesInventoryReferenceRow,
  type SalesInventoryReferenceTab,
} from '@/api/sales_inventory_references'
import SalesInventoryStockSourceGuardReadonly from '@/views/sales_inventory/components/SalesInventoryStockSourceGuardReadonly.vue'
import { useSalesInventoryStockSourceGuardReadonly } from '@/views/sales_inventory/composables/useSalesInventoryStockSourceGuardReadonly'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const rows = ref<SalesInventoryReferenceRow[]>([])
const usingFallback = ref(false)
const lastLoadedAt = ref('')
const activeTab = ref<SalesInventoryReferenceTab>(resolveReferenceTab(route.query.tab, route.query.parity))

const query = reactive({
  keyword: '',
  status: '',
  source: '',
})

const routeTabValue = computed(() => {
  const raw = route.query.tab
  return Array.isArray(raw) ? raw[0] : raw
})
const parityValue = computed(() => String(route.query.parity || '').trim().toLowerCase())
const focusValue = computed(() => String(route.query.focus || '').trim().toLowerCase())
const readonlyParityHint = computed(() => {
  if (parityValue.value === 'foundation-reference') return 'foundation-reference parity'
  if (parityValue.value === 'foundation-customer') return 'foundation-customer parity'
  if (parityValue.value === 'foundation-supplier') return 'foundation-supplier parity'
  return ''
})
const parityScopeLabel = computed(() => readonlyParityHint.value || 'sales-inventory-references')
const pageTitle = computed(() => (activeTab.value === 'customers' ? '客户引用来源守卫核对' : '供应商引用来源守卫核对'))
const activeTabLabel = computed(() => (activeTab.value === 'customers' ? 'customers' : 'suppliers'))
const keywordPlaceholder = computed(() =>
  activeTab.value === 'customers' ? '客户编码 / 客户名称' : '供应商编码 / 供应商名称',
)
const emptyText = computed(() =>
  activeTab.value === 'customers' ? '当前筛选下暂无客户引用数据' : '当前筛选下暂无供应商引用数据',
)
const filteredRows = computed(() => filterReferenceRows(rows.value, query))
const activeCount = computed(() => filteredRows.value.filter((row) => row.status === 'active').length)
const inactiveCount = computed(() => filteredRows.value.filter((row) => row.status === 'inactive').length)
const filterStateLabel = computed(
  () =>
    `keyword=${query.keyword.trim() || '-'}; status=${query.status || 'all'}; source=${query.source || 'all'}`,
)
const { stockSourceGuardReadonlySummary } = useSalesInventoryStockSourceGuardReadonly({
    rows: filteredRows,
    activeTab,
    currentPath: computed(() => route.path),
    tab: routeTabValue,
    parity: parityValue,
    focus: focusValue,
    filterStateLabel,
    usingFallback,
    canRead: computed(() => true),
  })
const sourceTagLabel = computed(() => stockSourceGuardReadonlySummary.value.sourceStatusLabel)

const setLoadedAt = (): void => {
  lastLoadedAt.value = new Date().toISOString()
}

const refreshReferences = async (showToast = false): Promise<void> => {
  loading.value = true
  try {
    const result = await loadSalesInventoryReferenceRows(activeTab.value, parityValue.value)
    rows.value = result.rows
    usingFallback.value = result.usingFallback
    setLoadedAt()
    if (showToast) {
      if (result.usingFallback) {
        ElMessage.warning(`${activeTab.value === 'customers' ? '客户' : '供应商'}引用数据已切换到本地只读回退视图`)
      } else {
        ElMessage.success(`${activeTab.value === 'customers' ? '客户' : '供应商'}引用数据已刷新`)
      }
    }
  } finally {
    loading.value = false
  }
}

const resetQuery = (): void => {
  query.keyword = ''
  query.status = ''
  query.source = ''
}

const syncTabFromRoute = (): void => {
  activeTab.value = resolveReferenceTab(route.query.tab, route.query.parity)
}

const handleTabChange = async (tabName: string | number): Promise<void> => {
  const nextTab: SalesInventoryReferenceTab = tabName === 'suppliers' ? 'suppliers' : 'customers'
  const nextParity =
    parityValue.value === 'foundation-customer' || parityValue.value === 'foundation-supplier'
      ? nextTab === 'customers'
        ? 'foundation-customer'
        : 'foundation-supplier'
      : undefined
  await router.replace({
    path: '/sales-inventory/references',
    query: {
      tab: nextTab,
      ...(nextParity ? { parity: nextParity } : {}),
    },
  })
}

watch(
  () => [route.query.tab, route.query.parity],
  () => {
    syncTabFromRoute()
    resetQuery()
    void refreshReferences(false)
  },
)

onMounted(() => {
  syncTabFromRoute()
  void refreshReferences(false)
})
</script>

<style scoped>
.reference-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.title-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.title {
  font-size: 16px;
  font-weight: 600;
}

.sub-title {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.header-actions {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 8px;
}

.header-tags,
.guarded-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
}

.scope-alert,
.reference-tabs,
.filter-panel,
.readonly-readback,
.table-panel {
  margin-top: 12px;
}

.row-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.summary-grid {
  margin-top: 12px;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
}

.summary-card {
  min-height: 84px;
}

.summary-label {
  display: block;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  margin-bottom: 8px;
}

.summary-value {
  font-size: 20px;
  line-height: 1;
}
</style>
