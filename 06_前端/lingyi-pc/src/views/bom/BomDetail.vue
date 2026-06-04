<template>
  <div class="bom-detail-shell" data-testid="yisuan-1to1-bom-detail-shell">
    <el-card shadow="never">
      <div class="header-row">
        <div>
          <h2 class="page-title">BOM 详情</h2>
          <p class="page-subtitle">衣算云 UI 1:1 + REALOBJ-CAND-002 回读壳层（local-dev only）</p>
        </div>
        <div class="actions">
          <el-button @click="goList">返回列表</el-button>
          <el-button :disabled="!localReadbackRef.objectId" :loading="localReadbackRef.loading" @click="refreshLocalReadback">
            刷新本地回读
          </el-button>
        </div>
      </div>

      <div class="source-readback" data-testid="yisuan-1to1-ui-source-readback">
        <el-tag type="success">source_status=found</el-tag>
        <el-tag type="primary">covered_contract_ids=A002,A005</el-tag>
        <el-tag type="warning">A005 partial/unknown kept pending</el-tag>
        <span>来源：A002/A005 contract sources（B010 继承，B011 local write/readback）</span>
      </div>

      <el-alert v-if="detailRef.error" type="warning" :closable="false" :title="detailRef.error" class="readback-descriptions" />

      <el-descriptions :column="3" border class="style-summary" data-testid="yisuan-1to1-bom-style-summary">
        <el-descriptions-item label="BOM 编号">{{ bomNo }}</el-descriptions-item>
        <el-descriptions-item label="款号">{{ displayStyleCode }}</el-descriptions-item>
        <el-descriptions-item label="款式名称">{{ displayStyleName }}</el-descriptions-item>
        <el-descriptions-item label="版本">{{ displayVersion }}</el-descriptions-item>
        <el-descriptions-item label="开发员">张工</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="statusType(displayStatus)">{{ statusLabel(displayStatus) }}</el-tag>
        </el-descriptions-item>
      </el-descriptions>
    </el-card>

    <el-card shadow="never" data-testid="realobj-bom-detail-local-readback">
      <template #header>
        <div class="panel-header">
          <span>REALOBJ-CAND-002 本地对象回读</span>
          <el-tag type="info">local-dev/sqlite/scenario_tag/test_data only</el-tag>
        </div>
      </template>

      <el-alert
        v-if="localReadbackRef.error"
        type="warning"
        :closable="false"
        :title="localReadbackRef.error"
      />
      <el-alert
        v-else-if="!localReadbackRef.data"
        type="info"
        :closable="false"
        title="未携带 object_id/scenario_tag，当前显示静态回读壳层。"
      />

      <el-descriptions
        v-if="localReadbackRef.data"
        border
        :column="2"
        class="readback-descriptions"
        data-testid="realobj-bom-main-readback"
      >
        <el-descriptions-item label="object_id">{{ localReadbackRef.data.object_id }}</el-descriptions-item>
        <el-descriptions-item label="scenario_tag">{{ localReadbackRef.data.scenario_tag }}</el-descriptions-item>
        <el-descriptions-item label="bom_main_readback_success">
          {{ localReadbackRef.data.readback_flags.bom_main_readback_success ? 'true' : 'false' }}
        </el-descriptions-item>
        <el-descriptions-item label="style_binding_readback_success">
          {{ localReadbackRef.data.readback_flags.style_binding_readback_success ? 'true' : 'false' }}
        </el-descriptions-item>
        <el-descriptions-item label="fabric_line_readback_success">
          {{ localReadbackRef.data.readback_flags.fabric_line_readback_success ? 'true' : 'false' }}
        </el-descriptions-item>
        <el-descriptions-item label="trim_line_readback_success">
          {{ localReadbackRef.data.readback_flags.trim_line_readback_success ? 'true' : 'false' }}
        </el-descriptions-item>
        <el-descriptions-item label="status_validation_readback_success">
          {{ localReadbackRef.data.readback_flags.status_validation_readback_success ? 'true' : 'false' }}
        </el-descriptions-item>
        <el-descriptions-item label="scenario_tag_present">
          {{ localReadbackRef.data.readback_flags.scenario_tag_present ? 'true' : 'false' }}
        </el-descriptions-item>
      </el-descriptions>
    </el-card>

    <el-card shadow="never">
      <el-tabs type="border-card" data-testid="yisuan-1to1-bom-material-tabs">
        <el-tab-pane label="面料">
          <el-table :data="displayFabricLines" border stripe data-testid="yisuan-1to1-bom-fabric-lines">
            <el-table-column prop="code" label="面料编码" min-width="160" />
            <el-table-column prop="name" label="面料名称" min-width="200" />
            <el-table-column prop="spec" label="规格" min-width="160" />
            <el-table-column prop="uom" label="单位" min-width="80" />
            <el-table-column prop="usage" label="单件用量" min-width="110" />
            <el-table-column prop="lossRate" label="损耗率" min-width="90" />
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="辅料">
          <el-table :data="displayTrimLines" border stripe data-testid="yisuan-1to1-bom-trim-lines">
            <el-table-column prop="code" label="辅料编码" min-width="160" />
            <el-table-column prop="name" label="辅料名称" min-width="200" />
            <el-table-column prop="spec" label="规格" min-width="160" />
            <el-table-column prop="uom" label="单位" min-width="80" />
            <el-table-column prop="usage" label="单件用量" min-width="110" />
            <el-table-column prop="remark" label="备注" min-width="180" />
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <el-card shadow="never" data-testid="cand164-bom-alternate-readonly-panel">
      <template #header>
        <div class="panel-header">
          <span>BOM 颜色尺码 / 替代料只读回读</span>
          <div class="tag-row compact">
            <el-tag :type="bomAlternateReadonlyView.readonlySourceType" effect="plain">
              {{ bomAlternateReadonlyView.readonlySourceTag }}
            </el-tag>
            <el-tag :type="bomAlternateReadonlyView.coverageType" effect="plain">
              {{ bomAlternateReadonlyView.coverageLabel }}
            </el-tag>
            <el-tag type="warning" effect="plain">{{ bomAlternateReadonlyView.parityScopeLabel }}</el-tag>
          </div>
        </div>
      </template>

      <div class="cost-grid">
        <div
          v-for="field in BOM_COLOR_SIZE_SUMMARY_FIELDS"
          :key="field.key"
          class="metric"
        >
          <span class="metric-label">{{ field.label }}</span>
          <strong class="metric-value">{{ bomSummaryValue(field.key) }}</strong>
        </div>
      </div>

      <el-alert
        type="info"
        :closable="false"
        :title="bomAlternateReadonlyView.readonlyGuardReason"
        class="readback-descriptions"
        data-testid="cand164-bom-readonly-guard"
      />

      <el-alert
        v-if="bomAlternateReadonlyView.missingAlternatePrompt"
        type="warning"
        :closable="false"
        :title="bomAlternateReadonlyView.missingAlternatePrompt"
        class="readback-descriptions"
        data-testid="cand164-bom-missing-alternate-prompt"
      />

      <el-table
        :data="bomAlternateReadonlyView.colorSizeUsageRows"
        border
        stripe
        class="readback-descriptions"
        data-testid="cand164-bom-color-size-usage-table"
      >
        <el-table-column prop="color" label="颜色" min-width="120" />
        <el-table-column prop="size" label="尺码" min-width="120" />
        <el-table-column prop="totalUsageLabel" label="用量汇总" min-width="120" />
        <el-table-column prop="materialCount" label="物料行数" min-width="120" />
        <el-table-column prop="sourceTag" label="来源标签" min-width="160" />
      </el-table>

      <el-table
        :data="bomAlternateReadonlyView.alternateRows"
        border
        stripe
        class="readback-descriptions"
        data-testid="cand164-bom-alternate-material-table"
      >
        <el-table-column prop="materialLabel" label="物料" min-width="220" />
        <el-table-column prop="colorSizeLabel" label="颜色 / 尺码" min-width="150" />
        <el-table-column label="替代料状态" min-width="150">
          <template #default="{ row }">
            <el-tag :type="bomAlternateStateType(row.alternateState)" effect="plain">
              {{ row.alternateStateLabel }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="alternateMaterialLabel" label="替代料" min-width="180" />
        <el-table-column prop="sourceTag" label="来源标签" min-width="140" />
        <el-table-column prop="note" label="备注" min-width="220" />
      </el-table>

      <el-alert
        type="warning"
        :closable="false"
        :title="bomAlternateReadonlyView.remainingGap"
        class="readback-descriptions"
        data-testid="cand164-bom-remaining-gap"
      />
    </el-card>

    <el-card shadow="never" data-testid="yisuan-1to1-bom-cost-usage-panel">
      <template #header>
        <div class="panel-header">
          <span>成本 / 用量概览</span>
          <el-tag type="info">只读展示</el-tag>
        </div>
      </template>

      <div class="cost-grid">
        <div class="metric">
          <span class="metric-label">面料总成本</span>
          <strong class="metric-value">¥ {{ fabricTotalCost.toFixed(2) }}</strong>
        </div>
        <div class="metric">
          <span class="metric-label">辅料总成本</span>
          <strong class="metric-value">¥ {{ trimTotalCost.toFixed(2) }}</strong>
        </div>
        <div class="metric">
          <span class="metric-label">单位件估算</span>
          <strong class="metric-value">¥ {{ totalCost.toFixed(2) }}</strong>
        </div>
        <div class="metric">
          <span class="metric-label">总损耗系数</span>
          <strong class="metric-value">{{ totalLossRate.toFixed(2) }}%</strong>
        </div>
      </div>
    </el-card>

    <el-card shadow="never" class="contract-card">
      <template #header>
        <div class="panel-header">
          <span>合同字段与规则回读（A002/A005）</span>
          <el-tag type="danger" effect="plain">not_claimed_for_unknown_fields</el-tag>
        </div>
      </template>

      <el-table :data="contractFieldRows" border stripe class="contract-field-table" data-testid="yisuan-contract-fields-observation">
        <el-table-column prop="field" label="字段" min-width="160" />
        <el-table-column prop="contract" label="合同来源" min-width="130" />
        <el-table-column prop="status" label="状态" min-width="170" />
        <el-table-column prop="evidence" label="页面策略" min-width="220" />
      </el-table>

      <div class="contract-block" data-testid="yisuan-contract-validation-rules">
        <h4>validation_rules</h4>
        <ul>
          <li v-for="field in a005UnknownFields" :key="`unknown-${field}`">
            {{ field }} => source_unknown / pending_confirmation / not_claimed
          </li>
        </ul>
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
        <div class="tag-row compact">
          <el-tag v-for="action in a005BlockedActions" :key="`blocked-${action}`" type="danger" effect="plain">
            {{ action }} blocked
          </el-tag>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  fetchBomDetail,
  fetchLocalBomReadback,
  type BomDetailData,
  type LocalBomReadbackData,
} from '@/api/bom'
import { BOM_COLOR_SIZE_SUMMARY_FIELDS } from './constants/bomAlternateMaterialFields'
import { useBomAlternateReadonly } from './composables/useBomAlternateReadonly'

