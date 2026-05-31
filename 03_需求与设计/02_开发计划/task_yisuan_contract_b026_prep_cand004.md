# TASK-YISUAN-CONTRACT-B026-PREP-CAND004

## Baseline

- HEAD: `cc386563111c0b648d29236264f66af12b5029b5`
- branch: `codex/sprint4-seal`
- cached_count: `0`
- HEAD_tag_count: `0`
- git_diff_check: `PASS`
- selected_candidate: `CONTRACT-CAND-004`
- covered_contract_ids: `["A002","A004","A006"]`

## Routes / Source

- routes:
  - `/materialPurchase/materialPurchaseProcess`
  - `/subcontract/list`
  - `/subcontract/detail`
- route_source_locations:
  - `/materialPurchase/materialPurchaseProcess` -> `06_前端/lingyi-pc/src/router/index.ts:269-270` (redirect `/subcontract/list?parity=material-purchase`)
  - `/subcontract/list` -> `06_前端/lingyi-pc/src/router/index.ts:63-65`
  - `/subcontract/detail` -> `06_前端/lingyi-pc/src/router/index.ts:69-71`

## Allowed Files / Contract Sources

- allowed_files:
  - `06_前端/lingyi-pc/src/views/subcontract/SubcontractOrderList.vue`
  - `06_前端/lingyi-pc/src/views/subcontract/SubcontractOrderDetail.vue`
- allowed_files_exist: `true`
- allowed_files_clean: `true`
- contract_sources (3):
  - `04_测试与验收/测试证据/yisuan_business_shadow_capture/YISUAN_CAP_A002_business_contract_merge_20260520/yisuan_development_contract_input.json`
  - `04_测试与验收/测试证据/yisuan_business_shadow_capture/YISUAN_CAP_A004_quote_draft_field_status_readback_contract_20260520/quote_draft_development_input.json`
  - `04_测试与验收/测试证据/yisuan_business_shadow_capture/YISUAN_CAP_A006_order_page_static_field_button_nogo_contract_20260521/order_page_development_input.json`
- contract_sources_exist: `true`
- optional_support_files:
  - `07_后端/lingyi_service/app/local_dev.py` (`read_only_support_only`, exists+clean)

## Frozen Contract Boundary

- module_scope: `采购/外协契约合并`
- business_contract_summary: 采购 parity、外协列表/详情字段、草稿状态与只读按钮边界按 A002/A004/A006 合并。
- forbidden_scope:
  - 真实采购外协写入
  - 财务结算真实写入
  - production readback / remote lifecycle / go-live
- rollback_zero_residual_requirement: `mandatory_for_any_local_write_or_auto_validation`

- key_fields (inherited):
  - A004 verified field keys: `quoteNo/customer/quoteDate/quotePerson/exchangeRate/currency/taxRate/remark/status/styleCode/styleName/color/size/taxIncludedPrice/taxExcludedPrice/quoteCost/taxExcludedPriceRmb/grossProfit/createdAt/createdBy/modifiedAt/modifiedBy`
  - A002 popup-only keys: `draftStatus=待提交`, `quantitySource=预览矩阵/颜色尺码交叉格`, `popupSaveButton=保存(S)`, `writebackTarget=主页面订单数量矩阵`
  - A006 display-only keys inherited from `allowed_for_development_display` (static UI scope)

- validation_rules (inherited):
  - A004 partial_fields limitations: 价格/税/毛利算法未验证，不可外推为业务 1:1
  - A004 unknown_fields: 完整报价算法/价格公式/利润公式/税价换算/转订单规则/提交审核流转/采购库存财务副作用
  - A006 boundary: `static_ui_and_popup_only_contract_reference; no main save, no production/BOM/inventory/finance action logic`

- status_rules (inherited):
  - A002 state labels: `VERIFIED/PARTIAL/UNKNOWN/NO-GO/BLOCKED`
  - A004 blocked_actions: `提交/审核/反审核/删除/作废/生成订单转订单/导入导出/编辑添加`
  - A006 blocked_or_unknown_contracts: `主订单保存、订单详情回读、生产制单、加工单、BOM、工序、库存、财务、提交审核删除作废、生成生产采购加工单`

- readonly/readback rules (inherited):
  - contract source readback 必须可定位
  - A002 explicitNonClaim 必须保留（报价提交/审核/转订单未验证；mainOrderSaveClicked=false；orderCreated=false）
  - A006 unknown/blocked 事实不得确认为真实业务动作

## Frozen B027 Evidence Requirement

- 三条 routes HTTP 200
- `/materialPurchase/materialPurchaseProcess` final_path: `/subcontract/list?parity=material-purchase`
- PNG screenshot: `1440x1200`
- contract source readback present=true
- covered_contract_ids=`["A002","A004","A006"]`
- key_fields/validation_rules/status_rules/readonly-readback observed=true
- partial/unknown/blocked preserved=true, claimed_as_confirmed=false
- popup-only/disabled-only real_action_triggered=false
- write_requests_observed_count=0
- production_write_requests=0
- erpnext_production_write_requests=0
- real_production_account_used=false
- real_business_object_created=false
- linked_calculation_enabled=false
- typecheck exit_code=0
- dev server started/stopped=true

## Dirty Classification

- tracked_dirty_count: `16`
- frontend_dirty_count: `3`
- backend_or_test_dirty_count: `10`
- log_control_dirty_count: `3`
- dirty_intersections: `[]`
- unknown_dirty: `[]`
- must_block_before_continue: `[]`

## Decision

- implementation_allowed: `true`
- next_task: `TASK-YISUAN-CONTRACT-B027-IMPL-CAND004`

## Data Boundary

- data_classification: `contract_merge_no_real_object`
- test_data_used: `false` (if needed later: scenario_tag + rollback + zero_residual)
- seed_data_used: `false`
- sqlite_not_formal_database: `true`
- sqlite_direct_reuse_for_production_forbidden: `true`
- real_business_object_created: `false`
- linked_calculation_enabled: `false`
- erpnext_production_connected: `false`
- real_production_account_used: `false`
- production_readback: `false`
- go_live: `false`
- project_completion: `false`
- remote_lifecycle_parked: `true`
- prior A005/A006 unknown/blocked claimed_as_confirmed: `false`

## Prohibited Actions Confirmation

- code_modified: `false`
- browser/typecheck/pytest: `not_run`
- stage/commit/amend: `not_performed`
- push/PR/tag/release: `not_performed`
- reset/restore/clean/delete: `not_performed`
- ERPNext production connected: `false`
- real production account used: `false`
- real business object created: `false`
- linked calculation enabled: `false`

residual_risk: 仓库历史噪声较大，B027 需继续严格限于 2 个 allowed 前端文件，并保持 A006 blocked/unknown/popup-only 边界不被提升为 confirmed 业务动作。
