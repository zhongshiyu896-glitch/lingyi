<template>
  <div class="operation-wage-rate">
    <el-card shadow="never">
      <template #header>
        <div class="header-row">
          <span>工价档案</span>
          <div class="header-actions">
            <el-button @click="goList">返回工票列表</el-button>
            <el-button type="primary" :disabled="!canManage" @click="createVisible = true">新增工价</el-button>
          </div>
        </div>
      </template>

      <el-form :inline="true" :model="query">
        <el-form-item label="款式">
          <el-input v-model="query.item_code" clearable placeholder="Item Code，空表示通用工价" />
        </el-form-item>
        <el-form-item label="公司">
          <el-input v-model="query.company" clearable placeholder="Company" />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="query.rate_scope" clearable style="width: 140px">
            <el-option label="全部" value="" />
            <el-option label="款式专属" value="specific" />
            <el-option label="通用工价" value="global" />
          </el-select>
        </el-form-item>
        <el-form-item label="工序">
          <el-input v-model="query.process_name" clearable placeholder="Process" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.status" clearable style="width: 140px">
            <el-option label="active" value="active" />
            <el-option label="inactive" value="inactive" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :disabled="!canRead" @click="loadRows">查询</el-button>
        </el-form-item>
      </el-form>

      <el-empty v-if="!canRead" description="无工价查看权限" />
      <template v-else>
        <el-table :data="rows" v-loading="loading" border>
          <el-table-column prop="id" label="ID" width="80" />
          <el-table-column label="类型" width="110">
            <template #default="scope">
              {{ scope.row.is_global ? '通用' : '款式专属' }}
            </template>
          </el-table-column>
          <el-table-column label="款式" min-width="140">
            <template #default="scope">
              {{ scope.row.item_code || '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="company" label="公司" min-width="120" />
          <el-table-column prop="process_name" label="工序" min-width="120" />
          <el-table-column prop="wage_rate" label="计件单价" min-width="120" />
          <el-table-column prop="effective_from" label="生效开始" min-width="120" />
          <el-table-column prop="effective_to" label="生效结束" min-width="120" />
          <el-table-column prop="status" label="状态" width="110" />
          <el-table-column prop="created_by" label="创建人" min-width="120" />
          <el-table-column label="操作" width="130" fixed="right">
            <template #default="scope">
              <el-button
                v-if="canManage"
                link
                type="danger"
                :disabled="scope.row.status !== 'active' || (scope.row.is_global && !canManageAll)"
                @click="deactivate(scope.row.id)"
              >
                停用
              </el-button>
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

    <el-dialog v-model="createVisible" title="新增工价" width="540px">
      <el-form label-width="120px" :model="createForm">
        <el-form-item label="款式">
          <el-input v-model="createForm.item_code" placeholder="可为空，空表示通用工价" />
        </el-form-item>
        <el-form-item label="公司">
          <el-input v-model="createForm.company" placeholder="建议填写，款式工价必填" />
        </el-form-item>
        <el-form-item label="工序">
          <el-input v-model="createForm.process_name" />
        </el-form-item>
        <el-form-item label="计件单价">
          <el-input-number v-model="createForm.wage_rate" :min="0" :step="0.01" :precision="6" />
        </el-form-item>
        <el-form-item label="生效开始">
          <el-date-picker v-model="createForm.effective_from" type="date" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="生效结束">
          <el-date-picker v-model="createForm.effective_to" type="date" value-format="YYYY-MM-DD" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :disabled="!canManage" :loading="creating" @click="createRate">
          提交
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createWorkshopWageRate,
  deactivateWorkshopWageRate,
  fetchWorkshopWageRates,
  type WorkshopWageRateRow,
} from '@/api/workshop'
import { usePermissionStore } from '@/stores/permission'

const router = useRouter()
const permissionStore = usePermissionStore()
const loading = ref<boolean>(false)
const creating = ref<boolean>(false)
const createVisible = ref<boolean>(false)
const rows = ref<WorkshopWageRateRow[]>([])
const total = ref<number>(0)

const query = reactive({
  item_code: '',
  company: '',
  rate_scope: '',
  process_name: '',
  status: '',
  page: 1,
  page_size: 20,
})

const createForm = reactive({
  item_code: '',
  company: '',
  process_name: '',
  wage_rate: 0,
  effective_from: '',
  effective_to: '',
})

const canRead = computed<boolean>(() => permissionStore.state.buttonPermissions.wage_rate_read)
const canReadAll = computed<boolean>(() => permissionStore.state.buttonPermissions.wage_rate_read_all)
const canManage = computed<boolean>(() => permissionStore.state.buttonPermissions.wage_rate_manage)
const canManageAll = computed<boolean>(() => permissionStore.state.buttonPermissions.wage_rate_manage_all)

const buildWageRateQuery = (): {
  item_code?: string
  company?: string
  is_global?: boolean
  process_name?: string
  status?: string
  page: number
  page_size: number
} => ({
  item_code: query.item_code || undefined,
  company: query.company || undefined,
  is_global:
    query.rate_scope === 'global' ? true : query.rate_scope === 'specific' ? false : undefined,
  process_name: query.process_name || undefined,
  status: query.status || undefined,
  page: query.page,
  page_size: query.page_size,
})

const loadRows = async (): Promise<void> => {
  if (!canRead.value) {
    rows.value = []
    total.value = 0
    return
  }
  if (query.rate_scope === 'global' && !canReadAll.value) {
    rows.value = []
    total.value = 0
    ElMessage.warning('无通用工价查看权限')
    return
  }
  loading.value = true
  try {
    const result = await fetchWorkshopWageRates(buildWageRateQuery())
    rows.value = result.data.items
    total.value = result.data.total
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    loading.value = false
  }
}

const createRate = async (): Promise<void> => {
  if (!createForm.process_name || !createForm.effective_from) {
    ElMessage.warning('请填写工序和生效开始日期')
    return
  }
  const isGlobalRate = !createForm.item_code.trim()
  if (isGlobalRate && !canManageAll.value) {
    ElMessage.error('无通用工价维护权限')
    return
  }
  creating.value = true
  try {
    await createWorkshopWageRate({
      item_code: createForm.item_code || undefined,
      company: createForm.company || undefined,
      process_name: createForm.process_name,
      wage_rate: createForm.wage_rate,
      effective_from: createForm.effective_from,
      effective_to: createForm.effective_to || null,
    })
    ElMessage.success('工价创建成功')
    createVisible.value = false
    createForm.item_code = ''
    createForm.company = ''
    createForm.process_name = ''
    createForm.wage_rate = 0
    createForm.effective_from = ''
    createForm.effective_to = ''
    await loadRows()
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    creating.value = false
  }
}

const deactivate = async (id: number): Promise<void> => {
  try {
    const reason = await ElMessageBox.prompt('请输入停用原因', '停用工价', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      inputPlaceholder: '例如：新工价生效替代',
    })
    await deactivateWorkshopWageRate(id, reason.value || 'manual deactivate')
    ElMessage.success('已停用')
    await loadRows()
  } catch (error) {
    if ((error as Error).message?.includes('cancel')) {
      return
    }
    ElMessage.error((error as Error).message)
  }
}

const onPageChange = (page: number): void => {
  query.page = page
  loadRows()
}

const onSizeChange = (size: number): void => {
  query.page_size = size
  query.page = 1
  loadRows()
}

const goList = (): void => {
  void router.push('/workshop/tickets')
}

onMounted(async () => {
  try {
    await permissionStore.loadCurrentUser()
    await permissionStore.loadModuleActions('workshop')
  } catch (error) {
    ElMessage.error((error as Error).message)
  }
  await loadRows()
})
</script>

<style scoped>
.operation-wage-rate {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.pager {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}
</style>
