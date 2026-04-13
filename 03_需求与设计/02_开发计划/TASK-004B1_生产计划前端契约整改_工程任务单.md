# TASK-004B1 生产计划前端契约整改工程任务单

- 任务编号：TASK-004B1
- 模块：生产计划集成
- 优先级：P0
- 版本：V1.0
- 更新时间：2026-04-13 19:14 CST
- 作者：技术架构师
- 审计来源：审计意见书第 64 份，TASK-004B 有条件通过，中危 3 / 低危 1
- 前置依赖：TASK-004B 已交付但存在契约问题；本任务只允许修复第 64 份审计指出的问题
- 架构依据：`/03_需求与设计/01_架构设计/05_模块设计_生产计划集成.md` V1.3；`ADR-061`
- 任务边界：只修 planned_start_date 契约、内部 worker 按钮权限过滤、详情页只读 DTO 字段、状态标签；允许最小后端 schema/model/service/migration 变更以闭合只读/事实字段，不得改生产计划主业务流程，不得进入 TASK-005/TASK-006

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-004B1
模块：生产计划前端契约整改
优先级：P0（前后端契约闭环）
════════════════════════════════════════════════════════════════════════════

【任务目标】
关闭审计意见书第 64 份的 4 个问题，使 TASK-004B 达到复审条件。

【架构决策】
1. `planned_start_date` 是本地生产计划事实字段，必须进入 `ly_production_plan`、创建计划请求、列表响应、详情响应和前端展示。
2. Work Order `start_date` 是创建 ERPNext Work Order outbox 时的工单开工日期；前端可默认带入 `planned_start_date`，但必须作为 `create-work-order` 请求体独立提交。
3. Work Order 映射区必须展示真实后端 DTO 字段：`erpnext_docstatus/erpnext_status/sync_status/last_synced_at`。后端暂未返回时必须补后端只读 DTO，不允许前端硬编码 `-` 冒充真实空值。
4. 物料快照 `checked_at` 是物料检查事实字段，必须由后端返回并由前端展示。
5. 内部 worker 权限不得进入前端按钮权限状态；不仅要过滤 actions，也要在 `button_permissions` 层强制清零。

【涉及文件】

允许修改：
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/production.ts
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/production/ProductionPlanList.vue
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/production/ProductionPlanDetail.vue
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/stores/permission.ts
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/auth.ts（仅限类型补齐）
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/production.py（仅限 `planned_start_date` 字段确认/补齐）
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/production.py（仅限 create/list/detail/material/work_order 只读 DTO 字段补齐）
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/production_service.py（仅限保存/返回上述字段，不改业务流程）
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/versions/task_004a_create_production_tables.py（仅限字段/索引幂等补齐）
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_production_plan.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_production_work_order_outbox.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_production_job_card_sync.py

禁止修改：
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/production_work_order_worker.py（除非只调整 DTO 返回引用，禁止改 worker 业务）
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/production_work_order_outbox_service.py（除非只读取已有字段，禁止改 claim/worker 逻辑）
- 任意 subcontract/workshop/BOM 后端业务文件
- 任意 TASK-005/TASK-006 文件

【整改清单】

| 编号 | 严重级别 | 整改项 | 必须结果 |
| --- | --- | --- | --- |
| FIX-001 | P2 | 闭合 `planned_start_date` 前后端契约 | 创建计划提交、后端保存、列表返回、详情返回、前端展示全部一致 |
| FIX-002 | P2 | 内部 worker 按钮权限清零 | `production:work_order_worker` 对应按钮权限不会进入 UI 状态 |
| FIX-003 | P2 | Work Order / 物料快照详情字段真实返回 | `erpnext_docstatus/erpnext_status/last_synced_at/checked_at` 来自后端 DTO，不用硬编码占位冒充字段 |
| FIX-004 | P3 | 补齐状态中文标签 | `draft/job_cards_synced/cancelled/failed` 等状态均有中文标签，未知状态原样展示 |

【FIX-001：planned_start_date 契约】

