# TASK-Z007B-31-IMPL UI业务证据第二轮readonly扩边复测执行与回归报告

## 执行结论
- task_status: PASS
- source_head: 52febae283660b643153ff65aef81eef6723092e
- selected_candidate_id: Z007-CAND-003
- target_page_count: 13
- valid_target_screenshot_count: 26
- screenshot_count: 26
- blocked_or_split_required_page_count: 4
- non_allowed_read_request_count: 0
- write_request_count: 0
- unexpected_write_request_count: 0
- forbidden_request_count: 0
- blocking_console_error_count: 0
- network_error_count: 0
- target_final_url_mismatch_count: 0

## 详情页ID发现
- sales_order_id(from list): None
- bom_id(from list): None
- plan_id(from list): None
- statement_id(from list): None

## 说明
- production plan detail 仅允许 list-discovered plan_id；若无合法 id 保持 blocked_or_split_required，不造 id。
- blocked_or_split_required_pages: [{"page_target": "/fate/sales-inventory/sales-orders/detail?id={from_list}", "resolved_target": "/fate/sales-inventory/sales-orders/detail?id={from_list}", "reason": "blocked_no_sales_order_id_from_list"}, {"page_target": "/fate/bom/detail?id={from_list}", "resolved_target": "/fate/bom/detail?id={from_list}", "reason": "blocked_no_bom_id_from_list"}, {"page_target": "/fate/production/plans/detail?id={from_list}", "resolved_target": "/fate/production/plans/detail?id={from_list}", "reason": "blocked_no_plan_id_from_list"}, {"page_target": "/fate/factory-statements/detail?id={from_list_or_1}", "resolved_target": "/fate/factory-statements/detail?id=1", "reason": "fallback_to_id_1"}, {"page_target": "/fate/sales-inventory/sales-orders/detail?id={from_list}", "resolved_target": "/fate/sales-inventory/sales-orders/detail?id={from_list}", "reason": "blocked_no_sales_order_id_from_list"}, {"page_target": "/fate/bom/detail?id={from_list}", "resolved_target": "/fate/bom/detail?id={from_list}", "reason": "blocked_no_bom_id_from_list"}, {"page_target": "/fate/production/plans/detail?id={from_list}", "resolved_target": "/fate/production/plans/detail?id={from_list}", "reason": "blocked_no_plan_id_from_list"}, {"page_target": "/fate/factory-statements/detail?id={from_list_or_1}", "resolved_target": "/fate/factory-statements/detail?id=1", "reason": "fallback_to_id_1"}]

## 证据文件
- browser_result_json: `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/task_z007b_31_ui_evidence_second_readonly_expansion_browser_result.json`
- api_regression_json: `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/task_z007b_31_ui_evidence_second_readonly_expansion_api_regression.json`
- evidence_json: `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/task_z007b_31_ui_evidence_second_readonly_expansion_evidence.json`
- screenshot_output_dir: `/tmp/task_z007b31_screenshots`

## 匹配规则落实
- 仅统计 `/api/*` 业务请求。
- 静态精确优先，静态未命中后动态模板匹配。
- factory-statements 静态子路由逐项静态匹配，不回落 `{statement_id}`。
- 请求方法仅 GET。
