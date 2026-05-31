<template>
  <div class="bom-detail-page" data-testid="bom-detail-page">
    <el-card shadow="never" data-testid="mvp-bom-master-card">
      <template #header>
        <div class="header-row">
          <span class="title">BOM 详情（本地可用闭环）</span>
          <el-button data-testid="bom-detail-back" @click="goBack">返回列表</el-button>
        </div>
      </template>

      <el-alert
        v-if="loadError"
        :title="loadError"
        type="error"
        show-icon
        :closable="false"
        data-testid="bom-detail-load-error"
      />

      <template v-else>
        <el-form label-width="130px">
          <el-form-item label="BOM 编号">
            <el-input :model-value="bomNo || '-'" disabled />
          </el-form-item>
          <el-form-item label="款式编码">
            <el-input v-model="form.item_code" />
          </el-form-item>
          <el-form-item label="版本号">
            <el-input v-model="form.version_no" />
          </el-form-item>
          <el-form-item label="状态">
            <el-tag>{{ statusText }}</el-tag>
          </el-form-item>
          <el-form-item label="默认 BOM">
            <el-tag :type="isDefault ? 'success' : 'info'">{{ isDefault ? '是' : '否' }}</el-tag>
          </el-form-item>
        </el-form>

        <el-alert
          title="所有写入仅走 local-dev/sqlite/scenario_tag，生产写入口保持禁用。"
          type="info"
          show-icon
          :closable="false"
          data-testid="bom-local-write-policy"
          data-readonly-boundary="true"
          data-write-request-success-allowed="false"
          data-real-write-action-added="false"
        />

        <section class="style-binding-section" data-testid="mvp-bom-style-binding">
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item label="款式 -> BOM">{{ form.item_code || '-' }} -> {{ bomNo || '-' }}</el-descriptions-item>
            <el-descriptions-item label="BOM -> 面料">{{ fabricCount }} 条</el-descriptions-item>
            <el-descriptions-item label="BOM -> 辅料">{{ trimCount }} 条</el-descriptions-item>
            <el-descriptions-item label="scenario_tag">{{ localDraftForm.scenario_tag || '-' }}</el-descriptions-item>
          </el-descriptions>
        </section>
      </template>
    </el-card>

    <el-card shadow="never" data-testid="bom-detail-list-editable-card">
      <template #header>
        <div class="card-header">
          <span>BOM 明细绑定</span>
          <div class="header-actions">
            <el-button size="small" @click="addFabricLine">新增面料</el-button>
            <el-button size="small" @click="addTrimLine">新增辅料</el-button>
            <el-button size="small" @click="addOperationLine">新增工序</el-button>
          </div>
        </div>
      </template>

      <el-table :data="bomItems" border empty-text="暂无 BOM 物料明细">
        <el-table-column label="物料编码" min-width="180">
          <template #default="scope">
            <el-input v-model="scope.row.material_item_code" />
            <span
              v-if="isFabricLine(scope.row) && firstFabricId === scope.row.id"
              class="anchor-mark"
              data-testid="mvp-bom-fabric-line"
            />
            <span
              v-if="isTrimLine(scope.row) && firstTrimId === scope.row.id"
              class="anchor-mark"
              data-testid="mvp-bom-trim-line"
            />
          </template>
        </el-table-column>
        <el-table-column label="颜色" min-width="100">
          <template #default="scope">
            <el-input v-model="scope.row.color" />
          </template>
        </el-table-column>
        <el-table-column label="尺码" min-width="90">
          <template #default="scope">
            <el-input v-model="scope.row.size" />
          </template>
        </el-table-column>
        <el-table-column label="单耗" min-width="100">
          <template #default="scope">
            <el-input-number v-model="scope.row.qty_per_piece" :precision="4" :step="0.1" :min="0.0001" />
          </template>
        </el-table-column>
        <el-table-column label="损耗率" min-width="100">
          <template #default="scope">
            <el-input-number v-model="scope.row.loss_rate" :precision="4" :step="0.01" :min="0" />
          </template>
        </el-table-column>
        <el-table-column label="单位" min-width="90">
          <template #default="scope">
            <el-input v-model="scope.row.uom" />
          </template>
        </el-table-column>
        <el-table-column label="备注" min-width="160">
          <template #default="scope">
            <el-input v-model="scope.row.remark" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="90">
          <template #default="scope">
            <el-button link type="danger" @click="removeMaterial(scope.$index)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-divider />

      <el-table :data="operations" border empty-text="暂无 BOM 工序明细">
        <el-table-column label="工序名称" min-width="160">
          <template #default="scope">
            <el-input v-model="scope.row.process_name" />
          </template>
        </el-table-column>
        <el-table-column label="序号" width="90">
          <template #default="scope">
            <el-input-number v-model="scope.row.sequence_no" :min="1" :step="1" />
          </template>
        </el-table-column>
        <el-table-column label="外发" width="100">
          <template #default="scope">
            <el-switch v-model="scope.row.is_subcontract" />
          </template>
        </el-table-column>
        <el-table-column label="本厂工价" min-width="120">
          <template #default="scope">
            <el-input-number v-model="scope.row.wage_rate" :min="0" :precision="2" :step="0.1" />
          </template>
        </el-table-column>
        <el-table-column label="外发单价" min-width="120">
          <template #default="scope">
            <el-input-number v-model="scope.row.subcontract_cost_per_piece" :min="0" :precision="2" :step="0.1" />
          </template>
        </el-table-column>
        <el-table-column label="备注" min-width="160">
          <template #default="scope">
            <el-input v-model="scope.row.remark" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="90">
          <template #default="scope">
            <el-button link type="danger" @click="removeOperation(scope.$index)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card shadow="never" data-testid="mvp-bom-local-draft">
      <template #header>
        <div class="card-header">
          <span>本地草稿写闭环（local-dev/sqlite/scenario_tag）</span>
          <el-tag type="warning">test_data</el-tag>
        </div>
      </template>

      <el-form :inline="true" label-width="120px">
        <el-form-item label="scenario_tag">
          <el-input v-model="localDraftForm.scenario_tag" style="width: 300px" data-testid="bom-local-scenario-tag" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="localDraftForm.note" style="width: 340px" data-testid="bom-local-note" />
        </el-form-item>
      </el-form>

      <div class="local-actions">
        <el-button
          type="primary"
          :loading="localWriteLoading"
          data-testid="mvp-bom-local-save"
          @click="saveLocalDraft"
        >
          保存本地草稿
        </el-button>
        <el-button
          :loading="localWriteLoading"
          data-testid="mvp-bom-local-cancel"
          @click="cancelLocalDraft"
        >
          取消草稿
        </el-button>
        <el-button
          :loading="localWriteLoading"
          data-testid="mvp-bom-local-readback"
          @click="readbackLocalDraft"
        >
          回读草稿
        </el-button>
        <el-button
          type="danger"
          plain
          :loading="localWriteLoading"
          data-testid="mvp-bom-rollback-zero-residual"
          @click="rollbackScenario"
        >
          rollback + zero_residual
        </el-button>
      </div>

      <el-alert
        v-if="localWriteFeedback"
        :title="localWriteFeedback"
        type="info"
        show-icon
        :closable="false"
        class="feedback-alert"
      />

      <el-descriptions :column="2" border size="small">
        <el-descriptions-item label="draft_id">{{ currentDraftId || '-' }}</el-descriptions-item>
        <el-descriptions-item label="scenario_tag">{{ localDraftForm.scenario_tag || '-' }}</el-descriptions-item>
        <el-descriptions-item label="save_success">{{ String(loopState.saveSuccess) }}</el-descriptions-item>
        <el-descriptions-item label="draft_id_created">{{ String(loopState.draftIdCreated) }}</el-descriptions-item>
        <el-descriptions-item label="fabric_line_saved">{{ String(loopState.fabricLineSaved) }}</el-descriptions-item>
        <el-descriptions-item label="trim_line_saved">{{ String(loopState.trimLineSaved) }}</el-descriptions-item>
        <el-descriptions-item label="cancel_success">{{ String(loopState.cancelSuccess) }}</el-descriptions-item>
        <el-descriptions-item label="readback_success">{{ String(loopState.readbackSuccess) }}</el-descriptions-item>
        <el-descriptions-item label="rollback_success">{{ String(loopState.rollbackSuccess) }}</el-descriptions-item>
        <el-descriptions-item label="zero_residual_success">{{ String(loopState.zeroResidualSuccess) }}</el-descriptions-item>
        <el-descriptions-item label="residual_records_after_rollback">
          {{ loopState.residualRecordsAfterRollback }}
        </el-descriptions-item>
        <el-descriptions-item label="data_classification">test_data</el-descriptions-item>
        <el-descriptions-item label="seed_data_used">false</el-descriptions-item>
        <el-descriptions-item label="sqlite_not_formal_database">true</el-descriptions-item>
        <el-descriptions-item label="sqlite_direct_reuse_for_production_forbidden">true</el-descriptions-item>
      </el-descriptions>

      <div class="loop-metrics">
        <span class="anchor-mark" data-testid="mvp-bom-loop-save-success">{{ String(loopState.saveSuccess) }}</span>
        <span class="anchor-mark" data-testid="mvp-bom-loop-draft-id-created">{{ String(loopState.draftIdCreated) }}</span>
        <span class="anchor-mark" data-testid="mvp-bom-loop-fabric-line-saved">{{ String(loopState.fabricLineSaved) }}</span>
        <span class="anchor-mark" data-testid="mvp-bom-loop-trim-line-saved">{{ String(loopState.trimLineSaved) }}</span>
        <span class="anchor-mark" data-testid="mvp-bom-loop-cancel-success">{{ String(loopState.cancelSuccess) }}</span>
        <span class="anchor-mark" data-testid="mvp-bom-loop-readback-success">{{ String(loopState.readbackSuccess) }}</span>
        <span class="anchor-mark" data-testid="mvp-bom-loop-rollback-success">{{ String(loopState.rollbackSuccess) }}</span>
        <span class="anchor-mark" data-testid="mvp-bom-loop-zero-residual-success">{{ String(loopState.zeroResidualSuccess) }}</span>
        <span class="anchor-mark" data-testid="mvp-bom-loop-residual">{{ String(loopState.residualRecordsAfterRollback) }}</span>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { request } from '@/api/request'