后端要求：
1. `ProductionPlanCreateRequest` 必须包含 `planned_start_date?: date | null`。
2. `ly_production_plan` 必须保存 `planned_start_date`；如当前表缺字段，迁移补齐。
3. 创建计划时，前端传入 `planned_start_date` 后，后端必须保存该值。
4. `ProductionPlanListItem` 必须返回 `planned_start_date`。
5. `ProductionPlanDetailData.plan` 必须返回 `planned_start_date`。
6. 幂等 `request_hash` 必须包含 `planned_start_date`；相同 idempotency_key 不同 planned_start_date 应返回 `PRODUCTION_IDEMPOTENCY_CONFLICT`。
7. 不允许前端或后端把 `planned_start_date` 当成权限资源来源。
8. 不允许由前端传入 `company`。

前端要求：
1. `ProductionPlanCreatePayload` 必须包含 `planned_start_date?: string`。
2. `createPlan()` 必须提交 `planned_start_date`。
3. 列表类型必须包含 `planned_start_date?: string | null`。
4. 详情类型必须包含 `planned_start_date?: string | null`。
5. 列表和详情展示后端返回的 `planned_start_date`。
6. 创建 Work Order 表单的 `start_date` 默认可取 `planned_start_date`，但字段名仍为 `start_date`，不得复用错误字段名。
7. 创建计划成功后刷新 `idempotency_key`。

【FIX-002：内部 worker 按钮权限过滤】

必须修改 `src/stores/permission.ts`：
1. 继续过滤 `actions` 中的内部动作。
2. 在 `button_permissions` 合并后，强制清零内部按钮字段。
3. 至少清零：
   - `work_order_worker`
   - `stock_sync_worker`
   - 如已有或新增：`job_card_sync_worker`
4. 即使后端返回 `button_permissions.work_order_worker=true`，前端状态也必须为 false。
5. 不得在任何 production 页面使用 `work_order_worker` 控制按钮。
6. 不得新增内部 worker UI 入口。

【FIX-003：详情字段真实返回】

后端 DTO 必须补齐：
1. Work Order 映射返回：
   - `work_order`
   - `erpnext_docstatus`
   - `erpnext_status`
   - `sync_status`
   - `last_synced_at`
2. 物料快照返回：
   - `checked_at`
   - 如已有字段：`uom/material_name` 也应按 schema 返回，不得前端伪造。
3. 字段无值时返回 `null`，不得省略字段导致前端类型漂移。
4. 详情服务必须在资源权限通过后读取子表字段。

前端必须修改：
1. Work Order 映射区展示后端 `erpnext_docstatus/erpnext_status/last_synced_at`。
2. 不得硬编码 `ERP Docstatus = '-'`、`ERP 状态 = '-'`。
3. 不得用 Job Card `synced_at` 冒充 Work Order `last_synced_at`。
4. 物料快照表展示后端 `checked_at`。
5. 如果后端返回 `null`，可显示 `-`；但类型和字段必须真实存在。

【FIX-004：状态标签】

列表和详情必须至少覆盖：
- `draft`：草稿
- `planned`：已计划
- `material_checked`：已检查物料
- `work_order_pending`：工单待同步
- `work_order_created`：工单已创建
- `job_cards_synced`：工序卡已同步
- `cancelled`：已取消
- `failed`：失败
- `pending`：待同步
- `processing`：同步中
- `succeeded`：已同步
- `dead`：死信
- `blocked_scope`：范围阻断

未知状态原样展示，不得报错。

【测试要求】

后端必须新增或补齐：
1. 创建计划传 `planned_start_date` 后，列表返回该字段。
2. 创建计划传 `planned_start_date` 后，详情返回该字段。
3. 同一 idempotency_key 不同 `planned_start_date` 返回 `PRODUCTION_IDEMPOTENCY_CONFLICT`。
4. Work Order link 返回 `erpnext_docstatus/erpnext_status/sync_status/last_synced_at`。
5. 物料快照返回 `checked_at`。
6. 无资源权限时不得读取子表详情。

