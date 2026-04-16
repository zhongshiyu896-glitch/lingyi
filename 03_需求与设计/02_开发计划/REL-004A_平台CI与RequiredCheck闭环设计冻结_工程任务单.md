# REL-004A 平台 CI / Required Check 闭环设计冻结 工程任务单

- 任务编号：REL-004A
- 优先级：P1
- 角色：工程师
- 前置依赖：TASK-S2-RETRO-COMMIT 审计通过
- 当前基线 HEAD：`04aa45842a589ca695739a90802e51e686f35ec0`

## 1. 任务目标

冻结 Sprint 3 平台 CI / Required Check 闭环方案，统一 GitHub Actions、required checks、前端 verify、后端测试、PostgreSQL non-skip gate、证据回填和管理员动作边界。

## 2. 执行边界

1. 本任务仅输出文档。
2. 不写代码。
3. 不修改 workflow。
4. 不配置 remote。
5. 不 push。
6. 不创建 PR。

## 3. 输出文件

新建：

1. `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/REL-004_平台CI与RequiredCheck闭环方案.md`
2. `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/REL-004A_平台CI与RequiredCheck闭环设计冻结_工程任务单.md`

## 4. 必含内容清单

## 4.1 当前状态口径

文档必须明确：

1. 当前 HEAD 为 `04aa45842a589ca695739a90802e51e686f35ec0`。
2. 未 push。
3. 未配置 remote。
4. 未创建 PR。
5. GitHub required check 未闭环。
6. ERPNext 生产联调未完成。
7. 生产发布未完成。

## 4.2 Required Check 名称冻结

必须逐字包含以下名称：

1. `Frontend Verify Hard Gate / lingyi-pc-verify`
2. `Backend Test Hard Gate / lingyi-service-test`
3. `Backend PostgreSQL Hard Gate / postgresql-non-skip-gate`
4. `Docs Boundary Gate / docs-boundary-check`

## 4.3 CI 检查矩阵冻结

前端必须覆盖：

1. `npm ci`
2. `npm run verify`
3. `npm audit --audit-level=high`
4. `test:frontend-contract-engine`
5. `test:style-profit-contracts`
6. `test:factory-statement-contracts`
7. `test:sales-inventory-contracts`
8. `test:quality-contracts`

后端必须覆盖：

1. `pytest -q`
2. `unittest discover`
3. `py_compile`

PostgreSQL gate 必须覆盖：

1. subcontract / factory-statement PostgreSQL gate
2. style-profit PostgreSQL gate
3. 所有 PostgreSQL JUnit 指标必须 `skipped=0`

## 4.4 Artifact / JUnit 证据规范冻结

必须定义：

1. artifact 文件命名规范
2. `tests / skipped / failures / errors` 四项指标
3. run URL
4. commit SHA
5. runner OS
6. Node / Python / PostgreSQL 版本
7. 执行时间
8. 敏感信息扫描结果
9. 禁止记录 DSN、密码、token、cookie、authorization

## 4.5 平台动作边界冻结

必须明确：

1. 仅管理员可配置 remote。
2. 仅管理员可 push。
3. 仅管理员可配置 required checks。
4. 禁止 force push。
5. push 前必须检查远端 main。
6. 远端 main 不兼容历史必须停止。
7. 禁止把本地通过冒充 hosted runner 通过。
8. 禁止在文档写入凭据。

## 4.6 REL-004B 实现边界冻结

允许：

1. 新增 `.github/workflows/**`
2. 新增 CI 辅助脚本
3. 新增 docs boundary check
4. 新增证据模板

禁止：

1. 修改业务代码
2. 修改前端页面
3. 修改后端业务逻辑
4. 修改数据库迁移
5. push
6. remote
7. PR
8. 生产发布
9. 写入凭据

## 5. 禁止修改路径

1. `/Users/hh/Desktop/领意服装管理系统/06_前端/**`
2. `/Users/hh/Desktop/领意服装管理系统/07_后端/**`
3. `/Users/hh/Desktop/领意服装管理系统/.github/**`
4. `/Users/hh/Desktop/领意服装管理系统/02_源码/**`

## 6. 验证命令

```bash
cd /Users/hh/Desktop/领意服装管理系统
test -f "03_需求与设计/01_架构设计/REL-004_平台CI与RequiredCheck闭环方案.md"
test -f "03_需求与设计/02_开发计划/REL-004A_平台CI与RequiredCheck闭环设计冻结_工程任务单.md"
git diff --name-only -- "06_前端" "07_后端" ".github" "02_源码"
git diff --cached --name-only
grep -R "<secret-patterns>" \
  "03_需求与设计/01_架构设计/REL-004_平台CI与RequiredCheck闭环方案.md" \
  "03_需求与设计/02_开发计划/REL-004A_平台CI与RequiredCheck闭环设计冻结_工程任务单.md" || true
```

## 7. 验收标准

1. REL-004 方案文档已输出。
2. REL-004A 任务单已输出。
3. Required Check 名称完整。
4. 前端 CI 检查矩阵完整。
5. 后端 CI 检查矩阵完整。
6. PostgreSQL non-skip 口径明确。
7. Artifact / JUnit 证据规范完整。
8. 管理员平台动作边界明确。
9. REL-004B 实现边界明确。
10. 未修改前端。
11. 未修改后端。
12. 未修改 `.github`。
13. 未修改 `02_源码`。
14. 未暂存、未提交、未 push。
15. 文档不含凭据。

## 8. 交付回报格式

```text
REL-004A 执行完成。
结论：待审计

已输出：
- /03_需求与设计/01_架构设计/REL-004_平台CI与RequiredCheck闭环方案.md
- /03_需求与设计/02_开发计划/REL-004A_平台CI与RequiredCheck闭环设计冻结_工程任务单.md

本次只输出文档。
未修改前端/后端/.github/02_源码。
未暂存、未提交、未 push。
文档不含凭据。
```