import {
  fetchBomDetail,
  fetchBomList,
  type BomItemPayload,
  type BomOperationPayload,
} from '@/api/bom'
import { usePermissionStore } from '@/stores/permission'

interface BomItemForm {
  id: string
  material_item_code: string
  color: string
  size: string
  qty_per_piece: number
  loss_rate: number
  uom: string
  remark: string
}

interface BomOperationForm {
  id: string
  process_name: string
  sequence_no: number
  is_subcontract: boolean
  wage_rate: number | null
  subcontract_cost_per_piece: number | null
  remark: string
}

interface BomLocalDraftPayload {
  draft_id?: number
  scenario_tag: string
  bom_no: string
  item_code: string
  version_no: string
  status: string
  is_default: boolean
  bom_items: BomItemPayload[]
  operations: BomOperationPayload[]
  note: string
}

interface BomLocalDraftData {
  draft_id: number
  scenario_tag: string
  bom_no: string
  item_code: string
  version_no: string
  status: string
  is_default: boolean
  bom_items: BomItemPayload[]
  operations: BomOperationPayload[]
  note: string
  state: string
  created_at: string
  updated_at: string
  cancelled_at: string | null
  cancel_reason: string | null
  fabric_line_saved: boolean
  trim_line_saved: boolean
}

interface BomLocalResidualData {
  scenario_tag: string
  total: number
}

