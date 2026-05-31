STATUS: DONE
TASK_ID: TASK-YISUAN-1TO1-B034-SOURCE-ATTRIBUTION-CAND005
ROLE: B Engineer

SUMMARY:
- source_status: partial
- needs_ui_source: true
- selected_candidate: null
- blocked_candidate: YISUAN-1TO1-CAND-005
- unified_contract_available: false
- next_task: TASK-YISUAN-1TO1-B035-SOURCE-CAPTURE-PREP-CAND005

SOURCE_ATTRIBUTION:
- source_files:
  - 04_测试与验收/测试证据/yisuan_incremental_capture/20260517T211026Z/screenshots/sidebar_modules/09_物料采购.png
  - 04_测试与验收/测试证据/yisuan_incremental_capture/20260517T211026Z/screenshots/sidebar_modules/10_物料进销存.png
  - 04_测试与验收/测试证据/yisuan_business_shadow_capture/G0_baseline_20260518/module_entry_baseline.json
  - 03_需求与设计/02_开发计划/task_z007b_17_module_entry_to_list_route_parity_evidence.json
  - 04_测试与验收/测试证据/z046_cand004_subcontract_interaction_regression/route_evidence.json
  - 04_测试与验收/测试证据/z045_cand005_subcontract_sync_readback/route_evidence.json
  - 04_测试与验收/测试证据/z045_cand005_subcontract_sync_readback/dom_anchors_evidence.json
  - 04_测试与验收/测试证据/z045_cand005_subcontract_sync_readback/z045_cand005_list_1440x1200.png
  - 04_测试与验收/测试证据/z045_cand005_subcontract_sync_readback/z045_cand005_detail_1440x1200.png
- missing_source_items:
  - subcontract/detail 字段-布局-按钮-状态映射合同
  - stock-ledger 与 warehouse 联合视觉合同
  - materialPurchase parity 到 subcontract list/detail 统一入口-详情合同
  - 列表/详情/库存页统一 readback 与视觉联动合同
  - CAND-005 统一详情级 UI 合同包索引

ROUTES:
- /materialPurchase/materialPurchaseProcess -> /subcontract/list?parity=material-purchase
- /subcontract/list -> SubcontractOrderList.vue
- /subcontract/detail -> SubcontractOrderDetail.vue
- /sales-inventory/stock-ledger -> SalesInventoryStockLedger.vue
- /warehouse -> WarehouseDashboard.vue

CHECKS:
- allowed_files_clean_status: all_exist=true, all_clean=true
- dirty_intersections: []
- unknown_dirty: []
- must_block_before_continue:
  - missing_unified_cand005_ui_contract

DATA_BOUNDARY:
- data_classification: ui_source_attribution_no_write
- test_data_used: false
- seed_data_used: false
- sqlite_not_formal_database: true
- erpnext_production_forbidden: true
- real_production_account_forbidden: true
- real_purchase_subcontract_inventory_finance_production_migration_forbidden: true
- a001_a006_business_contract_merged: false
