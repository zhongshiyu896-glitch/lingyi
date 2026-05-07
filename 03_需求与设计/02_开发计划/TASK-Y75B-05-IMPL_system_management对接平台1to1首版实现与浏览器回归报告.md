# TASK-Y75B-05-IMPL /system/management 对接平台 1:1 首版实现与浏览器回归报告

## 1. 任务与边界
- TASK_ID: `TASK-Y75B-05-IMPL`
- 路由: `/system/management`
- 目标语义: `TASK-Y74B-P1-05 对接平台`（只读首版）
- allowlist: `TASK-Y75B-05` baseline 冻结的 5 个 `/system/management` 承载文件
- 约束: 仅 GET 只读；不新增写路由；同步/测试连接/启停/导出/打印入口全部 guarded 或 disabled

## 2. 实现摘要
- 前端页面（`SystemManagement.vue`）新增“对接平台（TASK-Y74B-P1-05，只读）”区块：
  - `data-testid="integration-platform-section"`（`SystemManagement.vue:270`）
  - 新增筛选项：平台类型、状态、接入模式、关键词、更新开始、更新结束
  - 新增字段：平台编码、平台名称、平台类型、接入模式、连接器、Webhook（脱敏）、同步方向、状态、最近同步、重试策略、更新时间、备注
  - 操作按钮：查看（只读）、测试连接/同步/启停（guarded）、导出/打印（disabled）
  - 新增只读加载链路：`fetchSystemIntegrationPlatforms` + `loadIntegrationPlatforms`（`SystemManagement.vue:1027`）
- 前端 API（`system_management.ts`）新增只读方法：
  - `fetchSystemIntegrationPlatforms`（`system_management.ts:302`）
  - `GET /api/system/integration-platforms`（`system_management.ts:313`）
- 后端 router（`system_management.py`）新增只读路由：
  - `GET /api/system/integration-platforms`（`system_management.py:359`）
  - 权限动作复用 `SYSTEM_READ + SYSTEM_CONFIG_READ`
  - 支持查询参数：`platform_type/status/endpoint_mode/keyword/updated_start_date/updated_end_date`
- 后端 schema/service 新增只读聚合：
  - schema: `SystemIntegrationPlatformActionData` / `SystemIntegrationPlatformItemData` / `SystemIntegrationPlatformData`
  - service: `_INTEGRATION_PLATFORM_CATALOG` + `list_integration_platform_catalog(...)`（`system_config_catalog_service.py:800`）
  - service 侧补齐：平台类型 options、接入模式 options、状态标签、guarded 按钮映射、表头映射、更新时间区间过滤
- route order 说明：
  - 当前 `system_management.py` 未定义 `/{id}` 动态详情路由；静态路由显式注册，不存在 route shadowing 风险
- 写路由新增: `NO`（未新增 POST/PUT/PATCH/DELETE）

## 3. preserved 检查
- `/system/management` 既有主语义 preserved: PASS
- 审批流程、用户目录、组织框架、配置目录、字典目录、系统健康摘要 preserved: PASS
- 权限态、空态、错误态、禁用态 preserved: PASS
- 上传/下载/导出/打印 guarded preserved: PASS
- 共享路由边界（仅在 `/system/management` 内扩展）preserved: PASS

## 4. 验证结果
- `python3 -m py_compile`（router/schema/service）: PASS
- `npm run precheck:dev-runtime`（`06_前端/lingyi-pc`）: PASS
- `npm run typecheck`（`06_前端/lingyi-pc`）: PASS
- `npm run verify`（`06_前端/lingyi-pc`）: PASS
- `git diff --cached --name-only`: 空
- `git diff --cached --check`: PASS
- `git diff --check`: PASS
- `git diff --name-only -- 06_前端 07_后端`：
  - 当前累计产品 dirty 为 10 文件：`/reports/catalog` 5 文件（前序 `TASK-Y75B-01/02-IMPL`）+ `/system/management` 5 文件（前序 `TASK-Y75B-03-IMPL` 持续演进）
  - 本轮“对接平台”实现未新增 allowlist 外产品文件，未把前序 `/reports/catalog` 与前序组织框架累计 dirty 归入本轮范围

## 5. 浏览器回归证据
- 回归路由: `/system/management`
- script: `/tmp/task_y75b_05_impl_browser_check.mjs`
- result_json: `/tmp/task_y75b_05_impl_20260507T151946Z_browser_results.json`
- screenshots_dir: `/tmp/task_y75b_05_impl_20260507T151946Z_screenshots`
- screenshots_count: `6`
- 核心断言:
  - `route_open=true`
  - `first_screen_visible=true`
  - `filters_present=true`
  - `integration_platform_fields_mapped=true`
  - `buttons_mapped=true`
  - `status_tags_mapped=true`
  - `empty_state=true`
  - `error_state=true`
  - `permission_or_disabled_state=true`
  - `write_request_count=0`
  - `upload_download_export_print_request_count=0`
  - `unexplained_console_errors_total=0`
  - `unexplained_network_4xx_5xx_total=0`
- 说明:
  - 错误态通过可控 `keyword=__simulate_error__` 注入触发，`network_4xx_5xx_total=1` 与 `console_errors_total=1` 均为 expected，不计入 unexplained

## 6. 禁止动作核对
- 未修改 allowlist 外产品代码: PASS
- 未修改测试代码: PASS
- 未修改 A 控制面文件: PASS
- 未修改 C 审计记录: PASS
- 未执行 `git add/commit/push`: PASS
- 未执行 `PR/merge/tag/release`: PASS
- 未执行 `cleanup/reset/restore/clean/delete`: PASS
- 未启动后续页面任务: PASS
- 未释放 parked blockers: PASS
