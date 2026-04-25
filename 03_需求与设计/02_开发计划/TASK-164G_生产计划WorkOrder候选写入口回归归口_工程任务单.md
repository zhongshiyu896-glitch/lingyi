# TASK-164G 生产计划 Work Order 候选写入口回归归口工程任务单

```text
STATUS: READY_FOR_BUILD
TASK_ID: TASK-164G
ROLE: B Engineer

任务：
对 TASK-164A baseline 中的生产计划与 Work Order 候选写入口/Outbox 七文件做定向回归验证、必要最小修复与归口冻结。

本任务只覆盖以下 7 个 tracked diff：
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/router/index.ts
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/production/ProductionPlanList.vue
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/production/ProductionPlanDetail.vue
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/error_codes.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/production.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/production_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_production_plan.py

背景：
- TASK-164F 已由 C 返回 AUDIT_RESULT: PASS，仓库六文件归口完成。
- 当前剩余 business tracked diff 仍未全部归口完成。
- 本组七文件对应历史生产计划/工单链路：
  - TASK-004A / TASK-004B：生产计划后端基线、WorkOrderOutbox 与前端联动。
  - TASK-015D / TASK-015E / TASK-015F：生产工单最小合法写链、候选写入口局部解冻与普通入口边界冻结。
  - TASK-021B / TASK-021C / TASK-021D：生产计划本地草稿、候选写入口、内部 Worker 与 Outbox 闭环门禁。
  - TASK-100A~TASK-100D：生产计划创建、物料检查页面承载与状态白名单实现。
- 当前七文件 diff stat：7 files changed, 355 insertions(+), 24 deletions(-)

允许修改：
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/router/index.ts
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/production/ProductionPlanList.vue
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/production/ProductionPlanDetail.vue
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/error_codes.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/production.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/production_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_production_plan.py
- 新增归口冻结报告：
  /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-164G_生产计划WorkOrder候选写入口回归归口报告.md
- 追加工程师会话日志：
  /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md

禁止修改：
- /Users/hh/Desktop/领意服装管理系统/.gitignore
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/vite.config.ts
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/** 中除上述 3 个前端文件之外的任何文件
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/**
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/** 中除上述 3 个后端 app 文件之外的任何文件
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/** 中除 test_production_plan.py 之外的任何文件
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
- 禁止运行后端全量测试。
- 禁止启动、停止、重载 CCC server。
- 禁止调用 /api/relay/start 或 /api/relay/stop。
- 禁止 push / PR / tag / 发布。
- 禁止把本任务结论外推为剩余 business tracked diff 放行、dirty worktree 清理完成、REL-004/REL-005、生产联调、GitHub 管理配置、ERPNext 生产写入或业务功能放行。

执行要求：
1. 先只读核对七文件 diff：
   git -C '/Users/hh/Desktop/领意服装管理系统' diff -- '06_前端/lingyi-pc/src/router/index.ts' '06_前端/lingyi-pc/src/views/production/ProductionPlanList.vue' '06_前端/lingyi-pc/src/views/production/ProductionPlanDetail.vue' '07_后端/lingyi_service/app/core/error_codes.py' '07_后端/lingyi_service/app/routers/production.py' '07_后端/lingyi_service/app/services/production_service.py' '07_后端/lingyi_service/tests/test_production_plan.py'
2. 执行定向验证：
   - 在 /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc 下运行：
     npm run check:production-contracts
     npm run test:production-contracts
     npm run typecheck
   - 在 /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service 下运行：
     python3 -m py_compile app/core/error_codes.py app/routers/production.py app/services/production_service.py tests/test_production_plan.py
     .venv/bin/python -m pytest tests/test_production_plan.py -v --tb=short
3. 静态核对最小业务锚点：
   - `src/router/index.ts` 应承载生产计划合法页面路由，不得暴露 `/api/production/internal`、`work-order-sync/run-once` 或 worker 直跑入口。
   - `ProductionPlanList.vue` 应保留生产计划列表/创建入口、物料检查入口、Work Order 候选入口或状态展示的普通 UI 边界。
   - `ProductionPlanDetail.vue` 应保留 material-check、create-work-order 候选写入口、outbox/link 状态展示、冻结/候选提示与权限/状态 guard。
   - 前端 scoped 文件不得直连 ERPNext `/api/resource`、`/api/method`、`frappe`，不得裸 `fetch()` 绕过统一请求层。
   - `error_codes.py`、`routers/production.py`、`production_service.py` 应覆盖本地 outbox candidate、material-check 状态白名单、write_entry_frozen_reason、idempotency_key、outbox pending/event_key 边界。
   - 普通前端路径不得直接创建 ERPNext 生产 Work Order 或直接运行内部 worker，只能走受控 candidate/outbox/adapter 边界。
   - `test_production_plan.py` 应覆盖生产计划 CRUD/material-check、create-work-order 本地 outbox candidate、详情 work_order link 字段、物料检查仓库必填与状态白名单。
4. 如验证全部通过：
   - 不修改七文件代码。
   - 新增归口冻结报告并追加工程师日志。
5. 如验证失败：
   - 先判断失败是否落在本任务 7 文件范围内。
   - 仅当失败可归因到这 7 文件时，允许在这 7 文件内做最小修复。
   - 若失败来自其他 dirty diff、非白名单测试、依赖、环境、后端非白名单文件或前端非白名单文件，禁止扩大修改范围，回交 BLOCKERS 或 RISK_NOTES。

报告必须包含：
- 七文件 diff 摘要。
- 与 TASK-004A/TASK-004B/TASK-015D~015F/TASK-021B~021D/TASK-100A~100D 的归属关系。
- 每条验证命令结果。
- 静态业务锚点核对结果。
- 若有修复，说明修复是否仅限 7 文件。
- 是否可将这七文件从 BUSINESS_CODE_TRACKED_DIFF_NEEDS_OWNER 收敛为 HISTORICAL_TASK_OUTPUT_VERIFIED。
- 明确本任务不覆盖 warehouse / sales-inventory / factory-statement / style-profit / CCC 等其他 business diff。

必须验证：
- git -C '/Users/hh/Desktop/领意服装管理系统' diff --check -- '06_前端/lingyi-pc/src/router/index.ts' '06_前端/lingyi-pc/src/views/production/ProductionPlanList.vue' '06_前端/lingyi-pc/src/views/production/ProductionPlanDetail.vue' '07_后端/lingyi_service/app/core/error_codes.py' '07_后端/lingyi_service/app/routers/production.py' '07_后端/lingyi_service/app/services/production_service.py' '07_后端/lingyi_service/tests/test_production_plan.py'
- git -C '/Users/hh/Desktop/领意服装管理系统' diff --name-only -- '06_前端/lingyi-pc/src/router/index.ts' '06_前端/lingyi-pc/src/views/production/ProductionPlanList.vue' '06_前端/lingyi-pc/src/views/production/ProductionPlanDetail.vue' '07_后端/lingyi_service/app/core/error_codes.py' '07_后端/lingyi_service/app/routers/production.py' '07_后端/lingyi_service/app/services/production_service.py' '07_后端/lingyi_service/tests/test_production_plan.py' '03_需求与设计/02_开发计划/TASK-164G_生产计划WorkOrder候选写入口回归归口报告.md' '03_需求与设计/02_开发计划/工程师会话日志.md'
- 确认未修改禁止范围文件。

REPORT_BACK_FORMAT:

STATUS: READY_FOR_REVIEW
TASK_ID: TASK-164G
ROLE: B Engineer

CHANGED_FILES:
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-164G_生产计划WorkOrder候选写入口回归归口报告.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md
- 如确有本任务内修复，再列出七文件中的实际修改文件

CODE_CHANGED:
- YES/NO

SCOPE_FILES:
- src/router/index.ts
- ProductionPlanList.vue
- ProductionPlanDetail.vue
- error_codes.py
- production.py
- production_service.py
- test_production_plan.py

OWNERSHIP_RESULT:
- related_tasks: TASK-004A/TASK-004B/TASK-015D~015F/TASK-021B~021D/TASK-100A~100D
- can_reclassify_to: HISTORICAL_TASK_OUTPUT_VERIFIED / NEEDS_FIX / BLOCKED
- remaining_unowned_business_diffs_excluded: YES

VALIDATION:
- npm run check:production-contracts: PASS/FAIL/NOT_RUN
- npm run test:production-contracts: PASS/FAIL/NOT_RUN
- npm run typecheck: PASS/FAIL/NOT_RUN
- python3 -m py_compile production backend/test files: PASS/FAIL/NOT_RUN
- targeted production pytest: PASS/FAIL/NOT_RUN
- static_business_anchors: PASS/FAIL
- git diff --check: PASS/FAIL
- forbidden_files_touched: NO/YES

RISK_NOTES:
- 未运行 npm run dev/build/verify
- 未运行后端全量测试
- 未触碰其他前端 src/scripts、后端非白名单文件、tests 非白名单文件、CCC、控制面、AGENTS、架构师日志、审计官日志、生产/GitHub 管理配置
- 不代表剩余 business tracked diff、REL-004/REL-005、生产联调、ERPNext 生产写入或业务功能放行

NEXT_ROLE: A Technical Architect
BLOCKERS:
- NONE 或具体阻塞
```
