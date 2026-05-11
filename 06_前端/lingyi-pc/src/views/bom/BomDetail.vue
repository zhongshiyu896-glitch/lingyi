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
            <el-input :model-value="form.version_no" disabled data-testid="bom-detail-field-version-no" />
          </el-form-item>
          <el-form-item label="状态">
            <el-tag :type="statusTagType" data-testid="bom-detail-status-tag">{{ statusText }}</el-tag>
          </el-form-item>
        </el-form>

        <div class="actions" data-testid="bom-detail-actions">
          <el-button
            data-testid="bom-detail-action-save-draft"
            data-action-type="write"
            data-write-guard="guarded:readonly"
            @click="guardedWriteAction('保存草稿')"
          >
            保存草稿
          </el-button>
          <el-button
            data-testid="bom-detail-action-create"
            data-action-type="write"
            data-write-guard="guarded:readonly"
            @click="guardedWriteAction('创建 BOM')"
          >
            创建 BOM
          </el-button>
          <el-button
            data-testid="bom-detail-action-set-default"
            data-action-type="write"
            data-write-guard="guarded:readonly"
            @click="guardedWriteAction('设为默认')"
          >
            设为默认
          </el-button>
          <el-button
            data-testid="bom-detail-action-activate"
            data-action-type="write"
            data-write-guard="guarded:readonly"
            @click="guardedWriteAction('发布')"
          >
            发布
          </el-button>
          <el-button
            data-testid="bom-detail-action-deactivate"
            data-action-type="write"
            data-write-guard="guarded:readonly"
            @click="guardedWriteAction('停用')"
          >
            停用
          </el-button>
          <el-button
            data-testid="bom-detail-action-explode"
            data-action-type="write"
            data-write-guard="guarded:readonly"
            @click="guardedWriteAction('展开计算')"
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
          v-if="showEmptyState"
          data-testid="bom-detail-empty-state"
          title="暂无 BOM 明细数据"
          type="info"
          show-icon
          :closable="false"
          style="margin-top: 12px"
        />

        <p class="state-tip" data-testid="bom-detail-permission-or-disabled-state">
          当前页面仅提供只读浏览，写操作入口均已禁用。
        </p>
      </template>
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
import { fetchBomDetail } from '@/api/bom'
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

const form = reactive({
  item_code: '',
  version_no: 'V1',
})

const bomItems = ref<BomItemForm[]>([])
const operations = ref<BomOperationForm[]>([])
const loadError = ref<string>('')
const guardedFeedback = ref<string>('')
const loading = ref<boolean>(false)
const detailLoaded = ref<boolean>(false)

const canRead = computed<boolean>(() => permissionStore.state.buttonPermissions.read)
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

const guardedWriteAction = (action: string): void => {
  guardedFeedback.value = `${action}已禁用：详情页当前为只读模式`
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
