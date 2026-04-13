# TASK-004C6 Git 仓库根与 CI 可见性整改工程任务单

- 任务编号：TASK-004C6
- 模块：生产计划集成 / 前端工程基建 / GitHub 仓库根治理
- 优先级：P0
- 版本：V1.0
- 更新时间：2026-04-13 21:02 CST
- 作者：技术架构师
- 审计来源：审计意见书第 71 份，TASK-004C5 有条件通过但平台闭环未完成；最高风险为 workflow 文件不在真实 git root 内，GitHub 可能看不到 CI 配置
- 前置依赖：TASK-004C5 有条件通过，平台闭环阻塞在仓库根口径
- 架构依据：`/03_需求与设计/01_架构设计/05_模块设计_生产计划集成.md` V1.10；`ADR-068`
- 任务边界：只做 Git 仓库根确认、CI 文件可见性整改和证据补齐；不新增业务功能，不修改前后端业务逻辑，不进入 TASK-005/TASK-006

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-004C6
模块：Git 仓库根与 CI 可见性整改
优先级：P0（CI 可见性阻断整改）
════════════════════════════════════════════════════════════════════════════

【任务目标】
确认真实 GitHub 仓库根，并确保 `.github/workflows/frontend-verify.yml`、前端目录、后端目录在同一个 GitHub 仓库根下可被 GitHub 识别和执行。

【本地已知事实】

审计与架构侧本地探针已确认：

1. `/Users/hh/Desktop/领意服装管理系统` 当前不是 git repository。
2. `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc` 当前不是 git repository。
3. `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service` 当前不是 git repository。
4. 当前可检测 git root 是 `/Users/hh/Desktop/领意服装管理系统/02_源码`。
5. 当前 workflow 文件位于 `/Users/hh/Desktop/领意服装管理系统/.github/workflows/frontend-verify.yml`，不在 `/Users/hh/Desktop/领意服装管理系统/02_源码` git root 内。
6. 如果 GitHub 远端实际对应 `/02_源码`，则当前 `.github/workflows/frontend-verify.yml` 不会被 GitHub 识别。

【架构决策】

生产系统 GitHub 仓库根必须同时包含：

1. `.github/workflows/frontend-verify.yml`
2. `.github/workflows/backend-postgresql.yml`
3. `06_前端/lingyi-pc/package.json`
4. `07_后端/lingyi_service/requirements.txt`
5. 与 TASK-004 相关的前端、后端、测试、脚本文件

推荐仓库根：
`/Users/hh/Desktop/领意服装管理系统`

如果管理员决定继续使用 `/Users/hh/Desktop/领意服装管理系统/02_源码` 作为 GitHub 仓库根，则必须把前端、后端和 workflow 迁入该 git root，并同步修正 workflow 中的 working-directory 与 paths。不得出现 workflow 在一个目录、源码在另一个未纳入 git 目录的状态。

【允许执行】

允许新增或修改：
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录/TASK-004C6_Git仓库根与CI可见性证据.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/当前 sprint 任务清单.md（仅允许记录 TASK-004C6 状态）
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/架构师会话日志.md（仅允许追加会话记录）
- GitHub 仓库根内 `.github/workflows/frontend-verify.yml`（仅允许为匹配真实仓库根修正路径）
- GitHub 仓库根内 `.github/workflows/backend-postgresql.yml`（仅允许为匹配真实仓库根修正路径）
- GitHub 仓库根内 `.gitignore`（仅允许排除 node_modules/dist/.venv 等生成物，不得忽略业务源码和 workflow）

禁止修改：
- 前端 production 业务代码
- 后端业务代码
- 后端测试业务断言
- TASK-005/TASK-006 任意文件

【必须完成】

1. 确认 GitHub 真实仓库根。
2. 输出 `git rev-parse --show-toplevel` 结果。
3. 输出 `git remote -v` 结果。
4. 确认 `.github/workflows/frontend-verify.yml` 在真实 git root 内。
5. 确认 `06_前端/lingyi-pc/package.json` 在真实 git root 内。
6. 确认 `07_后端/lingyi_service/requirements.txt` 在真实 git root 内。
7. 确认 workflow 中的 `working-directory` 与真实仓库内路径一致。
8. 确认 workflow `paths` 与真实仓库内路径一致。
9. 确认 `git ls-files` 能看到 frontend workflow 和前端 package 文件。
10. 确认 `.gitignore` 未忽略 `.github/workflows/**`、`06_前端/lingyi-pc/**`、`07_后端/lingyi_service/**`。
11. 在 GitHub 上确认 workflow 已出现在 Actions 列表。
12. 在 GitHub hosted runner 上实跑 `Frontend Verify Hard Gate / lingyi-pc-verify`。
13. 若真实仓库根迁移或路径调整，必须重新执行 TASK-004C4 的本地与 CI 验证。

【必须执行命令】

在推荐仓库根执行：

```bash
cd /Users/hh/Desktop/领意服装管理系统
pwd
git rev-parse --show-toplevel
git remote -v
git status --short
git ls-files .github/workflows/frontend-verify.yml 06_前端/lingyi-pc/package.json 07_后端/lingyi_service/requirements.txt
git check-ignore -v .github/workflows/frontend-verify.yml 06_前端/lingyi-pc/package.json 07_后端/lingyi_service/requirements.txt || true
```

如果继续使用 `/02_源码` 作为仓库根，则必须执行：