前端必须新增或静态验证：
1. `ProductionPlanCreatePayload` 包含 `planned_start_date`。
2. create plan payload 包含 `planned_start_date`，不包含 `company`。
3. create Work Order payload 包含 `start_date`，且默认可从 `planned_start_date` 填入。
4. `button_permissions.work_order_worker=true` 输入后，store 状态中 `work_order_worker=false`。
5. production 视图中没有内部 worker 入口。
6. 状态标签覆盖 FIX-004 列出的状态。
7. 详情页未使用 Job Card `synced_at` 冒充 Work Order `last_synced_at`。

建议静态扫描命令：

```bash
cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc
rg "planned_start_date" src/api/production.ts src/views/production
rg "work_order_worker|stock_sync_worker|job_card_sync_worker" src/stores/permission.ts src/views/production
rg "job_cards.*synced_at|synced_at.*job_cards" src/views/production/ProductionPlanDetail.vue
rg "/api/production/internal|fetch\\(|/api/resource|ERPNext" src/api/production.ts src/views/production
```

后端验证命令：

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest -q tests/test_production_plan.py tests/test_production_work_order_outbox.py tests/test_production_job_card_sync.py
.venv/bin/python -m pytest -q
.venv/bin/python -m unittest discover
.venv/bin/python -m py_compile $(find app tests scripts -name '*.py' -print)
```

如前端目录仍无 `package.json`，交付回报必须继续说明无法执行 `npm run typecheck/build`。

【验收标准】

□ `planned_start_date` 已确认为生产计划事实字段，并在后端保存/返回。  
□ 新建计划前端 payload 提交 `planned_start_date`。  
□ 列表页和详情页展示真实 `planned_start_date`。  
□ Work Order `start_date` 仍作为 create-work-order 独立字段提交。  
□ `button_permissions.work_order_worker` 即使后端返回 true，前端状态也为 false。  
□ 前端没有内部 worker 入口。  
□ Work Order 映射区展示后端真实 `erpnext_docstatus/erpnext_status/last_synced_at`。  
□ 物料快照展示后端真实 `checked_at`。  
□ 状态中文标签覆盖任务单要求。  
□ 前端 production 代码无裸 fetch、无内部 worker 调用、无 ERPNext 直连。  
□ 后端 production 定向测试通过。  
□ 后端全量 pytest/unittest/py_compile 通过。  
□ 如 package.json 存在，前端 typecheck/build 通过；如不存在，交付回报说明无法执行。  
□ 未修改外发结算、工票计薪、BOM 主业务逻辑。  
□ 未进入 TASK-005/TASK-006。  

【禁止事项】

- 禁止删除计划开工日来规避问题；本次架构已确认 `planned_start_date` 是生产计划事实字段。
- 禁止把 `planned_start_date` 和 Work Order `start_date` 混成同一个含义。
- 禁止前端传 `company`。
- 禁止前端调用 `/api/production/internal/work-order-sync/run-once`。
- 禁止新增内部 worker 页面或按钮。
- 禁止裸 `fetch()`。
- 禁止前端直接调用 ERPNext。
- 禁止用硬编码 `-` 冒充后端字段已返回。
- 禁止修改生产计划 worker claim 逻辑。
- 禁止进入 TASK-005/TASK-006。

【交付回报格式】

工程师完成后按以下格式回复：

```text
TASK-004B1 已完成。

修复项：
1. FIX-001 planned_start_date 契约：...
2. FIX-002 内部 worker 权限过滤：...
3. FIX-003 详情真实字段：...
4. FIX-004 状态标签：...

涉及文件：
- ...

验证结果：
- 前端静态扫描：...
- production 定向 pytest：...
- 全量 pytest：...
- unittest discover：...
- py_compile：...
- npm run typecheck/build：...

未进入范围：
- 未修改外发结算
- 未修改工票计薪
- 未调用内部 worker
- 未直接调用 ERPNext
- 未进入 TASK-005/TASK-006
```

【前置依赖】
TASK-004B 有条件通过；本任务为契约整改。

【预计工时】
0.5-1 天

════════════════════════════════════════════════════════════════════════════
