<template>
  <div class="factory-statement-list-page">
    <el-card shadow="never">
      <template #header>
        <div class="header-row">
          <span>加工厂对账单列表</span>
        </div>
      </template>

      <el-form :inline="true" :model="query">
        <el-form-item label="供应商">
          <el-input v-model="query.supplier" clearable placeholder="supplier" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.statement_status" clearable style="width: 160px">
            <el-option label="草稿" value="draft" />
            <el-option label="已确认" value="confirmed" />
            <el-option label="已取消" value="cancelled" />
            <el-option label="应付草稿已生成" value="payable_draft_created" />
          </el-select>
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
        <el-form-item>
          <el-button type="primary" :disabled="!canRead" @click="loadRows">查询</el-button>
        </el-form-item>
      </el-form>

      <el-empty v-if="!canRead" description="无加工厂对账单查看权限" />
      <template v-else>
        <el-table :data="rows" border v-loading="loading">
          <el-table-column prop="statement_no" label="对账单号" min-width="180" />
          <el-table-column prop="company" label="公司" min-width="140" />
          <el-table-column prop="supplier" label="供应商" min-width="140" />
          <el-table-column label="期间" min-width="200">
            <template #default="scope">
              {{ scope.row.from_date }} ~ {{ scope.row.to_date }}
            </template>
          </el-table-column>
          <el-table-column label="数量" width="110">
            <template #default="scope">{{ scope.row.source_count }}</template>
          </el-table-column>
          <el-table-column label="加工费" width="130">
            <template #default="scope">{{ formatAmount(scope.row.gross_amount) }}</template>
          </el-table-column>
          <el-table-column label="扣款" width="130">
            <template #default="scope">{{ formatAmount(scope.row.deduction_amount) }}</template>
          </el-table-column>
          <el-table-column label="实付金额" width="130">
            <template #default="scope">{{ formatAmount(scope.row.net_amount) }}</template>
          </el-table-column>
          <el-table-column label="状态" min-width="150">
            <template #default="scope">
              <el-tag :type="statusTag(scope.row.statement_status)">
                {{ statementStatusLabel(scope.row.statement_status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="应付草稿同步" min-width="140">
            <template #default="scope">
              {{ outboxStatusLabel(scope.row.payable_outbox_status) }}
            </template>
          </el-table-column>
          <el-table-column label="ERP 发票草稿" min-width="180">
            <template #default="scope">
              {{ scope.row.purchase_invoice_name || '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="创建时间" min-width="180" />
          <el-table-column label="操作" fixed="right" width="100">
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
  fetchFactoryStatements,
  type FactoryStatementListItem,
} from '@/api/factory_statement'
import { usePermissionStore } from '@/stores/permission'

const router = useRouter()
const permissionStore = usePermissionStore()

const loading = ref<boolean>(false)
const rows = ref<FactoryStatementListItem[]>([])
const total = ref<number>(0)

const canRead = computed<boolean>(() => permissionStore.state.buttonPermissions.factory_statement_read)

const query = reactive({
  supplier: '',
  statement_status: '',
  from_date: '',
  to_date: '',
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

const statementStatusLabel = (status: string | null | undefined): string => {
  if (status === 'draft') {
    return '草稿'
  }
  if (status === 'confirmed') {
    return '已确认'
  }
  if (status === 'cancelled') {
    return '已取消'
  }
  if (status === 'payable_draft_created') {
    return '应付草稿已生成'
  }
  return status || '-'
}

const outboxStatusLabel = (status: string | null | undefined): string => {
  if (status === 'pending') {
    return '待同步'
  }
  if (status === 'processing') {
    return '同步中'
  }
  if (status === 'succeeded') {
    return '已生成草稿'
  }
  if (status === 'failed') {
    return '同步失败'
  }
  if (status === 'dead') {
    return '同步死信'
  }
  return '-'
}

const statusTag = (status: string | null | undefined): 'warning' | 'success' | 'danger' | 'info' => {
  if (status === 'draft') {
    return 'warning'
  }
  if (status === 'confirmed') {
    return 'success'
  }
  if (status === 'cancelled') {
    return 'danger'
  }
  return 'info'
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

  loading.value = true
  try {
    const result = await fetchFactoryStatements({
      supplier: query.supplier.trim() || undefined,
      statement_status: query.statement_status || undefined,
      from_date: query.from_date || undefined,
      to_date: query.to_date || undefined,
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

const goDetail = (statementId: number): void => {
  router.push({ path: '/factory-statements/detail', query: { id: String(statementId) } })
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
    await permissionStore.loadModuleActions('factory_statement')
  } catch (error) {
    ElMessage.error((error as Error).message)
    return
  }
  if (canRead.value) {
    await loadRows()
  }
})
</script>

<style scoped>
.factory-statement-list-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.pager {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}
</style>
