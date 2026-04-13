# TASK-002H6 PostgreSQL 非 Skip CI 硬门禁工程任务单

- 任务编号：TASK-002H6
- 模块：外发加工管理
- 优先级：P1
- 版本：V1.0
- 更新时间：2026-04-13 16:35 CST
- 作者：技术架构师
- 审计来源：TASK-002H5 审计意见书第 56 份通过，剩余风险为 PostgreSQL marker 在缺 `POSTGRES_TEST_DSN`、缺 `POSTGRES_TEST_ALLOW_DESTRUCTIVE` 或缺驱动时会安全 skip；若 CI 不做 skip 硬断言，可能出现“流水线绿了但 PostgreSQL 并发语义没跑”
- 架构裁决：PostgreSQL 非 skip 集成测试必须纳入 CI 硬门禁，要求 `-m postgresql` 实际执行 4 条用例且 `0 skipped`，否则 CI 失败
- 前置依赖：TASK-002H5 已通过审计意见书第 56 份；继续遵守外发模块 V1.24、ADR-052
- 任务边界：只做 CI 门禁脚本、CI 配置、测试说明和门禁自测；不得修改结算业务逻辑、不得创建 TASK-006 对账单主表、不得调用 ERPNext 写接口

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-002H6
模块：PostgreSQL 非 Skip CI 硬门禁
优先级：P1（防止 PostgreSQL 集成测试被 skip 后误绿）
════════════════════════════════════════════════════════════════════════════

【任务目标】
把 TASK-002H5 的 PostgreSQL 非 skip 验证固化为 CI 硬门禁：CI 中 `-m postgresql` 必须 `4 passed, 0 skipped`，否则流水线失败。

【模块概述】
TASK-002H5 已由工程师在一次性测试库 `lingyi_test_20260413` 上完成 PostgreSQL 非 skip 实跑，并通过审计。但是审计窗口本地无 DSN 时仍会安全 skip，这对本地开发是合理的，对 CI 却是风险：如果 CI 忘记配置 DSN、allow env 或 PostgreSQL 驱动，流水线可能显示通过但关键并发测试没有执行。本任务把“非 skip”从人工回报升级为自动化硬门禁。

【涉及文件】
新建：
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/scripts/assert_pytest_junit_no_skip.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/scripts/run_postgresql_ci_gate.sh
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_ci_postgresql_gate.py
- /Users/hh/Desktop/领意服装管理系统/.github/workflows/backend-postgresql.yml

修改：
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/README.md（如不存在则新建后端测试说明段落）
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/requirements-dev.txt（仅当门禁脚本需要已有依赖以外的测试依赖；优先不新增）

禁止修改：
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/subcontract_settlement_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/subcontract.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/factory_statement.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/factory_statement_service.py

【CI 门禁规则】
1. CI 必须启动一次性 PostgreSQL 测试库，库名必须命中白名单：`*_test`、`test_*`、`lingyi_test_*`、`tmp_lingyi_*`。
2. CI 必须设置 `POSTGRES_TEST_ALLOW_DESTRUCTIVE=true`。
3. CI 必须设置 `POSTGRES_TEST_DSN`，且 DSN 只允许指向一次性测试库。
4. CI 必须安装开发依赖，包含 `psycopg[binary]>=3.2,<4.0`。
5. CI 必须执行：
   ```bash
   .venv/bin/python -m pytest -q -m postgresql tests/test_subcontract_settlement_postgresql.py --junitxml=.pytest-postgresql.xml
   ```
6. CI 必须执行 JUnit 结果断言，要求：
   - `tests == 4`
   - `failures == 0`
   - `errors == 0`
   - `skipped == 0`
7. 如果实际执行数不是 4，CI 必须失败。
8. 如果 skipped 大于 0，CI 必须失败。
9. 如果 JUnit 文件不存在或无法解析，CI 必须失败。
10. CI 日志不得打印完整 DSN、账号或密码。
11. 本地无 DSN 时允许安全 skip，但 CI job 不允许把 skip 当成功。

【推荐实现】
1. `scripts/assert_pytest_junit_no_skip.py`
   - 入参：JUnit XML 路径、期望 tests 数、期望 skipped 数。
   - 解析 pytest JUnit XML。
   - 汇总 `tests/failures/errors/skipped`。
   - 不满足期望时 `sys.exit(1)`。
   - 错误信息只输出统计结果，不输出 DSN。

2. `scripts/run_postgresql_ci_gate.sh`
   - `set -euo pipefail`。
   - 检查 `POSTGRES_TEST_DSN` 非空。
   - 检查 `POSTGRES_TEST_ALLOW_DESTRUCTIVE=true`。
   - 运行 PostgreSQL marker 测试并生成 `.pytest-postgresql.xml`。
   - 调用 `assert_pytest_junit_no_skip.py .pytest-postgresql.xml --expected-tests 4 --expected-skipped 0`。

3. `.github/workflows/backend-postgresql.yml`
   - 使用 PostgreSQL service 容器。
   - 创建一次性测试库，例如 `lingyi_test_ci`。
   - 设置：
     - `POSTGRES_TEST_ALLOW_DESTRUCTIVE=true`
     - `POSTGRES_TEST_DSN=postgresql+psycopg://postgres:postgres@localhost:5432/lingyi_test_ci`
   - 执行 `scripts/run_postgresql_ci_gate.sh`。
   - 上传 `.pytest-postgresql.xml` 作为测试产物。

【必须补测试】
1. `test_assert_junit_passes_when_four_tests_zero_skipped`
   - 构造 JUnit：`tests=4, skipped=0, failures=0, errors=0`。
   - 断言脚本退出码为 0。

