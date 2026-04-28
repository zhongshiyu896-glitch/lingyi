<template>
  <div class="dashboard-overview-page">
    <el-card shadow="never">
      <template #header>
        <div class="header-row">
          <span>报表与仪表盘总览（只读）</span>
          <el-button type="primary" :loading="loading" @click="loadOverview">查询</el-button>
        </div>
      </template>

      <el-form :inline="true" :model="query">
        <el-form-item label="公司">
          <el-input v-model="query.company" clearable placeholder="company（必填）" />
        </el-form-item>
        <el-form-item label="物料">
          <el-input v-model="query.item_code" clearable placeholder="item_code" />
        </el-form-item>
        <el-form-item label="仓库">
          <el-input v-model="query.warehouse" clearable placeholder="warehouse" />
        </el-form-item>
        <el-form-item label="开始日期">
          <el-date-picker
            v-model="query.from_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="from_date（可选）"
            clearable
          />
        </el-form-item>
        <el-form-item label="结束日期">
          <el-date-picker
            v-model="query.to_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="to_date（可选）"
            clearable
          />
        </el-form-item>
      </el-form>

      <el-alert
        v-if="!canRead"
        type="warning"
        :closable="false"
        title="当前账号无 dashboard:read 权限"
        style="margin-bottom: 12px"
      />

      <template v-if="overview">
        <el-row :gutter="12" class="summary-row">
          <el-col :span="8">
            <el-card shadow="never">
              <template #header>质量摘要</template>
              <p>检验单数：{{ overview.quality.inspection_count }}</p>
              <p>合格数量：{{ formatAmount(overview.quality.accepted_qty) }}</p>
              <p>不合格数量：{{ formatAmount(overview.quality.rejected_qty) }}</p>
              <p>缺陷数量：{{ overview.quality.defect_count }}</p>
              <p>通过率：{{ formatPercent(overview.quality.pass_rate) }}</p>
            </el-card>
          </el-col>
          <el-col :span="8">
            <el-card shadow="never">
              <template #header>销售库存摘要</template>
              <p>物料行数：{{ overview.sales_inventory.item_count }}</p>
              <p>实际库存总量：{{ formatAmount(overview.sales_inventory.total_actual_qty) }}</p>
              <p>低于安全库存：{{ overview.sales_inventory.below_safety_count }}</p>
              <p>低于补货阈值：{{ overview.sales_inventory.below_reorder_count }}</p>
            </el-card>
          </el-col>
          <el-col :span="8">
            <el-card shadow="never">
              <template #header>仓库预警摘要</template>
              <p>预警总数：{{ overview.warehouse.alert_count }}</p>
              <p>严重预警：{{ overview.warehouse.critical_alert_count }}</p>
              <p>一般预警：{{ overview.warehouse.warning_alert_count }}</p>
            </el-card>
          </el-col>
        </el-row>

        <el-card shadow="never">
          <template #header>
            <div class="header-row">
              <span>来源状态</span>
              <span>生成时间：{{ overview.generated_at }}</span>
            </div>
          </template>
          <el-table :data="overview.source_status" border empty-text="暂无来源状态数据">
            <el-table-column prop="module" label="模块" min-width="180" />
            <el-table-column prop="status" label="状态" width="120" />
          </el-table>
        </el-card>
      </template>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { fetchDashboardOverview, type DashboardOverviewData } from '@/api/dashboard'
import { usePermissionStore } from '@/stores/permission'

const permissionStore = usePermissionStore()
const loading = ref<boolean>(false)
const overview = ref<DashboardOverviewData | null>(null)

const query = reactive({
  company: '',
  item_code: '',
  warehouse: '',
  from_date: '',
  to_date: '',
})

const canRead = computed<boolean>(() => permissionStore.state.actions.includes('dashboard:read'))

const formatAmount = (value: string | number | null | undefined): string => {
  if (value === null || value === undefined || value === '') {
    return '-'
  }
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric.toFixed(2) : String(value)
}

const formatPercent = (value: string | number | null | undefined): string => {
  if (value === null || value === undefined || value === '') {
    return '-'
  }
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) {
    return String(value)
  }
  return `${(numeric * 100).toFixed(2)}%`
}

const loadOverview = async (): Promise<void> => {
  const company = query.company.trim()
  if (!company) {
    ElMessage.warning('company 不能为空')
    return
  }
  loading.value = true
  try {
    const result = await fetchDashboardOverview({
      company,
      item_code: query.item_code.trim() || undefined,
      warehouse: query.warehouse.trim() || undefined,
      from_date: query.from_date || undefined,
      to_date: query.to_date || undefined,
    })
    overview.value = result.data
  } catch (error) {
    overview.value = null
    ElMessage.error((error as Error).message)
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  try {
    await permissionStore.loadCurrentUser()
    await permissionStore.loadModuleActions('dashboard')
  } catch (error) {
    ElMessage.error((error as Error).message)
  }
})
</script>

<style scoped>
.dashboard-overview-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.summary-row {
  margin-bottom: 12px;
}

.summary-row p {
  margin: 8px 0;
}
</style>
