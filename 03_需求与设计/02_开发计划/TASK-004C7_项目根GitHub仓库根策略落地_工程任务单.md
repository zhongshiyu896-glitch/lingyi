# TASK-004C7 项目根 GitHub 仓库根策略落地工程任务单

- 任务编号：TASK-004C7
- 模块：生产计划集成 / 前端工程基建 / GitHub 仓库根治理
- 优先级：P0
- 版本：V1.0
- 更新时间：2026-04-13 21:08 CST
- 作者：技术架构师
- 审计来源：审计意见书第 72 份，TASK-004C6 通过；最优先问题为必须先确定仓库根策略，否则 Hosted Runner 和 required check 都是纸面门禁
- 前置依赖：TASK-004C6 已通过
- 架构依据：`/03_需求与设计/01_架构设计/05_模块设计_生产计划集成.md` V1.11；`ADR-069`
- 任务边界：只做 GitHub 仓库根策略落地、嵌套 git 风险治理、CI 可见性验证和证据补齐；不新增业务功能，不修改前后端业务逻辑，不进入 TASK-005/TASK-006

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-004C7
模块：项目根 GitHub 仓库根策略落地
优先级：P0（仓库根策略封版）
════════════════════════════════════════════════════════════════════════════

【任务目标】
将 `/Users/hh/Desktop/领意服装管理系统` 确定并落地为唯一真实 GitHub 仓库根，让 `.github`、`06_前端`、`07_后端`、`03_需求与设计` 位于同一个 GitHub 仓库内，确保 CI 能看到 workflow 和被验证源码。

【架构决策】

采用方案 A：项目根作为唯一真实 GitHub 仓库根。

```text
/Users/hh/Desktop/领意服装管理系统
```

不采用方案 B：把 `.github`、`06_前端`、`07_后端` 迁入 `/Users/hh/Desktop/领意服装管理系统/02_源码`。

决策理由：
1. 当前正式交付目录、架构文档、CI workflow、前端、后端都已经位于项目根下。
2. `/02_源码` 是历史源码与旧 ERPNext app 目录，不是当前 FastAPI + Vue3 新开发主路径。
3. 若把新前端/后端迁入 `/02_源码`，会破坏当前文档路径、任务单路径、CI working-directory 和团队协作口径。
4. 项目根作为仓库根，能最小化迁移成本，并让 `.github`、`06_前端`、`07_后端`、`03_需求与设计` 一次性进入同一个版本控制边界。

【本地已知风险】

1. `/Users/hh/Desktop/领意服装管理系统` 当前不是 git repository。
2. `/Users/hh/Desktop/领意服装管理系统/02_源码` 当前存在 `.git`，是嵌套 git root。
3. 若直接在项目根 `git init` 后 `git add .`，`02_源码` 可能被识别为 embedded repository/submodule 风险。
4. 必须先备份并治理 `/02_源码/.git`，不得直接删除。

【允许执行】

允许新增或修改：
- /Users/hh/Desktop/领意服装管理系统/.gitignore
- /Users/hh/Desktop/领意服装管理系统/README.md（仅允许补仓库根说明）
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录/TASK-004C7_项目根仓库根策略落地证据.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/当前 sprint 任务清单.md（仅允许记录 TASK-004C7 状态）
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/架构师会话日志.md（仅允许追加会话记录）

允许由管理员执行：
- 在项目根执行 `git init -b main`。
- 给项目根配置 GitHub remote。
- 备份并移走 `/02_源码/.git`，把 `/02_源码` 降级为普通历史源码目录。
- 将项目根首次提交推送到 GitHub。
- 在 GitHub Actions 实跑前端和后端 workflow。
- 配置 required check。

禁止修改：
- 前端 production 业务代码。
- 后端业务代码。
- 后端测试业务断言。
- TASK-005/TASK-006 任意文件。
- 不得执行 `git reset --hard`、强制推送、覆盖远端历史，除非仓库管理员另行书面确认。

【必须执行步骤】

## 1. 备份嵌套 git 元数据

必须先备份 `/02_源码/.git`，不得直接删除。

建议命令：

