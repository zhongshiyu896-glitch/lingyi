# TASK-Z002B-62-IMPL-FIX1 BOM local gate fail-closed no-DB-write 修复报告

## 1) 结论
- TASK_ID: `TASK-Z002B-62-IMPL-FIX1`
- ROLE: `B Engineer`
- STATUS: `READY_FOR_REVIEW`
- CODE_CHANGED: `YES`

本轮完成 BOM gate failure 路径修复：local gate/carrier/local-dev 失败时直接 `409` 返回，不再写入审计日志、不再触发 commit。并重跑 6 个写接口闭环与 fail-closed 证据。

## 2) 修复点
- 文件：`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/bom.py`
- 关键变更：
  - `_validate_local_bom_request_gate` 的 local-dev 不满足场景改为 `WORKSHOP_IDEMPOTENCY_CONFLICT`（409）。
  - 新增 `_is_local_bom_gate_failure(exc)`。
  - 在 `create / update / set-default / activate / deactivate` 的 `except AppException` 分支中，对 gate failure 直接 `return _app_err(exc)`，不调用 `_record_failure_safely`。
  - `explode` 维持 `except AppException -> _app_err(exc)`，无审计写入路径。

## 3) 回归结果
- 受控写接口（全部 200）：
  - `POST /api/bom/`
  - `PUT /api/bom/{bom_id}`
  - `POST /api/bom/{bom_id}/set-default`
  - `POST /api/bom/{bom_id}/activate`
  - `POST /api/bom/{bom_id}/deactivate`
  - `POST /api/bom/{bom_id}/explode`
- `approved_write_request_count=6`
- `unexpected_write_request_count=0`

### fail-closed（全部 409）
- `missing_request_id_status=409`
- `mismatched_request_id_status=409`
- `mismatched_bom_no_or_source_ref_status=409`
- `mismatched_item_code_status=409`
- `mismatched_reason_status=409`

### 关键审计口径
- `db_write_on_failed_gate_count=0`
- `audit_log_delta_on_failed_gate.ly_operation_audit_log=0`
- `audit_log_delta_on_failed_gate.ly_security_audit_log=0`
- `audit_log_delta_on_failed_gate.ly_operation_audit_log_failed_create_resource_no=0`

## 4) 清理与残留
- `rollback_cleanup_executed=true`
- `zero_residual=true`
- `residual_counts_by_table`：
  - `ly_apparel_bom=0`
  - `ly_apparel_bom_item=0`
  - `ly_bom_operation=0`
  - `ly_operation_audit_log=0`
  - `ly_security_audit_log=0`

## 5) 证据文件
- evidence: `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/task_z002b_62_bom_write_compute_closure_evidence.json`
- regression API: `/tmp/task_z002b62_regression_api.json`
- cleanup: `/tmp/task_z002b62_cleanup.json`
- browser: `/tmp/task_z002b62_browser_result.json`
- screenshots: `/tmp/task_z002b62_screenshots`（`screenshots_count=3`）

## 6) 禁止项核对
- allowlist 外编辑: NO
- `models/bom.py` 编辑: NO
- tests 编辑: NO
- `app/core/request_id.py` 编辑: NO
- worker / ERPNext adapter 编辑: NO
- ERPNext/worker/sync/internal/production 写入触发: NO
- `git add/commit/push`: NO
- `PR/merge/close/tag/release/cleanup/reset/restore/clean/delete`: NO
- parked blockers released: NO
