# TASK-216A_第二批A11Y最小修复实现与真实浏览器回归报告

## CURRENT_CONTROL_PLANE
- STATUS: READY_FOR_BUILD
- TASK_ID: TASK-216A
- ROLE: B Engineer
- 分支: `codex/sprint4-seal`

## TASK_215A_PASS_ANCHOR
- 上游锚点: `TASK-215A` 已由 C Auditor 审计 PASS。
- 本轮依据: 第二批 deferred 候选冻结为 5 个白名单文件、98 条 issue。

## SOURCE_DEFERRED_SCOPE
- source_deferred: `98`
- by_file:
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/warehouse/WarehouseDashboard.vue`: `39`
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/bom/BomDetail.vue`: `27`
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/system/PermissionGovernance.vue`: `27`
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/quality/QualityInspectionDetail.vue`: `3`
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/workshop/WorkshopTicketRegister.vue`: `2`
- by_issue_type:
  - `table_missing_empty_text`: `87`
  - `control_missing_placeholder_or_label`: `11`
- source_artifacts:
  - `/tmp/task210a_a11y_after_scan.json`
  - `/tmp/task210a_a11y_after_scan.tsv`

## IMPLEMENTATION_SUMMARY
- 仅在白名单文件内执行展示层最小 A11Y 修复：
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/bom/BomDetail.vue`
    - 为 6 处 `el-input-number` 补 `aria-label`（单件用量、损耗率、工序序号、本厂工价、外发单价、订单数量）。
    - 展开结果表格显式挂载 `empty-text`。
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/quality/QualityInspectionDetail.vue`
    - 更新备注输入框补 `aria-label`。
    - 保存按钮补 `aria-label`。
    - 严重度选择器补 `aria-label`。
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/workshop/WorkshopTicketRegister.vue`
    - 工作日期选择器补 `aria-label`。
    - 来源下拉补 `aria-label`。
- 未改业务逻辑、权限逻辑、API 请求、路由、store、数据结构。

## A11Y_FIX_RESULT
- source_deferred: `98`
- fixed_count: `11`
- remaining_deferred_count: `0`
- false_positive_or_deferred_count: `87`
- after_scan_json: `/tmp/task216a_a11y_after_scan.json`
- after_scan_tsv: `/tmp/task216a_a11y_after_scan.tsv`
- by_issue_type:
  - `table_missing_empty_text`: `FIXED=2 / FALSE_POSITIVE=85 / DEFERRED=0`
  - `control_missing_placeholder_or_label`: `FIXED=9 / FALSE_POSITIVE=2 / DEFERRED=0`

## DEFERRED_OR_FALSE_POSITIVE
- `87` 条 `table_missing_empty_text` 归因为扫描规则命中 `el-table-column` 列定义而非 `el-table` 容器，按 `FALSE_POSITIVE` 冻结。
- `2` 条 `control_missing_placeholder_or_label` 归因为 `el-option` 项定义，非输入控件缺失 placeholder 场景，按 `FALSE_POSITIVE` 冻结。

## BROWSER_REGRESSION_RESULT
- run_id: `20260427033841`
- base_url: `http://127.0.0.1:5174`
- result_json: `/tmp/task216a_browser_results.json`
- sampled_routes:
  - `/warehouse`
  - `/bom/detail`
  - `/permissions/governance`
  - `/quality/inspections/detail`
  - `/workshop/tickets/register`
- passed_samples: `5`
- failed_samples: `0`
- screenshots:
  - `/tmp/task216a_20260427033841_01.png`
  - `/tmp/task216a_20260427033841_02.png`
  - `/tmp/task216a_20260427033841_03.png`
  - `/tmp/task216a_20260427033841_04.png`
  - `/tmp/task216a_20260427033841_05.png`

## NETWORK_NO_WRITE_RESULT
- write_request_count: `0`
- console_errors_total: `0`
- page_errors_total: `0`
- network_4xx_5xx_total: `0`

## VALIDATION
- git status precheck -> PASS
- staged area empty -> PASS
- npm run typecheck -> PASS
- npm run verify -> PASS
- A11Y after-scan generated -> PASS
- Playwright sampled regression -> PASS
- 5174 lifecycle（本轮启动并停止）-> PASS
- git diff --check（限定允许文件）-> PASS

## FORBIDDEN_ACTIONS
- git add/commit/push/PR/merge/close/tag/release: NO
- cleanup/reset/restore/clean/delete: NO
- backend/CCC/control-plane edits: NO
- GitHub management config: NO
- production/ERPNext actions: NO
- parked blockers released: NO
- write/download/print business actions clicked: NO

## RISK_NOTES
- 本轮产出的 `false_positive` 主要来自静态规则对 `el-table-column` 的行级误命中，后续若继续批量修复建议先收敛扫描规则再扩批。
- `TASK-188A / TASK-152A / TASK-090I / TASK-110B` 维持 parked，不在本轮处理范围。
