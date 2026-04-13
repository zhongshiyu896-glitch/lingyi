# TASK-002G 前端状态与权限联动工程任务单

- 任务编号：TASK-002G
- 模块：外发加工管理
- 优先级：P1
- 版本：V1.0
- 更新时间：2026-04-13 13:58 CST
- 作者：技术架构师
- 审计来源：TASK-002F3 审计意见书第 46 份通过，允许进入 TASK-002G
- 前置依赖：TASK-002A/B1/C1/D1/E1/F3 已通过；继续遵守外发模块 V1.14 与 ADR-030~ADR-042
- 任务边界：只做外发前端列表/详情的真实数据、状态显示、按钮权限联动和 API 类型契约修正；不得实现加工厂对账单、结算、应付、付款、ERPNext GL/AP；不得调用内部 worker run-once API

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-002G
模块：前端状态与权限联动
优先级：P1（第一阶段闭环）
════════════════════════════════════════════════════════════════════════════

【任务目标】
把外发列表和详情页从演示表单升级为基于真实 `/api/subcontract/` 数据、状态机和 `/api/auth/actions` 权限动作的可操作页面，确保按钮显示、禁用原因、接口入参与后端契约一致。

【模块概述】
外发加工后端已经完成创建、发料 outbox、回料 outbox、验货扣款金额和库存同步重试。前端当前仍存在旧契约残留，例如回料表单带验货字段、retry 不传 `outbox_id/stock_action/idempotency_key`、验货字段使用 `deduction_rate`。本任务负责把 Vue3 页面接到真实后端契约，并用后端权限动作 + 单据状态共同控制按钮，避免前端展示可点击但后端必然拒绝的操作。

【涉及文件】
新建或修改：
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/subcontract.ts
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/auth.ts
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/stores/permission.ts
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/subcontract/SubcontractOrderList.vue
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/subcontract/SubcontractOrderDetail.vue
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/router/index.ts
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/subcontract.py（仅允许补详情只读字段）
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/subcontract.py（仅允许补详情只读字段）
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/subcontract_service.py（仅允许补详情只读查询）
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_detail.py（仅允许补详情字段测试）

【接口契约修正】
必须把前端 API 类型修正为后端现行契约：

1. 新增 `fetchSubcontractOrderDetail(orderId)`：
   - 方法：`GET /api/subcontract/{id}`
   - 出参：`SubcontractOrderDetailData`

2. 修正 `receiveSubcontract(orderId, payload)`：
   - 入参：`receipt_warehouse, received_qty, idempotency_key, color?, size?, batch_no?, uom?`
   - 禁止继续传 `inspected_qty/rejected_qty`
   - 出参：`receipt_batch_no, outbox_id, sync_status, stock_entry_name`

3. 修正 `inspectSubcontract(orderId, payload)`：
   - 入参：`receipt_batch_no, inspected_qty, rejected_qty, deduction_amount_per_piece, idempotency_key, remark?`
   - 禁止使用旧字段 `deduction_rate`
   - 出参：`inspection_no, receipt_batch_no, inspected_qty, accepted_qty, rejected_qty, rejected_rate, gross_amount, deduction_amount, net_amount, status`

4. 修正 `retrySubcontractStockSync(orderId, payload)`：
   - 入参：`outbox_id, stock_action, idempotency_key, reason?`
   - 禁止无请求体调用 retry
   - 出参：`outbox_id, stock_action, status, next_retry_at?`

5. 所有请求必须沿用统一错误处理：
   - 401 跳登录
   - 403 显示无权限
   - 503 显示权限源/服务不可用
   - 业务错误显示后端 `message`，必要时展示 `code`

【权限接口要求】
1. `src/api/auth.ts` 的 `button_permissions` 类型必须补齐 subcontract keys：`issue_material, receive, inspect, cancel, stock_sync_retry, stock_sync_worker`。
2. `src/stores/permission.ts` 必须过滤内部非 UI 动作：`subcontract:stock_sync_worker` 不得作为普通按钮展示。
3. 列表页加载：`loadCurrentUser()` + `loadModuleActions('subcontract')`。
4. 详情页加载：先获取详情，再调用 `loadModuleActions('subcontract')` 或 `fetchModuleActions({module:'subcontract', resource_type:'subcontract_order', resource_id: orderId})`。
5. 前端按钮显示必须同时满足：后端 `button_permissions` 为 true + 当前单据状态允许 + 单据未 `blocked_scope/settled/cancelled/completed`。
6. 前端按钮隐藏不能替代后端鉴权；后端 403 必须正常提示。

