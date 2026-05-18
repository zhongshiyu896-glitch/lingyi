# TASK-Z007B-11-IMPL G1完整基础对象前置链路最小实现与回归报告

- TASK_ID: `TASK-Z007B-11-IMPL`
- task_status: `PASS`
- source_head: `48892f2fa01622587b931ef58117654505575478`
- selected_candidate_id: `Z007-CAND-001-S1`

## 1. 执行边界
- 未修改 `06_前端` / `07_后端` 代码。
- 未调用 sales order draft create/cancel。
- 未调用 factory statement 写端点。
- 仅使用允许写端点：
  1. `POST /api/bom/`
  2. `POST /api/bom/{bom_id}/activate`
  3. `POST /api/bom/{bom_id}/deactivate`

## 2. 对象链路执行结果
- customer/supplier/factory：按 B10 策略保持复用证据路径，本轮未创建独立主数据（`created_independent_master_data_count=0`）。
- fabric/style：通过 BOM 载体完成绑定验证。
  - style: `LY-APLUS-STYLE-20260518-01`
  - fabric: `LY-APLUS-FAB-20260518-01`
  - created_bom_no: `BOM-LY-APLUS-STYLE-20260518-01-V1-Z002-BOM-20260518-711-20260518131629123409`

## 3. baseline -> write -> cleanup
1. baseline scan：
   - style 维度 draft/active 基线数量：`1`
2. write phase：
   - `POST /api/bom/` -> `200`
   - `POST /api/bom/11/activate` -> `200`
   - `POST /api/bom/11/deactivate` -> `200`
3. after cleanup scan：
   - style 维度 draft/active 数量：`1`
   - 新增 draft/active 残留：`[]`

## 4. zero_residual 结论
- `zero_residual=true`
- `residual_scan_result=no_new_active_or_draft_residual`
- 本轮新建 BOM 最终状态：`inactive`
- 不重复处理 B03/B05 已闭合 residual BOM。

## 5. 写请求门禁统计
- `allowed_write_hit`：
  - `POST /api/bom/`（200）
  - `POST /api/bom/{bom_id}/activate`（200）
  - `POST /api/bom/{bom_id}/deactivate`（200）
- `unexpected_write_request_count=0`
- `forbidden_write_request_count=0`
- `production_write_count=0`
- `erpnext_write_count=0`
- `worker_sync_internal_job_request_count=0`
- `import_export_download_upload_print_count=0`

## 6. 状态保持
- `production_readback_ready=false`
- `go_live_ready=false`
- `project_completion_claimed=false`
- `remote_lifecycle_parked=true`
- `readback_business_closed=true`
- `readback_business_closed_scope=local_dev_static_fallback_only`
