<template>
  <div class="bom-detail-page">
    <el-card shadow="never">
      <template #header>
        <div class="header-row">
          <span>BOM 详情</span>
          <el-button @click="goBack">返回列表</el-button>
        </div>
      </template>

      <el-form label-width="110px">
        <el-form-item label="BOM编号">
          <el-input :model-value="bomNo" disabled />
        </el-form-item>
        <el-form-item label="款式编码">
          <el-input v-model="form.item_code" :disabled="isEditMode" placeholder="Item Code" />
        </el-form-item>
        <el-form-item label="版本号">
          <el-input v-model="form.version_no" :disabled="!isDraftEditable" placeholder="如：V1" />
        </el-form-item>
        <el-form-item label="状态">
          <el-tag>{{ statusText }}</el-tag>
        </el-form-item>
      </el-form>

      <div class="actions">
        <el-button
          v-if="isDraftEditable && ((isEditMode && canUpdate) || (!isEditMode && canCreate))"
          type="primary"
          :loading="saving"
          @click="saveDraft"
        >
          {{ isEditMode ? '保存草稿' : '创建 BOM' }}
        </el-button>
        <el-button
          v-if="canSetDefault"
          :disabled="!isEditMode || status !== 'active'"
          :loading="settingDefault"
          @click="setDefault"
        >
          设为默认
        </el-button>
        <el-button
          v-if="canPublish"
          type="success"
          :disabled="!isEditMode || status !== 'draft'"
          :loading="activating"
          @click="activate"
        >
          发布
        </el-button>
        <el-button
          v-if="canDeactivate"
          type="danger"
          :disabled="!isEditMode || status !== 'active'"
          :loading="deactivating"
          @click="deactivate"
        >
          停用
        </el-button>
      </div>
    </el-card>

    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>物料明细</span>
          <el-button size="small" :disabled="!isDraftEditable" @click="addBomItem">新增物料</el-button>
        </div>
      </template>
      <el-table :data="bomItems" border>
        <el-table-column label="物料编码" min-width="180">
          <template #default="scope">
            <el-input v-model="scope.row.material_item_code" :disabled="!isDraftEditable" />
          </template>
        </el-table-column>
        <el-table-column label="颜色" min-width="120">
          <template #default="scope">
            <el-input v-model="scope.row.color" :disabled="!isDraftEditable" />
          </template>
        </el-table-column>
        <el-table-column label="尺码" min-width="100">
          <template #default="scope">
            <el-input v-model="scope.row.size" :disabled="!isDraftEditable" />
          </template>
        </el-table-column>
        <el-table-column label="单件用量" min-width="120">
          <template #default="scope">
            <el-input-number v-model="scope.row.qty_per_piece" :disabled="!isDraftEditable" :min="0.000001" :step="0.1" />
          </template>
        </el-table-column>
        <el-table-column label="损耗率" min-width="120">
          <template #default="scope">
            <el-input-number v-model="scope.row.loss_rate" :disabled="!isDraftEditable" :min="0" :step="0.01" />
          </template>
        </el-table-column>
        <el-table-column label="单位" min-width="100">
          <template #default="scope">
            <el-input v-model="scope.row.uom" :disabled="!isDraftEditable" />
          </template>
        </el-table-column>
        <el-table-column label="备注" min-width="160">
          <template #default="scope">
            <el-input v-model="scope.row.remark" :disabled="!isDraftEditable" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="90">
          <template #default="scope">
            <el-button link type="danger" :disabled="!isDraftEditable" @click="removeBomItem(scope.$index)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>工序明细</span>
          <el-button size="small" :disabled="!isDraftEditable" @click="addOperation">新增工序</el-button>
        </div>
      </template>
      <el-table :data="operations" border>
        <el-table-column label="工序名称" min-width="180">
          <template #default="scope">
            <el-input v-model="scope.row.process_name" :disabled="!isDraftEditable" />
          </template>
        </el-table-column>
        <el-table-column label="序号" width="100">
          <template #default="scope">
            <el-input-number v-model="scope.row.sequence_no" :disabled="!isDraftEditable" :min="1" :step="1" />
          </template>
        </el-table-column>
        <el-table-column label="外发" width="100">
          <template #default="scope">
            <el-switch v-model="scope.row.is_subcontract" :disabled="!isDraftEditable" />
          </template>
        </el-table-column>
        <el-table-column label="本厂工价" min-width="120">
          <template #default="scope">
            <el-input-number
              v-model="scope.row.wage_rate"
              :disabled="!isDraftEditable || scope.row.is_subcontract"
              :min="0"
              :step="0.1"
            />
          </template>
        </el-table-column>
        <el-table-column label="外发单价" min-width="120">
          <template #default="scope">
            <el-input-number
              v-model="scope.row.subcontract_cost_per_piece"
              :disabled="!isDraftEditable || !scope.row.is_subcontract"
              :min="0"
              :step="0.1"
            />
          </template>
        </el-table-column>
        <el-table-column label="备注" min-width="160">
          <template #default="scope">
            <el-input v-model="scope.row.remark" :disabled="!isDraftEditable" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="90">
          <template #default="scope">
            <el-button link type="danger" :disabled="!isDraftEditable" @click="removeOperation(scope.$index)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card shadow="never">
      <template #header><span>BOM 展开预览</span></template>
      <el-form :inline="true">
        <el-form-item label="订单数量">
          <el-input-number v-model="explodeForm.order_qty" :min="0.000001" :step="1" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :disabled="!isEditMode || !canRead" :loading="exploding" @click="explode">
            展开计算
          </el-button>
        </el-form-item>
      </el-form>
      <el-form-item label="尺码分布(JSON)">
        <el-input
          v-model="explodeForm.size_ratio_json"
          type="textarea"
          :rows="2"
          placeholder='例如 {"M":60,"L":40}'
        />
      </el-form-item>

      <el-descriptions :column="2" border v-if="explodeResult">
        <el-descriptions-item label="物料总量">{{ explodeResult.total_material_qty }}</el-descriptions-item>
        <el-descriptions-item label="工序总成本">{{ explodeResult.total_operation_cost }}</el-descriptions-item>
      </el-descriptions>

      <el-table
        v-if="explodeResult && explodeResult.material_requirements.length > 0"
        :data="explodeResult.material_requirements"
        border
        style="margin-top: 12px"
      >
        <el-table-column prop="material_item_code" label="物料编码" min-width="160" />
        <el-table-column prop="color" label="颜色" min-width="100" />
        <el-table-column prop="size" label="尺码" min-width="100" />
        <el-table-column prop="uom" label="单位" width="100" />
        <el-table-column prop="qty" label="需求数量" min-width="120" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  activateBom,
  createBom,
  deactivateBom,
  explodeBom,
  fetchBomDetail,
  fetchBomList,
  setDefaultBom,
  updateBomDraft,
  type BomCreatePayload,
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

