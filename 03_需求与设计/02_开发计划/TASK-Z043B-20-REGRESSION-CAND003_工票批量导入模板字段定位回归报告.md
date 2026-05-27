# TASK-Z043B-20-REGRESSION-CAND003 工票批量导入模板字段定位回归报告

## 回归结论

- task_id: TASK-Z043B-20-REGRESSION-CAND003
- role: B Engineer
- code_modified_in_this_task: false
- changed_files_observed:
  - 06_前端/lingyi-pc/src/views/workshop/WorkshopTicketBatch.vue
- allowed_files_only: true
- api_workshop_touched: false
- backend_api_added: false
- real_write_action_added: false
- read_only_boundary_preserved: true
- stage_performed: false
- commit_performed: false
- remote_lifecycle_released: false

## Regression Runtime Evidence

- route: /workshop/tickets/batch
- route_http_status: 200
- screenshot: 04_测试与验收/测试证据/z043_cand003_batch_template_field_locator_regression/workshop_ticket_batch_z043_template_field_locator_regression.png
- screenshot_png_dimensions: 1440x1200
- runtime_dom_anchors: 8/8 observed
- guarded_entries_covered:
  - 批量导入
  - 解析后提交
  - 失败重试
- auth_401_count: 1
- runtime_readonly_fallback_risk: true
- write_requests_observed_count: 0
- write_request_success_observed: false
- write_request_success_allowed: false

## Typecheck

- command: npm run typecheck
- workdir: 06_前端/lingyi-pc
- exit_code: 0

## Dev Server

- dev_server_started: true
- dev_server_url: http://127.0.0.1:5174
- dev_server_stopped: true

## Evidence Files

- route_evidence: 04_测试与验收/测试证据/z043_cand003_batch_template_field_locator_regression/route_evidence.json
- dom_anchors_evidence: 04_测试与验收/测试证据/z043_cand003_batch_template_field_locator_regression/dom_anchors_evidence.json
- guarded_readonly_state_evidence: 04_测试与验收/测试证据/z043_cand003_batch_template_field_locator_regression/guarded_readonly_state_evidence.json
- network_write_request_observation: 04_测试与验收/测试证据/z043_cand003_batch_template_field_locator_regression/network_write_request_observation.json

## 风险字段保留

- CAND003 B19 auth_401_count=1 readonly fallback risk
- CAND003 B20 auth_401_count=1 readonly fallback risk
- CAND002 B11/B12 auth_401_count=30/30 readonly fallback risk
- Z043-CAND-001 readonly fallback risk: B03/B04 auth_401_count=2/2
- CAND001 runtime_summary 与 CAND002 screenshot_metadata/runtime_summary 为 non-allowlisted evidence summary/metadata，后续继续排除
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

## 下一步

- next_task: TASK-Z043B-21-LEDGER-CAND003
