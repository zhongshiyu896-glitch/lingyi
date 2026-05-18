# TASK-Z007B-05-IMPL BOM草稿残留最小解阻与回归报告

- TASK_ID: TASK-Z007B-05-IMPL
- task_status: PASS
- source_head: 7ae7867bb62e846d644dab556df08f8bd4268611
- residual_bom_id: BOM-LY-APLUS-STYLE-20260518-01-V1-20260518120718702643

## 执行范围
- 未修改 `06_前端` / `07_后端` 任何代码。
- 仅调用允许写端点：
  - `POST /api/bom/{bom_id}/activate`
  - `POST /api/bom/{bom_id}/deactivate`
- 仅调用允许读端点：
  - `GET /api/bom/`

## 回滚执行结果
1. baseline scan：目标 BOM（id=10）状态为 `draft`。
2. rollback phase：
   - `POST /api/bom/10/activate` -> `200`（status=`active`）
   - `POST /api/bom/10/deactivate` -> `200`（status=`inactive`）
3. after rollback scan：目标 BOM 状态为 `inactive`。

## zero_residual 结论
- baseline_draft_active_count=2
- after_rollback_draft_active_count=1
- `created_new_bom_count=0`
- `zero_residual=true`
- `residual_scan_result=no_new_active_or_draft_residual`

## 写请求门禁统计
- `allowed_write_hit`：
  - `POST /api/bom/{bom_id}/activate`（200）
  - `POST /api/bom/{bom_id}/deactivate`（200）
- `unexpected_write_request_count=0`
- `forbidden_request_count=0`
- `production_write_count=0`
- `erpnext_write_count=0`
- `worker_sync_internal_job_request_count=0`
- `import_export_download_upload_print_count=0`

## 状态保持
- `production_readback_ready=false`
- `go_live_ready=false`
- `project_completion_claimed=false`
- `remote_lifecycle_parked=true`
