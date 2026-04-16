# REL-004D 平台管理员待办证据模板

## 1. 模板状态

- 任务编号：REL-004D
- 模板版本：V1.0
- 创建时间：2026-04-16 CST
- 本地基线 commit：`1818d971ef7062562845ff758b21d057d61ff244`
- 本地 commit message：`ci: add platform required check gates`
- 当前状态：待仓库管理员 / DevOps 管理员执行平台闭环
- 当前 remote 状态：未配置
- 当前 push 状态：未 push
- 当前 PR 状态：未创建
- 平台闭环状态：未完成
- 生产发布状态：未发布
- 重要声明：本模板用于管理员执行与审计回填；模板创建完成不等于 Hosted Runner 通过，不等于 branch protection required checks 已配置，不等于生产发布完成。

## 2. 管理员执行前置

管理员执行前必须确认：

1. 具备 GitHub 仓库管理员权限，或具备 Actions、Secrets、Branch protection / Rulesets 管理权限。
2. GitHub 仓库 URL 不含 token、password、secret、cookie、authorization。
3. 本地待推送 HEAD 为：`1818d971ef7062562845ff758b21d057d61ff244`。
4. 禁止 force push。
5. 禁止在任何证据文档中填写完整 DSN、密码、token、cookie、authorization。
6. 若远端 `main` 存在不兼容历史，必须停止并单独下发远端历史对齐任务，不得强推覆盖。

## 3. GitHub Secret 配置待办

管理员在 GitHub 仓库中配置以下 Secret：

| Secret 名称 | 用途 | 配置状态 | 配置人 | 配置时间 |
| --- | --- | --- | --- | --- |
| `LINGYI_CI_POSTGRES_PASSWORD` | PostgreSQL Hosted Runner service 与 `POSTGRES_TEST_DSN` 使用 | 管理员回填 | 管理员回填 | 管理员回填 |

核验要求：

1. 只记录 Secret 名称，不记录 Secret 值。
2. 未配置该 Secret 时，`Backend PostgreSQL Hard Gate / postgresql-non-skip-gate` 必须 fail closed。
3. Secret 值不得写入 workflow、日志、artifact、审计记录或本模板。

## 4. Remote / Push 待办

### 4.1 Remote 配置

| 项目 | 管理员回填 |
| --- | --- |
| GitHub 仓库 URL（无凭据） | 管理员回填 |
| remote 名称 | `origin` / 管理员回填 |
| `git remote -v` 脱敏结果 | 管理员回填 |
| 配置人 | 管理员回填 |
| 配置时间 | 管理员回填 |

禁止事项：

1. 禁止 remote URL 中包含 token、password、secret、cookie、authorization。
2. 禁止把私人凭据写入文档。

### 4.2 Push 前检查

管理员执行前必须记录：

```bash
git rev-parse HEAD
git remote -v
git ls-remote origin main
```

| 检查项 | 结果 |
| --- | --- |
| 本地 HEAD 是否为 `1818d971ef7062562845ff758b21d057d61ff244` | 管理员回填 |
| 远端 `main` 是否存在 | 管理员回填 |
| 远端 `main` 是否可 fast-forward / 安全推送 | 管理员回填 |
| 是否未使用 force push | 管理员回填 |

### 4.3 Push 结果

| 项目 | 管理员回填 |
| --- | --- |
| 推送分支 | `main` / 管理员回填 |
| 远端 HEAD SHA | 管理员回填 |
| 远端 HEAD 是否等于本地基线 commit | 管理员回填 |
| push 执行人 | 管理员回填 |
| push 时间 | 管理员回填 |

## 5. Hosted Runner 执行证据

必须在 GitHub Actions Hosted Runner 上实跑以下四个 workflow / job，并记录 GitHub 实际显示名称。

### 5.1 Frontend Verify Hard Gate