const parsedId = Number(Array.isArray(route.query.id) ? route.query.id[0] : route.query.id || '0')
const bomId = ref<number | null>(parsedId > 0 ? parsedId : null)
const bomNo = ref<string>('-')
const status = ref<string>('draft')

const saving = ref<boolean>(false)
const settingDefault = ref<boolean>(false)
const activating = ref<boolean>(false)
const deactivating = ref<boolean>(false)
const exploding = ref<boolean>(false)

const form = reactive({
  item_code: '',
  version_no: 'V1',
})

const emptyBomItem = (): BomItemForm => ({
  material_item_code: '',
  color: '',
  size: '',
  qty_per_piece: 1,
  loss_rate: 0,
  uom: '',
  remark: '',
})

const emptyOperation = (): BomOperationForm => ({
  process_name: '',
  sequence_no: 1,
  is_subcontract: false,
  wage_rate: 0,
  subcontract_cost_per_piece: null,
  remark: '',
})

const bomItems = ref<BomItemForm[]>([emptyBomItem()])
const operations = ref<BomOperationForm[]>([emptyOperation()])

const explodeForm = reactive({
  order_qty: 100,
  size_ratio_json: '',
})
const explodeResult = ref<BomExplodeData | null>(null)

const isEditMode = computed<boolean>(() => bomId.value !== null)
const canRead = computed<boolean>(() => permissionStore.state.buttonPermissions.read)
const canCreate = computed<boolean>(() => permissionStore.state.buttonPermissions.create)
const canUpdate = computed<boolean>(() => permissionStore.state.buttonPermissions.update)
const canPublish = computed<boolean>(() => permissionStore.state.buttonPermissions.publish)
const canDeactivate = computed<boolean>(() => permissionStore.state.buttonPermissions.deactivate)
const canSetDefault = computed<boolean>(() => permissionStore.state.buttonPermissions.set_default)
const isDraftEditable = computed<boolean>(() => !isEditMode.value || status.value === 'draft')
const statusText = computed<string>(() => {
  if (status.value === 'active') return '已发布'
  if (status.value === 'inactive') return '已停用'
  return '草稿'
})

