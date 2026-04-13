# TASK-004C11 GitHub 平台最终闭环工程任务单

- 任务编号：TASK-004C11
- 模块：生产计划集成 / GitHub 平台闭环 / 前端 Required Check
- 优先级：P0
- 版本：V1.0
- 更新时间：2026-04-13 21:49 CST
- 作者：技术架构师
- 审计来源：审计意见书第 76 份，TASK-004C10 通过；最优先问题为 GitHub 平台闭环仍未完成，需配置 `origin`、push `main`、触发 `Frontend Verify Hard Gate / lingyi-pc-verify` hosted runner，并将该 check 设为 `main` required check
- 前置依赖：TASK-004C10 已通过，C9 证据与第 75 份审计记录已完成 docs-only commit
- 当前本地基线：git root `/Users/hh/Desktop/领意服装管理系统`，branch `main`，当前提交 `b32585c`，提交信息 `docs: record frontend platform gate blocker`，当前未配置 GitHub remote
- 架构依据：`/03_需求与设计/01_架构设计/05_模块设计_生产计划集成.md` V1.15；`ADR-073`
- 任务边界：只做 C11 文档补提交、GitHub remote、push、hosted runner 实跑、required check 配置和平台证据补齐；不新增业务功能，不修改前后端业务逻辑，不进入 TASK-005/TASK-006

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-004C11
模块：GitHub 平台最终闭环
优先级：P0（前端 CI 合并门禁最终闭环）
════════════════════════════════════════════════════════════════════════════

【任务目标】
完成 GitHub 平台最终闭环：推送当前项目根仓库到 GitHub，确认 hosted runner 上 `Frontend Verify Hard Gate / lingyi-pc-verify` 通过，并将该 check 配置为 main 分支 required check。

【当前可用前置成果】

1. 项目根已成为 git root：`/Users/hh/Desktop/领意服装管理系统`。
2. 当前分支：`main`。
3. 当前提交：`b32585c docs: record frontend platform gate blocker`。
4. 根仓库 tracked 文件已补齐，审计确认 tracked snapshot 前后端验证通过。
5. C9 平台阻塞证据和第 75 份审计记录已进入 docs-only commit。
6. 当前缺口：未配置 GitHub remote，未 push `main`，未 hosted runner 实跑，未 required check 配置。

【必须由管理员提供】

1. GitHub 仓库 URL。
2. 是否使用 SSH remote 或 HTTPS remote。
3. 如 GitHub 远端已有历史，必须提供历史处理策略；默认禁止强推覆盖。
4. GitHub branch protection / ruleset 管理权限。

【允许修改或创建】

允许修改：
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/03_技术决策记录.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/05_模块设计_生产计划集成.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/架构师会话日志.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/当前 sprint 任务清单.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录/审计官会话日志.md

允许新建：
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-004C11_GitHub平台最终闭环_工程任务单.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录/TASK-004C11_GitHub平台最终闭环证据.md

允许执行：
- 配置 GitHub remote。
- push `main`。
- GitHub hosted runner 实跑。
- GitHub branch protection / ruleset required check 配置。
- 平台证据 docs-only commit 和 push。

