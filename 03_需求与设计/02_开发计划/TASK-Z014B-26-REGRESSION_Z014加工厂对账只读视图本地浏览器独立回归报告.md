# TASK-Z014B-26-REGRESSION｜Z014 加工厂对账只读视图本地浏览器独立回归报告

## 任务边界
- task_id: TASK-Z014B-26-REGRESSION
- role: B Engineer
- selected_candidate_id: Z014-CAND-014
- module: 加工厂对账只读视图
- task_type: evidence-only REGRESSION
- CODE_CHANGED: NO
- source_head: 8280b1f628c7677c699ee54e28003edf0cdc300b
- product_code_changed: false
- backend_changed: false
- source_edit_performed: false

## B25 基线复核
- B25 impl JSON/TSV: 19/19 PASS
- B25 JSON/TSV alignment: PASS

## 浏览器回归证据
- route_hit_count: 3/3
- routes:
  - http://127.0.0.1:5173/factory-statements/list
  - http://127.0.0.1:5173/factory-statements/detail
  - http://127.0.0.1:5173/factory-statements/print
- screenshot_count: 6
- screenshot_dir: /tmp/task_z014b26_factory_statement_regression_screenshots
- screenshots:
  - /tmp/task_z014b26_factory_statement_regression_screenshots/list_01_initial.png
  - /tmp/task_z014b26_factory_statement_regression_screenshots/list_02_after_readonly_probe.png
  - /tmp/task_z014b26_factory_statement_regression_screenshots/detail_01_initial.png
  - /tmp/task_z014b26_factory_statement_regression_screenshots/detail_02_readonly_detail_state.png
  - /tmp/task_z014b26_factory_statement_regression_screenshots/print_01_initial.png
  - /tmp/task_z014b26_factory_statement_regression_screenshots/print_02_readonly_print_route.png
- request_methods: ["GET"]
- write_request_count: 0
- unexpected_write_request_count: 0
- forbidden_request_count: 0
- blocking_console_error_count: 0
- blocking_response_error_count: 0
- network_error_count: 0
- export_download_print_sync_called: false
- print_route_access_only_no_system_print_action: true

## Expected Non-blocking Errors
- response 500 http://127.0.0.1:5173/api/auth/me (list)｜local readback non-blocking only
- response 500 http://127.0.0.1:5173/api/auth/me (detail)｜local readback non-blocking only
- response 500 http://127.0.0.1:5173/api/auth/me (print)｜local readback non-blocking only

## 分类说明
- Vite 源码资源不计为导出/打印网络副作用。
- ignored_asset_matches_count: 6

## 产物
- 03_需求与设计/02_开发计划/TASK-Z014B-26-REGRESSION_Z014加工厂对账只读视图本地浏览器独立回归报告.md
- 04_测试与验收/测试证据/z014_frontend_testable_gap/z014_factory_statement_interaction_regression_result.json
- 04_测试与验收/测试证据/z014_frontend_testable_gap/z014_factory_statement_interaction_regression_result.tsv
- 04_测试与验收/测试证据/z014_frontend_testable_gap/z014_factory_statement_interaction_regression_browser_result.json
- /tmp/task_z014b26_factory_statement_regression_screenshots
- 03_需求与设计/02_开发计划/工程师会话日志.md

## 验证
- b25_c_pass_checked: PASS
- B25 impl JSON/TSV: PASS
- B26 regression JSON/TSV alignment: PASS
- browser result JSON parse: PASS
- git diff --cached --name-only: []
- git diff --name-only -- 06_前端: []
- git diff --name-only -- 07_后端: []
- git diff --cached --check: PASS
- git diff --check: PASS
- text hygiene: PASS
- no tag at HEAD: PASS
- remote_contains_head: false
- pr_list: []

## 禁止动作确认
- product code edits: NO
- backend edits: NO
- source edits: NO
- stage/commit/push: NO
- PR/tag/release: NO
- cleanup/reset/restore/clean/delete: NO
- production account / ERPNext production / real business write: NO
- Z014-CAND-015 started: NO
- parked blockers released: NO