interface BomLocalRollbackData {
  scenario_tag: string
  deleted_count: number
  residual_records_after_rollback: number
  rollback_success: boolean
  zero_residual_success: boolean
}

const route = useRoute()
const router = useRouter()
const permissionStore = usePermissionStore()

const bomId = ref<number | null>(null)
const bomNo = ref<string>('')
const status = ref<string>('draft')
const isDefault = ref<boolean>(false)
const loadError = ref<string>('')
const loading = ref<boolean>(false)

const form = reactive({
  item_code: '',
  version_no: 'V1',
})

const bomItems = ref<BomItemForm[]>([])
const operations = ref<BomOperationForm[]>([])

const localWriteLoading = ref<boolean>(false)
const localWriteFeedback = ref<string>('')
const currentDraftId = ref<number | null>(null)

const localDraftForm = reactive({
  scenario_tag: '',
  note: 'MVP-CAND-003 local bom draft',
})

const loopState = reactive({
  saveSuccess: false,
  draftIdCreated: false,
  fabricLineSaved: false,
  trimLineSaved: false,
  cancelSuccess: false,
  readbackSuccess: false,
  rollbackSuccess: false,
  zeroResidualSuccess: false,
  residualRecordsAfterRollback: -1,
})

const statusText = computed<string>(() => {
  if (status.value === 'active') return '已发布'
  if (status.value === 'inactive') return '已停用'
  return '草稿'
})

