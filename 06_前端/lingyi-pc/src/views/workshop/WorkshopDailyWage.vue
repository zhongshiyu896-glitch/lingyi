<template>
  <div class="workshop-daily-wage">
    <el-card shadow="never">
      <template #header>
        <div class="header-row">
          <span>员工日薪统计</span>
          <el-button @click="goList">返回工票列表</el-button>
        </div>
      </template>

      <el-form :inline="true" :model="query">
        <el-form-item label="员工">
          <el-input v-model="query.employee" clearable placeholder="Employee" />
        </el-form-item>
        <el-form-item label="工序">
          <el-input v-model="query.process_name" clearable placeholder="Process" />
        </el-form-item>
        <el-form-item label="款式">
          <el-input v-model="query.item_code" clearable placeholder="Item Code" />
        </el-form-item>
        <el-form-item label="日期从">
          <el-date-picker v-model="query.from_date" type="date" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="到">
          <el-date-picker v-model="query.to_date" type="date" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :disabled="!canRead" @click="loadRows">查询</el-button>
        </el-form-item>
      </el-form>

      <el-empty v-if="!canRead" description="无日薪查看权限" />
      <template v-else>
        <el-alert
          style="margin-bottom: 12px"
          type="success"
          :closable="false"
          show-icon
          :title="`当前查询工资合计：${totalAmount}`"
        />

        <el-table :data="rows" v-loading="loading" border>
          <el-table-column prop="employee" label="员工" min-width="120" />
          <el-table-column prop="work_date" label="日期" min-width="120" />
          <el-table-column prop="process_name" label="工序" min-width="120" />
          <el-table-column prop="item_code" label="款式" min-width="120" />
          <el-table-column prop="register_qty" label="登记数量" min-width="110" />
          <el-table-column prop="reversal_qty" label="撤销数量" min-width="110" />
          <el-table-column prop="net_qty" label="净数量" min-width="110" />
          <el-table-column prop="wage_amount" label="工资金额" min-width="120" />
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
import { fetchWorkshopDailyWages, type WorkshopDailyWageRow } from '@/api/workshop'
import { usePermissionStore } from '@/stores/permission'

const router = useRouter()
const permissionStore = usePermissionStore()
const loading = ref<boolean>(false)
const rows = ref<WorkshopDailyWageRow[]>([])
const total = ref<number>(0)
const totalAmount = ref<string | number>('0')

const query = reactive({
  employee: '',
  from_date: '',
  to_date: '',
  process_name: '',
  item_code: '',
  page: 1,
  page_size: 20,
})

const canRead = computed<boolean>(() => permissionStore.state.buttonPermissions.wage_read)

const loadRows = async (): Promise<void> => {
  if (!canRead.value) {
    rows.value = []
    total.value = 0
    totalAmount.value = '0'
    return
  }
  loading.value = true
  try {
    const result = await fetchWorkshopDailyWages(query)
    rows.value = result.data.items
    total.value = result.data.total
    totalAmount.value = result.data.total_amount
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    loading.value = false
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
.workshop-daily-wage {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.pager {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}
</style>
