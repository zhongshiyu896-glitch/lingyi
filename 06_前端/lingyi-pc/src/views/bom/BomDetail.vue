<template>
  <main class="ys-bom-page" data-testid="yisuan-1to1-bom-detail-shell">
    <header class="ys-bom-topbar" data-testid="m2-bom-detail-topbar">
      <div class="ys-bom-crumbs">
        <button class="ys-back" type="button" @click="goList">‹</button>
        <span>物料开发</span>
        <span>/</span>
        <span>面料</span>
        <span>/</span>
        <span class="ys-bom-crumbs__active">{{ detailTitle }}</span>
      </div>
      <el-select v-model="activeMaterialType" class="ys-bom-title-select" aria-label="物料类型">
        <el-option label="面料" value="fabric" />
      </el-select>
      <div class="ys-bom-top-actions">
        <span>看板中心</span>
        <span>DeepSeek</span>
        <span>销售部（销售单）</span>
      </div>
    </header>

    <nav class="ys-bom-tabs" aria-label="物料开发页签">
      <button v-for="tab in materialTabs" :key="tab" class="ys-bom-tab" type="button">
        <span>{{ tab }}</span>
        <span class="ys-bom-tab__close">×</span>
      </button>
      <button class="ys-bom-tab ys-bom-tab--active" type="button">
        <span>面料</span>
        <span class="ys-bom-tab__close">×</span>
      </button>
    </nav>

    <section class="ys-bom-panel" data-testid="m2-bom-detail-panel">
      <div class="ys-bom-toolbar" data-testid="m2-bom-lifecycle-toolbar">
        <el-button class="ys-secondary-button" @click="goList">返回</el-button>
        <el-button
          v-if="showUpdateButton"
          class="ys-secondary-button"
          :disabled="!canUpdate || isUiDisabled || !detailRef.data"
          data-testid="m2-bom-detail-edit-button"
          @click="openEditDialog"
        >
          编辑
        </el-button>
        <el-button
          v-if="showSetDefaultButton"
          class="ys-secondary-button"
          :loading="actionLoading === 'set-default'"
          :disabled="!canSetDefault || isUiDisabled || !detailRef.data"
          data-testid="m2-bom-set-default-button"
          @click="submitSetDefault"
        >
          设默认
        </el-button>
        <el-button
          v-if="showPublishButton"
          type="primary"
          class="ys-primary-button"
          :loading="actionLoading === 'activate'"
          :disabled="!canPublish || isUiDisabled || !detailRef.data"
          data-testid="m2-bom-activate-button"
          @click="submitActivate"
        >
          启用
        </el-button>
        <el-button
          v-if="showDeactivateButton"
          class="ys-secondary-button"
          :loading="actionLoading === 'deactivate'"
          :disabled="!canDeactivate || isUiDisabled || !detailRef.data"
          data-testid="m2-bom-deactivate-button"
          @click="submitDeactivate"
        >
          停用
        </el-button>
        <el-button
          class="ys-secondary-button"
          :loading="actionLoading === 'explode'"
          :disabled="!canExplode || isUiDisabled || !detailRef.data"
          data-testid="m2-bom-explode-button"
          @click="submitExplode"
        >
          展开
        </el-button>
        <div class="ys-bom-toolbar__spacer" />
        <el-button class="ys-secondary-button" disabled>↙ 导入图片</el-button>
        <el-button class="ys-secondary-button" disabled>↓ 导出</el-button>
        <el-button class="ys-secondary-button" disabled>⚙ 列设置</el-button>
      </div>

      <el-alert
        v-if="stateMessage"
        :type="stateMessage.type"
        :closable="false"
        :title="stateMessage.text"
        class="ys-state-alert"
        data-testid="m2-bom-detail-state-alert"
      />

      <section class="ys-detail-summary" data-testid="m2-bom-detail-summary">
        <div>
          <span>编号</span>
          <strong>{{ detailRow.code }}</strong>
        </div>
        <div>
          <span>名称</span>
          <strong>{{ detailRow.name }}</strong>
        </div>
        <div>
          <span>版本</span>
          <strong>{{ detailRow.versionNo }}</strong>
        </div>
        <div>
          <span>状态</span>
          <strong>{{ statusLabel(detailRow.status) }}</strong>
        </div>
      </section>

      <div class="ys-bom-table-wrap" :class="{ 'is-disabled': isUiDisabled }">
        <div v-if="isLoadingState" class="ys-state-mask" data-testid="m2-bom-detail-loading-state">加载中</div>
        <table class="ys-bom-table" data-testid="yisuan-1to1-bom-detail-table">
          <thead>
            <tr>
              <th class="ys-check"><input type="checkbox" disabled /></th>
              <th>图片</th>
              <th>编号</th>
              <th>部位</th>
              <th>名称</th>
              <th>颜色</th>
              <th>成分</th>
              <th>幅宽</th>
              <th>克重</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody v-if="detailMaterialRows.length && !isNoPermissionState">
            <tr v-for="row in detailMaterialRows" :key="row.key">
              <td class="ys-check"><input type="checkbox" disabled /></td>
              <td><span class="ys-image-placeholder" aria-hidden="true"></span></td>
              <td><span class="ys-link">{{ row.code }}</span></td>
              <td>{{ row.part }}</td>
              <td>{{ row.name }}</td>
              <td>{{ row.color }}</td>
              <td>{{ row.composition }}</td>
              <td>{{ row.width }}</td>
              <td>{{ row.weight }}</td>
              <td class="ys-actions">
                <button type="button" class="ys-text-button" :disabled="!canUpdate || isUiDisabled" @click="openEditDialog">
                  编辑
                </button>
                <button type="button" class="ys-text-button ys-text-button--danger" disabled>删除</button>
              </td>
            </tr>
          </tbody>
          <tbody v-else>
            <tr>
              <td colspan="10" class="ys-empty" data-testid="m2-bom-detail-empty-state">{{ emptyText }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <section v-if="explodeResultRows.length" class="ys-explode-panel" data-testid="m2-bom-explode-result">
        <h3>展开结果</h3>
        <table class="ys-mini-table">
          <thead>
            <tr>
              <th>物料编号</th>
              <th>颜色</th>
              <th>尺码</th>
              <th>单位</th>
              <th>需求量</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in explodeResultRows" :key="`${row.material_item_code}-${row.color}-${row.size}`">
              <td>{{ row.material_item_code }}</td>
              <td>{{ row.color || '-' }}</td>
              <td>{{ row.size || '-' }}</td>
              <td>{{ row.uom }}</td>
              <td>{{ row.qty }}</td>
            </tr>
          </tbody>
        </table>
      </section>
    </section>

    <el-dialog
      v-model="recordDialogVisible"
      width="720px"
      title="面料编辑"
      class="ys-bom-dialog"
      data-testid="m2-bom-detail-edit-dialog"
    >
      <el-form :model="recordForm" label-width="88px" class="ys-bom-form">
        <el-form-item label="款号">
          <el-input v-model="recordForm.itemCode" disabled />
        </el-form-item>
        <el-form-item label="版本">
          <el-input v-model="recordForm.versionNo" placeholder="V1" />
        </el-form-item>
        <el-form-item label="编号">
          <el-input v-model="recordForm.materialItemCode" placeholder="物料编号" />
        </el-form-item>
        <el-form-item label="名称">
          <el-input v-model="recordForm.materialName" placeholder="面料名称" />
        </el-form-item>
        <el-form-item label="部位">
          <el-input v-model="recordForm.part" placeholder="面料" />
        </el-form-item>
        <el-form-item label="颜色">
          <el-input v-model="recordForm.color" placeholder="颜色" />
        </el-form-item>
        <el-form-item label="成分">
          <el-input v-model="recordForm.composition" placeholder="成分" />
        </el-form-item>
        <el-form-item label="幅宽">
          <el-input-number v-model="recordForm.width" :min="0.01" :precision="2" />
        </el-form-item>
        <el-form-item label="克重">
          <el-input-number v-model="recordForm.weight" :min="0" :precision="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button class="ys-secondary-button" @click="recordDialogVisible = false">取消</el-button>
        <el-button
          type="primary"
          class="ys-primary-button"
          :loading="actionLoading === 'update'"
          :disabled="!canSubmitRecord"
          data-testid="m2-bom-detail-save-button"
          @click="submitUpdate"
        >
          保存
        </el-button>
      </template>
    </el-dialog>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  activateBom,
  deactivateBom,
  explodeBom,
  fetchBomDetail,
  setDefaultBom,
  updateBomDraft,
  type BomDetailData,
  type BomExplodeData,
  type BomExplodePayload,
  type BomItemPayload,
  type BomOperationPayload,
  type BomUpdatePayload,
  type BomWriteCarrierPayload,
} from '@/api/bom'
import { usePermissionStore } from '@/stores/permission'