const isFabricLine = (item: BomItemForm): boolean => {
  const token = `${item.material_item_code} ${item.remark}`.toUpperCase()
  return token.includes('FABRIC') || token.includes('FAB') || token.includes('面料')
}

const isTrimLine = (item: BomItemForm): boolean => {
  const token = `${item.material_item_code} ${item.remark}`.toUpperCase()
  return token.includes('TRIM') || token.includes('BUTTON') || token.includes('辅料') || token.includes('包材')
}

const fabricCount = computed<number>(() => bomItems.value.filter((item) => isFabricLine(item)).length)
const trimCount = computed<number>(() => bomItems.value.filter((item) => isTrimLine(item)).length)
const firstFabricId = computed<string | null>(() => {
  const found = bomItems.value.find((item) => isFabricLine(item))
  return found ? found.id : null
})
const firstTrimId = computed<string | null>(() => {
  const found = bomItems.value.find((item) => isTrimLine(item))
  return found ? found.id : null
})

const rowId = (): string => `${Date.now()}-${Math.random().toString(16).slice(2, 8)}`

const pad3 = (value: number): string => String(value).padStart(3, '0')
const SCENARIO_SEQ_KEY = 'mvp.bom.local.seq'
const buildScenarioTag = (): string => {
  const now = new Date()
  const y = String(now.getFullYear())
  const m = String(now.getMonth() + 1).padStart(2, '0')
  const d = String(now.getDate()).padStart(2, '0')
  const current = Number(window.sessionStorage.getItem(SCENARIO_SEQ_KEY) || '0')
  const next = Number.isFinite(current) ? current + 1 : 1
  window.sessionStorage.setItem(SCENARIO_SEQ_KEY, String(next))
  return `MVP-BOM-${y}${m}${d}-${pad3(next)}`
}

const normalizeScenarioTag = (value: string): string => value.trim() || buildScenarioTag()

const toNumber = (value: string | number | null | undefined): number => {
  if (value === null || value === undefined) return 0
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : 0
}

