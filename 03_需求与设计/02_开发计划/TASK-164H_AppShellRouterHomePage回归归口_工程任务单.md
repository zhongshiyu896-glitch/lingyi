# TASK-164H App Shell Router/HomePage 回归归口工程任务单

```text
STATUS: READY_FOR_BUILD
TASK_ID: TASK-164H
ROLE: B Engineer

任务：
对 TASK-164A baseline 中遗留的 app shell router/HomePage 入口做定向回归验证、必要最小修复与归口冻结。

本任务只覆盖以下 2 个文件：
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/router/index.ts
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/HomePage.vue

背景：
- TASK-164G FIX1 已由 C 返回 AUDIT_RESULT: PASS。
- TASK-164G 以 PARTIAL_ONLY 收口：production 语义范围可归口为 HISTORICAL_TASK_OUTPUT_VERIFIED；router/HomePage 不属于生产计划/Work Order 链路，保留为 PENDING_OWNER。
- 当前 router diff：
  - `/` redirect 从 `/bom/list` 改为 `/home`
  - 新增 `/home` 路由，`name: HomePage`，`component: () => import('@/views/HomePage.vue')`
  - 新增 `/app/:pathMatch(.*)*` redirect `/home`
  - 新增 `/:pathMatch(.*)*` redirect `/home`
- 当前 `HomePage.vue` 为 untracked，mtime 与 router diff 同为 `2026-04-24 15:15:32 +0800`。

允许修改：
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/router/index.ts
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/HomePage.vue
- 新增归口冻结报告：
  /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-164H_AppShellRouterHomePage回归归口报告.md
- 追加工程师会话日志：
  /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md

禁止修改：
- /Users/hh/Desktop/领意服装管理系统/.gitignore
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/vite.config.ts
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/** 中除上述 2 个文件之外的任何文件
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/**
- /Users/hh/Desktop/领意服装管理系统/07_后端/**
- /Users/hh/Desktop/ccc/**
- LOOP_STATE / TASK_BOARD / HANDOVER_STATUS / INTERVENTION_QUEUE / AUTO_LOOP_PROTOCOL
- AGENTS 规则文件
- 架构师日志、审计官日志
- 任何生产/GitHub 管理配置

禁止动作：
- 禁止清理、删除、回滚、还原其他既有 diff。
- 禁止运行 npm run dev。
- 禁止运行 npm run build。
- 禁止运行全量 npm run verify。
- 禁止运行后端测试。
- 禁止启动、停止、重载 CCC server。
- 禁止调用 /api/relay/start 或 /api/relay/stop。
- 禁止 push / PR / tag / 发布。
- 禁止把本任务结论外推为剩余 business tracked diff 放行、dirty worktree 清理完成、REL-004/REL-005、生产联调、GitHub 管理配置、ERPNext 生产写入或业务功能放行。

执行要求：
1. 先只读核对 router/HomePage 状态：
   git -C '/Users/hh/Desktop/领意服装管理系统' diff -- '06_前端/lingyi-pc/src/router/index.ts'
   git -C '/Users/hh/Desktop/领意服装管理系统' status --short -- '06_前端/lingyi-pc/src/router/index.ts' '06_前端/lingyi-pc/src/views/HomePage.vue'
2. 执行定向验证，在 /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc 下运行：
   - npm run typecheck
   - npm run check:production-contracts
   - npm run test:production-contracts
   - npm run check:sales-inventory-contracts
   - npm run test:sales-inventory-contracts
   - npm run check:factory-statement-contracts
   - npm run test:factory-statement-contracts
   - npm run check:quality-contracts
   - npm run test:quality-contracts
   - npm run check:style-profit-contracts
   - npm run test:style-profit-contracts
3. 静态核对最小业务锚点：
   - `router/index.ts` 应只新增 app shell 合法入口：`/home`、`/app/:pathMatch(.*)*`、全局 catch-all redirect。
   - `router/index.ts` 不得暴露 internal/run-once/worker/debug/diagnostic 路由。
   - `HomePage.vue` 快捷入口必须指向已存在的合法业务页面路由，不得指向 internal/run-once/worker/debug/diagnostic 路由。
   - `HomePage.vue` 不得直连 ERPNext `/api/resource`、`/api/method`、`frappe`，不得裸 `fetch()` 绕过统一请求层。
   - `HomePage.vue` 不得引入真实鉴权副作用；调用 `fetchCurrentUser` 只能用于展示当前会话，不得注入 header/token/role。
   - 若 `HomePage.vue` 存在 `local.dev` / `System Manager` 默认显示，必须判断其是否会误导为真实登录/权限身份；如有风险，仅允许在 `HomePage.vue` 内做最小 UI 文案修正。
4. 如验证全部通过：
   - 若无需修复，不修改代码，只新增报告并追加日志。
   - 若需要最小修复，只允许在 `router/index.ts` / `HomePage.vue` 内修改。
5. 如验证失败：
   - 先判断失败是否落在本任务 2 文件范围内。
   - 仅当失败可归因到这 2 文件时，允许在这 2 文件内做最小修复。
   - 若失败来自其他 dirty diff、依赖、环境、后端或非白名单文件，禁止扩大修改范围，回交 BLOCKERS 或 RISK_NOTES。

报告必须包含：
- router diff 摘要。
- HomePage.vue 文件状态、mtime 与主要内容归口说明。
- 每条验证命令结果。
- 静态业务锚点核对结果。
- 若有修复，说明修复是否仅限 2 文件。
- 是否可将 router/HomePage 从 PENDING_OWNER 收敛为 HISTORICAL_TASK_OUTPUT_VERIFIED。
- 明确本任务不覆盖 production / warehouse / sales-inventory / factory-statement / style-profit / backend / CCC 等其他 diff。

必须验证：
- git -C '/Users/hh/Desktop/领意服装管理系统' diff --check -- '06_前端/lingyi-pc/src/router/index.ts' '06_前端/lingyi-pc/src/views/HomePage.vue'
- git -C '/Users/hh/Desktop/领意服装管理系统' diff --name-only -- '06_前端/lingyi-pc/src/router/index.ts' '06_前端/lingyi-pc/src/views/HomePage.vue' '03_需求与设计/02_开发计划/TASK-164H_AppShellRouterHomePage回归归口报告.md' '03_需求与设计/02_开发计划/工程师会话日志.md'
- 确认未修改禁止范围文件。

REPORT_BACK_FORMAT:

STATUS: READY_FOR_REVIEW
TASK_ID: TASK-164H
ROLE: B Engineer

CHANGED_FILES:
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-164H_AppShellRouterHomePage回归归口报告.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md
- 如确有本任务内修复，再列出 router/HomePage 实际修改文件

CODE_CHANGED:
- YES/NO

SCOPE_FILES:
- src/router/index.ts
- src/views/HomePage.vue

OWNERSHIP_RESULT:
- related_scope: APP_SHELL_ROUTER_HOMEPAGE
- can_reclassify_to: HISTORICAL_TASK_OUTPUT_VERIFIED / NEEDS_FIX / BLOCKED
- remaining_unowned_business_diffs_excluded: YES

VALIDATION:
- npm run typecheck: PASS/FAIL/NOT_RUN
- npm run check:production-contracts: PASS/FAIL/NOT_RUN
- npm run test:production-contracts: PASS/FAIL/NOT_RUN
- npm run check:sales-inventory-contracts: PASS/FAIL/NOT_RUN
- npm run test:sales-inventory-contracts: PASS/FAIL/NOT_RUN
- npm run check:factory-statement-contracts: PASS/FAIL/NOT_RUN
- npm run test:factory-statement-contracts: PASS/FAIL/NOT_RUN
- npm run check:quality-contracts: PASS/FAIL/NOT_RUN
- npm run test:quality-contracts: PASS/FAIL/NOT_RUN
- npm run check:style-profit-contracts: PASS/FAIL/NOT_RUN
- npm run test:style-profit-contracts: PASS/FAIL/NOT_RUN
- static_business_anchors: PASS/FAIL
- git diff --check: PASS/FAIL
- forbidden_files_touched: NO/YES

RISK_NOTES:
- 未运行 npm run dev/build/verify
- 未运行后端测试
- 未触碰其他前端 src/scripts、后端、CCC、控制面、AGENTS、架构师日志、审计官日志、生产/GitHub 管理配置
- 不代表剩余 business tracked diff、REL-004/REL-005、生产联调、ERPNext 生产写入或业务功能放行

NEXT_ROLE: A Technical Architect
BLOCKERS:
- NONE 或具体阻塞
```
