<template>
  <main class="ys-bom-page" data-testid="yisuan-1to1-bom-list-shell">
    <header class="ys-bom-topbar" data-testid="m2-bom-yisuan-topbar">
      <div class="ys-bom-crumbs">
        <span class="ys-icon">‹</span>
        <span>物料开发</span>
        <span>/</span>
        <span class="ys-bom-crumbs__active">面料</span>
      </div>
      <el-select v-model="activeMaterialType" class="ys-bom-title-select" size="default" aria-label="物料类型">
        <el-option label="面料" value="fabric" />
      </el-select>
      <div class="ys-bom-top-actions">
        <span>看板中心</span>
        <span>DeepSeek</span>
        <span>衣算</span>
        <span>销售部（销售单）</span>
      </div>
    </header>

    <nav class="ys-bom-tabs" aria-label="物料开发页签">
      <button v-for="tab in materialTabs" :key="tab" class="ys-bom-tab" type="button">
        <span>{{ tab }}</span>
        <span class="ys-bom-tab__close">×</span>
      </button>
      <button class="ys-bom-tab ys-bom-tab--active" type="button" data-testid="m2-bom-active-fabric-tab">
        <span>面料</span>
        <span class="ys-bom-tab__close">×</span>
      </button>
    </nav>

    <section class="ys-bom-panel" data-testid="m2-bom-list-panel">
      <div class="ys-bom-toolbar" data-testid="yisuan-1to1-bom-list-toolbar">
        <el-button
          type="primary"
          class="ys-primary-button"
          :disabled="!canCreate || isUiDisabled"
          data-testid="m2-bom-new-button"
          @click="openCreateDialog"
        >
          新建
          <span class="ys-button-caret">⌄</span>
        </el-button>
        <el-input
          v-model="query.keyword"
          class="ys-bom-search"
          clearable
          placeholder="请输入名称/供应商/编号"
          data-testid="m2-bom-search"
          @keyup.enter="runQuery"
        >
          <template #append>
            <el-button aria-label="搜索" @click="runQuery">⌕</el-button>
          </template>
        </el-input>
        <el-button class="ys-secondary-button" :disabled="isUiDisabled" @click="toggleFilter">筛选</el-button>
        <el-button class="ys-danger-button" disabled>批量删除</el-button>
        <div class="ys-bom-toolbar__spacer" />
        <el-button class="ys-secondary-button" :disabled="isUiDisabled">↙ 导入图片</el-button>
        <el-button class="ys-secondary-button" :disabled="isUiDisabled">↙ 导入</el-button>
        <el-button class="ys-secondary-button" :disabled="isUiDisabled">↓ 导出</el-button>
        <el-button class="ys-secondary-button" :disabled="isUiDisabled">↙ 导入物料计价</el-button>
        <el-button class="ys-secondary-button" :disabled="isUiDisabled">⚙ 列设置</el-button>
      </div>

      <div v-if="filterOpen" class="ys-filter-row" data-testid="m2-bom-filter-panel">
        <el-input v-model="query.itemCode" clearable placeholder="编号" />
        <el-select v-model="query.status" clearable placeholder="状态">
          <el-option label="草稿" value="draft" />
          <el-option label="已启用" value="active" />
          <el-option label="已停用" value="inactive" />
        </el-select>
        <el-button type="primary" class="ys-primary-button" :disabled="isUiDisabled" @click="runQuery">查询</el-button>
        <el-button class="ys-secondary-button" :disabled="isUiDisabled" @click="resetQuery">重置</el-button>
      </div>

      <el-alert
        v-if="stateMessage"
        :type="stateMessage.type"
        :closable="false"
        :title="stateMessage.text"
        class="ys-state-alert"
        data-testid="m2-bom-state-alert"
      />

      <div class="ys-bom-table-wrap" :class="{ 'is-disabled': isUiDisabled }">
        <div v-if="isLoadingState" class="ys-state-mask" data-testid="m2-bom-loading-state">加载中</div>
        <table class="ys-bom-table" data-testid="yisuan-1to1-bom-table">
          <thead>
            <tr>
              <th class="ys-check"><input type="checkbox" :disabled="isUiDisabled" /></th>
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
          <tbody v-if="visibleRows.length && !isNoPermissionState">
            <tr v-for="row in visibleRows" :key="row.key" :data-bom-id="row.id || ''">
              <td class="ys-check"><input type="checkbox" :disabled="isUiDisabled" /></td>
              <td><span class="ys-image-placeholder" aria-hidden="true"></span></td>
              <td><button class="ys-link" type="button" @click="openDetail(row)">{{ row.code }}</button></td>
              <td>{{ row.part }}</td>
              <td>{{ row.name }}</td>
              <td>{{ row.color }}</td>
              <td>{{ row.composition }}</td>
              <td>{{ row.width }}</td>
              <td>{{ row.weight }}</td>
              <td class="ys-actions">
                <button
                  type="button"
                  class="ys-text-button"
                  :disabled="!canCreate || isUiDisabled"
                  @click="duplicateRow(row)"
                >
                  复制
                </button>
                <button type="button" class="ys-text-button" @click="openDetail(row)">详情</button>
                <button type="button" class="ys-text-button ys-text-button--danger" disabled>删除</button>
              </td>
            </tr>
          </tbody>
          <tbody v-else>
            <tr>
              <td colspan="10" class="ys-empty" data-testid="m2-bom-empty-state">
                {{ emptyText }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <footer class="ys-pagination" data-testid="m2-bom-pagination">
        <span>共 {{ listTotal }} 条</span>
        <el-select v-model="pageSize" class="ys-page-size" size="small" @change="runQuery">
          <el-option :value="30" label="30条/页" />
          <el-option :value="60" label="60条/页" />
          <el-option :value="100" label="100条/页" />
        </el-select>
        <el-button size="small" disabled>‹</el-button>
        <el-button size="small" type="primary" class="ys-page-current">{{ currentPage }}</el-button>
        <el-button size="small" :disabled="visibleRows.length >= listTotal" @click="nextPage">›</el-button>
      </footer>
    </section>

    <el-dialog
      v-model="recordDialogVisible"
      width="720px"
      :title="recordDialogMode === 'create' ? '面料建档' : '面料编辑'"
      class="ys-bom-dialog"
      data-testid="m2-bom-record-dialog"
    >
      <el-form :model="recordForm" label-width="88px" class="ys-bom-form">
        <el-form-item label="款号">
          <el-input v-model="recordForm.itemCode" placeholder="请输入款号" data-testid="m2-bom-form-item-code" />
        </el-form-item>
        <el-form-item label="版本">
          <el-input v-model="recordForm.versionNo" placeholder="V1" />
        </el-form-item>
        <el-form-item label="编号">
          <el-input v-model="recordForm.materialItemCode" placeholder="物料编号" data-testid="m2-bom-form-material-code" />
        </el-form-item>
        <el-form-item label="名称">
          <el-input v-model="recordForm.materialName" placeholder="面料名称" data-testid="m2-bom-form-material-name" />
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
          :loading="writeLoading"
          :disabled="!canSubmitRecord"
          data-testid="m2-bom-save-button"
          @click="submitRecord"
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
  createBom,
  fetchBomList,
  updateBomDraft,
  type BomCreatePayload,
  type BomItemPayload,
  type BomListItem,
  type BomOperationPayload,
  type BomUpdatePayload,
} from '@/api/bom'
import { usePermissionStore } from '@/stores/permission'

