<template>
  <div class="basic-reference-page" data-testid="yisuan-1to1-reference-shell">
    <el-card shadow="never">
      <template #header>
        <div class="header-row" data-testid="yisuan-1to1-reference-toolbar">
          <div class="title-group">
            <span class="title">基础资料引用中心</span>
            <span class="sub-title">MVP-CAND-002 / 本地可用闭环</span>
            <el-tag
              v-if="foundationCustomerParityHint"
              size="small"
              type="info"
              effect="plain"
              class="parity-hint"
            >
              {{ foundationCustomerParityHint }}
            </el-tag>
          </div>
          <div class="header-actions">
            <el-button size="small" @click="readbackDraft" :disabled="!currentDraftId">回读草稿</el-button>
            <el-button size="small" @click="checkZeroResidual">校验零残留</el-button>
          </div>
        </div>
      </template>

      <el-alert
        type="info"
        :closable="false"
        title="本页提供客户/仓库/供应商/加工厂/物料引用查询与本地草稿闭环。所有写入仅走 local-dev/sqlite/scenario_tag，不连接生产。"
        class="scope-alert"
      />
      <section class="contract-merge-panel" data-testid="contract-cand001-source-readback">
        <div class="contract-merge-title">A001/A003 契约合并回读</div>
        <div class="contract-tag-row">
          <span class="contract-inline-label">covered_contract_ids:</span>
          <el-tag
            v-for="contractId in coveredContractIds"
            :key="contractId"
            size="small"
            effect="plain"
            type="success"
            class="contract-id-tag"
          >
            {{ contractId }}
          </el-tag>
          <el-tag size="small" effect="plain" type="info">A001-A006 contract merge scope=true</el-tag>
        </div>
        <div class="contract-readback-grid">
          <el-card shadow="never" class="contract-readback-card" data-testid="contract-source-files-readback">
            <template #header>contract source readback</template>
            <ul>
              <li v-for="sourceFile in contractSourceFiles" :key="sourceFile">{{ sourceFile }}</li>
            </ul>
          </el-card>
          <el-card shadow="never" class="contract-readback-card" data-testid="contract-key-fields-readback">
            <template #header>key_fields</template>
            <ul>
              <li v-for="field in contractKeyFields" :key="field">{{ field }}</li>
            </ul>
          </el-card>
          <el-card shadow="never" class="contract-readback-card" data-testid="contract-validation-rules-readback">
            <template #header>validation_rules</template>
            <ul>
              <li v-for="rule in contractValidationRules" :key="rule">{{ rule }}</li>
            </ul>
          </el-card>
          <el-card shadow="never" class="contract-readback-card" data-testid="contract-status-rules-readback">
            <template #header>status_rules / readonly_readback</template>
            <ul>
              <li v-for="rule in contractStatusAndReadonlyRules" :key="rule">{{ rule }}</li>
            </ul>
          </el-card>
        </div>
      </section>

      <section class="query-panel" data-testid="yisuan-1to1-reference-filter-panel">
        <el-form :model="query" :inline="true">
          <el-form-item label="关键字">
            <el-input
              v-model="query.keyword"
              clearable
              placeholder="编码/名称/联系人"
              data-testid="mvp-basic-query-keyword"
            />
          </el-form-item>
          <el-form-item label="类别">
            <el-select v-model="query.category" clearable placeholder="全部" style="width: 130px">
              <el-option label="全部" value="" />
              <el-option label="客户" value="customer" />
              <el-option label="仓库" value="warehouse" />
              <el-option label="供应商" value="supplier" />
              <el-option label="加工厂" value="factory" />
              <el-option label="物料引用" value="material" />
            </el-select>
          </el-form-item>
          <el-form-item label="状态">
            <el-select v-model="query.status" clearable placeholder="全部" style="width: 120px">
              <el-option label="全部" value="" />
              <el-option label="active" value="active" />
              <el-option label="inactive" value="inactive" />
              <el-option label="draft" value="draft" />
            </el-select>
          </el-form-item>
          <el-form-item label="仓库联动">
            <el-input v-model="query.warehouse" clearable placeholder="仓库编码/名称" />
          </el-form-item>
          <el-form-item label="物料联动">
            <el-input v-model="query.material" clearable placeholder="物料编码/名称" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="applyQuery">查询</el-button>
            <el-button @click="resetQuery">重置</el-button>
          </el-form-item>
        </el-form>
      </section>

      <el-tabs v-model="activeTab" class="tabs" data-testid="mvp-basic-reference-tabs">
        <el-tab-pane label="客户引用" name="customer">
          <section data-testid="yisuan-1to1-reference-customer-list">
            <el-table :data="displayRows.customer" border>
              <el-table-column prop="code" label="客户编码" min-width="130" />
              <el-table-column prop="name" label="客户名称" min-width="150" />
              <el-table-column prop="contact" label="联系人" min-width="120" />
              <el-table-column prop="phone" label="电话" min-width="130" />
              <el-table-column label="状态" width="120">
                <template #default="{ row }">
                  <el-tag :type="statusTagType(row.status)" effect="plain">{{ row.status }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="120">
                <template #default="{ row }">
                  <el-button link type="primary" @click="loadRowToDraft(row)">写入草稿</el-button>
                </template>
              </el-table-column>
            </el-table>
          </section>
        </el-tab-pane>

        <el-tab-pane label="仓库引用" name="warehouse">
          <section data-testid="mvp-basic-warehouse-reference">
            <el-table :data="displayRows.warehouse" border>
              <el-table-column prop="code" label="仓库编码" min-width="130" />
              <el-table-column prop="name" label="仓库名称" min-width="150" />
              <el-table-column prop="warehouseType" label="仓库类型" min-width="120" />
              <el-table-column prop="address" label="仓库地址" min-width="200" />
              <el-table-column label="状态" width="120">
                <template #default="{ row }">
                  <el-tag :type="statusTagType(row.status)" effect="plain">{{ row.status }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="120">
                <template #default="{ row }">
                  <el-button link type="primary" @click="loadRowToDraft(row)">写入草稿</el-button>
                </template>
              </el-table-column>
            </el-table>
          </section>
        </el-tab-pane>

        <el-tab-pane label="供应商引用" name="supplier">
          <section data-testid="yisuan-1to1-reference-supplier-list">
            <el-table :data="displayRows.supplier" border>
              <el-table-column prop="code" label="供应商编码" min-width="130" />
              <el-table-column prop="name" label="供应商名称" min-width="150" />
              <el-table-column prop="materialCategory" label="物料类别" min-width="120" />
              <el-table-column prop="contact" label="联系方式" min-width="160" />
              <el-table-column label="状态" width="120">
                <template #default="{ row }">
                  <el-tag :type="statusTagType(row.status)" effect="plain">{{ row.status }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="120">
                <template #default="{ row }">
                  <el-button link type="primary" @click="loadRowToDraft(row)">写入草稿</el-button>
                </template>
              </el-table-column>
            </el-table>
          </section>
        </el-tab-pane>

        <el-tab-pane label="加工厂引用" name="factory">
          <section data-testid="mvp-basic-factory-reference">
            <el-table :data="displayRows.factory" border>
              <el-table-column prop="code" label="加工厂编码" min-width="130" />
              <el-table-column prop="name" label="加工厂名称" min-width="150" />
              <el-table-column prop="processCapability" label="工序能力" min-width="140" />
              <el-table-column prop="contact" label="联系方式" min-width="160" />
              <el-table-column label="状态" width="120">
                <template #default="{ row }">
                  <el-tag :type="statusTagType(row.status)" effect="plain">{{ row.status }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="120">
                <template #default="{ row }">
                  <el-button link type="primary" @click="loadRowToDraft(row)">写入草稿</el-button>
                </template>
              </el-table-column>
            </el-table>
          </section>
        </el-tab-pane>

        <el-tab-pane label="物料引用" name="material">
          <section data-testid="yisuan-1to1-reference-material-list">
            <el-table :data="displayRows.material" border>
              <el-table-column prop="code" label="物料编码" min-width="140" />
              <el-table-column prop="name" label="物料名称" min-width="150" />
              <el-table-column prop="materialCategory" label="类别" min-width="120" />
              <el-table-column prop="unit" label="单位" min-width="90" />
              <el-table-column prop="defaultWarehouse" label="默认仓库" min-width="140" />
              <el-table-column label="状态" width="120">
                <template #default="{ row }">
                  <el-tag :type="statusTagType(row.status)" effect="plain">{{ row.status }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="120">
                <template #default="{ row }">
                  <el-button link type="primary" @click="loadRowToDraft(row)">写入草稿</el-button>
                </template>
              </el-table-column>
            </el-table>
          </section>
        </el-tab-pane>
      </el-tabs>

      <el-empty
        v-show="activeRows.length === 0"
        data-testid="yisuan-1to1-basic-data-empty-state"
        description="当前筛选下暂无基础资料数据"
      />

      <el-alert
        data-testid="yisuan-1to1-ui-source-readback"
        type="info"
        :closable="false"
        title="UI source readback: incremental capture + G0 baseline（基础资料）"
        class="scope-alert"
      />

      <section class="local-write-panel" data-testid="mvp-basic-local-draft">
        <div class="local-write-title">本地草稿写闭环（local-dev/sqlite/scenario_tag）</div>
        <el-form :inline="true" :model="draftForm">
          <el-form-item label="scenario_tag">
            <el-input v-model="draftForm.scenarioTag" style="width: 220px" data-testid="mvp-basic-scenario-tag" />
          </el-form-item>
          <el-form-item label="类别">
            <el-select v-model="draftForm.category" style="width: 130px">
              <el-option label="客户" value="customer" />
              <el-option label="仓库" value="warehouse" />
              <el-option label="供应商" value="supplier" />
              <el-option label="加工厂" value="factory" />
              <el-option label="物料引用" value="material" />
            </el-select>
          </el-form-item>
          <el-form-item label="编码">
            <el-input v-model="draftForm.referenceCode" style="width: 150px" />
          </el-form-item>
          <el-form-item label="名称">
            <el-input v-model="draftForm.referenceName" style="width: 180px" />
          </el-form-item>
          <el-form-item label="状态">
            <el-input v-model="draftForm.status" style="width: 120px" />
          </el-form-item>
          <el-form-item label="关键字段">
            <el-input v-model="draftForm.keyField" style="width: 210px" />
          </el-form-item>
          <el-form-item label="仓库联动">
            <el-input v-model="draftForm.linkageWarehouse" style="width: 150px" />
          </el-form-item>
          <el-form-item label="物料联动">
            <el-input v-model="draftForm.linkageMaterial" style="width: 150px" />
          </el-form-item>
          <el-form-item label="备注">
            <el-input v-model="draftForm.note" style="width: 240px" />
          </el-form-item>
        </el-form>

        <div class="local-write-actions" data-testid="mvp-basic-local-save-cancel-readback">
          <el-button type="primary" :loading="localWriteLoading" @click="saveDraft">保存草稿</el-button>
          <el-button :loading="localWriteLoading" :disabled="!currentDraftId" @click="cancelDraft">取消草稿</el-button>
          <el-button :loading="localWriteLoading" :disabled="!currentDraftId" @click="readbackDraft">回读草稿</el-button>
        </div>

        <div class="local-write-actions" data-testid="mvp-basic-rollback-zero-residual">
          <el-button :loading="localWriteLoading" @click="rollbackScenario">回滚 scenario</el-button>
          <el-button :loading="localWriteLoading" @click="checkZeroResidual">zero_residual 校验</el-button>
        </div>

        <el-alert v-if="localWriteFeedback" type="info" :closable="false" :title="localWriteFeedback" class="scope-alert" />

        <el-descriptions v-if="draftState" border :column="2" class="draft-state">
          <el-descriptions-item label="draft_id">{{ draftState.draft_id }}</el-descriptions-item>
          <el-descriptions-item label="scenario_tag">{{ draftState.scenario_tag }}</el-descriptions-item>
          <el-descriptions-item label="category">{{ draftState.category }}</el-descriptions-item>
          <el-descriptions-item label="state">{{ draftState.state }}</el-descriptions-item>
          <el-descriptions-item label="reference_code">{{ draftState.reference_code }}</el-descriptions-item>
          <el-descriptions-item label="updated_at">{{ draftState.updated_at }}</el-descriptions-item>
        </el-descriptions>

        <el-descriptions border :column="2" class="draft-state">
          <el-descriptions-item label="save_success">{{ loopState.saveSuccess ? 'true' : 'false' }}</el-descriptions-item>
          <el-descriptions-item label="cancel_success">{{ loopState.cancelSuccess ? 'true' : 'false' }}</el-descriptions-item>
          <el-descriptions-item label="readback_success">{{ loopState.readbackSuccess ? 'true' : 'false' }}</el-descriptions-item>
          <el-descriptions-item label="rollback_success">{{ loopState.rollbackSuccess ? 'true' : 'false' }}</el-descriptions-item>
          <el-descriptions-item label="zero_residual_success">{{ loopState.zeroResidualSuccess ? 'true' : 'false' }}</el-descriptions-item>
          <el-descriptions-item label="residual_records_after_rollback">{{ loopState.residualRecordsAfterRollback }}</el-descriptions-item>
        </el-descriptions>
      </section>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { request, type ApiResponse } from '@/api/request'

type ReferenceCategory = 'customer' | 'warehouse' | 'supplier' | 'factory' | 'material'
type ReferenceStatus = 'active' | 'inactive' | 'draft'

interface ReferenceRecord {
  category: ReferenceCategory
  code: string
  name: string
  status: ReferenceStatus
  keyField: string
  contact?: string
  phone?: string
  warehouseType?: string
  address?: string
  materialCategory?: string
  processCapability?: string
  unit?: string
  defaultWarehouse?: string
  linkageWarehouse?: string
  linkageMaterial?: string
}

interface BasicReferenceDraftData {
  draft_id: number
  scenario_tag: string
  category: ReferenceCategory
  reference_code: string
  reference_name: string
  status: string
  key_field: string
  linkage_warehouse: string
  linkage_material: string
  note: string
  state: 'saved' | 'cancelled'
  created_at: string
  updated_at: string
  cancelled_at: string | null
  cancel_reason: string | null
}

interface BasicReferenceDraftPayload {
  draft_id?: number
  scenario_tag: string
  category: ReferenceCategory
  reference_code: string
  reference_name: string
  status: string
  key_field: string
  linkage_warehouse?: string
  linkage_material?: string
  note?: string
}

interface BasicReferenceCancelPayload {
  scenario_tag: string
  reason?: string
}

interface BasicReferenceRollbackPayload {
  scenario_tag: string
}

interface BasicReferenceRollbackData {
  scenario_tag: string
  deleted_count: number
  residual_records_after_rollback: number
  rollback_success: boolean
  zero_residual_success: boolean
}

interface BasicReferenceResidualData {
  scenario_tag: string
  total: number
}

const route = useRoute()
const activeTab = ref<ReferenceCategory>('customer')
const localWriteLoading = ref<boolean>(false)
const localWriteFeedback = ref<string>('')
const currentDraftId = ref<number | null>(null)
const draftState = ref<BasicReferenceDraftData | null>(null)

const query = reactive({
  keyword: '',
  category: '',
  status: '',
  warehouse: '',
  material: '',
})

const loopState = reactive({
  saveSuccess: false,
  cancelSuccess: false,
  readbackSuccess: false,
  rollbackSuccess: false,
  zeroResidualSuccess: false,
  residualRecordsAfterRollback: -1,
})

const buildDatePart = (): string => {
  const now = new Date()
  const yyyy = now.getFullYear()
  const mm = String(now.getMonth() + 1).padStart(2, '0')
  const dd = String(now.getDate()).padStart(2, '0')
  return `${yyyy}${mm}${dd}`
}

const buildDefaultScenarioTag = (): string => `MVP-BASIC-${buildDatePart()}-001`

const draftForm = reactive({
  scenarioTag: buildDefaultScenarioTag(),
  category: 'customer' as ReferenceCategory,
  referenceCode: '',
  referenceName: '',
  status: 'draft',
  keyField: '',
  linkageWarehouse: '',
  linkageMaterial: '',
  note: '',
})

const foundationCustomerParityHint = computed<string>(() => {
  const parity = String(route.query.parity || '').trim().toLowerCase()
  return parity === 'foundation-customer' ? '衣算云 / 基础资料 / 客户（parity=foundation-customer）' : ''
})

const coveredContractIds: string[] = ['A001', 'A003']
const contractSourceFiles: string[] = [
  '04_测试与验收/测试证据/yisuan_business_shadow_capture/YISUAN_CAP_A001_evidence_coverage_matrix_20260520/evidence_coverage_matrix.json',
  '04_测试与验收/测试证据/yisuan_business_shadow_capture/YISUAN_CAP_A003_ui_route_field_button_readonly_contract_20260520/ui_contract_development_input.json',
]
const contractKeyFields: string[] = [
  '协同状态/状态/停用默认为否',
  '简称/全称/客户等级/联系人/业务员/电话',
  '结算方式/银行及账户/开票类型/开票信息/协同账号/地址',
  'customer:简称 / supplier:简称 / factory:简称',
  'fabric:名称 / fabric:类型 / fabric:用量单位',
  'warehouse parity readback / warehouse summary status',
]
const contractValidationRules: string[] = [
  'ui_shell_only=true',
  'can_use_for_action_logic=false',
  '高风险按钮仅展示，不实现动作',
  '高风险语义必须标记为 BLOCKED/UNKNOWN',
  '保留 /foundation/warehouse -> /warehouse?parity=foundation-warehouse',
]
const contractStatusAndReadonlyRules: string[] = [
  '状态定义: VERIFIED / PARTIAL / UNKNOWN / NO-GO / BLOCKED',
  '只读展示: 保存/提交/审核/删除/作废/生成类动作禁用',
  'readback 仅限展示层，不创建真实业务对象',
  'contract source readback present=true',
]

const referenceSeeds: ReferenceRecord[] = [
  {
    category: 'customer',
    code: 'CUS-001',
    name: '华东直营客户',
    status: 'active',
    keyField: '联系人:王敏',
    contact: '王敏',
    phone: '13800001111',
    linkageWarehouse: 'WH-FG-01',
    linkageMaterial: 'MAT-FAB-001',
  },
  {
    category: 'customer',
    code: 'CUS-002',
    name: '华南分销客户',
    status: 'inactive',
    keyField: '联系人:李泽',
    contact: '李泽',
    phone: '13900002222',
    linkageWarehouse: 'WH-FG-02',
    linkageMaterial: 'MAT-ACC-008',
  },
  {
    category: 'warehouse',
    code: 'WH-FG-01',
    name: '成品中心仓',
    status: 'active',
    keyField: '启用状态:启用',
    warehouseType: '成品仓',
    address: '苏州园区A-01',
    linkageWarehouse: 'WH-FG-01',
  },
  {
    category: 'warehouse',
    code: 'WH-MAT-02',
    name: '面辅料周转仓',
    status: 'draft',
    keyField: '启用状态:草稿',
    warehouseType: '物料仓',
    address: '苏州园区B-02',
    linkageWarehouse: 'WH-MAT-02',
  },
  {
    category: 'supplier',
    code: 'SUP-001',
    name: '远纺面料',
    status: 'active',
    keyField: '物料类别:面料',
    materialCategory: '面料',
    contact: '陈工 / 021-88990011',
    linkageMaterial: 'MAT-FAB-001',
    linkageWarehouse: 'WH-MAT-02',
  },
  {
    category: 'supplier',
    code: 'SUP-002',
    name: '合盛辅料',
    status: 'active',
    keyField: '物料类别:辅料',
    materialCategory: '辅料',
    contact: '周工 / 021-88990022',
    linkageMaterial: 'MAT-ACC-008',
    linkageWarehouse: 'WH-MAT-02',
  },
  {
    category: 'factory',
    code: 'FAC-001',
    name: '锦程加工厂',
    status: 'active',
    keyField: '工序能力:缝制+整烫',
    processCapability: '缝制+整烫',
    contact: '周主管 / 13700003333',
    linkageMaterial: 'MAT-FAB-001',
  },
  {
    category: 'factory',
    code: 'FAC-002',
    name: '博雅加工厂',
    status: 'inactive',
    keyField: '工序能力:裁剪',
    processCapability: '裁剪',
    contact: '韩主管 / 13700004444',
    linkageMaterial: 'MAT-ACC-008',
  },
  {
    category: 'material',
    code: 'MAT-FAB-001',
    name: '精梳棉布 230g',
    status: 'active',
    keyField: '默认仓库:WH-MAT-02',
    materialCategory: '面料',
    unit: '米',
    defaultWarehouse: 'WH-MAT-02',
    linkageWarehouse: 'WH-MAT-02',
    linkageMaterial: 'MAT-FAB-001',
  },
  {
    category: 'material',
    code: 'MAT-ACC-008',
    name: '树脂纽扣 18L',
    status: 'draft',
    keyField: '默认仓库:WH-MAT-02',
    materialCategory: '辅料',
    unit: '颗',
    defaultWarehouse: 'WH-MAT-02',
    linkageWarehouse: 'WH-MAT-02',
    linkageMaterial: 'MAT-ACC-008',
  },
]

const filterRows = (category: ReferenceCategory): ReferenceRecord[] => {
  const keyword = query.keyword.trim().toLowerCase()
  const status = query.status.trim().toLowerCase()
  const categoryFilter = query.category.trim().toLowerCase()
  const warehouse = query.warehouse.trim().toLowerCase()
  const material = query.material.trim().toLowerCase()

  return referenceSeeds.filter((row) => {
    if (row.category !== category) return false
    if (categoryFilter && row.category !== categoryFilter) return false
    if (status && row.status.toLowerCase() !== status) return false
    if (keyword) {
      const merged = [
        row.code,
        row.name,
        row.contact || '',
        row.phone || '',
        row.keyField,
      ].join('|').toLowerCase()
      if (!merged.includes(keyword)) return false
    }
    if (warehouse) {
      const mergedWarehouse = [
        row.linkageWarehouse || '',
        row.defaultWarehouse || '',
        row.address || '',
      ].join('|').toLowerCase()
      if (!mergedWarehouse.includes(warehouse)) return false
    }
    if (material) {
      const mergedMaterial = [
        row.linkageMaterial || '',
        row.materialCategory || '',
        row.name,
      ].join('|').toLowerCase()
      if (!mergedMaterial.includes(material)) return false
    }
    return true
  })
}

const displayRows = computed(() => ({
  customer: filterRows('customer'),
  warehouse: filterRows('warehouse'),
  supplier: filterRows('supplier'),
  factory: filterRows('factory'),
  material: filterRows('material'),
}))

const activeRows = computed<ReferenceRecord[]>(() => {
  const rows = displayRows.value[activeTab.value as keyof typeof displayRows.value]
  return Array.isArray(rows) ? rows : []
})

const statusTagType = (status: string): 'success' | 'warning' | 'info' => {
  if (status === 'active') return 'success'
  if (status === 'inactive') return 'warning'
  return 'info'
}

const applyQuery = (): void => {
  ElMessage.success('筛选已应用')
}

const resetQuery = (): void => {
  query.keyword = ''
  query.category = ''
  query.status = ''
  query.warehouse = ''
  query.material = ''
  ElMessage.success('筛选条件已重置')
}

const loadRowToDraft = (row: ReferenceRecord): void => {
  activeTab.value = row.category
  draftForm.category = row.category
  draftForm.referenceCode = row.code
  draftForm.referenceName = row.name
  draftForm.status = row.status
  draftForm.keyField = row.keyField
  draftForm.linkageWarehouse = row.linkageWarehouse || row.defaultWarehouse || ''
  draftForm.linkageMaterial = row.linkageMaterial || row.code
  draftForm.note = `from:${row.category}`
  ElMessage.info(`已加载 ${row.code} 到本地草稿表单`)
}

const postDraft = async (payload: BasicReferenceDraftPayload): Promise<BasicReferenceDraftData> => {
  const response = await request<BasicReferenceDraftData>('/api/local-dev/basic-reference-drafts', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  return response.data
}

const getDraft = async (draftId: number): Promise<BasicReferenceDraftData> => {
  const response = await request<BasicReferenceDraftData>(`/api/local-dev/basic-reference-drafts/${draftId}`)
  return response.data
}

const cancelDraftRequest = async (draftId: number, payload: BasicReferenceCancelPayload): Promise<BasicReferenceDraftData> => {
  const response = await request<BasicReferenceDraftData>(`/api/local-dev/basic-reference-drafts/${draftId}/cancel`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  return response.data
}

const rollbackScenarioRequest = async (payload: BasicReferenceRollbackPayload): Promise<BasicReferenceRollbackData> => {
  const response = await request<BasicReferenceRollbackData>('/api/local-dev/basic-reference-drafts/rollback-by-scenario', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  return response.data
}

const fetchResidualCount = async (scenarioTag: string): Promise<number> => {
  const queryString = new URLSearchParams({ scenario_tag: scenarioTag }).toString()
  const response = await request<BasicReferenceResidualData>(`/api/local-dev/basic-reference-drafts/residual-count?${queryString}`)
  return response.data.total
}

const normalizeScenarioTag = (value: string): string => {
  const trimmed = value.trim()
  return trimmed || buildDefaultScenarioTag()
}

const saveDraft = async (): Promise<void> => {
  const scenarioTag = normalizeScenarioTag(draftForm.scenarioTag)
  draftForm.scenarioTag = scenarioTag
  if (!draftForm.referenceCode.trim() || !draftForm.referenceName.trim()) {
    ElMessage.warning('请先填写引用编码和名称')
    return
  }
  localWriteLoading.value = true
  localWriteFeedback.value = ''
  try {
    const payload: BasicReferenceDraftPayload = {
      draft_id: currentDraftId.value || undefined,
      scenario_tag: scenarioTag,
      category: draftForm.category,
      reference_code: draftForm.referenceCode.trim(),
      reference_name: draftForm.referenceName.trim(),
      status: draftForm.status.trim() || 'draft',
      key_field: draftForm.keyField.trim() || '-',
      linkage_warehouse: draftForm.linkageWarehouse.trim(),
      linkage_material: draftForm.linkageMaterial.trim(),
      note: draftForm.note.trim(),
    }
    const saved = await postDraft(payload)
    currentDraftId.value = saved.draft_id
    draftState.value = saved
    loopState.saveSuccess = true
    localWriteFeedback.value = `save_success=true, draft_id=${saved.draft_id}, scenario_tag=${saved.scenario_tag}`
    ElMessage.success('本地草稿保存成功')
  } catch (error) {
    loopState.saveSuccess = false
    localWriteFeedback.value = `保存失败：${(error as Error).message}`
    ElMessage.error(localWriteFeedback.value)
  } finally {
    localWriteLoading.value = false
  }
}

const cancelDraft = async (): Promise<void> => {
  if (!currentDraftId.value) {
    ElMessage.warning('请先保存草稿')
    return
  }
  localWriteLoading.value = true
  try {
    const cancelled = await cancelDraftRequest(currentDraftId.value, {
      scenario_tag: normalizeScenarioTag(draftForm.scenarioTag),
      reason: `CANCEL-${normalizeScenarioTag(draftForm.scenarioTag)}`,
    })
    draftState.value = cancelled
    loopState.cancelSuccess = true
    localWriteFeedback.value = `cancel_success=true, state=${cancelled.state}`
    ElMessage.success('草稿取消成功')
  } catch (error) {
    loopState.cancelSuccess = false
    localWriteFeedback.value = `取消失败：${(error as Error).message}`
    ElMessage.error(localWriteFeedback.value)
  } finally {
    localWriteLoading.value = false
  }
}

const readbackDraft = async (): Promise<void> => {
  if (!currentDraftId.value) {
    ElMessage.warning('请先保存草稿')
    return
  }
  localWriteLoading.value = true
  try {
    const readback = await getDraft(currentDraftId.value)
    draftState.value = readback
    loopState.readbackSuccess = true
    localWriteFeedback.value = `readback_success=true, draft_id=${readback.draft_id}, state=${readback.state}`
    ElMessage.success('草稿回读成功')
  } catch (error) {
    loopState.readbackSuccess = false
    localWriteFeedback.value = `回读失败：${(error as Error).message}`
    ElMessage.error(localWriteFeedback.value)
  } finally {
    localWriteLoading.value = false
  }
}

const rollbackScenario = async (): Promise<void> => {
  const scenarioTag = normalizeScenarioTag(draftForm.scenarioTag)
  localWriteLoading.value = true
  try {
    const rolled = await rollbackScenarioRequest({ scenario_tag: scenarioTag })
    loopState.rollbackSuccess = rolled.rollback_success
    loopState.zeroResidualSuccess = rolled.zero_residual_success
    loopState.residualRecordsAfterRollback = rolled.residual_records_after_rollback
    if (rolled.zero_residual_success) {
      currentDraftId.value = null
      draftState.value = null
    }
    localWriteFeedback.value = `rollback_success=${rolled.rollback_success}, zero_residual_success=${rolled.zero_residual_success}, residual=${rolled.residual_records_after_rollback}`
    ElMessage.success('scenario 回滚已执行')
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
  localWriteLoading.value = true
  try {
    const total = await fetchResidualCount(scenarioTag)
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
</script>

<style scoped>
.basic-reference-page {
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

.title-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.title {
  font-size: 16px;
  font-weight: 600;
}

.sub-title {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.parity-hint {
  align-self: flex-start;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.scope-alert {
  margin-top: 10px;
}

.contract-merge-panel {
  margin-top: 12px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  padding: 12px;
  background: #f7fafc;
}

.contract-merge-title {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 8px;
}

.contract-tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  margin-bottom: 10px;
}

.contract-inline-label {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.contract-id-tag {
  letter-spacing: 0;
}

.contract-readback-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 8px;
}

.contract-readback-card ul {
  margin: 0;
  padding-left: 18px;
}

.contract-readback-card li {
  margin: 4px 0;
  line-height: 1.35;
}

.query-panel {
  margin-top: 12px;
  padding: 10px 12px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  background: var(--el-fill-color-lighter);
}

.tabs {
  margin-top: 12px;
}

.local-write-panel {
  margin-top: 16px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  padding: 12px;
  background: #fafafa;
}

.local-write-title {
  font-weight: 600;
  margin-bottom: 10px;
}

.local-write-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 10px;
}

.draft-state {
  margin-top: 8px;
}
</style>
