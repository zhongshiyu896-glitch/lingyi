STATUS: DONE
TASK_ID: TASK-YISUAN-1TO1-B035-SOURCE-CAPTURE-PREP-CAND005
ROLE: B Engineer

SUMMARY:
- capture_allowed: true
- selected_candidate: null
- blocked_candidate: YISUAN-1TO1-CAND-005
- next_task: TASK-YISUAN-1TO1-B036-SOURCE-CAPTURE-CAND005

CAPTURE_PLAN:
- capture_needed_items:
  - subcontract detail 字段/布局/按钮/状态来源补齐
  - materialPurchase parity 入口到 list/detail 的统一映射补齐
  - subcontract list/detail 入口与回读关系补齐
  - stock-ledger 与 warehouse 联合视觉合同补齐
  - CAND-005 统一详情级 UI 契约包索引补齐
- capture_allowed_sources:
  - 03_需求与设计 下既有 UI/source/contract 文档与 json
  - 04_测试与验收/测试证据 下既有截图、DOM、route、network 证据
  - G0 baseline、G2 reference map、A001-A006 contract pool 本地静态文件
  - 本地开发环境只读页面（仅用于缺口确认，不作为生产来源）
- capture_forbidden_sources:
  - ERPNext production
  - 真实生产账号会话
  - 任何线上生产写入路径
  - 任何 push/PR/tag/release 相关路径
  - 任何会产生真实采购、外协、库存、财务、生产数据的路径
- target_routes:
  - /materialPurchase/materialPurchaseProcess
  - /subcontract/list
  - /subcontract/detail
  - /sales-inventory/stock-ledger
  - /warehouse
- target_evidence_dir:
  - 03_需求与设计/02_开发计划/evidence/yisuan_1to1_b036_source_capture_cand005/
- expected_artifacts:
  - route map:
    - route_map.json
    - material_purchase_parity_chain.json
  - screenshots:
    - subcontract_list_1440x1200.png
    - subcontract_detail_1440x1200.png
    - stock_ledger_1440x1200.png
    - warehouse_1440x1200.png
    - material_purchase_redirect_parity_1440x1200.png
  - DOM snapshot or field map:
    - subcontract_detail_field_map.json
    - stock_ledger_field_map.json
    - warehouse_field_map.json
    - list_detail_linkage_map.json
  - UI source summary:
    - ui_source_summary.json
  - unified contract:
    - unified_cand005_ui_contract.json
    - unified_cand005_ui_contract.md
    - unified_cand005_ui_contract.tsv
- success_criteria:
  - unified_contract_available=true
  - source_status=found
  - missing_source_items=[]
  - subcontract list/detail 合同可追溯到 source 文件
  - materialPurchase parity 链条与 detail 合同一致
  - stock-ledger 与 warehouse 联动合同完整
  - 合同包具备可审计 source path + section 映射

PRODUCTION_SAFETY_BOUNDARY:
- no_production_account=true
- no_erpnext_production=true
- no_write_actions=true
- no_remote_actions=true
- no_code_modification=true

CHECKS:
- allowed_files_clean_status: all_exist=true, all_clean=true
- dirty_intersections: []
- unknown_dirty: []
- must_block_before_continue: []

DATA_BOUNDARY:
- data_classification: ui_source_capture_prep_no_write
- test_data_used: false
- seed_data_used: false
- sqlite_not_formal_database: true
- erpnext_production_forbidden: true
- real_production_account_forbidden: true
- real_purchase_subcontract_inventory_finance_production_migration_forbidden: true
- a001_a006_business_contract_merged: false
