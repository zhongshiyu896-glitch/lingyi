# TASK-164G FIX1 Router/HomePage 归因与结论修正工程任务单

```text
STATUS: READY_FOR_BUILD
TASK_ID: TASK-164G
FIX_PASS: FIX1
ROLE: B Engineer

任务：
对 C 审计发现的 `src/router/index.ts` 与 `src/views/HomePage.vue` 范围归因问题做只读补证，并修正 TASK-164G 归口结论。

C FINDINGS：
- `src/router/index.ts` 的实际 tracked diff 不是生产计划合法页面路由归口变更，而是将 `/` 重定向到 `/home`、新增 `HomePage` 路由、以及新增 `/app/:pathMatch` 和全局 catch-all redirect；这与 B 报告中“仅承载生产计划页面路由”及“七文件可归口到 TASK-004A/TASK-004B/TASK-015D~015F/TASK-021B~021D/TASK-100A~100D”的结论不一致。
- `src/router/index.ts` 当前引用未纳入 TASK-164G 回交范围的 untracked 文件 `06_前端/lingyi-pc/src/views/HomePage.vue`，该文件 mtime 与 router diff 同为 `2026-04-24 15:15:32 +0800`；虽早于 TASK-164G 窗口，但 B 未在本任务报告中归因，C 不能将该 router diff 纳入生产计划/Work Order 七文件历史归口。

A 只读复核：
- `git diff -- 06_前端/lingyi-pc/src/router/index.ts` 确认 diff 为：
  - `/` redirect 从 `/bom/list` 改为 `/home`
  - 新增 `/home` 路由，`name: HomePage`，`component: () => import('@/views/HomePage.vue')`
  - 新增 `/app/:pathMatch(.*)*` redirect `/home`
  - 新增 `/:pathMatch(.*)*` redirect `/home`
- `git status --short -- 06_前端/lingyi-pc/src/views/HomePage.vue 06_前端/lingyi-pc/src/router/index.ts` 显示：
  - `M 06_前端/lingyi-pc/src/router/index.ts`
  - `?? 06_前端/lingyi-pc/src/views/HomePage.vue`
- `stat` 显示两者 mtime 均为 `2026-04-24 15:15:32 +0800`。

允许修改：
- 新增 FIX1 归因报告：
  /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-164G_FIX1_RouterHomePage归因与结论修正报告.md
- 追加工程师会话日志：
  /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md

禁止修改：
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/router/index.ts
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/HomePage.vue
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/production/ProductionPlanList.vue
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/production/ProductionPlanDetail.vue
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/error_codes.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/production.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/production_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_production_plan.py
- /Users/hh/Desktop/领意服装管理系统/.gitignore
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/vite.config.ts
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/** 中任何其他文件
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/**
- /Users/hh/Desktop/领意服装管理系统/07_后端/**
- /Users/hh/Desktop/ccc/**
- LOOP_STATE / TASK_BOARD / HANDOVER_STATUS / INTERVENTION_QUEUE / AUTO_LOOP_PROTOCOL
- AGENTS 规则文件
- 架构师日志、审计官日志
- 任何生产/GitHub 管理配置

禁止动作：
- 禁止代码修改、清理、删除、回滚、还原 router 或 HomePage。
- 禁止运行 npm run dev/build/verify。
- 禁止运行前端 typecheck/contract 测试。
- 禁止运行后端测试。
- 禁止启动、停止、重载 CCC server。
- 禁止调用 /api/relay/start 或 /api/relay/stop。
- 禁止 push / PR / tag / 发布。

执行要求：
1. 只读核对 `src/router/index.ts` diff：
   git -C '/Users/hh/Desktop/领意服装管理系统' diff -- '06_前端/lingyi-pc/src/router/index.ts'
2. 只读核对 `HomePage.vue` 状态与 mtime：
   git -C '/Users/hh/Desktop/领意服装管理系统' status --short -- '06_前端/lingyi-pc/src/router/index.ts' '06_前端/lingyi-pc/src/views/HomePage.vue'
   stat -f '%Sm %N' -t '%Y-%m-%d %H:%M:%S %z' '/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/router/index.ts' '/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/HomePage.vue'
3. 只读检索历史日志/任务单，判断 `/home`、`HomePage`、catch-all redirect 是否有明确 TASK owner：
   - 可读：工程师会话日志、架构师会话日志、TASK-164A baseline 报告、相关开发计划文档。
   - 不得修改上述文件。
4. 输出 FIX1 归因报告，必须明确：
   - `src/router/index.ts` 中 `/home`、`HomePage`、catch-all redirect diff 的来源/owner 是否可确认。
   - `src/views/HomePage.vue` 是否应纳入 TASK-164G；如不能证明属于生产计划/Work Order 链路，必须结论为不纳入 TASK-164G。
   - TASK-164G 是否仍可整体重分类为 `HISTORICAL_TASK_OUTPUT_VERIFIED`。
   - 若 router/HomePage 不属于 TASK-164G，必须修正结论：不得声称七文件整体通过；只能对其余生产计划/Work Order 语义文件给出范围内 `HISTORICAL_TASK_OUTPUT_VERIFIED`，并保留 router/HomePage 为待归口 baseline diff。
5. 追加工程师会话日志。

必须验证：
- 只读命令完成。
- `git diff --name-only --` 限定本 FIX1 允许输出文件，确认本轮没有修改 router/HomePage/生产计划代码/测试。
- `git status --short -- '06_前端/lingyi-pc/src/router/index.ts' '06_前端/lingyi-pc/src/views/HomePage.vue'` 只用于证明现状，不得改变现状。

REPORT_BACK_FORMAT:

STATUS: READY_FOR_REVIEW
TASK_ID: TASK-164G
FIX_PASS: FIX1
ROLE: B Engineer

CHANGED_FILES:
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-164G_FIX1_RouterHomePage归因与结论修正报告.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md

CODE_CHANGED_IN_FIX1:
- NO

ROUTER_TOUCHED_IN_FIX1:
- NO

HOMEPAGE_TOUCHED_IN_FIX1:
- NO

ATTRIBUTION_RESULT:
- ROUTER_HOMEPAGE_NOT_TASK_164G / ROUTER_HOMEPAGE_TASK_164G_PROVEN / INCONCLUSIVE

OWNERSHIP_CORRECTION:
- TASK_164G_OVERALL_RECLASSIFICATION: HISTORICAL_TASK_OUTPUT_VERIFIED / PARTIAL_ONLY / BLOCKED
- PRODUCTION_SCOPE_RECLASSIFICATION: HISTORICAL_TASK_OUTPUT_VERIFIED / NEEDS_FIX / BLOCKED
- ROUTER_HOMEPAGE_RECLASSIFICATION: PENDING_OWNER / HISTORICAL_TASK_OUTPUT_VERIFIED / BLOCKED

READONLY_EVIDENCE:
- router diff summary:
- HomePage.vue status/mtime:
- history/task owner evidence:
- no-code-change evidence:

VALIDATION:
- readonly router/HomePage attribution commands: PASS/FAIL
- forbidden_files_touched: NO/YES

RISK_NOTES:
- 不代表剩余 business tracked diff、router/HomePage owner、REL-004/REL-005、生产联调、ERPNext 生产写入或业务功能放行

NEXT_ROLE: A Technical Architect
BLOCKERS:
- NONE 或具体阻塞
```
