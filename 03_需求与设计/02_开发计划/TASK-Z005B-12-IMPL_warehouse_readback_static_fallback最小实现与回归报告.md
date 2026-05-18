# TASK-Z005B-12-IMPL warehouse readback static fallback 最小实现与回归报告

## 任务结论

- `task_id=TASK-Z005B-12-IMPL`
- `selected_mainline=TASK-Z005A-READBACK-PRECONDITION-MAINLINE`
- `source_head=9dd14e3f0a34de0c6d6c782974d051173b1246ff`
- `source_subject=chore: seal z005 readback carrier precondition`
- `task_status=PASS`

## 本次实现（仅 allowlist 文件）

- 修改文件：
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/warehouse.py`
- 未修改文件：
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/warehouse_service.py`

### 实现点

1. 新增 alerts fallback builder：
   - 在 `EXTERNAL_SERVICE_UNAVAILABLE` 且 `_local_warehouse_read_fallback_enabled(exc)=true` 时返回 empty-state。
   - 结构固定：
     - `company=query.company`
     - `warehouse=query.warehouse`
     - `item_code=query.item_code`
     - `alert_type=query.alert_type_normalized`
     - `items=[]`
2. 新增 batches fallback builder：
   - 同样仅在上述 trigger 条件下启用。
   - 结构固定：
     - `company=query.company`
     - `warehouse=query.warehouse`
     - `item_code=query.item_code`
     - `batch_no=query.batch_no`
     - `total=0`
     - `items=[]`
3. `get_stock_alerts` 与 `list_batches` 的 `ERPNextAdapterException` 分支改为：
   - 满足 trigger -> fallback
   - 否则 -> 维持原 `_handle_erpnext_error` fail-closed
4. 未放宽非 local-dev / 非 static / 非 `EXTERNAL_SERVICE_UNAVAILABLE` 情况下的失败路径。

## local-dev gate 与回归

- local-dev 运行方式：
  - `bash scripts/run_local_dev_runtime.sh -> app.local_dev:app`
  - `APP_ENV=development`
  - `LINGYI_PERMISSION_SOURCE=static`
  - `LINGYI_ERPNEXT_BASE_URL=""`
  - `LINGYI_DB_URL=sqlite:///./lingyi_service.local.db`
- dev auth：
  - `X-LY-Dev-User=local.dev`
  - `X-LY-Dev-Roles=System Manager`

### API 回归（GET only）

- `GET /api/warehouse/alerts`
  - `status=200`
  - `data.company=Z005 Local Company 005`
  - `data.warehouse=样衣仓`
  - `data.item_code=LY-MTRL-001`
  - `data.alert_type=low_stock`
  - `data.items=[]`
- `GET /api/warehouse/batches`
  - `status=200`
  - `data.company=Z005 Local Company 005`
  - `data.warehouse=样衣仓`
  - `data.item_code=LY-MTRL-001`
  - `data.batch_no=BATCH-Z005-001`
  - `data.total=0`
  - `data.items=[]`

## 计数与约束

- `allowed_read_hit=["GET /api/warehouse/alerts","GET /api/warehouse/batches"]`
- `write_request_count=0`
- `unexpected_write_request_count=0`
- `forbidden_request_count=0`
- `erpnext_write_count=0`
- `worker_sync_internal_job_request_count=0`
- `production_write_count=0`
- `import_export_download_upload_print_count=0`
- `failed_gate_db_write_count=0`

## readback 业务状态

- 继承前置证据：
  - `statement_detail_readback_status=hit`（来自 `task_z005b_05_factory_statement_scenario_carrier_evidence.json`）
- 本次结果：
  - `alerts_readback_status=hit_local_dev_static_empty_state`
  - `batches_readback_status=hit_local_dev_static_empty_state`
- 判定：
  - `readback_business_closed=true`（仅指 readback 口径闭合）
  - `project_completion_claimed=false`
  - `remote_lifecycle_parked=true`

## 证据产物

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/task_z005b_12_warehouse_readback_static_fallback_evidence.json`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/task_z005b_12_warehouse_readback_static_fallback_api_regression.json`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/task_z005b_12_warehouse_readback_static_fallback_browser_result.json`
- `/tmp/task_z005b12_screenshots`（`screenshot_count=0`）

## 约束遵守说明

- 未修改 allowlist 外文件。
- 未执行任何 `POST/PUT/PATCH/DELETE`。
- 未创建数据，未执行 cleanup/SQL cleanup/rollback。
- 未执行 stage/commit/push/PR/tag/release/reset/restore/clean。
- 未声明项目完成。
