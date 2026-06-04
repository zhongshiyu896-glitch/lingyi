<template>
  <div class="bom-list-shell" data-testid="yisuan-1to1-bom-list-shell">
    <el-card shadow="never" class="bom-header-card">
      <div class="header-row">
        <div class="header-main">
          <h2 class="page-title">物料开发 BOM 列表</h2>
          <p class="page-subtitle">衣算云 UI 1:1 + REALOBJ-CAND-002 本地写入闭环（local-dev only）</p>
        </div>
        <div class="header-actions" data-testid="yisuan-1to1-bom-list-toolbar">
          <el-button type="primary" @click="runQuery">查询</el-button>
          <el-button @click="resetQuery">重置</el-button>
          <el-button :disabled="!currentObjectId" @click="readbackObject">回读本地对象</el-button>
          <el-button @click="checkZeroResidual">zero_residual 校验</el-button>
        </div>
      </div>

      <div class="source-readback" data-testid="yisuan-1to1-ui-source-readback">
        <el-tag type="success">source_status=found</el-tag>
        <el-tag type="primary">covered_contract_ids=A002,A005</el-tag>
        <el-tag type="info">real_business_object_created=false (production)</el-tag>
        <el-tag type="info">linked_calculation_enabled=false (cross-module)</el-tag>
        <span>来源：A002/A005 contract sources（B010 继承，B011 local-dev/sqlite/scenario_tag/test_data）</span>
      </div>
    </el-card>

    <el-card shadow="never" class="filter-card">
      <el-form :inline="true" :model="query" data-testid="yisuan-1to1-bom-filter-panel">
        <el-form-item label="关键字">
          <el-input v-model="query.keyword" clearable placeholder="BOM 编号/款号/版本" style="width: 220px" />
        </el-form-item>
        <el-form-item label="款号">
          <el-input v-model="query.styleCode" clearable placeholder="输入款号" style="width: 160px" />
        </el-form-item>
        <el-form-item label="物料分组">
          <el-select v-model="query.materialGroup" clearable placeholder="选择分组" style="width: 170px">
            <el-option label="针织上装" value="针织上装" />
            <el-option label="梭织外套" value="梭织外套" />
            <el-option label="牛仔系列" value="牛仔系列" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.status" clearable placeholder="选择状态" style="width: 140px">
            <el-option label="草稿" value="draft" />
            <el-option label="审核中" value="review" />
            <el-option label="已发布" value="published" />
          </el-select>
        </el-form-item>
      </el-form>

      <div class="status-legend" data-testid="yisuan-1to1-bom-status-tags">
        <el-tag type="info">草稿</el-tag>
        <el-tag type="warning">审核中</el-tag>
        <el-tag type="success">已发布</el-tag>
      </div>

      <el-alert v-if="listError" type="warning" :closable="false" :title="listError" class="feedback-alert" />
    </el-card>

    <el-card shadow="never" class="contract-boundary-card">
      <template #header>
        <div class="contract-header">
          <strong>合同边界回读（A002/A005）</strong>
          <el-tag type="warning">A005 partial/unknown 不宣称已确认</el-tag>
        </div>
      </template>

      <div class="contract-grid">
        <div class="contract-block" data-testid="yisuan-contract-key-fields">
          <h4>key_fields</h4>
          <div class="tag-row">
            <el-tag v-for="field in a005VerifiedFields" :key="`verified-${field}`" type="success" effect="light">
              {{ field }} VERIFIED
            </el-tag>
            <el-tag v-for="field in a005PartialFields" :key="`partial-${field}`" type="warning" effect="plain">
              {{ field }} pending_confirmation
            </el-tag>
          </div>
        </div>

        <div class="contract-block" data-testid="yisuan-contract-validation-rules">
          <h4>validation_rules</h4>
          <ul>
            <li v-for="field in a005UnknownFields" :key="`unknown-${field}`">
              {{ field }} => source_unknown / pending_confirmation / not_claimed
            </li>
          </ul>
          <div class="tag-row compact">
            <el-tag v-for="action in a005BlockedActions" :key="`blocked-${action}`" type="danger" effect="plain">
              {{ action }} blocked
            </el-tag>
          </div>
        </div>

        <div class="contract-block" data-testid="yisuan-contract-status-rules">
          <h4>status_rules</h4>
          <div class="tag-row">
            <el-tag v-for="state in a002StateLabels" :key="state" type="info" effect="light">{{ state }}</el-tag>
            <el-tag type="warning" effect="light">quote_draft_status=待提交</el-tag>
          </div>
        </div>

        <div class="contract-block" data-testid="yisuan-contract-readonly-readback-rules">
          <h4>readonly/readback rules</h4>
          <ul>
            <li v-for="rule in explicitNonClaimRules" :key="rule">{{ rule }}</li>
          </ul>
        </div>
      </div>
    </el-card>

    <el-card shadow="never" class="readonly-summary-card" data-testid="cand164-bom-list-readonly-summary">
      <template #header>
        <div class="contract-header">
          <strong>BOM 颜色尺码 / 替代料只读提示</strong>
          <el-tag type="info" effect="plain">{{ listReadonlySummary.readonlySourceTag }}</el-tag>
        </div>
      </template>

      <el-alert
        v-if="listReadonlySummary.parityReadonlyHint"
        type="warning"
        :closable="false"
        :title="listReadonlySummary.parityReadonlyHint"
        data-testid="cand164-material-fabric-parity-readonly"
      />

      <el-descriptions border :column="2" class="readback-descriptions" data-testid="cand164-bom-list-readonly-descriptions">
        <el-descriptions-item label="当前入口">{{ listReadonlySummary.parityScopeLabel }}</el-descriptions-item>
        <el-descriptions-item label="列表行数">{{ listReadonlySummary.rowCountLabel }}</el-descriptions-item>
        <el-descriptions-item label="颜色尺码用量">{{ listReadonlySummary.usageSummaryLabel }}</el-descriptions-item>
        <el-descriptions-item label="替代料状态">{{ listReadonlySummary.alternateStatusLabel }}</el-descriptions-item>
        <el-descriptions-item label="readonly_guard">{{ listReadonlySummary.readonlyGuardReason }}</el-descriptions-item>
        <el-descriptions-item label="write_boundary">{{ listReadonlySummary.writeBoundary }}</el-descriptions-item>
      </el-descriptions>

      <el-alert
        type="info"
        :closable="false"
        :title="listReadonlySummary.remainingGap"
        class="feedback-alert"
        data-testid="cand164-bom-list-remaining-gap"
      />
    </el-card>

    <el-card shadow="never" class="readonly-summary-card" data-testid="cand206-bom-audit-readonly-summary">
      <template #header>
        <div class="contract-header">
          <strong>BOM 审计来源 / 默认版本只读提示</strong>
          <el-tag :type="bomAuditReadonlySummary.readonlySourceType" effect="plain">
            {{ bomAuditReadonlySummary.readonlySourceTag }}
          </el-tag>
        </div>
      </template>

      <el-alert
        v-if="bomAuditReadonlySummary.parityReadonlyHint"
        type="warning"
        :closable="false"
        :title="bomAuditReadonlySummary.parityReadonlyHint"
        data-testid="cand206-bom-product-style-parity-readonly"
      />

      <el-descriptions border :column="2" class="readback-descriptions" data-testid="cand206-bom-audit-readonly-descriptions">
        <el-descriptions-item label="当前入口">{{ bomAuditReadonlySummary.parityScopeLabel }}</el-descriptions-item>
        <el-descriptions-item label="列表行数">{{ bomAuditReadonlySummary.rowCountLabel }}</el-descriptions-item>
        <el-descriptions-item label="审计来源">{{ bomAuditReadonlySummary.auditSourceLabel }}</el-descriptions-item>
        <el-descriptions-item label="默认版本状态">
          {{ bomAuditReadonlySummary.defaultVersionStatusLabel }}
        </el-descriptions-item>
        <el-descriptions-item label="版本覆盖">
          {{ bomAuditReadonlySummary.defaultVersionCoverageLabel }}
        </el-descriptions-item>
        <el-descriptions-item label="readonly_guard">{{ bomAuditReadonlySummary.readonlyGuardReason }}</el-descriptions-item>
      </el-descriptions>

      <el-alert
        type="warning"
        :closable="false"
        :title="bomAuditReadonlySummary.versionSourceGapPrompt"
        class="feedback-alert"
        data-testid="cand206-bom-version-source-gap"
      />

      <el-alert
        type="info"
        :closable="false"
        :title="bomAuditReadonlySummary.remainingGap"
        class="feedback-alert"
        data-testid="cand206-bom-remaining-gap"
      />
    </el-card>

    <el-card shadow="never">
      <el-table
        v-loading="listLoading"
        :data="filteredRows"
        border
        height="460"
        stripe
        data-testid="yisuan-1to1-bom-table"
      >
        <el-table-column prop="bomNo" label="BOM 编号" min-width="170" />
        <el-table-column prop="styleCode" label="款号" min-width="120" />
        <el-table-column prop="styleName" label="款式名称" min-width="180" />
        <el-table-column prop="materialGroup" label="物料分组" min-width="140" />
        <el-table-column prop="version" label="版本" min-width="90" />
        <el-table-column prop="owner" label="开发员" min-width="110" />
        <el-table-column label="状态" min-width="110">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="updatedAt" label="更新时间" min-width="180" />
        <el-table-column label="操作" width="210" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="loadRowToLocalLoop(row)">写入闭环</el-button>
            <el-button link type="primary" @click="goDetail(row)">查看详情</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card shadow="never" class="local-write-panel" data-testid="realobj-bom-local-loop">
      <template #header>
        <div class="panel-header">
          <strong>REALOBJ-CAND-002 本地对象写入闭环（BOM）</strong>
          <el-tag type="info">local-dev/sqlite/scenario_tag/test_data only</el-tag>
        </div>
      </template>

      <el-form :inline="true" :model="draftForm">
        <el-form-item label="scenario_tag">
          <el-input
            v-model="draftForm.scenarioTag"
            style="width: 250px"
            data-testid="realobj-bom-scenario-tag"
          />
        </el-form-item>
        <el-form-item label="BOM 编号">
          <el-input v-model="draftForm.bomNo" style="width: 180px" />
        </el-form-item>
        <el-form-item label="款号">
          <el-input v-model="draftForm.styleCode" style="width: 150px" />
        </el-form-item>
        <el-form-item label="款式名称">
          <el-input v-model="draftForm.styleName" style="width: 180px" />
        </el-form-item>
        <el-form-item label="版本">
          <el-input v-model="draftForm.versionNo" style="width: 110px" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="draftForm.status" style="width: 120px">
            <el-option label="草稿" value="draft" />
            <el-option label="审核中" value="review" />
            <el-option label="已发布" value="published" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="draftForm.note" style="width: 260px" />
        </el-form-item>
      </el-form>

      <div class="local-write-actions">
        <el-button type="primary" :loading="localWriteLoading" @click="saveObject">
          {{ saveButtonLabel }}
        </el-button>
        <el-button :loading="localWriteLoading" :disabled="!currentObjectId" @click="readbackObject">
          回读本地对象
        </el-button>
        <el-button :loading="localWriteLoading" :disabled="!currentObjectId" @click="rollbackScenario">
          回滚 scenario
        </el-button>
        <el-button :loading="localWriteLoading" @click="checkZeroResidual">zero_residual 校验</el-button>
      </div>

      <el-alert
        v-if="localWriteFeedback"
        type="info"
        :closable="false"
        :title="localWriteFeedback"
        class="feedback-alert"
      />

      <el-descriptions border :column="2" class="readback-descriptions">
        <el-descriptions-item label="object_id">{{ currentObjectId || '-' }}</el-descriptions-item>
        <el-descriptions-item label="scenario_tag">{{ draftForm.scenarioTag }}</el-descriptions-item>
        <el-descriptions-item label="readback_total">{{ readbackTotal }}</el-descriptions-item>
        <el-descriptions-item label="residual_records">{{ loopState.residualRecordsAfterRollback }}</el-descriptions-item>
        <el-descriptions-item label="create_success">{{ loopState.createSuccess ? 'true' : 'false' }}</el-descriptions-item>
        <el-descriptions-item label="update_success">{{ loopState.updateSuccess ? 'true' : 'false' }}</el-descriptions-item>
        <el-descriptions-item label="readback_success">{{ loopState.readbackSuccess ? 'true' : 'false' }}</el-descriptions-item>
        <el-descriptions-item label="rollback_success">{{ loopState.rollbackSuccess ? 'true' : 'false' }}</el-descriptions-item>
        <el-descriptions-item label="zero_residual_success">{{ loopState.zeroResidualSuccess ? 'true' : 'false' }}</el-descriptions-item>
        <el-descriptions-item label="test_data_used">true</el-descriptions-item>
      </el-descriptions>

      <el-descriptions
        v-if="readbackState"
        border
        :column="2"
        class="readback-descriptions"
        data-testid="realobj-bom-readback-evidence"
      >
        <el-descriptions-item label="bom_main_readback_success">
          {{ readbackState.readback_flags.bom_main_readback_success ? 'true' : 'false' }}
        </el-descriptions-item>
        <el-descriptions-item label="style_binding_readback_success">
          {{ readbackState.readback_flags.style_binding_readback_success ? 'true' : 'false' }}
        </el-descriptions-item>
        <el-descriptions-item label="fabric_line_readback_success">
          {{ readbackState.readback_flags.fabric_line_readback_success ? 'true' : 'false' }}
        </el-descriptions-item>
        <el-descriptions-item label="trim_line_readback_success">
          {{ readbackState.readback_flags.trim_line_readback_success ? 'true' : 'false' }}
        </el-descriptions-item>
        <el-descriptions-item label="status_validation_readback_success">
          {{ readbackState.readback_flags.status_validation_readback_success ? 'true' : 'false' }}
        </el-descriptions-item>
        <el-descriptions-item label="scenario_tag_present">
          {{ readbackState.readback_flags.scenario_tag_present ? 'true' : 'false' }}
        </el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  createLocalBom,
  fetchBomList,
  fetchLocalBomListSummary,
  fetchLocalBomReadback,
  fetchLocalBomResidualCount,
  rollbackLocalBomScenario,
  updateLocalBom,
  type BomListItem,
  type LocalBomLinePayload as BomLinePayload,
  type LocalBomListSummaryData,
  type LocalBomOperationPayload as BomOperationPayload,
  type LocalBomReadbackData,
  type LocalBomRollbackData,
  type LocalBomUpsertPayload,
} from '@/api/bom'
import { useBomAlternateReadonly } from './composables/useBomAlternateReadonly'
import { useBomAuditDefaultVersionReadonly } from './composables/useBomAuditDefaultVersionReadonly'

