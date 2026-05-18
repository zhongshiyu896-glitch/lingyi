# TASK-Z006B-21-IMPL-FIX1：UI business evidence 只读采样修复与回归报告

## 1. 任务信息
- TASK_ID：`TASK-Z006B-21-IMPL-FIX1`
- 角色：`B Engineer`
- 主线：`TASK-Z006A-PRODUCTION-READBACK-READINESS-MAINLINE`
- 候选：`Z006-CAND-007`
- source_head：`47e0f1b6113a05155e857fe1039d84df08f37776`
- `base_path_corrected=true`

## 2. 修复结论
- 已按 FIX1 要求使用 Vite base path 进行重新采样，目标路径为：
  1. `/fate/warehouse`
  2. `/fate/factory-statements/list?z005_readback=1`
  3. `/fate/factory-statements/detail?id=1`
- 旧采样遗留文件仍在截图目录，已在 browser result 中逐张标记 `is_target_page=false` 并给出 `rejection_reason`，不计入业务证据。

## 3. 采样覆盖与截图
- 视口：desktop + mobile。
- 截图目录：`/tmp/task_z006b21_screenshots`。
- 目录内 PNG 总数：`10`。
- 其中有效目标页截图：`6`（3 页 × 2 视口，均为 `is_target_page=true`）。
- 无效旧截图：`4`（`legacy_pre_fix1_capture_not_counted`）。

## 4. 只读请求与端点命中
- request log 已记录 `method/url/status/allowed_read_endpoint`。
- `request_methods=["GET"]`。
- 仅统计 `/api/*` 请求：
  - `allowed_read_hit=18`
  - `api_404_count=0`
  - 状态分布：`500` 与 `requestfailed(net::ERR_ABORTED)`，未出现写请求。
- 命中允许读端点：
  - `GET /api/warehouse/alerts`
  - `GET /api/warehouse/batches`
  - `GET /api/factory-statements/`
  - `GET /api/factory-statements/{statement_id}`
- 计数保持：
  - `write_request_count=0`
  - `unexpected_write_request_count=0`
  - `forbidden_request_count=0`
  - `allowed_write_endpoints=[]`
  - `production_write_count=0`
  - `erpnext_write_count=0`
  - `worker_sync_internal_job_request_count=0`
  - `import_export_download_upload_print_count=0`

## 5. factory statement detail 状态
- 本轮未创建新数据，沿用既有证据 `statement_id=1` 做 detail 只读采样。
- `/fate/factory-statements/detail?id=1` 页面可进入业务详情页 UI。
- `factory_statement_detail_status=ui_rendered_with_statement_id_1_api_500_or_requestfailed`

## 6. 状态保持
- `local_acceptance_closed=true`
- `production_readback_ready=false`
- `go_live_ready=false`
- `project_completion_claimed=false`
- `remote_lifecycle_parked=true`

## 7. 交付产物
- `task_z006b_21_ui_business_evidence_readonly_capture_evidence.json`
- `task_z006b_21_ui_business_evidence_readonly_capture_api_regression.json`
- `task_z006b_21_ui_business_evidence_readonly_capture_browser_result.json`
- `/tmp/task_z006b21_screenshots`
