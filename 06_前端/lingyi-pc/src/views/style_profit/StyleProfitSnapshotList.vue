<template>
  <div class="style-profit-list-page">
    <el-card shadow="never">
      <template #header>
        <div class="header-row">
          <span>款式利润快照列表</span>
        </div>
      </template>

      <el-form :inline="true" :model="query">
        <el-form-item label="公司">
          <el-input v-model="query.company" clearable placeholder="company" />
        </el-form-item>
        <el-form-item label="款式">
          <el-input v-model="query.item_code" clearable placeholder="item_code" />
        </el-form-item>
        <el-form-item label="销售订单">
          <el-input v-model="query.sales_order" clearable placeholder="sales_order" />
        </el-form-item>
        <el-form-item label="开始日期">
          <el-date-picker
            v-model="query.from_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="from_date"
            clearable
          />
        </el-form-item>
        <el-form-item label="结束日期">
          <el-date-picker
            v-model="query.to_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="to_date"
            clearable
          />
        </el-form-item>
        <el-form-item label="快照状态">
          <el-select v-model="query.snapshot_status" clearable style="width: 140px">
            <el-option label="complete" value="complete" />
            <el-option label="incomplete" value="incomplete" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :disabled="!canRead" @click="loadRows">查询</el-button>
        </el-form-item>
      </el-form>

      <el-empty v-if="!canRead" description="无款式利润查看权限" />
      <template v-else>
        <el-table :data="rows" border v-loading="loading">
          <el-table-column prop="snapshot_no" label="快照号" min-width="180" />
          <el-table-column prop="company" label="公司" min-width="130" />
          <el-table-column prop="item_code" label="款式" min-width="130" />
          <el-table-column prop="sales_order" label="销售订单" min-width="150" />
          <el-table-column label="期间" min-width="190">
            <template #default="scope">
              {{ scope.row.from_date || '-' }} ~ {{ scope.row.to_date || '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="revenue_status" label="收入口径" width="110" />
          <el-table-column label="收入金额" width="130">
            <template #default="scope">{{ formatAmount(scope.row.revenue_amount) }}</template>
          </el-table-column>
          <el-table-column label="实际总成本" width="130">
            <template #default="scope">{{ formatAmount(scope.row.actual_total_cost) }}</template>
          </el-table-column>
          <el-table-column label="利润金额" width="130">
            <template #default="scope">{{ formatAmount(scope.row.profit_amount) }}</template>
          </el-table-column>
          <el-table-column label="利润率" width="110">
            <template #default="scope">{{ formatProfitRate(scope.row.profit_rate) }}</template>
          </el-table-column>
          <el-table-column label="状态" min-width="150">
            <template #default="scope">
              <el-tag :type="scope.row.snapshot_status === 'complete' ? 'success' : 'warning'">
                {{ scope.row.snapshot_status }}
              </el-tag>
              <el-tag v-if="scope.row.unresolved_count > 0" type="danger" class="warn-tag">
                unresolved={{ scope.row.unresolved_count }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="创建时间" min-width="180" />
          <el-table-column label="操作" width="100" fixed="right">
            <template #default="scope">
              <el-button link type="primary" @click="goDetail(scope.row.id)">详情</el-button>
            </template>
          </el-table-column>
        </el-table>

        <div class="pager">
          <el-pagination
            background
            layout="prev, pager, next, total, sizes"
            :current-page="query.page"
            :page-size="query.page_size"
            :total="total"
            :page-sizes="[10, 20, 50, 100]"
            @current-change="onPageChange"
            @size-change="onSizeChange"
          />
        </div>
      </template>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { fetchStyleProfitSnapshots, type StyleProfitSnapshotListItem } from '@/api/style_profit'
import { usePermissionStore } from '@/stores/permission'

const router = useRouter()
const permissionStore = usePermissionStore()
const loading = ref<boolean>(false)
const rows = ref<StyleProfitSnapshotListItem[]>([])
const total = ref<number>(0)

const canRead = computed<boolean>(() => permissionStore.state.buttonPermissions.read)

const query = reactive({
  company: '',
  item_code: '',
  sales_order: '',
  from_date: '',
  to_date: '',
  snapshot_status: '',
  page: 1,
  page_size: 20,
})

const formatAmount = (value: string | number | null | undefined): string => {
  if (value === null || value === undefined || value === '') {
    return '-'
  }
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric.toFixed(2) : String(value)
}

const formatProfitRate = (value: string | number | null | undefined): string => {
  if (value === null || value === undefined || value === '') {
    return '-'
  }
  const numeric = Number(value)
  return Number.isFinite(numeric) ? `${(numeric * 100).toFixed(2)}%` : String(value)
}

const hasRequiredScope = (): boolean => {
  return Boolean(query.company.trim()) && Boolean(query.item_code.trim())
}

const resetRows = (): void => {
  rows.value = []
  total.value = 0
}

const loadRows = async (): Promise<void> => {
  if (!canRead.value) {
    resetRows()
    return
  }
  if (!hasRequiredScope()) {
    ElMessage.warning('company 与 item_code 不能为空')
    resetRows()
    return
  }

  loading.value = true
  try {
    const result = await fetchStyleProfitSnapshots({
      company: query.company.trim(),
      item_code: query.item_code.trim(),
      sales_order: query.sales_order.trim() || undefined,
      from_date: query.from_date || undefined,
      to_date: query.to_date || undefined,
      snapshot_status: query.snapshot_status || undefined,
      page: query.page,
      page_size: query.page_size,
    })
    rows.value = result.data.items
    total.value = result.data.total
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    loading.value = false
  }
}

const goDetail = (snapshotId: number): void => {
  router.push({ path: '/reports/style-profit/detail', query: { id: String(snapshotId) } })
}

const onPageChange = (page: number): void => {
  query.page = page
  loadRows()
}

const onSizeChange = (size: number): void => {
  query.page_size = size
  query.page = 1
  loadRows()
}

onMounted(async () => {
  try {
    await permissionStore.loadCurrentUser()
    await permissionStore.loadModuleActions('style_profit')
  } catch (error) {
    ElMessage.error((error as Error).message)
    return
  }
  if (canRead.value && hasRequiredScope()) {
    await loadRows()
  }
})
</script>

<style scoped>
.style-profit-list-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.warn-tag {
  margin-left: 8px;
}

.pager {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}
</style>
