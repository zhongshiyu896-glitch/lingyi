# TASK-Z014B-05-REGRESSION Z014首页与经营总览本地浏览器独立回归报告

## 范围
- selected_candidate_id: Z014-CAND-011
- module: 首页与经营总览
- source_head: e34cb6518dbdd053fcf82cc25186887473a3a875
- runtime_mode: READONLY_GET_ONLY_BROWSER_EVIDENCE_ONLY
- CODE_CHANGED: NO
- browser_route_checks: http://127.0.0.1:5173/home, http://127.0.0.1:5173/dashboard/overview

## B04 基线复核
- B04 impl JSON/TSV: PASS
- B04 browser result: PASS
- B04 screenshot paths: PASS

## B05 浏览器回归
- route_hit_count: 2/2
- screenshot_count: 4
- screenshot_dir: /tmp/task_z014b05_dashboard_home_regression_screenshots
- request_methods: ["GET"]
- write_request_count: 0
- unexpected_write_request_count: 0
- forbidden_request_count: 0
- blocking_console_error_count: 0
- blocking_response_error_count: 0
- network_error_count: 0
- export_download_print_sync_called: false
- expected_non_blocking_errors: []
- local_evidence_mode: PLAYWRIGHT_GET_ONLY_WITH_LOCAL_API_FULFILL

## 只读交互记录
- home_dashboard_entry_navigation: PASS, network_side_effect=false
- dashboard_reset: PASS, network_side_effect=false
- dashboard_refresh_metrics: PASS, network_side_effect=false
- dashboard_guarded_write_semantic_button: PASS, network_side_effect=false
- dashboard_detail_drawer_readonly: PASS, network_side_effect=false

## 边界声明
本任务仅做独立回归证据采集，未修改产品代码、未修改后端、未 stage、未 commit、未触发真实订单/库存/财务/主数据写入，未触发 export/download/print/sync 网络副作用。