```bash
mkdir -p /Users/hh/Desktop/领意服装管理系统_git_backups
cd /Users/hh/Desktop/领意服装管理系统/02_源码
tar -czf /Users/hh/Desktop/领意服装管理系统_git_backups/02_源码_git_$(date +%Y%m%d_%H%M%S).tar.gz .git
shasum -a 256 /Users/hh/Desktop/领意服装管理系统_git_backups/02_源码_git_*.tar.gz
```

备份完成后，由管理员将 `/02_源码/.git` 移出项目目录，禁止直接 `rm -rf`：

```bash
mv /Users/hh/Desktop/领意服装管理系统/02_源码/.git /Users/hh/Desktop/领意服装管理系统_git_backups/02_源码.git.backup_$(date +%Y%m%d_%H%M%S)
```

## 2. 初始化项目根仓库

```bash
cd /Users/hh/Desktop/领意服装管理系统
git init -b main
git rev-parse --show-toplevel
```

期望输出：

```text
/Users/hh/Desktop/领意服装管理系统
```

## 3. 配置 .gitignore

`.gitignore` 至少必须排除：

```gitignore
.DS_Store
node_modules/
dist/
.vite/
.venv/
__pycache__/
.pytest_cache/
.mypy_cache/
.ruff_cache/
*.pyc
*.log
.env
.env.*
!.env.example
```

禁止忽略：

```gitignore
.github/workflows/**
06_前端/lingyi-pc/**
07_后端/lingyi_service/**
03_需求与设计/**
```

## 4. 确认关键文件可被 git 跟踪

```bash
cd /Users/hh/Desktop/领意服装管理系统
git check-ignore -v .github/workflows/frontend-verify.yml .github/workflows/backend-postgresql.yml 06_前端/lingyi-pc/package.json 07_后端/lingyi_service/requirements.txt 03_需求与设计/01_架构设计/05_模块设计_生产计划集成.md || true
git add .github/workflows/frontend-verify.yml .github/workflows/backend-postgresql.yml 06_前端/lingyi-pc/package.json 07_后端/lingyi_service/requirements.txt 03_需求与设计/01_架构设计/05_模块设计_生产计划集成.md
git status --short
git ls-files .github/workflows/frontend-verify.yml .github/workflows/backend-postgresql.yml 06_前端/lingyi-pc/package.json 07_后端/lingyi_service/requirements.txt 03_需求与设计/01_架构设计/05_模块设计_生产计划集成.md
```

## 5. 配置 remote 并推送

由管理员选择新 GitHub 仓库或确认现有远端迁移策略。

禁止未经确认直接覆盖现有远端历史。

```bash
cd /Users/hh/Desktop/领意服装管理系统
git remote add origin <GitHub仓库URL>
git remote -v
git status --short
git add .
git commit -m "chore: establish project root repository"
git push -u origin main
```

如 remote 已存在，使用 `git remote set-url origin <GitHub仓库URL>` 前必须在证据文档记录原 remote。

## 6. GitHub Actions 与 required check 闭环

推送后必须确认：

1. GitHub Actions 页面能看到 `Frontend Verify Hard Gate`。
2. GitHub Actions 页面能看到 `Backend PostgreSQL Hard Gate`。
3. `Frontend Verify Hard Gate / lingyi-pc-verify` hosted runner 实跑通过。
4. main 分支 required check 配置为 `Frontend Verify Hard Gate / lingyi-pc-verify`。
5. TASK-002 的后端 PostgreSQL required check 仍保持阻塞口径，不得因为本任务自动放行 TASK-006。

【必须创建证据文件】

路径：
`/Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录/TASK-004C7_项目根仓库根策略落地证据.md`

模板：

