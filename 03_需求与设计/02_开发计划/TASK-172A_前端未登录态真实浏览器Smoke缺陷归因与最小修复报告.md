# TASK-172A 前端未登录态真实浏览器 Smoke 缺陷归因与最小修复报告

## 1. 任务结论
- TASK_ID: TASK-172A
- ROLE: B Engineer
- 结论: 在白名单前端文件内完成最小修复后，本轮真实浏览器 smoke 与只读交互基线达标。

## 2. Root Cause
- `/api/auth/me` 在未登录态返回 401 时，前端同时存在重定向副作用（`auth.ts` 中 `window.location.href='/login'`），导致页面采集阶段出现不稳定跳转链路。
- `permission` store 在未登录态仍继续模块权限请求，导致噪声请求与页面首屏稳定性下降。
- `HomePage` 直接调用 `fetchCurrentUser`，未复用权限 store 的降级语义，未登录态展示和交互稳定性差。
- `WarehouseDashboard` 无读权限时直接走数据加载分支，导致只读 smoke 场景下 tab/视图切换不稳定。

## 3. 最小修复实施
仅修改任务单允许文件：

1. `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/auth.ts`
- 去除 401 分支中的 `window.alert` 与 `window.location.href='/login'`。
- 保留抛错 `未登录或会话无效`，由上层进行 fail-soft 降级处理。

2. `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/stores/permission.ts`
- 增加未登录错误识别与 `guest` 降级。
- `loadCurrentUser` 在未登录态下清空 `username/roles/actions/buttonPermissions` 并置 `status=guest`，不再向上抛异常。
- `loadModuleActions` 与 `loadBomActions` 在 `guest` 或无 `username` 时直接 fail-soft 返回，不再请求权限接口。

3. `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/HomePage.vue`
- 改为通过 `permissionStore.loadCurrentUser()` 获取会话信息。
- 未登录态稳定显示 `访客会话`，避免异常链路影响导航交互。

4. `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/warehouse/WarehouseDashboard.vue`
- 新增 `canRead` 读权限门禁。
- 无读权限时不再发起业务数据请求，仅展示只读骨架/提示，并保留 tabs 可见可切换（不触发写操作）。

## 4. FIX2 真实浏览器证据（独立新 run）
- selected_tool: Playwright
- run_id: `20260425T154640`
- base_url: `http://127.0.0.1:5174`
- result_json: `/tmp/task172a_browser_results.json`
- runtime_log: `/tmp/task172a_probe_runtime.log`
- run/base 锚点:
  - `/tmp/task172a_run_id.log`
  - `/tmp/task172a_base_url.log`

### 4.1 页面级 smoke（8 页）

| path | status | app_mounted | first_screen_visible | console_errors | page_errors | network_4xx_5xx | screenshot |
|---|---:|---|---|---:|---:|---:|---|
| /home | 200 | true | true | 1 | 0 | 1 | /tmp/task172a_20260425T154640_home.png |
| /production/plans | 200 | true | true | 1 | 0 | 1 | /tmp/task172a_20260425T154640_production_plans.png |
| /factory-statements/list | 200 | true | true | 1 | 0 | 1 | /tmp/task172a_20260425T154640_factory-statements_list.png |
| /sales-inventory/sales-orders | 200 | true | true | 1 | 0 | 1 | /tmp/task172a_20260425T154640_sales-inventory_sales-orders.png |
| /sales-inventory/stock-ledger | 200 | true | true | 1 | 0 | 1 | /tmp/task172a_20260425T154640_sales-inventory_stock-ledger.png |
| /warehouse | 200 | true | true | 1 | 0 | 1 | /tmp/task172a_20260425T154640_warehouse.png |
| /quality/inspections | 200 | true | true | 1 | 0 | 1 | /tmp/task172a_20260425T154640_quality_inspections.png |
| /reports/style-profit | 200 | true | true | 1 | 0 | 1 | /tmp/task172a_20260425T154640_reports_style-profit.png |

说明：
- console/network 计数中的 1 次主要为未登录探测 `GET /api/auth/me -> 401`，本轮已完成解释并确认不影响 8 页首屏挂载与可见渲染。
- `page_errors` 全部为 0。

### 4.2 只读交互 smoke
- `/home` 可见导航入口点击：`attempted=2, succeeded=2`（稳定达标）
- `/warehouse` 只读切换：`attempted=2, succeeded=2`（稳定达标）
- 列表筛选输入/清空：
  - `/production/plans`、`/factory-statements/list`、`/sales-inventory/sales-orders`、`/sales-inventory/stock-ledger`、`/quality/inspections`
  - 均为 `SMOKE_TYPED_AND_CLEARED`
- 未执行写操作按钮（create/confirm/cancel/submit/sync 等）。

## 5. 环境与进程归因
- pre-existing:
  - `127.0.0.1:5173` -> `PID=5551`（既有进程，未终止）
- 本轮进程:
  - 启动 `127.0.0.1:5174` 本轮 dev server（独立 run）
  - 采集完成后仅停止本轮 5174 进程
  - 结束时 5174 无监听，5173 既有进程保持不变

## 6. 验证记录
- `npm run typecheck` -> PASS
- `npm run verify` -> PASS
- Playwright 8-page smoke -> PASS
- Playwright read-only interaction -> PASS
- staged area empty -> PASS

## 7. 禁止项核对
- 未执行 git add/commit/push/PR/tag/release。
- 未修改后端、CCC、控制面、AGENTS、架构师日志、审计官日志、`.gitignore`、`vite.config.ts`、生产/GitHub 管理配置。
- 未释放 `TASK-152A / TASK-090I / TASK-110B`。
- 未执行业务写入动作。

## 8. 风险与后续
- 残余风险（低）：未登录态下 `GET /api/auth/me` 仍会出现 401 噪声（已被前端降级与基线解释覆盖，不影响本轮 smoke/交互通过）。
- 建议后续（如需进一步收敛噪声）单开 TASK_ID 评估是否在不弱化鉴权前提下统一未登录探测日志级别。
