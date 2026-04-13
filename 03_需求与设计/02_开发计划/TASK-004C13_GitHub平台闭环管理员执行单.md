# TASK-004C13 GitHub 平台闭环管理员执行单

- 任务编号：TASK-004C13
- 模块：生产计划集成 / GitHub 平台闭环 / 管理员执行
- 优先级：P0
- 版本：V1.0
- 更新时间：2026-04-13 22:10 CST
- 作者：技术架构师
- 审计来源：审计意见书第 78 份，TASK-004C12 通过；剩余阻塞为 GitHub 平台闭环未完成
- 前置依赖：TASK-004C12 已通过，当前新的本地待推送 HEAD 为 `64fdfe4`
- 当前本地基线：git root `/Users/hh/Desktop/领意服装管理系统`，branch `main`，本地 HEAD `64fdfe4`，当前未配置 GitHub remote
- 架构依据：`/03_需求与设计/01_架构设计/05_模块设计_生产计划集成.md` V1.17；`ADR-075`
- 执行人：仓库管理员 / DevOps 管理员
- 任务边界：只做 GitHub 远端配置、push、Hosted Runner 实跑、required check 配置和平台证据回填；不修改前后端业务代码，不进入 TASK-005/TASK-006

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-004C13
模块：GitHub 平台闭环管理员执行
优先级：P0（平台门禁阻塞项）
════════════════════════════════════════════════════════════════════════════

【任务目标】
完成 `Frontend Verify Hard Gate / lingyi-pc-verify` 在 GitHub 平台侧的真实闭环：配置 `origin`、推送 `main`、确认 Hosted Runner 通过、配置 main required check，并回填平台证据。

【前置输入】
1. GitHub 仓库 URL：由管理员提供，必须是不含 token/password/secret/cookie 的 HTTPS 或 SSH URL。
2. 管理员权限：必须能推送 `main`、查看 Actions、配置 branch protection required check。
3. 当前本地仓库：`/Users/hh/Desktop/领意服装管理系统`。
4. 当前本地 HEAD：`64fdfe4 docs: clarify frontend ci platform sha lineage`。

【允许修改或创建】

允许修改：
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录/TASK-004C11_GitHub平台最终闭环证据.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录/TASK-004C12_C11证据SHA口径修正证据.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录/审计官会话日志.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/03_技术决策记录.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/05_模块设计_生产计划集成.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/架构师会话日志.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/当前 sprint 任务清单.md

允许新建：
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录/TASK-004C13_GitHub平台闭环证据.md