type UiStateProbe = '' | 'loading' | 'error' | 'disabled' | 'empty' | 'no_permission'
type ActionKey = '' | 'update' | 'set-default' | 'activate' | 'deactivate' | 'explode'

interface MaterialRow {
  key: string
  code: string
  part: string
  name: string
  color: string
  composition: string
  width: string
  weight: string
}

interface RecordFormState {
  itemCode: string
  versionNo: string
  materialItemCode: string
  materialName: string
  part: string
  color: string
  composition: string
  width: number
  weight: number
}

const materialTabs = ['工类类型', '品牌管理', '条码中心', '国际条码', '洗水类型', '面料类型', '执行标准', '工序模板', '号型', '合格证/洗唛']
const permissionStore = usePermissionStore()
const router = useRouter()
const route = useRoute()

const activeMaterialType = ref('fabric')
const detailRef = reactive<{ loading: boolean; data: BomDetailData | null; error: string }>({
  loading: false,
  data: null,
  error: '',
})
const actionLoading = ref<ActionKey>('')
const recordDialogVisible = ref(false)
const explodeResultRows = ref<BomExplodeData['material_requirements']>([])

const recordForm = reactive<RecordFormState>({
  itemCode: '',
  versionNo: '',
  materialItemCode: '',
  materialName: '',
  part: '面料',
  color: '',
  composition: '',
  width: 150,
  weight: 230,
})

