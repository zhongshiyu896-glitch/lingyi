# TASK-005F5 PostgreSQL 门禁目标恢复与双 JUnit 断言工程任务单

- 任务编号：TASK-005F5
- 模块：款式利润报表 / 外发加工管理 / CI 本地门禁
- 版本：V1.0
- 更新时间：2026-04-14 15:40 CST
- 作者：技术架构师
- 优先级：P0
- 前置依赖：TASK-005F4 审计不通过，审计意见书第 107 份
- 执行角色：后端工程师
- 审计要求：完成后必须提交审计官复审；复审通过前不得进入 TASK-005G、前端创建入口或 TASK-006

## 1. 任务目标

修复 TASK-005F4 审计发现的 PostgreSQL hard gate 被静默替换问题。

当前 `scripts/run_postgresql_ci_gate.sh` 被改成只跑 TASK-005F4 款式利润 PostgreSQL 测试，但该脚本仍由 `subcontract-postgresql-gate` required check 调用。这样会让原 TASK-002H 外发结算 PostgreSQL 并发门禁被静默覆盖。

本任务采用方案 B：保留单一脚本，但脚本必须同时运行两组 PostgreSQL 测试，并分别生成/断言 JUnit：

1. TASK-002H 外发结算 PostgreSQL 门禁：`tests/test_subcontract_settlement_postgresql.py`，必须保留 4 条非 skip。
2. TASK-005F4 款式利润外发 PostgreSQL 门禁：`tests/test_style_profit_subcontract_postgresql.py`，必须新增 4 条非 skip。

## 2. 本任务边界

