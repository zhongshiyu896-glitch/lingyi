<template>
  <div class="purchase-list-page" data-testid="yisuan-1to1-subcontract-list-shell">
    <el-card shadow="never" data-testid="yisuan-contract-safety-boundary">
      <template #header>
        <div class="header-row">
          <div>
            <h2>外协采购列表（A002/A004/A006 契约壳层）</h2>
            <p class="sub-title">CONTRACT-CAND-004 / contract_merge_no_real_object</p>
          </div>
          <div class="header-actions">
            <el-button type="info" plain @click="openA006PopupPreview">A006 popup-only 预览</el-button>
            <el-button type="primary" plain :loading="loading" @click="loadRows">刷新</el-button>
          </div>
        </div>
      </template>
      <el-alert
        type="warning"
        :closable="false"
        title="本页仅允许只读/回读 UI 壳层；禁止真实保存、提交、审核、采购、外协、库存、结算、生产写入。"
      />
    </el-card>

    <el-card shadow="never" data-testid="yisuan-contract-source-readback">
      <template #header>
        <span>合同回读（source readback）</span>
      </template>
      <el-descriptions border :column="2">
        <el-descriptions-item label="covered_contract_ids">A002 / A004 / A006</el-descriptions-item>
        <el-descriptions-item label="contract_source_readback_present">true</el-descriptions-item>
        <el-descriptions-item label="unknown_blocked_fields_preserved">true</el-descriptions-item>
        <el-descriptions-item label="unknown_blocked_fields_claimed_as_confirmed">false</el-descriptions-item>
        <el-descriptions-item label="popup_or_disabled_boundary">true</el-descriptions-item>
        <el-descriptions-item label="not_claimed_as_business_action">true</el-descriptions-item>
      </el-descriptions>
      <div class="contract-status-row" data-testid="yisuan-1to1-subcontract-status-tags">
        <el-tag>VERIFIED</el-tag>
        <el-tag type="success">PARTIAL</el-tag>
        <el-tag type="warning">UNKNOWN</el-tag>
        <el-tag type="danger">BLOCKED</el-tag>
        <el-tag type="info">NO-GO</el-tag>
      </div>
      <el-alert
        type="info"
        :closable="false"
        title="A006 blocked/source_unknown/pending_confirmation 项仅支持 popup_only/disabled_only/not_claimed 表达。"
      />
    </el-card>

    <el-card shadow="never">
      <div v-if="isMaterialPurchaseParity" data-testid="yisuan-1to1-purchase-parity-shell">
        <el-alert
          type="info"
          :closable="false"
          class="parity-alert"
          data-testid="mvp-purchase-parity-material"
          title="materialPurchase parity：/materialPurchase/materialPurchaseProcess -> /subcontract/list?parity=material-purchase"
        />
      </div>

      <el-form
        :inline="true"
        data-testid="yisuan-1to1-subcontract-list-filter-panel"
        data-legacy-testid="mvp-purchase-list-query"
      >
        <el-form-item label="keyword">
          <el-input v-model="query.keyword" clearable placeholder="单据号/供应商/物料编码" style="width: 220px" />
        </el-form-item>
        <el-form-item label="供应商/加工厂">
          <el-input v-model="query.partnerName" clearable placeholder="供应商或加工厂" style="width: 180px" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.status" clearable placeholder="全部状态" style="width: 140px">
            <el-option label="draft" value="draft" />
            <el-option label="saved" value="saved" />
            <el-option label="cancelled" value="cancelled" />
          </el-select>
        </el-form-item>
        <el-form-item label="物料类别">
          <el-select v-model="query.materialCategory" clearable placeholder="全部类别" style="width: 150px">
            <el-option label="fabric" value="fabric" />
            <el-option label="trim" value="trim" />
            <el-option label="packaging" value="packaging" />
            <el-option label="mixed" value="mixed" />
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
        empty-text="暂无外协采购草稿（只读回显）"
        data-testid="yisuan-1to1-subcontract-list-table"
        data-legacy-testid="mvp-purchase-list-table"
      >
        <el-table-column prop="document_no" label="单据号" min-width="190" />
        <el-table-column prop="partner_name" label="供应商/加工厂" min-width="170" />
        <el-table-column prop="document_type" label="单据类型" min-width="120" />
        <el-table-column prop="business_date" label="业务日期" min-width="130" />
        <el-table-column prop="material_category" label="物料类别" min-width="120" />
        <el-table-column label="物料明细" min-width="140">
          <template #default="{ row }">
            {{ row.material_lines.length }} 条
          </template>
        </el-table-column>
        <el-table-column label="发料/回料" min-width="180">
          <template #default="{ row }">
            发 {{ row.issue_return.issued_qty }} / 回 {{ row.issue_return.returned_qty }} / 差 {{ row.issue_return.delta_qty }}
          </template>
        </el-table-column>
        <el-table-column label="验货/结算预览" min-width="220">
          <template #default="{ row }">
            验收 {{ row.inspection_settlement.accepted_qty }} / 不良 {{ row.inspection_settlement.rejected_qty }}
            / 结算 {{ row.inspection_settlement.settlement_qty }} / 预估 {{ row.inspection_settlement.estimated_amount }}
          </template>
        </el-table-column>
        <el-table-column label="状态" min-width="110">
          <template #default="{ row }">
            <el-tag :type="tagType(row.status)" data-testid="yisuan-1to1-subcontract-status-tags">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="230" fixed="right">
          <template #default="{ row }">
            <div class="row-actions">
              <el-button link type="primary" @click="openDetail(row.draft_id)">详情</el-button>
              <el-button link type="info" disabled>提交（blocked）</el-button>
              <el-button link type="info" disabled>审核（disabled_only）</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <div class="pager">
        <el-pagination
          background
          layout="prev, pager, next, total"
          :current-page="query.page"
          :page-size="query.page_size"
          :total="total"
          @current-change="onPageChange"
        />
      </div>
    </el-card>

    <el-dialog v-model="a006PopupVisible" title="A006 popup-only / not_claimed" width="560px">
      <el-alert type="warning" :closable="false" title="本弹窗为合同边界展示，不触发任何业务动作。" />
      <el-descriptions border :column="1" class="popup-descriptions">
        <el-descriptions-item label="source_state">source_unknown / pending_confirmation</el-descriptions-item>
        <el-descriptions-item label="boundary">popup_only + disabled_only + not_claimed</el-descriptions-item>
        <el-descriptions-item label="main_save_or_submit_triggered">false</el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <el-button @click="a006PopupVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { request } from '@/api/request'

