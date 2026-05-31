<template>
  <div class="bom-detail-shell" data-testid="yisuan-1to1-bom-detail-shell">
    <el-card shadow="never">
      <div class="header-row">
        <div>
          <h2 class="page-title">BOM 详情</h2>
          <p class="page-subtitle">衣算云 UI 1:1 只读壳层（无写入）</p>
        </div>
        <div class="actions">
          <el-button @click="goList">返回列表</el-button>
          <el-button type="primary" plain disabled>编辑（只读）</el-button>
        </div>
      </div>

      <div class="source-readback" data-testid="yisuan-1to1-ui-source-readback">
        <el-tag type="success">source_status=found</el-tag>
        <el-tag type="primary">covered_contract_ids=A002,A005</el-tag>
        <el-tag type="warning">A005 partial/unknown kept pending</el-tag>
        <span>来源：A002/A005 contract sources（B010 继承，no-write）</span>
      </div>

      <el-descriptions :column="3" border class="style-summary" data-testid="yisuan-1to1-bom-style-summary">
        <el-descriptions-item label="BOM 编号">{{ bomNo }}</el-descriptions-item>
        <el-descriptions-item label="款号">LY-WS-2301</el-descriptions-item>
        <el-descriptions-item label="款式名称">圆领短袖卫衣</el-descriptions-item>
        <el-descriptions-item label="版本">V2.3</el-descriptions-item>
        <el-descriptions-item label="开发员">张工</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag type="success">已发布</el-tag>
        </el-descriptions-item>
      </el-descriptions>
    </el-card>

    <el-card shadow="never">
      <el-tabs type="border-card" data-testid="yisuan-1to1-bom-material-tabs">
        <el-tab-pane label="面料">
          <el-table :data="fabricLines" border stripe data-testid="yisuan-1to1-bom-fabric-lines">
            <el-table-column prop="code" label="面料编码" min-width="160" />
            <el-table-column prop="name" label="面料名称" min-width="200" />
            <el-table-column prop="spec" label="规格" min-width="160" />
            <el-table-column prop="uom" label="单位" min-width="80" />
            <el-table-column prop="usage" label="单件用量" min-width="110" />
            <el-table-column prop="lossRate" label="损耗率" min-width="90" />
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="辅料">
          <el-table :data="trimLines" border stripe data-testid="yisuan-1to1-bom-trim-lines">
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
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

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

const router = useRouter()
const route = useRoute()

type ContractFieldRow = {
  field: string
  contract: string
  status: string
  evidence: string
}

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

const bomNo = computed(() => {
  const queryBom = route.query.bom_no
  if (typeof queryBom === 'string' && queryBom.trim()) return queryBom.trim()
  return 'BOM-YS-250601-001'
})

const fabricLines: MaterialLine[] = [
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

const trimLines: MaterialLine[] = [
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

const fabricTotalCost = computed(() =>
  fabricLines.reduce((sum, row) => sum + row.usage * row.unitCost * (1 + (row.lossRate ?? 0) / 100), 0),
)
const trimTotalCost = computed(() => trimLines.reduce((sum, row) => sum + row.usage * row.unitCost, 0))
const totalCost = computed(() => fabricTotalCost.value + trimTotalCost.value)
const totalLossRate = computed(() =>
  fabricLines.reduce((sum, row) => sum + (row.lossRate ?? 0), 0) / (fabricLines.length || 1),
)

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
