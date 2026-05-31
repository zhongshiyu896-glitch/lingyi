STATUS: DONE
TASK_ID: TASK-YISUAN-1TO1-B039-REGRESSION-CAND005
ROLE: B Engineer

SUMMARY:
- head: `a078e5c24c220b45a37a7f690e6f3070a4265a08`
- branch: `codex/sprint4-seal`
- cached: `[]`
- head_tag: `[]`
- next_task: `TASK-YISUAN-1TO1-B040-LEDGER-CAND005`

REGRESSION_RESULT:
- code_modified_in_this_task: `false`
- changed_files:
  - `06_前端/lingyi-pc/src/views/subcontract/SubcontractOrderList.vue`
  - `06_前端/lingyi-pc/src/views/subcontract/SubcontractOrderDetail.vue`
  - `06_前端/lingyi-pc/src/views/sales_inventory/SalesInventoryStockLedger.vue`
  - `06_前端/lingyi-pc/src/views/warehouse/WarehouseDashboard.vue`
- forbidden_paths_touched: `[]`

ROUTES:
- `/materialPurchase/materialPurchaseProcess` -> HTTP 200, final_path=`/subcontract/list?parity=material-purchase`
- `/subcontract/list` -> HTTP 200, final_path=`/subcontract/list`
- `/subcontract/detail` -> HTTP 200, final_path=`/subcontract/detail`
- `/sales-inventory/stock-ledger` -> HTTP 200, final_path=`/sales-inventory/stock-ledger`
- `/warehouse` -> HTTP 200, final_path=`/warehouse`

SCREENSHOTS (PNG 1440x1200):
- `03_需求与设计/02_开发计划/evidence/yisuan_1to1_b039_regression_cand005/material_purchase_parity_1440x1200.png`
- `03_需求与设计/02_开发计划/evidence/yisuan_1to1_b039_regression_cand005/subcontract_list_1440x1200.png`
- `03_需求与设计/02_开发计划/evidence/yisuan_1to1_b039_regression_cand005/subcontract_detail_1440x1200.png`
- `03_需求与设计/02_开发计划/evidence/yisuan_1to1_b039_regression_cand005/stock_ledger_1440x1200.png`
- `03_需求与设计/02_开发计划/evidence/yisuan_1to1_b039_regression_cand005/warehouse_1440x1200.png`

UI SOURCE:
- source_status: `found`
- unified_contract_available: `true`
- ui_source_readback_present: `true`
- A001-A006 business contract merged: `false`

DOM:
- anchors observed: `12/12`
- contract_source: `B037_PREP`

NETWORK/WRITE SAFETY:
- write_requests_observed_count: `0`
- production_write_requests: `0`
- erpnext_production_write_requests: `0`
- real_production_account_used: `false`
- auth_401_count: `0`
- request_methods_summary: `GET only`

TYPECHECK:
- command: `npm run typecheck`
- workdir: `06_前端/lingyi-pc`
- exit_code: `0`

DATA_BOUNDARY:
- data_classification: `ui_parity_no_write`
- test_data_used: `false`
- seed_data_used: `false`
- sqlite_not_formal_database: `true`
- 禁止 ERPNext production: `true`
- 禁止真实生产账号: `true`
- 禁止真实采购/外协/库存/财务/生产数据迁移: `true`

EVIDENCE FILE ATTRIBUTION:
- capture_method: `inline_node_script_plus_playwright`
- temp_script_file_persisted: `false`

SCOPE_GUARD:
- dirty_intersections: `[]`
- unknown_dirty: `[]`
- must_block_before_continue: `[]`

EVIDENCE:
- `03_需求与设计/02_开发计划/evidence/yisuan_1to1_b039_regression_cand005/route_probe.json`
- `03_需求与设计/02_开发计划/evidence/yisuan_1to1_b039_regression_cand005/browser_evidence.json`
- `03_需求与设计/02_开发计划/evidence/yisuan_1to1_b039_regression_cand005/ui_source_summary.json`
- `03_需求与设计/02_开发计划/evidence/yisuan_1to1_b039_regression_cand005/dom_anchors.json`
- `03_需求与设计/02_开发计划/evidence/yisuan_1to1_b039_regression_cand005/network_write_observation.json`
- `03_需求与设计/02_开发计划/evidence/yisuan_1to1_b039_regression_cand005/typecheck_result.json`
