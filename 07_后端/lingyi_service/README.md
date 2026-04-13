# lingyi_service

## PostgreSQL CI Hard Gate (TASK-002H6)

结算并发集成测试在本地和 CI 的行为不同：

- 本地未设置 `POSTGRES_TEST_DSN` 时，`tests/test_subcontract_settlement_postgresql.py` 允许安全 `skip`。
- CI 必须执行 PostgreSQL 非 skip 验证，并且硬性要求：
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

### Maintenance note (expected test count)

`scripts/run_postgresql_ci_gate.sh` currently asserts:

- `tests=4`
- `skipped=0`

If you add/remove PostgreSQL marker cases in `tests/test_subcontract_settlement_postgresql.py`,
you must update `--expected-tests` in [scripts/run_postgresql_ci_gate.sh](/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/scripts/run_postgresql_ci_gate.sh) and keep CI required-check semantics aligned.
