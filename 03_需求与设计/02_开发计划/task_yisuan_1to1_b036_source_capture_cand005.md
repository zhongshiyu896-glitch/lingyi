# STATUS: DONE
TASK_ID: TASK-YISUAN-1TO1-B036-SOURCE-CAPTURE-CAND005
ROLE: B Engineer

## SUMMARY
- head: `a078e5c24c220b45a37a7f690e6f3070a4265a08`
- branch: `codex/sprint4-seal`
- cached_empty: true
- head_tag_empty: true
- git_diff_check: PASS
- source_status: found
- unified_contract_available: true
- missing_source_items: []
- next_task: `TASK-YISUAN-1TO1-B037-PREP`

## ARTIFACTS_WRITTEN
- `03_需求与设计/02_开发计划/evidence/yisuan_1to1_b036_source_capture_cand005/route_map.json`
- `03_需求与设计/02_开发计划/evidence/yisuan_1to1_b036_source_capture_cand005/ui_source_summary.json`
- `03_需求与设计/02_开发计划/evidence/yisuan_1to1_b036_source_capture_cand005/unified_contract.json`
- `03_需求与设计/02_开发计划/evidence/yisuan_1to1_b036_source_capture_cand005/unified_contract.md`
- `03_需求与设计/02_开发计划/evidence/yisuan_1to1_b036_source_capture_cand005/unified_contract.tsv`
- `03_需求与设计/02_开发计划/evidence/yisuan_1to1_b036_source_capture_cand005/field_layout_map.json`
- `03_需求与设计/02_开发计划/evidence/yisuan_1to1_b036_source_capture_cand005/dom_or_structure_map.json`
- `03_需求与设计/02_开发计划/evidence/yisuan_1to1_b036_source_capture_cand005/screenshot_manifest.json`
- `03_需求与设计/02_开发计划/evidence/yisuan_1to1_b036_source_capture_cand005/source_file_index.json`

## ROUTE_MAP
- `materialPurchase`: `/materialPurchase/materialPurchaseProcess` -> `/subcontract/list?parity=material-purchase`
- `subcontract`: list/detail 入口与 readback 关系已纳入统一合同
- `inventory`: stock-ledger 与 warehouse 视觉联动关系已纳入统一合同

## PRODUCTION_SAFETY_BOUNDARY
- erpnext_production_forbidden: true
- real_production_account_forbidden: true
- online_production_write_forbidden: true
- remote_lifecycle_release_forbidden: true

## ALLOWED_FILES_CLEAN_STATUS
- `06_前端/lingyi-pc/src/views/subcontract/SubcontractOrderList.vue`: clean
- `06_前端/lingyi-pc/src/views/subcontract/SubcontractOrderDetail.vue`: clean
- `06_前端/lingyi-pc/src/views/sales_inventory/SalesInventoryStockLedger.vue`: clean
- `06_前端/lingyi-pc/src/views/warehouse/WarehouseDashboard.vue`: clean

## DIRTY_STATE
- dirty_intersections: []
- unknown_dirty: []
- must_block_before_continue: []

## DATA_BOUNDARY
- data_classification: `ui_source_capture_no_write`
- test_data_used: false
- seed_data_used: false
- sqlite_not_formal_database: true
- erpnext_production_forbidden: true
- real_production_account_forbidden: true
- real_purchase_subcontract_inventory_finance_production_migration_forbidden: true
- a001_a006_business_contract_merged: false