interface MaterialLine {
  code: string
  name: string
  spec: string
  uom: string
  usage: number
  lossRate?: number
  remark?: string
  unitCost: number
}

type ContractFieldRow = {
  field: string
  contract: string
  status: string
  evidence: string
}

const router = useRouter()
const route = useRoute()
const { bomAlternateStateType, buildBomAlternateDetailView } = useBomAlternateReadonly()

const a002StateLabels = ['VERIFIED', 'PARTIAL', 'UNKNOWN', 'NO-GO', 'BLOCKED']
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
const a005UnknownFields = ['完整颜色尺码矩阵规则', '设计号生成/录入规则', '纸样师选择规则', '价格规则']
const explicitNonClaimRules = [
  'UI 静态证据不等同业务算法 1:1',
  '报价提交未验证',
  '审核未验证',
  '转订单未验证',
  'mainOrderSaveClicked=false',
  'orderCreated=false',
  'orderNumberGenerated=false',
]
const contractFieldRows: ContractFieldRow[] = [
  { field: '款号', contract: 'A005', status: 'VERIFIED', evidence: '主信息区直接回读' },
  { field: '款名', contract: 'A005', status: 'VERIFIED', evidence: '主信息区直接回读' },
  { field: '单位', contract: 'A005', status: 'VERIFIED', evidence: '物料明细单位列' },
  { field: '面料', contract: 'A005', status: 'VERIFIED', evidence: '面料 Tab 明细' },
  { field: '备注', contract: 'A005', status: 'VERIFIED', evidence: '辅料 Tab 备注列' },
  { field: '可打样', contract: 'A005', status: 'VERIFIED', evidence: '只读标记展示' },
  { field: '创建人/修改人', contract: 'A005', status: 'VERIFIED', evidence: '主信息区展示' },
  { field: '颜色/尺码', contract: 'A005', status: 'PARTIAL pending_confirmation', evidence: '标注未确认，不参与联动计算' },
  { field: '吊牌价', contract: 'A005', status: 'PARTIAL pending_confirmation', evidence: '仅状态占位，禁止宣称已确认' },
  { field: '设计号/纸样师', contract: 'A005', status: 'PARTIAL pending_confirmation', evidence: '保留为待确认字段' },
  { field: '只读壳层规则', contract: 'A002', status: 'VERIFIED', evidence: '无写入按钮，无真实对象创建' },
]