const parsePositiveInt = (value: unknown): number | null => {
  const raw = Array.isArray(value) ? value[0] : value
  const parsed = Number(raw)
  if (!Number.isFinite(parsed) || parsed <= 0) return null
  return Math.floor(parsed)
}

const queryText = (key: string, fallback = ''): string => {
  const raw = route.query[key]
  const value = Array.isArray(raw) ? raw[0] : raw
  return typeof value === 'string' && value.trim() ? value.trim() : fallback
}

const bomId = computed(() => parsePositiveInt(route.query.bom_id))
const uiStateProbe = computed<UiStateProbe>(() => {
  const value = queryText('m2_state')
  if (value === 'loading' || value === 'error' || value === 'disabled' || value === 'empty' || value === 'no_permission') {
    return value
  }
  return ''
})

const buttonPermissions = computed(() => permissionStore.state.buttonPermissions)
const canRead = computed(() => buttonPermissions.value.read && uiStateProbe.value !== 'no_permission')
const canUpdate = computed(() => buttonPermissions.value.update && uiStateProbe.value !== 'no_permission')
const canPublish = computed(() => buttonPermissions.value.publish && uiStateProbe.value !== 'no_permission')
const canDeactivate = computed(() => buttonPermissions.value.deactivate && uiStateProbe.value !== 'no_permission')
const canSetDefault = computed(() => buttonPermissions.value.set_default && uiStateProbe.value !== 'no_permission')
const canExplode = computed(() => canRead.value && uiStateProbe.value !== 'no_permission')
const isUiDisabled = computed(() => uiStateProbe.value === 'disabled' || uiStateProbe.value === 'no_permission')
const isLoadingState = computed(() => detailRef.loading || uiStateProbe.value === 'loading')
const isNoPermissionState = computed(() => !canRead.value || uiStateProbe.value === 'no_permission')

const showUpdateButton = computed(() => canUpdate.value)
const showSetDefaultButton = computed(() => canSetDefault.value)
const showPublishButton = computed(() => canPublish.value)
const showDeactivateButton = computed(() => canDeactivate.value)