type BomStatus = 'draft' | 'review' | 'published'

interface BomRow {
  bomId: number | null
  bomNo: string
  styleCode: string
  styleName: string
  materialGroup: string
  version: string
  owner: string
  status: BomStatus
  updatedAt: string
  isDefault: boolean
}

const router = useRouter()
const route = useRoute()
const { buildBomAlternateListSummary } = useBomAlternateReadonly()
const { buildBomAuditListSummary } = useBomAuditDefaultVersionReadonly()

const a005VerifiedFields = ['款号', '款名', '单位', '面料', '备注', '可打样', '创建人', '修改人']
const a005PartialFields = ['颜色', '尺码', '吊牌价', '创建时间', '修改时间', '设计号', '纸样师']
const a005UnknownFields = ['完整颜色尺码矩阵规则', '设计号生成/录入规则', '纸样师选择规则', '价格规则']
const a005BlockedActions = [
  '样板生成/生成样衣/确定推送',
  '提交',
  '审核',
  '反审核',
  '删除',
  '作废',
  'BOM',
  '生产制单',
  '加工单',
  '库存入库',
  '库存出库',
  '领料',
  '完工',
  '财务收付款',
  '报价/订单联动',
]
const a002StateLabels = ['VERIFIED', 'PARTIAL', 'UNKNOWN', 'NO-GO', 'BLOCKED']
const explicitNonClaimRules = [
  'UI 静态证据不等同业务算法 1:1',
  '报价提交未验证',
  '审核未验证',
  '转订单未验证',
  'mainOrderSaveClicked=false',
  'orderCreated=false',
  'orderNumberGenerated=false',
]