type UiStateProbe = '' | 'loading' | 'error' | 'disabled' | 'empty' | 'no_permission'
type RecordDialogMode = 'create' | 'edit'

interface BomMaterialRow {
  id: number | null
  key: string
  bomNo: string
  itemCode: string
  versionNo: string
  status: string
  isDefault: boolean
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
const fallbackRows: BomMaterialRow[] = [
  {
    id: null,
    key: 'fallback-20260320001',
    bomNo: 'BOM-20260320001',
    itemCode: '20260320001',
    versionNo: 'V1',
    status: 'draft',
    isDefault: false,
    code: '20260320001',
    part: '',
    name: '雪纺里布',
    color: '',
    composition: '',
    width: '150',
    weight: '230',
  },
  {
    id: null,
    key: 'fallback-20260316001',
    bomNo: 'BOM-20260316001',
    itemCode: '20260316001',
    versionNo: 'V1',
    status: 'draft',
    isDefault: false,
    code: '20260316001',
    part: '',
    name: '针织布',
    color: '',
    composition: '',
    width: '150',
    weight: '230',
  },
  {
    id: null,
    key: 'fallback-20260316002',
    bomNo: 'BOM-20260316002',
    itemCode: '20260316002',
    versionNo: 'V1',
    status: 'draft',
    isDefault: false,
    code: '20260316002',
    part: '面料',
    name: '化纤',
    color: '黑色',
    composition: '',
    width: '150',
    weight: '0',
  },
]

const permissionStore = usePermissionStore()
const router = useRouter()
const route = useRoute()

const activeMaterialType = ref('fabric')
const currentPage = ref(1)
const pageSize = ref(30)
const listLoading = ref(false)
const listError = ref('')
const listTotal = ref(0)
const apiRows = ref<BomMaterialRow[]>([])
const filterOpen = ref(false)
const recordDialogVisible = ref(false)
const recordDialogMode = ref<RecordDialogMode>('create')
const writeLoading = ref(false)
const editingRow = ref<BomMaterialRow | null>(null)

const query = reactive({
  keyword: '',
  itemCode: '',
  status: '',
})

const recordForm = reactive<RecordFormState>({
  itemCode: 'ITEM-NEW',
  versionNo: 'V1',
  materialItemCode: 'MAT-NEW',
  materialName: '雪纺里布',
  part: '面料',
  color: '',
  composition: '',
  width: 150,
  weight: 230,
})

const uiStateProbe = computed<UiStateProbe>(() => {
  const raw = route.query.m2_state
  const value = Array.isArray(raw) ? raw[0] : raw
  if (value === 'loading' || value === 'error' || value === 'disabled' || value === 'empty' || value === 'no_permission') {
    return value
  }
  return ''
})

const buttonPermissions = computed(() => permissionStore.state.buttonPermissions)
const canRead = computed(() => buttonPermissions.value.read && uiStateProbe.value !== 'no_permission')
const canCreate = computed(() => buttonPermissions.value.create && uiStateProbe.value !== 'no_permission')
const canUpdate = computed(() => buttonPermissions.value.update && uiStateProbe.value !== 'no_permission')
const isUiDisabled = computed(() => uiStateProbe.value === 'disabled' || uiStateProbe.value === 'no_permission')
const isLoadingState = computed(() => listLoading.value || uiStateProbe.value === 'loading')
const isNoPermissionState = computed(() => !canRead.value || uiStateProbe.value === 'no_permission')

const activeRows = computed(() => (apiRows.value.length ? apiRows.value : fallbackRows))
const visibleRows = computed(() => {
  if (uiStateProbe.value === 'empty' || isNoPermissionState.value) return []
  const keyword = query.keyword.trim().toLowerCase()
  return activeRows.value.filter((row) => {
    const hitKeyword = keyword
      ? [row.code, row.name, row.itemCode, row.bomNo].join('|').toLowerCase().includes(keyword)
      : true
    const hitItem = query.itemCode.trim() ? row.itemCode.includes(query.itemCode.trim()) : true
    const hitStatus = query.status ? row.status === query.status : true
    return hitKeyword && hitItem && hitStatus
  })
})

const emptyText = computed(() => {
  if (uiStateProbe.value === 'no_permission' || !canRead.value) return '无权限查看面料档案'
  if (uiStateProbe.value === 'error') return '面料档案读取失败'
  return '暂无面料档案'
})

const stateMessage = computed(() => {
  if (uiStateProbe.value === 'no_permission' || !canRead.value) {
    return { type: 'warning' as const, text: '当前会话未获得 bom:read，面料列表 fail-closed。' }
  }
  if (uiStateProbe.value === 'error') {
    return { type: 'error' as const, text: '模拟错误状态：面料列表不可用。' }
  }
  if (listError.value) {
    return { type: 'warning' as const, text: listError.value }
  }
  if (uiStateProbe.value === 'disabled') {
    return { type: 'info' as const, text: '模拟禁用状态：写入按钮保持禁用。' }
  }
  return null
})

const canSubmitRecord = computed(() => {
  const hasRequired = Boolean(
    recordForm.itemCode.trim() &&
      recordForm.versionNo.trim() &&
      recordForm.materialItemCode.trim() &&
      recordForm.materialName.trim() &&
      recordForm.width > 0,
  )
  const hasPermission = recordDialogMode.value === 'create' ? canCreate.value : canUpdate.value
  return hasRequired && hasPermission && !isUiDisabled.value
})

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

const buildSourceRef = (scenarioTag: string, itemCode: string, versionNo: string): string =>
  `${scenarioTag}-SRC-${itemCode}-${versionNo}`

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
  remark: 'M2 BOM 真实端点写入',
})

