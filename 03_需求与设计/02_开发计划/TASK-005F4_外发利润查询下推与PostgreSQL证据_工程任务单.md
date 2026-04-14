# TASK-005F4 外发利润查询下推与 PostgreSQL 证据工程任务单

- 任务编号：TASK-005F4
- 模块：款式利润报表 / 外发加工管理
- 版本：V1.0
- 更新时间：2026-04-14 15:15 CST
- 作者：技术架构师
- 优先级：P0
- 前置依赖：TASK-005F3 审计通过，审计意见书第 106 份
- 执行角色：后端工程师
- 审计要求：完成后必须提交审计官复审；复审通过前不得进入 TASK-005G、前端创建入口或 TASK-006

## 1. 任务目标

修复 TASK-005F3 审计保留的最优先风险：外发来源当前先按 `company/item_code` 拉取候选，再在 Python 层按 `inspected_at` 过滤期间。数据量上来后，这会让款式利润快照生成变成大查询和内存过滤。

本任务要求把 `inspected_at` 期间过滤下推到数据库，并补 PostgreSQL 非 skip 集成证据，作为 TASK-005 财务封版前置门禁之一。

## 2. 本任务边界

### 2.1 允许修改

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_style_profit_adapter.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/style_profit_service.py`（仅限 source_map 诊断字段需要，不得改公式）
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_subcontract_bridge.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_api_postgresql.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_ci_postgresql_gate.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/scripts/run_postgresql_ci_gate.sh`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/scripts/assert_pytest_junit_no_skip.py`（仅限扩展测试数断言配置，不得削弱原门禁）
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/pytest.ini`（仅限 marker 或测试路径说明）

### 2.2 允许新建

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_subcontract_postgresql.py`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005F4_PostgreSQL非Skip证据.md`

### 2.3 禁止修改

- 禁止修改 `/Users/hh/Desktop/领意服装管理系统/06_前端/**`
- 禁止修改 `/Users/hh/Desktop/领意服装管理系统/.github/**`
- 禁止修改 `/Users/hh/Desktop/领意服装管理系统/02_源码/**`
- 禁止新增或修改迁移文件，除非审计官明确要求
- 禁止新增或修改任何 `TASK-006*` 文件
- 禁止修改利润公式
- 禁止弱化现有 PostgreSQL 安全门禁
- 禁止用 `created_at` 替代 `inspected_at` 做利润期间过滤

## 3. 查询下推要求

### 3.1 业务口径

外发利润来源期间过滤必须以 `LySubcontractInspection.inspected_at` 为准：

1. `from_date` 非空时，数据库查询必须包含 `inspected_at >= from_date`。
2. `to_date` 非空时，数据库查询必须包含 `inspected_at <= to_date` 的日期结束边界。
3. `inspected_at IS NULL` 不得进入正常成本候选查询。
4. 缺 `inspected_at` 的候选事实如需诊断，必须单独走受限诊断查询，不得混入正常成本候选。
5. `created_at` 不得作为默认 fallback。

### 3.2 查询形态

外发来源 Adapter 查询必须尽量在数据库层收敛：

1. 必须过滤 `company == selector.company`。
2. 必须过滤 `item_code == selector.item_code`。
3. 必须过滤 `inspected_at` 期间。
4. 如果 selector.sales_order 非空，优先在数据库层过滤 `sales_order == selector.sales_order` 或 order fallback 桥接。
5. 如果 selector.work_order 非空，优先在数据库层过滤 `work_order == selector.work_order` 或 order fallback 桥接。
6. Python 层只允许做最终安全校验和 source_map 解释，不得负责主要期间过滤。

### 3.3 缺 inspected_at 诊断集合

如保留缺 `inspected_at` 的 unresolved 诊断，必须满足：

1. 单独查询。
2. 查询必须限制 `company + item_code`。
3. 必须设置最大返回数量，例如 `STYLE_PROFIT_SUBCONTRACT_DIAGNOSTIC_LIMIT=200`。
4. 超过限制时，写一个聚合诊断项，不得拉全量。
5. 诊断项不得计入利润。
6. source_map 原因码为 `SUBCONTRACT_INSPECTED_AT_REQUIRED`。

## 4. PostgreSQL 非 skip 集成测试要求

### 4.1 新增测试文件

新增：

`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_subcontract_postgresql.py`

必须使用 `@pytest.mark.postgresql`，并沿用现有安全门禁：

1. `POSTGRES_TEST_DSN` 必须存在。
2. `POSTGRES_TEST_ALLOW_DESTRUCTIVE=true` 必须存在。
3. 数据库名必须匹配测试库规则，例如 `*_test` 或 `lingyi_test_*`。
4. 错误信息必须脱敏 DSN，不得泄露用户名、密码。
5. 无 DSN 本地路径可以 skip，但 CI 硬门禁必须检查非 skip 证据。

### 4.2 必须覆盖的 PostgreSQL 用例

至少 4 条非 skip 用例：

1. `test_postgresql_subcontract_profit_filters_by_inspected_at`  
   插入三条外发验货：`inspected_at` 在期间内、期间外、为空。断言正常采集只返回期间内，空值只进入受限诊断或不进入成本。

