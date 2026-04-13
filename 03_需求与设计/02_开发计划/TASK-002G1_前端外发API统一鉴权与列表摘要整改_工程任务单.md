# TASK-002G1 前端外发 API 统一鉴权与列表摘要整改工程任务单

- 任务编号：TASK-002G1
- 模块：外发加工管理
- 优先级：P1
- 版本：V1.0
- 更新时间：2026-04-13 14:20 CST
- 作者：技术架构师
- 审计来源：TASK-002G 审计意见书第 47 份不通过，阻断项为外发前端 API 裸 `fetch()` 未接入统一鉴权、`credentials: include` 和统一错误信封；中危项为列表页逐行拉详情造成 N+1 请求与权限检查放大
- 前置依赖：TASK-002G 已交付但未通过审计；TASK-002A/B1/C1/D1/E1/F3 已通过；继续遵守外发模块 V1.15 与 ADR-030~ADR-043
- 任务边界：只修前端外发 API 鉴权封装、统一错误处理、列表同步摘要字段和列表 N+1；不得实现加工厂对账单、结算、应付、付款、ERPNext GL/AP；不得调用内部 worker run-once API

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-002G1
模块：前端外发 API 统一鉴权与列表摘要整改
优先级：P1（审计阻断整改）
════════════════════════════════════════════════════════════════════════════

【任务目标】
修复外发前端 API 仍使用裸 `fetch()` 导致生产登录态/Token 鉴权失效的问题，并取消列表页逐行拉详情的 N+1 同步状态查询。

【模块概述】
TASK-002G 已把外发详情、按钮权限和接口入参基本接到后端契约，但前端 API 层仍直接调用 `fetch()`。生产环境中，裸 `fetch()` 不带统一 Authorization 头、不带 `credentials: 'include'`、不处理 `{code,message,data}` 统一错误信封，会导致外发模块在真实登录态下直接 401/403。列表页为了展示库存同步状态逐行调用详情接口，也会放大权限校验、子表读取和 HTTP 请求数量。本任务只修这两个审计阻断点，不新增外发业务写逻辑。

【涉及文件】
必须修改：
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/subcontract.ts
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/auth.ts
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/subcontract/SubcontractOrderList.vue
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/subcontract/SubcontractOrderDetail.vue

允许新增或修改：
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/request.ts
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/stores/permission.ts
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/subcontract.py（仅允许补 list 只读摘要字段）
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/subcontract.py（仅允许补 list 只读摘要字段）
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/subcontract_service.py（仅允许补 list 批量摘要查询）
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_list_summary.py
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/__tests__/subcontract.spec.ts（如当前测试体系存在）

【整改范围】
1. `src/api/subcontract.ts` 禁止直接调用 `fetch()`。
2. 外发所有 API 必须走统一 `request<T>()` 或等价封装。
3. 统一请求封装必须带 `credentials: 'include'`。
4. 统一请求封装必须带登录 Token 的 `Authorization` 头；如 token 已含 `Bearer ` 前缀不得重复添加。
5. 统一请求封装必须解析后端 `{code,message,data}` 信封。
6. `code != 0` 或 HTTP 非 2xx 时必须抛出统一前端错误对象，保留 `code/message/status`，不得丢失后端业务错误码。
7. 401 必须走未登录处理，不得显示原始响应体或堆栈。
8. 403 必须显示无权限提示，不得静默失败。
9. 503、`PERMISSION_SOURCE_UNAVAILABLE`、`ERPNEXT_SERVICE_UNAVAILABLE` 必须显示服务暂不可用提示。
10. 错误提示和日志不得输出 Authorization、Cookie、token、password、secret、SQL 原文或堆栈。
11. `SubcontractOrderList.vue` 禁止通过逐行 `fetchSubcontractOrderDetail(row.id)` 获取同步状态。
12. 删除或废弃 `loadSyncStatusHints()` 一类 N+1 详情拉取逻辑。
13. 外发列表同步状态必须来自 list API 的轻量摘要字段；若后端暂不补 list 摘要，则列表页不得展示同步摘要，只能在详情页展示。
14. 架构裁决：本轮正式将 list 轻量同步摘要字段纳入 TASK-002G1 合同，优先补后端 list 摘要，禁止用前端 N+1 兜底。
15. `allowed_actions_for_current_order` 允许作为详情接口只读增强字段，但不是 TASK-002G1 必做项；前端按钮最终仍以后端写接口鉴权为准。

