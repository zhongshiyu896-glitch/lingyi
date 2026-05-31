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
        <span>来源：incremental capture / G0 baseline（B018 继承）</span>
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

@media (max-width: 1180px) {
  .cost-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
