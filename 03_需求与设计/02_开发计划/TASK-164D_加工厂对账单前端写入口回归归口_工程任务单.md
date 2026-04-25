# TASK-164D 加工厂对账单前端写入口回归归口工程任务单

```text
STATUS: READY_FOR_BUILD
TASK_ID: TASK-164D
ROLE: B Engineer

任务：
对 TASK-164A baseline 中的加工厂对账单前端 API / 列表页 / 详情页三文件做定向回归验证、必要最小修复与归口冻结。

本任务只覆盖以下 3 个 tracked diff：
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/factory_statement.ts
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementList.vue
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementDetail.vue

背景：
- TASK-164C 已由 C 返回 AUDIT_RESULT: PASS，前端 contract engine / request auth 三文件归口完成。
- 剩余 business tracked diff 尚未归口完成。
- 本组三文件对应历史任务：
  - TASK-120C：加工厂对账单创建/确认/取消可放行补证，冻结列表页创建、详情页确认/取消、factory_statement.ts 最小 API 承载。
  - TASK-120B：加工厂对账单前端实现，补齐创建入口、确认/取消入口、权限/状态/payable guard、idempotency_key 与 API 封装。
- 当前三文件 diff stat：3 files changed, 410 insertions(+)

允许修改：
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/factory_statement.ts
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementList.vue
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementDetail.vue
- 新增归口冻结报告：
  /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-164D_加工厂对账单前端写入口回归归口报告.md
- 追加工程师会话日志：
  /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md

禁止修改：
- /Users/hh/Desktop/领意服装管理系统/.gitignore
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/vite.config.ts
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/** 中除上述 3 个 factory_statement 文件之外的任何文件
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
1. 先只读核对三文件 diff：
   git -C '/Users/hh/Desktop/领意服装管理系统' diff -- '06_前端/lingyi-pc/src/api/factory_statement.ts' '06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementList.vue' '06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementDetail.vue'
2. 执行定向验证，在 /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc 下运行：
   - npm run check:factory-statement-contracts
   - npm run test:factory-statement-contracts
   - npm run typecheck
3. 静态核对最小业务锚点：
   - `factory_statement.ts` 应包含 createFactoryStatement / confirmFactoryStatement / cancelFactoryStatement 与 idempotency_key payload。
   - `FactoryStatementList.vue` 应包含创建入口、权限 guard、日期范围校验、idempotency_key。
   - `FactoryStatementDetail.vue` 应包含确认/取消入口、权限 guard、状态 guard、payable/outbox 阻断、idempotency_key。
4. 如验证全部通过：
   - 不修改三文件代码。
   - 新增归口冻结报告并追加工程师日志。
5. 如验证失败：
   - 先判断失败是否落在本任务 3 文件范围内。
   - 仅当失败可归因到这 3 文件时，允许在这 3 文件内做最小修复。
   - 若失败来自其他 dirty diff、依赖、环境、后端或非白名单文件，禁止扩大修改范围，回交 BLOCKERS 或 RISK_NOTES。

报告必须包含：
- 三文件 diff 摘要。
- 与 TASK-120C / TASK-120B 的归属关系。
- 每条验证命令结果。
- 静态业务锚点核对结果。
- 若有修复，说明修复是否仅限 3 文件。
- 是否可将这三文件从 BUSINESS_CODE_TRACKED_DIFF_NEEDS_OWNER 收敛为 HISTORICAL_TASK_OUTPUT_VERIFIED。
- 明确本任务不覆盖 sales-inventory / warehouse / production / backend / CCC 等其他 business diff。

必须验证：
- git -C '/Users/hh/Desktop/领意服装管理系统' diff --check -- '06_前端/lingyi-pc/src/api/factory_statement.ts' '06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementList.vue' '06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementDetail.vue'
- git -C '/Users/hh/Desktop/领意服装管理系统' diff --name-only -- '06_前端/lingyi-pc/src/api/factory_statement.ts' '06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementList.vue' '06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementDetail.vue' '03_需求与设计/02_开发计划/TASK-164D_加工厂对账单前端写入口回归归口报告.md' '03_需求与设计/02_开发计划/工程师会话日志.md'
- 确认未修改禁止范围文件。

REPORT_BACK_FORMAT:

STATUS: READY_FOR_REVIEW
TASK_ID: TASK-164D
ROLE: B Engineer

CHANGED_FILES:
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-164D_加工厂对账单前端写入口回归归口报告.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md
- 如确有本任务内修复，再列出三文件中的实际修改文件

CODE_CHANGED:
- YES/NO

SCOPE_FILES:
- factory_statement.ts
- FactoryStatementList.vue
- FactoryStatementDetail.vue

OWNERSHIP_RESULT:
- related_tasks: TASK-120C / TASK-120B
- can_reclassify_to: HISTORICAL_TASK_OUTPUT_VERIFIED / NEEDS_FIX / BLOCKED
- remaining_unowned_business_diffs_excluded: YES

VALIDATION:
- npm run check:factory-statement-contracts: PASS/FAIL/NOT_RUN
- npm run test:factory-statement-contracts: PASS/FAIL/NOT_RUN
- npm run typecheck: PASS/FAIL/NOT_RUN
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