const normalizePayload = (): { bom_items: BomItemPayload[]; operations: BomOperationPayload[] } | null => {
  const normalizedItems: BomItemPayload[] = bomItems.value
    .map((item) => ({
      material_item_code: item.material_item_code.trim(),
      color: item.color.trim() || undefined,
      size: item.size.trim() || undefined,
      qty_per_piece: toNumber(item.qty_per_piece),
      loss_rate: toNumber(item.loss_rate),
      uom: item.uom.trim(),
      remark: item.remark.trim() || undefined,
    }))
    .filter((item) => item.material_item_code.length > 0 && item.uom.length > 0 && item.qty_per_piece > 0)

  const normalizedOps: BomOperationPayload[] = operations.value
    .map((op) => ({
      process_name: op.process_name.trim(),
      sequence_no: Number(op.sequence_no),
      is_subcontract: Boolean(op.is_subcontract),
      wage_rate: op.wage_rate ?? undefined,
      subcontract_cost_per_piece: op.subcontract_cost_per_piece ?? undefined,
      remark: op.remark.trim() || undefined,
    }))
    .filter((op) => op.process_name.length > 0 && op.sequence_no >= 1)

  if (normalizedItems.length === 0) {
    localWriteFeedback.value = '缺少有效物料明细，无法保存草稿'
    ElMessage.warning(localWriteFeedback.value)
    return null
  }
  if (normalizedOps.length === 0) {
    localWriteFeedback.value = '缺少有效工序明细，无法保存草稿'
    ElMessage.warning(localWriteFeedback.value)
    return null
  }

  const hasFabric = normalizedItems.some((item) => isFabricLine({ id: '', ...item, color: item.color ?? '', size: item.size ?? '', remark: item.remark ?? '' }))
  const hasTrim = normalizedItems.some((item) => isTrimLine({ id: '', ...item, color: item.color ?? '', size: item.size ?? '', remark: item.remark ?? '' }))
  if (!hasFabric || !hasTrim) {
    localWriteFeedback.value = '必须至少绑定 1 条面料和 1 条辅料'
    ElMessage.warning(localWriteFeedback.value)
    return null
  }

  loopState.fabricLineSaved = hasFabric
  loopState.trimLineSaved = hasTrim
  return { bom_items: normalizedItems, operations: normalizedOps }
}

const goBack = (): void => {
  router.push('/bom/list')
}

const addFabricLine = (): void => {
  bomItems.value.push({
    id: rowId(),
    material_item_code: `FABRIC-${Date.now().toString().slice(-4)}`,
    color: '白色',
    size: 'M',
    qty_per_piece: 1,
    loss_rate: 0.03,
    uom: '米',
    remark: '本地面料草稿',
  })
}

const addTrimLine = (): void => {
  bomItems.value.push({
    id: rowId(),
    material_item_code: `TRIM-${Date.now().toString().slice(-4)}`,
    color: '',
    size: '',
    qty_per_piece: 1,
    loss_rate: 0,
    uom: '个',
    remark: '本地辅料草稿',
  })
}

const removeMaterial = (index: number): void => {
  bomItems.value.splice(index, 1)
}

const addOperationLine = (): void => {
  const nextSeq = operations.value.length + 1
  operations.value.push({
    id: rowId(),
    process_name: `工序-${nextSeq}`,
    sequence_no: nextSeq * 10,
    is_subcontract: false,
    wage_rate: 1.5,
    subcontract_cost_per_piece: null,
    remark: '本地工序草稿',
  })
}

const removeOperation = (index: number): void => {
  operations.value.splice(index, 1)
}

const ensureBindingBaseline = (): void => {
  if (bomItems.value.every((item) => !isFabricLine(item))) {
    addFabricLine()
  }
  if (bomItems.value.every((item) => !isTrimLine(item))) {
    addTrimLine()
  }
  if (operations.value.length === 0) {
    addOperationLine()
  }
}

const upsertLocalDraft = async (payload: BomLocalDraftPayload): Promise<BomLocalDraftData> => {
  const response = await request<BomLocalDraftData>('/api/local-dev/bom-drafts', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  return response.data
}

const getLocalDraft = async (draftId: number): Promise<BomLocalDraftData> => {
  const response = await request<BomLocalDraftData>(`/api/local-dev/bom-drafts/${draftId}`)
  return response.data
}

const cancelLocalDraftRequest = async (draftId: number, scenarioTag: string): Promise<BomLocalDraftData> => {
  const response = await request<BomLocalDraftData>(`/api/local-dev/bom-drafts/${draftId}/cancel`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      scenario_tag: scenarioTag,
      reason: `CANCEL-${scenarioTag}`,
    }),
  })
  return response.data
}

const rollbackScenarioRequest = async (scenarioTag: string): Promise<BomLocalRollbackData> => {
  const response = await request<BomLocalRollbackData>('/api/local-dev/bom-drafts/rollback-by-scenario', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scenario_tag: scenarioTag }),
  })
  return response.data
}