| 字段 | 管理员回填 |
| --- | --- |
| Required Check 名称 | `Frontend Verify Hard Gate / lingyi-pc-verify` |
| Workflow | `Frontend Verify Hard Gate` |
| Job | `lingyi-pc-verify` |
| Run URL | 管理员回填 |
| Run conclusion | 管理员回填 |
| Commit SHA | 管理员回填 |
| Runner | GitHub Actions hosted runner / 管理员回填 |
| Runner OS | 管理员回填 |
| 执行开始时间 | 管理员回填 |
| 执行结束时间 | 管理员回填 |
| 执行总耗时 | 管理员回填 |
| Artifact | `frontend-verify-report-<sha>` / 管理员回填 |
| Node 版本 | 管理员回填 |
| npm 版本 | 管理员回填 |
| `npm ci` | 管理员回填 |
| `npm run verify` | 管理员回填 |
| `npm audit --audit-level=high` | 管理员回填 |
| frontend-contract-engine scenarios | 管理员回填 |
| style-profit scenarios | 管理员回填 |
| factory-statement scenarios | 管理员回填 |
| sales-inventory scenarios | 管理员回填 |
| quality scenarios | 管理员回填 |
| 敏感信息扫描 | 管理员回填 |

### 5.2 Backend Test Hard Gate

| 字段 | 管理员回填 |
| --- | --- |
| Required Check 名称 | `Backend Test Hard Gate / lingyi-service-test` |
| Workflow | `Backend Test Hard Gate` |
| Job | `lingyi-service-test` |
| Run URL | 管理员回填 |
| Run conclusion | 管理员回填 |
| Commit SHA | 管理员回填 |
| Runner | GitHub Actions hosted runner / 管理员回填 |
| Runner OS | 管理员回填 |
| 执行开始时间 | 管理员回填 |
| 执行结束时间 | 管理员回填 |
| 执行总耗时 | 管理员回填 |
| Artifact | `backend-test-report-<sha>` / 管理员回填 |
| Python 版本 | 管理员回填 |
| pytest 结果 | 管理员回填 |
| unittest 结果 | 管理员回填 |
| py_compile 结果 | 管理员回填 |
| JUnit tests | 管理员回填 |
| JUnit skipped | 管理员回填 |
| JUnit failures | 管理员回填 |
| JUnit errors | 管理员回填 |
| 敏感信息扫描 | 管理员回填 |

### 5.3 Backend PostgreSQL Hard Gate

| 字段 | 管理员回填 |
| --- | --- |
| Required Check 名称 | `Backend PostgreSQL Hard Gate / postgresql-non-skip-gate` |
| Workflow | `Backend PostgreSQL Hard Gate` |
| Job | `postgresql-non-skip-gate` |
| Run URL | 管理员回填 |
| Run conclusion | 管理员回填 |
| Commit SHA | 管理员回填 |
| Runner | GitHub Actions hosted runner / 管理员回填 |
| Runner OS | 管理员回填 |
| 执行开始时间 | 管理员回填 |
| 执行结束时间 | 管理员回填 |
| 执行总耗时 | 管理员回填 |
| Artifact | `postgresql-non-skip-report-<sha>` / 管理员回填 |
| Settlement JUnit artifact | `postgresql-settlement-junit` / 管理员回填 |
| Style-profit JUnit artifact | `postgresql-style-profit-junit` / 管理员回填 |
| PostgreSQL 版本 | 管理员回填 |
| PostgreSQL test database（仅库名） | `lingyi_test_ci` / 管理员回填 |
| Secret 是否使用 `LINGYI_CI_POSTGRES_PASSWORD` | 管理员回填 |
| 敏感信息扫描 | 管理员回填 |

PostgreSQL JUnit 必填：