const detailTitle = computed(() => detailRef.data?.bom.bom_no || queryText('bom_no', '面料详情'))
const detailRow = computed(() => {
  const bom = detailRef.data?.bom
  return {
    bomNo: bom?.bom_no || queryText('bom_no', '-'),
    itemCode: bom?.item_code || queryText('item_code', '-'),
    versionNo: bom?.version_no || queryText('version_no', '-'),
    status: bom?.status || 'draft',
    code: queryText('item_code', bom?.item_code || '-'),
    name: queryText('material_name', bom?.item_code || '面料'),
    color: queryText('color'),
    composition: queryText('composition'),
    width: queryText('width', '150'),
    weight: queryText('weight', '230'),
  }
})

const detailMaterialRows = computed<MaterialRow[]>(() => {
  if (uiStateProbe.value === 'empty') return []
  const items = detailRef.data?.items || []
  if (items.length) {
    return items.map((item) => ({
      key: String(item.id),
      code: item.material_item_code,
      part: '面料',
      name: item.remark?.split(' / ')[1] || item.material_item_code,
      color: item.color || '',
      composition: item.size || '',
      width: String(item.qty_per_piece || ''),
      weight: item.remark?.match(/克重:([^/]+)/)?.[1]?.trim() || '0',
    }))
  }
  if (detailRow.value.code !== '-') {
    return [
      {
        key: 'query-fallback',
        code: detailRow.value.code,
        part: '面料',
        name: detailRow.value.name,
        color: detailRow.value.color,
        composition: detailRow.value.composition,
        width: detailRow.value.width,
        weight: detailRow.value.weight,
      },
    ]
  }
  return []
})

const emptyText = computed(() => {
  if (isNoPermissionState.value) return '无权限查看面料详情'
  if (uiStateProbe.value === 'error') return '面料详情读取失败'
  return '暂无面料明细'
})

const stateMessage = computed(() => {
  if (isNoPermissionState.value) {
    return { type: 'warning' as const, text: '当前会话未获得 bom:read，详情页 fail-closed。' }
  }
  if (uiStateProbe.value === 'error') {
    return { type: 'error' as const, text: '模拟错误状态：面料详情不可用。' }
  }
  if (detailRef.error) {
    return { type: 'warning' as const, text: detailRef.error }
  }
  if (uiStateProbe.value === 'disabled') {
    return { type: 'info' as const, text: '模拟禁用状态：生命周期按钮保持禁用。' }
  }
  return null
})

const canSubmitRecord = computed(() =>
  Boolean(
    canUpdate.value &&
      !isUiDisabled.value &&
      detailRef.data &&
      recordForm.itemCode.trim() &&
      recordForm.versionNo.trim() &&
      recordForm.materialItemCode.trim() &&
      recordForm.materialName.trim() &&
      recordForm.width > 0,
  ),
)

const todayCompact = (): string => {
  const now = new Date()
  return `${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}`
}

const buildScenarioTag = (): string => `Z002-BOM-${todayCompact()}-001`

const carrierCode = (value: string): string => {
  let hashValue = 2166136261
  for (const char of new TextEncoder().encode(value.trim())) {
    hashValue ^= char
    hashValue = Math.imul(hashValue, 16777619) >>> 0
  }
  return hashValue.toString(16).toUpperCase().padStart(8, '0').slice(-4)
}

const buildRequestId = (scenarioTag: string, itemCode: string, bomRef: string, reason = 'NONE'): string =>
  `${scenarioTag}-RQ-I${carrierCode(itemCode)}-B${carrierCode(bomRef)}-R${carrierCode(reason)}`

const buildCarrierPayload = (reason?: string): { payload: BomWriteCarrierPayload; requestId: string } => {
  const bom = detailRef.data?.bom
  if (!bom) throw new Error('缺少 BOM 详情')
  const scenarioTag = buildScenarioTag()
  const requestId = buildRequestId(scenarioTag, bom.item_code, bom.bom_no, reason)
  return {
    requestId,
    payload: {
      scenario_tag: scenarioTag,
      idempotency_key: requestId,
      source_ref: bom.bom_no,
      bom_no: bom.bom_no,
      item_code: bom.item_code,
    },
  }
}

const buildMaterialPayload = (): BomItemPayload => ({
  material_item_code: recordForm.materialItemCode.trim(),
  color: recordForm.color.trim() || undefined,
  size: recordForm.composition.trim() || undefined,
  qty_per_piece: Number(recordForm.width),
  loss_rate: 0,
  uom: '米',
  remark: [recordForm.part.trim(), recordForm.materialName.trim(), `克重:${recordForm.weight}`].filter(Boolean).join(' / '),
})

