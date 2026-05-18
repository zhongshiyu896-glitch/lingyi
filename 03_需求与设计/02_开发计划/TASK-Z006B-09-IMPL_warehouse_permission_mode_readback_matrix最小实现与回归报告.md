# TASK-Z006B-09-IMPL｜warehouse permission mode readback matrix 最小实现与回归报告

## 1. 任务与边界
- TASK_ID: `TASK-Z006B-09-IMPL`
- 角色: `B Engineer`
- 主线: `TASK-Z006A-PRODUCTION-READBACK-READINESS-MAINLINE`
- source_head: `5236ec2cb3924baf742b8dd946fae7320e3ba5c6`
- source_subject: `chore: seal z006 warehouse adapter contract fixture`
- selected_candidate_id: `Z006-CAND-003`
- boundary_file: `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/task_z006b_08_warehouse_permission_mode_readback_boundary.json`

本轮遵守约束：
- 仅新增 `test_warehouse_permission_mode_readback_matrix.py` 并更新证据文档。
- 不修改 allowlist 外文件。
- 不触发 POST/PUT/PATCH/DELETE。
- 不触发 ERPNext 生产读写，不使用生产账号，不创建 DB 业务数据。

## 2. 本轮实现
新增测试文件：
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_warehouse_permission_mode_readback_matrix.py`

测试覆盖目标：
- permission mode matrix 的 `M01` 到 `M06`。
- 每个 mode 同时验证 `GET /api/warehouse/alerts` 与 `GET /api/warehouse/batches`。
- 只允许 `M01` 返回 local-dev/static empty-state 200。
- `M02-M06` 必须 fail-closed。

## 3. 回归结果
### 3.1 permission mode matrix（6/6）
1. `M01 local_dev_static_external_service_unavailable`
   - alerts: `200 + local_dev_static_empty_state` PASS
   - batches: `200 + local_dev_static_empty_state` PASS
2. `M02 local_dev_static_invalid_response`
   - alerts: `502 + ERPNEXT_RESPONSE_INVALID` PASS
   - batches: `502 + ERPNEXT_RESPONSE_INVALID` PASS
3. `M03 local_dev_static_non_external_service_unavailable`
   - alerts: `503 + ERPNEXT_TIMEOUT` PASS
   - batches: `503 + ERPNEXT_TIMEOUT` PASS
4. `M04 local_dev_non_static_external_service_unavailable`
   - alerts: `503 + PERMISSION_SOURCE_UNAVAILABLE` PASS
   - batches: `503 + PERMISSION_SOURCE_UNAVAILABLE` PASS
5. `M05 non_local_dev_static_external_service_unavailable`
   - alerts: `503 + EXTERNAL_SERVICE_UNAVAILABLE` PASS
   - batches: `503 + EXTERNAL_SERVICE_UNAVAILABLE` PASS
6. `M06 non_local_dev_non_static_external_service_unavailable`
   - alerts: `503 + PERMISSION_SOURCE_UNAVAILABLE` PASS
   - batches: `503 + PERMISSION_SOURCE_UNAVAILABLE` PASS

结论：
- `permission_mode_matrix_passed=6/6`
- `fallback_allowed_modes=[M01]`
- `fail_closed_modes=[M02,M03,M04,M05,M06]`
- `alerts_matrix_status=PASS`
- `batches_matrix_status=PASS`

### 3.2 既有 adapter contract fixture 回归
- `tests.test_warehouse_adapter_contract_fixture`：`10/10 PASS`

### 3.3 编译校验
- `py_compile` 覆盖：
  - `app/routers/warehouse.py`
  - `app/services/warehouse_service.py`
  - `tests/test_warehouse_permission_mode_readback_matrix.py`
  - `tests/test_warehouse_adapter_contract_fixture.py`
- 结果：PASS

## 4. 风险与状态保持
- `allowed_write_endpoints=[]`
- `write_request_count=0`
- `erpnext_write_count=0`
- `worker_sync_internal_job_request_count=0`
- `production_write_count=0`
- `import_export_download_upload_print_count=0`
- `readback_business_closed=true`
- `readback_business_closed_scope=local_dev_static_fallback_only`
- `production_erpnext_non_fallback_readback_closed=false`
- `project_completion_claimed=false`
- `remote_lifecycle_parked=true`

说明：
- 本轮闭环仅提升 permission mode 可验证性，不外推为生产 ERPNext 非 fallback 闭合。
