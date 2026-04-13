# TASK-002G2 外发列表同步摘要字段封版整改工程任务单

- 任务编号：TASK-002G2
- 模块：外发加工管理
- 优先级：P2
- 版本：V1.0
- 更新时间：2026-04-13 14:31 CST
- 作者：技术架构师
- 审计来源：TASK-002G1 审计意见书第 48 份，N+1 和鉴权高危已修复，剩余低危为前端列表读取 `latest_issue_sync_status/latest_receipt_sync_status`，但后端列表接口尚未返回对应字段
- 架构裁决：不移除库存同步状态列；后端补齐 `GET /api/subcontract/` list item 轻量同步摘要字段，前端读取真实字段展示
- 前置依赖：TASK-002G1 高危阻断已关闭；继续遵守外发模块 V1.16 与 ADR-044
- 任务边界：只补外发列表只读同步摘要字段、前端类型和列表展示；不得新增或修改外发业务写逻辑

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-002G2
模块：外发列表同步摘要字段封版整改
优先级：P2（封版前低危整改）
════════════════════════════════════════════════════════════════════════════

【任务目标】
补齐外发列表接口的 latest issue/receipt 同步摘要字段，让列表“库存同步状态”列读取真实后端数据，避免长期显示“进入详情查看”。

【模块概述】
TASK-002G1 已修复外发前端 API 裸 `fetch()` 和列表 N+1 详情请求问题。当前剩余低危问题是前端列表已读取 `latest_issue_sync_status/latest_receipt_sync_status`，但后端 `GET /api/subcontract/` list item 还没有返回这些字段。为保持产品体验和 ADR-043 的列表摘要契约，本任务选择后端补齐轻量只读摘要，而不是删除前端库存同步状态列。

【涉及文件】
必须修改：
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/subcontract.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/subcontract.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/subcontract_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_list_summary.py
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/subcontract.ts
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/subcontract/SubcontractOrderList.vue

允许新增：
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_list_summary.py（若不存在）
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/__tests__/subcontract-list-summary.spec.ts（如当前前端测试体系存在）

【后端字段契约】
`GET /api/subcontract/` 的每条 list item 必须返回以下字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `latest_issue_outbox_id` | number/null | 当前外发单最新发料 outbox ID |
| `latest_issue_sync_status` | string/null | 最新发料同步状态：pending/processing/succeeded/failed/dead |
| `latest_issue_stock_entry_name` | string/null | ERPNext 真实 Stock Entry name |
| `latest_issue_idempotency_key` | string/null | 最新发料幂等键，用于精确 retry |
| `latest_issue_error_code` | string/null | 最新发料错误码 |
| `latest_receipt_outbox_id` | number/null | 当前外发单最新回料 outbox ID |
| `latest_receipt_sync_status` | string/null | 最新回料同步状态：pending/processing/succeeded/failed/dead |
| `latest_receipt_stock_entry_name` | string/null | ERPNext 真实 Stock Entry name |
| `latest_receipt_idempotency_key` | string/null | 最新回料幂等键，用于精确 retry |
| `latest_receipt_error_code` | string/null | 最新回料错误码 |

【后端实现规则】
1. 摘要字段必须在外发订单资源权限过滤之后计算。
2. 摘要字段只读，不得触发 outbox 状态变化、retry、worker、ERPNext 调用或审计写操作。
3. 最新 outbox 定义：同一 `subcontract_id + stock_action` 下按 `created_at desc, id desc` 取 1 条。
4. 必须区分 `stock_action='issue'` 和 `stock_action='receipt'`，不得混用。
5. 必须使用批量查询、窗口函数或一次性子查询取当前页订单摘要，不得在订单循环中逐条查询详情。
6. 只允许返回状态展示所需字段，不得返回 `payload_json`、`last_error_message`、ERPNext 原始异常、Authorization、Cookie、token。
7. `last_error_code` 可以映射到 `latest_*_error_code`；错误消息不得进入 list item。
8. 没有对应 outbox 时，所有 latest 字段返回 `null`。
9. 权限源不可用时保持现有 fail closed 行为，不得为了摘要字段放开列表数据。
10. 数据库读取异常必须返回 `DATABASE_READ_FAILED` 或项目现有等价错误码，不得裸 500，不得 `detail=str(exc)`。