const buildOperationPayload = (): BomOperationPayload => ({
  process_name: '面料建档',
  sequence_no: 1,
  is_subcontract: false,
  wage_rate: 0,
  subcontract_cost_per_piece: 0,
  remark: 'M2 BOM 真实端点编辑',
})

const statusLabel = (status: string): string => {
  if (status === 'active' || status === 'published') return '已启用'
  if (status === 'inactive') return '已停用'
  return '草稿'
}

const loadPermissions = async (): Promise<void> => {
  try {
    await permissionStore.loadCurrentUser()
    if (bomId.value) {
      await permissionStore.loadBomActions(bomId.value)
    } else {
      await permissionStore.loadModuleActions('bom')
    }
  } catch {
    // Permission state is fail-closed by the store.
  }
}

const loadDetail = async (): Promise<void> => {
  if (!bomId.value || !canRead.value || uiStateProbe.value === 'loading' || uiStateProbe.value === 'error') {
    return
  }
  detailRef.loading = true
  detailRef.error = ''
  try {
    detailRef.data = (await fetchBomDetail(bomId.value)).data
  } catch (error) {
    detailRef.data = null
    detailRef.error = `面料详情读取失败：${(error as Error).message}`
  } finally {
    detailRef.loading = false
  }
}

const refreshAfterAction = async (): Promise<void> => {
  await loadDetail()
  if (bomId.value) await permissionStore.loadBomActions(bomId.value)
}

const openEditDialog = (): void => {
  if (!canUpdate.value || !detailRef.data) {
    ElMessage.warning('无 BOM 编辑权限或缺少真实 BOM 详情')
    return
  }
  const primary = detailMaterialRows.value[0]
  recordForm.itemCode = detailRef.data.bom.item_code
  recordForm.versionNo = detailRef.data.bom.version_no
  recordForm.materialItemCode = primary?.code || 'MAT-NEW'
  recordForm.materialName = primary?.name || detailRef.data.bom.item_code
  recordForm.part = primary?.part || '面料'
  recordForm.color = primary?.color || ''
  recordForm.composition = primary?.composition || ''
  recordForm.width = Number(primary?.width) || 150
  recordForm.weight = Number(primary?.weight) || 0
  recordDialogVisible.value = true
}

const submitUpdate = async (): Promise<void> => {
  if (!canSubmitRecord.value || !bomId.value || !detailRef.data) return
  actionLoading.value = 'update'
  try {
    const { payload: carrier, requestId } = buildCarrierPayload()
    const payload: BomUpdatePayload = {
      ...carrier,
      version_no: recordForm.versionNo.trim(),
      bom_items: [buildMaterialPayload()],
      operations: [buildOperationPayload()],
    }
    await updateBomDraft(bomId.value, payload, { requestId })
    ElMessage.success('面料编辑已提交真实 BOM 端点')
    recordDialogVisible.value = false
    await refreshAfterAction()
  } catch (error) {
    ElMessage.error(`编辑失败：${(error as Error).message}`)
  } finally {
    actionLoading.value = ''
  }
}

const submitSetDefault = async (): Promise<void> => {
  if (!canSetDefault.value || !bomId.value) return
  actionLoading.value = 'set-default'
  try {
    const { payload, requestId } = buildCarrierPayload()
    await setDefaultBom(bomId.value, payload, { requestId })
    ElMessage.success('已提交设默认')
    await refreshAfterAction()
  } catch (error) {
    ElMessage.error(`设默认失败：${(error as Error).message}`)
  } finally {
    actionLoading.value = ''
  }
}

const submitActivate = async (): Promise<void> => {
  if (!canPublish.value || !bomId.value) return
  actionLoading.value = 'activate'
  try {
    const { payload, requestId } = buildCarrierPayload()
    await activateBom(bomId.value, payload, { requestId })
    ElMessage.success('已提交启用')
    await refreshAfterAction()
  } catch (error) {
    ElMessage.error(`启用失败：${(error as Error).message}`)
  } finally {
    actionLoading.value = ''
  }
}