【统一请求封装要求】
实现方式二选一：
1. 推荐：新增 `src/api/request.ts`，导出 `request<T>()`、`buildAuthHeaders()`、`ApiError`。
2. 可接受：从 `src/api/auth.ts` 导出已有 `request<T>()` 和 `buildAuthHeaders()`，但不得在 `subcontract.ts` 复制一份独立实现。

统一封装必须满足：
1. `credentials: 'include'` 固定存在。
2. `Content-Type: application/json` 按需存在；GET 请求不得强制发送 body。
3. 从本地 token 存储读取登录 token，兼容现有项目约定键名。
4. 如果 token 非空且不以 `Bearer ` 开头，则请求头写 `Authorization: Bearer ${token}`。
5. 如果 token 已以 `Bearer ` 开头，则原样写入 `Authorization`。
6. 响应 JSON 为 `{code,message,data}` 时，`code === 0` 返回 `data`。
7. 响应 JSON 为 `{code,message,data}` 且 `code !== 0` 时抛出 `ApiError(code,message,status,data)`。
8. 非 JSON 响应或 5xx 响应必须转成安全错误，不得把 HTML、堆栈或 SQL 透给 UI。
9. 不得吞掉 `request_id`，但展示时只允许展示已脱敏/白名单后的 request id。
10. `auth.ts` 原有登录、登出、权限动作接口不得被破坏。

【外发 API 改造清单】
`src/api/subcontract.ts` 中以下函数必须全部走统一 `request<T>()`：

| 函数 | HTTP 方法 | 路径 | 要求 |
| --- | --- | --- | --- |
| `fetchSubcontractOrders` | GET | `/api/subcontract/` | 返回分页数据和 list 摘要字段 |
| `fetchSubcontractOrderDetail` | GET | `/api/subcontract/{id}` | 返回详情、receipts、inspections、latest outbox |
| `createSubcontractOrder` | POST | `/api/subcontract/` | 带鉴权、统一错误信封 |
| `issueSubcontractMaterial` | POST | `/api/subcontract/{id}/issue-material` | 带鉴权、统一错误信封 |
| `receiveSubcontract` | POST | `/api/subcontract/{id}/receive` | 带鉴权、统一错误信封 |
| `inspectSubcontract` | POST | `/api/subcontract/{id}/inspect` | 带鉴权、统一错误信封 |
| `retrySubcontractStockSync` | POST | `/api/subcontract/{id}/stock-sync/retry` | 必须传 `outbox_id + stock_action + idempotency_key` |
| `cancelSubcontractOrder` | POST | `/api/subcontract/{id}/cancel` | 如当前已实现，必须带鉴权、统一错误信封 |

【列表摘要字段契约】
后端 `GET /api/subcontract/` 的每条 list item 必须补齐或确认返回以下轻量字段，用于替代前端 N+1 详情请求：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `latest_issue_outbox_id` | number/null | 最新发料 outbox ID |
| `latest_issue_sync_status` | string/null | 最新发料同步状态：pending/processing/succeeded/failed/dead |
| `latest_issue_stock_entry_name` | string/null | ERPNext 真实 Stock Entry name |
| `latest_issue_idempotency_key` | string/null | 最新发料幂等键，用于精确 retry |
| `latest_issue_error_code` | string/null | 最新发料错误码 |
| `latest_receipt_outbox_id` | number/null | 最新回料 outbox ID |
| `latest_receipt_sync_status` | string/null | 最新回料同步状态：pending/processing/succeeded/failed/dead |
| `latest_receipt_stock_entry_name` | string/null | ERPNext 真实 Stock Entry name |
| `latest_receipt_idempotency_key` | string/null | 最新回料幂等键，用于精确 retry |
| `latest_receipt_error_code` | string/null | 最新回料错误码 |

后端查询要求：
1. list 摘要必须在订单列表资源权限过滤之后计算。
2. list 摘要必须用批量查询或窗口函数，不得后端对每个订单循环查详情子表。
3. list 摘要只允许返回当前用户有权限看到的订单对应数据。
4. list 摘要不得返回 payload_json、last_error_message 明文、ERPNext 原始异常、Authorization/Cookie/token。
5. list 摘要字段只读，不得触发任何 outbox 状态变更。

【列表页改造要求】
`SubcontractOrderList.vue` 必须满足：
1. 删除逐行详情请求同步状态逻辑。
2. 删除 `loadSyncStatusHints()` 或改为纯读取 list item 已有字段，不发额外详情 HTTP 请求。
3. 每次加载列表最多只调用一次 `GET /api/subcontract/` 和必要的权限动作接口。
4. 列表展示库存同步状态时，只使用 `latest_issue_*` 和 `latest_receipt_*` 字段。
5. 如果 list item 没有摘要字段，列表显示“进入详情查看”，不得发详情请求兜底。
6. 列表按钮不得调用内部 worker run-once API。
7. 列表页 401/403/503 展示友好提示，不展示原始 JSON/堆栈。