const sourceRows: BomRow[] = [
  {
    bomId: null,
    bomNo: 'BOM-YS-250601-001',
    styleCode: 'LY-WS-2301',
    styleName: '圆领短袖卫衣',
    materialGroup: '针织上装',
    version: 'V2.3',
    owner: '张工',
    status: 'published',
    updatedAt: '2026-05-31 19:40',
    isDefault: true,
  },
  {
    bomId: null,
    bomNo: 'BOM-YS-250601-002',
    styleCode: 'LY-JK-1412',
    styleName: '轻量风衣外套',
    materialGroup: '梭织外套',
    version: 'V1.7',
    owner: '李工',
    status: 'review',
    updatedAt: '2026-05-31 18:22',
    isDefault: false,
  },
  {
    bomId: null,
    bomNo: 'BOM-YS-250601-003',
    styleCode: 'LY-DN-0877',
    styleName: '直筒牛仔裤',
    materialGroup: '牛仔系列',
    version: 'V0.9',
    owner: '王工',
    status: 'draft',
    updatedAt: '2026-05-31 17:58',
    isDefault: false,
  },
]

const buildDatePart = (): string => {
  const now = new Date()
  const yyyy = now.getFullYear()
  const mm = String(now.getMonth() + 1).padStart(2, '0')
  const dd = String(now.getDate()).padStart(2, '0')
  return `${yyyy}${mm}${dd}`
}

