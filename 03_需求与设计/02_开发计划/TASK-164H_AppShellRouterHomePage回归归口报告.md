# TASK-164H App Shell Router/HomePage 回归归口报告

## 1. 任务范围

- TASK_ID: `TASK-164H`
- 白名单文件：
  - `06_前端/lingyi-pc/src/router/index.ts`
  - `06_前端/lingyi-pc/src/views/HomePage.vue`
- 文档输出：
  - `03_需求与设计/02_开发计划/TASK-164H_AppShellRouterHomePage回归归口报告.md`
  - `03_需求与设计/02_开发计划/工程师会话日志.md`

## 2. router/HomePage 基线核对

### 2.1 router diff 摘要

命令：

`git -C '/Users/hh/Desktop/领意服装管理系统' diff -- '06_前端/lingyi-pc/src/router/index.ts'`

摘要：

- `/` redirect：`/bom/list -> /home`
- 新增 `/home` 路由（`name: HomePage`，组件 `@/views/HomePage.vue`）
- 新增 `/app/:pathMatch(.*)* -> /home`
- 新增 `/:pathMatch(.*)* -> /home`

### 2.2 HomePage 状态与 mtime

命令：

1. `git -C '/Users/hh/Desktop/领意服装管理系统' status --short -- '06_前端/lingyi-pc/src/router/index.ts' '06_前端/lingyi-pc/src/views/HomePage.vue'`
2. `stat -f '%Sm %N' -t '%Y-%m-%d %H:%M:%S %z' '/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/router/index.ts' '/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/HomePage.vue'`

结果：

- `M src/router/index.ts`
- `?? src/views/HomePage.vue`
- `router/index.ts` mtime：`2026-04-24 15:15:32 +0800`
- `HomePage.vue` mtime：`2026-04-24 19:41:58 +0800`（本轮仅做最小 UI 文案修正）

## 3. 定向验证结果（按任务单要求）

执行目录：`/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc`

1. `npm run typecheck` -> **PASS**
2. `npm run check:production-contracts` -> **PASS**
3. `npm run test:production-contracts` -> **PASS**
4. `npm run check:sales-inventory-contracts` -> **PASS**
5. `npm run test:sales-inventory-contracts` -> **PASS**
6. `npm run check:factory-statement-contracts` -> **PASS**
7. `npm run test:factory-statement-contracts` -> **PASS**
8. `npm run check:quality-contracts` -> **FAIL**
   - 失败文件：`06_前端/lingyi-pc/src/api/quality.ts`（非本任务白名单）
   - 失败点：裸 `fetch()`、`URL.createObjectURL`、缺少 `updateQualityInspection`、必须走统一 `request()`
9. `npm run test:quality-contracts` -> **PASS**
10. `npm run check:style-profit-contracts` -> **PASS**
11. `npm run test:style-profit-contracts` -> **PASS**（`scenarios=475`）

结论：存在任务单必跑验证失败，且失败位于非白名单文件，按约束不可在本任务内修复。

## 4. 静态业务锚点核对

- router 合法入口：
  - 存在 `/home`、`/app/:pathMatch(.*)*`、全局 catch-all redirect `/home`。
- router 禁止项核对：
  - `internal/run-once/worker/debug/diagnostic` 路由无命中。
- HomePage 快捷入口核对：
  - 所有快捷入口路径均指向已存在业务页面路由（`/bom/list`、`/production/plans`、`/warehouse`、`/sales-inventory/*`、`/factory-statements/list`、`/reports/*`、`/permissions/governance`、`/system/management`、`/cross-module/view`）。
- HomePage 安全约束核对：
  - 未命中 `/api/resource`、`/api/method`、`frappe`、裸 `fetch()`。
  - `fetchCurrentUser` 仅用于读取并展示当前会话，不注入 header/token/role。
- 默认身份文案风险修正：
  - 识别到原 fallback `local.dev/System Manager` 有误导风险。
  - 本轮在 `HomePage.vue` 做最小 UI 文案修正：
    - `local.dev -> 未获取到会话`
    - `System Manager -> 未获取到角色`
    - 异常分支不再注入角色值。

静态核对结论：**PASS**（router/HomePage 语义范围内）。

## 5. 收尾校验

1. `git -C '/Users/hh/Desktop/领意服装管理系统' diff --check -- '06_前端/lingyi-pc/src/router/index.ts' '06_前端/lingyi-pc/src/views/HomePage.vue'`
   - 结果：**PASS**（无输出）
2. `git -C '/Users/hh/Desktop/领意服装管理系统' diff --name-only -- '06_前端/lingyi-pc/src/router/index.ts' '06_前端/lingyi-pc/src/views/HomePage.vue' '03_需求与设计/02_开发计划/TASK-164H_AppShellRouterHomePage回归归口报告.md' '03_需求与设计/02_开发计划/工程师会话日志.md'`
   - 当前结果为：`router/index.ts`、`工程师会话日志.md`（`HomePage.vue` 为 untracked，不出现在 `diff --name-only`）
3. `git status --short`（限定关键路径）显示：
   - `.gitignore`、`vite.config.ts` 为历史基线脏状态（本轮未改）
   - `router/index.ts` 仍为基线 tracked diff
   - `HomePage.vue` 仍为 untracked（本轮仅该文件最小文案修正）

## 6. 归口结论

- `related_scope`: `APP_SHELL_ROUTER_HOMEPAGE`
- `can_reclassify_to`: `BLOCKED`
- `remaining_unowned_business_diffs_excluded`: `YES`

阻塞原因：

- 任务单要求的必跑验证 `npm run check:quality-contracts` 失败，且失败位于非白名单文件 `src/api/quality.ts`。
- 按约束不得扩大范围修复，因此本轮不能给出完整通过结论。

## 7. 风险边界

- 未运行 `npm run dev/build/verify`
- 未运行后端测试
- 未触碰其他前端 src/scripts、后端、CCC、控制面、AGENTS、架构师日志、审计官日志、生产/GitHub 管理配置
- 不代表剩余 business tracked diff、REL-004/REL-005、生产联调、ERPNext 生产写入或业务功能放行
