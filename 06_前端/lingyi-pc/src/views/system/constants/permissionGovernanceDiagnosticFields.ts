import type {
  PermissionGovernanceDiagnosticCheck,
  PermissionGovernanceDiagnosticData,
  PermissionMenuManagementData,
  PermissionOperationAuditData,
  PermissionRoleMatrixEntry,
  PermissionSecurityAuditData,
} from '@/api/permission_governance'

export interface PermissionGovernanceCatalogRow {
  module: string
  action: string
  category: string
  is_high_risk: boolean
  ui_exposed: boolean
  description: string
}

export interface PermissionGovernanceExpectedMenuContract {
  menuKey: string
  menuName: string
  expectedRoute: string
  expectedStatus: string
  expectedPermissionAction: string
  requiredGuardedActionKeys: string[]
}

export interface PermissionGovernanceDiagnosticCheckMeta {
  label: string
  group: string
  passHint: string
}

export const permissionGovernanceRemainingGap =
  '未开放 audit export、权限写入、审计写入、ERPNext、outbox、worker 与真实保存链路。'

export const permissionGovernanceExpectedMenus: PermissionGovernanceExpectedMenuContract[] = [
  {
    menuKey: 'permission_governance',
    menuName: '权限治理',
    expectedRoute: '/permissions/governance',
    expectedStatus: 'enabled',
    expectedPermissionAction: 'permission:read',
    requiredGuardedActionKeys: ['menu:create', 'menu:update', 'menu:delete'],
  },
  {
    menuKey: 'security_audit',
    menuName: '安全审计',
    expectedRoute: '/permissions/governance?tab=security',
    expectedStatus: 'enabled',
    expectedPermissionAction: 'permission:audit_read',
    requiredGuardedActionKeys: ['audit:export:security'],
  },
  {
    menuKey: 'operation_audit',
    menuName: '操作审计',
    expectedRoute: '/permissions/governance?tab=operation',
    expectedStatus: 'enabled',
    expectedPermissionAction: 'permission:audit_read',
    requiredGuardedActionKeys: ['audit:export:operation'],
  },
]

export const permissionGovernanceDiagnosticCheckMetaMap: Record<string, PermissionGovernanceDiagnosticCheckMeta> = {
  'permission:read_registered': {
    label: 'permission:read 注册',
    group: '动作目录',
    passHint: '动作目录具备基础只读入口。',
  },
  'permission:audit_read_registered': {
    label: 'permission:audit_read 注册',
    group: '审计回读',
    passHint: '审计只读查询入口可回读。',
  },
  'permission:export_registered': {
    label: 'permission:export 注册',
    group: '导出守卫',
    passHint: '导出动作存在但保持前端 guarded。',
  },
  'permission:diagnostic_registered': {
    label: 'permission:diagnostic 注册',
    group: '诊断入口',
    passHint: '治理诊断入口已注册。',
  },
  permission_diagnostic_hidden: {
    label: '诊断动作前端隐藏',
    group: '前端暴露面',
    passHint: '诊断动作不作为普通写按钮暴露。',
  },
  permission_diagnostic_high_risk: {
    label: '诊断动作高危标记',
    group: '高危识别',
    passHint: '诊断动作已被高危标记隔离。',
  },
  permission_audit_legacy_kept: {
    label: '旧审计兼容动作保留',
    group: '兼容性',
    passHint: '旧权限审计兼容动作仍可回读。',
  },
  no_wildcard_permission_action: {
    label: '无通配符权限动作',
    group: '权限收敛',
    passHint: '权限动作未放大为通配符。',
  },
}

export const readonlyCatalogFallbackRows: PermissionGovernanceCatalogRow[] = [
  {
    module: 'menu',
    action: 'permission:menu:create',
    category: '菜单管理',
    is_high_risk: true,
    ui_exposed: true,
    description: '菜单新增写入口，当前只读治理页仅展示 guarded 状态。',
  },
  {
    module: 'menu',
    action: 'permission:menu:update',
    category: '菜单管理',
    is_high_risk: true,
    ui_exposed: true,
    description: '菜单编辑写入口，当前只读治理页不发起写请求。',
  },
  {
    module: 'menu',
    action: 'permission:menu:delete',
    category: '菜单管理',
    is_high_risk: true,
    ui_exposed: true,
    description: '菜单删除写入口，当前只读治理页保持 disabled/guarded。',
  },
  {
    module: 'audit',
    action: 'permission:audit:export',
    category: '审计导出',
    is_high_risk: true,
    ui_exposed: true,
    description: '安全审计与操作审计导出属于副作用动作，仅展示 guarded_readonly。',
  },
]

export const readonlyRoleFallbackRows: PermissionRoleMatrixEntry[] = [
  {
    role: 'permission_admin',
    actions: ['permission:read', 'permission:audit_read'],
    modules: ['permission', 'system'],
    high_risk_actions: ['permission:menu:create', 'permission:menu:update', 'permission:menu:delete'],
    ui_hidden_actions: [],
  },
  {
    role: 'auditor',
    actions: ['permission:audit_read'],
    modules: ['permission'],
    high_risk_actions: ['permission:audit:export'],
    ui_hidden_actions: ['permission:menu:delete'],
  },
]

