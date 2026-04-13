# TASK-002G3 外发列表摘要自动化测试补齐工程任务单

- 任务编号：TASK-002G3
- 模块：外发加工管理
- 优先级：P2
- 版本：V1.0
- 更新时间：2026-04-13 14:41 CST
- 作者：技术架构师
- 审计来源：TASK-002G2 审计意见书第 49 份，功能修复已通过，剩余低危为列表同步摘要字段和 latest outbox 选择规则缺少自动化测试覆盖
- 架构裁决：补齐后端自动化测试后再允许外发前端封版；本任务原则上只改测试，除非测试证明现有实现与 TASK-002G2 契约不一致
- 前置依赖：TASK-002G2 功能修复通过；继续遵守外发模块 V1.17 与 ADR-045
- 任务边界：只补外发列表摘要自动化测试和必要测试辅助数据；不得修改发料、回料、验货、retry、worker、ERPNext 调用等业务逻辑

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-002G3
模块：外发列表摘要自动化测试补齐
优先级：P2（封版前低危整改）
════════════════════════════════════════════════════════════════════════════

【任务目标】
补齐外发列表 latest issue/receipt 同步摘要字段的后端自动化测试，锁住摘要返回和 latest outbox 选择规则，避免后续回归。

【模块概述】
TASK-002G2 已让外发列表可以读取后端 `latest_issue_sync_status/latest_receipt_sync_status` 等摘要字段，N+1 和鉴权高危已经关闭。当前剩余问题是没有自动化测试保护该契约，未来工程师重构 list service 或 outbox 查询时，可能再次丢字段、串扰 issue/receipt，或错误选择旧 outbox。本任务只补测试，不扩大业务范围。

【涉及文件】
必须新增或修改：
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_list_summary.py

允许修改：
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/conftest.py（仅限复用测试 fixture）
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/factories.py（如已有，仅限补测试工厂）
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/subcontract_service.py（仅当新增测试证明实现与契约不一致时，才允许最小修复）
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/subcontract.py（仅当新增测试证明字段契约遗漏时，才允许最小修复）

【必须覆盖的测试】
1. `test_list_returns_latest_issue_and_receipt_summary_fields`
   - 创建一个有权限访问的外发单。
   - 创建一条 `stock_action='issue'` 的 outbox。
   - 创建一条 `stock_action='receipt'` 的 outbox。
   - 调用 `GET /api/subcontract/`。
   - 断言 list item 返回：
     - `latest_issue_outbox_id`
     - `latest_issue_sync_status`
     - `latest_issue_stock_entry_name`
     - `latest_issue_idempotency_key`
     - `latest_issue_error_code`
     - `latest_receipt_outbox_id`
     - `latest_receipt_sync_status`
     - `latest_receipt_stock_entry_name`
     - `latest_receipt_idempotency_key`
     - `latest_receipt_error_code`
   - 断言 issue 字段来自 issue outbox，receipt 字段来自 receipt outbox。

2. `test_list_summary_separates_actions_and_picks_newest_by_created_at_desc_id_desc`
   - 同一外发单下创建多条 issue outbox 和多条 receipt outbox。
   - issue 和 receipt 使用不同 status、stock_entry_name、idempotency_key、error_code。
   - 每个 action 至少包含一条旧 outbox 和一条新 outbox。
   - 调用 `GET /api/subcontract/`。
   - 断言 issue 摘要只取最新 issue outbox。
   - 断言 receipt 摘要只取最新 receipt outbox。
   - 断言 issue/receipt 互不串扰。
   - 断言排序规则为 `created_at desc, id desc`；当 `created_at` 相同时，取 `id` 更大的 outbox。

【建议补充测试】
如实现成本低，建议同时补：
1. `test_list_summary_returns_null_when_order_has_no_outbox`
2. `test_list_summary_does_not_expose_payload_json_or_raw_error_message`
3. `test_list_summary_applies_resource_filter_before_exposing_outbox_summary`

【测试数据要求】
1. 测试必须使用真实 ORM 模型或现有项目测试工厂创建 `ly_subcontract_order` 和 `ly_subcontract_stock_outbox`。
2. 测试必须通过当前用户权限或测试 fixture，让目标订单可被 list 接口返回。
3. 测试不得依赖执行顺序。
4. 测试不得依赖真实 ERPNext 服务。
5. 测试不得调用 worker。
6. 测试不得创建真实 Stock Entry。
7. 测试不得使用伪 `STE-ISS-* / STE-REC-*` 作为业务成功依据；如需 stock_entry_name，可使用测试常量并只断言透传。
8. 测试不得写入敏感 token、Authorization、Cookie。

【验收标准】
□ 已新增 `test_list_returns_latest_issue_and_receipt_summary_fields` 或等价测试。  
□ 已新增 `test_list_summary_separates_actions_and_picks_newest_by_created_at_desc_id_desc` 或等价测试。  
□ 测试断言 list item 包含 issue/receipt 全部摘要字段。  
□ 测试断言 issue 和 receipt 摘要互不串扰。  
□ 测试断言多条 outbox 时按 `created_at desc, id desc` 取最新。  
□ 测试不调用 ERPNext、worker、retry 或内部 run-once。  
□ 测试不修改发料、回料、验货、retry 写接口业务逻辑。  
□ `.venv/bin/python -m pytest -q tests/test_subcontract_list_summary.py` 通过。  
□ `.venv/bin/python -m pytest -q` 通过。  
□ `.venv/bin/python -m unittest discover` 通过。  
□ `.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)` 通过。  
□ 静态扫描确认前端未恢复 `fetchSubcontractOrderDetail(row.id)` 和裸 `fetch()`。  

【禁止事项】
- 禁止修改发料、回料、验货、retry 写接口业务逻辑。
- 禁止调用或测试 `/api/subcontract/internal/stock-sync/run-once`。
- 禁止通过真实 ERPNext 服务完成测试。
- 禁止为通过测试伪造生产逻辑。
- 禁止返回或断言 `payload_json`、`last_error_message`、ERPNext 原始异常、Authorization、Cookie、token。
- 禁止前端恢复 N+1 详情请求。
- 禁止 `src/api/subcontract.ts` 回退到裸 `fetch()`。

【前置依赖】
TASK-002G2 功能修复已通过；必须完成本任务并通过审计后，才允许进入 TASK-002H。

【预计工时】
0.5 天

════════════════════════════════════════════════════════════════════════════