【详情页改造要求】
`SubcontractOrderDetail.vue` 必须满足：
1. 继续使用详情接口展示 receipts、inspections、latest issue/receipt outbox。
2. retry 按钮必须使用详情或 list 摘要中的 `outbox_id + stock_action + idempotency_key`。
3. 详情页不得调用内部 worker run-once API。
4. 详情页所有写操作错误必须使用统一 `ApiError` 展示。
5. 详情页按钮隐藏不能替代后端鉴权；后端 403 必须正常提示。

【验收标准】
□ `src/api/subcontract.ts` 不存在直接 `fetch(` 调用。  
□ `src/api/subcontract.ts` 中所有 `/api/subcontract` 请求都走统一 `request<T>()`。  
□ 统一请求封装固定包含 `credentials: 'include'`。  
□ 统一请求封装会写入标准 `Authorization: Bearer ...` 头。  
□ 统一请求封装能处理 `{code,message,data}` 成功信封并返回 `data`。  
□ 统一请求封装能处理 `{code,message,data}` 业务错误并抛出含 `code/message/status` 的安全错误。  
□ 401、403、503 在外发页面有友好提示。  
□ 外发前端错误提示不展示 Authorization/Cookie/token/password/secret/SQL/堆栈。  
□ `SubcontractOrderList.vue` 不存在 `fetchSubcontractOrderDetail(row.id)` 或等价逐行详情查询。  
□ `SubcontractOrderList.vue` 不存在会为每行发 HTTP 请求的 `loadSyncStatusHints()` 逻辑。  
□ `GET /api/subcontract/` list item 返回最新 issue/receipt 同步摘要字段，或列表明确不展示同步摘要并提示进入详情查看。  
□ 若补后端 list 摘要，后端以批量查询实现，不在循环里按订单查详情。  
□ retry 仍只按 `outbox_id + stock_action + idempotency_key` 精确提交。  
□ 前端不调用 `/api/subcontract/internal/stock-sync/run-once`。  
□ 业务代码扫描无伪 `STE-ISS-* / STE-REC-*`。  
□ 前端 TypeScript 类型检查通过；若当前前端目录仍缺 `package.json/tsconfig/vite`，工程师必须在交付说明中写明不可执行原因，并提供静态扫描结果。  
□ 如修改后端，必须通过 `.venv/bin/python -m pytest -q`。  
□ 如修改后端，必须通过 `.venv/bin/python -m unittest discover`。  
□ 如修改后端，必须通过 `.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)`。  

【测试要求】
必须新增或补齐以下测试/静态检查：
1. `subcontract api uses unified request for list/detail/create/issue/receive/inspect/retry/cancel`
2. `subcontract api has no bare fetch to /api/subcontract`
3. `request wrapper sends credentials include`
4. `request wrapper sends Authorization Bearer token`
5. `request wrapper handles code nonzero as ApiError`
6. `request wrapper handles 401/403/503 without leaking raw response`
7. `list page does not call detail API for sync status hints`
8. `list page renders latest_issue/latest_receipt summary from list item`
9. `retry payload still requires outbox_id stock_action idempotency_key`
10. `frontend scan finds no internal stock-sync run-once call`
11. 若补后端 list 摘要：`list endpoint returns latest issue/receipt summary after resource filtering`
12. 若补后端 list 摘要：`list endpoint does not expose payload_json or raw error message`

【禁止事项】
- 禁止 `src/api/subcontract.ts` 直接 `fetch()`。
- 禁止外发 API 绕过统一鉴权请求封装。
- 禁止列表页为每行调用详情接口获取同步状态。
- 禁止调用 `/api/subcontract/internal/stock-sync/run-once`。
- 禁止恢复旧 retry 无 body 调用。
- 禁止回料表单提交验货字段。
- 禁止验货表单使用 `deduction_rate` 作为后端字段。
- 禁止在错误提示中展示 Authorization、Cookie、token、password、secret、SQL 原文或堆栈。
- 禁止实现加工厂对账单、结算、应付、付款、GL。
- 禁止新增新的外发业务写接口。

【前置依赖】
TASK-002G 审计意见书第 47 份不通过；必须完成本任务并通过审计，才允许进入 TASK-002H。

【预计工时】
1-2 天

════════════════════════════════════════════════════════════════════════════
