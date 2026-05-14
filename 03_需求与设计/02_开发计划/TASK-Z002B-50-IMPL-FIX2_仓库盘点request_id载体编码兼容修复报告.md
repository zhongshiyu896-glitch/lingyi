# TASK-Z002B-50-IMPL-FIX2｜仓库盘点 request_id 载体编码兼容修复报告

## 1. 修复目标
- TASK_ID: `TASK-Z002B-50-IMPL-FIX2`
- 角色: `B Engineer`
- 修复范围: 仅 `TASK-Z002B-49-PREP` 冻结的 5 个 warehouse allowlist 产品文件
- 修复问题: inventory-count 的 `request_id` 载体编码与全局白名单冲突，导致合法闭环请求被 fail-closed

## 2. 关键修复
- 未修改全局文件 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/request_id.py`
- 将 inventory-count `request_id` 编码改为白名单兼容短格式（仅 `A-Za-z0-9_.-`，长度 <= 64）:
  - `{scenario_tag}-REQ-COUNT-W{warehouse_fnv32_hex8}-D{count_date_yyyymmdd}`
- 前端与后端统一 FNV-1a 32 位算法生成 `warehouse` 载体码。
- 后端 gate 在 create/submit/variance-review/confirm/cancel 全链路校验:
  - `scenario_tag`
  - `warehouse` 载体码
  - `count_date` 载体码
  - `idempotency_key` / `source_ref` / `count_no` / `reason`
- mismatched 或 missing carrier 保持 `409 + no DB write` fail-closed。

## 3. 本轮证据
- scenario_tag: `Z002-WAREHOUSE-COUNT-20260514-698`
- request_id: `Z002-WAREHOUSE-COUNT-20260514-698-REQ-COUNT-WF115D8E6-D20260514`
- browser 证据: `/tmp/task_z002b50_fix2_browser_result.json`
- cleanup 证据: `/tmp/task_z002b50_fix2_cleanup.json`
- 截图目录: `/tmp/task_z002b50_fix2_screenshots`（3 张）

## 4. 回归结果
- 闭环写入状态:
  - `create=201`
  - `submit=200`
  - `variance-review=200`
  - `confirm=200`
  - `cancel=200`
- 写入计数:
  - `approved_write_request_count=5`
  - `unexpected_write_request_count=0`
  - `worker_sync_internal_job_request_count=0`
  - `erpnext_write_count=0`
  - `production_write_count=0`
  - `upload_download_export_print_request_count=0`
- fail-closed:
  - `missing_request_id_status=409`
  - `mismatched_request_id_status=409`
  - `mismatched_source_ref_status=409`
  - `mismatched_warehouse_status=409`
  - `mismatched_count_date_status=409`
  - `db_write_on_failed_gate_count=0`
- cleanup:
  - `rollback_cleanup_executed=true`
  - `zero_residual=true`
  - `residual_counts_by_table` 七表均为 `0`

## 5. 验证命令
- `python3 -m py_compile app/routers/warehouse.py app/schemas/warehouse.py app/services/warehouse_service.py` -> PASS
- `npm run precheck:dev-runtime` -> PASS（`passedChecks=4`, `failedChecks=0`）
- `npm run typecheck` -> PASS
- `npm run verify` -> PASS
- `python3 -m json.tool /tmp/task_z002b50_fix2_browser_result.json` -> PASS
- `python3 -m json.tool /tmp/task_z002b50_fix2_cleanup.json` -> PASS
- `python3 -m json.tool /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/task_z002b_50_impl_fix2_evidence.json` -> PASS
- `python3 -m json.tool /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/task_z002b_50_warehouse_inventory_count_write_closure_evidence.json` -> PASS

## 6. 结论
- `request_id carrier` 编码已与全局白名单兼容，且未放宽全局规则。
- inventory-count 五个 POST 闭环恢复为可通过状态。
- warehouse/count_date mismatch fail-closed 证据已补齐，可进入 C 复审。