const submitDeactivate = async (): Promise<void> => {
  if (!canDeactivate.value || !bomId.value) return
  actionLoading.value = 'deactivate'
  try {
    const reason = `${buildScenarioTag()}-停用面料`
    const { payload, requestId } = buildCarrierPayload(reason)
    await deactivateBom(bomId.value, { ...payload, reason }, { requestId })
    ElMessage.success('已提交停用')
    await refreshAfterAction()
  } catch (error) {
    ElMessage.error(`停用失败：${(error as Error).message}`)
  } finally {
    actionLoading.value = ''
  }
}

const submitExplode = async (): Promise<void> => {
  if (!canExplode.value || !bomId.value) return
  actionLoading.value = 'explode'
  try {
    const { payload, requestId } = buildCarrierPayload()
    const explodePayload: BomExplodePayload = {
      ...payload,
      order_qty: 10,
      size_ratio: {},
    }
    const response = await explodeBom(bomId.value, explodePayload, { requestId })
    explodeResultRows.value = response.data.material_requirements
    ElMessage.success('BOM 展开完成')
  } catch (error) {
    ElMessage.error(`展开失败：${(error as Error).message}`)
  } finally {
    actionLoading.value = ''
  }
}

const goList = (): void => {
  void router.push('/bom/list')
}

onMounted(async () => {
  await loadPermissions()
  await loadDetail()
})
</script>

<style scoped>
.ys-bom-page {
  --ys-color-primary: #4e88f3;
  --ys-color-primary-weak: rgba(78, 136, 243, 0.1);
  --ys-color-bg-page: #f6f8f9;
  --ys-color-bg-table-head: #f5f7fa;
  --ys-color-text-main: #515a6e;
  --ys-color-text-title: #303133;
  --ys-color-text-minor: #606266;
  --ys-color-border: #dcdfe6;
  --ys-color-danger: #fd4e4e;
  min-height: calc(100vh - 42px);
  padding: 0 12px 12px;
  background: var(--ys-color-bg-page);
  color: var(--ys-color-text-main);
  font-family: "PingFang SC", Arial, "Microsoft YaHei", sans-serif;
  font-size: 14px;
}

.ys-bom-topbar {
  height: 60px;
  display: grid;
  grid-template-columns: 1fr 200px 1fr;
  align-items: center;
  gap: 12px;
  border-bottom: 1px solid var(--ys-color-border);
  background: #fff;
}

.ys-bom-crumbs,
.ys-bom-top-actions,
.ys-bom-tabs,
.ys-bom-toolbar,
.ys-actions {
  display: flex;
  align-items: center;
}

.ys-bom-crumbs {
  gap: 10px;
  color: var(--ys-color-text-title);
}

.ys-bom-crumbs__active {
  color: var(--ys-color-primary);
}

.ys-back {
  border: 0;
  background: transparent;
  color: var(--ys-color-text-minor);
  font-size: 24px;
  cursor: pointer;
}

.ys-bom-title-select {
  width: 200px;
}

.ys-bom-top-actions {
  justify-content: flex-end;
  gap: 14px;
  color: var(--ys-color-text-minor);
  font-size: 13px;
  white-space: nowrap;
}

.ys-bom-tabs {
  height: 50px;
  overflow: hidden;
  border-bottom: 1px solid var(--ys-color-border);
  background: #fff;
}

.ys-bom-tab {
  height: 50px;
  padding: 0 12px;
  border: 0;
  border-right: 1px solid #ebeef5;
  background: transparent;
  color: var(--ys-color-text-title);
  font: inherit;
  cursor: default;
}

.ys-bom-tab--active {
  color: var(--ys-color-primary);
  background: var(--ys-color-primary-weak);
}

.ys-bom-tab__close {
  margin-left: 12px;
  color: #909399;
}

.ys-bom-panel {
  margin-top: 12px;
  padding: 12px;
  border: 1px solid var(--ys-color-border);
  border-radius: 4px;
  background: #fff;
}

.ys-bom-toolbar {
  gap: 8px;
  min-height: 32px;
}

.ys-bom-toolbar__spacer {
  flex: 1;
}

.ys-primary-button,
.ys-secondary-button {
  min-height: 32px;
  border-radius: 4px;
  padding: 8px 15px;
  font-size: 14px;
}

