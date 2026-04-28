<template>
  <div class="subcontract-list-page">
    <el-card shadow="never">
      <template #header>
        <div class="header-row">
          <span>外发单列表</span>
        </div>
      </template>

      <el-form :inline="true" :model="query">
        <el-form-item label="加工厂">
          <el-input v-model="query.supplier" clearable placeholder="Supplier" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select
            v-model="query.status"
            clearable
            placeholder="全部状态"
            aria-label="外发单状态筛选"
            style="width: 150px"
          >
            <el-option label="草稿" value="draft" />
            <el-option label="已发料" value="issued" />
            <el-option label="加工中" value="processing" />
            <el-option label="待回料" value="waiting_receive" />
            <el-option label="待验货" value="waiting_inspection" />
            <el-option label="已完成" value="completed" />
            <el-option label="已取消" value="cancelled" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :disabled="!canRead" @click="loadOrders">查询</el-button>
        </el-form-item>
      </el-form>

      <el-empty v-if="!canRead" description="无外发查看权限" />
      <template v-else>
        <el-table :data="rows" v-loading="loading" border empty-text="暂无外发单数据">
          <el-table-column prop="subcontract_no" label="外发单号" min-width="220" />
          <el-table-column prop="company" label="公司" min-width="150" />
          <el-table-column prop="supplier" label="加工厂" min-width="160" />
          <el-table-column prop="item_code" label="款式" min-width="140" />
          <el-table-column prop="process_name" label="工序" min-width="120" />
          <el-table-column prop="planned_qty" label="计划数量" width="110" />
          <el-table-column prop="issued_qty" label="已发料" width="110" />
          <el-table-column prop="received_qty" label="已回料" width="110" />
          <el-table-column prop="inspected_qty" label="已验货" width="110" />
          <el-table-column prop="net_amount" label="净应付金额" width="120" />
          <el-table-column label="状态" min-width="180">
            <template #default="scope">
              <el-tag>{{ statusLabel(scope.row.status) }}</el-tag>
              <el-tag v-if="scope.row.resource_scope_status === 'blocked_scope'" type="danger" class="scope-tag">
                权限范围异常
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="库存同步状态" min-width="160">
            <template #default="scope">{{ syncStatusLabel(scope.row) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="120" fixed="right">
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
import {
  fetchSubcontractOrders,
  type SubcontractOrderListItem,
} from '@/api/subcontract'
import { usePermissionStore } from '@/stores/permission'

const router = useRouter()
const permissionStore = usePermissionStore()
const loading = ref<boolean>(false)
const rows = ref<SubcontractOrderListItem[]>([])
const total = ref<number>(0)

const canRead = computed<boolean>(() => permissionStore.state.buttonPermissions.read)

const query = reactive({
  supplier: '',
  status: '',
  page: 1,
  page_size: 20,
})

const statusLabel = (value: string): string => {
  const labels: Record<string, string> = {
    draft: '草稿',
    issued: '已发料',
    processing: '加工中',
    waiting_receive: '待回料',
    waiting_inspection: '待验货',
    completed: '已完成',
    cancelled: '已取消',
  }
  return labels[value] || value
}

const stockSyncLabel = (status?: string | null): string => {
  if (!status) return ''
  const labels: Record<string, string> = {
    pending: '待同步',
    processing: '同步中',
    succeeded: '已同步',
    failed: '同步失败',
    dead: '死信',
    blocked_scope: '范围阻断',
  }
  return labels[status] || status
}

const syncStatusLabel = (row: SubcontractOrderListItem): string => {
  const issue = stockSyncLabel(row.latest_issue_sync_status)
  const receipt = stockSyncLabel(row.latest_receipt_sync_status)
  if (issue && receipt) {
    return `发料:${issue} / 回料:${receipt}`
  }
  if (receipt) {
    return `回料:${receipt}`
  }
  if (issue) {
    return `发料:${issue}`
  }
  return '未入列'
}

const loadOrders = async (): Promise<void> => {
  if (!canRead.value) {
    rows.value = []
    total.value = 0
    return
  }
  loading.value = true
  try {
    const payload = await fetchSubcontractOrders(query)
    rows.value = payload.data.items
    total.value = payload.data.total
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    loading.value = false
  }
}

const goDetail = (id: number): void => {
  router.push({ path: '/subcontract/detail', query: { id: String(id) } })
}

const onPageChange = (page: number): void => {
  query.page = page
  loadOrders()
}

const onSizeChange = (size: number): void => {
  query.page_size = size
  query.page = 1
  loadOrders()
}

onMounted(async () => {
  try {
    await permissionStore.loadCurrentUser()
    await permissionStore.loadModuleActions('subcontract')
  } catch (error) {
    ElMessage.error((error as Error).message)
  }
  await loadOrders()
})
</script>

<style scoped>
.subcontract-list-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.scope-tag {
  margin-left: 8px;
}

.pager {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}
</style>
