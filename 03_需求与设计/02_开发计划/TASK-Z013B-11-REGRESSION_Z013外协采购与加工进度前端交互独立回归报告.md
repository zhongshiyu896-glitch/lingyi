# TASK-Z013B-11-REGRESSION_Z013外协采购与加工进度前端交互独立回归报告

## 任务信息
- task_id: TASK-Z013B-11-REGRESSION
- role: B Engineer
- source_task_id: TASK-Z013B-10-IMPL
- selected_candidate_id: Z013-CAND-002
- code_changed: NO

## 回归覆盖路由
- http://127.0.0.1:5173/materialPurchase/materialPurchaseProcess
- http://127.0.0.1:5173/subcontract/list?parity=material-purchase

## 结果复核
- B10 result JSON/TSV: 14/14 对齐，全部 PASS。
- B11 regression JSON/TSV: 14/14 对齐，全部 PASS。
- browser result JSON: 可解析。

## 本轮回归结论
- route_hit_count: 2/2
- screenshot_dir: /tmp/task_z013b11_subcontract_purchase_regression_screenshots
- screenshot_count: 2
- request_methods: ["GET"]
- write_request_count: 0
- unexpected_write_request_count: 0
- forbidden_request_count: 0
- blocking_console_error_count: 0
- blocking_response_error_count: 0
- network_error_count: 0
- export_endpoint_called: false
- expected_non_blocking_response_errors:
  - 500 GET /api/auth/me（仅记录，不外推为后端稳定性或生产 readback 闭合）

## 回归说明
- 本轮在 direct route 与 alias route 命中均 PASS。
- 只读筛选/分页/详情入口在运行态权限回落场景下，采用运行态 + 源码锚点双轨验证，保持可测性与一致性。

## 状态口径
- full_browser_route_smoke_closed=false
- production_readback_ready=false
- go_live_ready=false
- project_completion_claimed=false
- remote_lifecycle_parked=true
