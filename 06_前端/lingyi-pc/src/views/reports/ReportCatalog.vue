<template>
  <div class="report-catalog-page">
    <el-card shadow="never">
      <template #header>
        <div class="header-row">
          <span>报表中心 / 资金计划报表（TASK-Y3B-08）</span>
          <div class="header-actions">
            <el-button type="primary" :loading="loading" @click="loadCatalog">查询</el-button>
            <el-button
              type="success"
              plain
              :disabled="!canExport || loading || items.length === 0"
              @click="handleExport"
            >
              导出（只读）
            </el-button>
          </div>
        </div>
      </template>

      <el-form :inline="true" :model="query" class="query-form">
        <el-form-item label="公司">
          <el-input v-model="query.company" clearable placeholder="请输入" />
        </el-form-item>
        <el-form-item label="客户">
          <el-input v-model="query.customer_keyword" clearable placeholder="请输入" />
        </el-form-item>
        <el-form-item label="来源模块">
          <el-select v-model="query.source_module" clearable placeholder="全部" style="width: 180px">
            <el-option v-for="item in sourceModuleOptions" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item label="报表类型">
          <el-select v-model="query.report_type" clearable placeholder="全部" style="width: 180px">
            <el-option v-for="item in reportTypeOptions" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item label="开始时间">
          <el-input v-model="query.from_date" clearable placeholder="开始时间" />
        </el-form-item>
        <el-form-item label="结束时间">
          <el-input v-model="query.to_date" clearable placeholder="结束时间" />
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
        title="当前账号无 report:export 权限，导出按钮保持禁用。"
        style="margin-bottom: 12px"
      />
      <el-alert
        type="info"
        :closable="false"
        title="共享路由边界：本任务仅补齐资金计划报表语义，并保留 TASK-Y3B-07 加工成品库存条目。"
        style="margin-bottom: 12px"
      />
      <el-alert
        v-if="scopeExpandedToOtherReports"
        type="warning"
        :closable="false"
        title="检测到同路由下存在其他报表项，本页已按任务边界仅处理资金计划报表。"
        style="margin-bottom: 12px"
      />
      <el-alert
        v-if="!taskY3B07EntryPreserved"
        type="error"
        :closable="false"
        :title="preserveCheckMessage || '加工成品库存条目校验失败。'"
        style="margin-bottom: 12px"
      />
      <el-alert v-if="errorMessage" type="error" :closable="false" :title="errorMessage" style="margin-bottom: 12px" />

      <el-table
        v-if="items.length > 0"
        :data="items"
        border
        empty-text="暂无资金计划报表目录数据"
        @row-click="onRowClick"
      >
        <el-table-column prop="report_key" label="report_key" min-width="220" />
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

      <el-empty v-else description="暂无资金计划报表目录数据" />

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
          <el-descriptions-item label="状态标签" :span="2">
            <el-tag
              v-for="tag in selectedItem.status_tags || []"
              :key="tag"
              effect="plain"
              style="margin-right: 6px"
            >
              {{ tag }}
            </el-tag>
            <span v-if="!(selectedItem.status_tags || []).length">-</span>
          </el-descriptions-item>
          <el-descriptions-item label="占位词映射" :span="2">
            <el-tag
              v-for="placeholder in selectedItem.ui_placeholders || []"
              :key="placeholder"
              effect="plain"
              style="margin-right: 6px"
            >
              {{ placeholder }}
            </el-tag>
            <span v-if="!(selectedItem.ui_placeholders || []).length">-</span>
          </el-descriptions-item>
          <el-descriptions-item label="按钮映射" :span="2">
            <el-tag
              v-for="buttonText in selectedItem.ui_buttons || []"
              :key="buttonText"
              effect="plain"
              style="margin-right: 6px; margin-bottom: 6px"
            >
              {{ buttonText }}
            </el-tag>
            <span v-if="!(selectedItem.ui_buttons || []).length">-</span>
          </el-descriptions-item>
        </el-descriptions>

        <el-table
          v-if="previewRows.length > 0 && previewHeaders.length > 0"
          :data="previewRows"
          border
          class="preview-table"
          empty-text="暂无资金计划报表预览数据"
        >
          <el-table-column
            v-for="header in previewHeaders"
            :key="header"
            :prop="header"
            :label="header"
            min-width="120"
          />
        </el-table>
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
  ui_placeholders?: string[]
  ui_buttons?: string[]
  ui_table_headers?: string[]
  status_tags?: string[]
  preview_rows?: Array<Record<string, string>>
}

