# TASK-Y23B-02-IMPL /factory-statements/list 款式打板下单对账表 1to1 首版实现与浏览器回归报告

## SOURCE_TASK_ENTRY
- TASK_ID: `TASK-Y23B-02-IMPL`
- ROLE: `B Engineer`
- route: `/factory-statements/list`
- source baseline: `task_y23b_02_allowlist_baseline.json`
- allowlist_mismatch: `NO`（已按 Y23B-02 基线纠偏到 `factory_statement` 实际路径）

## IMPLEMENTATION_SUMMARY
- 在共享路由 `/factory-statements/list` 保留“加工厂对账单列表”主语义与详情/打印入口前提下，补齐 `TASK-Y22B-P1-02` 款式打板下单对账表只读语义。
- 前端补齐：
  - 增加“款式打板下单对账表”提示区块与二级筛选（打板单号/款号/工厂/下单时间/金额区间/状态）。
  - 增加对账映射字段（打板单号、款号、工厂、下单时间、下单金额）并保留原对账主字段。
  - 增加写语义按钮（导出/生成应付/确认/取消）guarded 提示，不触发真实写请求。
  - 增加可承接的错误态（`readError` + `error-alert`）。
- API 层补齐：
  - 在 `factory_statement.ts` 对 `create/confirm/cancel/createPayableDraft` 增加只读 guard，阻断真实写调用。
- 未新增真实写路由，未放宽既有写接口权限，未扩展到其他候选页面。

## ROUTE_API_BACKEND_MAPPING
- Frontend view: `06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementList.vue`
- Frontend API: `06_前端/lingyi-pc/src/api/factory_statement.ts`
- Backend router: `07_后端/lingyi_service/app/routers/factory_statement.py`（本轮未改）
- Backend schema: `07_后端/lingyi_service/app/schemas/factory_statement.py`（本轮未改）
- Backend service: `07_后端/lingyi_service/app/services/factory_statement_service.py`（本轮未改）

## SHARED_ROUTE_SCOPE_BOUNDARY
- 仅实现 `TASK-Y22B-P1-02` 款式打板下单对账表语义。
- 未启动其他 P1/P2 候选，未扩展至 `/production/plans`、`/bom/list`、`/warehouse`、`/reports/style-profit`。
- 工厂对账列表主语义保留：PASS。
- 详情入口 `/factory-statements/detail` 保留：PASS。
- 打印入口 `/factory-statements/print` 保留：PASS。

## BROWSER_VALIDATION
- run_id: `20260503T231358Z`
- result_json: `/tmp/task_y23b_02_impl_20260503T231358Z_browser_results.json`
- screenshot_dir: `/tmp/task_y23b_02_impl_20260503T231358Z_screenshots`
- screenshots_count: `7`
- checks:
  - route_open: PASS
  - first_screen_visible: PASS
  - filters_present: PASS
  - structure_mapped: PASS
  - fields_or_headers_mapped: PASS
  - sample_order_reconciliation_fields_mapped: PASS
  - buttons_mapped: PASS
  - status_tags_mapped: PASS
  - empty_state: PASS
  - error_state: PASS
  - permission_or_disabled_state: PASS
  - factory_statement_list_preserved_check: PASS
  - detail_entry_preserved_check: PASS
  - print_entry_preserved_check: PASS
  - write_actions_guarded_check: PASS
- network/console:
  - write_request_count: `0`
  - download_export_print_request_count: `0`
  - console_errors_total: `1`
  - page_errors_total: `0`
  - network_4xx_5xx_total: `1`
  - expected_error_state_count: `1`（手动注入 503 验证错误态承接）
  - unexplained_console_errors_total: `0`
  - unexplained_network_4xx_5xx_total: `0`

## WRITE_ACTION_BOUNDARY
- 创建/确认/取消/生成应付草稿：API 层只读 guard，禁止真实写请求。
- 列表动作“导出/生成应付/确认/取消”：前端 guarded 提示，不触发写动作。
- 本轮未触发 POST/PUT/PATCH/DELETE；未触发真实下载/导出/打印请求。

## FORBIDDEN_ACTIONS
- git add/commit/push: NO
- PR/merge/close/tag/release: NO
- cleanup/reset/restore/clean/delete: NO
- other P1/P2 started: NO
- allowlist outside modified: NO
- real write routes added: NO
- write permission relaxed: NO
- production/GitHub management actions: NO
- parked blockers released: NO
