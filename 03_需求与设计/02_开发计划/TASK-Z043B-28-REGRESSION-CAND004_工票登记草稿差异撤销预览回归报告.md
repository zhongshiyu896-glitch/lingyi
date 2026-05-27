# TASK-Z043B-28-REGRESSION-CAND004 回归报告

## 任务范围

- ROLE: B Engineer
- 目标: 对 Z043-CAND-004 做 regression-only 复核。
- code_modified_in_this_task: false
- 产品代码未修改；未 stage、未 commit、未执行远端生命周期动作。

## 基线核对

- head: 20e12d99a7a2c51bd7928c6c4e9809e134a59002
- branch: codex/sprint4-seal
- cached_empty: true
- head_tag_empty: true
- worktree_check_pass: true
- changed_files_observed:
  - 06_前端/lingyi-pc/src/views/workshop/WorkshopTicketRegister.vue
- allowed_files_only: true
- api_workshop_touched: false

## 运行态复核

- route: /workshop/tickets/register
- http_status: 200
- final_path: /workshop/tickets/register
- screenshot: 04_测试与验收/测试证据/z043_cand004_register_draft_cancel_preview_regression/workshop_ticket_register_z043_draft_cancel_preview_regression.png
- screenshot_png_dimensions: 1440x1200

## DOM Anchors

- observed_count: 8
- all_observed: true
- observed:
  - workshop-ticket-register-page
  - workshop-ticket-register-form
  - workshop-ticket-register-readonly-draft-preview
  - workshop-ticket-register-validation-hint
  - z043-register-field-diff-summary
  - z043-register-cancel-preview
  - z043-register-readonly-confirm-chain
  - z043-register-return-source-readback

## Guarded / Readonly State

- guarded_entries_covered:
  - 提交登记
  - 提交撤销
  - 只读降级确认
- dataReadonlyBoundary: true
- dataWriteRequestSuccessAllowed: false
- dataRealWriteActionAdded: false
- guarded_readonly_not_write_success: true

## Network / Write Observation

- auth_401_count: 1
- runtime_readonly_fallback_risk: true
- write_requests_observed_count: 0
- write_request_success_observed: false
- write_request_success_allowed: false
- auth 401 仅记录为 readonly fallback risk，未解释为权限通过或写成功。

## Typecheck

- command: npm run typecheck
- workdir: 06_前端/lingyi-pc
- exit_code: 0

## 风险字段保留

- CAND004 B27 auth_401_count=1 readonly fallback risk
- CAND004 B28 auth_401_count=1 readonly fallback risk
- CAND003 B19/B20 auth_401_count=1/1 readonly fallback risk
- CAND002 B11/B12 auth_401_count=30/30 readonly fallback risk
- Z043-CAND-001 B03/B04 auth_401_count=2/2 readonly fallback risk
- prior non-allowlisted summary/metadata 后续继续排除
- Z042/Z041/Z040/Z039/Z038 fallback risks
- guarded_readonly_not_write_success=true
- B28 shell_wrapper_anomaly
- Z033 skipped_only
- Z035 screenshot_missing_risk
- remote_lifecycle_parked=true
- push_tag_pr_release=false
- production_readback=false
- go_live=false
- project_completion=false

## 禁止动作确认

- backend_api_added: false
- real_write_action_added: false
- read_only_boundary_preserved: true
- dev_server_started: true
- dev_server_stopped: true
- stage_performed: false
- commit_performed: false
- remote_lifecycle_released: false
- next_task: TASK-Z043B-29-LEDGER-CAND004