【列表页要求】
`SubcontractOrderList.vue` 必须实现：
1. 无 `read` 权限时显示无权限空状态，不请求或不展示业务列表。
2. `create` 权限为 false 时隐藏或禁用“新建外发单”。
3. 列表显示：外发单号、公司、加工厂、款式、工序、计划数量、已发料、已回料、已验货、净应付金额、状态、库存同步状态。
4. 状态使用中文标签：草稿、已发料、加工中、待回料、待验货、已完成、已取消。
5. `resource_scope_status='blocked_scope'` 时显示“权限范围异常/资源不可用”标记。
6. 点击详情使用 router 跳转，不使用 `window.location.href`。
7. 查询条件保留分页、加工厂、状态，并支持 item_code/process_name 可选筛选。
8. API 错误不显示原始 JSON 堆栈或 token。

【详情页要求】
`SubcontractOrderDetail.vue` 必须实现：
1. 页面加载真实 `GET /api/subcontract/{id}` 数据，不再只显示 `orderId/currentStatus`。
2. 展示主单：外发单号、公司、加工厂、款式、BOM、工序、计划数量、状态、结算状态、资源范围状态。
3. 展示数量汇总：计划、已发料、已回料、已验货、合格、不合格。
4. 展示金额汇总：加工费总额、扣款金额、净应付金额。
5. 展示库存同步卡片：latest issue outbox、latest receipt outbox、真实 `stock_entry_name`、sync status、错误码。
6. 展示回料批次列表 `receipts[]`；若后端当前未返回，必须补只读详情字段。
7. 展示验货明细 `inspections[]`，字段包含批次、验货数量、合格数量、不合格数量、不合格率、扣款、净额、验货人、验货时间。
8. 发料表单只提交发料字段，成功后 reload detail。
9. 回料表单只提交回料字段，成功后 reload detail。
10. 验货表单必须选择已同步成功且仍有可验数量的 `receipt_batch_no`。
11. 验货成功后 reload detail。
12. 所有写操作生成前端 `idempotency_key`，建议格式：`subcontract:{action}:{orderId}:{timestamp}:{random}`。
13. 写操作成功提示必须显示业务结果和同步状态，不得显示伪 Stock Entry。
14. `retry` 按钮只对 latest issue/receipt 中 `failed/dead` 的 outbox 展示。
15. `retry` 必须传 `outbox_id + stock_action + idempotency_key`；如果详情没有 outbox id 或 idempotency_key，不展示 retry 按钮。
16. 禁止调用 `/api/subcontract/internal/stock-sync/run-once`。

【按钮状态规则】
按钮显示/启用必须按以下规则：

| 按钮 | 权限动作 | 状态条件 | 其他条件 |
| --- | --- | --- | --- |
| 新建外发单 | `subcontract:create` | 无 | 资源权限由后端最终校验 |
| 发料 | `subcontract:issue_material` | `draft/issued/processing/waiting_receive` | 非 `blocked_scope`、非 `settled`、非 `completed/cancelled` |
| 回料 | `subcontract:receive` | `issued/processing/waiting_receive/waiting_inspection` | 非 `blocked_scope`、非 `settled`、有回料仓 |
| 验货 | `subcontract:inspect` | `waiting_inspection/waiting_receive` | 存在已同步成功且剩余可验的 receipt batch |
| 重试库存同步 | `subcontract:stock_sync_retry` | 不依赖主单状态 | 目标 outbox status 为 `failed/dead`，且有 `outbox_id/idempotency_key/stock_action` |
| 取消 | `subcontract:cancel` | `draft/issued` | 非 `settled` |