const normalizeStatus = (status: string): string => {
  if (status === 'active' || status === 'published') return 'active'
  if (status === 'inactive') return 'inactive'
  return 'draft'
}

const mapBomListItem = (item: BomListItem): BomMaterialRow => ({
  id: item.id,
  key: String(item.id),
  bomNo: item.bom_no,
  itemCode: item.item_code,
  versionNo: item.version_no,
  status: normalizeStatus(item.status),
  isDefault: item.is_default,
  code: item.item_code,
  part: item.is_default ? '面料' : '',
  name: item.item_code,
  color: '',
  composition: '',
  width: '150',
  weight: item.is_default ? '230' : '0',
})

const loadPermissions = async (): Promise<void> => {
  try {
    await permissionStore.loadCurrentUser()
    await permissionStore.loadModuleActions('bom')
  } catch {
    // Permission state is fail-closed by the store.
  }
}

const loadBomList = async (): Promise<void> => {
  if (!canRead.value) {
    apiRows.value = []
    listTotal.value = 0
    return
  }
  if (uiStateProbe.value === 'loading' || uiStateProbe.value === 'error') {
    return
  }
  listLoading.value = true
  listError.value = ''
  try {
    const response = await fetchBomList({
      item_code: query.itemCode.trim() || undefined,
      status: query.status || undefined,
      page: currentPage.value,
      page_size: pageSize.value,
    })
    apiRows.value = response.data.items.map(mapBomListItem)
    listTotal.value = response.data.total
  } catch (error) {
    apiRows.value = []
    listTotal.value = 0
    listError.value = `面料列表读取失败：${(error as Error).message}`
  } finally {
    listLoading.value = false
  }
}