const buildDefaultScenarioTag = (): string => `REALOBJ-CAND002-${buildDatePart()}-001`
const normalizeScenarioTag = (value: string): string => value.trim() || buildDefaultScenarioTag()

const query = reactive({
  keyword: '',
  styleCode: '',
  materialGroup: '',
  status: '' as '' | BomStatus,
})

const localWriteLoading = ref(false)
const localWriteFeedback = ref('')
const currentObjectId = ref<number | null>(null)
const readbackState = ref<LocalBomReadbackData | null>(null)
const readbackTotal = ref<number>(0)
const listLoading = ref(false)
const listLoadedFromApi = ref(false)
const listError = ref('')
const apiRows = ref<BomRow[]>([])

const draftForm = reactive({
  scenarioTag: buildDefaultScenarioTag(),
  bomNo: 'BOM-YS-250601-001',
  styleCode: 'LY-WS-2301',
  styleName: '圆领短袖卫衣',
  versionNo: 'V2.3',
  status: 'draft',
  note: 'REALOBJ-CAND-002 test_data',
})

const loopState = reactive({
  createSuccess: false,
  updateSuccess: false,
  readbackSuccess: false,
  rollbackSuccess: false,
  zeroResidualSuccess: false,
  residualRecordsAfterRollback: -1,
})

