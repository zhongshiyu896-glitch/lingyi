# TASK-Y75B-03-IMPL /system/management 组织框架 1:1 首版实现与浏览器回归报告

## 1. 任务与边界
- TASK_ID: `TASK-Y75B-03-IMPL`
- 路由: `/system/management`
- 目标语义: `TASK-Y74B-P1-03 组织框架`（只读首版）
- allowlist: `TASK-Y75B-03` baseline 冻结的 5 个 `/system/management` 承载文件
- 约束: 仅 GET 只读；不新增写路由；确认/复核/导出/打印/上传入口全部 guarded 或 disabled

## 2. 实现摘要
- 前端页面（`SystemManagement.vue`）新增“组织框架（TASK-Y74B-P1-03，只读）”区块：
  - `data-testid="organization-framework-section"`（`SystemManagement.vue:127`）
  - 新增筛选项：组织层级、状态、关键词、生效开始、生效结束
  - 新增字段：组织编码、组织名称、上级组织、负责人、组织层级、编制人数、在岗人数、状态、生效日期、更新时间、备注
  - 操作按钮：查看（只读）、确认/复核（guarded）、导出/打印/上传（disabled）
  - 新增只读加载链路：`fetchSystemOrganizationFrameworks` + `loadOrganizationFrameworks`
- 前端 API（`system_management.ts`）新增只读方法：
  - `fetchSystemOrganizationFrameworks`（`system_management.ts:246`）
  - `GET /api/system/organization-frameworks`（`system_management.ts:256`）
- 后端 router（`system_management.py`）新增只读路由：
  - `GET /api/system/organization-frameworks`（`system_management.py:300`）
  - 权限动作复用 `SYSTEM_READ + SYSTEM_CONFIG_READ`
  - 支持查询参数：`org_level/status/keyword/effective_start_date/effective_end_date`
- 后端 schema/service 新增只读聚合：
  - schema: `SystemOrganizationFrameworkActionData` / `SystemOrganizationFrameworkItemData` / `SystemOrganizationFrameworkData`
  - service: `_ORGANIZATION_FRAMEWORK_CATALOG` + `list_organization_framework_catalog(...)`
  - service 侧补齐：状态标签、按钮映射、表头映射、生效日期区间过滤
- route order 说明：
  - 当前 `system_management.py` 未定义 `/{id}` 动态详情路由；静态路由显式注册，不存在 route shadowing 风险
- 写路由新增: `NO`（未新增 POST/PUT/PATCH/DELETE）

## 3. preserved 检查
- `/system/management` 既有主语义 preserved: PASS
- 审批流程、用户目录、配置目录、字典目录、系统健康摘要 preserved: PASS
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
- `git diff --name-only -- 06_前端 07_后端`: 本轮新增改动仅命中 5 个 `/system/management` allowlist 文件（另有前序 `/reports/catalog` 5 文件历史 dirty）

## 5. 浏览器回归证据
- 回归路由: `/system/management`
- script: `/tmp/task_y75b_03_impl_browser_check.mjs`
- result_json: `/tmp/task_y75b_03_impl_20260507T135851Z_browser_results.json`
- screenshots_dir: `/tmp/task_y75b_03_impl_20260507T135851Z_screenshots`
- screenshots_count: `6`
- 核心断言:
  - `route_open=true`
  - `first_screen_visible=true`
  - `filters_present=true`
  - `organization_framework_fields_mapped=true`
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
  - 错误态通过可控 `keyword=__simulate_error__` 注入触发，`network_4xx_5xx_total=1` 与 `console_errors_total=1` 均为 expected，不计入 unexplained。

## 6. 禁止动作核对
- 未修改 allowlist 外产品代码: PASS
- 未修改测试代码: PASS
- 未修改 A 控制面文件: PASS
- 未修改 C 审计记录: PASS
- 未执行 `git add/commit/push`: PASS
- 未执行 `PR/merge/tag/release`: PASS
- 未执行 `cleanup/reset/restore/clean/delete`: PASS
- 未启动 `TASK-Y75B-04` 或后续页面: PASS
- 未释放 parked blockers: PASS
