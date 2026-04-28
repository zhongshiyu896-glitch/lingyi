<template>
  <div class="subcontract-detail-page">
    <el-card shadow="never" v-loading="loading">
      <template #header>
        <div class="header-row">
          <span>外发单详情</span>
          <el-button @click="goBack">返回</el-button>
        </div>
      </template>
      <el-skeleton v-if="!permissionReady" :rows="4" animated />
      <el-empty v-else-if="!canRead" description="无外发查看权限" />
      <template v-else>
        <el-empty v-if="missingOrderId" description="请从外发单列表进入详情页" />
        <el-descriptions v-else-if="detail" :column="3" border>
          <el-descriptions-item label="外发单号">{{ detail.subcontract_no }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag>{{ statusLabel(detail.status) }}</el-tag>
            <el-tag v-if="isScopeBlocked" type="danger" class="scope-tag">权限范围异常</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="公司">{{ detail.company || '-' }}</el-descriptions-item>
          <el-descriptions-item label="加工厂">{{ detail.supplier }}</el-descriptions-item>
          <el-descriptions-item label="款式">{{ detail.item_code }}</el-descriptions-item>
          <el-descriptions-item label="工序">{{ detail.process_name }}</el-descriptions-item>
          <el-descriptions-item label="计划数量">{{ detail.planned_qty }}</el-descriptions-item>
          <el-descriptions-item label="已发料">{{ detail.issued_qty }}</el-descriptions-item>
          <el-descriptions-item label="已回料">{{ detail.received_qty }}</el-descriptions-item>
          <el-descriptions-item label="已验货">{{ detail.inspected_qty }}</el-descriptions-item>
          <el-descriptions-item label="不合格数量">{{ detail.rejected_qty }}</el-descriptions-item>
          <el-descriptions-item label="合格数量">{{ detail.accepted_qty }}</el-descriptions-item>
          <el-descriptions-item label="加工单价">{{ detail.subcontract_rate }}</el-descriptions-item>
          <el-descriptions-item label="验货总金额">{{ detail.gross_amount }}</el-descriptions-item>
          <el-descriptions-item label="扣款金额">{{ detail.deduction_amount }}</el-descriptions-item>
          <el-descriptions-item label="净应付金额">{{ detail.net_amount }}</el-descriptions-item>
          <el-descriptions-item label="发料同步状态">
            {{ stockSyncLabel(detail.latest_issue_sync_status) || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="回料同步状态">
            {{ stockSyncLabel(detail.latest_receipt_sync_status) || '-' }}
          </el-descriptions-item>
        </el-descriptions>
      </template>
    </el-card>

    <el-card v-if="canRead" shadow="never">
      <el-alert
        title="当前页面为只读履约投影基线，普通前端已冻结新建外发单、发料、回料、验货和同步重试入口。"
        type="info"
        :closable="false"
        show-icon
      />
    </el-card>

    <el-card v-if="canRead && detail" shadow="never">
      <template #header><span>回料批次</span></template>
      <el-table :data="detail?.receipts || []" border empty-text="暂无回料批次数据">
        <el-table-column prop="receipt_batch_no" label="回料批次" min-width="160" />
        <el-table-column prop="receipt_warehouse" label="回料仓" min-width="120" />
        <el-table-column prop="received_qty" label="回料数量" width="120" />
        <el-table-column prop="sync_status" label="同步状态" width="120" />
        <el-table-column prop="stock_entry_name" label="Stock Entry" min-width="180" />
      </el-table>
    </el-card>

    <el-card v-if="canRead && detail" shadow="never">
      <template #header><span>验货明细</span></template>
      <el-table :data="detail?.inspections || []" border empty-text="暂无验货明细数据">
        <el-table-column prop="inspection_no" label="验货单号" min-width="180" />
        <el-table-column prop="receipt_batch_no" label="回料批次" min-width="160" />
        <el-table-column prop="inspected_qty" label="验货数量" width="110" />
        <el-table-column prop="accepted_qty" label="合格数量" width="110" />
        <el-table-column prop="rejected_qty" label="不合格数量" width="120" />
        <el-table-column prop="gross_amount" label="验货总金额" width="120" />
        <el-table-column prop="deduction_amount" label="扣款金额" width="120" />
        <el-table-column prop="net_amount" label="净应付金额" width="120" />
        <el-table-column prop="inspected_by" label="验货人" width="120" />
        <el-table-column prop="inspected_at" label="验货时间" min-width="180" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { fetchSubcontractOrderDetail, type SubcontractOrderDetailData } from '@/api/subcontract'
import { usePermissionStore } from '@/stores/permission'

const route = useRoute()
const router = useRouter()
const permissionStore = usePermissionStore()
const detail = ref<SubcontractOrderDetailData | null>(null)
const missingOrderId = ref<boolean>(false)
const loading = ref<boolean>(false)
const permissionReady = ref<boolean>(false)

const canRead = computed<boolean>(() => permissionStore.state.buttonPermissions.read)
const orderId = computed<number>(() => Number(route.query.id || '0'))
const hasValidOrderId = computed<boolean>(() => Number.isInteger(orderId.value) && orderId.value > 0)
const isScopeBlocked = computed<boolean>(() => detail.value?.resource_scope_status === 'blocked_scope')

const stockSyncLabel = (value?: string | null): string => {
  if (!value) return ''
  const labels: Record<string, string> = {
    pending: '待同步',
    processing: '同步中',
    succeeded: '已同步',
    failed: '同步失败',
    dead: '死信',
    blocked_scope: '范围阻断',
  }
  return labels[value] || value
}

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

const loadDetail = async (): Promise<void> => {
  if (!canRead.value) {
    detail.value = null
    missingOrderId.value = false
    return
  }
  if (!hasValidOrderId.value) {
    detail.value = null
    missingOrderId.value = true
    return
  }
  missingOrderId.value = false
  loading.value = true
  try {
    const result = await fetchSubcontractOrderDetail(orderId.value)
    detail.value = result.data
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    loading.value = false
  }
}

const goBack = (): void => {
  router.push('/subcontract/list')
}

watch(
  () => orderId.value,
  async () => {
    await loadDetail()
  },
)

onMounted(async () => {
  try {
    await permissionStore.loadCurrentUser()
    await permissionStore.loadModuleActions('subcontract')
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    permissionReady.value = true
  }
  await loadDetail()
})
</script>

<style scoped>
.subcontract-detail-page {
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
</style>
