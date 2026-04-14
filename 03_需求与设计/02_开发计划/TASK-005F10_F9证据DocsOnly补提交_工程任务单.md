# TASK-005F10 F9 证据 Docs-Only 补提交工程任务单

- 任务编号：TASK-005F10
- 模块：款式利润报表 / PostgreSQL CI 门禁 / 本地基线证据
- 版本：V1.0
- 更新时间：2026-04-14 16:40 CST
- 作者：技术架构师
- 优先级：P0
- 前置依赖：TASK-005F9 审计通过，审计意见书第 112 份
- 执行角色：后端工程师
- 审计要求：完成后必须提交审计官复审；复审通过前不得进入 TASK-005G、前端创建入口或 TASK-006

## 1. 任务目标

将 TASK-005F9 的本地基线提交证据文件纳入本地仓库，形成 docs-only 补提交。

本任务只允许提交文档，不允许修改代码、测试、迁移、脚本、workflow 或运行时产物。

必须纳入的核心文件：

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005F9_本地基线提交证据.md`

## 2. 当前风险背景

审计意见书第 112 份确认：

1. `TASK-005F9` 本地基线 commit `81c3cfa25acc77b0a57ae00a282fecb8dca81550` 已通过。
2. `.pytest-postgresql-*.xml` 未混入 commit。
3. `06_前端/**`、`02_源码/**`、`TASK-006*` 未被提交。
4. settlement/style-profit 两份真实 PostgreSQL JUnit 均为 `tests=4, skipped=0, failures=0, errors=0`。
5. 唯一需优先关注的风险：`TASK-005F9_本地基线提交证据.md` 仍未跟踪，需要 docs-only 补提交。

## 3. 本任务边界

### 3.1 允许修改 / 新增

只允许以下文档路径：

- `03_需求与设计/02_开发计划/TASK-005F9_本地基线提交证据.md`
- `03_需求与设计/02_开发计划/TASK-005F10_F9证据DocsOnly补提交_工程任务单.md`
- `03_需求与设计/02_开发计划/当前 sprint 任务清单.md`
- `03_需求与设计/01_架构设计/03_技术决策记录.md`
- `03_需求与设计/01_架构设计/06_模块设计_款式利润报表.md`
- `03_需求与设计/01_架构设计/架构师会话日志.md`
- `03_需求与设计/05_审计记录.md`
- `03_需求与设计/05_审计记录/审计官会话日志.md`

### 3.2 禁止修改 / 禁止提交

禁止提交以下任一路径：

- `.github/**`
- `06_前端/**`
- `07_后端/**`
- `02_源码/**`
- `00_交接与日志/**`
- `01_需求与资料/**`
- `03_环境与部署/**`
- `04_测试与验收/**`
- `05_交付物/**`
- `.pytest-postgresql-*.xml`
- `TASK-006*`

禁止执行：

- `git add .`
- `git add -A`
- `git commit --amend`
- force push
- 任何业务代码修改

## 4. 提交前 staged 状态清理要求

执行前必须先查看：

```bash
cd /Users/hh/Desktop/领意服装管理系统

git status --short
```

如果当前存在已 staged 的非白名单文件，尤其是以下路径，必须先停止并处理 staging：

- `00_交接与日志/**`
- `01_需求与资料/**`
- `02_源码/**`
- `03_环境与部署/**`
- `04_测试与验收/**`
- `05_交付物/**`
- `06_前端/**`
- `07_后端/**`
- `.pytest-postgresql-*.xml`
- `TASK-006*`

允许使用非破坏性取消 staging：

```bash
git restore --staged <非白名单路径>
```

注意：只能取消 staging，不得删除文件，不得 `git reset --hard`，不得 `git checkout --`。

## 5. 推荐 staging 命令

只允许执行显式白名单 add：

```bash
cd /Users/hh/Desktop/领意服装管理系统

git add -- \
  '03_需求与设计/02_开发计划/TASK-005F9_本地基线提交证据.md' \
  '03_需求与设计/02_开发计划/TASK-005F10_F9证据DocsOnly补提交_工程任务单.md' \
  '03_需求与设计/02_开发计划/当前 sprint 任务清单.md' \
  '03_需求与设计/01_架构设计/03_技术决策记录.md' \
  '03_需求与设计/01_架构设计/06_模块设计_款式利润报表.md' \
  '03_需求与设计/01_架构设计/架构师会话日志.md' \
  '03_需求与设计/05_审计记录.md' \
  '03_需求与设计/05_审计记录/审计官会话日志.md'
```

## 6. staged 文件复核

staging 后必须执行：

```bash
git diff --cached --name-only
```

输出只能包含第 5 章白名单文件。

如果出现非白名单文件，必须停止并取消 staging。

## 7. 提交前验证

本任务是 docs-only，不要求重跑全量后端测试，但必须执行以下轻量验证：

```bash
git diff --cached --name-only | rg -n '^(\.github/|06_前端/|07_后端/|02_源码/|00_交接与日志/|01_需求与资料/|03_环境与部署/|04_测试与验收/|05_交付物/|.*\.pytest-postgresql-.*\.xml|.*TASK-006)' && exit 1 || true

git diff --cached --name-only
```

必须确认：

1. 没有 `.github/**`。
2. 没有 `07_后端/**`。
3. 没有 `.pytest-postgresql-*.xml`。
4. 没有前端、源码、历史资料目录。
5. 没有 TASK-006。

## 8. 提交命令

验证通过后执行：

```bash
git commit -m "docs: add task 005f9 baseline evidence"
```

禁止 amend，禁止 push。

## 9. 提交后验证

提交后执行：

```bash
git show --stat --oneline --name-only HEAD

git status --short
```

要求：

1. HEAD 只包含第 5 章白名单文件。
2. `TASK-005F9_本地基线提交证据.md` 已进入 HEAD。
3. 不包含 `.pytest-postgresql-*.xml`。
4. 不包含 `07_后端/**`。
5. 不包含 `06_前端/**`。
6. 不包含 `02_源码/**`。
7. 不包含 `TASK-006*`。

## 10. 验收标准

□ `TASK-005F9_本地基线提交证据.md` 已纳入本地 commit。  
□ 本次 commit 为 docs-only。  
□ 未使用 `git add .` 或 `git add -A`。  
□ 未提交 `.pytest-postgresql-*.xml`。  
□ 未提交 `.github/**`。  
□ 未提交 `07_后端/**`。  
□ 未提交 `06_前端/**`。  
□ 未提交 `02_源码/**`。  
□ 未提交历史未跟踪大目录。  
□ 未提交 TASK-006。  
□ 提交后 HEAD 和文件清单已记录。  
□ 审计官复审通过前不得进入 TASK-005G、前端创建入口或 TASK-006。  

## 11. 交付说明要求

工程师交付时必须说明：

1. commit hash。
2. commit message。
3. `git show --stat --name-only HEAD` 摘要。
4. `git diff --cached --name-only` 提交前复核结果。
5. 是否存在剩余未跟踪目录。
6. `.pytest-postgresql-*.xml` 是否未提交。
7. 是否未修改后端、前端、workflow 和 TASK-006。
8. 明确未进入 TASK-005G、前端创建入口或 TASK-006。
