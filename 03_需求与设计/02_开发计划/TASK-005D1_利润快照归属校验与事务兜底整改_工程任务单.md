# TASK-005D1 利润快照归属校验与事务兜底整改工程任务单

- 任务编号：TASK-005D1
- 模块：款式利润报表 / 利润快照计算服务整改
- 优先级：P0
- 版本：V1.0
- 更新时间：2026-04-14 10:10 CST
- 作者：技术架构师
- 审计来源：审计意见书第 91 份，TASK-005D 有条件通过/有问题，高危 3 / 中危 3
- 前置依赖：TASK-005D 已交付但未通过验收；ADR-079、ADR-085 生效
- 架构依据：`/03_需求与设计/01_架构设计/06_模块设计_款式利润报表.md` V1.0；`ADR-086`
- 任务边界：只修 TASK-005D 服务和测试；不注册 API；不改前端；不新增迁移；不进入 TASK-005E；不得进入 TASK-006

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-005D1
模块：利润快照归属校验与事务兜底整改
优先级：P0（阻断整改）
════════════════════════════════════════════════════════════════════════════

【任务目标】
关闭第 91 份审计提出的 6 个必修问题，确保利润快照不会跨订单/跨款式/跨公司计入成本，不会在异常后留下半快照，并补齐 V1 必填与工价缺失规则。

【允许修改】
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/style_profit_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/style_profit.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/style_profit_source_service.py（仅限补归属校验辅助函数，不得放宽 TASK-005C1/C2 规则）
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_snapshot_calculation.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_snapshot_idempotency.py
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

【架构决策】
1. V1 利润快照强制要求 `sales_order` 非空。
2. `sales_order` 为空、空字符串或全空白时，必须返回/抛出 `STYLE_PROFIT_SALES_ORDER_REQUIRED`，不得创建 snapshot/detail/source_map。
3. 计算服务内部必须使用数据库保存点或等价嵌套事务兜底；任何计算异常后，调用方即使误 `commit()` 也不得留下半快照、半明细、半 source_map。
4. 工票、外发、标准工序的价格字段必须区分“缺失/非法”和“明确 0”。缺失或非法必须 unresolved；明确 0 只有字段真实存在且可解析为 0 时才允许作为 0 计算。

【必须修复】

## 1. Workshop 实际工票成本归属校验

规则：
1. 每条工票来源必须先做 scope 校验，再计算金额。
2. `company` 必须等于快照 `company`；不等则 `excluded/company_mismatch`，不得纳入利润。
3. 工票款式字段 `item_code/style_item_code` 必须等于快照 `item_code`；不等则 `excluded/item_mismatch`，不得纳入利润。
4. 工票 `sales_order` 若存在，必须等于快照 `sales_order`；不等则 `excluded/sales_order_mismatch`。
5. 工票若无 `sales_order`，必须能通过 `work_order` 或 `job_card` 桥接到当前快照；不能桥接时写 `unresolved/unable_to_link_workshop_scope`。
6. 只有 scope 校验通过、状态已提交、净数量有效、工价有效时，才允许 `mapping_status=mapped` 且 `include_in_profit=true`。

必须补测试：
1. `SO-A/STYLE-A` 快照不得计入 `SO-B/STYLE-B` 工票。
2. 错公司工票不得计入。
3. 缺少 `sales_order/work_order/job_card` 归属桥的工票必须 unresolved。
4. 正确归属工票仍能计入 `actual_workshop_cost`。

## 2. Subcontract 实际外发成本归属校验

规则：
1. 每条外发来源必须校验 `company + item_code + sales_order`。
2. `company` 不匹配时写 `excluded/company_mismatch`。
3. `item_code/style_item_code` 不匹配时写 `excluded/item_mismatch`。
4. `sales_order` 不匹配时写 `excluded/sales_order_mismatch`。
5. 缺少 `sales_order` 且不能通过 `work_order/production_plan` 归属时写 `unresolved/unable_to_link_subcontract_scope`。
6. 已结算/锁定来源优先计入结算锁定净额。
7. 未结算验货只有 `include_provisional_subcontract=true` 时可 provisional 纳入。
8. `include_provisional_subcontract=false` 时，未结算验货不得纳入利润。

必须补测试：
1. `SO-A/STYLE-A` 快照不得计入 `SO-B/STYLE-B` 外发成本。
2. 错公司外发不得计入。
3. 缺少归属桥的外发必须 unresolved。
4. 正确归属且锁定的外发仍优先使用结算锁定净额。

## 3. 工票工价缺失不得按 0 mapped

规则：
1. 当 `net_ticket_qty != 0` 时，必须存在有效工价字段。
2. 工价字段候选：`wage_rate_snapshot / wage_rate / unit_rate`。
3. 字段缺失、空字符串、None、不可解析数字时，必须写 `unresolved/workshop_wage_rate_missing` 或 `unresolved/workshop_wage_rate_invalid`。
4. 工价缺失/非法时不得创建 mapped source_map，不得 `include_in_profit=true`，不得让 snapshot 为 complete。
5. 明确传入数值 0 可以作为 0 工价，但必须有字段存在且可解析为 0。

必须补测试：
1. 净数量大于 0 且工价缺失时，`actual_workshop_cost` 不增加。
2. 工价缺失时 snapshot 为 `incomplete`。
3. 工价缺失时 `unresolved_count > 0`。
4. 工价缺失 source_map 必须 `include_in_profit=false`。
5. 明确数值 0 工价按 0 计算但仍 mapped 的正向测试必须单独覆盖。

