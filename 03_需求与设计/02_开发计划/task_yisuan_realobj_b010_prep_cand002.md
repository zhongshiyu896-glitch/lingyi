# TASK-YISUAN-REALOBJ-B010-PREP-CAND002

## Baseline
- HEAD: `1465c5256dd83641c6d4b6cd5c1bbfc755cb89f5`
- branch: `codex/sprint4-seal`
- cached_count: `0`
- HEAD_tag_count: `0`
- git_diff_check: `PASS`

## Selected Candidate
- selected_candidate: `REALOBJ-CAND-002`
- module_scope: `BOM/款式/面辅料本地真实对象与回读闭环`
- covered_contract_ids: `["A002","A005"]`
- covered_routes:
  - `/bom/list`
  - `/bom/detail`
- route_source_locations:
  - `/bom/list` -> `06_前端/lingyi-pc/src/router/index.ts:39-41`
  - `/bom/detail` -> `06_前端/lingyi-pc/src/router/index.ts:45-47`

## Allowed Scope Status
- allowed_frontend_files:
  - `06_前端/lingyi-pc/src/views/bom/BomList.vue` (exists=true, clean=true)
  - `06_前端/lingyi-pc/src/views/bom/BomDetail.vue` (exists=true, clean=true)
- allowed_backend_support_files:
  - `07_后端/lingyi_service/app/local_dev.py` (exists=true, clean=true, read-only in B010)

## Contract Sources
- A002:
  - `04_测试与验收/测试证据/yisuan_business_shadow_capture/YISUAN_CAP_A002_business_contract_merge_20260520/yisuan_development_contract_input.json`
- A005:
  - `04_测试与验收/测试证据/yisuan_business_shadow_capture/YISUAN_CAP_A005_style_field_color_size_material_contract_20260521/style_development_input.json`

## Frozen Contract Boundary (for B011)
- local_object_model:
  - `local_bom_header`
  - `local_bom_line`
  - `local_style_color_size_material_ref`
- local_dev_endpoint_plan:
  - `GET /local-dev/bom/list?scenario_tag=<tag>`
  - `POST /local-dev/bom (test_data only)`
  - `PATCH /local-dev/bom/:id (test_data only)`
  - `GET /local-dev/bom/:id/readback?scenario_tag=<tag>`
  - `POST /local-dev/bom/:id/rollback`
- sqlite_storage_plan:
  - `local_bom_header`
  - `local_bom_line`
  - `local_style_material_map`
- key_fields_boundary:
  - A005 verified: `款号/款名/单位/面料/备注/可打样/创建人/修改人`
  - A005 partial: `颜色/尺码/吊牌价/创建时间/修改时间/设计号/纸样师`
  - A002 popup-only 数量矩阵边界维持 non-claim
- validation_rules_boundary:
  - `scenario_tag required`
  - `test_data only`
  - `seed_data default false`
  - unknown/partial 不得升级为完整 confirmed 业务逻辑
- status_rules_boundary: `VERIFIED/PARTIAL/UNKNOWN/NO-GO/BLOCKED`
- readonly_readback_rules_boundary:
  - popup-only + non-claim 保留
  - readback 必须可验证
  - rollback + zero_residual 必须可验证
- forbidden_scope:
  - 不得直接复用 sqlite 为生产库
  - 不得进入真实采购/库存联动写入
  - 不得进入 production readback/go-live/release

## Frozen B011 Evidence Requirement
- routes HTTP 200:
  - `/bom/list`
  - `/bom/detail`
- screenshots: PNG `1440x1200`
- local-dev write only
- create/update success
- local_object_id_created=true
- BOM/material line readback success
- cancel/rollback success
- zero_residual=true
- scenario_tag present
- production_write_requests=0
- erpnext_production_write_requests=0
- real_production_account_used=false
- sqlite_not_formal_database=true
- seed_data_used=false
- typecheck exit_code=0
- dev server started/stopped=true
- local_dev server started/stopped=true

## Dirty Classification
- tracked_dirty_count: `16`
- frontend_dirty_count: `3`
- backend_or_test_dirty_count: `10`
- log_control_dirty_count: `3`
- dirty_intersections: `[]`
- unknown_dirty: `[]`
- must_block_before_continue: `[]`

## Data Boundary
- data_classification: `local_real_object_test_data_only`
- test_data_used: `true` (implementation phase)
- scenario_tag_required: `true`
- rollback_required: `true`
- zero_residual_required: `true`
- seed_data_used: `false` (default)
- sqlite_not_formal_database: `true`
- sqlite_direct_reuse_for_production_forbidden: `true`
- real_inventory_finance_production_records_migrated: `false`
- real_stock_in_out_records_migrated: `false`

## Production Safety Boundary
- erpnext_production_connected: `false`
- real_production_account_used: `false`
- production_readback: `false`
- go_live: `false`
- project_completion: `false`
- remote_lifecycle_parked: `true`

## Decision
- implementation_allowed: `true`
- next_task: `TASK-YISUAN-REALOBJ-B011-IMPL-CAND002`
- prohibited_actions_confirmation: all `false` / no unauthorized action observed
- residual_risk: `low`
- NEXT_ROLE: `C Auditor`
