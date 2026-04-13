# TASK-004B 生产计划前端联动工程任务单

- 任务编号：TASK-004B
- 模块：生产计划集成
- 优先级：P0
- 版本：V1.0
- 更新时间：2026-04-13 18:57 CST
- 作者：技术架构师
- 审计来源：审计意见书第 63 份，TASK-004A1 通过；保留风险为 PostgreSQL worker 非 skip 证据、库存可用量占位、部分字段差异
- 前置依赖：TASK-004A1 已通过；后端 production 接口契约已冻结
- 架构依据：`/03_需求与设计/01_架构设计/05_模块设计_生产计划集成.md` V1.2；`ADR-060`
- 任务边界：只做 Vue3 前端页面、API 封装、权限按钮、错误提示和前端契约测试；不改 production 后端业务逻辑，不做内部 worker 页面，不做生产入库，不做 TASK-005/TASK-006

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-004B
模块：生产计划前端联动
优先级：P0（生产主链路前端闭环）
════════════════════════════════════════════════════════════════════════════

【任务目标】
实现生产计划前端列表、详情、创建计划、物料检查、创建 Work Order outbox、同步 Job Card 的页面闭环。

【模块概述】
生产计划前端负责把已通过后端接口暴露给生产计划员使用。用户在列表页查询生产计划、创建计划；在详情页查看物料检查快照、Work Order 同步状态和 Job Card 映射，并触发物料检查、创建 Work Order outbox、同步 Job Card。前端只调用 FastAPI `/api/production/` 接口，不直接调用 ERPNext，不展示或触发内部 worker。按钮权限必须来自 `/api/auth/actions?module=production`，不能只靠前端状态判断替代后端鉴权。

【涉及文件】

新建：
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/production.ts
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/production/ProductionPlanList.vue
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/production/ProductionPlanDetail.vue

修改：
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/router/index.ts
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/stores/permission.ts
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/auth.ts（如需补充 production button_permissions 类型）

禁止修改：
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/production_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/production_work_order_worker.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/production_work_order_outbox_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/production.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/versions/task_004a_create_production_tables.py
- 任意 subcontract/workshop/BOM 后端业务文件
- 任意 TASK-005/TASK-006 文件

【API 封装】

必须在 `src/api/production.ts` 中封装以下接口，且必须全部复用 `src/api/request.ts` 的 `request()`：

| 接口名称 | HTTP 方法 | 路径 | 前端方法名 | 入参 | 出参 |
| --- | --- | --- | --- | --- | --- |
| 创建生产计划 | POST | `/api/production/plans` | `createProductionPlan` | `sales_order, sales_order_item?, bom_id?, planned_qty, planned_start_date?, idempotency_key` | `plan_id, plan_no, status` |
| 查询生产计划 | GET | `/api/production/plans` | `fetchProductionPlans` | `sales_order?, item_code?, status?, page, page_size` | `items,total,page,page_size` |
| 查询生产计划详情 | GET | `/api/production/plans/{plan_id}` | `fetchProductionPlanDetail` | `plan_id` | `plan, materials, work_order, job_cards` |
| 物料检查 | POST | `/api/production/plans/{plan_id}/material-check` | `checkProductionMaterials` | `warehouse` | `material_items, shortage_items, checked_at` |
| 创建 Work Order | POST | `/api/production/plans/{plan_id}/create-work-order` | `createProductionWorkOrder` | `fg_warehouse,wip_warehouse,start_date,idempotency_key` | `outbox_id,sync_status,work_order?` |
| 同步 Job Card | POST | `/api/production/work-orders/{work_order}/sync-job-cards` | `syncProductionJobCards` | `work_order` | `job_cards,sync_status` |

禁止：
1. 禁止在 `production.ts` 或 production 视图中直接使用裸 `fetch()`。
2. 禁止重复实现 Authorization/Cookie 请求逻辑。
3. 禁止调用 `/api/production/internal/work-order-sync/run-once`。
4. 禁止前端直接调用 ERPNext REST API。
5. 禁止前端传 company 作为创建计划或权限判断依据。

【权限按钮】

`src/stores/permission.ts` 必须补齐 production 按钮权限字段：
- `plan_create`
- `material_check`
- `work_order_create`
- `job_card_sync`

必须把内部动作加入前端过滤：
- `production:work_order_worker`

页面加载要求：
1. 生产计划列表页 mounted 时调用 `loadCurrentUser()` 和 `loadModuleActions('production')`。
2. 生产计划详情页 mounted 时调用 `loadCurrentUser()` 和 `loadModuleActions('production')`。
3. 无 `read` 权限时显示 `无生产计划查看权限`，不得请求详情子表。
4. 创建计划按钮只在 `plan_create` 权限下显示。
5. 物料检查按钮只在 `material_check` 权限下显示。
6. 创建 Work Order 按钮只在 `work_order_create` 权限下显示。
7. 同步 Job Card 按钮只在 `job_card_sync` 权限下显示。
8. 页面按钮隐藏不能替代后端鉴权；403 必须显示统一错误提示。

