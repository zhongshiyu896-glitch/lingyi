<template>
  <div class="permission-governance-page">
    <el-card shadow="never">
      <template #header>
        <div class="header-row">
          <span>权限治理动作目录（只读）</span>
          <el-button type="primary" :loading="loading" @click="loadData">刷新</el-button>
        </div>
      </template>

      <el-alert
        v-if="!canRead"
        type="warning"
        :closable="false"
        title="当前账号无 permission:read 权限"
        style="margin-bottom: 12px"
      />

      <template v-else>
        <el-table :data="catalogRows" border>
          <el-table-column prop="module" label="模块" width="160" />
          <el-table-column prop="action" label="动作" min-width="220" />
          <el-table-column prop="category" label="分类" width="160" />
          <el-table-column label="风险标记" width="190">
            <template #default="scope">
              <el-tag v-if="scope.row.is_high_risk || !scope.row.ui_exposed" type="danger" effect="plain">
                高危/非普通前端动作
              </el-tag>
              <el-tag v-else type="success" effect="plain">普通只读动作</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="description" label="说明" min-width="280" />
        </el-table>

        <el-divider />

        <el-table :data="roleRows" border>
          <el-table-column prop="role" label="角色" min-width="180" />
          <el-table-column label="模块" min-width="220">
            <template #default="scope">
              <el-tag
                v-for="module in scope.row.modules"
                :key="`${scope.row.role}-${module}`"
                type="info"
                effect="plain"
                style="margin-right: 6px"
              >
                {{ module }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="动作数" width="100">
            <template #default="scope">{{ scope.row.actions.length }}</template>
          </el-table-column>
          <el-table-column label="高危动作数" width="120">
            <template #default="scope">{{ scope.row.high_risk_actions.length }}</template>
          </el-table-column>
          <el-table-column label="隐藏动作数" width="120">
            <template #default="scope">{{ scope.row.ui_hidden_actions.length }}</template>
          </el-table-column>
        </el-table>
      </template>
    </el-card>

    <el-card shadow="never">
      <template #header>
        <div class="header-row">
          <span>审计查询（只读）</span>
          <div class="header-actions">
            <el-button type="primary" :loading="auditLoading" @click="loadAuditData">查询</el-button>
            <el-button
              type="success"
              plain
              :loading="securityExporting"
              :disabled="!canExport"
              @click="exportSecurityAuditCsv"
            >
              导出安全审计 CSV
            </el-button>
            <el-button
              type="success"
              plain
              :loading="operationExporting"
              :disabled="!canExport"
              @click="exportOperationAuditCsv"
            >
              导出操作审计 CSV
            </el-button>
          </div>
        </div>
      </template>

      <el-alert
        v-if="!canAuditRead"
        type="warning"
        :closable="false"
        title="当前账号无 permission:audit_read 权限，无法查看审计查询"
      />
      <el-alert
        v-if="!canExport"
        type="warning"
        :closable="false"
        title="当前账号无 permission:export 权限，无法导出审计CSV"
        style="margin-top: 8px; margin-bottom: 8px"
      />

      <template v-else>
        <el-form :inline="true" :model="securityQuery" class="query-form">
          <el-form-item label="开始日期">
            <el-input v-model="securityQuery.from_date" clearable placeholder="YYYY-MM-DD" />
          </el-form-item>
          <el-form-item label="结束日期">
            <el-input v-model="securityQuery.to_date" clearable placeholder="YYYY-MM-DD" />
          </el-form-item>
          <el-form-item label="模块">
            <el-input v-model="securityQuery.module" clearable placeholder="module" />
          </el-form-item>
          <el-form-item label="事件类型">
            <el-input v-model="securityQuery.event_type" clearable placeholder="event_type" />
          </el-form-item>
        </el-form>

        <el-table :data="securityAudit.items" border>
          <el-table-column prop="id" label="ID" width="90" />
          <el-table-column prop="created_at" label="时间" min-width="180" />
          <el-table-column prop="event_type" label="事件" min-width="150" />
          <el-table-column prop="module" label="模块" width="120" />
          <el-table-column prop="action" label="动作" min-width="180" />
          <el-table-column prop="user_id" label="用户" min-width="140" />
          <el-table-column prop="request_id" label="请求ID" min-width="160" />
          <el-table-column label="拒绝原因" min-width="220">
            <template #default="scope">
              <span :title="scope.row.deny_reason || ''">{{ formatDenyReason(scope.row.deny_reason) }}</span>
            </template>
          </el-table-column>
        </el-table>

        <el-divider />

        <el-form :inline="true" :model="operationQuery" class="query-form">
          <el-form-item label="开始日期">
            <el-input v-model="operationQuery.from_date" clearable placeholder="YYYY-MM-DD" />
          </el-form-item>
          <el-form-item label="结束日期">
            <el-input v-model="operationQuery.to_date" clearable placeholder="YYYY-MM-DD" />
          </el-form-item>
          <el-form-item label="模块">
            <el-input v-model="operationQuery.module" clearable placeholder="module" />
          </el-form-item>
          <el-form-item label="执行人">
            <el-input v-model="operationQuery.operator" clearable placeholder="operator" />
          </el-form-item>
          <el-form-item label="结果">
            <el-select v-model="operationQuery.result" clearable placeholder="全部" style="width: 140px">
              <el-option label="success" value="success" />
              <el-option label="failed" value="failed" />
            </el-select>
          </el-form-item>
        </el-form>

        <el-table :data="operationAudit.items" border>
          <el-table-column prop="id" label="ID" width="90" />
          <el-table-column prop="created_at" label="时间" min-width="180" />
          <el-table-column prop="module" label="模块" width="120" />
          <el-table-column prop="action" label="动作" min-width="180" />
          <el-table-column prop="operator" label="执行人" min-width="140" />
          <el-table-column prop="result" label="结果" width="100" />
          <el-table-column label="错误码" min-width="130">
            <template #default="scope">
              <span :title="scope.row.error_code || ''">{{ formatErrorCode(scope.row.error_code) }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="request_id" label="请求ID" min-width="160" />
          <el-table-column label="变更摘要" min-width="190">
            <template #default="scope">
              <span>
                before={{ scope.row.before_keys.join(',') || '-' }} / after={{ scope.row.after_keys.join(',') || '-' }}
              </span>
            </template>
          </el-table-column>
        </el-table>
      </template>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import permissionGovernanceApi, {
  type PermissionActionCatalogModule,
  type PermissionOperationAuditData,
  type PermissionOperationAuditQuery,
  type PermissionRoleMatrixEntry,
  type PermissionSecurityAuditData,
  type PermissionSecurityAuditQuery,
} from '@/api/permission_governance'
import { usePermissionStore } from '@/stores/permission'

interface CatalogRow {
  module: string
  action: string
  category: string
  is_high_risk: boolean
  ui_exposed: boolean
  description: string
}

const permissionStore = usePermissionStore()
const loading = ref<boolean>(false)
const auditLoading = ref<boolean>(false)
const securityExporting = ref<boolean>(false)
const operationExporting = ref<boolean>(false)
const catalogRows = ref<CatalogRow[]>([])
const roleRows = ref<PermissionRoleMatrixEntry[]>([])

const securityAudit = ref<PermissionSecurityAuditData>({
  items: [],
  total: 0,
  page: 1,
  page_size: 20,
})

const operationAudit = ref<PermissionOperationAuditData>({
  items: [],
  total: 0,
  page: 1,
  page_size: 20,
})

const securityQuery = reactive<PermissionSecurityAuditQuery>({
  from_date: '',
  to_date: '',
  module: '',
  action: '',
  request_id: '',
  resource_type: '',
  resource_id: '',
  event_type: '',
  user_id: '',
  page: 1,
  page_size: 20,
})

const operationQuery = reactive<PermissionOperationAuditQuery>({
  from_date: '',
  to_date: '',
  module: '',
  action: '',
  request_id: '',
  resource_type: '',
  operator: '',
  error_code: '',
  page: 1,
  page_size: 20,
})

const canRead = computed<boolean>(() => permissionStore.state.actions.includes('permission:read'))
const canAuditRead = computed<boolean>(() => permissionStore.state.actions.includes('permission:audit_read'))
const canExport = computed<boolean>(() => permissionStore.state.actions.includes('permission:export'))

const normalizeAuditText = (value?: string | null): string => {
  const raw = String(value ?? '').trim()
  if (!raw) return '-'
  if (/internal\s+error\s*,?\s*detail\s+redacted/i.test(raw)) {
    return '内部异常（细节已脱敏）'
  }
  if (/detail\s+redacted/i.test(raw)) {
    return '细节已脱敏'
  }
  return raw.replace(/error/gi, '异常')
}

const formatDenyReason = (value?: string | null): string => {
  return normalizeAuditText(value)
}

const formatErrorCode = (value?: string | null): string => {
  const raw = String(value ?? '').trim()
  if (!raw) return '-'
  if (/internal[\s_-]*error/i.test(raw) && /redacted/i.test(raw)) {
    return 'INTERNAL_REDACTED'
  }
  return raw.replace(/error/gi, 'ERR')
}

const flattenCatalog = (modules: PermissionActionCatalogModule[]): CatalogRow[] => {
  return modules.flatMap((module) => {
    return module.actions.map((action) => ({
      module: module.module,
      action: action.action,
      category: action.category,
      is_high_risk: action.is_high_risk,
      ui_exposed: action.ui_exposed,
      description: action.description,
    }))
  })
}

const loadData = async (): Promise<void> => {
  loading.value = true
  try {
    if (!canRead.value) {
      catalogRows.value = []
      roleRows.value = []
      return
    }
    const [catalogResp, matrixResp] = await Promise.all([
      permissionGovernanceApi.fetchPermissionActionCatalog(),
      permissionGovernanceApi.fetchPermissionRolesMatrix(),
    ])
    catalogRows.value = flattenCatalog(catalogResp.data.modules)
    roleRows.value = matrixResp.data.roles
  } catch (error: unknown) {
    catalogRows.value = []
    roleRows.value = []
    ElMessage.error((error as Error).message)
  } finally {
    loading.value = false
  }
}

const loadAuditData = async (): Promise<void> => {
  auditLoading.value = true
  try {
    if (!canAuditRead.value) {
      securityAudit.value = { items: [], total: 0, page: 1, page_size: 20 }
      operationAudit.value = { items: [], total: 0, page: 1, page_size: 20 }
      return
    }

    const [securityResp, operationResp] = await Promise.all([
      permissionGovernanceApi.fetchPermissionSecurityAudit(securityQuery),
      permissionGovernanceApi.fetchPermissionOperationAudit(operationQuery),
    ])
    securityAudit.value = securityResp.data
    operationAudit.value = operationResp.data
  } catch (error: unknown) {
    securityAudit.value = { items: [], total: 0, page: 1, page_size: 20 }
    operationAudit.value = { items: [], total: 0, page: 1, page_size: 20 }
    ElMessage.error((error as Error).message)
  } finally {
    auditLoading.value = false
  }
}

const exportSecurityAuditCsv = async (): Promise<void> => {
  if (!canExport.value) {
    ElMessage.warning('当前账号无 permission:export 权限')
    return
  }
  securityExporting.value = true
  try {
    await permissionGovernanceApi.exportPermissionSecurityAuditCsv({
      from_date: securityQuery.from_date,
      to_date: securityQuery.to_date,
      module: securityQuery.module,
      action: securityQuery.action,
      request_id: securityQuery.request_id,
      resource_type: securityQuery.resource_type,
      resource_id: securityQuery.resource_id,
      event_type: securityQuery.event_type,
      user_id: securityQuery.user_id,
      limit: 1000,
    })
  } catch (error: unknown) {
    ElMessage.error((error as Error).message || '导出失败')
  } finally {
    securityExporting.value = false
  }
}

const exportOperationAuditCsv = async (): Promise<void> => {
  if (!canExport.value) {
    ElMessage.warning('当前账号无 permission:export 权限')
    return
  }
  operationExporting.value = true
  try {
    await permissionGovernanceApi.exportPermissionOperationAuditCsv({
      from_date: operationQuery.from_date,
      to_date: operationQuery.to_date,
      module: operationQuery.module,
      action: operationQuery.action,
      request_id: operationQuery.request_id,
      resource_type: operationQuery.resource_type,
      resource_id: operationQuery.resource_id,
      operator: operationQuery.operator,
      result: operationQuery.result,
      error_code: operationQuery.error_code,
      limit: 1000,
    })
  } catch (error: unknown) {
    ElMessage.error((error as Error).message || '导出失败')
  } finally {
    operationExporting.value = false
  }
}

onMounted(() => {
  permissionStore
    .loadCurrentUser()
    .then(() => permissionStore.loadModuleActions('permission'))
    .then(async () => {
      await loadData()
      await loadAuditData()
    })
    .catch((error: unknown) => {
      ElMessage.error((error as Error).message)
    })
})
</script>

<style scoped>
.permission-governance-page {
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
</style>
