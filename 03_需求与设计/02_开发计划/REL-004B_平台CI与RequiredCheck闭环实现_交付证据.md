# REL-004B 平台 CI 与 Required Check 闭环实现交付证据

## 1. 执行结论

- 任务编号：REL-004B
- 执行时间：2026-04-16
- 前置审计：REL-004A 审计通过
- 结论：平台 CI / Required Check workflow 与辅助脚本已落地；REL-004B1 已按审计意见完成门禁收口，建议进入 REL-004B1 审计复核。
- 是否 push：否
- 是否配置 remote：否
- 是否创建 PR：否
- 是否生产发布：否
- 是否写入凭据：否

## 2. 本次实现文件

### 2.1 GitHub Actions workflow

- `.github/workflows/frontend-verify.yml`
- `.github/workflows/backend-test.yml`
- `.github/workflows/backend-postgresql.yml`
- `.github/workflows/docs-boundary.yml`

### 2.2 CI 辅助脚本

- `scripts/ci/write_ci_metadata.sh`
- `scripts/ci/assert_no_sensitive_values.py`
- `scripts/ci/docs_boundary_check.sh`

## 3. Required Check 名称落地

已按 REL-004A 冻结口径实现：

1. `Frontend Verify Hard Gate / lingyi-pc-verify`
2. `Backend Test Hard Gate / lingyi-service-test`
3. `Backend PostgreSQL Hard Gate / postgresql-non-skip-gate`
4. `Docs Boundary Gate / docs-boundary-check`

## 4. 检查矩阵落地

### 4.1 前端 gate

`Frontend Verify Hard Gate / lingyi-pc-verify` 覆盖：

- `npm ci`
- `npm run verify`
- `npm audit --audit-level=high`
- `npm run test:frontend-contract-engine`
- `npm run test:style-profit-contracts`
- `npm run test:factory-statement-contracts`
- `npm run test:sales-inventory-contracts`
- `npm run test:quality-contracts`

### 4.2 后端 gate

`Backend Test Hard Gate / lingyi-service-test` 覆盖：

- `.venv/bin/python -m pytest -q --junitxml=.ci-reports/backend-pytest.xml`
- `.venv/bin/python -m unittest discover`
- `.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)`

### 4.3 PostgreSQL non-skip gate

`Backend PostgreSQL Hard Gate / postgresql-non-skip-gate` 覆盖：

- `scripts/run_postgresql_ci_gate.sh`
- subcontract / factory-statement PostgreSQL JUnit
- style-profit PostgreSQL JUnit
- `assert_pytest_junit_no_skip.py` 强制 `tests=4, skipped=0, failures=0, errors=0`

### 4.4 Docs boundary gate

`Docs Boundary Gate / docs-boundary-check` 覆盖：

- 阻断 docs-only 提交混入 `06_前端/**`
- 阻断 docs-only 提交混入 `07_后端/**`
- 阻断 docs-only 提交混入 `.github/**`
- 阻断 docs-only 提交混入 `02_源码/**`
- 阻断 `node_modules/dist/__pycache__/.pytest_cache` 等运行产物
- 阻断 `.pytest-postgresql*.xml`、`.pyc`、非示例 `.env*`
- 对变更文本执行凭据形态扫描

### 4.5 REL-004B1 审计整改项

1. `docs_boundary_check.sh` 已补齐 docs-only 禁入路径：`06_前端/**`、`07_后端/**`、`.github/**`、`02_源码/**`。
2. 四个 workflow 已显式写入 required check 完整组合名，支持按任务卡 `grep` 精确命中：
   - `Frontend Verify Hard Gate / lingyi-pc-verify`
   - `Backend Test Hard Gate / lingyi-service-test`
   - `Backend PostgreSQL Hard Gate / postgresql-non-skip-gate`
   - `Docs Boundary Gate / docs-boundary-check`
3. 敏感信息扫描器已移除 PostgreSQL 明文密码/DSN 白名单，不再跳过 `POSTGRES_PASSWORD: lingyi_pwd` 或明文 DSN。
4. PostgreSQL workflow 已改为引用平台 secret：`LINGYI_CI_POSTGRES_PASSWORD`；仓库文件不记录密码或完整明文 DSN。
5. 若平台未配置 `LINGYI_CI_POSTGRES_PASSWORD`，PostgreSQL required check 会 fail closed，不得伪装通过。

## 5. Artifact / 元数据落地

已新增统一 CI 元数据脚本：`scripts/ci/write_ci_metadata.sh`。

各 gate 上传 artifact：

- `frontend-verify-report-${{ github.sha }}`
- `backend-test-report-${{ github.sha }}`
- `postgresql-non-skip-report-${{ github.sha }}`
- `docs-boundary-report-${{ github.sha }}`

保留 PostgreSQL 既有双 JUnit artifact：

- `postgresql-settlement-junit`
- `postgresql-style-profit-junit`

元数据包含：

- gate name
- run URL
- commit SHA
- runner OS
- Node / npm 版本
- Python 版本
- PostgreSQL 版本（如可用）
- UTC 收集时间
- 敏感信息扫描结果说明

## 6. 本地验证结果

- `bash -n scripts/ci/write_ci_metadata.sh scripts/ci/docs_boundary_check.sh 07_后端/lingyi_service/scripts/run_postgresql_ci_gate.sh`：通过
- `python3 -m py_compile scripts/ci/assert_no_sensitive_values.py 07_后端/lingyi_service/scripts/assert_pytest_junit_no_skip.py`：通过
- `.venv/bin/python -m pytest -q tests/test_ci_postgresql_gate.py`：通过（12 passed, 1 warning）
- `python3 scripts/ci/assert_no_sensitive_values.py .github/workflows scripts/ci 07_后端/lingyi_service/scripts/run_postgresql_ci_gate.sh`：通过
- 明文凭据反向样例 `POSTGRES_PASSWORD: lingyi_pwd`：敏感扫描按预期失败并返回 `credential-shaped value detected`
- `bash scripts/ci/docs_boundary_check.sh HEAD~1`：通过
- Required Check 完整组合名 grep：四组 workflow/job 名称均命中
- docs-only 禁入路径 grep：`06_前端/**`、`07_后端/**`、`.github/**`、`02_源码/**` 均命中
- `git diff --check`：通过
- 禁改业务路径扫描：`06_前端/lingyi-pc/src`、`07_后端/lingyi_service/app`、`07_后端/lingyi_service/migrations`、`02_源码` 无输出

## 7. 边界声明

- 未修改前端业务页面或前端业务源码。
- 未修改后端业务逻辑或数据库迁移。
- 未修改 `02_源码/**`。
- 未执行 push。
- 未配置 remote。
- 未创建 PR。
- 未宣称 hosted runner 已通过。
- 未宣称 required check 已闭环。
- 未宣称生产发布完成。
- 未写入凭据。
- PostgreSQL workflow 仅引用 GitHub secret 名称，不写入 secret 值。

## 8. 待平台动作

REL-004B 只完成本地 workflow / 脚本实现。后续仍需管理员：

1. 配置 GitHub Secret：`LINGYI_CI_POSTGRES_PASSWORD`。
2. 配置 remote。
3. 安全 push。
4. 在 GitHub hosted runner 实跑四个 required checks。
5. 将四个 required checks 配置为 `main` 分支保护要求。
6. 回填 run URL、artifact、JUnit 指标与 required check 配置截图/记录。