const localReadbackRef = reactive<{
  loading: boolean
  data: LocalBomReadbackData | null
  error: string
  objectId: number | null
  scenarioTag: string
}>({
  loading: false,
  data: null,
  error: '',
  objectId: null,
  scenarioTag: '',
})

const detailRef = reactive<{
  loading: boolean
  data: BomDetailData | null
  error: string
  bomId: number | null
}>({
  loading: false,
  data: null,
  error: '',
  bomId: null,
})

const parseObjectId = (value: unknown): number | null => {
  const raw = Array.isArray(value) ? value[0] : value
  const parsed = Number(raw)
  if (!Number.isFinite(parsed) || parsed <= 0) return null
  return Math.floor(parsed)
}

const parseScenarioTag = (value: unknown): string => {
  const raw = Array.isArray(value) ? value[0] : value
  return typeof raw === 'string' ? raw.trim() : ''
}

const parseTextQuery = (value: unknown): string => {
  const raw = Array.isArray(value) ? value[0] : value
  return typeof raw === 'string' ? raw.trim() : ''
}

const bomIdFromQuery = computed<number | null>(() => parseObjectId(route.query.bom_id))
const objectIdFromQuery = computed<number | null>(() => parseObjectId(route.query.object_id))
const scenarioTagFromQuery = computed<string>(() => parseScenarioTag(route.query.scenario_tag))
const styleNameFromQuery = computed<string>(() => parseTextQuery(route.query.style_name))
const parityFromQuery = computed<string>(() => parseTextQuery(route.query.parity))

