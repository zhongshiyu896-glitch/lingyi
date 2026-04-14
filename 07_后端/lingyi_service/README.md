# lingyi_service

## PostgreSQL CI Hard Gate (TASK-002H6 + TASK-005F4)

PostgreSQL hard gate 当前是“后端财务门禁组合”，包含两组测试：

1. TASK-002H 外发结算并发门禁：
   - `tests/test_subcontract_settlement_postgresql.py`
2. TASK-005F4 款式利润外发来源门禁：
   - `tests/test_style_profit_subcontract_postgresql.py`

本地和 CI 的行为不同：

- 本地未设置 `POSTGRES_TEST_DSN` 时，PostgreSQL 测试允许安全 `skip`。
- CI 必须执行 PostgreSQL 非 skip 验证，且两组测试各自硬性要求：
  - `tests=4`
  - `skipped=0`
  - `failures=0`
  - `errors=0`

### Required env

- `POSTGRES_TEST_DSN`
- `POSTGRES_TEST_ALLOW_DESTRUCTIVE=true`

并且测试库名必须命中白名单（由测试代码校验）：

- `*_test`
- `test_*`
- `lingyi_test_*`
- `tmp_lingyi_*`

### Local commands

```bash
cd "/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service"

# no DSN: safe skip
.venv/bin/python -m pytest -q tests/test_subcontract_settlement_postgresql.py
.venv/bin/python -m pytest -q tests/test_style_profit_subcontract_postgresql.py

# hard gate (non-skip) with a disposable PostgreSQL test DB
POSTGRES_TEST_ALLOW_DESTRUCTIVE=true \
POSTGRES_TEST_DSN='postgresql+psycopg://<user>:<password>@<host>:<port>/lingyi_test_ci' \
bash scripts/run_postgresql_ci_gate.sh
```

### GitHub Required Check

- Workflow name: `Backend PostgreSQL Hard Gate`
- Job/check name: `subcontract-postgresql-gate`
- Recommended required check in branch protection/ruleset:
  - `Backend PostgreSQL Hard Gate / subcontract-postgresql-gate`

说明：check 名称保持历史兼容，但语义已扩展为“后端 PostgreSQL 财务门禁组合”（结算 + 款式利润）。

### Workflow JUnit Artifacts

`backend-postgresql.yml` 在 CI 中上传两份独立 JUnit artifact：

1. Artifact: `postgresql-settlement-junit`
   - File: `.pytest-postgresql-subcontract-settlement.xml`
2. Artifact: `postgresql-style-profit-junit`
   - File: `.pytest-postgresql-style-profit-subcontract.xml`

旧单文件 `.pytest-postgresql.xml` 已废弃，不再作为 PostgreSQL hard gate 证据。

### Maintenance note (expected test count)

`scripts/run_postgresql_ci_gate.sh` 当前会分别生成并断言两份 JUnit：

- `.pytest-postgresql-subcontract-settlement.xml`
- `.pytest-postgresql-style-profit-subcontract.xml`

每一份均单独断言：

- `tests=4`
- `skipped=0`

如果你修改任一组 PostgreSQL marker 用例数量，
必须同步更新 [scripts/run_postgresql_ci_gate.sh](/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/scripts/run_postgresql_ci_gate.sh) 中对应的 `--expected-tests`，并保持 required-check 语义一致。
