STATUS: DONE
TASK_ID: TASK-MVP-B018-PREP
ROLE: B Engineer

SUMMARY:
- head: 5c8cef6d9bcc9e3d7fbf7443ae6bdbc2fd1d142a
- branch: codex/sprint4-seal
- cached_empty: true
- selected_candidate: MVP-CAND-003
- module: 物料开发
- routes:
  - /bom/list
  - /bom/detail
- prep_only: true
- next_task: TASK-MVP-B019-IMPL

BOUNDARY:
- allowed_files:
  - 06_前端/lingyi-pc/src/views/bom/BomList.vue
  - 06_前端/lingyi-pc/src/views/bom/BomDetail.vue
- optional_support_allowed_files:
  - 07_后端/lingyi_service/app/local_dev.py
- local_dev_py_status:
  - exists: true
  - tracked: true
  - clean: true
  - gitignored: false
  - support_role: local-dev/sqlite/scenario_tag only
  - reused_support: false
  - needs_bom_local_endpoint_extension_for_b019: true
- route_source_locations:
  - /bom/list -> 06_前端/lingyi-pc/src/router/index.ts:39
  - /bom/detail -> 06_前端/lingyi-pc/src/router/index.ts:45
- key_fields_required:
  - 款式: 款式编号, 款式名称, 季节/品类, 客户, 状态
  - BOM 主信息: BOM 编号, 版本, 适用款式, 生效状态, 备注
  - 面料明细: 物料编码, 物料名称, 颜色, 单位, 单耗, 损耗率
  - 辅料明细: 物料编码, 物料名称, 规格, 单位, 用量, 默认供应商
  - 绑定关系: 款式 -> BOM, BOM -> 面料, BOM -> 辅料
- query_flow_required:
  - keyword 查询
  - 款式/客户筛选
  - BOM 状态筛选
  - 面辅料类别筛选
  - 列表选择后进入详情
  - 查询结果必须影响可见列表或详情状态
- local_write_loop_design:
  - 新增或更新一条 BOM 本地草稿
  - 绑定至少 1 条面料与 1 条辅料
  - save / cancel / readback / rollback / zero_residual
  - scenario_tag 必填
  - storage=local-dev/sqlite/scenario_tag
  - production_write_forbidden=true
  - erpnext_production_write_forbidden=true
  - real_production_account_forbidden=true
- dom_anchors:
  - mvp-bom-list-query-filter
  - mvp-bom-style-binding
  - mvp-bom-master-card
  - mvp-bom-fabric-line
  - mvp-bom-trim-line
  - mvp-bom-local-draft
  - mvp-bom-local-save
  - mvp-bom-local-cancel
  - mvp-bom-local-readback
  - mvp-bom-rollback-zero-residual
- evidence_requirement:
  - routes: /bom/list HTTP 200, /bom/detail HTTP 200
  - screenshots: /bom/list PNG 1440x1200, /bom/detail PNG 1440x1200
  - dom_anchors_observed: 10/10
  - local_write_loop: scenario_tag, save_success, draft_id_created, fabric_line_saved, trim_line_saved, cancel_success, readback_success, rollback_success, zero_residual_success, residual_records_after_rollback=0
  - data_boundary: data_classification=test_data, seed_data_used=false, sqlite_not_formal_database=true, sqlite_direct_reuse_for_production_forbidden=true
  - network_write: production_write_requests=0, erpnext_production_write_requests=0, real_production_account_used=false, auth_401_on_local_sqlite_write_loop=false
  - typecheck: npm run typecheck @ 06_前端/lingyi-pc, exit_code=0

DATA_BOUNDARY:
- data_classification_default: test_data
- test_data_used_default: true
- seed_data_used_default: false
- sqlite_not_formal_database: true
- sqlite_direct_reuse_for_production_forbidden: true
- future_seed_data_export_migration_required_if_used: true

DIRTY:
- dirty_tracked_count: 19
- frontend_dirty_count: 6
- backend_dirty_count: 10
- log_control_dirty_count: 3
- dirty_intersections: []
- unknown_dirty: []
- must_block_before_continue: []

CHECKS:
- git_diff_check: PASS
- product_code_changed=false
- validation_rerun=false
- staged_area_empty=true
- outputs_unstaged=true

RESIDUAL_RISK:
- local_dev.py remains local-dev support only
- seed_data boundary must be carried into B019+
- remote_lifecycle_parked=true
- production_readback=false
- go_live=false
- project_completion=false

NEXT_RECOMMENDED_TASK:
- TASK-MVP-B019-IMPL