### 2.1 允许修改

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/scripts/run_postgresql_ci_gate.sh`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/scripts/assert_pytest_junit_no_skip.py`（仅限兼容多 JUnit 调用，不得削弱断言）
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_ci_postgresql_gate.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_subcontract_postgresql.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/README.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005F4_PostgreSQL非Skip证据.md`

### 2.2 禁止修改

- 禁止修改 `/Users/hh/Desktop/领意服装管理系统/06_前端/**`
- 禁止修改 `/Users/hh/Desktop/领意服装管理系统/.github/**`
- 禁止修改 `/Users/hh/Desktop/领意服装管理系统/02_源码/**`
- 禁止修改迁移文件
- 禁止新增或修改任何 `TASK-006*` 文件
- 禁止删除、跳过或弱化 `tests/test_subcontract_settlement_postgresql.py`
- 禁止把 settlement PG 测试替换成 style-profit PG 测试

## 3. 脚本修复要求

修改：

`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/scripts/run_postgresql_ci_gate.sh`

必须实现：

1. 检查 `POSTGRES_TEST_DSN` 存在。
2. 检查 `POSTGRES_TEST_ALLOW_DESTRUCTIVE=true`。
3. 检查 `.venv/bin/python` 存在。
4. 先运行 TASK-002H 外发结算 PG 测试：
   - target：`tests/test_subcontract_settlement_postgresql.py`
   - JUnit：`.pytest-postgresql-subcontract-settlement.xml`
   - 断言：`--expected-tests 4 --expected-skipped 0`
5. 再运行 TASK-005F4 款式利润外发 PG 测试：
   - target：`tests/test_style_profit_subcontract_postgresql.py`
   - JUnit：`.pytest-postgresql-style-profit-subcontract.xml`
   - 断言：`--expected-tests 4 --expected-skipped 0`
6. 任一组失败、skip、测试数量不符，脚本必须失败。
7. 成功输出必须明确两组门禁均通过。
8. 不得复用同一个 JUnit 文件覆盖前一组结果。
9. 不得把 expected-tests 改成 8 后只做总量断言；必须分别断言两组，避免一组多测、一组全 skip 被掩盖。

## 4. CI gate 目标一致性测试

修改：

`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_ci_postgresql_gate.py`

必须新增测试：

1. 读取 `scripts/run_postgresql_ci_gate.sh` 文本。
2. 断言包含 `tests/test_subcontract_settlement_postgresql.py`。
3. 断言包含 `tests/test_style_profit_subcontract_postgresql.py`。
4. 断言包含 `.pytest-postgresql-subcontract-settlement.xml`。
5. 断言包含 `.pytest-postgresql-style-profit-subcontract.xml`。
6. 断言 settlement gate 调用了 `--expected-tests 4 --expected-skipped 0`。
7. 断言 style-profit gate 调用了 `--expected-tests 4 --expected-skipped 0`。
8. 断言两个 JUnit 文件名不同。
9. 保留原有缺 env fail-fast 测试。
10. 增加反向测试：如果脚本文本只包含 style-profit 目标、不包含 settlement 目标，测试必须失败。

## 5. TASK-005F4 PostgreSQL 非 skip 证据

如当前环境仍无真实 PostgreSQL DSN：

1. 不得伪装非 skip 已通过。
2. 证据文件必须明确：本地无 DSN，`tests/test_style_profit_subcontract_postgresql.py` 当前为 `4 skipped`。
3. 证据文件必须明确：双门禁脚本已恢复 settlement + style-profit 两组目标。
4. 证据文件必须保留待回填字段：
   - settlement JUnit：`tests=4, skipped=0, failures=0, errors=0`
   - style-profit JUnit：`tests=4, skipped=0, failures=0, errors=0`
5. 后续拿到 DSN 后必须实跑并回填。

如有真实 PostgreSQL DSN：

1. 必须执行完整脚本。
2. 必须生成两个 JUnit 文件。
3. 必须用 `assert_pytest_junit_no_skip.py` 分别断言两份 JUnit。
4. 证据文件必须记录脱敏 DSN、命令、结果和两份 JUnit 指标。

## 6. README 更新要求

更新 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/README.md`：

1. 明确 `run_postgresql_ci_gate.sh` 同时覆盖：
   - TASK-002H 外发结算 PostgreSQL 门禁
   - TASK-005F4 款式利润外发 PostgreSQL 门禁
2. 明确 required check 名称如果仍叫 `subcontract-postgresql-gate`，其实际含义已经是“后端 PostgreSQL 财务门禁组合”。
3. 明确两组 JUnit 文件路径。
4. 明确无 DSN 时本地可 skip，但硬门禁必须非 skip。
5. 不得删除原 TASK-002H 说明。

## 7. 测试要求

必须通过：

1. `tests/test_ci_postgresql_gate.py`。
2. `tests/test_style_profit_subcontract_postgresql.py` 在无 DSN 下安全 skip。
3. `tests/test_subcontract_settlement_postgresql.py` 在无 DSN 下安全 skip。
4. 全量 pytest。
5. unittest discover。
6. py_compile。

如果有 PostgreSQL DSN，必须额外通过完整脚本：

```bash
POSTGRES_TEST_ALLOW_DESTRUCTIVE=true POSTGRES_TEST_DSN='postgresql+psycopg://***@HOST:PORT/lingyi_test_xxx' ./scripts/run_postgresql_ci_gate.sh
```

## 8. 建议验证命令

在 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service` 执行：

```bash
.venv/bin/python -m pytest -q tests/test_ci_postgresql_gate.py
.venv/bin/python -m pytest -q tests/test_style_profit_subcontract_postgresql.py tests/test_subcontract_settlement_postgresql.py
.venv/bin/python -m pytest -q -m postgresql tests/test_style_profit_subcontract_postgresql.py tests/test_subcontract_settlement_postgresql.py
.venv/bin/python -m pytest -q
.venv/bin/python -m unittest discover
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
```

## 9. 禁改扫描

交付前必须执行：

```bash
git status --short -- 06_前端 .github 02_源码 07_后端/lingyi_service/migrations 03_需求与设计/02_开发计划/TASK-006*
```

预期：无前端、`.github`、`02_源码`、migrations、TASK-006 改动。

## 10. 验收标准

□ `run_postgresql_ci_gate.sh` 同时运行 settlement PG 测试和 style-profit PG 测试。  
□ settlement PG 测试目标 `tests/test_subcontract_settlement_postgresql.py` 被保留。  
□ style-profit PG 测试目标 `tests/test_style_profit_subcontract_postgresql.py` 被保留。  
□ 两组测试分别生成不同 JUnit 文件。  
□ 两组 JUnit 分别断言 `tests=4, skipped=0`。  
□ 任一组全 skip 或测试数量不符时脚本失败。  
□ CI gate 目标一致性测试能发现 settlement 目标被移除的情况。  
□ README 明确双门禁含义。  
□ F4 证据文件不伪装非 skip，通过或 pending 状态清楚。  
□ 定向 pytest、全量 pytest、unittest、py_compile 通过。  
□ 禁改扫描通过。  
□ 审计官复审通过前不得进入 TASK-005G、前端创建入口或 TASK-006。  

## 11. 交付说明要求

工程师交付时必须说明：

1. `run_postgresql_ci_gate.sh` 当前包含的两个测试目标。
2. 两份 JUnit 文件名。
3. 两组 expected-tests / expected-skipped 断言。
4. `tests/test_ci_postgresql_gate.py` 新增的目标一致性测试。
5. 本地无 DSN 时的 skip 结果，或真实 DSN 下的非 skip 结果。
6. README 更新摘要。
7. 禁改扫描结果。
8. 未进入前端、未进入迁移、未进入 TASK-006。
