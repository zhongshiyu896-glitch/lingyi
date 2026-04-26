<template>
  <div class="style-profit-detail-page">
    <el-card shadow="never" v-loading="loading">
      <template #header>
        <div class="header-row">
          <span>款式利润快照详情</span>
          <el-button @click="goBack">返回列表</el-button>
        </div>
      </template>

      <el-skeleton v-if="!permissionReady" :rows="4" animated />
      <el-empty v-else-if="!canRead" description="无款式利润查看权限" />
      <template v-else>
        <el-empty v-if="missingSnapshotId" description="请从款式利润列表进入详情页" />
        <el-empty v-else-if="!snapshot" description="未找到利润快照数据" />
        <template v-else>
          <el-alert
            v-if="snapshot.unresolved_count > 0"
            type="warning"
            :closable="false"
            show-icon
            title="存在未解析来源，请财务复核后使用"
            class="warn-alert"
          />
          <el-descriptions :column="3" border>
            <el-descriptions-item label="快照号">{{ snapshot.snapshot_no }}</el-descriptions-item>
            <el-descriptions-item label="快照 ID">{{ snapshot.snapshot_id }}</el-descriptions-item>
            <el-descriptions-item label="状态">{{ snapshot.snapshot_status }}</el-descriptions-item>
            <el-descriptions-item label="公司">{{ snapshot.company }}</el-descriptions-item>
            <el-descriptions-item label="款式">{{ snapshot.item_code }}</el-descriptions-item>
            <el-descriptions-item label="销售订单">{{ snapshot.sales_order || '-' }}</el-descriptions-item>
            <el-descriptions-item label="收入口径">{{ snapshot.revenue_status }}</el-descriptions-item>
            <el-descriptions-item label="收入金额">{{ formatAmount(snapshot.revenue_amount) }}</el-descriptions-item>
            <el-descriptions-item label="实际总成本">{{ formatAmount(snapshot.actual_total_cost) }}</el-descriptions-item>
            <el-descriptions-item label="标准总成本">{{ formatAmount(snapshot.standard_total_cost) }}</el-descriptions-item>
            <el-descriptions-item label="利润金额">{{ formatAmount(snapshot.profit_amount) }}</el-descriptions-item>
            <el-descriptions-item label="利润率">{{ formatProfitRate(snapshot.profit_rate) }}</el-descriptions-item>
            <el-descriptions-item label="未解析数量">{{ snapshot.unresolved_count }}</el-descriptions-item>
            <el-descriptions-item label="分摊状态">{{ snapshot.allocation_status }}</el-descriptions-item>
            <el-descriptions-item label="纳入暂估外发">
              {{ snapshot.include_provisional_subcontract ? '是' : '否' }}
            </el-descriptions-item>
          </el-descriptions>
          <el-collapse v-model="auditPanels" class="audit-collapse">
            <el-collapse-item title="审计信息（仅供审计复核）" name="audit">
              <el-descriptions :column="1" border size="small">
                <el-descriptions-item label="幂等回放">
                  {{ snapshot.idempotent_replay ? '是' : '否' }}
                </el-descriptions-item>
                <el-descriptions-item label="请求哈希">{{ snapshot.request_hash }}</el-descriptions-item>
              </el-descriptions>
            </el-collapse-item>
          </el-collapse>
        </template>
      </template>
    </el-card>

    <el-card v-if="canRead && snapshot" shadow="never">
      <template #header><span>利润明细</span></template>
      <el-table :data="details" border>
        <el-table-column prop="line_no" label="行号" width="70" />
        <el-table-column prop="cost_type" label="成本类型" min-width="120" />
        <el-table-column prop="source_type" label="来源类型" min-width="120" />
        <el-table-column prop="source_name" label="来源名称" min-width="180" />
        <el-table-column prop="item_code" label="编码" min-width="120" />
        <el-table-column label="数量" width="110">
          <template #default="scope">{{ formatNullable(scope.row.qty) }}</template>
        </el-table-column>
        <el-table-column label="单价" width="110">
          <template #default="scope">{{ formatNullable(scope.row.unit_rate) }}</template>
        </el-table-column>
        <el-table-column label="金额" width="120">
          <template #default="scope">{{ formatAmount(scope.row.amount) }}</template>
        </el-table-column>
        <el-table-column label="未解析" width="90">
          <template #default="scope">
            <el-tag :type="scope.row.is_unresolved ? 'danger' : 'success'">
              {{ scope.row.is_unresolved ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="unresolved_reason" label="未解析原因" min-width="180" />
      </el-table>
    </el-card>

    <el-card v-if="canRead && snapshot" shadow="never">
      <template #header><span>来源追溯</span></template>
      <el-table :data="sourceMaps" border>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="source_system" label="来源系统" min-width="110" />
        <el-table-column prop="source_doctype" label="来源单据类型" min-width="140" />
        <el-table-column prop="source_status" label="来源状态" min-width="120" />
        <el-table-column prop="source_name" label="来源单据号" min-width="170" />
        <el-table-column prop="source_line_no" label="来源行号" min-width="120" />
        <el-table-column prop="style_item_code" label="款式编码" min-width="120" />
        <el-table-column prop="source_item_code" label="来源编码" min-width="120" />
        <el-table-column prop="sales_order" label="销售订单" min-width="140" />
        <el-table-column prop="warehouse" label="仓库" min-width="120" />
        <el-table-column prop="posting_date" label="过账日期" min-width="120" />
        <el-table-column label="金额" width="120">
          <template #default="scope">{{ formatAmount(scope.row.amount) }}</template>
        </el-table-column>
        <el-table-column label="纳入利润" width="100">
          <template #default="scope">
            <el-tag :type="scope.row.include_in_profit ? 'success' : 'info'">
              {{ scope.row.include_in_profit ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="mapping_status" label="映射状态" min-width="110" />
        <el-table-column prop="unresolved_reason" label="未解析原因" min-width="180" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  fetchStyleProfitSnapshotDetail,
  type StyleProfitDetailItem,
  type StyleProfitSnapshotResult,
  type StyleProfitSourceMapItem,
} from '@/api/style_profit'
import { usePermissionStore } from '@/stores/permission'

const route = useRoute()
const router = useRouter()
const permissionStore = usePermissionStore()

const loading = ref<boolean>(false)
const snapshot = ref<StyleProfitSnapshotResult | null>(null)
const details = ref<StyleProfitDetailItem[]>([])
const sourceMaps = ref<StyleProfitSourceMapItem[]>([])
const auditPanels = ref<string[]>([])
const missingSnapshotId = ref<boolean>(false)
const permissionReady = ref<boolean>(false)

const canRead = computed<boolean>(() => permissionStore.state.buttonPermissions.read)
const snapshotId = computed<number>(() => Number(route.query.id || '0'))
const hasValidSnapshotId = computed<boolean>(() => Number.isInteger(snapshotId.value) && snapshotId.value > 0)

const formatAmount = (value: string | number | null | undefined): string => {
  if (value === null || value === undefined || value === '') {
    return '-'
  }
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric.toFixed(2) : String(value)
}

const formatNullable = (value: string | number | null | undefined): string => {
  if (value === null || value === undefined || value === '') {
    return '-'
  }
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric.toFixed(4) : String(value)
}

const formatProfitRate = (value: string | number | null | undefined): string => {
  if (value === null || value === undefined || value === '') {
    return '-'
  }
  const numeric = Number(value)
  return Number.isFinite(numeric) ? `${(numeric * 100).toFixed(2)}%` : String(value)
}

const loadDetail = async (): Promise<void> => {
  if (!canRead.value) {
    snapshot.value = null
    details.value = []
    sourceMaps.value = []
    missingSnapshotId.value = false
    return
  }
  if (!hasValidSnapshotId.value) {
    snapshot.value = null
    details.value = []
    sourceMaps.value = []
    missingSnapshotId.value = true
    return
  }
  missingSnapshotId.value = false

  loading.value = true
  try {
    const result = await fetchStyleProfitSnapshotDetail(snapshotId.value)
    snapshot.value = result.data.snapshot
    details.value = result.data.details
    sourceMaps.value = result.data.source_maps
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    loading.value = false
  }
}

const goBack = (): void => {
  router.push({ path: '/reports/style-profit' })
}

onMounted(async () => {
  try {
    await permissionStore.loadCurrentUser()
    await permissionStore.loadModuleActions('style_profit')
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    permissionReady.value = true
  }
  await loadDetail()
})
</script>

<style scoped>
.style-profit-detail-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.warn-alert {
  margin-bottom: 12px;
}

.audit-collapse {
  margin-top: 12px;
}
</style>
