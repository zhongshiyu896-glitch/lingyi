# TASK-Y3B-01 大货看板 1:1 首版实现与浏览器回归报告

## SOURCE_TASK_ENTRY
- task_id: `TASK-Y3B-01`
- module: `大货管理`
- page_name: `大货看板`
- yisuan_url_or_route: `https://erp.huaaosoft.com/#/production/home`
- local_target_route: `/dashboard/overview`
- frontend_allowlist:
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/dashboard/DashboardOverview.vue`
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/dashboard.ts`
- backend_allowlist:
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/dashboard.py`
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/dashboard.py`
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/dashboard_service.py`

## EVIDENCE_USED
- yisuan screenshot:
  - `/Users/hh/Desktop/领意服装管理系统/04_测试与验收/测试证据/live_compare/20260404_171203/048_大货管理_大货看板.png`
- live_compare meta:
  - `/Users/hh/Desktop/领意服装管理系统/04_测试与验收/测试证据/live_compare/full_compare_report.json#results[47]`
- matrix/task breakdown:
  - `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/task_y1_yisuan_117_page_matrix.json`
  - `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/task_y2_p0_10_page_task_breakdown.json#TASK-Y3B-01`
  - `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/task_y7_next_p0_page_batch.json#TASK-Y3B-01`

## IMPLEMENTATION_SUMMARY
- 在 TASK-Y3B-01 allowlist 内完成“大货看板”页面 1:1 首版最小闭环，未扩散至非 allowlist 文件。
- 前端页面完成看板语义补齐：标题、副标题、看板选择、筛选项、流程节点、消息表格、状态标签、空态、错误态、权限提示、详情入口。
- 前端 API `fetchDashboardOverview` 增加 `keyword` 查询参数并扩展 `kanban` 响应类型。
- 后端 dashboard contract 最小补齐：
  - router 新增 `keyword` 参数透传；
  - schema 增加 `kanban flow/message` 结构；
  - service 新增 `kanban` 只读 payload 与本地过滤（`keyword/from_date/to_date`）。
- 写语义按钮全部 guarded，仅提示，不触发真实写动作。

## FIELD_BUTTON_TABLE_MAPPING
- 筛选映射：
  - `关键词` -> `query.keyword`
  - `开始时间` -> `query.from_date`
  - `结束时间` -> `query.to_date`
- 按钮映射：
  - 已展示：`搜索/重置/清空/确定/标志已读/删除消息/新增消息/保存`
  - `清空/确定/标志已读/删除消息/新增消息/保存` 全部为 guarded，只提示不执行写动作
- 流程节点映射：
  - `报价单/订单/生产制单/面料/大货跟进/工厂合同/工厂合同质检/辅料/包材/大货成本核算`
- 表格字段映射：
  - `订单号/客户/款号/款名/下单数量/超期/日/一/二/三/四/五/六/标题/发送时间/状态/发送人`

## ROUTE_API_BACKEND_MAPPING
- route:
  - `/dashboard/overview`
- frontend API:
  - `GET /api/dashboard/overview`
  - caller: `fetchDashboardOverview (src/api/dashboard.ts)`
- backend mapping:
  - router: `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/dashboard.py`
  - schema: `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/dashboard.py`
  - service: `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/dashboard_service.py`

## SCREENSHOT_COMPARISON
- yisuan_screenshot:
  - `/Users/hh/Desktop/领意服装管理系统/04_测试与验收/测试证据/live_compare/20260404_171203/048_大货管理_大货看板.png`
- local_screenshots:
  - `/tmp/task_y3b_01_20260503T095810_initial.png`
  - `/tmp/task_y3b_01_20260503T095810_queried.png`
  - `/tmp/task_y3b_01_20260503T095810_navigation.png`
  - `/tmp/task_y3b_01_20260503T095810_empty.png`
  - `/tmp/task_y3b_01_20260503T095810_error.png`
  - `/tmp/task_y3b_01_20260503T095810_final.png`
- comparison_notes:
  - 页面主标题、筛选区、流程节点与消息表头语义已对齐。
  - “流程入口”在本轮以看板内入口语义与 query 流程入口验证闭合；跨页业务流由对应页面任务独立闭环。
- evidence_gap_count: `0`

## BROWSER_VALIDATION
- run_id: `20260503T095810`
- result_json: `/tmp/task_y3b_01_20260503T095810_browser_results.json`
- base_url: `http://127.0.0.1:5174`
- route: `/dashboard/overview`
- route_open: PASS
- first_screen_visible: PASS
- filters_present: PASS
- structure_mapped: PASS
- fields_or_headers_mapped: PASS
- buttons_mapped: PASS
- status_tags_mapped: PASS
- empty_state: PASS
- error_state: PASS
- permission_or_disabled_state: PASS
- navigation_or_flow_entry: PASS
- write_request_count: `0`
- download_export_print_request_count: `0`
- console_errors_total: `0`
- page_errors_total: `0`
- network_4xx_5xx_total: `0`
- expected_error_state_count: `1`
- unexplained_error_count: `0`

## WRITE_ACTION_BOUNDARY
- 本轮验证仅使用本地 dev runtime（`127.0.0.1:8000` + `127.0.0.1:5174`）。
- 未触发 POST/PUT/PATCH/DELETE。
- 未触发真实导出/下载/打印请求。
- 写语义按钮全部保持 guarded，不伪造成功，不越权放开。

## PERMISSION_BOUNDARY
- user_or_role_faked: `NO`
- backend_permission_bypassed: `NO`
- write_permission_expanded: `NO`
- disabled_or_guarded_actions:
  - `清空/确定/标志已读/删除消息/新增消息/保存`
- evidence_summary:
  - 页面读取权限依赖 `dashboard:read`；无读权限时展示受限提示；
  - `dashboard:write` 未开放时展示“只读模式”提示，写动作保持受控。

## KNOWN_GAPS
- 当前为 TASK-Y3B-01 首版：流程入口跨页深链的完整业务闭环由对应页面任务独立承担，不在本页内放宽权限或伪造写成功。

## FORBIDDEN_ACTIONS
- git add/commit/push: NO
- PR/merge/close/tag/release/发布: NO
- cleanup/reset/restore/clean/delete: NO
- production actions: NO
- GitHub Secret / Hosted Runner / Branch protection / Ruleset: NO
- 释放 parked blockers: NO
- 修改 TASK-Y1/TASK-Y2/TASK-Y7 矩阵口径: NO

## NEXT_RECOMMENDATION
- 建议进入 `TASK-Y3B-01` C 审计。
- 审计通过后，再进入 second batch 收口任务（聚合 TASK-Y3B-04/06/01 的回归与候选账本冻结）。
