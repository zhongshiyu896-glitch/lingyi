STATUS: DONE
TASK_ID: TASK-MVP-B040-PREP
ROLE: B Engineer

SUMMARY:
- head: 5d4220f04c909e9a6d8189b3491630d6e575e1d7
- branch: codex/sprint4-seal
- cached_empty: true
- selected_candidate: MVP-CAND-005
- module: 物料采购
- routes:
  - /materialPurchase/materialPurchaseProcess
  - /subcontract/list?parity=material-purchase
  - /subcontract/detail
- prep_only: true
- next_task: TASK-MVP-B041-IMPL

BOUNDARY:
- allowed_files:
  - 06_前端/lingyi-pc/src/views/subcontract/SubcontractOrderList.vue
  - 06_前端/lingyi-pc/src/views/subcontract/SubcontractOrderDetail.vue
- optional_support_allowed_files:
  - 07_后端/lingyi_service/app/local_dev.py
- local_dev_py_status:
  - exists=true
  - tracked=true
  - gitignored=false
  - clean=true
  - support_scope=local-dev/sqlite/scenario_tag only
  - support_mode_for_b041=support_allowed_file_frozen_for_possible_extension
- route_source_locations:
  - 06_前端/lingyi-pc/src/router/index.ts:269-270
  - 06_前端/lingyi-pc/src/router/index.ts:63
  - 06_前端/lingyi-pc/src/router/index.ts:69
- key_fields_required:
  - 外协/采购单主信息: 单据号, 供应商/加工厂, 单据类型, 业务日期, 状态
  - 物料明细: 物料编码, 物料名称, 颜色/规格, 单位, 需求数量, 采购/外协数量
  - 发料/回料: 发料数量, 回料数量, 差异数量, 操作状态
  - 验货/结算预览: 验收数量, 不良数量, 结算数量, 预估金额
  - 关联: 供应商/加工厂, 物料, 前置单据, 本地草稿
- query_flow_required:
  - keyword 查询
  - 供应商/加工厂筛选
  - 单据状态筛选
  - 物料类别筛选
  - materialPurchase parity 路由进入采购视角
  - 列表选择后进入详情
  - 查询结果必须影响可见列表或详情状态
- local_write_loop_design:
  - 新增或更新一条采购/外协前置单据本地草稿
  - 至少保存 1 条物料明细
  - 保存发料/回料或验货/结算预览中的至少一个本地状态
  - save/cancel/readback/rollback/zero_residual
  - scenario_tag_required=true
  - storage=local-dev/sqlite/scenario_tag
  - production_write_forbidden=true
  - erpnext_production_write_forbidden=true
  - real_production_account_forbidden=true
- dom_anchors:
  - mvp-purchase-list-query
  - mvp-purchase-parity-material
  - mvp-purchase-order-master
  - mvp-purchase-material-line
  - mvp-purchase-issue-return
  - mvp-purchase-inspection-settlement
  - mvp-purchase-local-draft
  - mvp-purchase-local-save
  - mvp-purchase-local-cancel
  - mvp-purchase-local-readback
  - mvp-purchase-rollback-zero-residual
  - mvp-purchase-production-safety
- evidence_requirement:
  - routes_http_200:
    - /materialPurchase/materialPurchaseProcess (final_path=/subcontract/list?parity=material-purchase)
    - /subcontract/list?parity=material-purchase
    - /subcontract/detail
  - screenshots_1440x1200:
    - /materialPurchase/materialPurchaseProcess
    - /subcontract/list?parity=material-purchase
    - /subcontract/detail
  - dom_anchors_observed=12/12
  - local_write_loop: scenario_tag/save/draft_id/material_line/issue_return_or_inspection/cancel/readback/rollback/zero_residual/residual=0
  - data_boundary: test_data, seed_data_used=false, sqlite_not_formal_database=true, sqlite_direct_reuse_for_production_forbidden=true
  - network_write: production_write_requests=0, erpnext_production_write_requests=0, real_production_account_used=false, auth_401_on_local_sqlite_write_loop=false
  - typecheck: npm run typecheck (workdir=06_前端/lingyi-pc, exit_code=0)

DATA_BOUNDARY:
- data_classification_default: test_data
- test_data_used_default: true
- seed_data_used_default: false
- sqlite_not_formal_database: true
- sqlite_direct_reuse_for_production_forbidden: true
- real_purchase_subcontract_inventory_finance_data_migration_forbidden: true
- future_seed_data_export_migration_required_if_used: true

DIRTY:
- dirty_tracked_count: 16
- frontend_dirty_count: 3
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
- seed_data boundary must be carried into B041+
- remote_lifecycle_parked=true
- production_readback=false
- go_live=false
- project_completion=false

NEXT_RECOMMENDED_TASK:
- TASK-MVP-B041-IMPL
