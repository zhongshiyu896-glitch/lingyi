# TASK-Y3B-10 用户管理 1to1 首版实现与浏览器回归报告

## SOURCE_TASK_ENTRY
- TASK_ID: `TASK-Y3B-10`
- 目标路由: `/system/management`（共享路由）
- 任务边界: 仅实现 Y3B-10「用户管理」语义，保留 Y3B-09「审核流程」区块与语义。

## EVIDENCE_USED
- 基线与任务拆分:
  - `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/task_y13_system_management_shared_route_baseline.json`
  - `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/task_y2_p0_10_page_task_breakdown.json`
- 上游审计输入:
  - `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-Y3B-09_审核流程1to1首版实现与浏览器回归报告.md`
- 衣算云截图证据:
  - `/Users/hh/Desktop/领意服装管理系统/04_测试与验收/测试证据/live_compare/20260404_171203/108_系统管理_用户管理.png`
- 本轮浏览器结果:
  - `/tmp/task_y3b_10_20260503T204614_browser_results.json`
- 本轮截图:
  - `/tmp/task_y3b_10_20260503T204614_01_overview.png`
  - `/tmp/task_y3b_10_20260503T204614_02_user_section.png`
  - `/tmp/task_y3b_10_20260503T204614_03_detail_or_guarded.png`
  - `/tmp/task_y3b_10_20260503T204614_04_permission_disabled.png`
  - `/tmp/task_y3b_10_20260503T204614_05_error_state.png`

## IMPLEMENTATION_SUMMARY
- `/system/management` 增加「用户管理（TASK-Y3B-10，只读）」区块，覆盖筛选、列表字段、角色状态标签、只读详情、guarded 写语义按钮、空态和错误态。
- 前端新增用户目录 API 查询模型与函数：`GET /api/system/users/catalog`。
- 后端在 `system_management` 路由补充用户目录只读接口与 schema，并在服务层补充本地静态用户目录数据。
- 写语义（新增/编辑/禁用/重置密码）全部保持 guarded/disabled/提示型，不触发写请求。
- Y3B-09 审核流程区块保留，未覆盖。

## FIELD_BUTTON_TABLE_MAPPING
- 筛选项: 角色、状态、关键词、开始时间、结束时间。
- 列表字段: 用户名、姓名、角色、状态、部门、最近登录、更新时间。
- 按钮语义:
  - 可用只读: 查看（打开用户详情弹窗）。
  - Guarded: 新增、编辑、禁用、重置密码（仅提示，不写入）。
- 状态标签: 启用/锁定/停用。

## ROUTE_API_BACKEND_MAPPING
- 路由: `/system/management`
- 前端文件:
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/system/SystemManagement.vue`
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/system_management.ts`
- 后端文件:
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/system_management.py`
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/system_management.py`
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/system_config_catalog_service.py`
- 接口:
  - `GET /api/system/users/catalog`
  - 保留既有 `GET /api/system/approval-flows`（Y3B-09）

## SCREENSHOT_COMPARISON
- 本地页面已具备用户管理主语义（筛选 + 用户目录 + 只读详情 + guarded 写语义按钮），与衣算云用户管理证据的首版 1:1 目标一致。
- 与 Y3B-09 的共享路由边界已保持：审核流程区块仍可见，且语义未被覆盖。

## BROWSER_VALIDATION
- run_id: `20260503T204614`
- result_json: `/tmp/task_y3b_10_20260503T204614_browser_results.json`
- checks:
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
  - y3b_09_preserved_check: PASS
- counts:
  - screenshots_count: `5`
  - write_request_count: `0`
  - download_export_print_request_count: `0`
  - console_errors_total: `1`
  - page_errors_total: `0`
  - network_4xx_5xx_total: `1`
  - expected_error_state_count: `1`
  - unexplained_console_errors_total: `0`
  - unexplained_network_4xx_5xx_total: `0`

## WRITE_ACTION_BOUNDARY
- 未新增任何 `POST/PUT/PATCH/DELETE` 路由。
- 前端写语义按钮均 guarded/disabled。
- 导出/下载/打印未触发真实请求。

## PERMISSION_BOUNDARY
- 仍要求 `SYSTEM_READ + SYSTEM_CONFIG_READ` 后端权限。
- 未伪造生产权限，使用本地 dev runtime/dev-auth 验证。
- 未扩展到 `/reports/catalog` 或其他模块。

## KNOWN_GAPS
- 当前为 Y3B-10 首版只读闭环，不包含真实用户写操作（新增/编辑/禁用/重置密码提交）。
- 首次浏览器回归出现 `GET /api/system/users/catalog` 404，确认为旧 8000 runtime 未加载新路由；重启本地 runtime 后闭合。

## FORBIDDEN_ACTIONS
- git add/commit/push: NO
- PR/merge/close/tag/release/发布: NO
- cleanup/reset/restore/clean/delete: NO
- 修改 `/reports/catalog`: NO
- 修改 allowlist 外产品代码: NO
- 新增真实写路由: NO
- 生产联调/GitHub 管理配置: NO
- 释放 parked blockers: NO

## NEXT_RECOMMENDATION
- 进入 C 审计 TASK-Y3B-10。
- 若 C PASS，再由 A 决定是否进入剩余 P0 收口与批次冻结。