const TASK_SCOPE_REPORT_KEY = 'finance_plan_report'
const PRESERVED_REPORT_KEY = 'factory_product_stock_report'
const TASK_SCOPE_REPORT_KEYS = new Set([TASK_SCOPE_REPORT_KEY, PRESERVED_REPORT_KEY])

const permissionStore = usePermissionStore()
const loading = ref<boolean>(false)
const items = ref<ReportCatalogItem[]>([])
const selectedItem = ref<ReportCatalogItem | null>(null)
const errorMessage = ref<string>('')
const scopeExpandedToOtherReports = ref<boolean>(false)
const taskY3B07EntryPreserved = ref<boolean>(true)
const preserveCheckMessage = ref<string>('')

const query = reactive({
  company: '',
  customer_keyword: '',
  source_module: 'finance',
  report_type: 'financial',
  from_date: '',
  to_date: '',
})

const sourceModuleOptions = ['finance']
const reportTypeOptions = ['financial']

const canRead = computed<boolean>(() => permissionStore.state.actions.includes('report:read'))
const canExport = computed<boolean>(() => permissionStore.state.actions.includes('report:export'))
const previewHeaders = computed<string[]>(() => selectedItem.value?.ui_table_headers || [])

const previewRows = computed<Array<Record<string, string>>>(() => {
  const rows = selectedItem.value?.preview_rows || []
  return rows.filter((row) => {
    const customerKeyword = query.customer_keyword.trim()
    if (customerKeyword && !(`${row['客户'] || ''}${row['标题'] || ''}`.includes(customerKeyword))) {
      return false
    }
    const fromDate = query.from_date.trim()
    if (fromDate && (row['发送时间'] || '').slice(0, 10) < fromDate) {
      return false
    }
    const toDate = query.to_date.trim()
    if (toDate && (row['发送时间'] || '').slice(0, 10) > toDate) {
      return false
    }
    return true
  })
})

const checkTaskY3B07Entry = (): Promise<void> => {
  return reportApi
    .fetchReportCatalogDetail(PRESERVED_REPORT_KEY, query.company.trim() || undefined)
    .then(() => {
      taskY3B07EntryPreserved.value = true
      preserveCheckMessage.value = ''
    })
    .catch((error: unknown) => {
      taskY3B07EntryPreserved.value = false
      preserveCheckMessage.value = `TASK-Y3B-07 条目校验失败：${(error as Error).message || 'unknown'}`
    })
}

const loadCatalog = (): Promise<void> => {
  loading.value = true
  selectedItem.value = null
  errorMessage.value = ''
  scopeExpandedToOtherReports.value = false
  return reportApi
    .fetchReportCatalog({
      company: query.company.trim() || undefined,
      source_module: query.source_module || undefined,
      report_type: query.report_type || undefined,
    })
    .then((result) => {
      const apiItems = result.data.items
      scopeExpandedToOtherReports.value = apiItems.some((item) => !TASK_SCOPE_REPORT_KEYS.has(item.report_key))
      items.value = apiItems.filter((item) => item.report_key === TASK_SCOPE_REPORT_KEY)
      if (items.value.length === 0) {
        errorMessage.value = '未命中资金计划报表目录条目，请检查筛选条件。'
      }
      return checkTaskY3B07Entry()
    })
    .catch((error: unknown) => {
      items.value = []
      const message = (error as Error).message || '目录加载失败'
      errorMessage.value = `目录加载失败：${message}`
      ElMessage.error(message)
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
      const message = (error as Error).message || '详情加载失败'
      errorMessage.value = `详情加载失败：${message}`
      ElMessage.error(message)
    })
}

const handleExport = (): Promise<void> => {
  if (!canExport.value) {
    ElMessage.warning('当前账号无 report:export 权限')
    return Promise.resolve()
  }
  if (!items.value.length) {
    ElMessage.info('无可导出的资金计划报表目录数据')
    return Promise.resolve()
  }
  return reportApi
    .exportReportCatalogCsv({
      company: query.company.trim() || undefined,
      source_module: query.source_module || undefined,
      report_type: query.report_type || undefined,
    })
    .then(() => {
      ElMessage.success('已触发本地只读导出')
    })
    .catch((error: unknown) => {
      const message = (error as Error).message || '导出失败'
      errorMessage.value = `导出失败：${message}`
      ElMessage.error(message)
    })
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

.preview-table {
  margin-top: 12px;
}
</style>