禁止修改：
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/**
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/**
- /Users/hh/Desktop/领意服装管理系统/.github/workflows/**
- /Users/hh/Desktop/领意服装管理系统/02_源码/**
- 任意 TASK-005/TASK-006 文件

【必须执行步骤】

## 1. 确认本地基线

```bash
cd /Users/hh/Desktop/领意服装管理系统
git rev-parse --show-toplevel
git branch --show-current
git log --oneline -8
git rev-parse --short HEAD
git remote -v || true
git status --short
```

必须确认：

```text
git root = /Users/hh/Desktop/领意服装管理系统
branch = main
当前 HEAD = 64fdfe4 或 TASK-004C13 准备提交后的新 HEAD
remote 当前为空，或仅在本任务中由管理员配置
```

## 2. 先形成平台前置 docs-only 准备提交

目的：把第 78 份审计结果、TASK-004C13 任务单、最新架构记录和 sprint 状态带进远端，避免 push 后远端缺少最新证据链。

只允许 stage 文档白名单：

```bash
git add \
  '03_需求与设计/02_开发计划/TASK-004C13_GitHub平台闭环管理员执行单.md' \
  '03_需求与设计/02_开发计划/当前 sprint 任务清单.md' \
  '03_需求与设计/01_架构设计/05_模块设计_生产计划集成.md' \
  '03_需求与设计/01_架构设计/03_技术决策记录.md' \
  '03_需求与设计/01_架构设计/架构师会话日志.md' \
  '03_需求与设计/05_审计记录.md' \
  '03_需求与设计/05_审计记录/审计官会话日志.md'
```

禁止使用：

```bash
git add .
git push --force
git push --force-with-lease
```

提交前检查：

```bash
git diff --cached --name-only
```

不得出现 `06_前端/`、`07_后端/`、`.github/workflows/`、`02_源码/`、`04_测试与验收/`、`05_交付物/`、`node_modules`、`dist`、`.venv`、`__pycache__`、`.env`、`*.db`。

形成准备提交：

```bash
git commit -m "docs: prepare github platform final closure"
git rev-parse --short HEAD
```

记录此提交为：`PLATFORM_PREP_HEAD`。

## 3. 配置 origin

管理员提供 GitHub 仓库 URL 后执行：

```bash
git remote add origin <GitHub仓库URL>
git remote -v
```

如果已存在错误 remote：

```bash
git remote set-url origin <GitHub仓库URL>
git remote -v
```

要求：
1. `git remote -v` 不得出现 token、password、secret、cookie、Authorization。
2. 如果 URL 中包含凭据，立即删除 remote 并停止。

## 4. 检查远端 main，禁止覆盖历史

```bash
git ls-remote --heads origin main
```

规则：
1. 如果远端没有 `main`，允许首次 push。
2. 如果远端存在 `main`，先执行 `git fetch origin main`。
3. 如果 `origin/main` 是本地 `main` 的祖先，允许普通 push。
4. 如果本地 `main` 不包含 `origin/main`，立即停止，不得 force push，提交合并方案给架构师。

允许 push：

```bash
git push -u origin main
```

禁止：

```bash
git push --force
git push --force-with-lease
```

## 5. 触发 GitHub Hosted Runner

目标 workflow：

```text
Frontend Verify Hard Gate / lingyi-pc-verify
```

触发方式：
1. 如果 push 自动触发 workflow，直接使用该 run。
2. 如果未自动触发，由管理员在 GitHub Actions 页面手动 `workflow_dispatch`。

Hosted Runner 必须证明：
1. Run URL 可访问。
2. Commit SHA 等于远端 `main` HEAD。
3. Branch 为 `main`。
4. Node 版本为 `v22.22.1`。
5. npm 版本为 `10.9.4`。
6. `npm ci` 通过。
7. `npm run verify` 通过。
8. `npm audit --audit-level=high` 通过。

## 6. 配置 main required check

在 GitHub branch protection / ruleset 中配置：

```text
Frontend Verify Hard Gate / lingyi-pc-verify
```

如果 GitHub UI 显示名称不同，必须记录实际名称并提交架构师确认。

required check 证据必须包含：
1. 分支：`main`。
2. check 名称。
3. 启用状态。
4. 配置时间。
5. 管理员账号或操作人。

## 7. 回填平台证据

创建或更新：

```text
/Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录/TASK-004C13_GitHub平台闭环证据.md
```

证据必须包含：
1. GitHub 仓库 URL。
2. `origin` 配置结果，不能包含凭据。
3. 本地 `PLATFORM_PREP_HEAD`。
4. 远端 `main` HEAD。
5. Hosted Runner Run URL。
6. Hosted Runner Commit SHA。
7. Node/npm 版本。
8. `npm ci / npm run verify / npm audit` 结果。
9. required check 实际名称。
10. branch protection / ruleset 配置证据。
11. 敏感信息扫描结果。
12. `<pending>` 字段必须全部清零。

## 8. 平台证据 docs-only 提交并 push

只允许 stage：

```bash
git add \
  '03_需求与设计/05_审计记录/TASK-004C13_GitHub平台闭环证据.md' \
  '03_需求与设计/05_审计记录.md' \
  '03_需求与设计/05_审计记录/审计官会话日志.md'
```

提交：

```bash
git commit -m "docs: record github platform final closure"
git push origin main
```

记录最终远端 HEAD：

```bash
git rev-parse --short HEAD
```

【验收标准】
□ `origin` 已配置，且 remote URL 无敏感凭据。
□ `main` 已成功 push 到 GitHub。
□ 未使用 force push。
□ Hosted Runner `Frontend Verify Hard Gate / lingyi-pc-verify` 通过。
□ Hosted Runner 的 Commit SHA 等于远端 `main` HEAD。
□ Node `v22.22.1`、npm `10.9.4` 已在 Hosted Runner 日志中确认。
□ `npm ci`、`npm run verify`、`npm audit --audit-level=high` 均通过。
□ `Frontend Verify Hard Gate / lingyi-pc-verify` 已配置为 main required check。
□ `TASK-004C13_GitHub平台闭环证据.md` 已回填且无 `<pending>`。
□ 证据文档无 token/password/secret/cookie/Authorization/私钥。
□ 未修改前端、后端、workflow、TASK-005、TASK-006。
□ 审计官复审通过前，TASK-005/TASK-006 继续阻塞。

【失败处理】
1. 缺 GitHub URL：停止，回复“等待管理员提供 GitHub 仓库 URL”。
2. remote URL 含凭据：删除 remote，停止，重新提供安全 URL。
3. 远端 main 与本地 main 分叉：停止，不得 force push，提交合并方案给架构师。
4. Hosted Runner 失败：保留 Run URL 和失败日志，禁止配置 required check 为通过，提交修复任务给架构师。
5. required check 名称不一致：记录 GitHub 实际名称，提交架构师确认。

════════════════════════════════════════════════════════════════════════════