```markdown
# TASK-004C7 项目根仓库根策略落地证据

- 任务编号：TASK-004C7
- 更新时间：YYYY-MM-DD HH:MM CST
- 执行人：
- 结论：通过/不通过

## 架构决策

- 采用方案：项目根作为唯一 GitHub 仓库根
- 仓库根：/Users/hh/Desktop/领意服装管理系统
- 不采用方案：把 .github、06_前端、07_后端 迁入 /02_源码

## 嵌套 git 备份

- 原嵌套 git 路径：/Users/hh/Desktop/领意服装管理系统/02_源码/.git
- 备份文件或备份目录：
- SHA256：
- 是否已移出项目目录：是/否

## Git 根确认

- git rev-parse --show-toplevel：
- git remote -v：
- 当前分支：
- Commit SHA：

## 关键文件跟踪确认

| 文件 | git ls-files 可见 | 结论 |
| --- | --- | --- |
| .github/workflows/frontend-verify.yml | 是/否 | 通过/不通过 |
| .github/workflows/backend-postgresql.yml | 是/否 | 通过/不通过 |
| 06_前端/lingyi-pc/package.json | 是/否 | 通过/不通过 |
| 07_后端/lingyi_service/requirements.txt | 是/否 | 通过/不通过 |
| 03_需求与设计/01_架构设计/05_模块设计_生产计划集成.md | 是/否 | 通过/不通过 |

## GitHub 平台确认

- GitHub 仓库 URL：
- Frontend Verify Hard Gate 是否可见：是/否
- Backend PostgreSQL Hard Gate 是否可见：是/否
- Frontend Hosted Runner Run URL：
- Frontend Verify Hard Gate / lingyi-pc-verify：通过/不通过
- main required check 是否已配置：是/否

## 敏感信息检查

- remote 输出无 token：通过/不通过
- Run URL 无 token：通过/不通过
- 证据文档无 password/token/secret/cookie/私钥：通过/不通过

## 备注

- 如未通过，阻塞原因：
```

【验收标准】

□ `/Users/hh/Desktop/领意服装管理系统` 已成为真实 git root。  
□ `/02_源码/.git` 已备份并移出项目目录，未直接删除。  
□ `.github/workflows/frontend-verify.yml` 被项目根 git 跟踪。  
□ `.github/workflows/backend-postgresql.yml` 被项目根 git 跟踪。  
□ `06_前端/lingyi-pc/package.json` 被项目根 git 跟踪。  
□ `07_后端/lingyi_service/requirements.txt` 被项目根 git 跟踪。  
□ `.gitignore` 未忽略 workflow、前端、后端、设计文档关键路径。  
□ GitHub Actions 页面能看到 Frontend Verify Hard Gate。  
□ Frontend hosted runner 实跑通过。  
□ main required check 已配置为 `Frontend Verify Hard Gate / lingyi-pc-verify`。  
□ 证据文档完整记录备份、git root、remote、Commit SHA、Run URL、required check。  
□ 证据文档无 token/password/secret/cookie/私钥。  
□ 未修改前端业务代码。  
□ 未修改后端业务代码。  
□ 未进入 TASK-005/TASK-006。  

【禁止事项】

- 禁止把 `/02_源码` 继续作为生产 GitHub 仓库根。
- 禁止直接删除 `/02_源码/.git`，必须先备份并记录 SHA256。
- 禁止使用 `git reset --hard`。
- 禁止强制推送覆盖远端历史，除非管理员另行确认。
- 禁止提交 `node_modules`、`dist`、`.venv`、日志缓存、密钥文件。
- 禁止修改前端 production 业务代码。
- 禁止修改后端业务代码。
- 禁止进入 TASK-005/TASK-006。

【交付回报格式】

完成后按以下格式回复：

```text
TASK-004C7 已完成。

仓库根策略：
- 采用项目根作为唯一 GitHub 仓库根：是/否
- git root：...
- remote：...
- Commit SHA：...

嵌套 git 治理：
- /02_源码/.git 已备份：是/否
- 备份路径：...
- SHA256：...
- 已移出项目目录：是/否

关键文件跟踪：
- frontend-verify.yml：是/否
- backend-postgresql.yml：是/否
- 前端 package.json：是/否
- 后端 requirements.txt：是/否

平台验证：
- Frontend Verify Hard Gate 可见：是/否
- Hosted Runner Run URL：...
- Frontend Verify Hard Gate / lingyi-pc-verify：通过/不通过
- main required check 已配置：是/否

证据文件：
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录/TASK-004C7_项目根仓库根策略落地证据.md

未进入范围：
- 未修改前端业务代码
- 未修改后端业务代码
- 未进入 TASK-005/TASK-006
```