| JUnit 文件 | tests | skipped | failures | errors | 结论 |
| --- | --- | --- | --- | --- | --- |
| `.pytest-postgresql-subcontract-settlement.xml` | 管理员回填 | `0` / 管理员回填 | `0` / 管理员回填 | `0` / 管理员回填 | 管理员回填 |
| `.pytest-postgresql-style-profit-subcontract.xml` | 管理员回填 | `0` / 管理员回填 | `0` / 管理员回填 | `0` / 管理员回填 | 管理员回填 |

强制要求：

1. `skipped` 必须为 `0`。
2. `failures` 必须为 `0`。
3. `errors` 必须为 `0`。
4. 任一 JUnit 未生成、全部 skip、或指标不可读，均不得标记通过。

### 5.4 Docs Boundary Gate

| 字段 | 管理员回填 |
| --- | --- |
| Required Check 名称 | `Docs Boundary Gate / docs-boundary-check` |
| Workflow | `Docs Boundary Gate` |
| Job | `docs-boundary-check` |
| Run URL | 管理员回填 |
| Run conclusion | 管理员回填 |
| Commit SHA | 管理员回填 |
| Runner | GitHub Actions hosted runner / 管理员回填 |
| Runner OS | 管理员回填 |
| 执行开始时间 | 管理员回填 |
| 执行结束时间 | 管理员回填 |
| 执行总耗时 | 管理员回填 |
| Artifact | `docs-boundary-report-<sha>` / 管理员回填 |
| docs-only 禁入路径检查 | 管理员回填 |
| 运行产物阻断检查 | 管理员回填 |
| 敏感信息扫描 | 管理员回填 |

## 6. Required Check / Branch Protection 配置证据

管理员必须将以下四个 check 配置为主干 required checks。

| Required Check 精确名称 | 目标分支 | 配置方式 | Ruleset / Branch protection 名称 | 配置状态 | 配置人 | 配置时间 |
| --- | --- | --- | --- | --- | --- | --- |
| `Frontend Verify Hard Gate / lingyi-pc-verify` | `main` / 管理员回填 | Branch protection / Ruleset | 管理员回填 | 管理员回填 | 管理员回填 | 管理员回填 |
| `Backend Test Hard Gate / lingyi-service-test` | `main` / 管理员回填 | Branch protection / Ruleset | 管理员回填 | 管理员回填 | 管理员回填 | 管理员回填 |
| `Backend PostgreSQL Hard Gate / postgresql-non-skip-gate` | `main` / 管理员回填 | Branch protection / Ruleset | 管理员回填 | 管理员回填 | 管理员回填 | 管理员回填 |
| `Docs Boundary Gate / docs-boundary-check` | `main` / 管理员回填 | Branch protection / Ruleset | 管理员回填 | 管理员回填 | 管理员回填 | 管理员回填 |

核验要求：

1. Required Check 名称必须使用 GitHub 实际显示名称。
2. 如果 GitHub 实际显示名称与冻结名称不一致，必须停止并下发 REL-004 修正任务，不得自行替换。
3. 不能只记录截图，必须记录文字字段。
4. branch protection / ruleset 配置完成前，不得宣称 required checks 已闭环。

## 7. 敏感信息扫描证据

| 扫描对象 | 结果 | 扫描人 | 扫描时间 | 说明 |
| --- | --- | --- | --- | --- |
| Workflow logs | 管理员回填 | 管理员回填 | 管理员回填 | 不得包含完整 DSN、密码、token、cookie、authorization |
| Artifacts | 管理员回填 | 管理员回填 | 管理员回填 | 不得包含完整 DSN、密码、token、cookie、authorization |
| 本证据文档 | 管理员回填 | 管理员回填 | 管理员回填 | 不得包含完整 DSN、密码、token、cookie、authorization |

## 8. 最终闭环判定清单

全部为“是”才允许进入 REL-004E 平台闭环审计。

