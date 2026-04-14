# TASK-005D2 利润实际成本归属与事务兜底整改工程任务单

- 任务编号：TASK-005D2
- 模块：款式利润报表 / 利润快照计算服务审计整改
- 优先级：P0
- 版本：V1.0
- 更新时间：2026-04-14 10:36 CST
- 作者：技术架构师
- 审计来源：审计意见书第 93 份，TASK-005D1 有条件通过但仍有 2 个 P1、1 个 P2 必改项
- 前置依赖：TASK-005D1 已交付并完成第 93 份审计；TASK-005E/API 层未放行；TASK-006 继续阻塞
- 架构依据：`/03_需求与设计/01_架构设计/06_模块设计_款式利润报表.md` V1.1；`ADR-087`
- 任务边界：只修复实际成本归属校验、服务事务兜底、sales_order 强制非空和相关测试；不注册 API；不改前端；不新增迁移；不进入 TASK-005E/TASK-006

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-005D2
模块：利润实际成本归属与事务兜底整改
优先级：P0（阻断整改）
════════════════════════════════════════════════════════════════════════════

【任务目标】
修复第 93 份审计指出的 3 个阻断项：workshop/subcontract 实际成本跨范围污染、计算异常后半快照可提交、空 sales_order 仍可生成 complete 快照。

【架构决策】
TASK-005D V1 中 `sales_order` 强制非空。理由：利润快照 V1 的资源权限、收入归属、工票归属、外发归属都依赖 `company + item_code + sales_order`，允许空订单会导致无归属收入或成本进入 complete 快照。空 `sales_order` 必须在 DTO 或服务校验阶段直接拒绝，不得生成 snapshot/detail/source_map。

【允许修改】
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/style_profit_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/style_profit_source_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/style_profit.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_snapshot_calculation.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_snapshot_idempotency.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_source_mapping.py
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md