const bomNo = computed(() => {
  if (detailRef.data?.bom.bom_no) return detailRef.data.bom.bom_no
  const queryBom = route.query.bom_no
  if (typeof queryBom === 'string' && queryBom.trim()) return queryBom.trim()
  if (localReadbackRef.data?.bom_main.bom_no) return localReadbackRef.data.bom_main.bom_no
  return 'BOM-YS-250601-001'
})

const staticFabricLines: MaterialLine[] = [
  {
    code: 'FAB-CT-0021',
    name: '32支精梳棉汗布',
    spec: '185g / 米白',
    uom: 'KG',
    usage: 0.62,
    lossRate: 3.5,
    unitCost: 38.4,
  },
  {
    code: 'FAB-RB-0012',
    name: '1x1 罗纹',
    spec: '袖口/下摆',
    uom: 'KG',
    usage: 0.11,
    lossRate: 2.8,
    unitCost: 29.8,
  },
]

const staticTrimLines: MaterialLine[] = [
  {
    code: 'TRM-LB-1022',
    name: '主唛+洗水唛套组',
    spec: '国标成分标签',
    uom: 'SET',
    usage: 1,
    remark: '同款共版',
    unitCost: 0.85,
  },
  {
    code: 'TRM-PK-2010',
    name: '包装袋',
    spec: 'PE 自粘袋',
    uom: 'PCS',
    usage: 1,
    remark: '含条码贴',
    unitCost: 0.48,
  },
]