## 4. 计算异常不得留下半快照

规则：
1. `create_snapshot()` 首次写入路径必须使用 `session.begin_nested()` 或等价保存点。
2. snapshot/detail/source_map 写入与计算必须包在保存点内。
3. 任意计算异常、类型转换异常、业务异常、SQLAlchemy 异常都必须回滚保存点。
4. 异常抛出后，调用方即使继续 `session.commit()`，数据库中也不能出现本次请求的 snapshot/detail/source_map。
5. 幂等 replay 路径不得创建保存点写入新行。
6. 幂等冲突路径不得创建任何新行。

必须补测试：
1. BOM material `item_price='bad'` 或等价非法金额触发异常后，调用方执行 `commit()`，snapshot/detail/source_map 数量仍不变。
2. 标准工序非法金额触发异常后，commit 不落半快照。
3. source_map 写入异常后，commit 不落半快照。
4. replay 路径不新增行。
5. conflict 路径不新增行。

## 5. sales_order V1 强制非空

规则：
1. `sales_order` 在 TASK-005D V1 中强制非空。
2. schema 层应使用 `Field(..., min_length=1)` 或服务层显式 strip 校验。
3. 空字符串、全空白、None 必须返回/抛出 `STYLE_PROFIT_SALES_ORDER_REQUIRED`。
4. 该错误不得创建 snapshot/detail/source_map。
5. 不允许用空 sales_order 创建 complete snapshot。

必须补测试：
1. `sales_order=''` 返回 `STYLE_PROFIT_SALES_ORDER_REQUIRED`。
2. `sales_order='   '` 返回 `STYLE_PROFIT_SALES_ORDER_REQUIRED`。
3. 空 sales_order 不落任何 snapshot/detail/source_map。
4. request_hash 不应因为空 sales_order 进入有效快照流程。

## 6. 标准工序工价缺失不得按 0 mapped

规则：
1. 标准工序工价候选：`bom_operation_rate / operation_rate / rate`。
2. 工价字段缺失、空字符串、None、不可解析数字时，必须写 `unresolved/standard_operation_rate_missing` 或 `unresolved/standard_operation_rate_invalid`。
3. 工价缺失/非法时不得 `mapping_status=mapped`，不得 `include_in_profit=true`。
4. 明确传入数值 0 可以作为 0 工价，但必须有字段存在且可解析为 0。

必须补测试：
1. 标准工序缺工价时 `standard_operation_cost` 不增加。
2. 标准工序缺工价时 snapshot 为 `incomplete`。
3. 标准工序缺工价 source_map 为 unresolved 且 `include_in_profit=false`。
4. 明确数值 0 工价的正向测试必须单独覆盖。

## 7. idempotency_key 长度校验

规则：
1. `idempotency_key` 长度不得超过 128。
2. 超长 key 必须返回/抛出 `STYLE_PROFIT_IDEMPOTENCY_KEY_TOO_LONG`。
3. 超长 key 不得落 snapshot/detail/source_map。
4. 不能依赖 PostgreSQL 字段长度错误来表达该业务错误。

必须补测试：
1. 128 字符 key 可通过。
2. 129 字符 key 返回 `STYLE_PROFIT_IDEMPOTENCY_KEY_TOO_LONG`。
3. 129 字符 key 不落库。
4. SQLite 和 PostgreSQL 语义应一致。

【错误码新增/确认】
| 场景 | 错误码 |
| --- | --- |
| sales_order 为空 | `STYLE_PROFIT_SALES_ORDER_REQUIRED` |
| idempotency_key 超过 128 | `STYLE_PROFIT_IDEMPOTENCY_KEY_TOO_LONG` |
| 幂等 key 相同但 request_hash 不同 | `STYLE_PROFIT_IDEMPOTENCY_CONFLICT` |
| 计算来源读取失败 | `STYLE_PROFIT_SOURCE_READ_FAILED` |
| 数据库写入失败 | `DATABASE_WRITE_FAILED` |
| 未知异常 | `STYLE_PROFIT_INTERNAL_ERROR` |

【验证命令】
```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest -q tests/test_style_profit_service.py tests/test_style_profit_snapshot_calculation.py tests/test_style_profit_snapshot_idempotency.py
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
```

要求：禁改扫描不得出现本任务禁止修改路径。

【验收标准】
□ 错订单、错款式、错公司的工票不得计入当前利润。
□ 错订单、错款式、错公司的外发不得计入当前利润。
□ 工票工价缺失/非法必须 unresolved，不得按 0 mapped。
□ 标准工序工价缺失/非法必须 unresolved，不得按 0 mapped。
□ 计算异常后调用方 commit 不会留下半快照、半明细、半 source_map。
□ sales_order 为空返回 `STYLE_PROFIT_SALES_ORDER_REQUIRED`，且不落库。
□ idempotency_key 超过 128 返回 `STYLE_PROFIT_IDEMPOTENCY_KEY_TOO_LONG`，且不落库。
□ replay/conflict 路径均不新增行。
□ 未注册 API，未修改前端，未新增迁移，未进入 TASK-005E/TASK-006。
□ 定向 pytest、全量 pytest、unittest、py_compile 全部通过。
□ 工程师会话日志已追加执行记录。

【预计工时】
0.5-1.5 天

════════════════════════════════════════════════════════════════════════════