export const readonlyMenuManagementFallback: PermissionMenuManagementData = {
  total: 3,
  items: [
    {
      menu_key: 'permission_governance',
      menu_name: '权限治理',
      module: 'permission',
      route: '/permissions/governance',
      permission_action: 'permission:read',
      status: 'enabled',
      owner_role: 'permission_admin',
      description: '权限治理页只读入口，菜单维护动作均被 guarded。',
      actions: [
        {
          action_key: 'menu:create',
          action_label: '菜单新增',
          guarded: true,
          guard_reason: '只读治理流：菜单新增已禁用',
        },
        {
          action_key: 'menu:update',
          action_label: '菜单编辑',
          guarded: true,
          guard_reason: '只读治理流：菜单编辑已禁用',
        },
        {
          action_key: 'menu:delete',
          action_label: '菜单删除',
          guarded: true,
          guard_reason: '只读治理流：菜单删除已禁用',
        },
      ],
    },
    {
      menu_key: 'security_audit',
      menu_name: '安全审计',
      module: 'permission',
      route: '/permissions/governance?tab=security',
      permission_action: 'permission:audit_read',
      status: 'enabled',
      owner_role: 'auditor',
      description: '安全审计只读查询，导出动作在前端本地拦截。',
      actions: [
        {
          action_key: 'audit:export:security',
          action_label: '安全审计导出',
          guarded: true,
          guard_reason: '只读治理流：安全审计导出已拦截',
        },
      ],
    },
    {
      menu_key: 'operation_audit',
      menu_name: '操作审计',
      module: 'permission',
      route: '/permissions/governance?tab=operation',
      permission_action: 'permission:audit_read',
      status: 'enabled',
      owner_role: 'auditor',
      description: '操作审计只读查询，导出动作在前端本地拦截。',
      actions: [
        {
          action_key: 'audit:export:operation',
          action_label: '操作审计导出',
          guarded: true,
          guard_reason: '只读治理流：操作审计导出已拦截',
        },
      ],
    },
  ],
}

export const readonlySecurityAuditFallback: PermissionSecurityAuditData = {
  total: 2,
  page: 1,
  page_size: 20,
  items: [
    {
      id: 101,
      event_type: 'permission_denied',
      module: 'permission',
      action: 'permission:menu:create',
      resource_type: 'menu',
      resource_id: 'permission_governance',
      resource_no: 'MENU-PERMISSION-GOVERNANCE',
      user_id: 'readonly',
      permission_source: 'fallback',
      deny_reason: 'readonly guarded: menu create blocked',
      request_method: 'GUARDED',
      request_path: '/api/permissions/menu-management',
      request_id: 'readonly-security-101',
      created_at: '2026-05-27 10:00:00',
    },
    {
      id: 102,
      event_type: 'export_blocked',
      module: 'permission',
      action: 'permission:audit:export',
      resource_type: 'audit',
      resource_id: 'security',
      resource_no: 'AUDIT-SECURITY',
      user_id: 'readonly',
      permission_source: 'fallback',
      deny_reason: 'readonly guarded: audit export blocked',
      request_method: 'GET',
      request_path: '/api/permissions/audit/security/export',
      request_id: 'readonly-security-102',
      created_at: '2026-05-27 10:05:00',
    },
  ],
}

export const readonlyOperationAuditFallback: PermissionOperationAuditData = {
  total: 2,
  page: 1,
  page_size: 20,
  items: [
    {
      id: 201,
      module: 'permission',
      action: 'menu:update',
      operator: 'readonly',
      resource_type: 'menu',
      resource_id: 1001,
      resource_no: 'MENU-PERMISSION-GOVERNANCE',
      result: 'failed',
      error_code: 'READONLY_GUARDED',
      request_id: 'readonly-operation-201',
      created_at: '2026-05-27 10:10:00',
      has_before_data: false,
      has_after_data: false,
      before_keys: [],
      after_keys: ['guarded_readonly'],
    },
    {
      id: 202,
      module: 'permission',
      action: 'audit:export',
      operator: 'readonly',
      resource_type: 'audit',
      resource_id: null,
      resource_no: 'AUDIT-OPERATION',
      result: 'failed',
      error_code: 'READONLY_EXPORT_BLOCKED',
      request_id: 'readonly-operation-202',
      created_at: '2026-05-27 10:15:00',
      has_before_data: false,
      has_after_data: false,
      before_keys: [],
      after_keys: ['guarded_readonly'],
    },
  ],
}

export const readonlyDiagnosticFallback: PermissionGovernanceDiagnosticData = {
  module: 'permission',
  status: 'ok',
  registered_actions: ['permission:read', 'permission:audit_read', 'permission:export', 'permission:diagnostic'],
  legacy_permission_audit_actions: ['permission_audit:diagnostic'],
  high_risk_actions: ['permission:menu:create', 'permission:menu:update', 'permission:menu:delete', 'permission:diagnostic'],
  ui_hidden_actions: ['permission:diagnostic'],
  roles_with_permission_actions_count: 2,
  checks: [
    { name: 'permission:read_registered', status: 'pass' },
    { name: 'permission:audit_read_registered', status: 'pass' },
    { name: 'permission:diagnostic_registered', status: 'pass' },
    { name: 'permission_diagnostic_hidden', status: 'pass' },
  ],
  catalog_enabled: true,
  roles_matrix_enabled: true,
  audit_read_enabled: true,
  export_enabled: true,
  diagnostic_enabled: true,
  generated_at: '2026-06-03T00:00:00+00:00',
}

export const cloneDiagnosticChecks = (
  checks: PermissionGovernanceDiagnosticCheck[],
): PermissionGovernanceDiagnosticCheck[] => checks.map((item) => ({ ...item }))
