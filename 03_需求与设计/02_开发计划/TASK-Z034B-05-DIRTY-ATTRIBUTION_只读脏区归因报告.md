# TASK-Z034B-05-DIRTY-ATTRIBUTION 只读脏区归因报告

## 基本核对

- source_task: TASK-Z034A-REANCHOR-001
- current_head: `6bc20b833e3780e2bd10549a2ce906ee860941cb`
- cached_empty: true
- git diff --check: PASS
- dirty_files_total: 19
- product_test_dirty_count: 16
- log_control_dirty_count: 3
- B03 result: FAIL, `4 failed, 6 passed, 1 warning in 1.12s`, command_run_count=1
- B04 classification: `TEST_CONTRACT_UPDATE_ALLOWED`
- B04 allowed_fix_file: `07_后端/lingyi_service/tests/test_style_profit_api_audit.py`
- current target test dirty diff: false

## 归因证据边界

本轮仅使用只读证据：`git diff --numstat`、当前 dirty status、B03/B04 evidence、历史 ledger NO/historical forbidden 记录。未运行 pytest/npm/browser/build/typecheck/verify，未修改代码或测试，未 stage/commit/push/tag/PR/release。

关键历史证据：

- `03_需求与设计/02_开发计划/task_z032b_41_cand004_ledger.json` 的 `historical_dirty_forbidden_paths` 列出本轮 16 个 product/test dirty files 以及 3 个日志/交接 dirty files。
- `03_需求与设计/02_开发计划/task_z033b_04_cand001_ledger.json` 的 `no_paths` 继续列出本轮 16 个 product/test dirty files，并保持 `backend_yes_paths=[]`、`frontend_yes_paths=[]`、`backend_app_yes_paths=[]`、`historical_dirty_forbidden_in_yes=[]`。
- B04 允许修复范围仅为 `07_后端/lingyi_service/tests/test_style_profit_api_audit.py`，该目标测试当前无 dirty diff；以下 16 个文件均不是 current Z034-CAND-001 allowed fix file。

## 16 个 product/test dirty 逐项归因

