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

## Local Dev Runtime / Dev-Auth Gate (TASK-263A)

仅用于本地开发联调，禁止用于生产环境。

## Permission Source

生产环境权限源采用 FastAPI 自建口径：

- `APP_ENV=production` 时 `LINGYI_PERMISSION_SOURCE` 必须为 `fastapi`。
- `erpnext` 不再是生产强制权限源。
- `static` 仅用于本地开发和测试联调。

### 启动顺序（本地）

1. 启动后端本地 dev runtime（127.0.0.1:8000）：

```bash
cd "/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service"
bash scripts/run_local_dev_runtime.sh
```

- 脚本仅允许 `127.0.0.1:8000`，且仅在当前进程导出 `LINGYI_ALLOW_DEV_AUTH=true`。
- 若 8000 已被 pre-existing 进程占用，脚本只提示并退出，不会执行 kill。

2. 启动前端 dev server（127.0.0.1:5174）：

```bash
cd "/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc"
npm run dev -- --host 127.0.0.1 --port 5174
```

3. 执行只读门禁预检（仅 GET，本地地址）：

```bash
cd "/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc"
npm run precheck:dev-runtime
```

预检脚本会对以下端点注入 dev headers 并输出 JSON 摘要：

- `http://127.0.0.1:8000/api/auth/me`
- `http://127.0.0.1:8000/api/reports/catalog`
- `http://127.0.0.1:5174/api/auth/me`
- `http://127.0.0.1:5174/api/reports/catalog`

若任一端点非 200，脚本会以非 0 退出码返回门禁失败。

### Maintenance note (expected test count)

`scripts/run_postgresql_ci_gate.sh` 当前会分别生成并断言两份 JUnit：

- `.pytest-postgresql-subcontract-settlement.xml`
- `.pytest-postgresql-style-profit-subcontract.xml`

每一份均单独断言：

- `tests=4`
- `skipped=0`

如果你修改任一组 PostgreSQL marker 用例数量，
必须同步更新 [scripts/run_postgresql_ci_gate.sh](/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/scripts/run_postgresql_ci_gate.sh) 中对应的 `--expected-tests`，并保持 required-check 语义一致。