const runQuery = (): void => {
  currentPage.value = 1
  void loadBomList()
}

const resetQuery = (): void => {
  query.keyword = ''
  query.itemCode = ''
  query.status = ''
  runQuery()
}

const nextPage = (): void => {
  currentPage.value += 1
  void loadBomList()
}

const toggleFilter = (): void => {
  filterOpen.value = !filterOpen.value
}

const resetRecordForm = (): void => {
  recordForm.itemCode = 'ITEM-NEW'
  recordForm.versionNo = 'V1'
  recordForm.materialItemCode = 'MAT-NEW'
  recordForm.materialName = '雪纺里布'
  recordForm.part = '面料'
  recordForm.color = ''
  recordForm.composition = ''
  recordForm.width = 150
  recordForm.weight = 230
}

const openCreateDialog = (): void => {
  if (!canCreate.value) {
    ElMessage.warning('无 BOM 新建权限')
    return
  }
  recordDialogMode.value = 'create'
  editingRow.value = null
  resetRecordForm()
  recordDialogVisible.value = true
}

const duplicateRow = (row: BomMaterialRow): void => {
  if (!canCreate.value) {
    ElMessage.warning('无 BOM 新建权限')
    return
  }
  recordDialogMode.value = 'create'
  editingRow.value = null
  recordForm.itemCode = row.itemCode
  recordForm.versionNo = row.versionNo
  recordForm.materialItemCode = `${row.code}-COPY`
  recordForm.materialName = row.name
  recordForm.part = row.part || '面料'
  recordForm.color = row.color
  recordForm.composition = row.composition
  recordForm.width = Number(row.width) || 150
  recordForm.weight = Number(row.weight) || 0
  recordDialogVisible.value = true
}

const openEditDialog = (row: BomMaterialRow): void => {
  if (!canUpdate.value || !row.id) {
    ElMessage.warning('无 BOM 编辑权限或缺少真实 BOM ID')
    return
  }
  recordDialogMode.value = 'edit'
  editingRow.value = row
  recordForm.itemCode = row.itemCode
  recordForm.versionNo = row.versionNo
  recordForm.materialItemCode = row.code
  recordForm.materialName = row.name
  recordForm.part = row.part || '面料'
  recordForm.color = row.color
  recordForm.composition = row.composition
  recordForm.width = Number(row.width) || 150
  recordForm.weight = Number(row.weight) || 0
  recordDialogVisible.value = true
}

