<template>
  <div class="reference-page" data-testid="cand017-reference-shell">
    <el-card shadow="never">
      <template #header>
        <div class="header-row" data-testid="cand017-reference-toolbar">
          <div class="title-group">
            <span class="title">客户引用档案查询</span>
            <span class="sub-title">NEXT-CAND-017 / references.customer readonly</span>
          </div>
          <div class="header-tags">
            <el-tag size="small" type="success" effect="plain">local-dev only</el-tag>
            <el-tag size="small" type="info" effect="plain">{{ sourceTagLabel }}</el-tag>
            <el-tag
              v-if="foundationCustomerParityHint"
              size="small"
              type="warning"
              effect="plain"
            >
              {{ foundationCustomerParityHint }}
            </el-tag>
          </div>
        </div>
      </template>

      <el-alert
        type="info"
        :closable="false"
        title="当前切片仅提供客户引用档案只读查询，不包含写入、回写、导出或草稿闭环。"
        class="scope-alert"
      />

      <section class="summary-grid" data-testid="cand017-reference-summary">
        <el-card shadow="never" class="summary-card">
          <span class="summary-label">客户总数</span>
          <strong class="summary-value">{{ filteredRows.length }}</strong>
        </el-card>
        <el-card shadow="never" class="summary-card">
          <span class="summary-label">启用客户</span>
          <strong class="summary-value">{{ activeCount }}</strong>
        </el-card>
        <el-card shadow="never" class="summary-card">
          <span class="summary-label">停用客户</span>
          <strong class="summary-value">{{ inactiveCount }}</strong>
        </el-card>
        <el-card shadow="never" class="summary-card">
          <span class="summary-label">当前入口</span>
          <strong class="summary-value">{{ parityScopeLabel }}</strong>
        </el-card>
      </section>

      <section class="filter-panel" data-testid="cand017-reference-filter">
        <el-form :inline="true" :model="query">
          <el-form-item label="关键字">
            <el-input
              v-model="query.keyword"
              clearable
              placeholder="客户编码 / 客户名称"
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
          <el-form-item>
            <el-button type="primary" :loading="loading" @click="refreshCustomers(true)">刷新</el-button>
            <el-button @click="resetQuery">重置</el-button>
          </el-form-item>
        </el-form>
      </section>

      <section class="readonly-readback" data-testid="cand017-reference-readonly-notes">
        <el-descriptions border :column="2">
          <el-descriptions-item label="route_scope">/sales-inventory/references</el-descriptions-item>
          <el-descriptions-item label="parity_route">/foundation/customer</el-descriptions-item>
          <el-descriptions-item label="data_source">{{ sourceTagLabel }}</el-descriptions-item>
          <el-descriptions-item label="last_loaded_at">{{ lastLoadedAt || '-' }}</el-descriptions-item>
          <el-descriptions-item label="readonly_scope">customer reference query</el-descriptions-item>
          <el-descriptions-item label="write_chain">disabled</el-descriptions-item>
        </el-descriptions>
      </section>

      <section class="table-panel" data-testid="cand017-reference-table">
        <el-table :data="filteredRows" border v-loading="loading" empty-text="当前筛选下暂无客户引用数据">
          <el-table-column prop="code" label="客户编码" min-width="180" />
          <el-table-column prop="name" label="客户名称" min-width="220" />
          <el-table-column label="状态" width="120">
            <template #default="{ row }">
              <el-tag :type="row.status === 'active' ? 'success' : 'info'" effect="plain">
                {{ row.status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="source" label="数据源" min-width="140" />
          <el-table-column prop="parityScope" label="parity" min-width="180" />
        </el-table>
      </section>

      <el-empty
        v-if="!loading && filteredRows.length === 0"
        description="当前筛选下暂无客户引用数据"
        data-testid="cand017-reference-empty"
      />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { fetchSalesInventoryCustomers, type CustomerItem } from '@/api/sales_inventory'

type CustomerStatus = 'active' | 'inactive'

interface CustomerReferenceRow {
  code: string
  name: string
  status: CustomerStatus
  source: string
  parityScope: string
}

const route = useRoute()
const loading = ref(false)
const rows = ref<CustomerReferenceRow[]>([])
const usingLocalFallback = ref(false)
const lastLoadedAt = ref('')

const query = reactive({
  keyword: '',
  status: '',
})

const localFallbackRows: CustomerReferenceRow[] = [
  {
    code: 'CUST-REF-001',
    name: '华东直营客户',
    status: 'active',
    source: 'local-fallback',
    parityScope: 'sales-inventory-references',
  },
  {
    code: 'CUST-REF-002',
    name: '华南分销客户',
    status: 'active',
    source: 'local-fallback',
    parityScope: 'foundation-customer',
  },
  {
    code: 'CUST-REF-003',
    name: '停用样例客户',
    status: 'inactive',
    source: 'local-fallback',
    parityScope: 'foundation-customer',
  },
]

const foundationCustomerParityHint = computed(() => {
  const parity = String(route.query.parity || '').trim().toLowerCase()
  return parity === 'foundation-customer' ? 'foundation-customer parity' : ''
})

const parityScopeLabel = computed(() => foundationCustomerParityHint.value || 'sales-inventory-references')
const sourceTagLabel = computed(() => (usingLocalFallback.value ? 'customer fallback' : 'erpnext readonly'))

const filteredRows = computed(() => {
  const keyword = query.keyword.trim().toLowerCase()
  const status = query.status.trim().toLowerCase()
  return rows.value.filter((row) => {
    if (status && row.status !== status) return false
    if (!keyword) return true
    return [row.code, row.name, row.parityScope].join('|').toLowerCase().includes(keyword)
  })
})

const activeCount = computed(() => filteredRows.value.filter((row) => row.status === 'active').length)
const inactiveCount = computed(() => filteredRows.value.filter((row) => row.status === 'inactive').length)

const normalizeRow = (item: CustomerItem): CustomerReferenceRow => ({
  code: item.name,
  name: item.customer_name?.trim() || item.name,
  status: item.disabled ? 'inactive' : 'active',
  source: 'erpnext',
  parityScope: foundationCustomerParityHint.value ? 'foundation-customer' : 'sales-inventory-references',
})

const setLoadedAt = (): void => {
  lastLoadedAt.value = new Date().toISOString()
}

const refreshCustomers = async (showToast = false): Promise<void> => {
  loading.value = true
  try {
    const response = await fetchSalesInventoryCustomers({ page: 1, page_size: 100 })
    const remoteRows = response.data.items.map(normalizeRow)
    if (remoteRows.length > 0) {
      rows.value = remoteRows
      usingLocalFallback.value = false
    } else {
      rows.value = localFallbackRows.map((row) => ({
        ...row,
        parityScope: foundationCustomerParityHint.value ? 'foundation-customer' : row.parityScope,
      }))
      usingLocalFallback.value = true
    }
    setLoadedAt()
    if (showToast) {
      ElMessage.success('客户引用数据已刷新')
    }
  } catch (error) {
    rows.value = localFallbackRows.map((row) => ({
      ...row,
      parityScope: foundationCustomerParityHint.value ? 'foundation-customer' : row.parityScope,
    }))
    usingLocalFallback.value = true
    setLoadedAt()
    if (showToast) {
      ElMessage.warning((error as Error).message || '客户引用接口不可用，已切换到本地只读回退视图')
    }
  } finally {
    loading.value = false
  }
}

const resetQuery = (): void => {
  query.keyword = ''
  query.status = ''
}

onMounted(() => {
  void refreshCustomers(false)
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

.header-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
}

.scope-alert,
.filter-panel,
.readonly-readback,
.table-panel {
  margin-top: 12px;
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
