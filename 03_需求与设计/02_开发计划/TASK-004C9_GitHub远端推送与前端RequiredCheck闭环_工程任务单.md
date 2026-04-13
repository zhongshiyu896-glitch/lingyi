# TASK-004C9 GitHub 远端推送与前端 Required Check 闭环工程任务单

- 任务编号：TASK-004C9
- 模块：生产计划集成 / 前端工程基建 / GitHub 平台闭环
- 优先级：P0
- 版本：V1.0
- 更新时间：2026-04-13 21:33 CST
- 作者：技术架构师
- 审计来源：审计意见书第 74 份，TASK-004C8 通过；最优先问题为配置 `origin`、push `main`、触发 GitHub Hosted Runner，并将 `Frontend Verify Hard Gate / lingyi-pc-verify` 配置成 main required check
- 前置依赖：TASK-004C8 已通过，根仓库首个提交已完成，tracked 文件已从 6 个补齐到 236 个，离线 tracked snapshot 前后端验证通过
- 当前本地基线：git root `/Users/hh/Desktop/领意服装管理系统`，branch `main`，当前提交 `e4a3e4b`，当前未配置 GitHub remote
- 架构依据：`/03_需求与设计/01_架构设计/05_模块设计_生产计划集成.md` V1.13；`ADR-071`
- 任务边界：只做 GitHub remote、push、hosted runner 实跑、required check 配置和证据补齐；不新增业务功能，不修改前后端业务逻辑，不进入 TASK-005/TASK-006

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-004C9
模块：GitHub 远端推送与前端 Required Check 闭环
优先级：P0（平台合并门禁闭环）
════════════════════════════════════════════════════════════════════════════

【任务目标】
将本地项目根仓库推送到 GitHub，确认 GitHub Hosted Runner 能执行 `Frontend Verify Hard Gate / lingyi-pc-verify`，并把该 check 配置为 main 分支 required check。

【当前可用前置成果】

1. 项目根已成为 git root：`/Users/hh/Desktop/领意服装管理系统`。
2. 当前分支：`main`。
3. 当前本地提交：`e4a3e4b`。
4. tracked 文件数：236。
5. 前端 `package-lock/scripts/tsconfig/vite/src` 已进入 tracked 文件。
6. 后端 `app/tests/scripts/migrations` 已进入 tracked 文件。
7. 审计官已用只包含 `git tracked` 文件的 snapshot 复跑前后端验证，均通过。
8. 当前缺口：未配置 GitHub remote，未 push `main`，未 hosted runner 实跑，未 required check 配置。

【允许执行】

允许新增或修改：
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录/TASK-004C9_GitHub远端推送与前端RequiredCheck证据.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/当前 sprint 任务清单.md（仅允许记录 TASK-004C9 状态）
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/架构师会话日志.md（仅允许追加会话记录）
- GitHub 平台 branch protection / ruleset 配置