interface MaterialLine {
  material_code: string
  material_name: string
  color_spec: string
  uom: string
  demand_qty: number
  purchase_qty: number
}

interface IssueReturnState {
  issued_qty: number
  returned_qty: number
  delta_qty: number
  state: string
}

interface InspectionSettlementState {
  accepted_qty: number
  rejected_qty: number
  settlement_qty: number
  estimated_amount: number
  state: string
}

interface PurchaseDraftItem {
  draft_id: number
  scenario_tag: string
  document_no: string
  partner_name: string
  partner_type: string
  document_type: string
  business_date: string
  status: string
  material_category: string
  predecessor_doc_no: string
  note: string
  state: string
  material_lines: MaterialLine[]
  issue_return: IssueReturnState
  inspection_settlement: InspectionSettlementState
  material_line_saved: boolean
  issue_return_or_inspection_saved: boolean
}

interface ListData {
  items: PurchaseDraftItem[]
  total: number
  page: number
  page_size: number
  parity: string
}

const route = useRoute()
const router = useRouter()

const rows = ref<PurchaseDraftItem[]>([])
const total = ref(0)
const loading = ref(false)
const feedback = ref('')
const a006PopupVisible = ref(false)

const query = reactive({
  keyword: '',
  partnerName: '',
  status: '',
  materialCategory: '',
  page: 1,
  page_size: 20,
})

const parityToken = computed(() => {
  const raw = route.query.parity
  if (Array.isArray(raw)) return String(raw[0] || '').trim()
  return String(raw || '').trim()
})

const isMaterialPurchaseParity = computed(() => parityToken.value === 'material-purchase')

const buildListQuery = (): string => {
  const params = new URLSearchParams()
  if (query.keyword.trim()) params.set('keyword', query.keyword.trim())
  if (query.partnerName.trim()) params.set('partner_name', query.partnerName.trim())
  if (query.status.trim()) params.set('status', query.status.trim())
  if (query.materialCategory.trim()) params.set('material_category', query.materialCategory.trim())
  if (parityToken.value) params.set('parity', parityToken.value)
  params.set('page', String(query.page))
  params.set('page_size', String(query.page_size))
  return params.toString()
}

const loadRows = async (): Promise<void> => {
  loading.value = true
  feedback.value = ''
  try {
    const queryString = buildListQuery()
    const response = await request<ListData>(`/api/local-dev/purchase-subcontract-drafts?${queryString}`)
    rows.value = response.data.items || []
    total.value = Number(response.data.total || 0)
    if (isMaterialPurchaseParity.value) {
      feedback.value = 'materialPurchase parity 采购视角已生效（test_data only）'
    }
  } catch (error) {
    rows.value = []
    total.value = 0
    const message = (error as Error).message || '采购/外协列表加载失败'
    feedback.value = message
    ElMessage.error(message)
  } finally {
    loading.value = false
  }
}

const applyQuery = (): void => {
  query.page = 1
  void loadRows()
}

const resetQuery = (): void => {
  query.keyword = ''
  query.partnerName = ''
  query.status = ''
  query.materialCategory = ''
  query.page = 1
  query.page_size = 20
  void loadRows()
}

const onPageChange = (page: number): void => {
  query.page = page
  void loadRows()
}

const openDetail = (draftId: number): void => {
  router.push({
    path: '/subcontract/detail',
    query: {
      id: String(draftId),
      parity: parityToken.value || undefined,
    },
  })
}

const tagType = (status: string): 'success' | 'warning' | 'info' => {
  if (status === 'saved') return 'success'
  if (status === 'cancelled') return 'warning'
  return 'info'
}

const openA006PopupPreview = (): void => {
  a006PopupVisible.value = true
}

onMounted(() => {
  void loadRows()
})
</script>

<style scoped>
.purchase-list-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
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

.contract-status-row {
  margin: 10px 0;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.parity-alert {
  margin-bottom: 10px;
}

.feedback {
  margin: 10px 0;
}

.row-actions {
  display: inline-flex;
  gap: 8px;
}

.popup-descriptions {
  margin-top: 10px;
}

.pager {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}
</style>
