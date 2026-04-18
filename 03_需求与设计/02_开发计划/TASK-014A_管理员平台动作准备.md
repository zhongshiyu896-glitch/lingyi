# TASK-014A 管理员平台动作准备

- 任务编号：TASK-014A
- 任务名称：管理员平台动作准备
- 角色：架构师
- 优先级：P0
- 更新时间：2026-04-17
- 前置依赖：B-1 ~ B-6 补审已全部通过
- 当前基线 HEAD：`384970400f7a137e8384649bd73cab5ae2d33300`
- 任务结论定位：管理员平台动作清单与 evidence 模板，不代表平台闭环完成

## 1. 当前调度口径

### 1.1 平台阻塞处置

- `TASK-014B3` 已将平台证据缺失升级为管理员外部阻塞。
- 该阻塞不升级为 Sprint 3 整体阻塞。
- `TASK-014B / TASK-014B2` 不再重复执行。
- 管理员最小平台证据包到位后，从 `TASK-014B` 继续。
- `TASK-014C` 及之后的发布链路继续冻结等待。

### 1.2 本任务边界

本任务只输出管理员动作清单与 evidence 模板，不要求真实 Run URL，不要求真实 artifact，不要求真实 Branch Protection 配置截图。

本任务不构成以下结论：

- GitHub Hosted Runner 已闭环。
- Branch Protection required checks 已闭环。
- `TASK-014C` 可进入。
- 生产发布可执行。

### 1.3 补审闭环声明（TASK-014A-REFRESH）

- B-1~B-6：已全部审计通过。
- TASK-014C：仍冻结。
- 管理员真实平台证据包未到位前，不得进入 TASK-014C。
- 不得声明 required checks 闭环。
- 不得声明生产发布完成。

## 2. GitHub Secrets 配置清单

### 2.1 必需 Secret

| Secret 名称 | 用途 | 配置责任人 | 是否允许写入仓库 |
|---|---|---|---|
| `LINGYI_CI_POSTGRES_PASSWORD` | PostgreSQL CI gate 测试数据库密码 | 管理员 | 否 |

### 2.2 PostgreSQL CI 运行参数

| 项目 | 要求 |
|---|---|
| 数据库 | CI 专用 PostgreSQL 测试数据库 |
| 用户 | CI 专用最小权限用户 |
| 密码 | 仅通过 GitHub Secret 注入 |
| DSN | 仅在 workflow runtime 中组装，禁止写入仓库 |
| 适用 gate | `Backend PostgreSQL Hard Gate / postgresql-non-skip-gate` |

### 2.3 Secret 安全边界

- 严禁在仓库文件中写入真实 Secret 值。
- 严禁在文档、workflow、脚本、artifact 中落地明文密码或 DSN。
- 严禁将 GitHub token、ERPNext key、Cookie、Authorization header 写入 evidence 文档。
- 如 workflow log 或 artifact 出现敏感值，平台证据不得通过审计。

## 3. Hosted Runner 初始化步骤

管理员需要按以下顺序完成平台动作：

1. 确认 GitHub 目标仓库已存在。
2. 确认 GitHub Actions 已启用。
3. 确认当前本地基线已按管理员流程推送到目标仓库。
4. 确认以下 workflow 文件在平台默认分支可见：
   - `.github/workflows/frontend-verify.yml`
   - `.github/workflows/backend-test.yml`
   - `.github/workflows/backend-postgresql.yml`
   - `.github/workflows/docs-boundary.yml`
5. 配置 `LINGYI_CI_POSTGRES_PASSWORD`。
6. 触发四个 Hosted Runner gate。
7. 下载或归档四个 gate 的 artifact。
8. 回填 Run URL、artifact、JUnit 指标与敏感信息扫描结论。

## 4. Required Check 精确名称

管理员在 Branch Protection / Ruleset 中只能使用以下精确名称：

| 序号 | Required Check 精确名称 |
|---|---|
| 1 | `Frontend Verify Hard Gate / lingyi-pc-verify` |
| 2 | `Backend Test Hard Gate / lingyi-service-test` |
| 3 | `Backend PostgreSQL Hard Gate / postgresql-non-skip-gate` |
| 4 | `Docs Boundary Gate / docs-boundary-check` |

## 5. Branch Protection 配置清单

### 5.1 保护分支

| 分支 | 要求 |
|---|---|
| `main` | 必须保护 |
| `develop` | 如启用 develop 流程则必须保护 |

### 5.2 必须开启

- Require status checks to pass before merging。
- Require branches to be up to date before merging。
- Require the four required checks listed in section 4。
- Block force pushes。
- Block deletions。

### 5.3 禁止开启或绕过

- 禁止配置 bypass 绕过 required checks。
- 禁止允许管理员静默绕过 required checks，除非另有总调度书面豁免。
- 禁止把未运行或 missing 的 check 标记为通过。

## 6. Evidence 回填模板

### 6.1 Frontend Verify Hard Gate / lingyi-pc-verify