const bomPayloadState = reactive<{
  fabricLines: BomLinePayload[]
  trimLines: BomLinePayload[]
  operations: BomOperationPayload[]
}>({
  fabricLines: [],
  trimLines: [],
  operations: [],
})

const createFabricLines = (styleCode: string): BomLinePayload[] => [
  {
    material_item_code: `FAB-${styleCode}-001`,
    material_name: '精梳棉汗布',
    style_code: styleCode,
    color: '米白',
    size: 'M',
    qty_per_piece: 1.28,
    loss_rate: 0.04,
    uom: '米',
    remark: '面料行 test_data',
    material_type: 'fabric',
  },
]

const createTrimLines = (styleCode: string): BomLinePayload[] => [
  {
    material_item_code: `TRM-${styleCode}-001`,
    material_name: '树脂纽扣',
    style_code: styleCode,
    color: '米白',
    size: '18L',
    qty_per_piece: 5,
    loss_rate: 0,
    uom: '颗',
    remark: '辅料行 test_data',
    material_type: 'trim',
  },
]

const createDefaultOperations = (): BomOperationPayload[] => [
  {
    process_name: '裁剪',
    sequence_no: 10,
    is_subcontract: false,
    wage_rate: 0,
    subcontract_cost_per_piece: 0,
    remark: 'local-dev default operation',
  },
  {
    process_name: '缝制',
    sequence_no: 20,
    is_subcontract: false,
    wage_rate: 0,
    subcontract_cost_per_piece: 0,
    remark: 'local-dev default operation',
  },
]

