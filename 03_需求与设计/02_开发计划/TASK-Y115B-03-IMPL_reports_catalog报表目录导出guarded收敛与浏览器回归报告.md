# TASK-Y115B-03-IMPL /reports/catalog 报表目录导出 guarded 收敛与浏览器回归报告

## 1. 任务范围
- TASK_ID: `TASK-Y115B-03-IMPL`
- 路由: `/reports/catalog`
- 本轮仅修改 allowlist:
  - `06_前端/lingyi-pc/src/views/reports/ReportCatalog.vue`
  - `03_需求与设计/02_开发计划/TASK-Y115B-03-IMPL_reports_catalog报表目录导出guarded收敛与浏览器回归报告.md`
  - `03_需求与设计/02_开发计划/工程师会话日志.md`
- 未修改: `CrossModuleView.vue`、`06_前端/lingyi-pc/src/api/**`、`07_后端/**`、测试代码、控制面文件、C 审计记录。

## 2. 实现锚点
文件: `06_前端/lingyi-pc/src/views/reports/ReportCatalog.vue`

### 2.1 导出动作 guarded 收敛
- `handleExport` 移除 `exportReportCatalogCsv` 真实调用路径。
- 导出动作改为只读 guarded 提示，不触发下载或导出请求。
- 导出按钮增加:
  - `data-testid="report-catalog-export-guarded-button"`
  - `data-write-guard="guarded:readonly-report-export"`
- 新增可见 guarded 状态提示:
  - `data-testid="report-catalog-export-guarded-state"`

### 2.2 只读 GET 语义保留
- 保留并复核以下只读 GET 链路:
  - 报表目录: `fetchReportCatalog`
  - 员工任务统计: `fetchReportEmployeeTaskStatistics`
  - 审批报表: `fetchReportApprovalReports`
- 查询按钮继续触发三段只读 GET 联动加载。

### 2.3 fail-closed 收敛
- 请求失败时统一清空对应数据与选中态，避免展示陈旧数据:
  - `financeItems/selectedFinanceItem`
  - `employeeTaskItems/selectedEmployeeTaskItem/employeeTaskStatusTags/employeeTaskButtons/employeeTaskTableHeaders`
  - `approvalItems/selectedApprovalItem/approvalStatusTags/approvalButtons/approvalTableHeaders`
- 详情加载失败时清空 `selectedFinanceItem` 并显示错误态。

### 2.4 可审计 data-testid 补齐
- 页面与筛选:
  - `report-catalog-page`
  - `report-catalog-query-form`
  - `report-catalog-company-input`
  - `report-catalog-customer-input`
  - `report-catalog-source-module-select`
  - `report-catalog-query-button`
- 目录与详情:
  - `report-catalog-table`
  - `report-catalog-detail-card`
  - `report-catalog-empty-state`
  - `report-catalog-error-state`
- 权限/禁用:
  - `report-catalog-permission-state`
  - `report-catalog-export-permission-state`
- 子区块:
  - `employee-task-statistics-section`
  - `employee-task-statistics-table`
  - `employee-task-statistics-empty-state`
  - `approval-report-section`
  - `approval-report-table`
  - `approval-report-empty-state`

## 3. 浏览器回归证据
- result_json: `/tmp/task_y115b_03_impl_20260511T171855Z/browser_results.json`
- screenshots_dir: `/tmp/task_y115b_03_impl_20260511T171855Z/screenshots`
- screenshots_count: `8`

关键断言:
- `route_open=true`
- `first_screen_visible=true`
- `catalog_query_get_triggered=true`
- `employee_task_statistics_get_triggered=true`
- `approval_reports_get_triggered=true`
- `export_action_guarded=true`
- `empty_state=true`
- `error_state=true`
- `permission_or_disabled_state=true`

零副作用指标:
- `write_request_count=0`
- `upload_download_export_print_request_count=0`
- `unexplained_console_errors_total=0`
- `unexplained_network_4xx_5xx_total=0`

expected 说明:
- `expected_network_4xx_5xx_total=13`
  - 包含权限态 `401` 与受控错误态 `503`（审批报表接口）
- `expected_console_errors_total=13`
  - 与受控 401/503 验证对应，未计入 unexplained

## 4. 验证结果
前端目录: `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc`
- `npm run precheck:dev-runtime`: PASS
- `npm run typecheck`: PASS
- `npm run verify`: PASS

仓库校验: `/Users/hh/Desktop/领意服装管理系统`
- `git diff --cached --name-only`: EMPTY
- `git diff --cached --check`: PASS
- `git diff --check`: PASS
- `git diff --name-only -- 06_前端 07_后端`: 仅 `06_前端/lingyi-pc/src/views/cross_module/CrossModuleView.vue` 与 `06_前端/lingyi-pc/src/views/reports/ReportCatalog.vue`

## 5. 生命周期与边界核对
- 未执行 `git add / commit / push`: YES
- 未执行 `PR / merge / tag / release`: YES
- 未执行 `cleanup / reset / restore / clean / delete`: YES
- 未释放 parked blockers: YES
