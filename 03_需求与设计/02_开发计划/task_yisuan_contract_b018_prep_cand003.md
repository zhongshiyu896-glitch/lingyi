# TASK-YISUAN-CONTRACT-B018-PREP-CAND003

- TASK_ID: `TASK-YISUAN-CONTRACT-B018-PREP-CAND003`
- ROLE: `B Engineer`
- HEAD: `767dd71a2fcf4af58c60d4cf658eff5f8cb89afb`
- branch: `codex/sprint4-seal`
- cached_count: `0`
- HEAD_tag_count: `0`
- git_diff_check: `PASS`

## Selected Candidate

- selected_candidate: `CONTRACT-CAND-003`
- covered_contract_ids: `["A002","A006"]`
- module_scope: `销售订单/大货计划契约合并`
- routes:
  - `/sales-inventory/sales-orders`
  - `/sales-inventory/sales-orders/detail`
  - `/production/plans`

## Route Source Locations

- `/sales-inventory/sales-orders`: `06_前端/lingyi-pc/src/router/index.ts:162-164`
- `/sales-inventory/sales-orders/detail`: `06_前端/lingyi-pc/src/router/index.ts:168-170`
- `/production/plans`: `06_前端/lingyi-pc/src/router/index.ts:51-53`

## Allowed Files / Support Files

- allowed_files:
  - `06_前端/lingyi-pc/src/views/sales_inventory/SalesInventorySalesOrderList.vue`
  - `06_前端/lingyi-pc/src/views/sales_inventory/SalesInventorySalesOrderDetail.vue`
  - `06_前端/lingyi-pc/src/views/production/ProductionPlanList.vue`
- allowed_files_exist: `true`
- allowed_files_clean: `true`
- optional_support_files:
  - `07_后端/lingyi_service/app/local_dev.py`
- optional_support_status:
  - exists=`true`
  - clean=`true`
  - mode=`local-dev support only`
  - `modifiable_in_b018=false`

## Contract Sources

- `04_测试与验收/测试证据/yisuan_business_shadow_capture/YISUAN_CAP_A002_business_contract_merge_20260520/yisuan_development_contract_input.json`
- `04_测试与验收/测试证据/yisuan_business_shadow_capture/YISUAN_CAP_A006_order_page_static_field_button_nogo_contract_20260521/order_page_development_input.json`
- contract_sources_exist: `true`

## Frozen Contract Boundary

- business_contract_summary: `订单静态字段、按钮 NO-GO 边界与计划看板字段按 A002/A006 输入合并。`
- key_fields:
  - A002 contract ids（6项）：
    - `YISUAN-DEV-CONTRACT-baseline_reference`
    - `YISUAN-DEV-CONTRACT-base_objects_reference_contract`
    - `YISUAN-DEV-CONTRACT-style_min_create_readback_contract`
    - `YISUAN-DEV-CONTRACT-quote_draft_min_save_readback_contract`
    - `YISUAN-DEV-CONTRACT-order_qty_matrix_popup_only_contract`
    - `YISUAN-DEV-CONTRACT-ui_route_field_button_readonly_shell_contract`
  - A006 verified：
    - `订单数量矩阵 popup-only：预览矩阵/颜色尺码交叉格 黑色/M/2 -> 弹窗保存(S) -> 主页面数量矩阵回写 2。`
  - A006 allowed display sample：
    - `订单, 客户, 下单日期, 业务员, 汇率, 币种, 备注, 款号, 款名, 颜色, 尺码, 单价`
- validation_rules:
  - A006 partial static UI contracts 3项（字段展示、按钮展示、联动区壳层展示）
  - A006 forbidden actions 17项（保存/编辑/新增/提交/审核/反审核/删除/作废/生产采购加工/BOM/入出库/收付款对账）
- status_rules:
  - A002 state labels：`VERIFIED/PARTIAL/UNKNOWN/NO-GO/BLOCKED`
  - A006 blocked_or_unknown contracts：
    - `主订单保存, 订单详情回读, 生产制单, 加工单, BOM, 工序, 库存, 财务, 提交/审核/删除/作废, 生成生产/采购/加工单`
- readonly/readback rules:
  - contract source readback required=`true`
  - A002 explicit_non_claim:
    - `UI 静态证据不等同业务算法 1:1`
    - `mainOrderSaveClicked=false`
    - `orderCreated=false`
    - `orderNumberGenerated=false`
    - `审核未验证/报价提交未验证/转订单未验证`
  - A006 development_boundary:
    - `static_ui_and_popup_only_contract_reference; no main save, no production/BOM/inventory/finance action logic`
- forbidden_scope（继承）：
  - `主订单真实写入`
  - `生产联动计算`
  - `production readback / remote lifecycle / go-live`

## Frozen B019 Evidence Requirement

- routes HTTP 200：`/sales-inventory/sales-orders`、`/sales-inventory/sales-orders/detail`、`/production/plans`
- route final_path: `N/A`
- PNG screenshots: `1440x1200`
- contract source readback present=`true`
- covered_contract_ids=`["A002","A006"]`
- key_fields / validation_rules / status_rules / readonly_readback observed=`true`
- partial/unknown fields:
  - preserved=`true`
  - claimed_as_confirmed=`false`
- write_requests_observed_count=`0`
- production_write_requests=`0`
- erpnext_production_write_requests=`0`
- real_production_account_used=`false`
- real_business_object_created=`false`
- linked_calculation_enabled=`false`
- typecheck_exit_code=`0`
- dev_server_started_stopped=`true`

## Dirty Classification

- tracked_dirty_count: `16`
- frontend_dirty_count: `3`
- backend_or_test_dirty_count: `10`
- log_control_dirty_count: `3`
- dirty_intersections: `[]`
- unknown_dirty: `[]`
- must_block_before_continue: `[]`

## Decision / Boundary

- implementation_allowed: `true`
- next_task: `TASK-YISUAN-CONTRACT-B019-IMPL-CAND003`

## Data Boundary

- data_classification: `contract_merge_no_real_object`
- test_data_used: `false`（若 B019 需临时数据，必须 `scenario_tag + rollback + zero_residual`）
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

## Prohibited Actions Confirmation

- code_modified: `false`
- browser/typecheck/pytest_rerun: `false`
- stage/commit/amend_used: `false`
- push/pr/tag/release_used: `false`
- reset/restore/clean/delete_used: `false`
- 后端、router、API 修改: `false`
- real_business_object_created: `false`
- linked_calculation_enabled: `false`

- residual_risk: `A006 存在 blocked/unknown 合同项，B019 必须维持 no-claim 与 no-action 语义。`
- NEXT_ROLE: `C Auditor`
