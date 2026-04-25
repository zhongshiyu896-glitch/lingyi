# TASK-164G FIX1 Router/HomePage 归因与结论修正 C 复审任务单

```text
STATUS: READY_FOR_AUDIT
TASK_ID: TASK-164G
FIX_PASS: FIX1
ROLE: C Auditor

复审对象：
复审 B 对 TASK-164G FIX1 的 Router/HomePage 归因补证与归口结论修正，并判断是否可以关闭 C 原 FIX finding。

原工程任务单：
/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-164G_生产计划WorkOrder候选写入口回归归口_工程任务单.md

FIX1 工程任务单：
/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-164G_FIX1_RouterHomePage归因与结论修正_工程任务单.md

B FIX1 归因报告：
/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-164G_FIX1_RouterHomePage归因与结论修正报告.md

C 原 FINDINGS：
- `src/router/index.ts` 的实际 tracked diff 不是生产计划合法页面路由归口变更，而是将 `/` 重定向到 `/home`、新增 `HomePage` 路由、以及新增 `/app/:pathMatch` 和全局 catch-all redirect；这与 B 报告中“仅承载生产计划页面路由”及“七文件可归口到 TASK-004A/TASK-004B/TASK-015D~015F/TASK-021B~021D/TASK-100A~100D”的结论不一致。
- `src/router/index.ts` 当前引用未纳入 TASK-164G 回交范围的 untracked 文件 `06_前端/lingyi-pc/src/views/HomePage.vue`，该文件 mtime 与 router diff 同为 `2026-04-24 15:15:32 +0800`；虽早于 TASK-164G 窗口，但 B 未在本任务报告中归因，C 不能将该 router diff 纳入生产计划/Work Order 七文件历史归口。

B FIX1 回交摘要：
- CHANGED_FILES 仅为 FIX1 归因报告与工程师会话日志。
- CODE_CHANGED_IN_FIX1: NO
- ROUTER_TOUCHED_IN_FIX1: NO
- HOMEPAGE_TOUCHED_IN_FIX1: NO
- ATTRIBUTION_RESULT: ROUTER_HOMEPAGE_NOT_TASK_164G
- OWNERSHIP_CORRECTION:
  - TASK_164G_OVERALL_RECLASSIFICATION: PARTIAL_ONLY
  - PRODUCTION_SCOPE_RECLASSIFICATION: HISTORICAL_TASK_OUTPUT_VERIFIED
  - ROUTER_HOMEPAGE_RECLASSIFICATION: PENDING_OWNER
- READONLY_EVIDENCE:
  - router diff summary: `/ -> /home`、新增 `/home` HomePage route、`/app/:pathMatch -> /home`、`/:pathMatch -> /home`
  - HomePage.vue status/mtime: router 为 `M`，HomePage.vue 为 `??`，两者 mtime 均为 `2026-04-24 15:15:32 +0800`
  - history/task owner evidence: TASK-004/015/021/100 相关文档未检索到 `/home`、`HomePage`、catch-all redirect 明确 owner；TASK-164A 仅将 router 标为 BUSINESS_CODE_TRACKED_DIFF_NEEDS_OWNER

A intake 复核：
- 控制面已切换为 READY_FOR_AUDIT / C Auditor / TASK-164G。
- 工程师会话日志存在 TASK-164G FIX1 交付报告第107份。
- FIX1 归因报告已落盘，mtime 为 `2026-04-24 19:27:50 +0800`。
- `git status --short -- router/HomePage` 仍显示：
  - `M 06_前端/lingyi-pc/src/router/index.ts`
  - `?? 06_前端/lingyi-pc/src/views/HomePage.vue`
- `stat` 仍显示 router 与 HomePage.vue mtime 均为 `2026-04-24 15:15:32 +0800`，未见 FIX1 触碰证据。
- A 未运行前端命令、后端测试、CCC 启停/重载或 relay start/stop API。

C 必审范围：
1. FIX1 是否仅新增归因报告并追加工程师会话日志。
2. FIX1 是否未修改 router/HomePage/production 前后端文件/test_production_plan.py。
3. B 是否正确承认 `router/index.ts` 的 `/home`、HomePage、catch-all redirect 不属于 TASK-164G 生产计划/Work Order 链路。
4. B 是否正确将 `TASK_164G_OVERALL_RECLASSIFICATION` 从整体通过修正为 `PARTIAL_ONLY`。
5. B 是否可将 production 语义范围，即 ProductionPlanList.vue、ProductionPlanDetail.vue、error_codes.py、production.py、production_service.py、test_production_plan.py，维持为 `HISTORICAL_TASK_OUTPUT_VERIFIED`。
6. B 是否正确将 router/HomePage 保留为 `PENDING_OWNER`，不得在本任务内放行。
7. 原 TASK-164G 的生产范围验证证据是否仍可支撑 production semantic scope 局部归口。
8. 是否未触碰其他前端 src/scripts、后端非白名单文件、tests 非白名单文件、CCC、控制面、AGENTS、架构师日志、审计官日志、生产/GitHub 管理配置。
9. 是否不得把本复审结论外推为 router/HomePage owner、剩余 business tracked diff、REL-004/REL-005、生产联调、ERPNext 生产写入或业务功能放行。

禁止动作：
- 禁止 C 修改任何代码或文档。
- 禁止运行 npm run dev/build/verify/typecheck/contract 测试。
- 禁止运行后端测试。
- 禁止启动/停止/重载 CCC。
- 禁止调用 /api/relay/start 或 /api/relay/stop。
- 禁止 push / PR / tag / 发布。
- 禁止 GitHub Secret / Hosted Runner / Branch protection / Ruleset / ERPNext 生产联调 / 生产账号 / 主数据回填动作。

输出格式只能为以下之一，禁止裸 PASS：

AUDIT_RESULT: PASS
TASK_ID: TASK-164G
FIX_PASS: FIX1
ROLE: C Auditor
SCOPE_CONFIRMED:
- ...
RESIDUAL_RISK:
- NONE 或具体风险
NEXT_ROLE: A Technical Architect

或：

AUDIT_RESULT: FIX
TASK_ID: TASK-164G
FIX_PASS: FIX1
ROLE: C Auditor
FINDINGS:
- ...
REQUIRED_FIX:
- ...
NEXT_ROLE: A Technical Architect

或：

AUDIT_RESULT: BLOCK
TASK_ID: TASK-164G
FIX_PASS: FIX1
ROLE: C Auditor
BLOCKERS:
- ...
NEXT_ROLE: A Technical Architect
```
