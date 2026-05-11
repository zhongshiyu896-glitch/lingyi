# TASK-Y115B-04-IMPL /permissions/governance 权限治理审计导出 guarded 收敛与浏览器回归报告

## 1. 任务范围
- TASK_ID: `TASK-Y115B-04-IMPL`
- 路由: `/permissions/governance`
- 本轮仅修改 allowlist:
  - `06_前端/lingyi-pc/src/views/system/PermissionGovernance.vue`
  - `03_需求与设计/02_开发计划/TASK-Y115B-04-IMPL_permissions_governance权限治理审计导出guarded收敛与浏览器回归报告.md`
  - `03_需求与设计/02_开发计划/工程师会话日志.md`
- 未修改:
  - `06_前端/lingyi-pc/src/views/cross_module/CrossModuleView.vue`
  - `06_前端/lingyi-pc/src/views/reports/ReportCatalog.vue`
  - `06_前端/lingyi-pc/src/api/**`
  - `07_后端/**`
  - 测试代码、控制面文件、架构师日志、Y114 报告/JSON、C 审计记录

## 2. 实现锚点
文件: `06_前端/lingyi-pc/src/views/system/PermissionGovernance.vue`

### 2.1 导出动作 guarded 收敛
- `exportSecurityAuditCsv` 与 `exportOperationAuditCsv` 移除真实导出链路，仅保留 guarded 提示。
- 不再调用 `exportPermissionSecurityAuditCsv` / `exportPermissionOperationAuditCsv`。
- 导出按钮增加:
  - `data-testid="permission-security-audit-export-guarded-button"`
  - `data-testid="permission-operation-audit-export-guarded-button"`
  - `data-write-guard` 标记
- 新增可见 guarded 提示区:
  - `data-testid="permission-audit-export-guarded-state"`

### 2.2 只读 GET 语义保留
- 保留并复核以下只读 GET:
  - `fetchPermissionActionCatalog`
  - `fetchPermissionRolesMatrix`
  - `fetchPermissionMenuManagement`
  - `fetchPermissionSecurityAudit`
  - `fetchPermissionOperationAudit`
- `loadData/loadMenuManagement/loadAuditData` 继续按查询入口触发 GET。

### 2.3 fail-closed 收敛
- 请求失败时清空对应数据，避免陈旧数据残留:
  - 动作目录/角色矩阵清空
  - 菜单管理清空
  - 安全审计/操作审计清空
- 增加显式错误文案状态:
  - `catalogErrorMessage`
  - `menuErrorMessage`
  - `auditErrorMessage`

### 2.4 data-testid 与可审计状态补齐
- 页面与主区块:
  - `permission-governance-page`
  - `action-catalog-section`
  - `roles-matrix-table`
  - `menu-management-section`
  - `permission-audit-section`
- 查询与导出:
  - `action-catalog-refresh-button`
  - `menu-management-query-button`
  - `permission-audit-query-button`
  - 两个 export guarded 按钮
- 状态锚点:
  - 空态: `menu-management-empty-state`、`permission-security-audit-empty-state`、`permission-operation-audit-empty-state`
  - 错误态: `action-catalog-error-state`、`menu-management-error-state`、`permission-audit-error-state`
  - 权限/禁用态: `permission-governance-read-permission-state`、`permission-audit-read-permission-state`、`permission-audit-export-permission-state`

## 3. 浏览器回归证据
- result_json: `/tmp/task_y115b_04_impl_20260511T174137Z/browser_results.json`
- screenshots_dir: `/tmp/task_y115b_04_impl_20260511T174137Z/screenshots`
- screenshots_count: `9`

关键断言:
- `route_open=true`
- `first_screen_visible=true`
- `action_catalog_get_triggered=true`
- `roles_matrix_get_triggered=true`
- `menu_management_get_triggered=true`
- `security_audit_get_triggered=true`
- `operation_audit_get_triggered=true`
- `export_actions_guarded=true`
- `empty_state=true`
- `error_state=true`
- `permission_or_disabled_state=true`

零副作用指标:
- `write_request_count=0`
- `upload_download_export_print_request_count=0`
- `unexplained_console_errors_total=0`
- `unexplained_network_4xx_5xx_total=0`

expected 说明:
- `expected_network_4xx_5xx_total=1`（受控 `503`，用于错误态验证）
- `expected_console_errors_total=1`（与受控错误态一致，不计入 unexplained）

## 4. 验证结果
前端目录: `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc`
- `npm run precheck:dev-runtime`: PASS
- `npm run typecheck`: PASS
- `npm run verify`: PASS

仓库校验: `/Users/hh/Desktop/领意服装管理系统`
- `git diff --cached --name-only`: EMPTY
- `git diff --cached --check`: PASS
- `git diff --check`: PASS
- `git diff --name-only -- 06_前端 07_后端`: `CrossModuleView.vue`、`ReportCatalog.vue`（前序已 C PASS 残留）+ `PermissionGovernance.vue`（本轮新增）

## 5. 生命周期与边界核对
- 未执行 `git add / commit / push`: YES
- 未执行 `PR / merge / tag / release`: YES
- 未执行 `cleanup / reset / restore / clean / delete`: YES
- 未释放 parked blockers: YES