| 检查项 | 是 / 否 | 证据 |
| --- | --- | --- |
| GitHub Secret `LINGYI_CI_POSTGRES_PASSWORD` 已配置且未泄露值 | 管理员回填 | 管理员回填 |
| remote URL 无凭据 | 管理员回填 | 管理员回填 |
| 远端 `main` HEAD 等于本地基线 commit 或经审计批准的新 commit | 管理员回填 | 管理员回填 |
| 四个 Hosted Runner workflow 均成功 | 管理员回填 | 管理员回填 |
| 四个 Run URL 均可打开并指向同一目标 commit | 管理员回填 | 管理员回填 |
| PostgreSQL 两份 JUnit 均 `skipped=0/failures=0/errors=0` | 管理员回填 | 管理员回填 |
| 四个 required checks 均已配置到主干保护 | 管理员回填 | 管理员回填 |
| workflow log / artifact / 证据文档均未泄露敏感信息 | 管理员回填 | 管理员回填 |
| 未执行 force push | 管理员回填 | 管理员回填 |
| 未宣称生产发布 | 管理员回填 | 管理员回填 |

## 9. 失败处理分支

1. GitHub Secret 缺失：停止，配置 Secret 后重跑 PostgreSQL gate。
2. Remote URL 含凭据：停止，移除 remote，重新使用无凭据 URL。
3. 远端 `main` 不可 fast-forward：停止，下发远端历史对齐任务。
4. 任一 Hosted Runner 失败：停止，保留 Run URL 和失败摘要，下发对应修复任务。
5. PostgreSQL JUnit 缺失或 `skipped>0`：停止，不得标记 non-skip gate 通过。
6. 敏感信息扫描失败：停止，先清除泄露源并轮换已泄露凭据。
7. Required Check 名称不一致：停止，回到 REL-004 workflow / check 名称修正任务。
8. Branch protection / Ruleset 无权限：回报权限阻塞，不得写“已配置”。

## 10. 管理员回报格式

```text
REL-004D 平台管理员待办证据回填完成。

GitHub Secret：
- LINGYI_CI_POSTGRES_PASSWORD：已配置 / 未配置
- 是否记录 Secret 值：否

Remote / Push：
- remote URL：<无凭据 URL 或仓库 slug>
- 推送分支：main / <实际分支>
- 远端 HEAD：<sha>
- 是否 force push：否

Hosted Runner：
- Frontend Verify Hard Gate / lingyi-pc-verify：<run URL>，结论 <success/failure>
- Backend Test Hard Gate / lingyi-service-test：<run URL>，结论 <success/failure>
- Backend PostgreSQL Hard Gate / postgresql-non-skip-gate：<run URL>，结论 <success/failure>
- Docs Boundary Gate / docs-boundary-check：<run URL>，结论 <success/failure>

PostgreSQL JUnit：
- settlement：tests=<n>, skipped=0, failures=0, errors=0
- style-profit：tests=<n>, skipped=0, failures=0, errors=0

Required Checks：
- 目标分支：main / <实际分支>
- 配置方式：Branch protection / Ruleset
- 四个 required checks：已配置 / 未配置
- 配置人：<账号>
- 配置时间：YYYY-MM-DD HH:MM CST

安全检查：
- workflow logs：未发现完整 DSN、密码、token、cookie、authorization
- artifacts：未发现完整 DSN、密码、token、cookie、authorization
- evidence docs：未发现完整 DSN、密码、token、cookie、authorization

结论：建议 / 不建议进入 REL-004E 平台闭环审计。
生产发布：未完成。
```

## 11. 禁止事项

1. 禁止将本模板未回填状态称为完成。
2. 禁止将本地测试通过称为 Hosted Runner 通过。
3. 禁止将 workflow 存在称为 required check 已配置。
4. 禁止使用非 GitHub 实际显示名称作为 required check 证据。
5. 禁止泄露完整 DSN、密码、token、cookie、authorization。
6. 禁止 force push。
7. 禁止以截图替代文字化审计字段。
8. 禁止宣称生产发布完成。
