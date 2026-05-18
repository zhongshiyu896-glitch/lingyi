# TASK-Z005B-05-IMPL factory statement scenario carrier 最小修复与 readback 回归报告

- TASK_ID: TASK-Z005B-05-IMPL
- ROLE: B Engineer
- selected_mainline: TASK-Z005A-READBACK-PRECONDITION-MAINLINE
- source_head: ca1e2b977644bf76b4715b0d2255aeee0d93b3fe
- source_subject: chore: seal z004 final local closeout
- boundary_file: /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/task_z005b_04_factory_statement_scenario_carrier_boundary.json
- task_status: PASS

## 实现范围

本轮仅修改 allowlist 内后端 router 的 scenario pattern：

- before: `re.compile(r"(Z003-FACTORY-STMT-\d{8}-\d{3})")`
- after: `re.compile(r"((?:Z003-FACTORY-STMT|Z005-READBACK-PRECONDITION)-\d{8}-\d{3})")`

保留完整外层捕获组，`matched.group(1)` 仍返回完整 scenario tag。未放宽 `X-Request-ID`、normalized `request_id`、`scenario_tag`、`idempotency_key`、`source_ref`、`source_type`、`status_action` 校验链。

## 兼容性验证

- Z003 compatibility: PASS，`Z003-FACTORY-STMT-20260518-001` 仍可由 group 1 捕获。
- Z005 compatibility: PASS，`Z005-READBACK-PRECONDITION-20260518-001` 可由 group 1 捕获。
- Z005 pattern mismatch: 已解除，`POST /api/factory-statements/` 不再因 `request_id 未包含合法 scenario_tag` 返回 409。

## API 回归

- local-dev gate: PASS，运行时为 `bash scripts/run_local_dev_runtime.sh -> app.local_dev:app`，DB 为 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/lingyi_service.local.db`。
- scenario_tag: `Z005-READBACK-PRECONDITION-20260518-005`
- create: `POST /api/factory-statements/` 返回 200，生成 `statement_id=1`、`statement_no=FS-20260518034320486596-00DACD`。
- list readback: `GET /api/factory-statements/` 读回同一 `statement_id` 与 `statement_no`。
- detail readback: `GET /api/factory-statements/{statement_id}` 读回同一 `statement_id` 与 `statement_no`。
- rollback: `POST /api/factory-statements/{statement_id}/cancel` 返回 200，状态变更为 `cancelled`。
- warehouse alerts: `GET /api/warehouse/alerts` 返回 503 `EXTERNAL_SERVICE_UNAVAILABLE`，风险保留。
- warehouse batches: `GET /api/warehouse/batches` 返回 503 `EXTERNAL_SERVICE_UNAVAILABLE`，风险保留。

## Zero Residual

- baseline_total: 0
- after_write_total: 1
- after_cleanup_total: 0
- zero_residual: true
- residual_scan_result: no_new_residual
- failed_gate_db_write_count: 0

说明：cancel 后保留的 `ly_factory_statement_log`、`ly_factory_statement_operation`、`ly_security_audit_log`、`ly_operation_audit_log` 为审计历史，不计入 active business residual total。

## 请求范围

- allowed_write_hit:
  - `POST /api/factory-statements/`
  - `POST /api/factory-statements/{statement_id}/cancel`
- unexpected_write_request_count: 0
- erpnext_write_count: 0
- worker_sync_internal_job_request_count: 0
- production_write_count: 0
- import_export_download_upload_print_count: 0

## 浏览器只读证据

- browser scope: direct allowed read endpoint JSON screenshots
- screenshot_dir: `/tmp/task_z005b05_screenshots`
- screenshot_count: 2
- screenshots:
  - `/tmp/task_z005b05_screenshots/factory_statement_detail_real_statement_id.png`
  - `/tmp/task_z005b05_screenshots/factory_statement_list_filtered_real_statement_id.png`
- browser write_request_count: 0
- browser forbidden_request_count: 0

## 产物

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/task_z005b_05_factory_statement_scenario_carrier_evidence.json`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/task_z005b_05_factory_statement_scenario_carrier_api_regression.json`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/task_z005b_05_factory_statement_scenario_carrier_zero_residual.json`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/task_z005b_05_factory_statement_scenario_carrier_browser_result.json`
- `/tmp/task_z005b05_screenshots`

## 保留状态

- readback_business_closed: false
- project_completion_claimed: false
- remote_lifecycle_parked: true
- NEXT_ROLE: C Auditor
