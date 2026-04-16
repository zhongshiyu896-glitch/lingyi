# REL-004 平台 CI 与 Required Check 闭环方案

- 文档版本：V1.0
- 输出时间：2026-04-16
- 适用范围：Sprint 3 平台门禁闭环（本地仓库 -> GitHub Hosted Runner -> Required Check）
- 当前基线 HEAD：`04aa45842a589ca695739a90802e51e686f35ec0`
- 结论口径：本方案用于设计冻结与任务下发前置，不等同生产发布通过。

## 1. 当前状态

1. 当前 HEAD：`04aa45842a589ca695739a90802e51e686f35ec0`。
2. 当前未 push。
3. 当前未配置 remote。
4. 当前未创建 PR。
5. GitHub required check 未闭环。
6. ERPNext 生产联调未完成。
7. 生产发布未完成。

## 2. Required Check 名称冻结

以下名称冻结为 Sprint 3 平台门禁基线，后续变更必须单独审计：

1. `Frontend Verify Hard Gate / lingyi-pc-verify`
2. `Backend Test Hard Gate / lingyi-service-test`
3. `Backend PostgreSQL Hard Gate / postgresql-non-skip-gate`
4. `Docs Boundary Gate / docs-boundary-check`

## 3. CI 检查矩阵

### 3.1 前端检查矩阵

`lingyi-pc-verify` 必须覆盖并串行失败即中止：

1. `npm ci`
2. `npm run verify`
3. `npm audit --audit-level=high`
4. `npm run test:frontend-contract-engine`
5. `npm run test:style-profit-contracts`
6. `npm run test:factory-statement-contracts`
7. `npm run test:sales-inventory-contracts`
8. `npm run test:quality-contracts`

前端门禁补充要求：

1. `npm run verify` 必须继续包含 typecheck 与 build。
2. 合同场景数阈值应保持不回退（style-profit、factory-statement、sales-inventory、quality、frontend-contract-engine）。

### 3.2 后端检查矩阵

`lingyi-service-test` 必须覆盖并串行失败即中止：

1. `pytest -q`
2. `python -m unittest discover`
3. `python -m py_compile $(find app tests -name '*.py' -print)`

后端补充要求：

1. 保留关键模块回归（permissions、audit、erpnext fail-closed、sales inventory、quality、factory statement）。
2. 所有失败统一错误信封与审计路径在测试中保持可回归验证。

### 3.3 PostgreSQL non-skip Gate

`postgresql-non-skip-gate` 必须包含：

1. subcontract / factory-statement PostgreSQL gate。
2. style-profit PostgreSQL gate。
3. 后续新增 PostgreSQL gate 任务也必须纳入统一 gate。

强制口径：

1. 所有 PostgreSQL JUnit 指标必须满足 `skipped=0`。
2. 若因环境原因未执行，不得标记通过，必须显式失败或阻断并进入修复任务。

## 4. Artifact / JUnit 证据规范

## 4.1 Artifact 命名规范

建议固定命名：

1. `frontend-verify-report-<sha>.zip`
2. `backend-test-report-<sha>.zip`
3. `postgresql-non-skip-report-<sha>.zip`
4. `docs-boundary-report-<sha>.zip`

其中 `<sha>` 为提交 SHA 前 8~12 位。

## 4.2 JUnit 指标规范

每个 gate 必须回填并可审计：

1. `tests`
2. `skipped`
3. `failures`
4. `errors`

强制判断：

1. PostgreSQL gate 必须 `skipped=0`。
2. 任一 gate 的 `failures>0` 或 `errors>0` 直接阻断。

## 4.3 元数据回填规范

每个 gate 证据必须包含：

1. run URL
2. commit SHA
3. runner OS
4. Node 版本
5. Python 版本
6. PostgreSQL 版本（如适用）
7. 执行开始/结束时间与总耗时
8. 敏感信息扫描结果

## 4.4 敏感信息与脱敏规范

证据中禁止出现：

1. DSN 原文
2. 密码明文
3. 访问密钥
4. cookie 原文
5. authorization header 原文

## 5. GitHub 平台动作边界

1. 仅管理员可配置 remote。
2. 仅管理员可 push。
3. 仅管理员可配置 required checks。
4. 禁止 force push。
5. push 前必须检查远端 `main` 分支状态。
6. 远端 `main` 若存在不兼容历史，必须停止并单独下发清理/对齐任务，不得强推覆盖。
7. 禁止将本地通过冒充 hosted runner 通过。
8. 文档、脚本、日志中禁止写入任何凭据。

## 6. 本地与平台口径区分

1. 本地封版不等同生产发布。
2. 本地 pytest 通过不等同 hosted runner 通过。
3. 本地 JUnit 文件不等同 required check 已闭环。
4. 未配置 remote 前不得宣称平台闭环。

## 7. REL-004B 实现边界

### 7.1 允许范围

1. 新增或修正 `.github/workflows/**`。
2. 新增 CI 辅助脚本。
3. 新增 `docs-boundary-check`。
4. 新增证据模板与产物回填脚本。

### 7.2 禁止范围

1. 修改业务代码。
2. 修改前端业务页面。
3. 修改后端业务逻辑。
4. 修改数据库迁移。
5. 执行 push。
6. 配置 remote。
7. 创建 PR。
8. 宣称生产发布完成。
9. 写入凭据。

## 8. 审计前置要求（REL-004B）

1. Required check 名称与 workflow job 名称一一对应且固定。
2. PostgreSQL non-skip gate 必须附带 `skipped=0` 硬断言。
3. artifact 必须包含元数据与敏感信息扫描结果。
4. docs boundary gate 必须阻断越界提交（前端/后端/.github/02_源码边界按任务单定义）。
5. 管理员动作必须有操作记录，不得口头放行。

## 9. 验收标准（REL-004A 设计冻结）

1. Required check 名称已冻结。
2. CI 检查矩阵（前端/后端/PostgreSQL）已冻结。
3. artifact/JUnit 证据规范已冻结。
4. 管理员平台动作边界已冻结。
5. 本地与平台口径区分已冻结。
6. REL-004B 实现边界已冻结。