```bash
cd /Users/hh/Desktop/领意服装管理系统/02_源码
pwd
git rev-parse --show-toplevel
git remote -v
git status --short
git ls-files .github/workflows/frontend-verify.yml 06_前端/lingyi-pc/package.json 07_后端/lingyi_service/requirements.txt
git check-ignore -v .github/workflows/frontend-verify.yml 06_前端/lingyi-pc/package.json 07_后端/lingyi_service/requirements.txt || true
```

【本地前端验证】

```bash
cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc
node -v
npm -v
npm ci
npm run verify
npm audit --audit-level=high
```

【后端回归验证】

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest -q tests/test_production_plan.py tests/test_production_work_order_outbox.py tests/test_production_job_card_sync.py
.venv/bin/python -m pytest -q
.venv/bin/python -m unittest discover
.venv/bin/python -m py_compile $(find app tests scripts -name '*.py' -print)
```

【证据文档要求】

必须创建：
`/Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录/TASK-004C6_Git仓库根与CI可见性证据.md`

模板：

```markdown
# TASK-004C6 Git 仓库根与 CI 可见性证据

- 任务编号：TASK-004C6
- 更新时间：YYYY-MM-DD HH:MM CST
- 执行人：
- 结论：通过/不通过

## 仓库根确认

- 本地项目根：/Users/hh/Desktop/领意服装管理系统
- git rev-parse --show-toplevel：
- GitHub remote：
- 当前分支：
- Commit SHA：

## CI 可见性确认

| 文件 | 是否在 git root 内 | git ls-files 是否可见 | 结论 |
| --- | --- | --- | --- |
| .github/workflows/frontend-verify.yml | 是/否 | 是/否 | 通过/不通过 |
| .github/workflows/backend-postgresql.yml | 是/否 | 是/否 | 通过/不通过 |
| 06_前端/lingyi-pc/package.json | 是/否 | 是/否 | 通过/不通过 |
| 07_后端/lingyi_service/requirements.txt | 是/否 | 是/否 | 通过/不通过 |

## GitHub Actions 可见性

- GitHub Actions 页面是否能看到 Frontend Verify Hard Gate：是/否
- Hosted Runner Run URL：
- `Frontend Verify Hard Gate / lingyi-pc-verify` 结果：通过/不通过

## Required Check 配置

- Branch protection / Ruleset 名称：
- Required check 名称：Frontend Verify Hard Gate / lingyi-pc-verify
- 配置结果：通过/不通过

## 敏感信息检查

- remote 输出无 token：通过/不通过
- Run URL 无 token：通过/不通过
- 日志/截图无 password/token/secret/cookie/私钥：通过/不通过

## 备注

- 如未通过，阻塞原因：
```

【验收标准】

□ 已确认真实 GitHub 仓库根。  
□ `.github/workflows/frontend-verify.yml` 位于真实 git root 内。  
□ `06_前端/lingyi-pc/package.json` 位于真实 git root 内。  
□ `07_后端/lingyi_service/requirements.txt` 位于真实 git root 内。  
□ `git ls-files` 能看到 frontend workflow 与前端 package 文件。  
□ `.gitignore` 未忽略 workflow、前端、后端关键路径。  
□ GitHub Actions 页面能看到 `Frontend Verify Hard Gate`。  
□ Hosted runner 实跑 `Frontend Verify Hard Gate / lingyi-pc-verify` 通过。  
□ main 分支 required check 已配置为 `Frontend Verify Hard Gate / lingyi-pc-verify`。  
□ 证据文档完整记录仓库根、remote、Run URL、Commit SHA、required check。  
□ 证据文档无 token/password/secret/cookie/私钥。  
□ 未修改前端业务代码。  
□ 未修改后端业务代码。  
□ 未进入 TASK-005/TASK-006。  

【禁止事项】

- 禁止把 `/Users/hh/Desktop/领意服装管理系统/.github/workflows/frontend-verify.yml` 留在 git root 外，却宣称 GitHub CI 已闭环。
- 禁止只配置 remote，不确认 workflow 被 `git ls-files` 跟踪。
- 禁止只本地运行 `npm run verify`，不做 hosted runner 实跑。
- 禁止把历史 `/02_源码` repo 与当前 `/06_前端`、`/07_后端` 分离状态视为合格。
- 禁止提交 node_modules、dist、.venv、日志缓存、密钥文件。
- 禁止修改前端 production 业务代码。
- 禁止修改后端业务代码。
- 禁止进入 TASK-005/TASK-006。

【交付回报格式】

完成后按以下格式回复：

```text
TASK-004C6 已完成。

仓库根结论：
- 真实 git root：...
- GitHub remote：...
- Commit SHA：...

CI 可见性：
- frontend-verify.yml 在 git root 内：是/否
- 06_前端/lingyi-pc/package.json 被 git 跟踪：是/否
- 07_后端/lingyi_service/requirements.txt 被 git 跟踪：是/否
- GitHub Actions 可见 Frontend Verify Hard Gate：是/否

平台验证：
- Hosted Runner Run URL：...
- Frontend Verify Hard Gate / lingyi-pc-verify：通过/不通过
- main required check 已配置：是/否

证据文件：
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录/TASK-004C6_Git仓库根与CI可见性证据.md

未进入范围：
- 未修改前端业务代码
- 未修改后端业务代码
- 未进入 TASK-005/TASK-006
```
