# TASK-164G 生产计划 Work Order 候选写入口回归归口 C 审计任务单

```text
STATUS: READY_FOR_AUDIT
TASK_ID: TASK-164G
ROLE: C Auditor

审计对象：
B 对 TASK-164G 的实现回交：生产计划与 Work Order 候选写入口/Outbox 七文件回归归口。

原工程任务单：
/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-164G_生产计划WorkOrder候选写入口回归归口_工程任务单.md

B 归口报告：
/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-164G_生产计划WorkOrder候选写入口回归归口报告.md

B 回交摘要：
- CHANGED_FILES 仅声明新增归口报告与追加工程师会话日志。
- CODE_CHANGED: NO
- SCOPE_FILES:
  - src/router/index.ts
  - ProductionPlanList.vue
  - ProductionPlanDetail.vue
  - error_codes.py
  - production.py
  - production_service.py
  - test_production_plan.py
- related_tasks: TASK-004A/TASK-004B/TASK-015D~015F/TASK-021B~021D/TASK-100A~100D
- can_reclassify_to: HISTORICAL_TASK_OUTPUT_VERIFIED
- VALIDATION:
  - npm run check:production-contracts: PASS
  - npm run test:production-contracts: PASS
  - npm run typecheck: PASS
  - python3 -m py_compile production backend/test files: PASS
  - targeted production pytest: PASS（17 passed, 18 warnings）
  - static_business_anchors: PASS
  - git diff --check: PASS
  - forbidden_files_touched: NO

A intake 复核：
- 控制面已切换为 READY_FOR_AUDIT / C Auditor / TASK-164G。
- 工程师会话日志存在 2026-04-24 19:16 TASK-164G 交付报告第106份。
- B 归口报告已落盘。
- 七个 scoped 文件仍为 tracked diff，但 mtime 均早于 TASK-164G 窗口，未见 TASK-164G 窗口新增代码修改证据：
  - /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/router/index.ts
  - /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/production/ProductionPlanList.vue
  - /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/production/ProductionPlanDetail.vue
  - /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/error_codes.py
  - /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/production.py
  - /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/production_service.py
  - /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_production_plan.py
- A 未运行前端命令、后端测试、CCC 启停/重载或 relay start/stop API。

C 必审范围：
1. B 本轮新增/追加交付物是否限定为 TASK-164G 归口报告与工程师会话日志。
2. 七个 scope 文件是否仍为历史 tracked diff，且未见 TASK-164G 窗口新增代码修改证据。
3. 七文件 diff 语义是否可对应 TASK-004A/TASK-004B/TASK-015D~015F/TASK-021B~021D/TASK-100A~100D 历史生产计划/工单链路。
4. `src/router/index.ts` 是否仅承载生产计划合法页面路由，且未暴露 `/api/production/internal`、`work-order-sync/run-once` 或 worker 直跑入口。
5. `ProductionPlanList.vue` 与 `ProductionPlanDetail.vue` 是否覆盖生产计划列表/详情、material-check、create-work-order 候选写入口、outbox/link 状态、权限/状态 guard 与冻结提示。
6. 前端 scoped 文件是否未直连 ERPNext `/api/resource`、`/api/method`、`frappe`，且未裸 `fetch()` 绕过统一请求层。
7. `error_codes.py`、`routers/production.py`、`production_service.py` 是否覆盖本地 outbox candidate、material-check 状态白名单、write_entry_frozen_reason、idempotency_key、outbox pending/event_key 边界。
8. `test_production_plan.py` 是否覆盖生产计划 CRUD/material-check、create-work-order 本地 outbox candidate、详情 work_order link 字段、物料检查仓库必填与状态白名单。
9. B 报告中的 production contracts、typecheck、后端 py_compile、定向 pytest、静态业务锚点与 scoped git diff --check 是否足以支撑七文件重分类为 `HISTORICAL_TASK_OUTPUT_VERIFIED`。
10. 是否未触碰其他前端 src/scripts、后端非白名单文件、tests 非白名单文件、CCC、控制面、AGENTS、架构师日志、审计官日志、生产/GitHub 管理配置。
11. 是否不得把本任务结论外推为剩余 business tracked diff、REL-004/REL-005、生产联调、ERPNext 生产写入或业务功能放行。

禁止动作：
- 禁止 C 修改任何代码或文档。
- 禁止运行 npm run dev/build/verify。
- 禁止运行后端全量测试。
- 禁止启动/停止/重载 CCC。
- 禁止调用 /api/relay/start 或 /api/relay/stop。
- 禁止 push / PR / tag / 发布。
- 禁止 GitHub Secret / Hosted Runner / Branch protection / Ruleset / ERPNext 生产联调 / 生产账号 / 主数据回填动作。

输出格式只能为以下之一，禁止裸 PASS：

AUDIT_RESULT: PASS
TASK_ID: TASK-164G
ROLE: C Auditor
SCOPE_CONFIRMED:
- ...
RESIDUAL_RISK:
- NONE 或具体风险
NEXT_ROLE: A Technical Architect

或：

AUDIT_RESULT: FIX
TASK_ID: TASK-164G
ROLE: C Auditor
FINDINGS:
- ...
REQUIRED_FIX:
- ...
NEXT_ROLE: A Technical Architect

或：

AUDIT_RESULT: BLOCK
TASK_ID: TASK-164G
ROLE: C Auditor
BLOCKERS:
- ...
NEXT_ROLE: A Technical Architect
```
