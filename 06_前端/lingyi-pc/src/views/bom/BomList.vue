<template>
  <div class="bom-list-page">
    <el-card shadow="never">
      <el-form :inline="true" :model="query">
        <el-form-item label="款式编码">
          <el-input v-model="query.item_code" clearable placeholder="Item Code" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select
            v-model="query.status"
            clearable
            placeholder="请选择状态"
            aria-label="BOM状态筛选"
            style="width: 160px"
          >
            <el-option label="草稿" value="draft" />
            <el-option label="已发布" value="active" />
            <el-option label="已停用" value="inactive" />
          </el-select>
        </el-form-item>
        <el-form-item label="操作">
          <el-button type="primary" :disabled="!canRead" @click="loadList">查询</el-button>
          <el-button
            v-if="canCreate"
            data-action-type="write"
            data-write-guard="permission:create(v-if)"
            data-guard-state="visible_when_allowed"
            @click="goCreate"
          >
            新建 BOM
          </el-button>
        </el-form-item>
      </el-form>

      <el-empty v-if="!canRead" description="无 BOM 查看权限" />
      <template v-else>
        <el-table :data="rows" v-loading="loading" border empty-text="暂无BOM数据" class="bom-main-table">
          <el-table-column prop="bom_no" label="BOM编号" min-width="280" />
          <el-table-column prop="item_code" label="款式编码" min-width="140" />
          <el-table-column prop="version_no" label="版本" min-width="100" />
          <el-table-column prop="status" label="状态" width="120" />
          <el-table-column label="默认" width="80">
            <template #default="scope">
              <el-tag :type="scope.row.is_default ? 'success' : 'info'">
                {{ scope.row.is_default ? '是' : '否' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="effective_date" label="生效日期" min-width="120" />
          <el-table-column label="操作" width="120" fixed="right">
            <template #default="scope">
              <el-button link type="primary" @click="goDetail(scope.row.id)">详情</el-button>
            </template>
          </el-table-column>
        </el-table>

        <div class="pager">
          <el-pagination
            background
            layout="prev, pager, next, total, sizes"
            :current-page="query.page"
            :page-size="query.page_size"
            :total="total"
            :page-sizes="[10, 20, 50, 100]"
            @current-change="onPageChange"
            @size-change="onSizeChange"
          />
        </div>

        <el-divider content-position="left">物料图库（TASK-Y22B-P1-01）</el-divider>

        <section class="material-gallery-section">
          <el-form :inline="true" :model="galleryQuery">
            <el-form-item label="物料分类">
              <el-select
                v-model="galleryQuery.category"
                clearable
                placeholder="请选择分类"
                style="width: 170px"
                aria-label="物料分类筛选"
              >
                <el-option v-for="category in galleryCategoryOptions" :key="category" :label="category" :value="category" />
              </el-select>
            </el-form-item>
            <el-form-item label="款号">
              <el-input v-model="galleryQuery.item_code" clearable placeholder="请输入款号" />
            </el-form-item>
            <el-form-item label="物料编码">
              <el-input v-model="galleryQuery.material_item_code" clearable placeholder="请输入物料编码" />
            </el-form-item>
            <el-form-item label="颜色">
              <el-input v-model="galleryQuery.color" clearable placeholder="请输入颜色" />
            </el-form-item>
            <el-form-item label="规格">
              <el-input v-model="galleryQuery.size" clearable placeholder="请输入规格" />
            </el-form-item>
            <el-form-item label="操作">
              <el-button type="primary" :disabled="!canRead" @click="loadGallery">查询</el-button>
              <el-button :disabled="!canRead" @click="resetGalleryQuery">重置</el-button>
              <el-button
                data-action-type="write"
                data-write-guard="readonly-gallery-choose"
                @click="guardedReadonlyAction('选用')"
              >
                选用
              </el-button>
              <el-button
                data-action-type="write"
                data-write-guard="readonly-gallery-upload"
                @click="guardedReadonlyAction('上传')"
              >
                上传
              </el-button>
              <el-button
                data-action-type="write"
                data-write-guard="readonly-gallery-edit"
                @click="guardedReadonlyAction('编辑')"
              >
                编辑
              </el-button>
              <el-button
                data-action-type="write"
                data-write-guard="readonly-gallery-delete"
                @click="guardedReadonlyAction('删除')"
              >
                删除
              </el-button>
            </el-form-item>
          </el-form>

          <el-alert
            v-if="galleryError"
            class="gallery-error-alert"
            title="物料图库加载失败"
            :description="galleryError"
            type="error"
            show-icon
            :closable="false"
          />

          <el-table
            class="material-gallery-table"
            :data="galleryRows"
            v-loading="galleryLoading"
            border
            empty-text="暂无物料图库数据"
          >
            <el-table-column label="素材" width="100">
              <template #default="scope">
                <div class="gallery-thumb">
                  <span>{{ materialThumbText(scope.row.material_item_code) }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="category" label="物料分类" min-width="120" />
            <el-table-column prop="item_code" label="款号" min-width="130" />
            <el-table-column prop="material_item_code" label="物料编码" min-width="160" />
            <el-table-column prop="color" label="颜色" min-width="100" />
            <el-table-column prop="size" label="规格" min-width="100" />
            <el-table-column prop="qty_per_piece" label="单件用量" min-width="100" />
            <el-table-column prop="loss_rate" label="损耗率" min-width="90" />
            <el-table-column prop="uom" label="单位" width="80" />
            <el-table-column label="状态" width="110">
              <template #default="scope">
                <el-tag :type="statusTagType(scope.row.status)">{{ scope.row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="bom_no" label="来源BOM" min-width="160" />
            <el-table-column label="操作" width="240" fixed="right">
              <template #default="scope">
                <el-button link type="primary" @click="openGalleryPreview(scope.row)">查看</el-button>
                <el-button link type="warning" @click="guardedReadonlyAction('选用')">选用</el-button>
                <el-button link type="info" @click="guardedReadonlyAction('上传')">上传</el-button>
                <el-button link type="info" @click="guardedReadonlyAction('编辑')">编辑</el-button>
                <el-button link type="danger" @click="guardedReadonlyAction('删除')">删除</el-button>
              </template>
            </el-table-column>
          </el-table>

          <div class="pager gallery-pager">
            <el-pagination
              background
              layout="prev, pager, next, total, sizes"
              :current-page="galleryQuery.page"
              :page-size="galleryQuery.page_size"
              :total="galleryTotal"
              :page-sizes="[10, 20, 50, 100]"
              @current-change="onGalleryPageChange"
              @size-change="onGallerySizeChange"
            />
          </div>
        </section>

        <el-divider content-position="left">物料采购单（TASK-Y22B-P1-04）</el-divider>

        <section class="purchase-order-section">
          <el-form :inline="true" :model="purchaseQuery">
            <el-form-item label="采购单号">
              <el-input v-model="purchaseQuery.purchase_no" clearable placeholder="请输入采购单号" />
            </el-form-item>
            <el-form-item label="供应商">
              <el-input v-model="purchaseQuery.supplier_name" clearable placeholder="请输入供应商" />
            </el-form-item>
            <el-form-item label="物料">
              <el-input v-model="purchaseQuery.material_keyword" clearable placeholder="请输入物料编码/名称" />
            </el-form-item>
            <el-form-item label="交期">
              <el-date-picker
                v-model="purchaseQuery.delivery_date_range"
                type="daterange"
                unlink-panels
                range-separator="至"
                start-placeholder="开始日期"
                end-placeholder="结束日期"
                value-format="YYYY-MM-DD"
              />
            </el-form-item>
            <el-form-item label="状态">
              <el-select
                v-model="purchaseQuery.status"
                clearable
                placeholder="请选择状态"
                style="width: 150px"
                aria-label="采购单状态筛选"
              >
                <el-option label="草稿" value="草稿" />
                <el-option label="待确认" value="待确认" />
                <el-option label="已确认" value="已确认" />
                <el-option label="已取消" value="已取消" />
              </el-select>
            </el-form-item>
            <el-form-item label="数量区间">
              <el-input-number v-model="purchaseQuery.min_qty" :min="0" :controls="false" placeholder="最小数量" />
              <span class="range-sep">-</span>
              <el-input-number v-model="purchaseQuery.max_qty" :min="0" :controls="false" placeholder="最大数量" />
            </el-form-item>
            <el-form-item label="金额区间">
              <el-input-number v-model="purchaseQuery.min_amount" :min="0" :controls="false" placeholder="最小金额" />
              <span class="range-sep">-</span>
              <el-input-number v-model="purchaseQuery.max_amount" :min="0" :controls="false" placeholder="最大金额" />
            </el-form-item>
            <el-form-item label="操作">
              <el-button type="primary" :disabled="!canRead" @click="loadPurchaseOrders">查询</el-button>
              <el-button :disabled="!canRead" @click="resetPurchaseQuery">重置</el-button>
              <el-button
                data-action-type="write"
                data-write-guard="readonly-purchase-generate"
                @click="guardedReadonlyAction('生成采购')"
              >
                生成采购
              </el-button>
              <el-button
                data-action-type="write"
                data-write-guard="readonly-purchase-confirm"
                @click="guardedReadonlyAction('确认')"
              >
                确认
              </el-button>
              <el-button
                data-action-type="write"
                data-write-guard="readonly-purchase-cancel"
                @click="guardedReadonlyAction('取消')"
              >
                取消
              </el-button>
              <el-button
                data-action-type="write"
                data-write-guard="readonly-purchase-export"
                @click="guardedReadonlyAction('导出')"
              >
                导出
              </el-button>
            </el-form-item>
          </el-form>

          <el-alert
            v-if="purchaseError"
            class="purchase-error-alert"
            title="物料采购单加载失败"
            :description="purchaseError"
            type="error"
            show-icon
            :closable="false"
          />

          <el-table
            class="purchase-order-table"
            :data="purchaseRows"
            v-loading="purchaseLoading"
            border
            empty-text="暂无物料采购单数据"
          >
            <el-table-column prop="purchase_no" label="采购单号" min-width="220" />
            <el-table-column prop="supplier_name" label="供应商" min-width="160" />
            <el-table-column prop="item_code" label="款号" min-width="120" />
            <el-table-column prop="material_item_code" label="物料编码" min-width="160" />
            <el-table-column prop="material_name" label="物料名称" min-width="150" />
            <el-table-column prop="qty" label="数量" min-width="100" />
            <el-table-column prop="uom" label="单位" width="80" />
            <el-table-column prop="unit_price" label="单价" min-width="110" />
            <el-table-column prop="total_amount" label="金额" min-width="120" />
            <el-table-column prop="expected_delivery_date" label="交期" min-width="120" />
            <el-table-column label="状态" width="110">
              <template #default="scope">
                <el-tag :type="purchaseStatusTagType(scope.row.status)">{{ scope.row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="270" fixed="right">
              <template #default="scope">
                <el-button link type="primary" @click="openPurchaseDetail(scope.row)">查看</el-button>
                <el-button link type="warning" @click="guardedReadonlyAction('生成采购')">生成采购</el-button>
                <el-button link type="success" @click="guardedReadonlyAction('确认')">确认</el-button>
                <el-button link type="danger" @click="guardedReadonlyAction('取消')">取消</el-button>
                <el-button link type="info" @click="guardedReadonlyAction('导出')">导出</el-button>
              </template>
            </el-table-column>
          </el-table>

          <div class="pager purchase-pager">
            <el-pagination
              background
              layout="prev, pager, next, total, sizes"
              :current-page="purchaseQuery.page"
              :page-size="purchaseQuery.page_size"
              :total="purchaseTotal"
              :page-sizes="[10, 20, 50, 100]"
              @current-change="onPurchasePageChange"
              @size-change="onPurchaseSizeChange"
            />
          </div>
        </section>
      </template>
    </el-card>

    <el-dialog v-model="previewVisible" title="物料图库预览" width="520px">
      <template v-if="previewRow">
        <div class="preview-grid">
          <div class="preview-thumb">{{ materialThumbText(previewRow.material_item_code) }}</div>
          <div class="preview-meta">
            <p>款号：{{ previewRow.item_code }}</p>
            <p>物料编码：{{ previewRow.material_item_code }}</p>
            <p>物料分类：{{ previewRow.category }}</p>
            <p>颜色/规格：{{ previewRow.color || '-' }} / {{ previewRow.size || '-' }}</p>
            <p>单件用量：{{ previewRow.qty_per_piece }} {{ previewRow.uom }}</p>
            <p>损耗率：{{ previewRow.loss_rate }}</p>
            <p>来源BOM：{{ previewRow.bom_no }}</p>
          </div>
        </div>
      </template>
      <template #footer>
        <el-button @click="previewVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  fetchBomList,
  fetchBomMaterialGallery,
  fetchBomPurchaseOrders,
  type BomListItem,
  type BomMaterialGalleryItem,
  type BomPurchaseOrderItem,
} from '@/api/bom'
import { usePermissionStore } from '@/stores/permission'

const router = useRouter()
const loading = ref<boolean>(false)
const rows = ref<BomListItem[]>([])
const total = ref<number>(0)
const galleryLoading = ref<boolean>(false)
const galleryRows = ref<BomMaterialGalleryItem[]>([])
const galleryTotal = ref<number>(0)
const galleryError = ref<string>('')
const galleryCategoryOptions = ref<string[]>([])
const purchaseLoading = ref<boolean>(false)
const purchaseRows = ref<BomPurchaseOrderItem[]>([])
const purchaseTotal = ref<number>(0)
const purchaseError = ref<string>('')
const previewVisible = ref<boolean>(false)
const previewRow = ref<BomMaterialGalleryItem | null>(null)
const permissionStore = usePermissionStore()
const canRead = computed<boolean>(() => permissionStore.state.buttonPermissions.read)
const canCreate = computed<boolean>(() => permissionStore.state.buttonPermissions.create)

const query = reactive({
  item_code: '',
  status: '',
  page: 1,
  page_size: 20,
})

const galleryQuery = reactive({
  item_code: '',
  material_item_code: '',
  color: '',
  size: '',
  category: '',
  status: '',
  page: 1,
  page_size: 20,
})

const purchaseQuery = reactive({
  purchase_no: '',
  supplier_name: '',
  material_keyword: '',
  status: '',
  delivery_date_range: [] as string[],
  min_qty: undefined as number | undefined,
  max_qty: undefined as number | undefined,
  min_amount: undefined as number | undefined,
  max_amount: undefined as number | undefined,
  page: 1,
  page_size: 20,
})

const loadList = async (): Promise<void> => {
  if (!canRead.value) {
    rows.value = []
    total.value = 0
    return
  }
  loading.value = true
  try {
    const result = await fetchBomList(query)
    rows.value = result.data.items
    total.value = result.data.total
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    loading.value = false
  }
}

const onPageChange = (page: number): void => {
  query.page = page
  loadList()
}

const onSizeChange = (size: number): void => {
  query.page_size = size
  query.page = 1
  loadList()
}

const loadGallery = async (): Promise<void> => {
  if (!canRead.value) {
    galleryRows.value = []
    galleryTotal.value = 0
    galleryError.value = ''
    return
  }
  galleryLoading.value = true
  galleryError.value = ''
  try {
    const result = await fetchBomMaterialGallery(galleryQuery)
    galleryRows.value = result.data.items
    galleryTotal.value = result.data.total
    galleryCategoryOptions.value = Array.from(
      new Set(result.data.items.map((item) => item.category).filter((category) => category)),
    )
  } catch (error) {
    galleryRows.value = []
    galleryTotal.value = 0
    galleryError.value = (error as Error).message
    ElMessage.error((error as Error).message)
  } finally {
    galleryLoading.value = false
  }
}

const onGalleryPageChange = (page: number): void => {
  galleryQuery.page = page
  loadGallery()
}

const onGallerySizeChange = (size: number): void => {
  galleryQuery.page_size = size
  galleryQuery.page = 1
  loadGallery()
}

const loadPurchaseOrders = async (): Promise<void> => {
  if (!canRead.value) {
    purchaseRows.value = []
    purchaseTotal.value = 0
    purchaseError.value = ''
    return
  }
  purchaseLoading.value = true
  purchaseError.value = ''
  try {
    const [deliveryDateFrom, deliveryDateTo] = purchaseQuery.delivery_date_range
    const result = await fetchBomPurchaseOrders({
      purchase_no: purchaseQuery.purchase_no,
      supplier_name: purchaseQuery.supplier_name,
      material_keyword: purchaseQuery.material_keyword,
      status: purchaseQuery.status,
      delivery_date_from: deliveryDateFrom || undefined,
      delivery_date_to: deliveryDateTo || undefined,
      min_qty: purchaseQuery.min_qty,
      max_qty: purchaseQuery.max_qty,
      min_amount: purchaseQuery.min_amount,
      max_amount: purchaseQuery.max_amount,
      page: purchaseQuery.page,
      page_size: purchaseQuery.page_size,
    })
    purchaseRows.value = result.data.items
    purchaseTotal.value = result.data.total
  } catch (error) {
    purchaseRows.value = []
    purchaseTotal.value = 0
    purchaseError.value = (error as Error).message
    ElMessage.error((error as Error).message)
  } finally {
    purchaseLoading.value = false
  }
}

const resetPurchaseQuery = (): void => {
  purchaseQuery.purchase_no = ''
  purchaseQuery.supplier_name = ''
  purchaseQuery.material_keyword = ''
  purchaseQuery.status = ''
  purchaseQuery.delivery_date_range = []
  purchaseQuery.min_qty = undefined
  purchaseQuery.max_qty = undefined
  purchaseQuery.min_amount = undefined
  purchaseQuery.max_amount = undefined
  purchaseQuery.page = 1
  purchaseQuery.page_size = 20
  loadPurchaseOrders()
}

const onPurchasePageChange = (page: number): void => {
  purchaseQuery.page = page
  loadPurchaseOrders()
}

const onPurchaseSizeChange = (size: number): void => {
  purchaseQuery.page_size = size
  purchaseQuery.page = 1
  loadPurchaseOrders()
}

const purchaseStatusTagType = (status: string): 'success' | 'warning' | 'info' => {
  if (status === '已确认') return 'success'
  if (status === '已取消') return 'warning'
  return 'info'
}

const resetGalleryQuery = (): void => {
  galleryQuery.item_code = ''
  galleryQuery.material_item_code = ''
  galleryQuery.color = ''
  galleryQuery.size = ''
  galleryQuery.category = ''
  galleryQuery.status = ''
  galleryQuery.page = 1
  galleryQuery.page_size = 20
  loadGallery()
}

const statusTagType = (status: string): 'success' | 'info' | 'warning' => {
  if (status === 'active') return 'success'
  if (status === 'inactive') return 'warning'
  return 'info'
}

const materialThumbText = (materialItemCode: string): string => {
  const tokens = materialItemCode.split(/[-_]/).filter(Boolean)
  return (tokens[0] || 'IMG').slice(0, 3).toUpperCase()
}

const openGalleryPreview = (row: BomMaterialGalleryItem): void => {
  previewRow.value = row
  previewVisible.value = true
}

const guardedReadonlyAction = (action: string): void => {
  ElMessage.warning(`${action}功能受控：当前仅开放只读演示`)
}

const goDetail = (id: number): void => {
  router.push({ path: '/bom/detail', query: { id: String(id) } })
}

const goCreate = (): void => {
  if (!canCreate.value) {
    ElMessage.warning('无新建 BOM 权限')
    return
  }
  router.push('/bom/detail')
}

const openPurchaseDetail = (row: BomPurchaseOrderItem): void => {
  goDetail(row.bom_id)
}

onMounted(async () => {
  try {
    await permissionStore.loadCurrentUser()
    await permissionStore.loadModuleActions('bom')
  } catch (error) {
    ElMessage.error((error as Error).message)
  }
  await loadList()
  await loadGallery()
  await loadPurchaseOrders()
})
</script>

<style scoped>
.bom-list-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.pager {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}

.material-gallery-section {
  margin-top: 8px;
}

.purchase-order-section {
  margin-top: 8px;
}

.gallery-pager {
  margin-top: 10px;
}

.purchase-pager {
  margin-top: 10px;
}

.range-sep {
  margin: 0 6px;
  color: var(--el-text-color-secondary);
}

.gallery-thumb {
  width: 52px;
  height: 52px;
  border-radius: 8px;
  border: 1px solid var(--el-border-color);
  background: var(--el-fill-color-light);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.gallery-error-alert {
  margin-bottom: 12px;
}

.purchase-error-alert {
  margin-bottom: 12px;
}

.preview-grid {
  display: grid;
  grid-template-columns: 120px 1fr;
  gap: 12px;
  align-items: start;
}

.preview-thumb {
  width: 120px;
  height: 120px;
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  background: var(--el-fill-color-light);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  color: var(--el-text-color-secondary);
}

.preview-meta p {
  margin: 0 0 6px;
}
</style>
