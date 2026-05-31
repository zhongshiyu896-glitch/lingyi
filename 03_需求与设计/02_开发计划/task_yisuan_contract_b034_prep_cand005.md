# TASK-YISUAN-CONTRACT-B034-PREP-CAND005

## 1) 基线核对
- HEAD: `e73e8d427fcc5ca03b417a31df02b9fcb276021f`
- branch: `codex/sprint4-seal`
- cached_count: `0`
- HEAD_tag_count: `0`
- git_diff_check: `PASS`

## 2) 候选冻结（继承 B001/B033）
- selected_candidate: `CONTRACT-CAND-005`
- covered_contract_ids: `["A001","A002","A003"]`
- module_scope: `库存/仓库/跨模块读回契约合并`

### routes
- `/sales-inventory/stock-ledger` -> `06_前端/lingyi-pc/src/router/index.ts:174-176`
- `/warehouse` -> `06_前端/lingyi-pc/src/router/index.ts:186-188`

### allowed_files
- `06_前端/lingyi-pc/src/views/sales_inventory/SalesInventoryStockLedger.vue`
- `06_前端/lingyi-pc/src/views/warehouse/WarehouseDashboard.vue`
- allowed_files_exist: `true`
- allowed_files_clean: `true`

### contract_sources（3 份）
- `04_测试与验收/测试证据/yisuan_business_shadow_capture/YISUAN_CAP_A001_evidence_coverage_matrix_20260520/evidence_coverage_matrix.json`
- `04_测试与验收/测试证据/yisuan_business_shadow_capture/YISUAN_CAP_A002_business_contract_merge_20260520/yisuan_development_contract_input.json`
- `04_测试与验收/测试证据/yisuan_business_shadow_capture/YISUAN_CAP_A003_ui_route_field_button_readonly_contract_20260520/ui_contract_development_input.json`
- contract_sources_exist: `true`

### optional_support_files（只读支撑）
- `07_后端/lingyi_service/app/local_dev.py`
- status: `exists=true`, `clean=true`, `mode=read_only_support_only`

## 3) 冻结的合同边界
- business_contract_summary: `库存流水、仓库摘要、跨模块 readback 提示按 A001/A002/A003 合同合并。`
- user_visible_acceptance_goal: `库存/仓库页面字段与状态标签一致，跨模块读回边界可见。`
- local_dev_support_required: `true`
- rollback_zero_residual_requirement: `mandatory_for_any_local_write_or_auto_validation`
- forbidden_scope:
  - `真实库存财务写入`
  - `production readback / remote lifecycle / go-live`

### key_fields
- A001: `VERIFIED/PARTIAL/UNKNOWN/NO-GO/BLOCKED` 状态维度保留
- A002: `stateLabels` + `UI静态证据不等同业务算法1:1` 显式非宣称
- A003: `UI壳层/路由入口/字段展示/状态标签/只读禁用文案`

### validation_rules
- `can_support_development=true` 仅代表开发输入，不代表真实业务动作已验证
- `PARTIAL/UNKNOWN/NO-GO/BLOCKED` 禁止升级为 confirmed
- `mustNotImplementActions` 只允许展示，不允许执行

### status_rules + readonly/readback
- supported_status_tags: `VERIFIED/PARTIAL/UNKNOWN/NO-GO/BLOCKED`
- unknown_blocked_boundary: `preserved=true`, `claimed_as_confirmed=false`
- disabled/readback-only: `real_action_triggered=false`
- contract_source_readback_required: `true`

## 4) B035 证据冻结要求
- routes HTTP 200:
  - `/sales-inventory/stock-ledger`
  - `/warehouse`
- PNG screenshot: `1440x1200`
- contract source readback present: `true`
- covered_contract_ids: `["A001","A002","A003"]`
- key_fields / validation_rules / status_rules / readonly_readback: `observed=true`
- partial/unknown/blocked: `preserved=true`, `claimed_as_confirmed=false`
- disabled-only/readback-only: `real_action_triggered=false`
- network/write safety:
  - `write_requests_observed_count=0`
  - `production_write_requests=0`
  - `erpnext_production_write_requests=0`
  - `real_production_account_used=false`
- `real_business_object_created=false`
- `linked_calculation_enabled=false`
- typecheck: `exit_code=0`
- dev server: `started/stopped=true`

## 5) dirty 分类（只读）
- tracked_dirty_count: `16`
- frontend_dirty_count: `3`
- backend_or_test_dirty_count: `10`
- log_control_dirty_count: `3`
- dirty_intersections: `[]`
- unknown_dirty: `[]`
- must_block_before_continue: `[]`

## 6) 数据边界与结论
- data_classification: `contract_merge_no_real_object`
- test_data_used: `false`（若 B035 需要测试数据，必须 `scenario_tag + rollback + zero_residual`）
- seed_data_used: `false`
- sqlite_not_formal_database: `true`
- sqlite_direct_reuse_for_production_forbidden: `true`
- erpnext_production_connected: `false`
- real_production_account_used: `false`
- production_readback: `false`
- go_live: `false`
- project_completion: `false`
- remote_lifecycle_parked: `true`
- prior_A005_A006_unknown_or_blocked_claimed_as_confirmed: `false`

## 7) 执行授权判定
- implementation_allowed: `true`
- next_task: `TASK-YISUAN-CONTRACT-B035-IMPL-CAND005`
- residual_risk: `B035 必须严格锁定 2 个 allowed 前端文件，并持续 zero-write + unknown/blocked 非 confirmed。`