【后端只读补齐规则】
如当前详情接口缺前端必要只读字段，允许在本任务补齐：
1. `receipts[]`：`receipt_batch_no, receipt_warehouse, received_qty, sync_status, stock_entry_name, received_at, remaining_inspect_qty`。
2. `inspections[]`：TASK-002F1 已要求字段。
3. `materials[]`：`issue_batch_no, warehouse, material_item_code, required_qty, issued_qty, sync_status, stock_entry_name`。
4. `status_logs[]`：`from_status, to_status, action, operator, created_at`。
5. 子表明细必须在资源鉴权通过后读取。
6. 不允许新增写业务逻辑。

【验收标准】
□ `src/api/subcontract.ts` 的 receive/retry/inspect 类型与后端契约一致。  
□ 前端不再向 receive 传 `inspected_qty/rejected_qty`。  
□ 前端不再向 inspect 传 `deduction_rate`。  
□ retry 必须传 `outbox_id + stock_action + idempotency_key`。  
□ 前端不调用 `/api/subcontract/internal/stock-sync/run-once`。  
□ 权限 store 支持 subcontract button permissions。  
□ `subcontract:stock_sync_worker` 不显示为普通 UI 按钮。  
□ 列表页无 read 权限时显示无权限空状态。  
□ 列表页无 create 权限时不显示或禁用新建按钮。  
□ 详情页加载真实后端详情数据。  
□ 详情页展示主单、数量汇总、金额汇总、库存同步状态、回料批次、验货明细。  
□ 发料按钮按权限和状态显示。  
□ 回料按钮按权限和状态显示。  
□ 验货按钮只在有可验已同步回料批次时显示。  
□ retry 按钮只对 failed/dead outbox 显示。  
□ 写操作成功后 reload detail。  
□ 401/403/503 和业务错误提示友好，不泄露 token/SQL/堆栈。  
□ 使用 Vue Router 跳转，不使用 `window.location.href`。  
□ 如补后端详情字段，后端 pytest/unittest/py_compile 通过。  
□ 前端 TypeScript 静态检查通过；若当前前端目录缺 package.json，工程师必须至少提供 `vue-tsc` 或等价类型检查方式说明。  
□ 业务代码扫描不出现内部 worker run-once 前端调用。  
□ 业务代码扫描不出现旧 receive 验货字段和旧 retry 无 body 调用。

【测试要求】
必须新增或补齐以下测试；若当前前端没有测试框架，可先以类型检查 + 组件静态断言脚本替代，并在交付说明中写清：
1. `subcontract api receive payload does not include inspected_qty/rejected_qty`
2. `subcontract api retry requires outbox_id stock_action idempotency_key`
3. `subcontract api inspect uses deduction_amount_per_piece`
4. `permission store maps subcontract button permissions`
5. `permission store filters subcontract:stock_sync_worker from UI actions`
6. `list page hides create button without create permission`
7. `detail page hides issue button without issue_material permission`
8. `detail page hides receive button when status is draft/completed/cancelled`
9. `detail page hides inspect button when no synced receivable batch exists`
10. `detail page shows retry only for failed/dead outbox`
11. `detail page never calls internal stock sync run-once API`
12. `detail page reloads after issue/receive/inspect/retry success`
13. `detail page displays inspections[] amount snapshot`
14. `detail page displays backend error message without raw stack/token`

【禁止事项】
- 禁止调用 `/api/subcontract/internal/stock-sync/run-once`。
- 禁止前端伪造或展示 `STE-ISS-* / STE-REC-*`。
- 禁止继续使用旧 retry 无 body 调用。
- 禁止回料表单提交验货字段。
- 禁止验货表单使用 `deduction_rate` 作为后端字段。
- 禁止前端用按钮隐藏替代后端鉴权。
- 禁止实现加工厂对账单、结算、应付、付款、GL。
- 禁止在本任务新增新的外发业务写接口。
- 禁止在错误提示中展示 Authorization、Cookie、token、password、secret、SQL 原文或堆栈。

【前置依赖】
TASK-002F3 已通过审计意见书第 46 份；必须先完成本任务并通过审计，才允许进入 TASK-002H。

【预计工时】
2-3 天

════════════════════════════════════════════════════════════════════════════
