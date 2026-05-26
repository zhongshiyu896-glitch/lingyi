# TASK-Z037B-10-PREP CAND002 边界冻结报告

## 基本结论

- task_id: TASK-Z037B-10-PREP
- role: B Engineer
- source_task: TASK-Z037B-09-PREP
- candidate_id: Z037-CAND-002
- title: BOM 主列表与物料目录只读可见流
- page_scope: BOM / 物料目录
- read_only: true
- backend_allowed: false
- next_task: TASK-Z037B-11-IMPL
- run_this_task: false

## Routes

- /bom/list
- /material/materialFabric
- /goodsPlan/materialSamples
- /goodsPlan/goodsPlanProcess
- /product/product

## Allowed Scope

- 06_前端/lingyi-pc/src/views/bom/BomList.vue
- 06_前端/lingyi-pc/src/api/bom.ts
- allowed_files_exist: true
- allowed_files_dirty: false

## Forbidden Scope

- 06_前端/lingyi-pc/src/views/bom/BomDetail.vue
- 07_后端
- candidate pool
- historical dirty
- log/control dirty
- Z034 residual artifacts
- Z035/Z036 committed product paths
- runtime/cache/test-results
- remote lifecycle / production readback / go-live
- bom_detail_excluded: true

## Route Static Check

- /bom/list: 06_前端/lingyi-pc/src/router/index.ts routes to 06_前端/lingyi-pc/src/views/bom/BomList.vue
- /material/materialFabric: redirects to /bom/list with parity=material-fabric
- /goodsPlan/materialSamples: redirects to /bom/list with parity=goodsplan-material-samples
- /goodsPlan/goodsPlanProcess: redirects to /bom/list with parity=goodsplan-material-samples
- /product/product: redirects to /bom/list with parity=product-style
- routes_located: true

## Required Anchors

- bom-main-list-section
- bom-main-list-filters
- bom-main-table
- bom-fabric-section
- bom-accessories-section
- bom-processing-type-section
- bom-main-create-guarded-button
- bom-readonly-write-guard

## Guard Required

- 新建 BOM
- 选用
- 上传
- 导出
- 详情抽屉写入口

## B11 Evidence Requirement

- capture /bom/list screenshot
- capture material/product parity route evidence
- capture runtime DOM anchors
- capture guarded write-control state
- capture write request observation
- pure_static_fallback_allowed: false

## Scope Check

- intersections_with_historical_dirty: []
- intersections_with_log_control_dirty: []
- intersections_with_residual_artifacts: []
- intersections_with_z035_z036_committed_product_paths: []
- unknown_dirty: []
- must_block_before_continue: []

## 风险字段保留

- prior_readonly_fallback_risks: true
- guarded_readonly_not_write_success: true
- B28 shell_wrapper_anomaly: true
- Z033 skipped_only: true
- Z035 screenshot_missing_risk: true
- remote_lifecycle_parked: true
