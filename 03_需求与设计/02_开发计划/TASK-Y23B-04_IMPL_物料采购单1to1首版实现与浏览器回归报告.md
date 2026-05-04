# TASK-Y23B-04-IMPL /bom/list 物料采购单 1to1 首版实现与浏览器回归报告

## SOURCE_TASK_ENTRY
- TASK_ID: `TASK-Y23B-04-IMPL`
- ROLE: `B Engineer`
- route: `/bom/list`
- source baseline: `task_y23b_04_bom_list_allowlist_baseline.json`
- shared_route: `YES`
- allowlist_mismatch: `NO`

## IMPLEMENTATION_SUMMARY
- 在共享路由 `/bom/list` 保留 BOM 管理主列表、`TASK-Y23B-01-IMPL` 物料图库语义与 `/bom/detail` 入口的前提下，补齐 `TASK-Y22B-P1-04` 物料采购单只读语义。
- 前端补齐：
  - 新增“物料采购单（TASK-Y22B-P1-04）”区块与筛选项（采购单号/供应商/物料/交期/状态/数量区间/金额区间）。
  - 新增采购单表格字段（采购单号、供应商、款号、物料编码、物料名称、数量、单位、单价、金额、交期、状态）。
  - 新增操作语义按钮（查看/生成采购/确认/取消/导出），写语义均 guarded 提示。
  - 补齐采购单空态、错误态、状态标签与权限态承接。
- 后端补齐：
  - 新增只读接口 `GET /api/bom/purchase-orders`。
  - 新增采购单只读查询 schema/service 组合，不新增真实写路由。
- 运行态归因与收口：
  - 首次回归命中 `422 /api/bom/purchase-orders`，定位为本地 8000 后端旧进程未加载新路由版本（被 `/{bom_id}` 路由误匹配）。
  - 重启 8000 runtime 后接口恢复 200，复跑浏览器回归闭合。

## ROUTE_API_BACKEND_MAPPING
- Frontend view: `06_前端/lingyi-pc/src/views/bom/BomList.vue`
- Frontend API: `06_前端/lingyi-pc/src/api/bom.ts`
- Backend router: `07_后端/lingyi_service/app/routers/bom.py`
- Backend schema: `07_后端/lingyi_service/app/schemas/bom.py`
- Backend service: `07_后端/lingyi_service/app/services/bom_service.py`
- New readonly endpoint: `GET /api/bom/purchase-orders`

## SHARED_ROUTE_SCOPE_BOUNDARY
- 仅实现 `TASK-Y22B-P1-04` 物料采购单语义，未启动 `TASK-Y22B-P1-05` 或其他 P1/P2 页面。
- 未扩展到 `/factory-statements/list`、`/sales-inventory/sales-orders`、`/production/plans`、`/dashboard/overview`、`/warehouse`。
- BOM 管理列表主语义保留：PASS。
- `TASK-Y23B-01-IMPL` 物料图库语义保留：PASS。
- `/bom/detail` 入口链路保留：PASS。

## BROWSER_VALIDATION
- run_id: `20260504T000305Z`
- result_json: `/tmp/task_y23b_04_impl_20260504T000305Z_browser_results.json`
- screenshot_dir: `/tmp/task_y23b_04_impl_20260504T000305Z_screenshots`
- screenshots_count: `7`
- checks:
  - route_open: PASS
  - first_screen_visible: PASS
  - filters_present: PASS
  - structure_mapped: PASS
  - fields_or_headers_mapped: PASS
  - purchase_order_fields_mapped: PASS
  - buttons_mapped: PASS
  - status_tags_mapped: PASS
  - empty_state: PASS
  - error_state: PASS
  - permission_or_disabled_state: PASS
  - bom_management_list_preserved_check: PASS
  - material_gallery_preserved_check: PASS
  - bom_detail_entry_preserved_check: PASS
  - write_actions_guarded_check: PASS
- network/console:
  - write_request_count: `0`
  - upload_download_export_print_request_count: `0`
  - console_errors_total: `1`
  - page_errors_total: `0`
  - network_4xx_5xx_total: `1`
  - expected_error_state_count: `1`（手动注入 503 验证错误态承接）
  - unexplained_console_errors_total: `0`
  - unexplained_network_4xx_5xx_total: `0`

## VALIDATION_COMMANDS
- `git diff --cached --name-only`: PASS（空）
- `git diff --check`: PASS（无输出）
- `npm run precheck:dev-runtime`: PASS
- `npm run typecheck`: PASS
- `npm run verify`: PASS

## WRITE_ACTION_BOUNDARY
- “生成采购/确认/取消/导出/上传/编辑/删除”均为 guarded/提示型，不触发真实写请求。
- 本轮未触发 POST/PUT/PATCH/DELETE。
- 本轮未触发真实上传/下载/导出/打印请求。
- 未放宽历史 BOM 写接口权限。

## FORBIDDEN_ACTIONS
- git add/commit/push: NO
- PR/merge/close/tag/release: NO
- cleanup/reset/restore/clean/delete: NO
- TASK-Y22B-P1-05 or other P1/P2 started: NO
- allowlist outside modified: NO
- real write routes added: NO
- BOM write permission relaxed: NO
- upload/download/export/print real requests: NO
- production/GitHub management actions: NO
- parked blockers released: NO
