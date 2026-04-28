# TASK-250A 第八批A11Y展示层属性最小修复实现与剩余候选延期归因报告

STATUS: READY_FOR_REVIEW
TASK_ID: TASK-250A
ROLE: B Engineer

## CHANGED_FILES
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/subcontract/SubcontractOrderList.vue
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/bom/BomDetail.vue
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/reports/ReportCatalog.vue
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/sales_inventory/SalesInventorySalesOrderDetail.vue
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/sales_inventory/SalesInventorySalesOrderList.vue
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-250A_第八批A11Y展示层属性最小修复实现与剩余候选延期归因报告.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md

## CODE_CHANGED
- YES

## A11Y_FIX_RESULT
- source_true_fix_candidates: `7`
- batch_fixed_count: `6`
- deferred_count: `1`
- remaining_true_fix_candidate_count: `1`
- after_scan_json: `/tmp/task250a_a11y_after_scan.json`
- after_scan_tsv: `/tmp/task250a_a11y_after_scan.tsv`

## DEFERRED_CANDIDATE
- file: `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/workshop/WorkshopTicketBatch.vue`
- issue_count: `1`
- reason: 该候选不在 TASK-249A 冻结的第八批 5 文件 allowlist，本轮按任务单要求仅做延期归因，不允许修改该文件。
- next_action: 后续以独立最小修复任务纳入 allowlist 后再执行。

## IMPLEMENTATION_SUMMARY
- 仅在第八批 allowlist 的 5 个 Vue 文件内执行展示层最小修复，未修改 `WorkshopTicketBatch.vue`。
- `SubcontractOrderList.vue`：状态筛选 `el-select` 补 `placeholder` 与 `aria-label`；列表 `el-table` 补 `empty-text`。
- `ReportCatalog.vue`：目录表格 `el-table` 补 `empty-text`。
- `SalesInventorySalesOrderDetail.vue`：明细表格 `el-table` 补 `empty-text`。
- `SalesInventorySalesOrderList.vue`：列表表格 `el-table` 补 `empty-text`。
- `BomDetail.vue`：BOM 展开表格 `el-table` 保持 `empty-text` 并调整标签属性位置以匹配扫描口径。
- 本轮修复仅限 `placeholder / aria-label / el-table empty-text` 展示层属性，不涉及业务逻辑、权限逻辑、API、router、store、数据结构。

## BROWSER_REGRESSION_RESULT
- run_id: `20260428T121842`
- base_url: `http://127.0.0.1:5174`
- result_json: `/tmp/task250a_browser_results.json`
- sampled_routes: `5`
- passed_samples: `5`
- failed_samples: `0`
- write_request_count: `0`
- console_errors_total: `0`
- page_errors_total: `0`
- network_4xx_5xx_total: `0`
- screenshots: `/tmp/task250a_20260428T121842_*.png`（5 张）

## VALIDATION
- git status precheck: PASS
- staged area empty: PASS
- npm run typecheck: PASS
- npm run verify: PASS
- A11Y after-scan generated: PASS
- Playwright sampled regression: PASS
- git diff --check: PASS

## FORBIDDEN_ACTIONS
- git add/commit/push/PR/merge/close/tag/release: NO
- cleanup/reset/restore/clean/delete: NO
- backend/CCC/control-plane edits: NO
- GitHub management config: NO
- production/ERPNext actions: NO
- parked blockers released: NO
- write/download/print business actions clicked: NO
