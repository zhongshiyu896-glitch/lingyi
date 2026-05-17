# TASK-Z004B-33 CAND06 跨模块 E2E 验收执行报告

- source_head: `cb4cd4f98d094825e80b174e238f9df00d29dc53`
- source_subject: `chore: seal cand05 factory warehouse ui alignment`
- selected_candidate_id: `TASK-Z004B-CAND-06`
- master_chain_id: `Z004-CROSS-E2E-20260517-001`

## 1. 前置门槛
- staged_empty: `true`
- product_diff_empty: `true`
- local_dev_db_gate: `pass`

## 2. 跨模块写链路
- approved_write_request_count: `16`
- allowed_write_endpoint_hit_set: `['POST /api/production/plans', 'POST /api/production/plans/{plan_id}/create-work-order', 'POST /api/production/plans/{plan_id}/material-check', 'POST /api/production/work-orders/{work_order}/sync-job-cards', 'POST /api/subcontract/', 'POST /api/subcontract/settlement-locks', 'POST /api/subcontract/settlement-locks/release', 'POST /api/subcontract/settlement-preview', 'POST /api/subcontract/{order_id}/inspect', 'POST /api/subcontract/{order_id}/issue-material', 'POST /api/subcontract/{order_id}/receive', 'POST /api/warehouse/stock-entry-drafts', 'POST /api/warehouse/stock-entry-drafts/{draft_id}/cancel', 'POST /api/workshop/tickets/batch', 'POST /api/workshop/tickets/register', 'POST /api/workshop/tickets/reversal']`
- allowed_read_endpoint_hit_set: `['GET /api/factory-statements/', 'GET /api/production/plans', 'GET /api/production/plans/{plan_id}', 'GET /api/subcontract/', 'GET /api/subcontract/settlement-candidates', 'GET /api/subcontract/{order_id}', 'GET /api/warehouse/stock-entry-drafts/{draft_id}', 'GET /api/warehouse/stock-entry-drafts/{draft_id}/outbox-status', 'GET /api/warehouse/stock-ledger', 'GET /api/warehouse/stock-summary', 'GET /api/workshop/daily-wages', 'GET /api/workshop/job-cards/{job_card}/summary', 'GET /api/workshop/tickets']`
- allowed_read_endpoint_miss_set: `['GET /api/factory-statements/{statement_id}', 'GET /api/warehouse/alerts', 'GET /api/warehouse/batches']`
- allowed_read_endpoint_miss_reasons: `{'GET /api/factory-statements/{statement_id}': 'factory statement detail requires concrete statement_id in local chain; list read verified.', 'GET /api/warehouse/alerts': 'not hit in this chain sample.', 'GET /api/warehouse/batches': 'not hit in this chain sample.'}`

## 3. fail-closed
- fail_closed_case_count: `4`
- cases:
  - `missing_request_id`: status=409, code=WORKSHOP_IDEMPOTENCY_CONFLICT, message=request_id 不能为空
  - `scenario_tag_request_mismatch`: status=409, code=WORKSHOP_IDEMPOTENCY_CONFLICT, message=scenario_tag 载体缺失或格式非法
  - `source_ref_mismatch`: status=409, code=SUBCONTRACT_STOCK_OUTBOX_CONFLICT, message=LOCAL_GATE_FAIL_CLOSED:mismatched_source_ref
  - `non_local_dev_db_gate`: status=401, code=AUTH_UNAUTHORIZED, message=未登录或 Token 无效

## 4. 回滚与 zero_residual
- rollback_cleanup_executed: `True`
- baseline_total: `0`
- after_write_total: `22`
- after_cleanup_total: `0`
- residual_scan_result: `no_new_residual`
- zero_residual: `True`

## 5. 浏览器证据
- routes: `['/production/plans', '/workshop/tickets/register', '/workshop/tickets/batch', '/warehouse', '/subcontract/list', '/factory-statements/list']`
- screenshots_dir: `/tmp/task_z004b33_screenshots`
- before/after/rollback_after: `12/12/12`
- desktop/mobile: `18/18`
- png_count: `36`

## 6. 副作用计数
- unexpected_write_request_count: `0`
- forbidden_write_request_count: `0`
- erpnext_write_count: `0`
- worker_sync_internal_job_request_count: `0`
- production_write_count: `0`
- import_export_download_upload_print_count: `0`

## 7. 产物
- evidence: `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/task_z004b_33_cand06_cross_module_e2e_acceptance_evidence.json`
- api_result: `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/task_z004b_33_cand06_cross_module_e2e_api_result.json`
- zero_residual: `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/task_z004b_33_cand06_cross_module_zero_residual_result.json`
- browser_result: `/tmp/task_z004b33_browser_result.json`

## 8. 说明
- 本任务仅执行本地 dev gate 下的受控样板链路；未进行任何远端生命周期动作。
