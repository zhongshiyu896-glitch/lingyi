# TASK-005F6 Workflow 双 JUnit 上传证据

- 任务编号：TASK-005F6
- 执行时间：2026-04-14 16:10 CST
- 执行环境：`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service`

## 1. Workflow artifact 修改方案

采用方案 B（两个 artifact 分离上传）。

修改文件：
- `/Users/hh/Desktop/领意服装管理系统/.github/workflows/backend-postgresql.yml`

已修复内容：
1. 上传 settlement JUnit：
   - artifact：`postgresql-settlement-junit`
   - path：`07_后端/lingyi_service/.pytest-postgresql-subcontract-settlement.xml`
2. 上传 style-profit JUnit：
   - artifact：`postgresql-style-profit-junit`
   - path：`07_后端/lingyi_service/.pytest-postgresql-style-profit-subcontract.xml`
3. 不再使用旧单路径 `07_后端/lingyi_service/.pytest-postgresql.xml`。
4. workflow 仍调用 `bash scripts/run_postgresql_ci_gate.sh`。
5. workflow 仍保留 PostgreSQL service。

## 2. test_ci_postgresql_gate.py 新增测试

修改文件：
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_ci_postgresql_gate.py`

新增校验：
1. `test_backend_postgresql_workflow_uploads_both_junit_artifacts`
2. `test_backend_postgresql_workflow_validation_fails_for_legacy_single_junit_upload`

新增覆盖点：
- workflow 同时包含 settlement + style-profit 两个 JUnit 上传路径。
- workflow 不得回退为仅旧 `.pytest-postgresql.xml` 上传。
- workflow 必须继续调用 `run_postgresql_ci_gate.sh`。
- workflow 必须保留 postgres service。

## 3. README 更新摘要

修改文件：
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/README.md`

更新点：
1. 增加 “Workflow JUnit Artifacts” 说明。
2. 明确两份 artifact 与对应 JUnit 文件名。
3. 明确旧 `.pytest-postgresql.xml` 已废弃。
4. 保留 required check 语义说明（`subcontract-postgresql-gate` 代表后端 PostgreSQL 财务门禁组合）。

## 4. 验证结果

1. `pytest -q tests/test_ci_postgresql_gate.py`
   - 结果：`10 passed`
2. `pytest -q tests/test_style_profit_subcontract_postgresql.py tests/test_subcontract_settlement_postgresql.py`
   - 结果：`5 passed, 8 skipped`
3. `pytest -q -m postgresql tests/test_style_profit_subcontract_postgresql.py tests/test_subcontract_settlement_postgresql.py`
   - 结果：`8 skipped, 5 deselected`
4. `pytest -q`
   - 结果：`639 passed, 13 skipped`
5. `python -m unittest discover`
   - 结果：`Ran 624 tests ... OK (skipped=1)`
6. `python -m py_compile $(find app tests -name '*.py' -print)`
   - 结果：通过
7. `bash scripts/run_postgresql_ci_gate.sh`（无 DSN）
   - 结果：按预期 fast-fail，`POSTGRES_TEST_DSN is required for PostgreSQL CI gate`

## 5. PostgreSQL 非 skip 证据状态

当前本地未提供真实 `POSTGRES_TEST_DSN`，保持 pending，不伪装为 non-skip 通过：

- settlement JUnit：pending（待真实 PG DSN 回填 `tests=4, skipped=0, failures=0, errors=0`）
- style-profit JUnit：pending（待真实 PG DSN 回填 `tests=4, skipped=0, failures=0, errors=0`）

## 6. 敏感信息扫描

执行与检查结果：
1. 本次文档与 workflow 未写入 token/password/secret/cookie。
2. DSN 仅以占位形式记录，不包含明文凭据。
3. 无新增私钥、Authorization 头、Cookie 明文。

## 7. 禁改扫描

执行命令：

```bash
git status --short -- 06_前端 02_源码 07_后端/lingyi_service/migrations 03_需求与设计/02_开发计划/TASK-006*
```

结果：
- 未出现 `TASK-006*` 改动。
- 未新增前端或迁移改动。
- `02_源码` 与 `06_前端/lingyi-pc/README.md` 为既有未跟踪项，非本任务新增修改。

## 8. 范围确认

- 未修改业务代码（仅 workflow、门禁测试、README、证据文档）。
- 未进入前端实现。
- 未进入迁移。
- 未进入 TASK-006。
