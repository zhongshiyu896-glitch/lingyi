<template>
  <div class="bom-detail-page" data-testid="bom-detail-page">
    <el-card shadow="never" data-testid="bom-detail-main-card">
      <template #header>
        <div class="header-row" data-testid="bom-detail-header">
          <span data-testid="bom-detail-title">BOM 详情</span>
          <el-button data-testid="bom-detail-back" @click="goBack">返回列表</el-button>
        </div>
      </template>

      <el-alert
        v-if="missingId"
        data-testid="bom-detail-missing-id-state"
        title="缺少 BOM ID，无法加载详情"
        type="warning"
        show-icon
        :closable="false"
      />
      <el-alert
        v-else-if="permissionDenied"
        data-testid="bom-detail-permission-state"
        title="当前账号无 BOM 查看权限"
        type="warning"
        show-icon
        :closable="false"
      />
      <el-alert
        v-else-if="loadError"
        data-testid="bom-detail-error-state"
        :title="loadError"
        type="error"
        show-icon
        :closable="false"
      />

      <template v-else>
        <el-form label-width="110px" data-testid="bom-detail-main-fields">
          <el-form-item label="BOM编号">
            <el-input :model-value="bomNo" disabled data-testid="bom-detail-field-bom-no" />
          </el-form-item>
          <el-form-item label="款式编码">
            <el-input :model-value="form.item_code" disabled data-testid="bom-detail-field-item-code" />
          </el-form-item>
          <el-form-item label="版本号">
            <el-input
              v-model="form.version_no"
              :disabled="detailReadOnlyMode || !canDraftUpdate"
              data-testid="bom-detail-field-version-no"
            />
          </el-form-item>
          <el-form-item label="状态">
            <el-tag :type="statusTagType" data-testid="bom-detail-status-tag">{{ statusText }}</el-tag>
          </el-form-item>
          <el-form-item label="默认BOM">
            <el-tag :type="isDefault ? 'success' : 'info'" data-testid="bom-detail-default-tag">
              {{ isDefault ? '是' : '否' }}
            </el-tag>
          </el-form-item>
          <el-form-item label="场景标记">
            <el-input :model-value="scenarioTag || '-'" disabled data-testid="bom-detail-field-scenario-tag" />
          </el-form-item>
          <el-form-item label="场景序列">
            <el-input :model-value="scenarioTags.join(', ') || '-'" disabled data-testid="bom-detail-field-scenario-tags" />
          </el-form-item>
        </el-form>

        <el-alert
          data-testid="bom-detail-readonly-state"
          title="当前 BOM 详情为只读业务流，保存、创建、发布、默认、停用与展开计算入口均保持禁用。"
          type="info"
          show-icon
          :closable="false"
        />

        <div class="actions" data-testid="bom-detail-actions" data-readonly-state="true">
          <el-button
            data-testid="bom-detail-action-save-draft"
            data-action-type="write"
            :data-write-guard="canDraftUpdate ? 'allowed:update_bom_draft' : 'guarded:readonly'"
            :loading="savingDraft"
            :disabled="detailReadOnlyMode || savingDraft || creatingDraft"
            @click="handleSaveDraft"
          >
            保存草稿
          </el-button>
          <el-button
            data-testid="bom-detail-action-create"
            data-action-type="write"
            :data-write-guard="canDraftCreate ? 'allowed:create_bom' : 'guarded:readonly'"
            :loading="creatingDraft"
            :disabled="detailReadOnlyMode || savingDraft || creatingDraft"
            @click="handleCreateDraft"
          >
            创建 BOM
          </el-button>
          <el-button
            data-testid="bom-detail-action-set-default"
            data-action-type="write"
            :data-write-guard="canSetDefault ? 'allowed:set_default_bom' : 'guarded:readonly'"
            :loading="settingDefault"
            :disabled="detailReadOnlyMode || creatingDraft || savingDraft || activatingBom || settingDefault || deactivatingBom"
            @click="handleSetDefault"
          >
            设为默认
          </el-button>
          <el-button
            data-testid="bom-detail-action-activate"
            data-action-type="write"
            :data-write-guard="canPublish ? 'allowed:activate_bom' : 'guarded:readonly'"
            :loading="activatingBom"
            :disabled="detailReadOnlyMode || creatingDraft || savingDraft || activatingBom || settingDefault || deactivatingBom"
            @click="handleActivateBom"
          >
            发布
          </el-button>
          <el-button
            data-testid="bom-detail-action-deactivate"
            data-action-type="write"
            :data-write-guard="canDeactivate ? 'allowed:deactivate_bom' : 'guarded:readonly'"
            :loading="deactivatingBom"
            :disabled="detailReadOnlyMode || creatingDraft || savingDraft || activatingBom || settingDefault || deactivatingBom"
            @click="handleDeactivateBom"
          >
            停用
          </el-button>
          <el-button
            data-testid="bom-detail-action-explode"
            data-action-type="write"
            :data-write-guard="canExplode ? 'allowed:explode_bom' : 'guarded:readonly'"
            :loading="explodingBom"
            :disabled="detailReadOnlyMode || creatingDraft || savingDraft || activatingBom || settingDefault || deactivatingBom || explodingBom"
            @click="handleExplode"
          >
            展开计算
          </el-button>
        </div>

        <el-alert
          v-if="guardedFeedback"
          data-testid="bom-detail-guarded-feedback"
          :title="guardedFeedback"
          type="info"
          show-icon
          :closable="false"
          style="margin-top: 12px"
        />

        <el-alert
          v-if="actionFeedback"
          data-testid="bom-detail-action-feedback"
          :title="actionFeedback.message"
          :type="actionFeedback.type"
          show-icon
          :closable="false"
          style="margin-top: 12px"
        />

        <el-alert
          v-if="showEmptyState"
          data-testid="bom-detail-empty-state"
          title="暂无 BOM 明细数据"
          type="info"
          show-icon
          :closable="false"
          style="margin-top: 12px"
        />

        <p class="state-tip" data-testid="bom-detail-permission-or-disabled-state">
          当前候选仅验证 BOM 可见只读业务流；所有写入口均禁用，不触发 create_draft / update_draft / activate / set_default / deactivate / explode。
        </p>
      </template>
    </el-card>

    <el-card shadow="never" data-testid="bom-detail-explode-section">
      <template #header>
        <div class="card-header">
          <span>展开计算</span>
          <el-tag type="info" data-testid="bom-detail-explode-tolerance">
            tolerance={{ explodeTolerance }}
          </el-tag>
        </div>
      </template>

      <el-form label-width="120px" data-testid="bom-detail-explode-form">
        <el-form-item label="订单数量">
          <el-input-number
            v-model="explodeOrderQty"
            :min="0"
            :precision="2"
            :step="1"
            :disabled="detailReadOnlyMode"
            controls-position="right"
            data-testid="bom-detail-explode-order-qty"
          />
        </el-form-item>
        <el-form-item label="尺码配比(JSON)">
          <el-input
            v-model="explodeSizeRatioText"
            type="textarea"
            :rows="3"
            placeholder='例如：{"S":10,"M":20,"L":30}'
            :disabled="detailReadOnlyMode"
            data-testid="bom-detail-explode-size-ratio"
          />
        </el-form-item>
        <el-form-item>
          <el-button
            type="primary"
            data-action-type="write"
            data-testid="bom-detail-explode-submit"
            :data-write-guard="canExplode ? 'allowed:explode_bom' : 'guarded:readonly'"
            :loading="explodingBom"
            :disabled="detailReadOnlyMode || explodingBom"
            @click="handleExplode"
          >
            计算
          </el-button>
          <el-button data-testid="bom-detail-explode-clear" @click="clearExplodeResult">清空结果</el-button>
        </el-form-item>
      </el-form>

      <el-alert
        v-if="explodeValidationFeedback"
        data-testid="bom-detail-explode-validation-feedback"
        :title="explodeValidationFeedback"
        type="warning"
        show-icon
        :closable="false"
      />
      <el-alert
        v-if="explodeActionFeedback"
        data-testid="bom-detail-explode-action-feedback"
        :title="explodeActionFeedback.message"
        :type="explodeActionFeedback.type"
        show-icon
        :closable="false"
        style="margin-top: 8px"
      />

      <template v-if="explodeResult">
        <div class="explode-summary" data-testid="bom-detail-explode-summary">
          <el-statistic
            title="材料合计(复算)"
            :value="explodeComputed.materialRowsTotal"
            data-testid="bom-detail-material-total-recomputed"
          />
          <el-statistic
            title="材料合计(接口)"
            :value="explodeComputed.materialDeclaredTotal"
            data-testid="bom-detail-material-total-declared"
          />
          <el-statistic
            title="工序合计(复算)"
            :value="explodeComputed.operationRowsTotal"
            data-testid="bom-detail-operation-total-recomputed"
          />
          <el-statistic
            title="工序合计(接口)"
            :value="explodeComputed.operationDeclaredTotal"
            data-testid="bom-detail-operation-total-declared"
          />
          <el-statistic
            title="综合总计(复算)"
            :value="explodeComputed.grandRowsTotal"
            data-testid="bom-detail-grand-total-recomputed"
          />
          <el-statistic
            title="综合总计(接口)"
            :value="explodeComputed.grandDeclaredTotal"
            data-testid="bom-detail-grand-total-declared"
          />
        </div>
        <p class="state-tip" data-testid="bom-detail-explode-delta">
          material_delta={{ explodeComputed.materialDelta.toFixed(6) }},
          operation_delta={{ explodeComputed.operationDelta.toFixed(6) }},
          grand_delta={{ explodeComputed.grandDelta.toFixed(6) }},
          within_tolerance={{ explodeComputed.withinTolerance ? 'true' : 'false' }}
        </p>

        <el-table
          :data="explodeResult.material_requirements"
          border
          empty-text="暂无展开物料"
          data-testid="bom-detail-explode-material-table"
          style="margin-top: 8px"
        >
          <el-table-column prop="material_item_code" label="物料编码" min-width="180" />
          <el-table-column prop="color" label="颜色" min-width="100" />
          <el-table-column prop="size" label="尺码" min-width="100" />
          <el-table-column prop="uom" label="单位" width="90" />
          <el-table-column prop="qty" label="需求数量" min-width="120" />
        </el-table>

        <el-table
          :data="explodeResult.operation_costs"
          border
          empty-text="暂无展开工序"
          data-testid="bom-detail-explode-operation-table"
          style="margin-top: 8px"
        >
          <el-table-column prop="process_name" label="工序名称" min-width="160" />
          <el-table-column label="类型" width="100">
            <template #default="scope">
              <el-tag :type="scope.row.is_subcontract ? 'warning' : 'success'">
                {{ scope.row.is_subcontract ? '外发' : '本厂' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="unit_cost" label="单价" min-width="100" />
          <el-table-column prop="total_cost" label="总价" min-width="120" />
        </el-table>
      </template>
      <el-alert
        v-else
        data-testid="bom-detail-explode-empty-state"
        title="尚未执行展开计算"
        type="info"
        show-icon
        :closable="false"
      />
    </el-card>

    <el-card shadow="never" data-testid="bom-detail-material-section">
      <template #header>
        <div class="card-header">
          <span>物料明细</span>
          <el-button
            size="small"
            data-testid="bom-detail-add-material"
            data-action-type="write"
            data-write-guard="guarded:readonly"
            disabled
            @click="guardedWriteAction('新增物料')"
          >
            新增物料
          </el-button>
        </div>
      </template>
      <el-table :data="bomItems" border empty-text="暂无物料明细" data-testid="bom-detail-material-table">
        <el-table-column prop="material_item_code" label="物料编码" min-width="180" />
        <el-table-column prop="color" label="颜色" min-width="120" />
        <el-table-column prop="size" label="尺码" min-width="100" />
        <el-table-column prop="qty_per_piece" label="单件用量" min-width="120" />
        <el-table-column prop="loss_rate" label="损耗率" min-width="120" />
        <el-table-column prop="uom" label="单位" min-width="100" />
        <el-table-column prop="remark" label="备注" min-width="160" />
        <el-table-column label="操作" width="90">
          <template #default="scope">
            <el-button
              link
              type="danger"
              data-action-type="write"
              data-write-guard="guarded:readonly"
              disabled
              :data-testid="`bom-detail-remove-material-${scope.$index}`"
              @click="guardedWriteAction('删除物料')"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card shadow="never" data-testid="bom-detail-operation-section">
      <template #header>
        <div class="card-header">
          <span>工序明细</span>
          <el-button
            size="small"
            data-testid="bom-detail-add-operation"
            data-action-type="write"
            data-write-guard="guarded:readonly"
            disabled
            @click="guardedWriteAction('新增工序')"
          >
            新增工序
          </el-button>
        </div>
      </template>
      <el-table :data="operations" border empty-text="暂无工序明细" data-testid="bom-detail-operation-table">
        <el-table-column prop="process_name" label="工序名称" min-width="180" />
        <el-table-column prop="sequence_no" label="序号" width="100" />
        <el-table-column label="外发" width="100">
          <template #default="scope">
            <el-tag :type="scope.row.is_subcontract ? 'warning' : 'success'" data-testid="bom-detail-operation-mode-tag">
              {{ scope.row.is_subcontract ? '外发' : '本厂' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="本厂工价" min-width="120">
          <template #default="scope">
            {{ scope.row.wage_rate ?? '-' }}
          </template>
        </el-table-column>
        <el-table-column label="外发单价" min-width="120">
          <template #default="scope">
            {{ scope.row.subcontract_cost_per_piece ?? '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="remark" label="备注" min-width="160" />
        <el-table-column label="操作" width="90">
          <template #default="scope">
            <el-button
              link
              type="danger"
              data-action-type="write"
              data-write-guard="guarded:readonly"
              disabled
              :data-testid="`bom-detail-remove-operation-${scope.$index}`"
              @click="guardedWriteAction('删除工序')"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  activateBom,
  createBom,
  deactivateBom,
  explodeBom,
  fetchBomDetail,
  fetchBomList,
  setDefaultBom,
  updateBomDraft,
  type BomExplodeData,
  type BomItemPayload,
  type BomOperationPayload,
} from '@/api/bom'
import { usePermissionStore } from '@/stores/permission'

interface BomItemForm {
  material_item_code: string
  color: string
  size: string
  qty_per_piece: number
  loss_rate: number
  uom: string
  remark: string
}

interface BomOperationForm {
  process_name: string
  sequence_no: number
  is_subcontract: boolean
  wage_rate: number | null
  subcontract_cost_per_piece: number | null
  remark: string
}

const route = useRoute()
const router = useRouter()
const permissionStore = usePermissionStore()
const detailReadOnlyMode = true

const parsedId = Number(Array.isArray(route.query.id) ? route.query.id[0] : route.query.id || '0')
const bomId = ref<number | null>(parsedId > 0 ? parsedId : null)
const bomNo = ref<string>('-')
const status = ref<string>('draft')

const form = reactive({
  item_code: '',
  version_no: 'V1',
})

const bomItems = ref<BomItemForm[]>([])
const operations = ref<BomOperationForm[]>([])
const loadError = ref<string>('')
const guardedFeedback = ref<string>('')
const actionFeedback = ref<{ type: 'success' | 'warning' | 'error'; message: string } | null>(null)
const loading = ref<boolean>(false)
const detailLoaded = ref<boolean>(false)
const creatingDraft = ref<boolean>(false)
const savingDraft = ref<boolean>(false)
const activatingBom = ref<boolean>(false)
const settingDefault = ref<boolean>(false)
const deactivatingBom = ref<boolean>(false)
const explodingBom = ref<boolean>(false)
const scenarioTag = ref<string>('')
const scenarioTags = ref<string[]>([])
const scenarioItemCode = ref<string>('')
const isDefault = ref<boolean>(false)
const explodeOrderQty = ref<number>(100)
const explodeSizeRatioText = ref<string>('')
const explodeValidationFeedback = ref<string>('')
const explodeActionFeedback = ref<{ type: 'success' | 'warning' | 'error'; message: string } | null>(null)
const explodeResult = ref<BomExplodeData | null>(null)
const explodeTolerance = 0.000001
const BOM_SCENARIO_PATTERN = /(Z002-BOM-\d{8}-\d{3})/

const canRead = computed<boolean>(() => permissionStore.state.buttonPermissions.read)
const canDraftCreate = computed<boolean>(() => !detailReadOnlyMode && permissionStore.state.buttonPermissions.create)
const canDraftUpdate = computed<boolean>(() => !detailReadOnlyMode && permissionStore.state.buttonPermissions.update)
const canPublish = computed<boolean>(() => !detailReadOnlyMode && permissionStore.state.buttonPermissions.publish)
const canDeactivate = computed<boolean>(
  () =>
    !detailReadOnlyMode &&
    (permissionStore.state.buttonPermissions.deactivate || permissionStore.state.buttonPermissions.publish),
)
const canSetDefault = computed<boolean>(
  () =>
    !detailReadOnlyMode &&
    (permissionStore.state.buttonPermissions.set_default || permissionStore.state.buttonPermissions.publish),
)
const canExplode = computed<boolean>(() => !detailReadOnlyMode && (canRead.value || canPublish.value))
const missingId = computed<boolean>(() => bomId.value === null)
const permissionDenied = computed<boolean>(() => !missingId.value && !loading.value && !canRead.value)
const showEmptyState = computed<boolean>(
  () =>
    detailLoaded.value &&
    !loading.value &&
    !loadError.value &&
    !permissionDenied.value &&
    bomItems.value.length === 0 &&
    operations.value.length === 0,
)

const statusText = computed<string>(() => {
  if (status.value === 'active') return '已发布'
  if (status.value === 'inactive') return '已停用'
  return '草稿'
})

const statusTagType = computed<'success' | 'danger' | 'info'>(() => {
  if (status.value === 'active') return 'success'
  if (status.value === 'inactive') return 'danger'
  return 'info'
})

const toNumber = (value: string | number | null | undefined): number => {
  if (value === null || value === undefined) return 0
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : 0
}

const round6 = (value: number): number => Math.round(value * 1_000_000) / 1_000_000

const explodeComputed = computed(() => {
  if (!explodeResult.value) {
    return {
      materialRowsTotal: 0,
      materialDeclaredTotal: 0,
      operationRowsTotal: 0,
      operationDeclaredTotal: 0,
      grandRowsTotal: 0,
      grandDeclaredTotal: 0,
      materialDelta: 0,
      operationDelta: 0,
      grandDelta: 0,
      withinTolerance: true,
    }
  }

  const materialRowsTotal = round6(
    explodeResult.value.material_requirements.reduce((sum, row) => sum + toNumber(row.qty), 0),
  )
  const materialDeclaredTotal = round6(toNumber(explodeResult.value.total_material_qty))
  const operationRowsTotal = round6(explodeResult.value.operation_costs.reduce((sum, row) => sum + toNumber(row.total_cost), 0))
  const operationDeclaredTotal = round6(toNumber(explodeResult.value.total_operation_cost))
  const grandRowsTotal = round6(materialRowsTotal + operationRowsTotal)
  const grandDeclaredTotal = round6(materialDeclaredTotal + operationDeclaredTotal)

  const materialDelta = round6(Math.abs(materialRowsTotal - materialDeclaredTotal))
  const operationDelta = round6(Math.abs(operationRowsTotal - operationDeclaredTotal))
  const grandDelta = round6(Math.abs(grandRowsTotal - grandDeclaredTotal))
  const withinTolerance =
    materialDelta <= explodeTolerance && operationDelta <= explodeTolerance && grandDelta <= explodeTolerance

  return {
    materialRowsTotal,
    materialDeclaredTotal,
    operationRowsTotal,
    operationDeclaredTotal,
    grandRowsTotal,
    grandDeclaredTotal,
    materialDelta,
    operationDelta,
    grandDelta,
    withinTolerance,
  }
})

const refreshPermissions = async (): Promise<void> => {
  if (bomId.value) {
    await permissionStore.loadBomActions(bomId.value)
  } else {
    await permissionStore.loadModuleActions('bom')
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
  if (form.item_code.includes('-Z002A')) {
    scenarioItemCode.value = form.item_code
  }
  const matchedTag = form.version_no.match(BOM_SCENARIO_PATTERN)?.[0] || detail.bom.bom_no.match(BOM_SCENARIO_PATTERN)?.[0] || ''
  scenarioTag.value = matchedTag
  if (matchedTag && !scenarioTags.value.includes(matchedTag)) {
    scenarioTags.value.push(matchedTag)
  }
  bomItems.value = detail.items.map((item) => ({
    material_item_code: item.material_item_code,
    color: item.color ?? '',
    size: item.size ?? '',
    qty_per_piece: Number(item.qty_per_piece),
    loss_rate: Number(item.loss_rate),
    uom: item.uom,
    remark: item.remark ?? '',
  }))
  operations.value = detail.operations.map((op) => ({
    process_name: op.process_name,
    sequence_no: op.sequence_no,
    is_subcontract: op.is_subcontract,
    wage_rate: op.wage_rate ? Number(op.wage_rate) : null,
    subcontract_cost_per_piece: op.subcontract_cost_per_piece ? Number(op.subcontract_cost_per_piece) : null,
    remark: op.remark ?? '',
  }))
}

const SCENARIO_TAG_PREFIX = 'Z002-BOM'
const SCENARIO_SEQ_STORAGE_KEY = 'z002.bom.seq'

const nextScenarioSeq = (): string => {
  if (typeof window === 'undefined') return '001'
  const current = Number(window.sessionStorage.getItem(SCENARIO_SEQ_STORAGE_KEY) || '0')
  const next = Number.isFinite(current) ? current + 1 : 1
  window.sessionStorage.setItem(SCENARIO_SEQ_STORAGE_KEY, String(next))
  return String(next).padStart(3, '0')
}

const createScenarioTag = (): string => {
  const now = new Date()
  const y = String(now.getFullYear())
  const m = String(now.getMonth() + 1).padStart(2, '0')
  const d = String(now.getDate()).padStart(2, '0')
  return `${SCENARIO_TAG_PREFIX}-${y}${m}${d}-${nextScenarioSeq()}`
}

const scopeText = (value: unknown): string => String(value ?? '').trim()

const buildCarrierCode = (value: unknown): string => {
  const normalized = scopeText(value)
  const bytes = new TextEncoder().encode(normalized)
  let hashValue = 2166136261
  for (let i = 0; i < bytes.length; i += 1) {
    hashValue ^= bytes[i]
    hashValue = (hashValue * 16777619) >>> 0
  }
  return hashValue.toString(16).toUpperCase().padStart(8, '0').slice(-4)
}

const buildBomRequestId = (scenario: string, itemCode: string, bomRef: string, reason = 'NONE'): string => {
  return `${scenario}-RQ-I${buildCarrierCode(itemCode)}-B${buildCarrierCode(bomRef)}-R${buildCarrierCode(reason)}`
}

const buildIdempotencyKey = (scenario: string, action: string): string => `IDEMP-${action}-${scenario}`

const buildSourceRef = (scenario: string): string => `SRC-${scenario}`

const resolveScenarioItemCode = (sourceItemCode: string): string => {
  if (scenarioItemCode.value) return scenarioItemCode.value
  const trimmed = sourceItemCode.trim()
  const base = (trimmed.split('-Z002A')[0] || trimmed.split('-Z002-')[0] || '').trim() || 'DEMO-TEE'
  scenarioItemCode.value = `${base}-Z002A`.slice(0, 140)
  return scenarioItemCode.value
}

const ensureWritablePayload = (): { bom_items: BomItemPayload[]; operations: BomOperationPayload[] } | null => {
  const normalizedItems: BomItemPayload[] = bomItems.value
    .map((item) => ({
      material_item_code: item.material_item_code.trim(),
      color: item.color?.trim() || undefined,
      size: item.size?.trim() || undefined,
      qty_per_piece: Number(item.qty_per_piece),
      loss_rate: Number(item.loss_rate),
      uom: item.uom.trim(),
      remark: item.remark?.trim() || undefined,
    }))
    .filter((item) => item.material_item_code.length > 0 && item.uom.length > 0 && Number(item.qty_per_piece) > 0)

  const normalizedOperations: BomOperationPayload[] = operations.value
    .map((op) => ({
      process_name: op.process_name.trim(),
      sequence_no: Number(op.sequence_no),
      is_subcontract: Boolean(op.is_subcontract),
      wage_rate: op.wage_rate ?? undefined,
      subcontract_cost_per_piece: op.subcontract_cost_per_piece ?? undefined,
      remark: op.remark?.trim() || '',
    }))
    .filter((op) => op.process_name.length > 0 && Number(op.sequence_no) >= 1)

  if (normalizedItems.length === 0) {
    guardedFeedback.value = '创建/保存失败：缺少有效 BOM 物料明细'
    ElMessage.warning(guardedFeedback.value)
    return null
  }

  if (normalizedOperations.length === 0) {
    guardedFeedback.value = '创建/保存失败：缺少有效 BOM 工序明细'
    ElMessage.warning(guardedFeedback.value)
    return null
  }

  return {
    bom_items: normalizedItems,
    operations: normalizedOperations,
  }
}

const handleCreateDraft = async (): Promise<void> => {
  if (!canDraftCreate.value) {
    guardedWriteAction('创建 BOM')
    return
  }
  if (!canRead.value) {
    guardedFeedback.value = '无 BOM 查看权限，无法创建草稿'
    ElMessage.warning(guardedFeedback.value)
    return
  }
  const sourceItemCode = form.item_code.trim()
  if (!sourceItemCode) {
    guardedFeedback.value = '创建草稿失败：缺少款式编码'
    ElMessage.warning(guardedFeedback.value)
    return
  }

  const payloadSeed = ensureWritablePayload()
  if (!payloadSeed) return

  creatingDraft.value = true
  guardedFeedback.value = ''
  actionFeedback.value = null
  loadError.value = ''

  try {
    const tag = createScenarioTag()
    scenarioTag.value = tag
    if (!scenarioTags.value.includes(tag)) {
      scenarioTags.value.push(tag)
    }
    form.version_no = tag
    const createItemCode = resolveScenarioItemCode(sourceItemCode)
    const sourceRef = buildSourceRef(tag)
    const requestId = buildBomRequestId(tag, createItemCode, sourceRef)

    const createResult = await createBom({
      scenario_tag: tag,
      idempotency_key: buildIdempotencyKey(tag, 'CREATE'),
      source_ref: sourceRef,
      item_code: createItemCode,
      version_no: form.version_no.trim(),
      bom_items: payloadSeed.bom_items,
      operations: payloadSeed.operations,
    }, { requestId })

    const createdName = createResult.data.name
    const listResult = await fetchBomList({
      item_code: createItemCode,
      status: 'draft',
      page: 1,
      page_size: 50,
    })
    const createdRow = listResult.data.items.find((row) => row.bom_no === createdName)
    if (!createdRow) {
      throw new Error('创建成功但未在草稿列表中定位到新 BOM')
    }

    bomId.value = createdRow.id
    bomNo.value = createdRow.bom_no
    status.value = createdRow.status
    await refreshPermissions()
    await loadDetail(createdRow.id)
    detailLoaded.value = true
    actionFeedback.value = {
      type: 'success',
      message: `创建草稿成功：${createdName}`,
    }
    ElMessage.success(`已创建草稿 ${createdName}`)
  } catch (error) {
    loadError.value = (error as Error).message || '创建草稿失败'
    actionFeedback.value = {
      type: 'error',
      message: loadError.value,
    }
    ElMessage.error(loadError.value)
  } finally {
    creatingDraft.value = false
  }
}

const handleSaveDraft = async (): Promise<void> => {
  if (!canDraftUpdate.value) {
    guardedWriteAction('保存草稿')
    return
  }
  if (!bomId.value) {
    guardedFeedback.value = '保存草稿失败：缺少 BOM ID'
    ElMessage.warning(guardedFeedback.value)
    return
  }
  const payloadSeed = ensureWritablePayload()
  if (!payloadSeed) return

  let version = form.version_no.trim()
  if (!version) {
    guardedFeedback.value = '保存草稿失败：版本号不能为空'
    ElMessage.warning(guardedFeedback.value)
    return
  }
  if (scenarioTag.value && version === scenarioTag.value) {
    version = `${scenarioTag.value}-U1`.slice(0, 32)
    form.version_no = version
  }

  savingDraft.value = true
  guardedFeedback.value = ''
  actionFeedback.value = null
  loadError.value = ''

  try {
    const activeScenarioTag = scenarioTag.value || createScenarioTag()
    scenarioTag.value = activeScenarioTag
    const currentBomNo = bomNo.value.trim()
    if (!currentBomNo || currentBomNo === '-') {
      throw new Error('保存草稿失败：缺少 BOM 编号')
    }
    const currentItemCode = form.item_code.trim()
    if (!currentItemCode) {
      throw new Error('保存草稿失败：缺少款式编码')
    }
    const requestId = buildBomRequestId(activeScenarioTag, currentItemCode, currentBomNo)
    await updateBomDraft(bomId.value, {
      scenario_tag: activeScenarioTag,
      idempotency_key: buildIdempotencyKey(activeScenarioTag, 'UPDATE'),
      source_ref: currentBomNo,
      bom_no: currentBomNo,
      item_code: currentItemCode,
      version_no: version,
      bom_items: payloadSeed.bom_items,
      operations: payloadSeed.operations,
    }, { requestId })
    await fetchBomList({
      item_code: form.item_code.trim(),
      status: 'draft',
      page: 1,
      page_size: 50,
    })
    await loadDetail(bomId.value)
    detailLoaded.value = true
    actionFeedback.value = {
      type: 'success',
      message: '草稿保存成功',
    }
    ElMessage.success('草稿保存成功')
  } catch (error) {
    loadError.value = (error as Error).message || '保存草稿失败'
    actionFeedback.value = {
      type: 'error',
      message: loadError.value,
    }
    ElMessage.error(loadError.value)
  } finally {
    savingDraft.value = false
  }
}

const handleActivateBom = async (): Promise<void> => {
  if (!canPublish.value) {
    guardedWriteAction('发布')
    return
  }
  if (!bomId.value) {
    actionFeedback.value = {
      type: 'warning',
      message: '发布失败：缺少 BOM ID',
    }
    ElMessage.warning(actionFeedback.value.message)
    return
  }
  if (status.value === 'active') {
    actionFeedback.value = {
      type: 'warning',
      message: '当前 BOM 已是已发布状态',
    }
    ElMessage.warning(actionFeedback.value.message)
    return
  }

  activatingBom.value = true
  guardedFeedback.value = ''
  actionFeedback.value = null
  loadError.value = ''
  try {
    const activeScenarioTag = scenarioTag.value || createScenarioTag()
    scenarioTag.value = activeScenarioTag
    const currentBomNo = bomNo.value.trim()
    const currentItemCode = form.item_code.trim()
    if (!currentBomNo || currentBomNo === '-' || !currentItemCode) {
      throw new Error('发布失败：业务载体缺失')
    }
    const requestId = buildBomRequestId(activeScenarioTag, currentItemCode, currentBomNo)
    await activateBom(
      bomId.value,
      {
        scenario_tag: activeScenarioTag,
        idempotency_key: buildIdempotencyKey(activeScenarioTag, 'ACTIVATE'),
        source_ref: currentBomNo,
        bom_no: currentBomNo,
        item_code: currentItemCode,
      },
      { requestId },
    )
    await fetchBomList({
      item_code: form.item_code.trim(),
      status: 'active',
      page: 1,
      page_size: 50,
    })
    await loadDetail(bomId.value)
    detailLoaded.value = true
    actionFeedback.value = {
      type: 'success',
      message: '发布成功：状态已切换为已发布',
    }
    ElMessage.success(actionFeedback.value.message)
  } catch (error) {
    loadError.value = (error as Error).message || '发布失败'
    actionFeedback.value = {
      type: 'error',
      message: loadError.value,
    }
    ElMessage.error(loadError.value)
  } finally {
    activatingBom.value = false
  }
}

const handleSetDefault = async (): Promise<void> => {
  if (!canSetDefault.value) {
    guardedWriteAction('设为默认')
    return
  }
  if (!bomId.value) {
    actionFeedback.value = {
      type: 'warning',
      message: '设为默认失败：缺少 BOM ID',
    }
    ElMessage.warning(actionFeedback.value.message)
    return
  }
  if (status.value !== 'active') {
    actionFeedback.value = {
      type: 'warning',
      message: '设为默认失败：仅 active BOM 可设为默认',
    }
    ElMessage.warning(actionFeedback.value.message)
    return
  }

  settingDefault.value = true
  guardedFeedback.value = ''
  actionFeedback.value = null
  loadError.value = ''
  try {
    const activeScenarioTag = scenarioTag.value || createScenarioTag()
    scenarioTag.value = activeScenarioTag
    const currentBomNo = bomNo.value.trim()
    const currentItemCode = form.item_code.trim()
    if (!currentBomNo || currentBomNo === '-' || !currentItemCode) {
      throw new Error('设为默认失败：业务载体缺失')
    }
    const requestId = buildBomRequestId(activeScenarioTag, currentItemCode, currentBomNo)
    await setDefaultBom(
      bomId.value,
      {
        scenario_tag: activeScenarioTag,
        idempotency_key: buildIdempotencyKey(activeScenarioTag, 'SETDEFAULT'),
        source_ref: currentBomNo,
        bom_no: currentBomNo,
        item_code: currentItemCode,
      },
      { requestId },
    )
    await fetchBomList({
      item_code: form.item_code.trim(),
      status: 'active',
      page: 1,
      page_size: 50,
    })
    await loadDetail(bomId.value)
    detailLoaded.value = true
    actionFeedback.value = {
      type: 'success',
      message: '设为默认成功',
    }
    ElMessage.success(actionFeedback.value.message)
  } catch (error) {
    loadError.value = (error as Error).message || '设为默认失败'
    actionFeedback.value = {
      type: 'error',
      message: loadError.value,
    }
    ElMessage.error(loadError.value)
  } finally {
    settingDefault.value = false
  }
}

const handleDeactivateBom = async (): Promise<void> => {
  if (!canDeactivate.value) {
    guardedWriteAction('停用')
    return
  }
  if (!bomId.value) {
    actionFeedback.value = {
      type: 'warning',
      message: '停用失败：缺少 BOM ID',
    }
    ElMessage.warning(actionFeedback.value.message)
    return
  }
  if (status.value !== 'active') {
    actionFeedback.value = {
      type: 'warning',
      message: '停用失败：仅 active BOM 可停用',
    }
    ElMessage.warning(actionFeedback.value.message)
    return
  }

  deactivatingBom.value = true
  guardedFeedback.value = ''
  actionFeedback.value = null
  loadError.value = ''
  try {
    const activeScenarioTag = scenarioTag.value || createScenarioTag()
    scenarioTag.value = activeScenarioTag
    const currentBomNo = bomNo.value.trim()
    const currentItemCode = form.item_code.trim()
    if (!currentBomNo || currentBomNo === '-' || !currentItemCode) {
      throw new Error('停用失败：业务载体缺失')
    }
    const reason = `DEACT-${activeScenarioTag}`
    const requestId = buildBomRequestId(activeScenarioTag, currentItemCode, currentBomNo, reason)
    await deactivateBom(
      bomId.value,
      {
        scenario_tag: activeScenarioTag,
        idempotency_key: buildIdempotencyKey(activeScenarioTag, 'DEACT'),
        source_ref: currentBomNo,
        bom_no: currentBomNo,
        item_code: currentItemCode,
        reason,
      },
      { requestId },
    )
    await Promise.all([
      fetchBomList({
        item_code: form.item_code.trim(),
        status: 'inactive',
        page: 1,
        page_size: 50,
      }),
      fetchBomList({
        item_code: form.item_code.trim(),
        status: 'active',
        page: 1,
        page_size: 50,
      }),
    ])
    await loadDetail(bomId.value)
    detailLoaded.value = true
    actionFeedback.value = {
      type: 'success',
      message: '停用成功：状态已切换为已停用',
    }
    ElMessage.success(actionFeedback.value.message)
  } catch (error) {
    loadError.value = (error as Error).message || '停用失败'
    actionFeedback.value = {
      type: 'error',
      message: loadError.value,
    }
    ElMessage.error(loadError.value)
  } finally {
    deactivatingBom.value = false
  }
}

const clearExplodeResult = (): void => {
  explodeResult.value = null
  explodeValidationFeedback.value = ''
  explodeActionFeedback.value = null
}

const parseSizeRatio = (raw: string): Record<string, number> => {
  const text = raw.trim()
  if (!text) return {}
  let parsed: unknown
  try {
    parsed = JSON.parse(text)
  } catch {
    throw new Error('尺码配比必须是合法 JSON 对象')
  }
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
    throw new Error('尺码配比必须是对象，例如 {"M":10,"L":20}')
  }
  const result: Record<string, number> = {}
  Object.entries(parsed as Record<string, unknown>).forEach(([key, value]) => {
    const numeric = Number(value)
    if (!Number.isFinite(numeric) || numeric < 0) {
      throw new Error(`尺码配比非法：${key}=${String(value)}`)
    }
    result[key] = numeric
  })
  return result
}

const handleExplode = async (): Promise<void> => {
  if (!canExplode.value) {
    guardedWriteAction('展开计算')
    return
  }
  if (!bomId.value) {
    explodeValidationFeedback.value = '展开计算失败：缺少 BOM ID'
    explodeResult.value = null
    ElMessage.warning(explodeValidationFeedback.value)
    return
  }
  if (status.value !== 'active') {
    explodeValidationFeedback.value = '展开计算失败：仅 active BOM 可展开'
    explodeResult.value = null
    ElMessage.warning(explodeValidationFeedback.value)
    return
  }

  const orderQty = toNumber(explodeOrderQty.value)
  if (orderQty <= 0) {
    explodeValidationFeedback.value = '展开计算失败：订单数量必须大于 0'
    explodeResult.value = null
    ElMessage.warning(explodeValidationFeedback.value)
    return
  }

  let sizeRatio: Record<string, number> = {}
  try {
    sizeRatio = parseSizeRatio(explodeSizeRatioText.value)
  } catch (error) {
    explodeValidationFeedback.value = (error as Error).message
    explodeResult.value = null
    ElMessage.warning(explodeValidationFeedback.value)
    return
  }

  explodingBom.value = true
  explodeValidationFeedback.value = ''
  explodeActionFeedback.value = null
  loadError.value = ''
  try {
    const activeScenarioTag = scenarioTag.value || createScenarioTag()
    scenarioTag.value = activeScenarioTag
    const currentBomNo = bomNo.value.trim()
    const currentItemCode = form.item_code.trim()
    if (!currentBomNo || currentBomNo === '-' || !currentItemCode) {
      throw new Error('展开计算失败：业务载体缺失')
    }
    const requestId = buildBomRequestId(activeScenarioTag, currentItemCode, currentBomNo)
    const response = await explodeBom(bomId.value, {
      scenario_tag: activeScenarioTag,
      idempotency_key: buildIdempotencyKey(activeScenarioTag, 'EXPLODE'),
      source_ref: currentBomNo,
      bom_no: currentBomNo,
      item_code: currentItemCode,
      order_qty: orderQty,
      size_ratio: sizeRatio,
    }, { requestId })
    explodeResult.value = response.data
    const summary = explodeComputed.value
    explodeActionFeedback.value = {
      type: summary.withinTolerance ? 'success' : 'warning',
      message: summary.withinTolerance ? '展开计算成功，复算结果一致' : '展开计算成功，但复算结果存在偏差',
    }
    ElMessage.success('展开计算完成')
  } catch (error) {
    const message = (error as Error).message || '展开计算失败'
    explodeResult.value = null
    explodeActionFeedback.value = {
      type: 'error',
      message,
    }
    ElMessage.error(message)
  } finally {
    explodingBom.value = false
  }
}

const guardedWriteAction = (action: string): void => {
  guardedFeedback.value = `${action}已禁用：详情页当前为只读模式`
  actionFeedback.value = null
  ElMessage.warning(guardedFeedback.value)
}

const goBack = (): void => {
  router.push('/bom/list')
}

onMounted(async () => {
  loadError.value = ''
  guardedFeedback.value = ''
  try {
    await permissionStore.loadCurrentUser()
    await refreshPermissions()

    if (missingId.value) return
    if (!canRead.value) return

    loading.value = true
    await loadDetail(bomId.value as number)
    detailLoaded.value = true
  } catch (error) {
    loadError.value = (error as Error).message || '加载 BOM 详情失败'
    ElMessage.error(loadError.value)
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

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.explode-summary {
  display: grid;
  grid-template-columns: repeat(3, minmax(180px, 1fr));
  gap: 12px;
  margin: 10px 0;
}

.actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.state-tip {
  margin-top: 12px;
  margin-bottom: 0;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}
</style>
