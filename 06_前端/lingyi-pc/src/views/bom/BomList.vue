<template>
  <div class="bom-list-shell" data-testid="yisuan-1to1-bom-list-shell">
    <el-card shadow="never" class="bom-header-card">
      <div class="header-row">
        <div class="header-main">
          <h2 class="page-title">物料开发 BOM 列表</h2>
          <p class="page-subtitle">衣算云 UI 1:1 只读壳层（无写入）</p>
        </div>
        <div class="header-actions" data-testid="yisuan-1to1-bom-list-toolbar">
          <el-button type="primary" @click="runQuery">查询</el-button>
          <el-button @click="resetQuery">重置</el-button>
        </div>
      </div>

      <div class="source-readback" data-testid="yisuan-1to1-ui-source-readback">
        <el-tag type="success">source_status=found</el-tag>
        <el-tag type="primary">covered_contract_ids=A002,A005</el-tag>
        <el-tag type="info">real_business_object_created=false</el-tag>
        <el-tag type="info">linked_calculation_enabled=false</el-tag>
        <span>来源：A002/A005 contract sources（B010 继承，no-write）</span>
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
              {{ field }} => source_unknown / not_claimed
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

    <el-card shadow="never">
      <el-table
        :data="filteredRows"
        border
        height="520"
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
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="goDetail(row.bomNo)">查看详情</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive } from 'vue'
import { useRouter } from 'vue-router'

type BomStatus = 'draft' | 'review' | 'published'

interface BomRow {
  bomNo: string
  styleCode: string
  styleName: string
  materialGroup: string
  version: string
  owner: string
  status: BomStatus
  updatedAt: string
}

const router = useRouter()

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
    bomNo: 'BOM-YS-250601-001',
    styleCode: 'LY-WS-2301',
    styleName: '圆领短袖卫衣',
    materialGroup: '针织上装',
    version: 'V2.3',
    owner: '张工',
    status: 'published',
    updatedAt: '2026-05-31 19:40',
  },
  {
    bomNo: 'BOM-YS-250601-002',
    styleCode: 'LY-JK-1412',
    styleName: '轻量风衣外套',
    materialGroup: '梭织外套',
    version: 'V1.7',
    owner: '李工',
    status: 'review',
    updatedAt: '2026-05-31 18:22',
  },
  {
    bomNo: 'BOM-YS-250601-003',
    styleCode: 'LY-DN-0877',
    styleName: '直筒牛仔裤',
    materialGroup: '牛仔系列',
    version: 'V0.9',
    owner: '王工',
    status: 'draft',
    updatedAt: '2026-05-31 17:58',
  },
]

const query = reactive({
  keyword: '',
  styleCode: '',
  materialGroup: '',
  status: '' as '' | BomStatus,
})

const filteredRows = computed(() => {
  const keyword = query.keyword.trim().toLowerCase()
  const styleCode = query.styleCode.trim().toLowerCase()
  return sourceRows.filter((row) => {
    const hitKeyword = keyword
      ? [row.bomNo, row.styleCode, row.styleName, row.version].join('|').toLowerCase().includes(keyword)
      : true
    const hitStyleCode = styleCode ? row.styleCode.toLowerCase().includes(styleCode) : true
    const hitGroup = query.materialGroup ? row.materialGroup === query.materialGroup : true
    const hitStatus = query.status ? row.status === query.status : true
    return hitKeyword && hitStyleCode && hitGroup && hitStatus
  })
})

const runQuery = () => {
  // UI parity no-write: query is handled by local computed filtering.
}

const resetQuery = () => {
  query.keyword = ''
  query.styleCode = ''
  query.materialGroup = ''
  query.status = ''
}

const goDetail = (bomNo: string) => {
  void router.push({ path: '/bom/detail', query: { bom_no: bomNo } })
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
</script>

<style scoped>
.bom-list-shell {
  display: grid;
  gap: 12px;
}

.bom-header-card,
.filter-card {
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
</style>