2. `test_postgresql_subcontract_profit_filters_work_order_in_database`  
   插入同 SO 同款但不同 Work Order 的 ready 外发验货。selector 带 `WO-1` 时，只返回/计入 `WO-1`。

3. `test_postgresql_subcontract_profit_uses_indexed_period_query`  
   验证查询计划或查询构造使用 `company + item_code + sales_order/work_order + inspected_at` 条件。可通过 SQLAlchemy statement 编译断言，或在 PostgreSQL 下用 `EXPLAIN` 验证没有退化成只按 company/item 全表扫描。

4. `test_postgresql_subcontract_profit_missing_inspected_at_is_limited_diagnostic`  
   插入超过诊断限制数量的缺 `inspected_at` 外发验货，断言不会全量拉取，且返回聚合诊断或限制条数。

### 4.3 CI 硬门禁要求

如果复用现有 `scripts/run_postgresql_ci_gate.sh` 和 `tests/test_ci_postgresql_gate.py`：

1. 不得削弱现有 settlement PostgreSQL 4 条非 skip 断言。
2. 可新增 style-profit subcontract PostgreSQL gate，要求该文件至少 `4 passed, 0 skipped`。
3. JUnit 断言必须明确 tests 数量和 skipped=0。
4. 无 DSN 的本地默认测试仍可 skip，但审计证据必须区分“本地 skip”与“CI 非 skip”。
5. 如果当前没有真实 PostgreSQL DSN，必须生成证据模板，标记 pending，不得伪装非 skip 已通过。

## 5. 性能与安全要求

1. 外发来源正常路径不得拉取同公司同款全量历史后再 Python 过滤期间。
2. 不得把缺 `inspected_at` 的历史脏数据全量拉入内存。
3. 查询异常返回 `DATABASE_READ_FAILED` 或统一业务错误，不得吞错返回空列表。
4. source_map 和日志不得泄露敏感字段。
5. 保持 TASK-005F3 Work Order 严格匹配不回退。
6. 保持 `profit_scope_status == ready` fail-closed 门禁不回退。

## 6. 测试要求

必须补齐：

1. 单元测试：外发 Adapter 查询不再按 `created_at` 过滤。
2. 单元测试：`inspected_at` 在期间外不会进入正常成本候选。
3. 单元测试：缺 `inspected_at` 不计入利润。
4. 单元测试：诊断限制生效。
5. PostgreSQL 测试：至少 4 条 marker 用例。
6. CI gate 测试：非 skip JUnit 断言不会被全 skip 绕过。
7. 回归测试：TASK-005F3 的 work_order mismatch 不回退。

## 7. 建议验证命令

在 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service` 执行：

```bash
.venv/bin/python -m pytest -q tests/test_style_profit_subcontract_bridge.py tests/test_style_profit_api_source_adapter.py
.venv/bin/python -m pytest -q tests/test_style_profit_subcontract_postgresql.py
.venv/bin/python -m pytest -q -m postgresql tests/test_style_profit_subcontract_postgresql.py
.venv/bin/python -m pytest -q
.venv/bin/python -m unittest discover
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
```

如有 PostgreSQL DSN：

```bash
POSTGRES_TEST_ALLOW_DESTRUCTIVE=true POSTGRES_TEST_DSN='postgresql+psycopg://***@HOST:PORT/lingyi_test_xxx' .venv/bin/python -m pytest -q -m postgresql tests/test_style_profit_subcontract_postgresql.py --junitxml=/tmp/style-profit-subcontract-postgresql.xml
.venv/bin/python scripts/assert_pytest_junit_no_skip.py /tmp/style-profit-subcontract-postgresql.xml --expected-tests 4
```

注意：交付说明不得记录真实 DSN、用户名、密码、token。

## 8. 禁改扫描

交付前必须执行：

```bash
git status --short -- 06_前端 .github 02_源码 03_需求与设计/02_开发计划/TASK-006*
```

预期：无前端、`.github`、`02_源码`、TASK-006 改动。

## 9. 验收标准

□ 外发来源正常查询把 `inspected_at` 期间过滤下推到数据库。  
□ 正常成本候选不再通过 Python 层做主要期间过滤。  
□ `created_at` 不再作为利润期间默认过滤字段。  
□ 缺 `inspected_at` 的外发事实不计入利润。  
□ 缺 `inspected_at` 诊断集合有限制，不会拉全量。  
□ selector 带 work_order 时，数据库查询或最终结果只保留当前 work_order。  
□ PostgreSQL marker 测试至少 4 条。  
□ CI/JUnit 硬门禁能识别全 skip 并失败。  
□ 定向 pytest、全量 pytest、unittest、py_compile 通过。  
□ 禁改扫描通过。  
□ 审计官复审通过前不得进入 TASK-005G、前端创建入口或 TASK-006。  

## 10. 交付说明要求

工程师交付时必须说明：

1. 外发来源查询下推的实现位置。
2. `inspected_at` 正常查询和缺失诊断查询的区别。
3. 诊断限制值和超过限制的处理。
4. PostgreSQL marker 测试数量和结果。
5. JUnit 非 skip 硬门禁结果；如无 DSN，必须明确 pending，不得伪装通过。
6. 定向/全量测试结果。
7. 禁改扫描结果。
8. 未进入前端、未进入 TASK-006。