| path | category | evidence_basis | allowed_in_next_ledger |
|---|---|---|---|
| `06_前端/lingyi-pc/src/views/cross_module/CrossModuleView.vue` | historical_dirty_forbidden | 当前 tracked diff 为 1 insert/1 delete；Z032B-41 ledger historical_dirty_forbidden_paths 命中；Z033B-04 ledger no_paths 命中；非 B04 allowed_fix_file。 | false |
| `06_前端/lingyi-pc/src/views/production/ProductionPlanList.vue` | historical_dirty_forbidden | 当前 tracked diff 为 1 insert/1 delete；Z032B-41 ledger historical_dirty_forbidden_paths 命中；Z033B-04 ledger no_paths 命中；非 B04 allowed_fix_file。 | false |
| `06_前端/lingyi-pc/src/views/quality/QualityInspectionDetail.vue` | historical_dirty_forbidden | 当前 tracked diff 为 11 inserts/11 deletes；Z032B-41 ledger historical_dirty_forbidden_paths 命中；Z033B-04 ledger no_paths 命中；非 B04 allowed_fix_file。 | false |
| `06_前端/lingyi-pc/src/views/quality/QualityInspectionList.vue` | historical_dirty_forbidden | 当前 tracked diff 为 4 inserts/4 deletes；Z032B-41 ledger historical_dirty_forbidden_paths 命中；Z033B-04 ledger no_paths 命中；非 B04 allowed_fix_file。 | false |
| `06_前端/lingyi-pc/src/views/sales_inventory/SalesInventorySalesOrderDetail.vue` | historical_dirty_forbidden | 当前 tracked diff 为 2 inserts/2 deletes；Z032B-41 ledger historical_dirty_forbidden_paths 命中；Z033B-04 ledger no_paths 命中；非 B04 allowed_fix_file。 | false |
| `06_前端/lingyi-pc/src/views/sales_inventory/SalesInventorySalesOrderList.vue` | historical_dirty_forbidden | 当前 tracked diff 为 20 inserts/20 deletes；Z032B-41 ledger historical_dirty_forbidden_paths 命中；Z033B-04 ledger no_paths 命中；非 B04 allowed_fix_file。 | false |
| `07_后端/lingyi_service/app/schemas/report.py` | historical_dirty_forbidden | 当前 tracked diff 为 1 insert/1 delete；Z032B-41 ledger historical_dirty_forbidden_paths 命中；Z033B-04 ledger no_paths 命中；非 B04 allowed_fix_file。 | false |
| `07_后端/lingyi_service/app/services/report_catalog_service.py` | historical_dirty_forbidden | 当前 tracked diff 为 6 inserts/6 deletes；Z032B-41 ledger historical_dirty_forbidden_paths 命中；Z033B-04 ledger no_paths 命中；非 B04 allowed_fix_file。 | false |
| `07_后端/lingyi_service/app/services/system_config_catalog_service.py` | historical_dirty_forbidden | 当前 tracked diff 为 4 inserts/4 deletes；Z032B-41 ledger historical_dirty_forbidden_paths 命中；Z033B-04 ledger no_paths 命中；非 B04 allowed_fix_file。 | false |
| `07_后端/lingyi_service/tests/test_bom_permissions.py` | historical_dirty_forbidden | 当前 tracked diff 为 15 inserts/2 deletes；Z032B-41 ledger historical_dirty_forbidden_paths 命中；Z033B-04 ledger no_paths 命中；非 B04 allowed_fix_file。 | false |
| `07_后端/lingyi_service/tests/test_logging_sanitization.py` | historical_dirty_forbidden | 当前 tracked diff 为 37 inserts/9 deletes；Z032B-41 ledger historical_dirty_forbidden_paths 命中；Z033B-04 ledger no_paths 命中；非 B04 allowed_fix_file。 | false |
| `07_后端/lingyi_service/tests/test_permission_governance_audit_export.py` | historical_dirty_forbidden | 当前 tracked diff 为 7 inserts/4 deletes；Z032B-41 ledger historical_dirty_forbidden_paths 命中；Z033B-04 ledger no_paths 命中；非 B04 allowed_fix_file。 | false |
| `07_后端/lingyi_service/tests/test_request_id_sanitization.py` | historical_dirty_forbidden | 当前 tracked diff 为 42 inserts/3 deletes；Z032B-41 ledger historical_dirty_forbidden_paths 命中；Z033B-04 ledger no_paths 命中；非 B04 allowed_fix_file。 | false |
| `07_后端/lingyi_service/tests/test_style_profit_api.py` | historical_dirty_forbidden | 当前 tracked diff 为 18 inserts/13 deletes；Z032B-41 ledger historical_dirty_forbidden_paths 命中；Z033B-04 ledger no_paths 命中；虽然同属 style profit 命名空间，但非 B04 allowed_fix_file `test_style_profit_api_audit.py`。 | false |
| `07_后端/lingyi_service/tests/test_subcontract_company_permission.py` | historical_dirty_forbidden | 当前 tracked diff 为 212 inserts/47 deletes；Z032B-41 ledger historical_dirty_forbidden_paths 命中；Z033B-04 ledger no_paths 命中；非 B04 allowed_fix_file。 | false |
| `07_后端/lingyi_service/tests/test_workshop_permissions.py` | historical_dirty_forbidden | 当前 tracked diff 为 196 inserts/67 deletes；Z032B-41 ledger historical_dirty_forbidden_paths 命中；Z033B-04 ledger no_paths 命中；非 B04 allowed_fix_file。 | false |

## 日志/交接 dirty 记录

以下 3 个 dirty files 仅记录，不纳入 product/test 归因，也不用于代码方向判断：

- `00_交接与日志/HANDOVER_STATUS.md`
- `03_需求与设计/01_架构设计/架构师会话日志.md`
- `03_需求与设计/02_开发计划/工程师会话日志.md`

## 结论

- unknown_dirty: []
- must_block_before_continue: []
- blocked: false
- recommended_next_task: `TASK-Z034B-05-FIX-CAND001`

16 个 product/test dirty 均可由历史 ledger 证明为 `historical_dirty_forbidden`，不得进入后续 ledger/stage。当前 Z034-CAND-001 的合法修复边界仍仅限 `07_后端/lingyi_service/tests/test_style_profit_api_audit.py`，本轮未执行修复。