【禁止修改】
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/main.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/**
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/**
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/**
- /Users/hh/Desktop/领意服装管理系统/.github/**
- /Users/hh/Desktop/领意服装管理系统/02_源码/**
- 任意 TASK-005E 文件
- 任意 TASK-006 文件

【必须修复】

## 1. P1：workshop/subcontract 实际成本必须做资源归属校验

当前问题：`_persist_workshop_details()` 和 `_persist_subcontract_details()` 直接遍历 payload 行，未校验来源是否属于当前快照；错公司、错订单、错款式的工票和外发成本会被计入当前利润。

整改要求：
1. 增加统一 scope 校验 helper，例如 `_match_profit_scope(row, snapshot_scope, source_type)`。
2. `company` 必须匹配当前快照 company。
3. `item_code/style_item_code` 必须匹配当前快照 item_code。
4. `sales_order` 必须匹配当前快照 sales_order。
5. `work_order/job_card` 可作为辅助归属桥，但不能替代明确冲突的 `company/item_code/sales_order`。
6. 如果来源行存在 `company` 且不匹配，必须排除，不得纳入成本。
7. 如果来源行存在 `item_code/style_item_code` 且不匹配，必须排除，不得纳入成本。
8. 如果来源行存在 `sales_order` 且不匹配，必须排除，不得纳入成本。
9. 如果来源行缺少 `sales_order`，必须至少通过 `work_order/job_card` 已知桥接匹配；没有桥接时必须 unresolved，不得纳入成本。
10. 外发行必须校验 `company + item_code + sales_order`；若只有 `subcontract_order`，必须已有可验证归属字段，否则 unresolved。
11. 错范围来源可以写 excluded source_map；无法确认归属但可能相关的来源写 unresolved source_map。
12. 错范围或 unresolved 来源不得影响 `actual_workshop_cost`、`actual_subcontract_cost`、`actual_total_cost`。
13. 错范围 excluded 不强制使 snapshot incomplete；无法确认归属的 unresolved 必须使 snapshot incomplete。

## 2. P1：create_snapshot 必须有保存点或异常回滚兜底

当前问题：`create_snapshot()` 先 flush snapshot/detail/source_map，后续计算异常被包装为业务异常，但已 flush 的半快照仍可能被调用方误 commit。

整改要求：
1. `create_snapshot()` 首次写入路径必须使用 `session.begin_nested()` 保存点，或等价显式保存点机制。
2. replay 路径不得开启不必要写事务，不得新增行。
3. 幂等冲突路径不得新增行。
4. 首次写入过程中，任意 `BusinessException`、`SQLAlchemyError`、`Exception` 都必须回滚本次保存点。
5. 保存点回滚后，调用方即使执行 `session.commit()`，也不得留下本次 snapshot/detail/source_map。
6. 数据库写入失败仍必须归类为 `DATABASE_WRITE_FAILED` 或等价数据库写异常。
7. 未知异常仍可归类为 `STYLE_PROFIT_INTERNAL_ERROR`，但不得留下半快照。
8. 不得在服务内调用外层 `session.commit()`。

## 3. P2：sales_order 在 V1 强制非空

当前问题：空 `sales_order` 可生成 complete 快照，收入来源行缺 sales_order 时仍可被计入。

整改要求：
1. `sales_order` 在 TASK-005D V1 强制非空。
2. DTO 层或 `_validate_payload()` 必须拒绝 `None`、空字符串、空白字符串。
3. 错误码建议为 `STYLE_PROFIT_SALES_ORDER_REQUIRED`。
4. 空 `sales_order` 必须在任何 snapshot/detail/source_map 写入前失败。
5. 空 `sales_order` 不得生成 unresolved 快照；V1 直接拒绝请求。
6. `StyleProfitSourceService.resolve_revenue_sources()` 不得在 expected_order 为空时把无 sales_order 来源行当作有效收入。
7. 测试必须断言空 `sales_order` 不落库。

【防回潮要求】
1. 不得回退 TASK-005D1 已修复内容：request_hash 来源输入、收入 unresolved、异常 SLE unresolved、缺工价 unresolved、真实 source_status、idempotency_key 长度校验。
2. 不得降低 TASK-005C1/C2 的状态 fail closed 和 `include_in_profit=false` 默认规则。
3. 不得恢复 Purchase Receipt 直接计入 actual_material_cost。
4. 不得注册 `/api/reports/style-profit/`。
5. 不得进入 TASK-005E/API 层。
6. 不得进入 TASK-006。

【必须新增或补齐测试】
1. 工票错 company 不计入 `actual_workshop_cost`。
2. 工票错 item_code/style_item_code 不计入 `actual_workshop_cost`。
3. 工票错 sales_order 不计入 `actual_workshop_cost`。
4. 工票缺 sales_order 且无 work_order/job_card 桥接时 unresolved，snapshot incomplete。
5. 工票 company/item/sales_order 全匹配时可计入成本。
6. 外发错 company 不计入 `actual_subcontract_cost`。
7. 外发错 item_code/style_item_code 不计入 `actual_subcontract_cost`。
8. 外发错 sales_order 不计入 `actual_subcontract_cost`。
9. 外发缺 sales_order 且无法通过来源归属字段验证时 unresolved，snapshot incomplete。
10. 外发 company/item/sales_order 全匹配且已结算时可计入成本。
11. 同一快照中混入错范围工票和外发行时，`actual_total_cost` 不包含错范围金额。
12. 计算中途抛非 SQLAlchemy 异常后，调用方误 `commit()` 也不会留下 snapshot/detail/source_map。
13. 计算中途抛 `SQLAlchemyError` 后，调用方误 `commit()` 也不会留下半快照。
14. 幂等 replay 不新增行，且不受保存点改造影响。
15. 幂等冲突不新增行，且不受保存点改造影响。
16. `sales_order=None` 返回 `STYLE_PROFIT_SALES_ORDER_REQUIRED` 或等价业务异常，不落库。
17. `sales_order=''` 返回 `STYLE_PROFIT_SALES_ORDER_REQUIRED` 或等价业务异常，不落库。
18. `sales_order='   '` 返回 `STYLE_PROFIT_SALES_ORDER_REQUIRED` 或等价业务异常，不落库。
19. 禁改扫描确认未注册 API、未改前端、未新增迁移、未进入 TASK-005E/TASK-006。

【验证命令】

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest -q tests/test_style_profit_models.py tests/test_style_profit_source_mapping.py tests/test_style_profit_service.py tests/test_style_profit_snapshot_calculation.py tests/test_style_profit_snapshot_idempotency.py
.venv/bin/python -m pytest -q
.venv/bin/python -m unittest discover
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
```

【禁改扫描】

```bash
cd /Users/hh/Desktop/领意服装管理系统
git diff --name-only -- 06_前端 .github 02_源码
git diff --name-only -- 07_后端/lingyi_service/app/main.py 07_后端/lingyi_service/app/routers 07_后端/lingyi_service/migrations
git diff --name-only -- '03_需求与设计/02_开发计划' | grep 'TASK-006' || true
git diff --name-only -- '03_需求与设计/02_开发计划' | grep 'TASK-005E' || true
```

要求：
1. 前两个禁改扫描必须无输出。
2. 第三个命令不得出现 TASK-006 文件。
3. 第四个命令不得出现 TASK-005E 文件。

【验收标准】
□ workshop/subcontract 来源按 company + item_code + sales_order 做资源归属校验。
□ 错公司、错订单、错款式的工票和外发成本不计入当前利润。
□ 缺归属桥的工票和外发来源 unresolved，并使 snapshot incomplete。
□ `create_snapshot()` 有保存点或等价回滚兜底，异常后误 commit 不会留下半快照。
□ `sales_order` 在 V1 强制非空，空值直接业务错误且不落库。
□ TASK-005D1 已修复项未回退。
□ 定向 pytest、全量 pytest、unittest、py_compile 全部通过。
□ 未注册 API，未修改前端，未新增迁移，未进入 TASK-005E/TASK-006。
□ 工程师会话日志已追加执行记录。

【预计工时】
0.5-1.5 天

════════════════════════════════════════════════════════════════════════════
