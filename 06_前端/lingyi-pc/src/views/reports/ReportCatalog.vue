<template>
  <div class="report-catalog-page">
    <el-card shadow="never">
      <template #header>
        <div class="header-row">
          <span>报表中心目录（只读）</span>
          <div class="header-actions">
            <el-button type="primary" :loading="loading" @click="loadCatalog">查询</el-button>
            <el-button
              type="success"
              plain
              :disabled="!canExport"
              @click="exportCatalogCsv"
            >
              导出目录 CSV
            </el-button>
          </div>
        </div>
      </template>

      <el-form :inline="true" :model="query" class="query-form">
        <el-form-item label="公司">
          <el-input v-model="query.company" clearable placeholder="company（可选）" />
        </el-form-item>
        <el-form-item label="来源模块">
          <el-select v-model="query.source_module" clearable placeholder="全部" style="width: 180px">
            <el-option v-for="item in sourceModuleOptions" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item label="报表类型">
          <el-select v-model="query.report_type" clearable placeholder="全部" style="width: 180px">
            <el-option label="readonly" value="readonly" />
            <el-option label="readonly_snapshot" value="readonly_snapshot" />
          </el-select>
        </el-form-item>
      </el-form>

      <el-alert
        v-if="!canRead"
        type="warning"
        :closable="false"
        title="当前账号无 report:read 权限"
        style="margin-bottom: 12px"
      />
      <el-alert
        v-if="!canExport"
        type="warning"
        :closable="false"
        title="当前账号无 report:export 权限"
        style="margin-bottom: 12px"
      />

      <el-table v-if="items.length > 0" :data="items" border @row-click="onRowClick">
        <el-table-column prop="report_key" label="report_key" min-width="180" />
        <el-table-column prop="name" label="报表名称" min-width="180" />
        <el-table-column label="来源模块" min-width="180">
          <template #default="scope">
            <el-tag
              v-for="module in scope.row.source_modules"
              :key="module"
              type="info"
              effect="plain"
              style="margin-right: 6px"
            >
              {{ module }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="report_type" label="类型" width="150" />
        <el-table-column prop="status" label="状态" width="120" />
      </el-table>

      <el-empty v-else description="暂无目录数据" />

      <el-card v-if="selectedItem" shadow="never" class="detail-card">
        <template #header>
          <div class="header-row">
            <span>报表详情：{{ selectedItem.name }}</span>
            <span>{{ selectedItem.report_key }}</span>
          </div>
        </template>
        <el-descriptions :column="2" border>
          <el-descriptions-item label="来源模块">{{ selectedItem.source_modules.join(', ') }}</el-descriptions-item>
          <el-descriptions-item label="类型">{{ selectedItem.report_type }}</el-descriptions-item>
          <el-descriptions-item label="必填过滤">{{ selectedItem.required_filters.join(', ') || '-' }}</el-descriptions-item>
          <el-descriptions-item label="可选过滤">{{ selectedItem.optional_filters.join(', ') || '-' }}</el-descriptions-item>
          <el-descriptions-item label="指标摘要" :span="2">{{ selectedItem.metric_summary.join(', ') || '-' }}</el-descriptions-item>
        </el-descriptions>
      </el-card>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import reportApi from '@/api/report'
import { usePermissionStore } from '@/stores/permission'

interface ReportCatalogItem {
  report_key: string
  name: string
  source_modules: string[]
  report_type: string
  required_filters: string[]
  optional_filters: string[]
  metric_summary: string[]
  permission_action: string
  status: string
}

const permissionStore = usePermissionStore()
const loading = ref<boolean>(false)
const items = ref<ReportCatalogItem[]>([])
const selectedItem = ref<ReportCatalogItem | null>(null)

const query = reactive({
  company: '',
  source_module: '',
  report_type: '',
})

const sourceModuleOptions = [
  'production',
  'workshop',
  'warehouse',
  'inventory',
  'style_profit',
  'factory_statement',
  'sales_inventory',
  'quality',
  'finance',
]

const canRead = computed<boolean>(() => permissionStore.state.actions.includes('report:read'))
const canExport = computed<boolean>(() => permissionStore.state.actions.includes('report:export'))

const loadCatalog = (): Promise<void> => {
  loading.value = true
  selectedItem.value = null
  return reportApi
    .fetchReportCatalog({
      company: query.company.trim() || undefined,
      source_module: query.source_module || undefined,
      report_type: query.report_type || undefined,
    })
    .then((result) => {
      items.value = result.data.items
    })
    .catch((error: unknown) => {
      items.value = []
      ElMessage.error((error as Error).message)
    })
    .finally(() => {
      loading.value = false
    })
}

const onRowClick = (row: ReportCatalogItem): Promise<void> => {
  return reportApi
    .fetchReportCatalogDetail(row.report_key, query.company.trim() || undefined)
    .then((result) => {
      selectedItem.value = result.data.item
    })
    .catch((error: unknown) => {
      ElMessage.error((error as Error).message)
    })
}

const exportCatalogCsv = async (): Promise<void> => {
  if (!canExport.value) {
    ElMessage.warning('当前账号无 report:export 权限')
    return
  }
  try {
    await reportApi.exportReportCatalogCsv({
      company: query.company.trim() || undefined,
      source_module: query.source_module || undefined,
      report_type: query.report_type || undefined,
    })
  } catch (error: unknown) {
    ElMessage.error((error as Error).message || '导出失败')
  }
}

onMounted(() => {
  permissionStore
    .loadCurrentUser()
    .then(() => permissionStore.loadModuleActions('report'))
    .then(() => loadCatalog())
    .catch((error: unknown) => {
      ElMessage.error((error as Error).message)
    })
})
</script>

<style scoped>
.report-catalog-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.query-form {
  margin-bottom: 12px;
}

.detail-card {
  margin-top: 12px;
}
</style>
