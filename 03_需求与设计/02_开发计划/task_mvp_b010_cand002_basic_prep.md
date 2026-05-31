# TASK-MVP-B010-PREP

## Summary
- head: `bacbc355e58b8f0fbf8a847f3775729927b9ad8c`
- branch: `codex/sprint4-seal`
- cached_empty: `true`
- selected_candidate: `MVP-CAND-002`
- module: `基础资料`
- routes:
  - `/sales-inventory/references`
  - `/foundation/warehouse`
- prep_only: `true`
- next_task: `TASK-MVP-B011-IMPL`

## Boundary
- allowed_files:
  - `06_前端/lingyi-pc/src/views/sales_inventory/SalesInventoryReferenceList.vue`
  - `06_前端/lingyi-pc/src/views/warehouse/WarehouseDashboard.vue`
- optional_support_allowed_files:
  - `07_后端/lingyi_service/app/local_dev.py`
- local_dev_py_status:
  - exists=true
  - tracked=true
  - clean=true
  - gitignored=false
  - reused_support=true
- route_source_locations:
  - `06_前端/lingyi-pc/src/router/index.ts:180-183` (`/sales-inventory/references`)
  - `06_前端/lingyi-pc/src/router/index.ts:233-234` (`/foundation/warehouse -> /warehouse?parity=foundation-warehouse`)
  - `06_前端/lingyi-pc/src/router/index.ts:186-189` (`/warehouse`)
- contract_source: `ui_business_contract_source`
- key_fields_required:
  - 客户: 客户编码、客户名称、联系人、电话、状态
  - 仓库: 仓库编码、仓库名称、仓库类型、仓库地址、启用状态
  - 供应商: 供应商编码、供应商名称、物料类别、联系方式、状态
  - 加工厂: 加工厂编码、加工厂名称、工序能力、联系方式、状态
  - 物料引用: 物料编码、物料名称、类别、单位、默认仓库
- query_flow_required:
  - keyword 查询
  - 类型/类别筛选
  - 状态筛选
  - 仓库/物料引用联动筛选
  - 查询结果必须影响可见列表或状态卡
- local_write_loop_design:
  - 新增或更新一条基础资料本地草稿
  - save / cancel / readback / rollback / zero_residual
  - scenario_tag required
  - storage=local-dev/sqlite/scenario_tag
  - production_write_forbidden=true
  - erpnext_production_write_forbidden=true
  - real_production_account_forbidden=true
- dom_anchors:
  - mvp-basic-reference-tabs
  - mvp-basic-reference-query-filter
  - mvp-basic-customer-reference
  - mvp-basic-supplier-reference
  - mvp-basic-factory-reference
  - mvp-basic-material-reference
  - mvp-basic-warehouse-card
  - mvp-basic-local-draft
  - mvp-basic-local-save-cancel-readback
  - mvp-basic-rollback-zero-residual
- evidence_requirement:
  - `/sales-inventory/references` HTTP 200
  - `/foundation/warehouse` HTTP 200
  - 两张 PNG 1440x1200
  - DOM anchors observed=10/10
  - local write loop success (save/cancel/readback/rollback/zero_residual + residual=0)
  - network: production_write_requests=0, erpnext_production_write_requests=0, real_production_account_used=false, auth_401_on_local_sqlite_write_loop=false
  - typecheck: `npm run typecheck` @ `06_前端/lingyi-pc`, exit_code=0

## Dirty
- dirty_tracked_count: `19`
- frontend_dirty_count: `6`
- backend_dirty_count: `10`
- log_control_dirty_count: `3`
- dirty_intersections: `[]`
- unknown_dirty: `[]`
- must_block_before_continue: `[]`

## Checks
- git_diff_check: `PASS`
- product_code_changed: `false`
- validation_rerun: `false`
- staged_area_empty: `true`
- outputs_unstaged: `true`

## Residual Risk
- local_dev.py remains local-dev support only
- remote_lifecycle_parked=true
- production_readback=false
- go_live=false
- project_completion=false