const submitRecord = async (): Promise<void> => {
  if (!canSubmitRecord.value) return
  writeLoading.value = true
  try {
    const scenarioTag = buildScenarioTag()
    const itemCode = recordForm.itemCode.trim()
    const versionNo = recordForm.versionNo.trim()
    const material = buildMaterialPayload()
    const operation = buildOperationPayload()

    if (recordDialogMode.value === 'create') {
      const sourceRef = buildSourceRef(scenarioTag, itemCode, versionNo)
      const requestId = buildRequestId(scenarioTag, itemCode, sourceRef)
      const payload: BomCreatePayload = {
        scenario_tag: scenarioTag,
        idempotency_key: requestId,
        source_ref: sourceRef,
        item_code: itemCode,
        version_no: versionNo,
        bom_items: [material],
        operations: [operation],
      }
      await createBom(payload, { requestId })
      ElMessage.success('面料建档已提交真实 BOM 端点')
    } else if (editingRow.value?.id) {
      const sourceRef = editingRow.value.bomNo
      const requestId = buildRequestId(scenarioTag, itemCode, sourceRef)
      const payload: BomUpdatePayload = {
        scenario_tag: scenarioTag,
        idempotency_key: requestId,
        source_ref: sourceRef,
        bom_no: editingRow.value.bomNo,
        item_code: itemCode,
        version_no: versionNo,
        bom_items: [material],
        operations: [operation],
      }
      await updateBomDraft(editingRow.value.id, payload, { requestId })
      ElMessage.success('面料编辑已提交真实 BOM 端点')
    }
    recordDialogVisible.value = false
    await loadBomList()
  } catch (error) {
    ElMessage.error(`保存失败：${(error as Error).message}`)
  } finally {
    writeLoading.value = false
  }
}

const openDetail = (row: BomMaterialRow): void => {
  void router.push({
    path: '/bom/detail',
    query: {
      bom_id: row.id ? String(row.id) : '',
      bom_no: row.bomNo,
      item_code: row.itemCode,
      version_no: row.versionNo,
      material_name: row.name,
      color: row.color,
      composition: row.composition,
      width: row.width,
      weight: row.weight,
      ...(route.query.m2_state ? { m2_state: route.query.m2_state } : {}),
    },
  })
}

onMounted(async () => {
  await loadPermissions()
  await loadBomList()
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
.ys-pagination,
.ys-actions {
  display: flex;
  align-items: center;
}

.ys-bom-crumbs {
  gap: 10px;
  color: var(--ys-color-text-title);
}

.ys-bom-crumbs__active {
  color: var(--ys-color-text-main);
}

.ys-icon {
  font-size: 24px;
  color: var(--ys-color-text-minor);
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

.ys-bom-search {
  width: 288px;
}

.ys-primary-button,
.ys-secondary-button,
.ys-danger-button {
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

.ys-danger-button {
  background: #ff9da1;
  border-color: #ff9da1;
  color: #fff;
}

.ys-button-caret {
  margin-left: 4px;
}

.ys-filter-row {
  display: grid;
  grid-template-columns: 180px 140px auto auto 1fr;
  gap: 8px;
  margin-top: 10px;
}

.ys-state-alert {
  margin-top: 10px;
}

.ys-bom-table-wrap {
  position: relative;
  margin-top: 18px;
  border: 1px solid #e4e7ed;
  min-height: 710px;
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

.ys-bom-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
  background: #fff;
}

.ys-bom-table th {
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

.ys-bom-table td {
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
  width: 170px;
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
  cursor: pointer;
}

.ys-text-button {
  padding: 0 6px;
  font-size: 12px;
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

.ys-pagination {
  justify-content: center;
  gap: 10px;
  height: 64px;
  color: var(--ys-color-text-main);
}

.ys-page-size {
  width: 128px;
}

.ys-page-current {
  min-width: 32px;
}

.ys-bom-form {
  display: grid;
  grid-template-columns: 1fr 1fr;
  column-gap: 16px;
}

@media (max-width: 980px) {
  .ys-bom-topbar {
    grid-template-columns: 1fr;
    height: auto;
    padding: 10px 0;
  }

  .ys-bom-top-actions {
    justify-content: flex-start;
    flex-wrap: wrap;
  }

  .ys-bom-toolbar {
    flex-wrap: wrap;
  }

  .ys-bom-toolbar__spacer {
    display: none;
  }

  .ys-bom-form,
  .ys-filter-row {
    grid-template-columns: 1fr;
  }
}
</style>
