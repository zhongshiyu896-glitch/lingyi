# TASK-Y75B-02-IMPL /reports/catalog 审批报表 1:1 首版实现与浏览器回归报告

## 1. 任务与边界
- TASK_ID: `TASK-Y75B-02-IMPL`
- 路由: `/reports/catalog`
- 目标语义: `TASK-Y74B-P1-02 审批报表`（只读首版）
- allowlist: `TASK-Y75B-02` baseline 冻结的 5 个 `/reports/catalog` 承载文件
- 约束: 仅 GET 只读；不新增写路由；确认/审核/上传/下载/导出/打印入口均 guarded 或 disabled

## 2. 实现摘要
- 前端页面（`ReportCatalog.vue`）新增“审批报表（TASK-Y74B-P1-02）”只读区块：
  - `data-testid="approval-report-section"`（`ReportCatalog.vue:320`）
  - 新增筛选项：审批人、审批状态、开始时间、结束时间（`ReportCatalog.vue:42,55`）
  - 新增字段：审批单号、审批类型、关联单据、申请人、审批人、部门、金额、优先级、提交时间、完成时间、状态、备注
  - 顶部按钮“确认/审核”为 guarded 提示；“导出/打印/上传”为 disabled
  - 新增只读加载链路：`fetchReportApprovalReports` + `loadApprovalReports`（`ReportCatalog.vue:666,671`）
- 前端 API（`report.ts`）新增只读方法：
  - `fetchReportApprovalReports`（`report.ts:165`）
  - `GET /api/reports/approval-reports`（`report.ts:173`）
- 后端 router（`report.py`）新增只读路由：
  - `GET /api/reports/approval-reports`（`report.py:238`）
  - 权限动作保持 `REPORT_READ`，并沿用 `PermissionService` scope 校验
- 后端 schema/service 新增只读聚合：
  - schema: `ReportApprovalReportItemData` / `ReportApprovalReportData`（`schemas/report.py:102,129`）
  - service: `get_approval_reports(...)`（`services/report_catalog_service.py:502`）
  - 服务端补齐状态标签、按钮映射、表头映射与只读样例行（`services/report_catalog_service.py:320,336`）
- 路由顺序 guard：
  - 静态 `approval-reports` 位于动态 `catalog/{report_key}` 之前（`238 < 323`），无 route shadowing 风险
- 写路由新增: `NO`（未新增 POST/PUT/PATCH/DELETE）

## 3. preserved 检查
- `/reports/catalog` 既有报表目录主语义 preserved: PASS
- 既有筛选/列表/详情/导出入口 preserved: PASS
- `TASK-Y75B-01-IMPL` 员工任务统计表只读语义 preserved: PASS
- 既有权限态、空态、错误态、禁用态 preserved: PASS
- 既有 guarded 写动作 preserved: PASS
- 共享路由边界（仅在 `/reports/catalog` 内扩展）preserved: PASS

## 4. 验证结果
- `python3 -m py_compile`（`report.py` / `report.py schema` / `report_catalog_service.py`）: PASS
- `npm run precheck:dev-runtime`（`06_前端/lingyi-pc`）: PASS
- `npm run typecheck`（`06_前端/lingyi-pc`）: PASS
- `npm run verify`（`06_前端/lingyi-pc`）: PASS
- `git diff --cached --name-only`: 空
- `git diff --cached --check`: PASS
- `git diff --check`: PASS
- `git diff --name-only -- 06_前端 07_后端`: 仅 5 个 allowlist 产品文件

## 5. 浏览器回归证据
- 回归路由: `/reports/catalog`
- script: `/tmp/task_y75b_02_impl_browser_check.mjs`
- result_json: `/tmp/task_y75b_02_impl_20260507T131402Z_browser_results.json`
- screenshots_dir: `/tmp/task_y75b_02_impl_20260507T131402Z_screenshots`
- screenshots_count: `6`
- 核心断言:
  - `route_open=true`
  - `first_screen_visible=true`
  - `filters_present=true`
  - `approval_report_fields_mapped=true`
  - `buttons_mapped=true`
  - `status_tags_mapped=true`
  - `empty_state=true`
  - `error_state=true`
  - `permission_or_disabled_state=true`
  - `write_request_count=0`
  - `upload_download_export_print_request_count=0`
  - `unexplained_console_errors_total=0`
  - `unexplained_network_4xx_5xx_total=0`
- 说明:
  - 错误态通过可控 `approver_keyword=__ERROR__` 注入触发，`network_4xx_5xx_total=1` 与 `console_errors_total=1` 均为 expected，不计入 unexplained。

## 6. 禁止动作核对
- 未修改 allowlist 外产品代码: PASS
- 未修改测试代码: PASS
- 未修改 A 控制面文件: PASS
- 未修改 C 审计记录: PASS
- 未执行 `git add/commit/push`: PASS
- 未执行 `PR/merge/tag/release`: PASS
- 未执行 `cleanup/reset/restore/clean/delete`: PASS
- 未启动 `TASK-Y75B-03` 或后续页面: PASS
- 未释放 parked blockers: PASS
