# TASK-YISUAN-CONTRACT-B028-REGRESSION-CAND004

## 1) 基本状态
- HEAD: `cc386563111c0b648d29236264f66af12b5029b5`
- branch: `codex/sprint4-seal`
- cached_count: `0`
- HEAD_tag_count: `0`
- code_modified_in_this_task: `false`
- git diff --check: `PASS`

## 2) 变更归因（仅复验，不改代码）
- expected_allowed_files:
  - `06_前端/lingyi-pc/src/views/subcontract/SubcontractOrderList.vue`
  - `06_前端/lingyi-pc/src/views/subcontract/SubcontractOrderDetail.vue`
- current_dirty_in_allowed_files:
  - `06_前端/lingyi-pc/src/views/subcontract/SubcontractOrderList.vue`
  - `06_前端/lingyi-pc/src/views/subcontract/SubcontractOrderDetail.vue`
- regression_task_code_patch_applied: `false`

## 3) 路由与截图复验
- routes_evidence: `03_需求与设计/02_开发计划/evidence/yisuan_contract_b028_cand004_regression/route_probe.json`
  - `/materialPurchase/materialPurchaseProcess` -> `200`
  - `/subcontract/list?parity=material-purchase` -> `200`
  - `/subcontract/detail` -> `200`
- material_purchase_parity_final_path: `/subcontract/list?parity=material-purchase`
- screenshots:
  - `material_purchase_parity_1440x1200.png` (`1440x1200`)
  - `subcontract_list_parity_1440x1200.png` (`1440x1200`)
  - `subcontract_detail_1440x1200.png` (`1440x1200`)

## 4) 合同回读与边界复验
- covered_contract_ids: `["A002","A004","A006"]`
- contract_source_readback_present: `true`
- key_fields_observed: `true`
- validation_rules_observed: `true`
- status_rules_observed: `true`
- readonly_readback_observed: `true`
- unknown_blocked_fields_preserved: `true`
- unknown_blocked_fields_claimed_as_confirmed: `false`
- popup_or_disabled_boundary: `true`
- popup_or_disabled_real_action_triggered: `false`
- not_claimed_as_business_action: `true`

## 5) 零写与对象边界复验
- write_requests_observed_count: `0`
- production_write_requests: `0`
- erpnext_production_write_requests: `0`
- real_production_account_used: `false`
- request_methods_observed_only_GET: `true`
- no_post_put_patch_delete_observed: `true`
- real_business_object_created: `false`
- linked_calculation_enabled: `false`

## 6) Typecheck 与服务状态
- typecheck:
  - command: `npm run typecheck`
  - workdir: `06_前端/lingyi-pc`
  - exit_code: `0`
- dev server: started=`true`, stopped=`true`

## 7) 数据边界
- data_classification: `contract_merge_no_real_object`
- test_data_used: `false`
- seed_data_used: `false`
- sqlite_not_formal_database: `true`
- sqlite_direct_reuse_for_production_forbidden: `true`
- erpnext_production_connected: `false`
- production_readback: `false`
- go_live: `false`
- project_completion: `false`
- remote_lifecycle_parked: `true`

## 8) 禁止动作确认
- 未改代码 / 未改 `local_dev.py` / 未改 router/API/后端
- 未 stage / commit / amend
- 未 push / PR / tag / release
- 未 reset / restore / clean / delete
- 未将 unknown/blocked 升级为 confirmed
- 未将 popup/disabled-only 转成真实业务动作

## 9) 脏区与阻塞
- dirty_intersections: `[]`
- unknown_dirty: `[]`
- must_block_before_continue: `[]`

## 10) Residual Risk
A006 仍有 `blocked/source_unknown/pending_confirmation` 合同项；当前仅允许 `popup_only/disabled_only/not_claimed` 壳层表达，不可解释为 confirmed 业务动作。

NEXT_ROLE: `C Auditor`
