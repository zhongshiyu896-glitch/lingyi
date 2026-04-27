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
        <el-table :data="rows" v-loading="loading" border empty-text="暂无BOM数据">
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
      </template>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { fetchBomList, type BomListItem } from '@/api/bom'
import { usePermissionStore } from '@/stores/permission'

const router = useRouter()
const loading = ref<boolean>(false)
const rows = ref<BomListItem[]>([])
const total = ref<number>(0)
const permissionStore = usePermissionStore()
const canRead = computed<boolean>(() => permissionStore.state.buttonPermissions.read)
const canCreate = computed<boolean>(() => permissionStore.state.buttonPermissions.create)

const query = reactive({
  item_code: '',
  status: '',
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

onMounted(async () => {
  try {
    await permissionStore.loadCurrentUser()
    await permissionStore.loadModuleActions('bom')
  } catch (error) {
    ElMessage.error((error as Error).message)
  }
  await loadList()
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
</style>