2. `test_assert_junit_fails_when_all_skipped`
   - 构造 JUnit：`tests=4, skipped=4`。
   - 断言脚本退出码非 0。

3. `test_assert_junit_fails_when_test_count_is_zero`
   - 构造 JUnit：`tests=0, skipped=0`。
   - 断言脚本退出码非 0。

4. `test_assert_junit_fails_when_test_count_is_not_four`
   - 构造 JUnit：`tests=3, skipped=0` 或 `tests=5, skipped=0`。
   - 断言脚本退出码非 0。

5. `test_assert_junit_fails_when_report_missing`
   - 传入不存在的 XML 路径。
   - 断言脚本退出码非 0。

6. `test_run_postgresql_ci_gate_requires_envs`
   - 验证缺 `POSTGRES_TEST_DSN` 或缺 `POSTGRES_TEST_ALLOW_DESTRUCTIVE=true` 时脚本直接失败，不进入 pytest。

【验收标准】
□ 已新增 CI 硬门禁脚本，能解析 pytest JUnit XML。  
□ JUnit 断言要求 PostgreSQL marker `tests=4` 且 `skipped=0`。  
□ skipped=4 时 CI 断言失败。  
□ tests=0、tests=3、tests=5 时 CI 断言失败。  
□ JUnit 文件缺失或解析失败时 CI 断言失败。  
□ CI job 设置 `POSTGRES_TEST_ALLOW_DESTRUCTIVE=true`。  
□ CI job 设置 `POSTGRES_TEST_DSN` 并指向一次性测试库。  
□ CI job 使用测试库名命中白名单，例如 `lingyi_test_ci`。  
□ CI job 执行 `scripts/run_postgresql_ci_gate.sh`。  
□ CI 日志不输出完整 DSN、账号、密码。  
□ README 说明本地允许 skip，CI 禁止 skip。  
□ `tests/test_ci_postgresql_gate.py` 通过。  
□ `tests/test_subcontract_settlement_postgresql.py` 本地无 DSN 路径仍为安全 skip。  
□ `tests/test_subcontract_settlement_export.py` 通过。  
□ 全量 pytest/unittest/py_compile 通过。  
□ 未修改结算业务逻辑、未创建 TASK-006 对账单主表、未调用 ERPNext 写接口。  

【建议命令】
```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service

# 门禁脚本单测
.venv/bin/python -m pytest -q tests/test_ci_postgresql_gate.py

# 本地无 DSN 安全路径
.venv/bin/python -m pytest -q tests/test_subcontract_settlement_postgresql.py
.venv/bin/python -m pytest -q -m postgresql tests/test_subcontract_settlement_postgresql.py

# 有一次性测试库时，模拟 CI 硬门禁
POSTGRES_TEST_ALLOW_DESTRUCTIVE=true \
POSTGRES_TEST_DSN='postgresql+psycopg://<user>:<password>@<host>:<port>/lingyi_test_ci' \
bash scripts/run_postgresql_ci_gate.sh

# 回归
.venv/bin/python -m pytest -q tests/test_subcontract_settlement_export.py
.venv/bin/python -m pytest -q
.venv/bin/python -m unittest discover
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
```

【回报格式】
工程师完成后按以下格式回报：

```text
TASK-002H6 PostgreSQL 非 Skip CI 硬门禁完成。

CI 门禁：
- workflow：.github/workflows/backend-postgresql.yml
- 测试库：lingyi_test_ci（一次性测试库，命中白名单）
- destructive gate：POSTGRES_TEST_ALLOW_DESTRUCTIVE=true
- JUnit 断言：tests=4, skipped=0

验证结果：
- tests/test_ci_postgresql_gate.py：X passed
- 本地无 DSN postgresql 文件：X passed, Y skipped
- 本地无 DSN -m postgresql：4 skipped, 5 deselected（安全 skip）
- CI 硬门禁模拟：4 passed, 0 skipped
- tests/test_subcontract_settlement_export.py：35 passed
- 全量 pytest：X passed, Y skipped
- unittest discover：Ran X tests OK
- py_compile：通过

改动文件：
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/scripts/assert_pytest_junit_no_skip.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/scripts/run_postgresql_ci_gate.sh
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_ci_postgresql_gate.py
- /Users/hh/Desktop/领意服装管理系统/.github/workflows/backend-postgresql.yml
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/README.md

风险/说明：
- [如无，写“无”]
```

【禁止事项】
- 禁止把 `4 skipped` 当成 CI 通过。
- 禁止 CI job 缺 `POSTGRES_TEST_DSN` 时显示成功。
- 禁止 CI job 缺 `POSTGRES_TEST_ALLOW_DESTRUCTIVE=true` 时显示成功。
- 禁止连接生产、预发、开发共享库或 ERPNext 真实业务库。
- 禁止在日志中输出完整 DSN、账号、密码。
- 禁止用 SQLite、mock 或 monkeypatch 替代 PostgreSQL CI 门禁。
- 禁止修改结算业务逻辑。
- 禁止进入 TASK-006 代码实现。
- 禁止创建加工厂对账单主表、Purchase Invoice、Payment Entry 或 GL。
- 禁止调用 ERPNext 写接口。

【前置依赖】
TASK-002H5 审计意见书第 56 份通过。

【后置门禁】
TASK-002H6 通过审计后，才允许进入 TASK-006 加工厂对账单模块开发。

【预计工时】
0.5 天

════════════════════════════════════════════════════════════════════════════