const fetchResidualCount = async (scenarioTag: string): Promise<number> => {
  const query = new URLSearchParams({ scenario_tag: scenarioTag }).toString()
  const response = await request<BomLocalResidualData>(`/api/local-dev/bom-drafts/residual-count?${query}`)
  return response.data.total
}

const applyDraftReadback = (draft: BomLocalDraftData): void => {
  currentDraftId.value = draft.draft_id
  localDraftForm.scenario_tag = draft.scenario_tag
  localDraftForm.note = draft.note || ''
  bomNo.value = draft.bom_no
  form.item_code = draft.item_code
  form.version_no = draft.version_no
  status.value = draft.status || 'draft'
  isDefault.value = Boolean(draft.is_default)
  bomItems.value = draft.bom_items.map((item) => ({
    id: rowId(),
    material_item_code: item.material_item_code,
    color: item.color ?? '',
    size: item.size ?? '',
    qty_per_piece: toNumber(item.qty_per_piece),
    loss_rate: toNumber(item.loss_rate),
    uom: item.uom,
    remark: item.remark ?? '',
  }))
  operations.value = draft.operations.map((op) => ({
    id: rowId(),
    process_name: op.process_name,
    sequence_no: Number(op.sequence_no),
    is_subcontract: Boolean(op.is_subcontract),
    wage_rate: op.wage_rate ?? null,
    subcontract_cost_per_piece: op.subcontract_cost_per_piece ?? null,
    remark: op.remark ?? '',
  }))
  ensureBindingBaseline()
}

const saveLocalDraft = async (): Promise<void> => {
  const payloadSeed = normalizePayload()
  if (!payloadSeed) return

  const scenarioTag = normalizeScenarioTag(localDraftForm.scenario_tag)
  localDraftForm.scenario_tag = scenarioTag
  localWriteLoading.value = true
  localWriteFeedback.value = ''
  try {
    const payload: BomLocalDraftPayload = {
      draft_id: currentDraftId.value || undefined,
      scenario_tag: scenarioTag,
      bom_no: bomNo.value || `LOCAL-BOM-${Date.now()}`,
      item_code: form.item_code.trim() || 'LOCAL-BOM-STYLE',
      version_no: form.version_no.trim() || 'V1',
      status: 'draft',
      is_default: false,
      bom_items: payloadSeed.bom_items,
      operations: payloadSeed.operations,
      note: localDraftForm.note.trim(),
    }
    const saved = await upsertLocalDraft(payload)
    applyDraftReadback(saved)
    loopState.saveSuccess = true
    loopState.draftIdCreated = Boolean(saved.draft_id)
    loopState.fabricLineSaved = saved.fabric_line_saved
    loopState.trimLineSaved = saved.trim_line_saved
    localWriteFeedback.value = `save_success=true, draft_id=${saved.draft_id}, scenario_tag=${saved.scenario_tag}`
    ElMessage.success('本地 BOM 草稿保存成功')
  } catch (error) {
    loopState.saveSuccess = false
    loopState.draftIdCreated = false
    localWriteFeedback.value = `保存失败：${(error as Error).message}`
    ElMessage.error(localWriteFeedback.value)
  } finally {
    localWriteLoading.value = false
  }
}

const cancelLocalDraft = async (): Promise<void> => {
  if (!currentDraftId.value) {
    ElMessage.warning('请先保存草稿')
    return
  }
  const scenarioTag = normalizeScenarioTag(localDraftForm.scenario_tag)
  localWriteLoading.value = true
  try {
    const cancelled = await cancelLocalDraftRequest(currentDraftId.value, scenarioTag)
    loopState.cancelSuccess = cancelled.state === 'cancelled'
    localWriteFeedback.value = `cancel_success=${loopState.cancelSuccess}, state=${cancelled.state}`
    ElMessage.success('草稿取消成功')
  } catch (error) {
    loopState.cancelSuccess = false
    localWriteFeedback.value = `取消失败：${(error as Error).message}`
    ElMessage.error(localWriteFeedback.value)
  } finally {
    localWriteLoading.value = false
  }
}

