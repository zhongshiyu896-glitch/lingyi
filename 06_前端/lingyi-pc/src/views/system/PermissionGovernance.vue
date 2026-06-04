<template>
  <div class="permission-governance-page" data-testid="permission-governance-page">
    <el-alert
      type="info"
      :closable="false"
      title="权限治理只读交互 /permissions/governance"
      description="仅允许 GET 查询动作目录、角色矩阵、菜单管理与审计记录；菜单写动作和审计导出均为本地 guarded_readonly。"
      data-testid="permission-governance-parity-hint"
      class="readonly-parity-hint"
    />
    <PermissionGovernanceGuardPanel
      data-testid="permission-governance-readonly-status"
      :can-read="canRead"
      :can-audit-read="canAuditRead"
      :can-diagnostic="canDiagnostic"
      :can-export="canExport"
      :guarded-buttons="menuGuardedButtons"
      :route-label="currentRouteLabel"
      mode-label="READONLY_GET_ONLY"
    />

    <el-card shadow="never" data-testid="action-catalog-section">
      <template #header>
        <div class="header-row">
          <span>权限治理动作目录（只读）</span>
          <el-button type="primary" :loading="loading" data-testid="action-catalog-refresh-button" @click="loadData">
            刷新
          </el-button>
        </div>
      </template>

      <el-alert
        v-if="!canRead"
        type="warning"
        :closable="false"
        title="当前账号无 permission:read 权限"
        data-testid="permission-governance-read-permission-state"
        style="margin-bottom: 12px"
      />
      <el-alert
        v-if="catalogErrorMessage"
        type="error"
        :closable="false"
        :title="catalogErrorMessage"
        data-testid="action-catalog-error-state"
        style="margin-bottom: 12px"
      />

      <template>
        <el-table :data="catalogRows" border empty-text="暂无动作目录数据" data-testid="action-catalog-table">
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

        <el-table :data="roleRows" border empty-text="暂无角色矩阵数据" data-testid="roles-matrix-table">
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

    <el-card shadow="never" data-testid="menu-management-section">
      <template #header>
        <div class="header-row">
          <span>菜单管理（TASK-Y79B-P1-01，只读）</span>
          <el-button type="primary" :loading="menuLoading" data-testid="menu-management-refresh-button" @click="loadMenuManagement">
            刷新
          </el-button>
        </div>
      </template>

      <el-alert
        v-if="!canRead"
        type="warning"
        :closable="false"
        title="当前账号无 permission:read 权限（菜单管理只读区块不可见）"
        data-testid="menu-management-permission-state"
      />
      <el-alert
        v-if="menuErrorMessage"
        type="error"
        :closable="false"
        :title="menuErrorMessage"
        data-testid="menu-management-error-state"
        style="margin-bottom: 12px"
      />

      <template>
        <el-form :inline="true" :model="menuManagementQuery" class="query-form" data-testid="menu-management-query-form">
          <el-form-item label="模块">
            <el-select v-model="menuManagementQuery.module" clearable placeholder="全部" style="width: 180px">
              <el-option
                v-for="option in menuManagementModuleOptions"
                :key="option"
                :label="option"
                :value="option"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="状态">
            <el-select v-model="menuManagementQuery.status" clearable placeholder="全部" style="width: 180px">
              <el-option label="enabled" value="enabled" />
              <el-option label="planned" value="planned" />
              <el-option label="disabled" value="disabled" />
            </el-select>
          </el-form-item>
          <el-form-item label="关键词">
            <el-input v-model="menuManagementQuery.keyword" clearable placeholder="菜单编码/菜单名称/路由" style="width: 260px" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="menuLoading" data-testid="menu-management-query-button" @click="loadMenuManagement">
              查询
            </el-button>
            <el-button data-testid="menu-management-reset-button" @click="resetMenuManagementQuery">重置</el-button>
          </el-form-item>
        </el-form>

        <div
          class="guarded-summary"
          data-testid="permission-governance-write-guard"
          data-write-guard="permission-governance-menu-and-audit"
          data-guard-state="guarded_readonly"
        >
          <span>guarded 按钮：{{ menuGuardedButtons.join(' / ') || '-' }}</span>
          <el-tag type="warning" effect="plain">菜单新增/编辑/删除 guarded</el-tag>
          <el-tag type="info" effect="plain">审计导出 readonly intercept</el-tag>
        </div>

        <el-table
          :data="menuManagement.items"
          border
          row-key="menu_key"
          empty-text="暂无菜单管理数据"
          data-testid="menu-management-table"
        >
          <el-table-column prop="menu_name" label="菜单名称" min-width="200" />
          <el-table-column prop="module" label="模块" min-width="120" />
          <el-table-column prop="route" label="路由" min-width="200" />
          <el-table-column prop="permission_action" label="读取动作" min-width="170" />
          <el-table-column label="状态" width="110">
            <template #default="scope">
              <el-tag
                :type="
                  scope.row.status === 'enabled' ? 'success' : scope.row.status === 'planned' ? 'warning' : 'info'
                "
                effect="plain"
              >
                {{ scope.row.status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="owner_role" label="归属角色" min-width="140" />
          <el-table-column prop="description" label="说明" min-width="220" />
          <el-table-column label="操作" width="280">
            <template #default="scope">
              <el-button
                v-for="action in scope.row.actions"
                :key="`${scope.row.menu_key}-${action.action_key}`"
                size="small"
                :type="action.guarded ? 'warning' : 'primary'"
                :plain="action.guarded"
                :disabled="action.guarded"
                :title="action.guarded ? action.guard_reason || '只读区块：写动作已禁用' : '只读查看'"
                :data-write-guard="`readonly:${action.action_key}`"
                data-guard-state="guarded_readonly"
                @click="onMenuAction(scope.row.menu_name, action.action_label, action.guarded, action.guard_reason)"
              >
                {{ action.action_label }}
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-empty v-if="!menuManagement.items.length" description="暂无菜单管理数据" data-testid="menu-management-empty-state" />
      </template>
    </el-card>

    <el-card shadow="never" data-testid="permission-diagnostic-section">
      <template #header>
        <div class="header-row">
          <span>治理摘要与诊断（只读）</span>
          <el-button
            type="primary"
            :loading="diagnosticLoading"
            data-testid="permission-diagnostic-refresh-button"
            @click="loadDiagnosticData"
          >
            刷新
          </el-button>
        </div>
      </template>

      <el-alert
        v-if="!canDiagnostic"
        type="warning"
        :closable="false"
        title="当前账号无 permission:diagnostic 权限，已使用本地只读诊断摘要"
        data-testid="permission-diagnostic-permission-state"
        style="margin-bottom: 12px"
      />
      <el-alert
        v-if="diagnosticErrorMessage"
        type="error"
        :closable="false"
        :title="diagnosticErrorMessage"
        data-testid="permission-diagnostic-error-state"
        style="margin-bottom: 12px"
      />

      <PermissionGovernanceAuditSummary
        :role-count="roleRows.length"
        :high-risk-count="diagnosticData.high_risk_actions.length"
        :security-audit-total="securityAudit.total"
        :operation-audit-total="operationAudit.total"
        :health-summary-count="healthSummaryRows.length"
        :menu-drift-count="menuDriftCount"
        :blocked-check-count="blockedCheckCount"
        :diagnostic-status="diagnosticData.status"
        :catalog-enabled="diagnosticData.catalog_enabled"
        :audit-read-enabled="diagnosticData.audit_read_enabled"
        :can-export="canExport"
        :fallback-source="fallbackSource"
        :generated-at="diagnosticData.generated_at"
      />

      <el-alert
        type="info"
        :closable="false"
        :title="`system health summary fallback: ${fallbackSource}`"
        :description="blockingHints.join('；') || '当前诊断 checks 与菜单 contract 未发现额外漂移。'"
        data-testid="permission-diagnostic-health-fallback"
        style="margin-bottom: 12px"
      />

      <el-table
        :data="healthSummaryRows"
        border
        empty-text="暂无健康摘要"
        data-testid="permission-diagnostic-health-summary-table"
      >
        <el-table-column prop="label" label="健康摘要项" min-width="220" />
        <el-table-column label="状态" width="120">
          <template #default="scope">
            <el-tag
              :type="scope.row.status === 'ok' ? 'success' : scope.row.status === 'warn' ? 'warning' : 'danger'"
              effect="plain"
            >
              {{ scope.row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="checkResult" label="结果" min-width="220" />
        <el-table-column prop="source" label="来源" min-width="200" />
      </el-table>

      <el-divider />

      <el-table
        :data="menuStatusDriftRows"
        border
        empty-text="暂无菜单状态漂移"
        data-testid="permission-diagnostic-menu-drift-table"
      >
        <el-table-column prop="menuName" label="菜单" min-width="180" />
        <el-table-column prop="expectedRoute" label="期望路由" min-width="220" />
        <el-table-column prop="actualRoute" label="实际路由" min-width="220" />
        <el-table-column label="状态" width="120">
          <template #default="scope">
            <el-tag
              :type="scope.row.status === 'ok' ? 'success' : scope.row.status === 'warn' ? 'warning' : 'danger'"
              effect="plain"
            >
              {{ scope.row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="message" label="漂移说明" min-width="320" />
      </el-table>

      <el-divider />

      <el-table
        :data="diagnosticCheckRows"
        border
        empty-text="暂无诊断结果"
        data-testid="permission-diagnostic-checks-table"
      >
        <el-table-column prop="label" label="诊断项" min-width="220" />
        <el-table-column prop="group" label="分组" width="140" />
        <el-table-column label="状态" width="120">
          <template #default="scope">
            <el-tag :type="scope.row.severity" effect="plain">
              {{ scope.row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="message" label="说明" min-width="280" />
      </el-table>

      <el-alert
        type="info"
        :closable="false"
        title="remaining_gap"
        :description="remainingGap"
        data-testid="permission-governance-remaining-gap"
        style="margin-top: 12px"
      />
    </el-card>

    <el-card shadow="never" data-testid="permission-audit-section">
      <template #header>
        <div class="header-row">
          <span>审计查询（只读）</span>
          <div class="header-actions">
            <el-button type="primary" :loading="auditLoading" data-testid="permission-audit-query-button" @click="loadAuditData">
              查询
            </el-button>
            <el-button
              type="success"
              plain
              :loading="securityExporting"
              :disabled="auditLoading || !canExport"
              :title="canExport ? '只读模式：导出动作将被 guarded 拦截' : '当前账号无 permission:export 权限'"
              data-testid="permission-security-audit-export-guarded-button"
              data-write-guard="guarded:readonly-security-audit-export"
              data-guard-state="guarded_readonly"
              data-side-effect-guard="download-disabled"
              @click="exportSecurityAuditCsv"
            >
              导出安全审计 CSV
            </el-button>
            <el-button
              type="success"
              plain
              :loading="operationExporting"
              :disabled="auditLoading || !canExport"
              :title="canExport ? '只读模式：导出动作将被 guarded 拦截' : '当前账号无 permission:export 权限'"
              data-testid="permission-operation-audit-export-guarded-button"
              data-write-guard="guarded:readonly-operation-audit-export"
              data-guard-state="guarded_readonly"
              data-side-effect-guard="download-disabled"
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
        data-testid="permission-audit-read-permission-state"
      />
      <el-alert
        v-if="!canExport"
        type="warning"
        :closable="false"
        title="当前账号无 permission:export 权限，无法导出审计CSV"
        data-testid="permission-audit-export-permission-state"
        style="margin-top: 8px; margin-bottom: 8px"
      />
      <el-alert
        v-if="auditErrorMessage"
        type="error"
        :closable="false"
        :title="auditErrorMessage"
        data-testid="permission-audit-error-state"
        style="margin-top: 8px; margin-bottom: 8px"
      />
      <el-alert
        v-if="exportGuardMessage"
        type="warning"
        :closable="false"
        :title="exportGuardMessage"
        data-testid="permission-audit-export-guarded-state"
        style="margin-top: 8px; margin-bottom: 8px"
      />

      <template>
        <el-form :inline="true" :model="securityQuery" class="query-form" data-testid="permission-security-audit-query-form">
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
          <el-form-item>
            <el-button data-testid="permission-security-audit-reset-button" @click="resetSecurityQuery">重置</el-button>
          </el-form-item>
        </el-form>

        <el-table :data="securityAudit.items" border empty-text="暂无安全审计记录" data-testid="permission-security-audit-table">
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

        <el-empty
          v-if="!securityAudit.items.length"
          description="暂无安全审计记录"
          data-testid="permission-security-audit-empty-state"
          style="margin: 12px 0"
        />

        <el-divider />

        <el-form :inline="true" :model="operationQuery" class="query-form" data-testid="permission-operation-audit-query-form">
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
          <el-form-item>
            <el-button data-testid="permission-operation-audit-reset-button" @click="resetOperationQuery">重置</el-button>
          </el-form-item>
        </el-form>

        <el-table :data="operationAudit.items" border empty-text="暂无操作审计记录" data-testid="permission-operation-audit-table">
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
        <el-empty
          v-if="!operationAudit.items.length"
          description="暂无操作审计记录"
          data-testid="permission-operation-audit-empty-state"
          style="margin-top: 12px"
        />
      </template>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import permissionGovernanceApi, {
  type PermissionActionCatalogModule,
  type PermissionGovernanceDiagnosticData,
  type PermissionMenuManagementData,
  type PermissionOperationAuditData,
  type PermissionOperationAuditQuery,
  type PermissionRoleMatrixEntry,
  type PermissionSecurityAuditData,
  type PermissionSecurityAuditQuery,
} from '@/api/permission_governance'
import { usePermissionStore } from '@/stores/permission'
import PermissionGovernanceAuditSummary from '@/views/system/components/PermissionGovernanceAuditSummary.vue'
import PermissionGovernanceGuardPanel from '@/views/system/components/PermissionGovernanceGuardPanel.vue'
import { usePermissionGovernanceDiagnosticReadonly } from '@/views/system/composables/usePermissionGovernanceDiagnosticReadonly'
import {
  type PermissionGovernanceCatalogRow,
  cloneDiagnosticChecks,
  readonlyCatalogFallbackRows,
  readonlyDiagnosticFallback,
  readonlyMenuManagementFallback,
  readonlyOperationAuditFallback,
  readonlyRoleFallbackRows,
  readonlySecurityAuditFallback,
} from '@/views/system/constants/permissionGovernanceDiagnosticFields'

const permissionStore = usePermissionStore()
const route = useRoute()
const loading = ref<boolean>(false)
const auditLoading = ref<boolean>(false)
const securityExporting = ref<boolean>(false)
const operationExporting = ref<boolean>(false)
const diagnosticLoading = ref<boolean>(false)
const menuLoading = ref<boolean>(false)
const catalogErrorMessage = ref<string>('')
const menuErrorMessage = ref<string>('')
const auditErrorMessage = ref<string>('')
const diagnosticErrorMessage = ref<string>('')
const exportGuardMessage = ref<string>('')
const catalogRows = ref<PermissionGovernanceCatalogRow[]>([])
const roleRows = ref<PermissionRoleMatrixEntry[]>([])
const menuManagement = ref<PermissionMenuManagementData>({
  items: [],
  total: 0,
})

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

const diagnosticData = ref<PermissionGovernanceDiagnosticData>({
  module: 'permission',
  status: 'fallback',
  registered_actions: [],
  legacy_permission_audit_actions: [],
  high_risk_actions: [],
  ui_hidden_actions: [],
  roles_with_permission_actions_count: 0,
  checks: [],
  catalog_enabled: true,
  roles_matrix_enabled: true,
  audit_read_enabled: true,
  export_enabled: false,
  diagnostic_enabled: false,
  generated_at: '',
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

const menuManagementQuery = reactive({
  module: '',
  status: '',
  keyword: '',
})

const canRead = computed<boolean>(() => permissionStore.state.actions.includes('permission:read'))
const canAuditRead = computed<boolean>(() => permissionStore.state.actions.includes('permission:audit_read'))
const canExport = computed<boolean>(() => permissionStore.state.actions.includes('permission:export'))
const canDiagnostic = computed<boolean>(() => permissionStore.state.actions.includes('permission:diagnostic'))
const currentRouteLabel = computed<string>(() => route.fullPath || '/permissions/governance')
const menuManagementModuleOptions = computed<string[]>(() => {
  const modules = new Set<string>()
  menuManagement.value.items.forEach((item) => modules.add(item.module))
  return Array.from(modules)
})
const menuGuardedButtons = computed<string[]>(() => {
  const labels = new Set<string>()
  menuManagement.value.items.forEach((item) => {
    item.actions.forEach((action) => {
      if (action.guarded) {
        labels.add(action.action_label)
      }
    })
  })
  return Array.from(labels)
})
const readonlyDiagnostic = usePermissionGovernanceDiagnosticReadonly({
  diagnosticData,
  menuManagement,
  canRead,
  canAuditRead,
  canDiagnostic,
  canExport,
})
const {
  diagnosticCheckRows,
  menuStatusDriftRows,
  blockedCheckCount,
  menuDriftCount,
  healthSummaryRows,
  blockingHints,
  remainingGap,
  fallbackSource,
} = readonlyDiagnostic

const applyReadonlyCatalogFallback = (): void => {
  catalogRows.value = readonlyCatalogFallbackRows.map((row) => ({ ...row }))
  roleRows.value = readonlyRoleFallbackRows.map((row) => ({
    ...row,
    actions: [...row.actions],
    modules: [...row.modules],
    high_risk_actions: [...row.high_risk_actions],
    ui_hidden_actions: [...row.ui_hidden_actions],
  }))
}

const applyReadonlyMenuFallback = (): void => {
  menuManagement.value = {
    total: readonlyMenuManagementFallback.total,
    items: readonlyMenuManagementFallback.items.map((item) => ({
      ...item,
      actions: item.actions.map((action) => ({ ...action })),
    })),
  }
}

const applyReadonlyAuditFallback = (): void => {
  securityAudit.value = {
    ...readonlySecurityAuditFallback,
    items: readonlySecurityAuditFallback.items.map((item) => ({ ...item })),
  }
  operationAudit.value = {
    ...readonlyOperationAuditFallback,
    items: readonlyOperationAuditFallback.items.map((item) => ({
      ...item,
      before_keys: [...item.before_keys],
      after_keys: [...item.after_keys],
    })),
  }
}

const applyReadonlyDiagnosticFallback = (): void => {
  diagnosticData.value = {
    ...readonlyDiagnosticFallback,
    registered_actions: [...readonlyDiagnosticFallback.registered_actions],
    legacy_permission_audit_actions: [...readonlyDiagnosticFallback.legacy_permission_audit_actions],
    high_risk_actions: [...readonlyDiagnosticFallback.high_risk_actions],
    ui_hidden_actions: [...readonlyDiagnosticFallback.ui_hidden_actions],
    checks: cloneDiagnosticChecks(readonlyDiagnosticFallback.checks),
  }
}

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

const flattenCatalog = (modules: PermissionActionCatalogModule[]): PermissionGovernanceCatalogRow[] => {
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
  catalogErrorMessage.value = ''
  try {
    if (!canRead.value) {
      applyReadonlyCatalogFallback()
      return
    }
    const [catalogResp, matrixResp] = await Promise.all([
      permissionGovernanceApi.fetchPermissionActionCatalog(),
      permissionGovernanceApi.fetchPermissionRolesMatrix(),
    ])
    catalogRows.value = flattenCatalog(catalogResp.data.modules)
    roleRows.value = matrixResp.data.roles
  } catch (error: unknown) {
    applyReadonlyCatalogFallback()
    const message = (error as Error).message || '动作目录加载失败'
    catalogErrorMessage.value = message
    ElMessage.error(message)
  } finally {
    loading.value = false
  }
}

const loadMenuManagement = async (): Promise<void> => {
  menuLoading.value = true
  menuErrorMessage.value = ''
  try {
    if (!canRead.value) {
      applyReadonlyMenuFallback()
      return
    }
    const response = await permissionGovernanceApi.fetchPermissionMenuManagement({
      module: menuManagementQuery.module || undefined,
      status: (menuManagementQuery.status as 'enabled' | 'disabled' | 'planned' | '') || undefined,
      keyword: menuManagementQuery.keyword || undefined,
    })
    menuManagement.value = response.data
  } catch (error: unknown) {
    applyReadonlyMenuFallback()
    const message = (error as Error).message || '菜单管理加载失败'
    menuErrorMessage.value = message
    ElMessage.error(message)
  } finally {
    menuLoading.value = false
  }
}

const resetMenuManagementQuery = (): void => {
  menuManagementQuery.module = ''
  menuManagementQuery.status = ''
  menuManagementQuery.keyword = ''
  void loadMenuManagement()
}

const onMenuAction = (
  menuName: string,
  actionLabel: string,
  guarded: boolean,
  guardReason?: string | null,
): void => {
  if (guarded) {
    ElMessage.warning(guardReason || '只读首版：写动作已禁用')
    return
  }
  ElMessage.info(`只读查看：${menuName} / ${actionLabel}`)
}

const loadAuditData = async (): Promise<void> => {
  auditLoading.value = true
  auditErrorMessage.value = ''
  try {
    if (!canAuditRead.value) {
      applyReadonlyAuditFallback()
      return
    }

    const [securityResp, operationResp] = await Promise.all([
      permissionGovernanceApi.fetchPermissionSecurityAudit(securityQuery),
      permissionGovernanceApi.fetchPermissionOperationAudit(operationQuery),
    ])
    securityAudit.value = securityResp.data
    operationAudit.value = operationResp.data
  } catch (error: unknown) {
    applyReadonlyAuditFallback()
    const message = (error as Error).message || '审计查询加载失败'
    auditErrorMessage.value = message
    ElMessage.error(message)
  } finally {
    auditLoading.value = false
  }
}

const loadDiagnosticData = async (): Promise<void> => {
  diagnosticLoading.value = true
  diagnosticErrorMessage.value = ''
  try {
    if (!canDiagnostic.value) {
      applyReadonlyDiagnosticFallback()
      return
    }
    const response = await permissionGovernanceApi.fetchPermissionGovernanceDiagnostic()
    diagnosticData.value = response.data
  } catch (error: unknown) {
    applyReadonlyDiagnosticFallback()
    const message = (error as Error).message || '诊断摘要加载失败'
    diagnosticErrorMessage.value = message
    ElMessage.error(message)
  } finally {
    diagnosticLoading.value = false
  }
}

const resetSecurityQuery = (): void => {
  securityQuery.from_date = ''
  securityQuery.to_date = ''
  securityQuery.module = ''
  securityQuery.action = ''
  securityQuery.request_id = ''
  securityQuery.resource_type = ''
  securityQuery.resource_id = ''
  securityQuery.event_type = ''
  securityQuery.user_id = ''
  securityQuery.page = 1
  securityQuery.page_size = 20
  void loadAuditData()
}

const resetOperationQuery = (): void => {
  operationQuery.from_date = ''
  operationQuery.to_date = ''
  operationQuery.module = ''
  operationQuery.action = ''
  operationQuery.request_id = ''
  operationQuery.resource_type = ''
  operationQuery.resource_id = undefined
  operationQuery.operator = ''
  operationQuery.result = undefined
  operationQuery.error_code = ''
  operationQuery.page = 1
  operationQuery.page_size = 20
  void loadAuditData()
}

const exportSecurityAuditCsv = async (): Promise<void> => {
  exportGuardMessage.value = ''
  if (!canExport.value) {
    exportGuardMessage.value = '当前账号无 permission:export 权限，安全审计导出动作已拦截。'
    ElMessage.warning(exportGuardMessage.value)
    return Promise.resolve()
  }
  securityExporting.value = true
  try {
    exportGuardMessage.value = '安全审计导出属于副作用动作，当前只读模式已执行 guarded 拦截。'
    ElMessage.warning(exportGuardMessage.value)
  } catch (error: unknown) {
    ElMessage.error((error as Error).message || '导出失败')
  } finally {
    securityExporting.value = false
  }
}

const exportOperationAuditCsv = async (): Promise<void> => {
  exportGuardMessage.value = ''
  if (!canExport.value) {
    exportGuardMessage.value = '当前账号无 permission:export 权限，操作审计导出动作已拦截。'
    ElMessage.warning(exportGuardMessage.value)
    return Promise.resolve()
  }
  operationExporting.value = true
  try {
    exportGuardMessage.value = '操作审计导出属于副作用动作，当前只读模式已执行 guarded 拦截。'
    ElMessage.warning(exportGuardMessage.value)
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
      await loadMenuManagement()
      await loadAuditData()
      await loadDiagnosticData()
    })
    .catch((error: unknown) => {
      applyReadonlyCatalogFallback()
      applyReadonlyMenuFallback()
      applyReadonlyAuditFallback()
      applyReadonlyDiagnosticFallback()
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

.readonly-parity-hint {
  margin-bottom: 0;
}

.readonly-status-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.header-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.query-form {
  margin-bottom: 12px;
}

.query-form :deep(.el-form-item) {
  margin-bottom: 10px;
}

.query-form :deep(.el-input),
.query-form :deep(.el-select),
.query-form :deep(.el-date-editor) {
  max-width: 260px;
}

.guarded-summary {
  margin-bottom: 10px;
  line-height: 1.5;
}

:deep(.el-card__header) {
  padding: 14px 16px;
}

:deep(.el-card__body) {
  padding: 14px 16px;
}

@media (max-width: 768px) {
  .header-row {
    align-items: flex-start;
  }

  .header-actions {
    width: 100%;
  }

  .query-form :deep(.el-form-item) {
    margin-right: 0;
    width: 100%;
  }

  .query-form :deep(.el-input),
  .query-form :deep(.el-select),
  .query-form :deep(.el-date-editor) {
    width: 100% !important;
    max-width: 100%;
  }
}
</style>