禁止修改：
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/**
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/**
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/**
- /Users/hh/Desktop/领意服装管理系统/.github/workflows/frontend-verify.yml（除非 hosted runner 明确失败且审计官确认是 workflow 配置问题）
- /Users/hh/Desktop/领意服装管理系统/.github/workflows/backend-postgresql.yml（除非 hosted runner 明确失败且审计官确认是 workflow 配置问题）
- 任意 TASK-005/TASK-006 文件

【必须完成】

1. 确认 GitHub 仓库 URL。
2. 确认 remote URL 不包含 token、password、secret、cookie。
3. 配置 `origin`。
4. push `main` 到 GitHub。
5. 在 GitHub Actions 页面确认可见 `Frontend Verify Hard Gate`。
6. 触发或等待 `Frontend Verify Hard Gate / lingyi-pc-verify` hosted runner 执行。
7. 确认 hosted runner 上 `node -v = v22.22.1`。
8. 确认 hosted runner 上 `npm -v = 10.9.4`。
9. 确认 hosted runner 上 `npm ci` 成功。
10. 确认 hosted runner 上 `npm run verify` 成功。
11. 确认 hosted runner 上 `npm audit --audit-level=high` 成功。
12. 将 `Frontend Verify Hard Gate / lingyi-pc-verify` 配置为 main 分支 required check。
13. 确认 branch protection 或 ruleset 对 main 生效。
14. 记录 Run URL、Commit SHA、Branch、Required Check 配置证据。
15. 运行敏感信息扫描，确认证据文件和 remote 输出不泄露 token/password/secret/cookie/私钥。

【必须执行命令】

## 1. 本地仓库状态确认

```bash
cd /Users/hh/Desktop/领意服装管理系统
pwd
git rev-parse --show-toplevel
git branch --show-current
git rev-parse HEAD
git status --short
git ls-files | wc -l
git remote -v || true
```

## 2. 配置 remote

由管理员提供 GitHub 仓库 URL。

推荐使用 SSH remote：

```bash
cd /Users/hh/Desktop/领意服装管理系统
git remote add origin git@github.com:<org-or-user>/<repo>.git
git remote -v
```

如必须使用 HTTPS remote，禁止在 URL 中写 token：

```bash
git remote add origin https://github.com/<org-or-user>/<repo>.git
git remote -v
```

敏感信息扫描：

```bash
git remote -v | rg -i "token|password|passwd|secret|cookie|ghp_|github_pat_" && exit 1 || true
```

## 3. 推送 main

```bash
cd /Users/hh/Desktop/领意服装管理系统
git push -u origin main
```

如果远端已有历史，禁止直接强推。必须暂停并提交冲突/历史合并方案给架构师和审计官确认。

## 4. 平台确认

在 GitHub 页面完成：

```text
Actions -> Frontend Verify Hard Gate -> lingyi-pc-verify
```

必须记录：

1. Run URL。
2. Commit SHA。
3. Branch。
4. job conclusion。
5. `node -v` 日志行。
6. `npm -v` 日志行。
7. `npm ci` 成功日志。
8. `npm run verify` 成功日志。
9. `npm audit --audit-level=high` 成功日志。

## 5. Required Check 配置

在 GitHub branch protection 或 ruleset 中配置：

```text
Frontend Verify Hard Gate / lingyi-pc-verify
```

要求：

1. 作用分支：`main`。
2. required check 必须为 GitHub 实际显示名称，不得手写近似名称。
3. 证据文档必须记录 branch protection/ruleset 名称。
4. 若 GitHub required check 名称显示与预期不同，必须记录实际名称并提交架构师确认。

【必须创建证据文件】

路径：
`/Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录/TASK-004C9_GitHub远端推送与前端RequiredCheck证据.md`

模板：

```markdown
# TASK-004C9 GitHub 远端推送与前端 Required Check 证据

- 任务编号：TASK-004C9
- 更新时间：YYYY-MM-DD HH:MM CST
- 执行人：
- 结论：通过/不通过

## 本地仓库状态

- git root：/Users/hh/Desktop/领意服装管理系统
- branch：main
- 本地 Commit SHA：
- tracked 文件数：
- git status --short：

## Remote 配置

- remote 类型：SSH / HTTPS
- remote URL 脱敏展示：
- remote 输出敏感信息扫描：通过/不通过

## Push 结果

- push main：通过/不通过
- GitHub 仓库 URL：
- 远端 main Commit SHA：

## Hosted Runner 结果

- Workflow 名称：Frontend Verify Hard Gate
- Job 名称：lingyi-pc-verify
- Run URL：
- Branch：main
- Commit SHA：
- Conclusion：success/failure/cancelled

| 检查项 | 结果 | 证据 |
| --- | --- | --- |
| node -v = v22.22.1 | 通过/不通过 | 日志行 |
| npm -v = 10.9.4 | 通过/不通过 | 日志行 |
| npm ci | 通过/不通过 | 日志行 |
| npm run verify | 通过/不通过 | 日志行 |
| npm audit --audit-level=high | 通过/不通过 | 日志行 |

## Required Check 配置

- Branch protection / Ruleset 名称：
- 作用分支：main
- Required check 实际名称：
- 是否等于 `Frontend Verify Hard Gate / lingyi-pc-verify`：是/否
- 配置结果：通过/不通过

## 敏感信息检查

- remote 无 token/password/secret/cookie：通过/不通过
- Run URL 无 token：通过/不通过
- 日志摘录无 token/password/secret/cookie/私钥：通过/不通过
- 证据文档无 token/password/secret/cookie/私钥：通过/不通过

## 备注

- 如未通过，阻塞原因：
```

【验收标准】

□ `origin` 已配置。  
□ `git remote -v` 不包含 token/password/secret/cookie。  
□ `main` 已成功 push 到 GitHub。  
□ GitHub Actions 页面可见 `Frontend Verify Hard Gate`。  
□ Hosted runner `Frontend Verify Hard Gate / lingyi-pc-verify` 执行成功。  
□ hosted runner 日志确认 `node -v = v22.22.1`。  
□ hosted runner 日志确认 `npm -v = 10.9.4`。  
□ hosted runner 日志确认 `npm ci` 成功。  
□ hosted runner 日志确认 `npm run verify` 成功。  
□ hosted runner 日志确认 `npm audit --audit-level=high` 成功。  
□ main 分支 required check 已配置为 `Frontend Verify Hard Gate / lingyi-pc-verify`。  
□ 证据文档记录 Run URL、Commit SHA、Branch、required check 名称。  
□ 证据文档无 token/password/secret/cookie/私钥。  
□ 未修改前端业务代码。  
□ 未修改后端业务代码。  
□ 未进入 TASK-005/TASK-006。  

【失败处理规则】

1. 如果 `git push` 因远端已有历史失败，停止，不得强推，提交远端历史冲突说明。
2. 如果 hosted runner 找不到 workflow，回到 TASK-004C6 仓库根可见性口径复核。
3. 如果 hosted runner 缺文件，回到 TASK-004C8 tracked 文件清单复核。
4. 如果 `npm ci` 失败，只允许修依赖锁文件或版本声明，不得跳过 `npm ci`。
5. 如果 `npm run verify` 失败，只允许按失败原因补契约或类型问题，不得弱化 verify 脚本。
6. 如果 required check 名称无法选择，记录 GitHub 实际显示名称，提交架构师确认。

【禁止事项】

- 禁止在 remote URL 中写 token。
- 禁止 `git push --force` 或覆盖远端历史。
- 禁止跳过 hosted runner，仅用本地验证替代。
- 禁止把近似 check 名称当成 required check。
- 禁止弱化 `.github/workflows/frontend-verify.yml`。
- 禁止弱化 `npm run verify`。
- 禁止修改前端 production 业务代码。
- 禁止修改后端业务代码。
- 禁止进入 TASK-005/TASK-006。

【交付回报格式】

完成后按以下格式回复：

```text
TASK-004C9 已完成。

Remote 与 Push：
- origin 已配置：是/否
- remote 类型：SSH/HTTPS
- main push：通过/不通过
- GitHub 仓库 URL：...
- Commit SHA：...

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

证据文件：
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录/TASK-004C9_GitHub远端推送与前端RequiredCheck证据.md

未进入范围：
- 未修改前端业务代码
- 未修改后端业务代码
- 未进入 TASK-005/TASK-006
```