【页面 1：ProductionPlanList.vue】

路径：`/production/plans`

页面内容：
1. 查询条件：`sales_order`、`item_code`、`status`。
2. 分页：`page/page_size`。
3. 表格列：`plan_no`、`company`、`sales_order`、`sales_order_item`、`item_code`、`bom_id`、`planned_qty`、`planned_start_date`、`status`、`work_order`、`sync_status`、`created_at`。
4. 操作列：详情。
5. 新建生产计划弹窗。

新建生产计划弹窗字段：
- `sales_order`
- `sales_order_item`（可选）
- `bom_id`（可选）
- `planned_qty`
- `planned_start_date`（可选）
- `idempotency_key`

规则：
1. 不允许用户输入 `company`。
2. `idempotency_key` 默认自动生成，允许用户复制查看，但创建成功后必须刷新。
3. `planned_qty` 必须大于 0；前端先拦截明显非法值，但仍以后端校验为准。
4. 创建成功后关闭弹窗并刷新列表。
5. 创建失败时展示后端统一错误 message。
6. 状态展示必须使用中文标签，未知状态原样展示。

【页面 2：ProductionPlanDetail.vue】

路径：`/production/plans/detail?id={plan_id}`

页面区域：
1. 生产计划概要：`plan_no/company/sales_order/sales_order_item/item_code/bom_id/planned_qty/planned_start_date/status`。
2. 物料检查快照表：`material_item_code/uom/qty_per_piece/loss_rate/required_qty/warehouse/available_qty/shortage_qty/checked_at`。
3. Work Order 映射区：`work_order/erpnext_docstatus/erpnext_status/sync_status/last_synced_at`。
4. Job Card 映射表：`job_card/work_order/operation/operation_sequence/expected_qty/completed_qty/erpnext_status/synced_at`。
5. 物料检查操作卡。
6. 创建 Work Order 操作卡。
7. 同步 Job Card 操作卡。

物料检查操作卡字段：
- `warehouse`

创建 Work Order 操作卡字段：
- `fg_warehouse`
- `wip_warehouse`
- `start_date`
- `idempotency_key`

同步 Job Card 操作卡字段：
- 读取当前详情中的 `work_order`，不得手工输入任意 Work Order。

详情页规则：
1. 如果没有 `read` 权限，不加载详情，显示无权限空状态。
2. `material-check` 成功后刷新详情。
3. `create-work-order` 成功后刷新详情；如果返回 pending/processing，提示“Work Order 已进入同步队列”。
4. `sync-job-cards` 只有存在 `work_order` 时可点击。
5. `available_qty` 当前可能为后端占位 0，页面必须显示说明：`可用库存为后端快照；未接 ERPNext 库存快照前仅作参考`。
6. 不展示内部 worker run-once 入口。
7. 不展示 TASK-005/TASK-006 入口。

【路由】

修改 `src/router/index.ts`，新增：

| 路径 | name | component | meta |
| --- | --- | --- | --- |
| `/production/plans` | `ProductionPlanList` | `@/views/production/ProductionPlanList.vue` | `{ module: 'production' }` |
| `/production/plans/detail` | `ProductionPlanDetail` | `@/views/production/ProductionPlanDetail.vue` | `{ module: 'production' }` |

不得修改现有 BOM、外发、工票路由语义。

【状态标签】

至少覆盖：
- `draft`：草稿
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

未知状态原样展示，不得报错。

【幂等键规则】

1. 新建计划和创建 Work Order 必须自动生成幂等键。
2. 优先使用 `crypto.randomUUID()`。
3. 浏览器不支持时，降级为 `prefix + timestamp + random`。
4. 幂等键不得包含 token、用户名、Cookie、Authorization、密码、Secret。
5. 创建成功后必须刷新对应幂等键，避免用户误重复提交不同 payload。

【错误处理】

1. 必须使用 `src/api/request.ts` 的统一错误处理。
2. 401 显示登录失效提示。
3. 403 显示无权执行该操作。
4. 503 / `PERMISSION_SOURCE_UNAVAILABLE` / `ERPNEXT_SERVICE_UNAVAILABLE` 显示服务暂不可用。
5. 业务错误显示后端 `message`。
6. 页面不得展示完整 request header、Authorization、Cookie、Token、Secret、完整 DSN 或堆栈。

【测试与自检要求】

