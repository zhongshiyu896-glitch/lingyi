# TASK-164F 仓库成品入仓与 Stock Entry 草稿回归归口工程任务单

```text
STATUS: READY_FOR_BUILD
TASK_ID: TASK-164F
ROLE: B Engineer

任务：
对 TASK-164A baseline 中的仓库成品入仓与 Stock Entry 草稿/Outbox 六文件做定向回归验证、必要最小修复与归口冻结。

本任务只覆盖以下 6 个 tracked diff：
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/warehouse.ts
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/warehouse/WarehouseDashboard.vue
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/warehouse.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/warehouse.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_warehouse_adapter.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/warehouse_service.py

背景：
- TASK-164E 已由 C 返回 AUDIT_RESULT: PASS，销售库存三文件归口完成。
- 当前剩余 business tracked diff 仍未全部归口完成。
- 本组六文件对应历史仓库链路：
  - TASK-050A~TASK-050I：仓库管理增强与本地封版链。
  - TASK-090C：成品入仓交互基线与修复链。
- 当前六文件 diff stat：6 files changed, 861 insertions(+), 26 deletions(-)

允许修改：
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/warehouse.ts
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/warehouse/WarehouseDashboard.vue
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/warehouse.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/warehouse.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_warehouse_adapter.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/warehouse_service.py
- 新增归口冻结报告：
  /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-164F_仓库成品入仓与StockEntry草稿回归归口报告.md
- 追加工程师会话日志：
  /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md

禁止修改：
- /Users/hh/Desktop/领意服装管理系统/.gitignore
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/vite.config.ts
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/** 中除上述 2 个 warehouse 前端文件之外的任何文件
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/**
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/** 中除上述 4 个 warehouse 后端文件之外的任何文件
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/**
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
1. 先只读核对六文件 diff：
   git -C '/Users/hh/Desktop/领意服装管理系统' diff -- '06_前端/lingyi-pc/src/api/warehouse.ts' '06_前端/lingyi-pc/src/views/warehouse/WarehouseDashboard.vue' '07_后端/lingyi_service/app/routers/warehouse.py' '07_后端/lingyi_service/app/schemas/warehouse.py' '07_后端/lingyi_service/app/services/erpnext_warehouse_adapter.py' '07_后端/lingyi_service/app/services/warehouse_service.py'
2. 执行定向验证：
   - 在 /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc 下运行：
     npm run typecheck
   - 在 /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service 下运行：
     python3 -m py_compile app/routers/warehouse.py app/schemas/warehouse.py app/services/warehouse_service.py app/services/erpnext_warehouse_adapter.py
   - 在 /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service 下运行定向 pytest：
     .venv/bin/python -m pytest tests/test_warehouse_finished_goods_inbound.py tests/test_warehouse_stock_entry_draft.py tests/test_warehouse_stock_entry_worker.py tests/test_warehouse_inventory_count.py tests/test_warehouse_readonly_baseline.py tests/test_warehouse_traceability_readonly.py tests/test_warehouse_export_diagnostic.py tests/test_warehouse_worker_permissions.py -v --tb=short
3. 静态核对最小业务锚点：
   - `warehouse.ts` 应包含 finished-goods inbound candidates、Stock Entry draft create/detail/cancel/outbox-status API。
   - `warehouse.ts` 应保留 `idempotency_key`、`strict_alloc`、`zero_placeholder_fallback` 等入仓/草稿参数。
   - `WarehouseDashboard.vue` 应包含成品入仓入口、Stock Entry 草稿创建/详情/取消/状态轮询入口。
   - `WarehouseDashboard.vue` 应包含 `permissionStore` 与 `warehouse:stock_entry_draft`、`warehouse:stock_entry_cancel` 权限 guard，并在无权限时禁用或提前返回。
   - 后端 router/schema/service/adapter 应覆盖 finished-goods inbound candidates、Stock Entry draft create/detail/cancel、outbox status/worker/adapter 边界。
   - UI 路径不得直接提交 ERPNext 生产 Stock Entry，只能走受控 draft/outbox/adapter 边界。
4. 如验证全部通过：
   - 不修改六文件代码。
   - 新增归口冻结报告并追加工程师日志。
5. 如验证失败：
   - 先判断失败是否落在本任务 6 文件范围内。
   - 仅当失败可归因到这 6 文件时，允许在这 6 文件内做最小修复。
   - 若失败来自其他 dirty diff、测试代码、依赖、环境、后端非白名单文件或前端非白名单文件，禁止扩大修改范围，回交 BLOCKERS 或 RISK_NOTES。

报告必须包含：
- 六文件 diff 摘要。
- 与 TASK-050A~TASK-050I / TASK-090C 的归属关系。
- 每条验证命令结果。
- 静态业务锚点核对结果。
- 若有修复，说明修复是否仅限 6 文件。
- 是否可将这六文件从 BUSINESS_CODE_TRACKED_DIFF_NEEDS_OWNER 收敛为 HISTORICAL_TASK_OUTPUT_VERIFIED。
- 明确本任务不覆盖 sales-inventory / factory-statement / production / style-profit / CCC 等其他 business diff。

必须验证：
- git -C '/Users/hh/Desktop/领意服装管理系统' diff --check -- '06_前端/lingyi-pc/src/api/warehouse.ts' '06_前端/lingyi-pc/src/views/warehouse/WarehouseDashboard.vue' '07_后端/lingyi_service/app/routers/warehouse.py' '07_后端/lingyi_service/app/schemas/warehouse.py' '07_后端/lingyi_service/app/services/erpnext_warehouse_adapter.py' '07_后端/lingyi_service/app/services/warehouse_service.py'
- git -C '/Users/hh/Desktop/领意服装管理系统' diff --name-only -- '06_前端/lingyi-pc/src/api/warehouse.ts' '06_前端/lingyi-pc/src/views/warehouse/WarehouseDashboard.vue' '07_后端/lingyi_service/app/routers/warehouse.py' '07_后端/lingyi_service/app/schemas/warehouse.py' '07_后端/lingyi_service/app/services/erpnext_warehouse_adapter.py' '07_后端/lingyi_service/app/services/warehouse_service.py' '03_需求与设计/02_开发计划/TASK-164F_仓库成品入仓与StockEntry草稿回归归口报告.md' '03_需求与设计/02_开发计划/工程师会话日志.md'
- 确认未修改禁止范围文件。

REPORT_BACK_FORMAT:

STATUS: READY_FOR_REVIEW
TASK_ID: TASK-164F
ROLE: B Engineer

CHANGED_FILES:
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-164F_仓库成品入仓与StockEntry草稿回归归口报告.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md
- 如确有本任务内修复，再列出六文件中的实际修改文件

CODE_CHANGED:
- YES/NO

SCOPE_FILES:
- warehouse.ts
- WarehouseDashboard.vue
- warehouse.py
- schemas/warehouse.py
- erpnext_warehouse_adapter.py
- warehouse_service.py

OWNERSHIP_RESULT:
- related_tasks: TASK-050A~TASK-050I / TASK-090C
- can_reclassify_to: HISTORICAL_TASK_OUTPUT_VERIFIED / NEEDS_FIX / BLOCKED
- remaining_unowned_business_diffs_excluded: YES

VALIDATION:
- npm run typecheck: PASS/FAIL/NOT_RUN
- python3 -m py_compile warehouse backend files: PASS/FAIL/NOT_RUN
- targeted warehouse pytest: PASS/FAIL/NOT_RUN
- static_business_anchors: PASS/FAIL
- git diff --check: PASS/FAIL
- forbidden_files_touched: NO/YES

RISK_NOTES:
- 未运行 npm run dev/build/verify
- 未运行后端全量测试
- 未触碰其他前端 src/scripts、后端非白名单文件、tests、CCC、控制面、AGENTS、架构师日志、审计官日志、生产/GitHub 管理配置
- 不代表剩余 business tracked diff、REL-004/REL-005、生产联调、ERPNext 生产写入或业务功能放行

NEXT_ROLE: A Technical Architect
BLOCKERS:
- NONE 或具体阻塞
```