const ensurePayloadState = (): void => {
  if (bomPayloadState.fabricLines.length === 0) {
    bomPayloadState.fabricLines = createFabricLines(draftForm.styleCode)
  }
  if (bomPayloadState.trimLines.length === 0) {
    bomPayloadState.trimLines = createTrimLines(draftForm.styleCode)
  }
  if (bomPayloadState.operations.length === 0) {
    bomPayloadState.operations = createDefaultOperations()
  }
}

ensurePayloadState()

const parseParity = (value: unknown): string => {
  const raw = Array.isArray(value) ? value[0] : value
  return typeof raw === 'string' ? raw.trim() : ''
}

const currentParity = computed(() => parseParity(route.query.parity))

const resolveMaterialGroup = (parity: string): string => {
  if (parity === 'material-fabric') return '面料清单'
  if (parity === 'goodsplan-material-samples') return '样板物料'
  if (parity === 'product-style') return '成衣款式'
  return 'BOM'
}

const normalizeBomStatus = (status: string): BomStatus => {
  if (status === 'draft') return 'draft'
  if (status === 'active' || status === 'published') return 'published'
  return 'review'
}

const mapBomListItem = (item: BomListItem): BomRow => ({
  bomId: item.id,
  bomNo: item.bom_no,
  styleCode: item.item_code,
  styleName: item.item_code,
  materialGroup: resolveMaterialGroup(currentParity.value),
  version: item.version_no,
  owner: 'local-dev',
  status: normalizeBomStatus(item.status),
  updatedAt: item.effective_date || '-',
  isDefault: item.is_default,
})

const loadBomList = async (showSuccess = false): Promise<void> => {
  listLoading.value = true
  listError.value = ''
  try {
    const response = await fetchBomList({
      item_code: query.styleCode.trim() || undefined,
      page: 1,
      page_size: 100,
    })
    apiRows.value = response.data.items.map(mapBomListItem)
    listLoadedFromApi.value = true
    if (showSuccess) {
      ElMessage.success(`BOM 列表已刷新，共 ${response.data.total} 条`)
    }
  } catch (error) {
    apiRows.value = []
    listLoadedFromApi.value = false
    listError.value = `BOM 列表读取失败，当前回退到静态壳层：${(error as Error).message}`
    ElMessage.warning(listError.value)
  } finally {
    listLoading.value = false
  }
}

const activeRows = computed(() => (listLoadedFromApi.value ? apiRows.value : sourceRows))

const filteredRows = computed(() => {
  const keyword = query.keyword.trim().toLowerCase()
  const styleCode = query.styleCode.trim().toLowerCase()
  return activeRows.value.filter((row) => {
    const hitKeyword = keyword
      ? [row.bomNo, row.styleCode, row.styleName, row.version].join('|').toLowerCase().includes(keyword)
      : true
    const hitStyleCode = styleCode ? row.styleCode.toLowerCase().includes(styleCode) : true
    const hitGroup = query.materialGroup ? row.materialGroup === query.materialGroup : true
    const hitStatus = query.status ? row.status === query.status : true
    return hitKeyword && hitStyleCode && hitGroup && hitStatus
  })
})

const listReadonlySummary = computed(() => buildBomAlternateListSummary(filteredRows.value.length, currentParity.value))

const bomAuditReadonlySummary = computed(() =>
  buildBomAuditListSummary(filteredRows.value, currentParity.value, listLoadedFromApi.value),
)

const saveButtonLabel = computed(() => (currentObjectId.value ? '更新本地对象' : '保存本地对象'))

const runQuery = () => {
  void loadBomList(true)
}

const resetQuery = () => {
  query.keyword = ''
  query.styleCode = ''
  query.materialGroup = ''
  query.status = ''
  void loadBomList(true)
}