禁止修改：
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/**
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/**
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/**
- /Users/hh/Desktop/领意服装管理系统/.github/workflows/frontend-verify.yml（除非 hosted runner 明确失败且审计官确认是 workflow 配置问题）
- 任意 TASK-005/TASK-006 文件

【执行步骤】

## 1. 先做 C11 文档准备提交

目的：让第 76 份审计结果、C11 任务单、最新架构设计和 ADR 先进入仓库，再推送到 GitHub。

```bash
cd /Users/hh/Desktop/领意服装管理系统
git rev-parse --show-toplevel
git branch --show-current
git rev-parse --short HEAD
git status --short
git remote -v || true
```

只允许 stage 以下文件：

```bash
cd /Users/hh/Desktop/领意服装管理系统
git add \
  '03_需求与设计/01_架构设计/03_技术决策记录.md' \
  '03_需求与设计/01_架构设计/05_模块设计_生产计划集成.md' \
  '03_需求与设计/01_架构设计/架构师会话日志.md' \
  '03_需求与设计/02_开发计划/当前 sprint 任务清单.md' \
  '03_需求与设计/02_开发计划/TASK-004C11_GitHub平台最终闭环_工程任务单.md' \
  '03_需求与设计/05_审计记录.md' \
  '03_需求与设计/05_审计记录/审计官会话日志.md'
```

阻断误提交检查：

```bash
git diff --cached --name-only | rg '^(00_交接与日志|01_需求与资料|02_源码|03_环境与部署|04_测试与验收|05_交付物|06_前端|07_后端)/' && exit 1 || true
git diff --cached --name-only | rg '(node_modules|dist/|\.venv|__pycache__|\.env|\.db$|\.xml$)' && exit 1 || true
git diff --cached | rg -i 'ghp_|github_pat_|authorization:|cookie:|password=|passwd=|secret=|token=' && exit 1 || true
git diff --cached --name-only
```

提交：

```bash
git commit -m "docs: prepare frontend ci platform closure"
git rev-parse --short HEAD
```

## 2. 配置 GitHub remote

推荐 SSH remote：

```bash
cd /Users/hh/Desktop/领意服装管理系统
git remote add origin git@github.com:<org-or-user>/<repo>.git
git remote -v
git remote -v | rg -i 'token|password|passwd|secret|cookie|ghp_|github_pat_' && exit 1 || true
```

如必须使用 HTTPS remote，禁止在 URL 中写 token：

```bash
git remote add origin https://github.com/<org-or-user>/<repo>.git
git remote -v
git remote -v | rg -i 'token|password|passwd|secret|cookie|ghp_|github_pat_' && exit 1 || true
```

## 3. Push main

```bash
cd /Users/hh/Desktop/领意服装管理系统
git push -u origin main
```

失败处理：
1. 如果远端为空仓库，应直接成功。
2. 如果远端已有历史导致 push 被拒绝，停止，不得强推。
3. 远端已有历史时，提交远端历史冲突说明给架构师和审计官确认。

## 4. Hosted Runner 实跑

在 GitHub 页面确认：

```text
Actions -> Frontend Verify Hard Gate -> lingyi-pc-verify
```

必须记录：

1. Run URL。
2. Branch：main。
3. Commit SHA。
4. Workflow conclusion。
5. Job conclusion。
6. `node -v = v22.22.1` 日志行。
7. `npm -v = 10.9.4` 日志行。
8. `npm ci` 成功日志。
9. `npm run verify` 成功日志。
10. `npm audit --audit-level=high` 成功日志。

## 5. 配置 main required check

在 GitHub branch protection 或 ruleset 中配置 required check：

```text
Frontend Verify Hard Gate / lingyi-pc-verify
```

要求：
1. 作用分支必须是 `main`。
2. required check 名称必须使用 GitHub 实际显示名称。
3. 如果实际显示名称不是 `Frontend Verify Hard Gate / lingyi-pc-verify`，必须记录实际名称并提交架构师确认。
4. 配置完成后保存 branch protection / ruleset 名称。

## 6. 创建平台闭环证据

必须创建：

```text
/Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录/TASK-004C11_GitHub平台最终闭环证据.md
```

模板：

```markdown
# TASK-004C11 GitHub 平台最终闭环证据

- 任务编号：TASK-004C11
- 更新时间：YYYY-MM-DD HH:MM CST
- 执行人：
- 结论：通过/不通过

## 本地提交

- git root：/Users/hh/Desktop/领意服装管理系统
- branch：main
- C10 后基线 commit：b32585c
- C11 文档准备 commit：
- remote 类型：SSH / HTTPS
- remote 脱敏 URL：
- remote 敏感信息扫描：通过/不通过

## Push 结果

- push main：通过/不通过
- GitHub 仓库 URL：
- 远端 main Commit SHA：

## Hosted Runner

- Workflow：Frontend Verify Hard Gate
- Job：lingyi-pc-verify
- Run URL：
- Branch：main
- Commit SHA：
- Workflow conclusion：
- Job conclusion：

| 检查项 | 结果 | 证据 |
| --- | --- | --- |
| node -v = v22.22.1 | 通过/不通过 | 日志行 |
| npm -v = 10.9.4 | 通过/不通过 | 日志行 |
| npm ci | 通过/不通过 | 日志行 |
| npm run verify | 通过/不通过 | 日志行 |
| npm audit --audit-level=high | 通过/不通过 | 日志行 |

## Required Check

- Branch protection / Ruleset 名称：
- 作用分支：main
- Required check 实际名称：
- 是否已配置为 required：是/否

## 敏感信息检查

- remote 无 token/password/secret/cookie：通过/不通过
- Run URL 无 token：通过/不通过
- 日志摘录无 token/password/secret/cookie/私钥：通过/不通过
- 证据文档无 token/password/secret/cookie/私钥：通过/不通过

## 剩余风险

- Backend PostgreSQL Hard Gate / subcontract-postgresql-gate 平台闭环：已完成/未完成
- TASK-005/TASK-006 是否放行：否
```

## 7. 平台证据 docs-only commit

证据创建后，只允许提交证据文件和必要日志：

```bash
cd /Users/hh/Desktop/领意服装管理系统
git add \
  '03_需求与设计/05_审计记录/TASK-004C11_GitHub平台最终闭环证据.md'

git diff --cached --name-only | rg '^(06_前端|07_后端|02_源码|04_测试与验收|05_交付物)/' && exit 1 || true
git diff --cached | rg -i 'ghp_|github_pat_|authorization:|cookie:|password=|passwd=|secret=|token=' && exit 1 || true
git commit -m "docs: record frontend ci platform closure"
git push origin main
```

【验收标准】

□ C11 文档准备 commit 已形成。  
□ `origin` 已配置。  
□ `git remote -v` 无 token/password/secret/cookie。  
□ `main` 已 push 到 GitHub。  
□ GitHub Actions 页面可见 `Frontend Verify Hard Gate`。  
□ Hosted runner `Frontend Verify Hard Gate / lingyi-pc-verify` 通过。  
□ hosted runner 日志确认 `node -v = v22.22.1`。  
□ hosted runner 日志确认 `npm -v = 10.9.4`。  
□ hosted runner 日志确认 `npm ci` 成功。  
□ hosted runner 日志确认 `npm run verify` 成功。  
□ hosted runner 日志确认 `npm audit --audit-level=high` 成功。  
□ main required check 已配置为 `Frontend Verify Hard Gate / lingyi-pc-verify` 或已记录 GitHub 实际显示名称并获架构师确认。  
□ 平台证据文件已创建。  
□ 平台证据 docs-only commit 已形成并 push。  
□ 未修改前端业务代码。  
□ 未修改后端业务代码。  
□ 未进入 TASK-005/TASK-006。  

【禁止事项】

- 禁止在 remote URL 中写 token。
- 禁止 `git push --force`。
- 禁止覆盖远端历史。
- 禁止跳过 hosted runner。
- 禁止用本地验证替代 hosted runner。
- 禁止弱化 `.github/workflows/frontend-verify.yml`。
- 禁止弱化 `npm run verify`。
- 禁止修改前端业务代码。
- 禁止修改后端业务代码。
- 禁止进入 TASK-005/TASK-006。

【交付回报格式】

完成后按以下格式回复：

```text
TASK-004C11 已完成。

Docs 准备提交：
- commit SHA：...

Remote 与 Push：
- origin 已配置：是/否
- remote 类型：SSH/HTTPS
- main push：通过/不通过
- GitHub 仓库 URL：...
- 远端 main Commit SHA：...

Hosted Runner：
- Run URL：...
- Frontend Verify Hard Gate / lingyi-pc-verify：通过/不通过
- node/npm 版本：...
- npm ci：...
- npm run verify：...
- npm audit --audit-level=high：...

Required Check：
- main required check 已配置：是/否
- Required check 实际名称：...

平台证据：
- 证据文件：/Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录/TASK-004C11_GitHub平台最终闭环证据.md
- 证据 commit SHA：...
- 证据已 push：是/否

未进入范围：
- 未修改前端业务代码
- 未修改后端业务代码
- 未进入 TASK-005/TASK-006
```
