# TASK-YISUAN-CONTRACT-B010-PREP-CAND002

- ROLE: `B Engineer`
- HEAD: `a58fb48689688ed02870667a22eb2de375722ac1`
- branch: `codex/sprint4-seal`
- cached_count: `0`
- HEAD_tag_count: `0`
- git_diff_check: `PASS`

## 选中候选

- selected_candidate: `CONTRACT-CAND-002`
- covered_contract_ids: `["A002","A005"]`
- module_scope: `物料/BOM 契约合并`

## routes / route_source_locations

- routes:
  - `/bom/list`
  - `/bom/detail`
- route_source_locations:
  - `/bom/list` -> `06_前端/lingyi-pc/src/router/index.ts:39-41` (direct)
  - `/bom/detail` -> `06_前端/lingyi-pc/src/router/index.ts:45-47` (direct)

## allowed_files_status

- allowed_files:
  - `06_前端/lingyi-pc/src/views/bom/BomList.vue`
  - `06_前端/lingyi-pc/src/views/bom/BomDetail.vue`
- allowed_files_exist: `true`
- allowed_files_clean: `true`

## contract_sources_status

- contract_sources:
  - `04_测试与验收/测试证据/yisuan_business_shadow_capture/YISUAN_CAP_A002_business_contract_merge_20260520/yisuan_development_contract_input.json`
  - `04_测试与验收/测试证据/yisuan_business_shadow_capture/YISUAN_CAP_A005_style_field_color_size_material_contract_20260521/style_development_input.json`
- contract_sources_exist: `true`

## optional_support_status

- optional_support_files:
  - `07_后端/lingyi_service/app/local_dev.py`
- status: `exists=true, clean=true`
- support mode: `local-dev support only`
- B010 backend modify authorization: `false`

## frozen_contract_boundary

- business_contract_summary:
  - `BOM 字段、状态、款式颜色尺码与物料引用按 A002/A005 输入合并`
- key_fields:
  - A005 verified: `款号, 款名, 单位, 面料, 备注, 可打样, 创建人, 修改人`
  - A005 partial: `颜色, 尺码, 吊牌价, 创建时间, 修改时间, 设计号, 纸样师`
  - A002 contract ids:
    - `YISUAN-DEV-CONTRACT-baseline_reference`
    - `YISUAN-DEV-CONTRACT-base_objects_reference_contract`
    - `YISUAN-DEV-CONTRACT-style_min_create_readback_contract`
    - `YISUAN-DEV-CONTRACT-quote_draft_min_save_readback_contract`
    - `YISUAN-DEV-CONTRACT-order_qty_matrix_popup_only_contract`
    - `YISUAN-DEV-CONTRACT-ui_route_field_button_readonly_shell_contract`
- validation_rules:
  - A005 unknown fields 不得宣称已实现：
    - `完整颜色尺码矩阵规则, 设计号生成/录入规则, 纸样师选择规则, 价格规则`
  - A005 blocked actions 不得启用：
    - `样板生成/生成样衣/确定推送, 提交, 审核, 反审核, 删除, 作废, BOM, 生产制单, 加工单, 库存入库, 库存出库, 领料, 完工, 财务收付款, 报价/订单联动`
- status_rules:
  - A002 state labels: `VERIFIED, PARTIAL, UNKNOWN, NO-GO, BLOCKED`
  - quote draft status reference: `待提交`
- readonly/readback rules:
  - `contract_source_readback_present=true`
  - explicit non-claim:
    - `UI 静态证据不等同业务算法 1:1`
    - `报价提交未验证 / 审核未验证 / 转订单未验证`
    - `mainOrderSaveClicked=false / orderCreated=false / orderNumberGenerated=false`
- forbidden_scope (继承):
  - `生产对象与库存财务联动计算`
  - `production readback / remote lifecycle / go-live`

## frozen_evidence_requirement (B011)

- routes HTTP 200: `/bom/list`, `/bom/detail`
- final_path: `N/A`
- screenshots: `PNG 1440x1200`
- contract source readback present
- covered_contract_ids: `["A002","A005"]`
- key_fields / validation_rules / status_rules / readonly_readback rules observed
- `write_requests_observed_count=0`
- `production_write_requests=0`
- `erpnext_production_write_requests=0`
- `real_production_account_used=false`
- `real_business_object_created=false`
- `linked_calculation_enabled=false`
- `typecheck_exit_code=0`
- `dev_server_started_stopped=true`

## dirty_classification

- tracked_dirty_count: `16`
- frontend_dirty_count: `3`
- backend_or_test_dirty_count: `10`
- log_control_dirty_count: `3`
- dirty_intersections: `[]`
- unknown_dirty: `[]`
- must_block_before_continue: `[]`

## data_boundary

- phase: `YISUAN-A001-A006-CONTRACT-MERGE-MAINLINE`
- data_classification: `contract_merge_no_real_object`
- test_data_used: `false`
- if needed later: `scenario_tag + rollback + zero_residual`
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

## prohibited_actions_confirmation

- code_modified: `false`
- browser/typecheck/pytest rerun: `false`
- stage/commit/amend: `false`
- push/PR/tag/release: `false`
- reset/restore/clean/delete: `false`
- ERPNext production / 真实生产账号: `false`
- real_business_object_created: `false`
- linked_calculation_enabled: `false`

- implementation_allowed: `true`
- next_task: `TASK-YISUAN-CONTRACT-B011-IMPL-CAND002`
- residual_risk: `A005 仍含 partial/unknown 字段，B011 必须严格保持 non-claim 与 no-write。`

NEXT_ROLE: `C Auditor`