必须新增或补齐以下检查：
1. `src/api/production.ts` 使用 `request()`，没有裸 `fetch()`。
2. production 视图中没有裸 `fetch()`。
3. production 视图中没有 `/api/production/internal/work-order-sync/run-once`。
4. production 视图中没有直接访问 ERPNext API。
5. 列表页无 `read` 权限时不调用 `fetchProductionPlans`。
6. 详情页无 `read` 权限时不调用 `fetchProductionPlanDetail`。
7. 没有 `plan_create` 时不显示新建按钮。
8. 没有 `material_check` 时不显示物料检查按钮。
9. 没有 `work_order_create` 时不显示创建 Work Order 按钮。
10. 没有 `job_card_sync` 时不显示同步 Job Card 按钮。
11. create-work-order payload 包含 `fg_warehouse/wip_warehouse/start_date/idempotency_key`。
12. material-check payload 包含 `warehouse`。
13. 创建计划 payload 不包含 `company`。
14. 状态标签未知值原样展示。
15. 如项目已有前端测试框架，必须新增 production API 和页面权限测试；如没有测试框架，至少提交上述静态扫描命令与结果。

建议静态扫描命令：

```bash
cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc
rg "fetch\\(" src/api/production.ts src/views/production
rg "/api/production/internal" src/api/production.ts src/views/production src/router src/stores
rg "ERPNext|/api/resource|Authorization|Cookie|token|secret|password" src/views/production src/api/production.ts
```

如项目存在 package.json，必须运行：

```bash
npm run typecheck
npm run build
```

如当前前端目录没有 package.json，交付回报必须明确说明“当前前端目录无 package.json，无法执行 npm typecheck/build”，并提交静态扫描结果。

【验收标准】

□ 新增 `src/api/production.ts`，且全部请求复用 `src/api/request.ts`。  
□ 新增 `ProductionPlanList.vue`。  
□ 新增 `ProductionPlanDetail.vue`。  
□ 新增 `/production/plans` 路由。  
□ 新增 `/production/plans/detail` 路由。  
□ permission store 支持 production 按钮权限。  
□ `production:work_order_worker` 不会进入前端按钮权限。  
□ 列表页可查询、分页、创建生产计划。  
□ 详情页可查看计划、物料快照、Work Order 映射、Job Card 映射。  
□ 详情页可触发物料检查并传 `warehouse`。  
□ 详情页可触发创建 Work Order outbox 并传 `fg_warehouse/wip_warehouse/start_date/idempotency_key`。  
□ 详情页可触发同步 Job Card。  
□ 无权限时不请求对应业务数据，不展示对应按钮。  
□ 前端不调用内部 worker 接口。  
□ 前端不直接调用 ERPNext。  
□ 前端不传 company 创建生产计划。  
□ 401/403/503 和业务错误均有用户可读提示。  
□ 静态扫描未发现裸 fetch、内部 worker 调用、ERPNext 直连、敏感字段泄露。  
□ 如 package.json 存在，typecheck/build 通过；如不存在，交付回报说明无法执行。  
□ 未修改 production 后端业务逻辑。  
□ 未进入 TASK-005/TASK-006。  

【禁止事项】

- 禁止前端直接调用 ERPNext。
- 禁止前端调用 `/api/production/internal/work-order-sync/run-once`。
- 禁止新增 worker 运维页面。
- 禁止在生产计划创建表单中让用户输入 company。
- 禁止用前端权限隐藏替代后端鉴权。
- 禁止裸 `fetch()`。
- 禁止在页面、日志、提示中展示 Authorization/Cookie/Token/Secret/完整 DSN。
- 禁止修改 production 后端业务逻辑。
- 禁止修改外发结算、工票计薪、BOM 主业务逻辑。
- 禁止进入 TASK-005/TASK-006。

【交付回报格式】

工程师完成后按以下格式回复：

```text
TASK-004B 已完成。

实现内容：
1. production API：...
2. 列表页：...
3. 详情页：...
4. 权限按钮：...
5. 路由：...

涉及文件：
- ...

验证结果：
- rg "fetch\\(" src/api/production.ts src/views/production：...
- rg "/api/production/internal" src/api/production.ts src/views/production src/router src/stores：...
- rg "ERPNext|/api/resource|Authorization|Cookie|token|secret|password" src/views/production src/api/production.ts：...
- npm run typecheck：...
- npm run build：...

未进入范围：
- 未修改 production 后端业务逻辑
- 未调用内部 worker
- 未直接调用 ERPNext
- 未进入 TASK-005/TASK-006
```

【前置依赖】
TASK-004A1 通过。

【预计工时】
1-2 天

════════════════════════════════════════════════════════════════════════════