const refreshPermissions = async (): Promise<void> => {
  if (bomId.value) {
    await permissionStore.loadBomActions(bomId.value)
  } else {
    await permissionStore.loadModuleActions('bom')
  }
}

const normalizeItemPayload = (): BomItemPayload[] =>
  bomItems.value.map((item) => ({
    material_item_code: item.material_item_code.trim(),
    color: item.color || undefined,
    size: item.size || undefined,
    qty_per_piece: item.qty_per_piece,
    loss_rate: item.loss_rate,
    uom: item.uom.trim(),
    remark: item.remark || undefined,
  }))

const normalizeOperationPayload = (): BomOperationPayload[] =>
  operations.value.map((op) => ({
    process_name: op.process_name.trim(),
    sequence_no: op.sequence_no,
    is_subcontract: op.is_subcontract,
    wage_rate: op.is_subcontract ? undefined : (op.wage_rate ?? undefined),
    subcontract_cost_per_piece: op.is_subcontract ? (op.subcontract_cost_per_piece ?? undefined) : undefined,
    remark: op.remark || undefined,
  }))

const validateBeforeSave = (): boolean => {
  if (!form.item_code.trim()) {
    ElMessage.warning('请填写款式编码')
    return false
  }
  if (!form.version_no.trim()) {
    ElMessage.warning('请填写版本号')
    return false
  }
  if (bomItems.value.length === 0) {
    ElMessage.warning('请至少添加一条物料明细')
    return false
  }
  if (operations.value.length === 0) {
    ElMessage.warning('请至少添加一条工序明细')
    return false
  }
  for (const item of bomItems.value) {
    if (!item.material_item_code.trim() || !item.uom.trim()) {
      ElMessage.warning('物料编码与单位不能为空')
      return false
    }
    if (item.qty_per_piece <= 0) {
      ElMessage.warning('单件用量必须大于0')
      return false
    }
    if (item.loss_rate < 0) {
      ElMessage.warning('损耗率必须大于等于0')
      return false
    }
  }
  for (const op of operations.value) {
    if (!op.process_name.trim() || op.sequence_no < 1) {
      ElMessage.warning('工序名称不能为空且序号必须大于0')
      return false
    }
    if (op.is_subcontract && (op.subcontract_cost_per_piece === null || op.subcontract_cost_per_piece < 0)) {
      ElMessage.warning('外发工序必须填写外发单价')
      return false
    }
    if (!op.is_subcontract && (op.wage_rate === null || op.wage_rate < 0)) {
      ElMessage.warning('本厂工序必须填写本厂工价')
      return false
    }
  }
  return true
}