const loadRowToLocalLoop = (row: BomRow) => {
  draftForm.bomNo = row.bomNo
  draftForm.styleCode = row.styleCode
  draftForm.styleName = row.styleName
  draftForm.versionNo = row.version
  draftForm.status = row.status
  draftForm.note = `from:${row.bomNo}`
  bomPayloadState.fabricLines = createFabricLines(row.styleCode)
  bomPayloadState.trimLines = createTrimLines(row.styleCode)
  bomPayloadState.operations = createDefaultOperations()
  ElMessage.info(`已加载 ${row.bomNo} 到本地对象表单`)
}

const goDetail = (row: BomRow) => {
  void router.push({
    path: '/bom/detail',
    query: {
      bom_id: row.bomId ? String(row.bomId) : '',
      bom_no: row.bomNo,
      style_code: row.styleCode,
      style_name: row.styleName,
      version_no: row.version,
      status: row.status,
      object_id: currentObjectId.value ? String(currentObjectId.value) : '',
      scenario_tag: normalizeScenarioTag(draftForm.scenarioTag),
      ...(currentParity.value ? { parity: currentParity.value } : {}),
    },
  })
}

const statusLabel = (status: BomStatus) => {
  if (status === 'draft') return '草稿'
  if (status === 'review') return '审核中'
  return '已发布'
}

const statusType = (status: BomStatus) => {
  if (status === 'draft') return 'info'
  if (status === 'review') return 'warning'
  return 'success'
}

const buildUpsertPayload = (): LocalBomUpsertPayload => {
  const scenarioTag = normalizeScenarioTag(draftForm.scenarioTag)
  draftForm.scenarioTag = scenarioTag
  ensurePayloadState()
  return {
    scenario_tag: scenarioTag,
    bom_main: {
      bom_no: draftForm.bomNo.trim(),
      item_code: draftForm.styleCode.trim(),
      version_no: draftForm.versionNo.trim() || 'V1',
      status: draftForm.status,
      is_default: false,
      style_name: draftForm.styleName.trim(),
      note: draftForm.note.trim(),
    },
    style_binding: {
      style_code: draftForm.styleCode.trim(),
      style_name: draftForm.styleName.trim(),
      style_version: draftForm.versionNo.trim() || 'V1',
      material_group: 'BOM',
      binding_note: 'REALOBJ-CAND-002 local binding',
    },
    fabric_lines: bomPayloadState.fabricLines,
    trim_lines: bomPayloadState.trimLines,
    operations: bomPayloadState.operations,
    note: draftForm.note.trim(),
  }
}

const refreshLocalReadbackSummary = async (scenarioTag: string): Promise<void> => {
  const response = await fetchLocalBomListSummary(scenarioTag)
  const summary: LocalBomListSummaryData = response.data
  readbackTotal.value = summary.total
}

const saveObject = async (): Promise<void> => {
  if (!draftForm.bomNo.trim() || !draftForm.styleCode.trim()) {
    ElMessage.warning('请先填写 BOM 编号与款号')
    return
  }
  localWriteLoading.value = true
  localWriteFeedback.value = ''
  try {
    const payload = buildUpsertPayload()
    const saved = currentObjectId.value
      ? (await updateLocalBom(currentObjectId.value, payload)).data
      : (await createLocalBom(payload)).data
    currentObjectId.value = saved.object_id || saved.draft_id
    readbackState.value = saved
    await refreshLocalReadbackSummary(saved.scenario_tag)
    if (payload && currentObjectId.value && loopState.createSuccess) {
      loopState.updateSuccess = true
    } else if (currentObjectId.value && !loopState.createSuccess) {
      loopState.createSuccess = true
    }
    localWriteFeedback.value = `save_success=true, object_id=${currentObjectId.value}, scenario_tag=${saved.scenario_tag}`
    ElMessage.success('本地对象写入成功')
  } catch (error) {
    localWriteFeedback.value = `保存失败：${(error as Error).message}`
    ElMessage.error(localWriteFeedback.value)
  } finally {
    localWriteLoading.value = false
  }
}