const isFabricMaterial = (materialItemCode: string, remark?: string | null): boolean => {
  const remarkText = (remark || '').trim()
  if (remarkText.includes('面料')) return true
  const token = materialItemCode.replace('_', '-').split('-', 1)[0].trim().toUpperCase()
  return token === 'FAB' || token === 'FABRIC' || token === 'CLOTH'
}

const toMaterialLine = (line: LocalBomReadbackData['fabric_lines'][number]): MaterialLine => ({
  code: line.material_item_code,
  name: line.material_name || line.remark || '-',
  spec: [line.color, line.size || ''].filter(Boolean).join(' / ') || '-',
  uom: line.uom || 'PCS',
  usage: Number(line.qty_per_piece || 0),
  lossRate: Number(line.loss_rate || 0) * 100,
  remark: line.remark || '',
  unitCost: 0,
})

const toDetailMaterialLine = (line: BomDetailData['items'][number]): MaterialLine => ({
  code: line.material_item_code,
  name: line.remark || line.material_item_code,
  spec: [line.color, line.size || ''].filter(Boolean).join(' / ') || '-',
  uom: line.uom || 'PCS',
  usage: Number(line.qty_per_piece || 0),
  lossRate: Number(line.loss_rate || 0) * 100,
  remark: line.remark || '',
  unitCost: 0,
})

const detailFabricLines = computed<MaterialLine[]>(() => {
  if (!detailRef.data?.items?.length) return []
  return detailRef.data.items.filter((line) => isFabricMaterial(line.material_item_code, line.remark)).map(toDetailMaterialLine)
})

const detailTrimLines = computed<MaterialLine[]>(() => {
  if (!detailRef.data?.items?.length) return []
  return detailRef.data.items.filter((line) => !isFabricMaterial(line.material_item_code, line.remark)).map(toDetailMaterialLine)
})

const displayFabricLines = computed<MaterialLine[]>(() => {
  if (detailFabricLines.value.length) {
    return detailFabricLines.value
  }
  if (localReadbackRef.data?.fabric_lines?.length) {
    return localReadbackRef.data.fabric_lines.map(toMaterialLine)
  }
  return staticFabricLines
})

const displayTrimLines = computed<MaterialLine[]>(() => {
  if (detailTrimLines.value.length) {
    return detailTrimLines.value
  }
  if (localReadbackRef.data?.trim_lines?.length) {
    return localReadbackRef.data.trim_lines.map(toMaterialLine)
  }
  return staticTrimLines
})

const displayStyleCode = computed(() => detailRef.data?.bom.item_code || localReadbackRef.data?.style_binding.style_code || 'LY-WS-2301')
const displayStyleName = computed(
  () => styleNameFromQuery.value || localReadbackRef.data?.style_binding.style_name || detailRef.data?.bom.item_code || '圆领短袖卫衣',
)
const displayVersion = computed(() => detailRef.data?.bom.version_no || localReadbackRef.data?.bom_main.version_no || 'V2.3')
const displayStatus = computed(() => detailRef.data?.bom.status || localReadbackRef.data?.bom_main.status || 'published')

const statusLabel = (status: string) => {
  if (status === 'draft') return '草稿'
  if (status === 'review') return '审核中'
  return '已发布'
}

const statusType = (status: string) => {
  if (status === 'draft') return 'info'
  if (status === 'review') return 'warning'
  return 'success'
}

