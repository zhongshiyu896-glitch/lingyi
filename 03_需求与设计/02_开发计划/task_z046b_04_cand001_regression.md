# TASK-Z046B-04-REGRESSION-CAND001 回归报告

## 1) Scope confirmation
- 任务类型：regression-only（未修改任何产品代码，未 stage/commit）。
- 仓库：`/Users/hh/Desktop/领意服装管理系统`
- 分支：`codex/sprint4-seal`
- HEAD：`62d7bb349204e4101afe4ad2ac242e4ffcac7301`（与基线一致）
- staged area：空
- HEAD tag：空
- `git diff --check`：PASS

## 2) Evidence check
- 候选产品 diff 仍仅：
  - `06_前端/lingyi-pc/src/views/reports/ReportCatalog.vue`
  - `06_前端/lingyi-pc/src/router/index.ts`
- 禁入路径核对：
  - `api/report.ts` touched=false
  - 后端新增 API=false
  - 真实写动作新增=false
- 5 条路由复核：
  - `/financial/financialReport/customerReconciliationReport` -> HTTP 200
  - `/financial/financialProcess` -> HTTP 200
  - `/finance/bank-flow` -> HTTP 200
  - `/reportManage/collaborationReport/factoryProductStockReport` -> HTTP 200
  - `/reports/catalog` -> HTTP 200
- final_path 回归结果：
  - 全部回到 `/reports/catalog?...`
  - 均保留 Z046 readback/guard 参数：
    - `z046_source_grouping`
    - `z046_download_disabled_hint`
    - `z046_export_lock_tooltip`
    - `z046_final_route_readback`
    - `z046_guarded_matrix_scope`
- screenshot：
  - `04_测试与验收/测试证据/z046_cand001_report_catalog_interaction_regression/z046_cand001_reports_catalog_regression_1440x1200.png`
  - PNG，`1440x1200`
- DOM anchors：
  - required 8 项 observed=8/8
- guarded readonly：
  - 覆盖 4/4：报表导出、财务下载、协同下载、明细导出
  - 顶层字段：
    - `dataReadonlyBoundary=true`
    - `dataWriteRequestSuccessAllowed=false`
    - `dataRealWriteActionAdded=false`
- network/write：
  - `auth_401_count=25`（仅作为 readonly fallback risk）
  - `write_requests_observed_count=0`
  - `write_request_success_observed=false`
  - `write_request_success_allowed=false`
- typecheck：
  - command=`npm run typecheck`
  - workdir=`06_前端/lingyi-pc`
  - exit_code=`0`
- dev server：
  - started=true
  - actual_url=`http://127.0.0.1:5178/`
  - stopped=true

## 3) Direction compliance
- `mainline_or_auxiliary=mainline`
- `user_visible_frontend_improvement=true`
- `interaction_experience_improvement=true`
- `one_to_one_ui_contract_focus=true`
- `readonly_guard_role=supporting`
- `candidate_direction_valid=true`

## 4) Residual risk
- Z046-CAND-001 B03/B04 `auth_401_count=25/25` readonly fallback risk
- Z045-CAND-005 `auth_401_count=5/5` readonly fallback risk
- Z045-CAND-004 `auth_401_count=1/1` readonly fallback risk
- Z045-CAND-003 `auth_401_count=1/1` readonly fallback risk
- Z045-CAND-002 `auth_401_count=25/25` readonly fallback risk
- Z044/Z043/Z042-Z038 fallback risks
- `guarded_readonly_not_write_success=true`
- prior non-allowlisted summary/metadata 继续排除
- Z034 residual、后端、runtime/cache、remote/prod-go-live 继续排除
- `remote_lifecycle_parked=true`
- `push_tag_pr_release=false`
- `production_readback=false`
- `go_live=false`
- `project_completion=false`

## 5) Next
- `next_task=TASK-Z046B-05-LEDGER-CAND001`
