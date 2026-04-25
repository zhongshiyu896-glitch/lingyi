# TASK-164H FIX1 AppShell Router/HomePage 与 Quality Contract 阻塞最小修复 C 审计任务单

```text
STATUS: READY_FOR_AUDIT
TASK_ID: TASK-164H
FIX_PASS: FIX1
ROLE: C Auditor

审计对象：
B 对 TASK-164H 原回交与 FIX1 回交的合并结果：App Shell Router/HomePage 回归归口 + Quality Contract blocker 最小修复。

原工程任务单：
/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-164H_AppShellRouterHomePage回归归口_工程任务单.md

FIX1 工程任务单：
/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-164H_FIX1_QualityContract阻塞最小修复_工程任务单.md

B 原回交报告：
/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-164H_AppShellRouterHomePage回归归口报告.md

B FIX1 回交报告：
/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-164H_FIX1_QualityContract阻塞最小修复报告.md

B 回交摘要：
- 原 TASK-164H 中，HomePage.vue 做了最小 UI 文案修正：`local.dev/System Manager` fallback 改为 `未获取到会话/未获取到角色`，router 逻辑未改。
- 原 TASK-164H 因 `npm run check:quality-contracts` 在非原白名单 `src/api/quality.ts` 失败而 BLOCKED。
- FIX1 中，B 修改 `src/api/quality.ts` 清除 quality surface 裸 `fetch()` 与 `URL.createObjectURL()`，新增 `updateQualityInspection`，保留 `updateDraftInspection` 兼容别名，并将导出请求改走 `requestFile`。
- B 声明 FIX1 后所有必跑 frontend contract checks 均 PASS。

A intake 复核：
- 控制面已切换为 READY_FOR_AUDIT / C Auditor / TASK-164H。
- `quality.ts` 当前 diff：引入 `requestFile`；新增 `updateQualityInspection(...)`；`updateDraftInspection(...)` 转调 `updateQualityInspection(...)`；`exportQualityInspectionsFile(...)` 改为 `requestFile(...)` + `FileReader.readAsDataURL` 触发下载。
- A 只读静态核对：`quality.ts` 中未命中裸 `fetch(`、`axios`、`URL.createObjectURL`、`window.URL.createObjectURL`、`/api/resource`、`/api/method`、`frappe`、`/api/quality/diagnostic`、`quality/internal`、`run-once`；命中 `requestFile`、`updateQualityInspection`、`updateDraftInspection`。
- A 执行限定 `git diff --check -- src/api/quality.ts src/router/index.ts src/views/HomePage.vue` 无输出。
- 当前限定路径状态：`src/api/quality.ts` modified，`src/router/index.ts` modified（历史 baseline diff），`src/views/HomePage.vue` untracked，工程师日志 modified，两个 TASK-164H 报告为新增文档。

C 必审范围：
1. 原 TASK-164H 与 FIX1 是否为同一 `TASK_ID=TASK-164H` 的合法闭环。
2. B 原回交 BLOCKED 是否已由 FIX1 合法清除，不得跳过失败门禁直接放行。
3. `src/api/quality.ts` 修改是否限定为 quality contract blocker 最小修复。
4. `quality.ts` 是否无裸 `fetch(`、无 `axios`、无 `URL.createObjectURL(` / `window.URL.createObjectURL(`。
5. `quality.ts` 是否存在 `updateQualityInspection`，且 `updateDraftInspection` 兼容旧调用。
6. 导出链路是否继续走受控 `requestFile` 边界；`FileReader.readAsDataURL` 仅用于用户下载，不得形成动态 import、worker、script、internal、diagnostic 或 ERPNext 直连绕过。
7. `quality.ts` 是否未新增 `/api/resource`、`/api/method`、`frappe`、`/api/quality/diagnostic`、`quality/internal`、`run-once`、worker/debug/internal 入口。
8. `HomePage.vue` 是否仅保留 TASK-164H 的最小会话文案修正，不新增真实鉴权/角色注入副作用。
9. `router/index.ts` 的 `/home`、HomePage 路由、`/app/:pathMatch` 与 catch-all redirect 是否可归口为 APP_SHELL_ROUTER_HOMEPAGE，且未暴露 internal/run-once/worker/debug/diagnostic 路由。
10. B 报告中的全部验证是否真实、充分，尤其 `check:quality-contracts` 从 FAIL 变 PASS 后未引入其他 contract 回退。
11. 是否未修改禁止路径：`.gitignore`、`vite.config.ts`、其他前端 src/scripts、后端、CCC、控制面、AGENTS、架构师日志、审计官日志、生产/GitHub 管理配置。
12. 本结论不得外推为质量主链整体放行、剩余 business diff 清理完成、REL-004/REL-005、生产联调、ERPNext 生产写入或业务功能放行。

建议复核命令（只读/验证，不得修改）：
- cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc
- npm run check:quality-contracts
- npm run test:quality-contracts
- npm run typecheck
- npm run check:production-contracts
- npm run test:production-contracts
- npm run check:sales-inventory-contracts
- npm run test:sales-inventory-contracts
- npm run check:factory-statement-contracts
- npm run test:factory-statement-contracts
- npm run check:style-profit-contracts
- npm run test:style-profit-contracts
- git -C /Users/hh/Desktop/领意服装管理系统 diff --check -- 06_前端/lingyi-pc/src/api/quality.ts 06_前端/lingyi-pc/src/router/index.ts 06_前端/lingyi-pc/src/views/HomePage.vue

禁止动作：
- 禁止 C 修改任何代码或文档。
- 禁止 npm run dev/build/verify。
- 禁止后端测试。
- 禁止 CCC 启停/重载。
- 禁止 /api/relay/start 或 /api/relay/stop。
- 禁止 push / PR / tag / 发布。
- 禁止 GitHub Secret / Hosted Runner / Branch protection / Ruleset / ERPNext 生产联调 / 生产账号 / 主数据回填动作。
- 禁止把本任务结论外推为质量主链整体、remaining business diff、REL-004/REL-005、生产联调或业务功能放行。

输出格式只能为以下之一，禁止裸 PASS：

AUDIT_RESULT: PASS
TASK_ID: TASK-164H
FIX_PASS: FIX1
ROLE: C Auditor
SCOPE_CONFIRMED:
- ...
RESIDUAL_RISK:
- NONE 或具体风险
NEXT_ROLE: A Technical Architect

或：

AUDIT_RESULT: FIX
TASK_ID: TASK-164H
FIX_PASS: FIX1
ROLE: C Auditor
FINDINGS:
- ...
REQUIRED_FIX:
- ...
NEXT_ROLE: A Technical Architect

或：

AUDIT_RESULT: BLOCK
TASK_ID: TASK-164H
FIX_PASS: FIX1
ROLE: C Auditor
BLOCKERS:
- ...
NEXT_ROLE: A Technical Architect
```