const readbackObject = async (): Promise<void> => {
  if (!currentObjectId.value) {
    ElMessage.warning('请先保存本地对象')
    return
  }
  localWriteLoading.value = true
  try {
    const scenarioTag = normalizeScenarioTag(draftForm.scenarioTag)
    draftForm.scenarioTag = scenarioTag
    const readback = (await fetchLocalBomReadback(currentObjectId.value, scenarioTag)).data
    readbackState.value = readback
    await refreshLocalReadbackSummary(scenarioTag)
    loopState.readbackSuccess = true
    localWriteFeedback.value = `readback_success=true, object_id=${currentObjectId.value}`
    ElMessage.success('本地对象回读成功')
  } catch (error) {
    loopState.readbackSuccess = false
    localWriteFeedback.value = `回读失败：${(error as Error).message}`
    ElMessage.error(localWriteFeedback.value)
  } finally {
    localWriteLoading.value = false
  }
}

const rollbackScenario = async (): Promise<void> => {
  if (!currentObjectId.value) {
    ElMessage.warning('请先保存本地对象')
    return
  }
  localWriteLoading.value = true
  try {
    const scenarioTag = normalizeScenarioTag(draftForm.scenarioTag)
    draftForm.scenarioTag = scenarioTag
    const rolled: LocalBomRollbackData = (await rollbackLocalBomScenario(currentObjectId.value, scenarioTag)).data
    loopState.rollbackSuccess = rolled.rollback_success
    loopState.zeroResidualSuccess = rolled.zero_residual_success
    loopState.residualRecordsAfterRollback = rolled.residual_records_after_rollback
    currentObjectId.value = null
    readbackState.value = null
    readbackTotal.value = 0
    localWriteFeedback.value = `rollback_success=${rolled.rollback_success}, zero_residual_success=${rolled.zero_residual_success}, residual=${rolled.residual_records_after_rollback}`
    ElMessage.success('scenario 回滚完成')
  } catch (error) {
    loopState.rollbackSuccess = false
    localWriteFeedback.value = `回滚失败：${(error as Error).message}`
    ElMessage.error(localWriteFeedback.value)
  } finally {
    localWriteLoading.value = false
  }
}

const checkZeroResidual = async (): Promise<void> => {
  const scenarioTag = normalizeScenarioTag(draftForm.scenarioTag)
  draftForm.scenarioTag = scenarioTag
  localWriteLoading.value = true
  try {
    const total = (await fetchLocalBomResidualCount(scenarioTag)).data.total
    await refreshLocalReadbackSummary(scenarioTag)
    loopState.residualRecordsAfterRollback = total
    loopState.zeroResidualSuccess = total === 0
    localWriteFeedback.value = `zero_residual_check: scenario_tag=${scenarioTag}, residual=${total}`
    if (total === 0) {
      ElMessage.success('zero_residual 校验通过')
    } else {
      ElMessage.warning(`zero_residual 未通过，残留 ${total} 条`)
    }
  } catch (error) {
    loopState.zeroResidualSuccess = false
    localWriteFeedback.value = `zero_residual 校验失败：${(error as Error).message}`
    ElMessage.error(localWriteFeedback.value)
  } finally {
    localWriteLoading.value = false
  }
}

onMounted(() => {
  void loadBomList()
})
</script>

<style scoped>
.bom-list-shell {
  display: grid;
  gap: 12px;
}

.bom-header-card,
.filter-card,
.local-write-panel {
  border-radius: 6px;
}

.header-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.header-main {
  min-width: 0;
}

.page-title {
  margin: 0;
  font-size: 18px;
  line-height: 1.3;
  color: #1f2a37;
}

.page-subtitle {
  margin: 6px 0 0;
  font-size: 13px;
  color: #6b7280;
}

.header-actions {
  display: inline-flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.source-readback {
  margin-top: 10px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #4b5563;
}

.status-legend {
  margin-top: 4px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.contract-boundary-card {
  border-radius: 6px;
}

.contract-header {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.contract-grid {
  display: grid;
  gap: 12px;
}

.contract-block h4 {
  margin: 0 0 8px;
  font-size: 13px;
  color: #1f2937;
}

.contract-block ul {
  margin: 0;
  padding-left: 18px;
  color: #4b5563;
  font-size: 12px;
  line-height: 1.5;
}

.tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tag-row.compact {
  margin-top: 8px;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.local-write-actions {
  margin-top: 6px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.feedback-alert {
  margin-top: 10px;
}

.readback-descriptions {
  margin-top: 10px;
}
</style>