.ys-primary-button {
  background: var(--ys-color-primary);
  border-color: var(--ys-color-primary);
}

.ys-primary-button:disabled {
  background: rgba(78, 136, 243, 0.5);
  border-color: transparent;
}

.ys-state-alert {
  margin-top: 10px;
}

.ys-detail-summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 1px;
  margin-top: 12px;
  border: 1px solid #e4e7ed;
  background: #e4e7ed;
}

.ys-detail-summary div {
  display: grid;
  gap: 6px;
  padding: 10px 12px;
  background: #fff;
}

.ys-detail-summary span {
  color: #909399;
  font-size: 12px;
}

.ys-detail-summary strong {
  color: var(--ys-color-text-title);
  font-weight: 500;
}

.ys-bom-table-wrap {
  position: relative;
  margin-top: 12px;
  border: 1px solid #e4e7ed;
  min-height: 620px;
  overflow: auto;
}

.ys-bom-table-wrap.is-disabled {
  opacity: 0.72;
}

.ys-state-mask {
  position: absolute;
  inset: 0;
  z-index: 2;
  display: grid;
  place-items: center;
  background: rgba(255, 255, 255, 0.7);
  color: var(--ys-color-text-minor);
}

.ys-bom-table,
.ys-mini-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
  background: #fff;
}

.ys-bom-table th,
.ys-mini-table th {
  height: 38px;
  padding: 8px 8px;
  border-right: 1px solid #ebeef5;
  border-bottom: 1px solid #e4e7ed;
  background: var(--ys-color-bg-table-head);
  color: #909399;
  font-size: 14px;
  font-weight: 500;
  text-align: left;
}

.ys-bom-table td,
.ys-mini-table td {
  height: 39px;
  padding: 0 8px;
  border-right: 1px solid #ebeef5;
  border-bottom: 1px solid #ebeef5;
  color: var(--ys-color-text-main);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ys-bom-table th:nth-child(1),
.ys-bom-table td:nth-child(1) {
  width: 36px;
}

.ys-bom-table th:nth-child(2),
.ys-bom-table td:nth-child(2) {
  width: 60px;
}

.ys-bom-table th:nth-child(3),
.ys-bom-table td:nth-child(3) {
  width: 150px;
}

.ys-bom-table th:nth-child(10),
.ys-bom-table td:nth-child(10) {
  width: 150px;
}

.ys-check {
  text-align: center;
}

.ys-image-placeholder {
  display: inline-block;
  width: 28px;
  height: 22px;
  border-radius: 3px;
  background:
    radial-gradient(circle at 70% 30%, #ffffff 0 2px, transparent 3px),
    linear-gradient(135deg, #cde6ff 0%, #8ebeff 100%);
  box-shadow: inset 0 0 0 1px #d8e6f5;
  vertical-align: middle;
}

.ys-link,
.ys-text-button {
  border: 0;
  background: transparent;
  color: #2f7df6;
  font: inherit;
}

.ys-text-button {
  padding: 0 6px;
  font-size: 12px;
  cursor: pointer;
}

.ys-text-button--danger {
  color: var(--ys-color-danger);
}

.ys-text-button:disabled {
  color: #c0c4cc;
  cursor: not-allowed;
}

.ys-actions {
  gap: 4px;
}

.ys-empty {
  height: 260px;
  text-align: center;
  color: #909399;
}

.ys-explode-panel {
  margin-top: 12px;
}

.ys-explode-panel h3 {
  margin: 0 0 8px;
  color: var(--ys-color-text-title);
  font-size: 14px;
  font-weight: 500;
}

.ys-bom-form {
  display: grid;
  grid-template-columns: 1fr 1fr;
  column-gap: 16px;
}

@media (max-width: 980px) {
  .ys-bom-topbar,
  .ys-detail-summary,
  .ys-bom-form {
    grid-template-columns: 1fr;
  }

  .ys-bom-topbar {
    height: auto;
    padding: 10px 0;
  }

  .ys-bom-toolbar,
  .ys-bom-top-actions {
    flex-wrap: wrap;
    justify-content: flex-start;
  }

  .ys-bom-toolbar__spacer {
    display: none;
  }
}
</style>