const readbackLocalDraft = async (): Promise<void> => {
  if (!currentDraftId.value) {
    ElMessage.warning('请先保存草稿')
    return
  }
  localWriteLoading.value = true
  try {
    const readback = await getLocalDraft(currentDraftId.value)
    applyDraftReadback(readback)
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
  const scenarioTag = normalizeScenarioTag(localDraftForm.scenario_tag)
  localDraftForm.scenario_tag = scenarioTag
  localWriteLoading.value = true
  try {
    const rolled = await rollbackScenarioRequest(scenarioTag)
    const residual = await fetchResidualCount(scenarioTag)
    loopState.rollbackSuccess = rolled.rollback_success
    loopState.zeroResidualSuccess = rolled.zero_residual_success && residual === 0
    loopState.residualRecordsAfterRollback = residual
    if (loopState.zeroResidualSuccess) {
      currentDraftId.value = null
    }
    localWriteFeedback.value = `rollback_success=${rolled.rollback_success}, zero_residual_success=${loopState.zeroResidualSuccess}, residual=${residual}`
    ElMessage.success('rollback 执行完成')
  } catch (error) {
    loopState.rollbackSuccess = false
    loopState.zeroResidualSuccess = false
    localWriteFeedback.value = `rollback 失败：${(error as Error).message}`
    ElMessage.error(localWriteFeedback.value)
  } finally {
    localWriteLoading.value = false
  }
}

const loadDetail = async (id: number): Promise<void> => {
  const result = await fetchBomDetail(id)
  const detail = result.data
  bomNo.value = detail.bom.bom_no
  status.value = detail.bom.status
  isDefault.value = Boolean(detail.bom.is_default)
  form.item_code = detail.bom.item_code
  form.version_no = detail.bom.version_no
  bomItems.value = detail.items.map((item) => ({
    id: rowId(),
    material_item_code: item.material_item_code,
    color: item.color ?? '',
    size: item.size ?? '',
    qty_per_piece: toNumber(item.qty_per_piece),
    loss_rate: toNumber(item.loss_rate),
    uom: item.uom,
    remark: item.remark ?? '',
  }))
  operations.value = detail.operations.map((op) => ({
    id: rowId(),
    process_name: op.process_name,
    sequence_no: Number(op.sequence_no),
    is_subcontract: Boolean(op.is_subcontract),
    wage_rate: op.wage_rate === null || op.wage_rate === undefined ? null : toNumber(op.wage_rate),
    subcontract_cost_per_piece:
      op.subcontract_cost_per_piece === null || op.subcontract_cost_per_piece === undefined
        ? null
        : toNumber(op.subcontract_cost_per_piece),
    remark: op.remark ?? '',
  }))
  ensureBindingBaseline()
}

const resolveInitialBomId = async (): Promise<number | null> => {
  const raw = Array.isArray(route.query.id) ? route.query.id[0] : route.query.id
  const parsed = Number(raw || '0')
  if (Number.isFinite(parsed) && parsed > 0) return parsed
  const list = await fetchBomList({ page: 1, page_size: 20, status: '' })
  return list.data.items[0]?.id ?? null
}

onMounted(async () => {
  loading.value = true
  loadError.value = ''
  try {
    await permissionStore.loadCurrentUser()
    await permissionStore.loadModuleActions('bom')
    const firstId = await resolveInitialBomId()
    if (!firstId) {
      loadError.value = '未找到可用 BOM 数据'
      return
    }
    bomId.value = firstId
    await loadDetail(firstId)
    if (!localDraftForm.scenario_tag.trim()) {
      localDraftForm.scenario_tag = buildScenarioTag()
    }
  } catch (error) {
    loadError.value = (error as Error).message || '加载 BOM 详情失败'
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.bom-detail-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.header-row,
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.title {
  font-weight: 600;
}

.header-actions,
.local-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.style-binding-section {
  margin-top: 12px;
}

.feedback-alert {
  margin: 12px 0;
}

.anchor-mark {
  display: inline-block;
  width: 0;
  height: 0;
  overflow: hidden;
}
</style>