【前端实现规则】
1. `src/api/subcontract.ts` 的 `SubcontractOrderListItem` 类型必须补齐上述 10 个字段。
2. `SubcontractOrderList.vue` 的库存同步状态列必须读取 list item 的 latest 字段。
3. 不得恢复逐行 `fetchSubcontractOrderDetail(row.id)`。
4. 如果字段为 `null`，显示“暂无同步任务”或等价空状态。
5. 如果 issue/receipt 任一状态为 `failed/dead`，列表可以显示失败标签，但 retry 操作仍建议进入详情页执行。
6. 列表页不得展示 `latest_*_idempotency_key` 原文，除非用于内部按钮 payload，不得作为普通文本暴露。
7. 列表页不得展示后端原始错误消息。
8. 前端 API 继续使用 TASK-002G1 的统一 `request<T>()`，不得回退到裸 `fetch()`。

【验收标准】
□ `GET /api/subcontract/` 每条 list item 返回 `latest_issue_sync_status` 和 `latest_receipt_sync_status`。  
□ `GET /api/subcontract/` 每条 list item 返回 issue/receipt 的 outbox_id、stock_entry_name、idempotency_key、error_code 摘要字段。  
□ 没有 outbox 的外发单，latest 字段全部为 `null`，接口仍正常返回。  
□ 同一订单同时有 issue 和 receipt outbox 时，两个 action 的摘要互不串扰。  
□ 多条 outbox 时，按 `created_at desc, id desc` 返回最新一条。  
□ list 摘要在资源权限过滤之后计算，无权限订单不会泄露摘要。  
□ 后端没有按订单循环查详情或逐条调用详情 service。  
□ list item 不返回 `payload_json`、`last_error_message`、ERPNext 原始异常或敏感凭证。  
□ `SubcontractOrderList.vue` 不再显示长期“进入详情查看”作为库存同步状态默认值。  
□ `SubcontractOrderList.vue` 不存在逐行详情请求。  
□ `src/api/subcontract.ts` 不存在直接 `fetch(`。  
□ retry 仍只在详情页或具备精确字段时按 `outbox_id + stock_action + idempotency_key` 提交。  
□ 不调用 `/api/subcontract/internal/stock-sync/run-once`。  
□ 后端 `.venv/bin/python -m pytest -q` 通过。  
□ 后端 `.venv/bin/python -m unittest discover` 通过。  
□ 后端 `.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)` 通过。  
□ 前端如可执行类型检查，必须通过；如当前前端目录仍缺构建配置，交付说明必须写明不可执行原因并附静态扫描结果。  

【测试要求】
必须新增或补齐以下测试：
1. `list endpoint returns latest issue and receipt summary fields`
2. `list endpoint returns null summary fields when order has no outbox`
3. `list endpoint keeps issue and receipt summaries separated`
4. `list endpoint picks newest outbox by created_at desc id desc`
5. `list endpoint does not expose payload_json or raw error message`
6. `list endpoint applies resource filtering before summary exposure`
7. `list endpoint avoids per-order detail lookup`
8. `frontend list item type includes latest issue and receipt summary fields`
9. `frontend list renders sync status from list item fields`
10. `frontend scan confirms no row detail fetch for sync status`

【禁止事项】
- 禁止恢复 `fetchSubcontractOrderDetail(row.id)` 逐行查询。
- 禁止在列表接口返回 `payload_json` 或原始异常消息。
- 禁止列表接口触发 retry、worker 或 ERPNext 调用。
- 禁止修改发料、回料、验货、retry 写接口业务逻辑。
- 禁止调用 `/api/subcontract/internal/stock-sync/run-once`。
- 禁止实现对账、结算、应付、付款、GL。
- 禁止 `src/api/subcontract.ts` 回退到裸 `fetch()`。

【前置依赖】
TASK-002G1 审计高危已关闭；必须完成本任务并通过审计后，才允许进入 TASK-002H。

【预计工时】
0.5-1 天

════════════════════════════════════════════════════════════════════════════
