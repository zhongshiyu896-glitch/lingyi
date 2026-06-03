<template>
  <div class="subcontract-list-page" data-testid="yisuan-1to1-subcontract-list-shell">
    <el-card shadow="never">
      <template #header>
        <div class="header-row">
          <div>
            <h2>外协采购列表（本地可试用）</h2>
            <p class="sub-title">local-dev only / no settlement release / no stock outbox release / no worker push</p>
          </div>
          <div class="header-actions">
            <el-button type="primary" plain :loading="loading" @click="loadRows">刷新列表</el-button>
          </div>
        </div>
      </template>
      <el-alert
        type="warning"
        :closable="false"
        title="仅允许 local-dev/test_data 展示；禁止触发真实结算、库存出入库 outbox、worker 推送或 ERPNext 生命周期。"
      />
      <el-alert
        v-if="isMaterialPurchaseParity"
        class="parity-alert"
        type="info"
        :closable="false"
        data-testid="realobj-subcontract-parity-alert"
        title="materialPurchase final_path: /materialPurchase/materialPurchaseProcess -> /subcontract/list?parity=material-purchase"
      />
    </el-card>

    <el-card shadow="never" data-testid="yisuan-1to1-subcontract-list-filter-panel">
      <el-form :inline="true" @submit.prevent>
        <el-form-item label="供应商">
          <el-input v-model="query.supplier" clearable placeholder="供应商 / 加工厂" style="width: 220px" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.status" clearable placeholder="全部" style="width: 150px">
            <el-option label="draft" value="draft" />
            <el-option label="issued" value="issued" />
            <el-option label="processing" value="processing" />
            <el-option label="waiting_receive" value="waiting_receive" />
            <el-option label="waiting_inspection" value="waiting_inspection" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="applyQuery">查询</el-button>
          <el-button :loading="loading" @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>

      <el-alert v-if="feedback" :title="feedback" type="info" :closable="false" class="feedback" />

      <el-table
        :data="rows"
        border
        v-loading="loading"
        empty-text="暂无外协采购对象，已保留本地可试用入口"
        data-testid="yisuan-1to1-subcontract-list-table"
      >
        <el-table-column prop="subcontract_no" label="单据号" min-width="170" />
        <el-table-column prop="supplier" label="供应商/加工厂" min-width="160" />
        <el-table-column prop="item_code" label="物料编码" min-width="150" />
        <el-table-column prop="company" label="公司" min-width="120" />
        <el-table-column prop="process_name" label="工序" min-width="120" />
        <el-table-column label="计划/发料/回料/验收" min-width="220">
          <template #default="{ row }">
            {{ row.planned_qty }} / {{ row.issued_qty }} / {{ row.received_qty }} / {{ row.accepted_qty }}
          </template>
        </el-table-column>
        <el-table-column label="状态" min-width="140">
          <template #default="{ row }">
            <el-tag :type="tagType(row.status)">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="资源范围" min-width="140">
          <template #default="{ row }">
            <el-tag :type="row.resource_scope_status === 'ready' ? 'success' : 'warning'" effect="plain">
              {{ row.resource_scope_status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row.id)">查看详情</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card shadow="never" data-testid="realobj-subcontract-readback-evidence">
      <template #header>
        <span>本地可试用边界</span>
      </template>
      <el-descriptions border :column="2">
        <el-descriptions-item label="final_path">{{ finalPath }}</el-descriptions-item>
        <el-descriptions-item label="parity">{{ parityToken || '-' }}</el-descriptions-item>
        <el-descriptions-item label="local_dev_only">true</el-descriptions-item>
        <el-descriptions-item label="settlement_release">false</el-descriptions-item>
        <el-descriptions-item label="stock_outbox_release">false</el-descriptions-item>
        <el-descriptions-item label="stock_worker_push">false</el-descriptions-item>
        <el-descriptions-item label="erpnext_production">false</el-descriptions-item>
        <el-descriptions-item label="real_production_account">false</el-descriptions-item>
        <el-descriptions-item label="row_count">{{ rows.length }}</el-descriptions-item>
        <el-descriptions-item label="fallback_snapshot_used">{{ fallbackSnapshotUsed ? 'true' : 'false' }}</el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { fetchSubcontractOrders, type SubcontractOrderListItem } from '@/api/subcontract'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const rows = ref<SubcontractOrderListItem[]>([])
const total = ref(0)
const feedback = ref('')
const fallbackSnapshotUsed = ref(false)

const query = reactive({
  supplier: '',
  status: '',
  page: 1,
  pageSize: 20,
})

const parityToken = computed(() => {
  const raw = route.query.parity
  if (Array.isArray(raw)) return String(raw[0] || '').trim()
  return String(raw || '').trim()
})

const isMaterialPurchaseParity = computed(() => parityToken.value === 'material-purchase')

const finalPath = computed(() =>
  isMaterialPurchaseParity.value ? '/subcontract/list?parity=material-purchase' : '/subcontract/list',
)

const buildSyntheticRows = (): SubcontractOrderListItem[] => {
  const supplier = isMaterialPurchaseParity.value ? '本地演示供应商' : '本地演示外协厂'
  return [
    {
      id: 900601,
      subcontract_no: 'SC-LOCAL-USABLE-001',
      supplier,
      item_code: 'ITEM-A',
      company: 'COMP-A',
      bom_id: 1,
      process_name: '外发裁剪',
      planned_qty: '120',
      subcontract_rate: '0.65',
      issued_qty: '90',
      received_qty: '56',
      inspected_qty: '56',
      rejected_qty: '3',
      accepted_qty: '53',
      gross_amount: '6800',
      deduction_amount: '180',
      net_amount: '6620',
      status: 'processing',
      resource_scope_status: 'ready',
      latest_issue_outbox_id: null,
      latest_issue_sync_status: null,
      latest_issue_stock_entry_name: null,
      latest_issue_idempotency_key: null,
      latest_issue_error_code: null,
      latest_receipt_outbox_id: null,
      latest_receipt_sync_status: null,
      latest_receipt_stock_entry_name: null,
      latest_receipt_idempotency_key: null,
      latest_receipt_error_code: null,
      production_plan_id: null,
      work_order: null,
      created_at: new Date().toISOString(),
    },
  ]
}

const tagType = (status: string): 'success' | 'warning' | 'info' => {
  if (status === 'processing' || status === 'waiting_receive' || status === 'waiting_inspection') return 'warning'
  if (status === 'issued') return 'success'
  return 'info'
}

const loadRows = async (): Promise<void> => {
  loading.value = true
  feedback.value = ''
  fallbackSnapshotUsed.value = false
  try {
    const response = await fetchSubcontractOrders({
      supplier: query.supplier.trim() || undefined,
      status: query.status || undefined,
      page: query.page,
      page_size: query.pageSize,
    })
    const items = response.data.items || []
    if (items.length > 0) {
      rows.value = items
      total.value = Number(response.data.total || items.length)
      return
    }
    rows.value = buildSyntheticRows()
    total.value = rows.value.length
    fallbackSnapshotUsed.value = true
    feedback.value = '未读取到本地外协单，已回退 synthetic snapshot 保持入口可试用。'
  } catch (error) {
    rows.value = buildSyntheticRows()
    total.value = rows.value.length
    fallbackSnapshotUsed.value = true
    feedback.value = (error as Error).message || '外协采购列表 API 不可用，已回退 synthetic snapshot。'
  } finally {
    loading.value = false
  }
}

const applyQuery = (): void => {
  query.page = 1
  void loadRows()
}

const resetQuery = (): void => {
  query.supplier = ''
  query.status = ''
  query.page = 1
  void loadRows()
}

const openDetail = (orderId: number): void => {
  router.push({
    path: '/subcontract/detail',
    query: {
      id: String(orderId),
      parity: parityToken.value || undefined,
    },
  })
}

onMounted(() => {
  void loadRows()
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
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.header-row h2 {
  margin: 0;
  font-size: 18px;
}

.sub-title {
  margin: 2px 0 0;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.parity-alert,
.feedback {
  margin-top: 12px;
}
</style>