const fabricTotalCost = computed(() =>
  displayFabricLines.value.reduce((sum, row) => sum + row.usage * row.unitCost * (1 + (row.lossRate ?? 0) / 100), 0),
)
const trimTotalCost = computed(() => displayTrimLines.value.reduce((sum, row) => sum + row.usage * row.unitCost, 0))
const totalCost = computed(() => fabricTotalCost.value + trimTotalCost.value)
const totalLossRate = computed(() =>
  displayFabricLines.value.reduce((sum, row) => sum + (row.lossRate ?? 0), 0) / (displayFabricLines.value.length || 1),
)

const bomAlternateReadonlyView = computed(() =>
  buildBomAlternateDetailView(detailRef.data, localReadbackRef.data, parityFromQuery.value),
)

const bomSummaryValue = (
  key: (typeof BOM_COLOR_SIZE_SUMMARY_FIELDS)[number]['key'],
): string => {
  switch (key) {
    case 'skuCount':
      return String(bomAlternateReadonlyView.value.skuCount)
    case 'materialCount':
      return String(bomAlternateReadonlyView.value.materialCount)
    case 'alternateCount':
      return String(bomAlternateReadonlyView.value.alternateCount)
    case 'parityScopeLabel':
      return bomAlternateReadonlyView.value.parityScopeLabel
    default:
      return '-'
  }
}

const refreshRemoteDetail = async () => {
  const bomId = bomIdFromQuery.value
  detailRef.bomId = bomId
  if (!bomId) {
    detailRef.data = null
    detailRef.error = ''
    return
  }

  detailRef.loading = true
  detailRef.error = ''
  try {
    detailRef.data = (await fetchBomDetail(bomId)).data
  } catch (error) {
    detailRef.data = null
    detailRef.error = `BOM 详情读取失败：${(error as Error).message}`
    ElMessage.warning(detailRef.error)
  } finally {
    detailRef.loading = false
  }
}

const refreshLocalReadback = async () => {
  const objectId = objectIdFromQuery.value
  const scenarioTag = scenarioTagFromQuery.value
  localReadbackRef.objectId = objectId
  localReadbackRef.scenarioTag = scenarioTag
  if (!objectId || !scenarioTag) {
    localReadbackRef.data = null
    localReadbackRef.error = ''
    return
  }

  localReadbackRef.loading = true
  localReadbackRef.error = ''
  try {
    localReadbackRef.data = (await fetchLocalBomReadback(objectId, scenarioTag)).data
  } catch (error) {
    localReadbackRef.data = null
    localReadbackRef.error = `本地回读失败：${(error as Error).message}`
    ElMessage.warning(localReadbackRef.error)
  } finally {
    localReadbackRef.loading = false
  }
}

watch([bomIdFromQuery, objectIdFromQuery, scenarioTagFromQuery], () => {
  void refreshRemoteDetail()
  void refreshLocalReadback()
})

onMounted(() => {
  void refreshRemoteDetail()
  void refreshLocalReadback()
})

const goList = () => {
  void router.push('/bom/list')
}
</script>

<style scoped>
.bom-detail-shell {
  display: grid;
  gap: 12px;
}

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
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

.actions {
  display: inline-flex;
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

.style-summary {
  margin-top: 10px;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.readback-descriptions {
  margin-top: 10px;
}

.cost-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.metric {
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 10px;
  background: #fbfcfe;
}

.metric-label {
  display: block;
  font-size: 12px;
  color: #6b7280;
}

.metric-value {
  margin-top: 6px;
  display: block;
  font-size: 18px;
  color: #111827;
  letter-spacing: 0;
}

.contract-card {
  border-radius: 6px;
}

.contract-field-table {
  margin-bottom: 12px;
}

.contract-block {
  margin-top: 10px;
}

.contract-block h4 {
  margin: 0 0 8px;
  font-size: 13px;
  color: #1f2937;
}

.contract-block ul {
  margin: 0;
  padding-left: 18px;
  font-size: 12px;
  color: #4b5563;
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

@media (max-width: 1180px) {
  .cost-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