| 字段 | 回填值 |
|---|---|
| Run URL |  |
| Commit SHA |  |
| Branch |  |
| Runner OS |  |
| 执行开始时间 |  |
| 执行结束时间 |  |
| 执行总耗时 |  |
| Conclusion |  |
| Artifact 名称 |  |
| Artifact URL 或归档路径 |  |
| 关键日志摘要 |  |
| 敏感信息扫描结论 |  |

### 6.2 Backend Test Hard Gate / lingyi-service-test

| 字段 | 回填值 |
|---|---|
| Run URL |  |
| Commit SHA |  |
| Branch |  |
| Runner OS |  |
| 执行开始时间 |  |
| 执行结束时间 |  |
| 执行总耗时 |  |
| Conclusion |  |
| Artifact 名称 |  |
| Artifact URL 或归档路径 |  |
| 关键日志摘要 |  |
| 敏感信息扫描结论 |  |

### 6.3 Backend PostgreSQL Hard Gate / postgresql-non-skip-gate

| 字段 | 回填值 |
|---|---|
| Run URL |  |
| Commit SHA |  |
| Branch |  |
| Runner OS |  |
| 执行开始时间 |  |
| 执行结束时间 |  |
| 执行总耗时 |  |
| Conclusion |  |
| Artifact 名称 |  |
| Artifact URL 或归档路径 |  |
| JUnit tests |  |
| JUnit skipped |  |
| JUnit failures |  |
| JUnit errors |  |
| 关键日志摘要 |  |
| 敏感信息扫描结论 |  |

PostgreSQL gate 通过条件：

```text
tests > 0
skipped = 0
failures = 0
errors = 0
```

### 6.4 Docs Boundary Gate / docs-boundary-check

| 字段 | 回填值 |
|---|---|
| Run URL |  |
| Commit SHA |  |
| Branch |  |
| Runner OS |  |
| 执行开始时间 |  |
| 执行结束时间 |  |
| 执行总耗时 |  |
| Conclusion |  |
| Artifact 名称 |  |
| Artifact URL 或归档路径 |  |
| 关键日志摘要 |  |
| 敏感信息扫描结论 |  |

## 7. 管理员最小平台证据包

管理员必须一次性回传以下材料，否则不重启 `TASK-014B`：

1. GitHub 仓库 URL。
2. 当前分支名。
3. 当前 commit SHA。
4. 四个 workflow Run URL。
5. 四个 gate 的 conclusion。
6. 四个 gate 的 artifact 链接或下载归档路径。
7. PostgreSQL JUnit 指标：`tests / skipped / failures / errors`。
8. CI metadata artifact。
9. workflow log / artifact / JUnit / evidence 的敏感信息扫描结论。
10. Branch Protection required checks 配置截图或 API 响应。

## 8. 管理员回报格式

```text
TASK-014A 平台动作准备完成。
GitHub Secret：已配置 / 未配置
Hosted Runner：已触发 / 未触发
Branch Protection：已配置 / 未配置
Required checks：
- Frontend Verify Hard Gate / lingyi-pc-verify：[状态]
- Backend Test Hard Gate / lingyi-service-test：[状态]
- Backend PostgreSQL Hard Gate / postgresql-non-skip-gate：[状态]
- Docs Boundary Gate / docs-boundary-check：[状态]
PostgreSQL JUnit：tests=... skipped=... failures=... errors=...
敏感信息扫描：通过 / 不通过 / 未提供
结论：提交审计 / 需整改
```

## 9. 当前冻结状态

| 项目 | 状态 |
|---|---|
| Hosted Runner | 未闭环 |
| Branch Protection required checks | 未闭环 |
| `TASK-014C` | 冻结 |
| `TASK-014B / TASK-014B2` | 不再重复执行，等待管理员最小平台证据包 |
| 生产发布 | 禁止 |
| push / remote / PR | 本任务不执行 |

## 10. 审计结论建议口径

若本文件通过审计，结论应为：

```text
TASK-014A 审计通过。
管理员平台动作清单与 evidence 模板已冻结。
本结论不代表 Hosted Runner 闭环。
本结论不代表 Branch Protection required checks 闭环。
TASK-014C 仍冻结，等待管理员最小平台证据包到位后从 TASK-014B 继续。
```

## 11. 禁止事项

- 禁止写业务代码。
- 禁止修改前端、后端、`.github`、`02_源码`。
- 禁止 push。
- 禁止配置 remote。
- 禁止创建 PR。
- 禁止伪造 Run URL。
- 禁止伪造 artifact。
- 禁止声明 required checks 已闭环。
- 禁止声明生产发布完成。

## 12. 验收标准

- [x] Secrets 配置清单完成。
- [x] Hosted Runner 初始化步骤完成。
- [x] Branch Protection 配置清单完成。
- [x] Evidence 回填模板完成。
- [x] 管理员最小平台证据包清单完成。
- [x] 明确 `TASK-014C` 继续冻结。
- [x] 明确不需要真实 URL。
- [x] 明确不代表平台闭环。