const loadDetail = async (id: number): Promise<void> => {
  if (!canRead.value) {
    ElMessage.warning('无权查看该 BOM')
    return
  }
  const result = await fetchBomDetail(id)
  const detail = result.data
  bomNo.value = detail.bom.bom_no
  status.value = detail.bom.status
  form.item_code = detail.bom.item_code
  form.version_no = detail.bom.version_no
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

const resolveCreatedBomId = async (name: string): Promise<number | null> => {
  const listResult = await fetchBomList({
    item_code: form.item_code,
    status: undefined,
    page: 1,
    page_size: 100,
  })
  const found = listResult.data.items.find((row) => row.bom_no === name)
  return found ? found.id : null
}

const saveDraft = async (): Promise<void> => {
  if (isEditMode.value && !canUpdate.value) {
    ElMessage.warning('无权执行该操作')
    return
  }
  if (!isEditMode.value && !canCreate.value) {
    ElMessage.warning('无权执行该操作')
    return
  }
  if (!validateBeforeSave()) return
  saving.value = true
  try {
    if (isEditMode.value && bomId.value) {
      await updateBomDraft(bomId.value, {
        version_no: form.version_no,
        bom_items: normalizeItemPayload(),
        operations: normalizeOperationPayload(),
      })
      ElMessage.success('草稿更新成功')
      await loadDetail(bomId.value)
      return
    }

    const payload: BomCreatePayload = {
      item_code: form.item_code.trim(),
      version_no: form.version_no.trim(),
      bom_items: normalizeItemPayload(),
      operations: normalizeOperationPayload(),
    }
    const result = await createBom(payload)
    const newId = await resolveCreatedBomId(result.data.name)
    if (newId) {
      bomId.value = newId
      await router.replace({ path: '/bom/detail', query: { id: String(newId) } })
      await refreshPermissions()
      await loadDetail(newId)
    } else {
      bomNo.value = result.data.name
    }
    ElMessage.success('BOM 创建成功')
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    saving.value = false
  }
}

const setDefault = async (): Promise<void> => {
  if (!bomId.value) return
  if (!canSetDefault.value) {
    ElMessage.warning('无权执行该操作')
    return
  }
  settingDefault.value = true
  try {
    await setDefaultBom(bomId.value)
    ElMessage.success('默认 BOM 设置成功')
    await refreshPermissions()
    await loadDetail(bomId.value)
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    settingDefault.value = false
  }
}

const activate = async (): Promise<void> => {
  if (!bomId.value) return
  if (!canPublish.value) {
    ElMessage.warning('无权执行该操作')
    return
  }
  activating.value = true
  try {
    await activateBom(bomId.value)
    ElMessage.success('BOM 发布成功')
    await refreshPermissions()
    await loadDetail(bomId.value)
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    activating.value = false
  }
}

const deactivate = async (): Promise<void> => {
  if (!bomId.value) return
  if (!canDeactivate.value) {
    ElMessage.warning('无权执行该操作')
    return
  }
  try {
    const promptResult = await ElMessageBox.prompt('请输入停用原因', '停用 BOM', {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      inputPlaceholder: '例如：版本替换',
    })
    deactivating.value = true
    await deactivateBom(bomId.value, promptResult.value || '')
    ElMessage.success('BOM 已停用')
    await refreshPermissions()
    await loadDetail(bomId.value)
  } catch (error) {
    if ((error as Error).message !== 'cancel') {
      ElMessage.error((error as Error).message)
    }
  } finally {
    deactivating.value = false
  }
}

const explode = async (): Promise<void> => {
  if (!bomId.value) return
  if (!canRead.value) {
    ElMessage.warning('无 BOM 查看权限')
    return
  }
  exploding.value = true
  try {
    let sizeRatio: Record<string, number> = {}
    if (explodeForm.size_ratio_json.trim()) {
      sizeRatio = JSON.parse(explodeForm.size_ratio_json) as Record<string, number>
    }
    const result = await explodeBom(bomId.value, {
      order_qty: explodeForm.order_qty,
      size_ratio: sizeRatio,
    })
    explodeResult.value = result.data
    ElMessage.success('BOM 展开完成')
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    exploding.value = false
  }
}

const addBomItem = (): void => {
  if (!isDraftEditable.value) return
  bomItems.value.push(emptyBomItem())
}

const removeBomItem = (index: number): void => {
  if (!isDraftEditable.value) return
  if (bomItems.value.length <= 1) return
  bomItems.value.splice(index, 1)
}

const addOperation = (): void => {
  if (!isDraftEditable.value) return
  operations.value.push({
    ...emptyOperation(),
    sequence_no: operations.value.length + 1,
  })
}

const removeOperation = (index: number): void => {
  if (!isDraftEditable.value) return
  if (operations.value.length <= 1) return
  operations.value.splice(index, 1)
}

const goBack = (): void => {
  router.push('/bom/list')
}

onMounted(async () => {
  try {
    await permissionStore.loadCurrentUser()
    await refreshPermissions()
    if (bomId.value) {
      if (!canRead.value) {
        ElMessage.warning('无 BOM 查看权限')
        return
      }
      await loadDetail(bomId.value)
    } else if (!canCreate.value) {
      ElMessage.warning('无权新建 BOM')
    }
  } catch (error) {
    ElMessage.error((error as Error).message)
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

.actions {
  display: flex;
  gap: 8px;
}
</style>
