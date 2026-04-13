# TASK-004C8 根仓库首个提交清单与离线 CI 模拟工程任务单

- 任务编号：TASK-004C8
- 模块：生产计划集成 / 前端工程基建 / GitHub 仓库首提治理
- 优先级：P0
- 版本：V1.0
- 更新时间：2026-04-13 21:20 CST
- 作者：技术架构师
- 审计来源：审计意见书第 73 份，TASK-004C7 有条件通过；最高风险为根仓库 index 只有 6 个文件，GitHub runner 看不到 `package-lock.json/scripts/tsconfig/vite/src` 等 CI 必需文件
- 前置依赖：TASK-004C7 有条件通过，项目根 git root 已立起来但首个提交清单未闭环
- 架构依据：`/03_需求与设计/01_架构设计/05_模块设计_生产计划集成.md` V1.12；`ADR-070`
- 任务边界：只做根仓库首个提交清单、git 跟踪范围、离线 CI 模拟和证据补齐；不新增业务功能，不修改前后端业务逻辑，不进入 TASK-005/TASK-006

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-004C8
模块：根仓库首个提交清单与离线 CI 模拟
优先级：P0（GitHub Runner 可复现门禁）
════════════════════════════════════════════════════════════════════════════

【任务目标】
补齐项目根仓库首个提交清单，确保 GitHub runner 能看到前端 verify 和后端回归所需全部文件；并用“只包含 git tracked 文件”的临时目录离线模拟 CI，证明推送后 hosted runner 能复现本地通过。

【当前阻断事实】

当前项目根 git index 只有以下 6 个文件：

```text
.github/workflows/backend-postgresql.yml
.github/workflows/frontend-verify.yml
.gitignore
03_需求与设计/01_架构设计/05_模块设计_生产计划集成.md
06_前端/lingyi-pc/package.json
07_后端/lingyi_service/requirements.txt
```

缺失会导致 CI 失败的关键文件包括：

1. `06_前端/lingyi-pc/package-lock.json`
2. `06_前端/lingyi-pc/scripts/**`
3. `06_前端/lingyi-pc/tsconfig.json`
4. `06_前端/lingyi-pc/tsconfig.node.json`
5. `06_前端/lingyi-pc/vite.config.ts`
6. `06_前端/lingyi-pc/index.html`
7. `06_前端/lingyi-pc/src/**`
8. `07_后端/lingyi_service/requirements-dev.txt`
9. `07_后端/lingyi_service/pytest.ini`
10. `07_后端/lingyi_service/app/**`
11. `07_后端/lingyi_service/tests/**`
12. `07_后端/lingyi_service/scripts/**`
13. `07_后端/lingyi_service/migrations/**`

【首个生产提交范围】

必须纳入首个生产提交：

```text
.github/workflows/**
.gitignore
README.md
03_需求与设计/01_架构设计/**
03_需求与设计/02_开发计划/**
03_需求与设计/05_审计记录.md
03_需求与设计/05_审计记录/**
06_前端/lingyi-pc/.nvmrc
06_前端/lingyi-pc/.npmrc
06_前端/lingyi-pc/package.json
06_前端/lingyi-pc/package-lock.json
06_前端/lingyi-pc/index.html
06_前端/lingyi-pc/tsconfig.json
06_前端/lingyi-pc/tsconfig.node.json
06_前端/lingyi-pc/vite.config.ts
06_前端/lingyi-pc/scripts/**
06_前端/lingyi-pc/src/**
07_后端/lingyi_service/README.md
07_后端/lingyi_service/pytest.ini
07_后端/lingyi_service/requirements.txt
07_后端/lingyi_service/requirements-dev.txt
07_后端/lingyi_service/app/**
07_后端/lingyi_service/tests/**
07_后端/lingyi_service/scripts/**
07_后端/lingyi_service/migrations/**
```

暂不纳入首个生产提交：

```text
02_源码/**
04_测试与验收/测试证据/**
05_交付物/**
```

说明：`02_源码` 已按 ADR-069 降级为历史源码目录，不作为当前生产 CI 仓库根。是否作为历史归档纳入 GitHub，后续单独出任务，不得混入 TASK-004C8。

【必须排除】

以下文件或目录不得进入 git 跟踪：

```text
**/node_modules/**
**/dist/**
**/.vite/**
**/.venv/**
**/__pycache__/**
**/.pytest_cache/**
**/.mypy_cache/**
**/.ruff_cache/**
**/*.pyc
**/*.log
**/.env
**/.env.*
07_后端/lingyi_service/lingyi_service.db
07_后端/lingyi_service/.pytest-postgresql.xml
```

【必须执行步骤】

## 1. 更新并核验 `.gitignore`

确保 `.gitignore` 排除所有生成物和敏感文件，同时不误伤生产源码。

```bash
cd /Users/hh/Desktop/领意服装管理系统
cat .gitignore
git check-ignore -v 06_前端/lingyi-pc/node_modules 06_前端/lingyi-pc/dist 07_后端/lingyi_service/.venv 07_后端/lingyi_service/lingyi_service.db 07_后端/lingyi_service/.pytest-postgresql.xml || true
git check-ignore -v .github/workflows/frontend-verify.yml 06_前端/lingyi-pc/package-lock.json 06_前端/lingyi-pc/scripts/check-production-contracts.mjs 06_前端/lingyi-pc/src/api/production.ts 07_后端/lingyi_service/app/main.py 07_后端/lingyi_service/tests/test_production_plan.py || true
```

要求：
1. 生成物应被 ignore 命中。
2. workflow、前端源码、后端源码、测试文件不得被 ignore 命中。

## 2. 按清单加入 git index

```bash
cd /Users/hh/Desktop/领意服装管理系统
git add .github/workflows .gitignore README.md
git add 03_需求与设计/01_架构设计 03_需求与设计/02_开发计划 03_需求与设计/05_审计记录.md 03_需求与设计/05_审计记录
git add 06_前端/lingyi-pc/.nvmrc 06_前端/lingyi-pc/.npmrc 06_前端/lingyi-pc/package.json 06_前端/lingyi-pc/package-lock.json 06_前端/lingyi-pc/index.html 06_前端/lingyi-pc/tsconfig.json 06_前端/lingyi-pc/tsconfig.node.json 06_前端/lingyi-pc/vite.config.ts 06_前端/lingyi-pc/scripts 06_前端/lingyi-pc/src
git add 07_后端/lingyi_service/README.md 07_后端/lingyi_service/pytest.ini 07_后端/lingyi_service/requirements.txt 07_后端/lingyi_service/requirements-dev.txt 07_后端/lingyi_service/app 07_后端/lingyi_service/tests 07_后端/lingyi_service/scripts 07_后端/lingyi_service/migrations
```

## 3. 检查不得进入 index 的文件

```bash
cd /Users/hh/Desktop/领意服装管理系统
git diff --cached --name-only | rg "node_modules|dist/|\.vite|\.venv|__pycache__|\.pytest_cache|\.pyc$|\.log$|\.env|lingyi_service\.db|\.pytest-postgresql\.xml" && exit 1 || true
git diff --cached --name-only | rg "^02_源码/" && exit 1 || true
git diff --cached --name-only | rg "^04_测试与验收/测试证据/" && exit 1 || true
```

## 4. 检查必须进入 index 的文件

```bash
cd /Users/hh/Desktop/领意服装管理系统
git diff --cached --name-only | rg '^\.github/workflows/frontend-verify\.yml$'
git diff --cached --name-only | rg '^\.github/workflows/backend-postgresql\.yml$'
git diff --cached --name-only | rg '^06_前端/lingyi-pc/package-lock\.json$'
git diff --cached --name-only | rg '^06_前端/lingyi-pc/scripts/check-production-contracts\.mjs$'
git diff --cached --name-only | rg '^06_前端/lingyi-pc/scripts/test-production-contracts\.mjs$'
git diff --cached --name-only | rg '^06_前端/lingyi-pc/tsconfig\.json$'
git diff --cached --name-only | rg '^06_前端/lingyi-pc/vite\.config\.ts$'
git diff --cached --name-only | rg '^06_前端/lingyi-pc/src/api/production\.ts$'
git diff --cached --name-only | rg '^06_前端/lingyi-pc/src/views/production/'
git diff --cached --name-only | rg '^07_后端/lingyi_service/requirements-dev\.txt$'
git diff --cached --name-only | rg '^07_后端/lingyi_service/pytest\.ini$'
git diff --cached --name-only | rg '^07_后端/lingyi_service/app/main\.py$'
git diff --cached --name-only | rg '^07_后端/lingyi_service/app/routers/production\.py$'
git diff --cached --name-only | rg '^07_后端/lingyi_service/tests/test_production_plan\.py$'
git diff --cached --name-only | rg '^07_后端/lingyi_service/tests/test_production_work_order_outbox\.py$'
git diff --cached --name-only | rg '^07_后端/lingyi_service/tests/test_production_job_card_sync\.py$'
```

## 5. 仅 git tracked 文件离线 CI 模拟

必须创建临时目录，只复制 `git ls-files` 文件，不能直接在原工作区跑。

```bash
cd /Users/hh/Desktop/领意服装管理系统
rm -rf /tmp/lingyi-root-ci-snapshot
mkdir -p /tmp/lingyi-root-ci-snapshot
git ls-files -z | rsync -a --files-from=- --from0 ./ /tmp/lingyi-root-ci-snapshot/
cd /tmp/lingyi-root-ci-snapshot
find . -maxdepth 3 -type d \( -name node_modules -o -name dist -o -name .venv -o -name __pycache__ \) -print
```

要求：上述 `find` 不得输出生成物目录。

## 6. 在离线 snapshot 中跑前端 CI 等价验证

```bash
cd /tmp/lingyi-root-ci-snapshot/06_前端/lingyi-pc
node -v
npm -v
npm ci
npm run verify
npm audit --audit-level=high
```

## 7. 在离线 snapshot 中跑后端回归

```bash
cd /tmp/lingyi-root-ci-snapshot/07_后端/lingyi_service
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt -r requirements-dev.txt
.venv/bin/python -m pytest -q tests/test_production_plan.py tests/test_production_work_order_outbox.py tests/test_production_job_card_sync.py
.venv/bin/python -m pytest -q
.venv/bin/python -m unittest discover
.venv/bin/python -m py_compile $(find app tests scripts -name '*.py' -print)
```

说明：snapshot 里的 `.venv` 是临时验证生成物，不得回拷项目根，不得进入 git index。

## 8. 形成首个提交

离线 CI 模拟通过后，才允许提交。

```bash
cd /Users/hh/Desktop/领意服装管理系统
git status --short
git commit -m "chore: establish production repository baseline"
```

禁止在离线 CI 模拟失败时提交。

【必须创建证据文件】

路径：
`/Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录/TASK-004C8_根仓库首个提交与离线CI证据.md`

模板：

```markdown
# TASK-004C8 根仓库首个提交与离线 CI 证据

- 任务编号：TASK-004C8
- 更新时间：YYYY-MM-DD HH:MM CST
- 执行人：
- 结论：通过/不通过

## Git 跟踪范围

- git root：/Users/hh/Desktop/领意服装管理系统
- staged 文件数：
- commit SHA：

## 必须文件检查

| 文件/目录 | 已进入 index | 结论 |
| --- | --- | --- |
| .github/workflows/frontend-verify.yml | 是/否 | 通过/不通过 |
| .github/workflows/backend-postgresql.yml | 是/否 | 通过/不通过 |
| 06_前端/lingyi-pc/package-lock.json | 是/否 | 通过/不通过 |
| 06_前端/lingyi-pc/scripts/** | 是/否 | 通过/不通过 |
| 06_前端/lingyi-pc/tsconfig.json | 是/否 | 通过/不通过 |
| 06_前端/lingyi-pc/vite.config.ts | 是/否 | 通过/不通过 |
| 06_前端/lingyi-pc/src/** | 是/否 | 通过/不通过 |
| 07_后端/lingyi_service/requirements-dev.txt | 是/否 | 通过/不通过 |
| 07_后端/lingyi_service/pytest.ini | 是/否 | 通过/不通过 |
| 07_后端/lingyi_service/app/** | 是/否 | 通过/不通过 |
| 07_后端/lingyi_service/tests/** | 是/否 | 通过/不通过 |
| 07_后端/lingyi_service/scripts/** | 是/否 | 通过/不通过 |

## 排除文件检查

| 规则 | 是否进入 index | 结论 |
| --- | --- | --- |
| node_modules/dist/.vite/.venv | 是/否 | 通过/不通过 |
| __pycache__/*.pyc | 是/否 | 通过/不通过 |
| .env/.env.* | 是/否 | 通过/不通过 |
| lingyi_service.db/.pytest-postgresql.xml | 是/否 | 通过/不通过 |
| 02_源码/** | 是/否 | 通过/不通过 |

## 离线 CI Snapshot

- snapshot 路径：/tmp/lingyi-root-ci-snapshot
- snapshot 来源：git ls-files
- 生成物扫描结果：通过/不通过

## 前端离线 CI 结果

- node -v：
- npm -v：
- npm ci：通过/不通过
- npm run verify：通过/不通过
- npm audit --audit-level=high：通过/不通过

## 后端离线回归结果

- 依赖安装：通过/不通过
- production 定向 pytest：通过/不通过
- 全量 pytest：通过/不通过
- unittest discover：通过/不通过
- py_compile：通过/不通过

## 敏感信息检查

- git diff --cached 无 .env/token/password/secret/cookie/私钥：通过/不通过
- 证据文档无 token/password/secret/cookie/私钥：通过/不通过
```

【验收标准】

□ `package-lock.json` 已被 git 跟踪。  
□ 前端 `scripts/**` 已被 git 跟踪。  
□ 前端 `tsconfig*.json`、`vite.config.ts`、`index.html` 已被 git 跟踪。  
□ 前端 `src/**` 已被 git 跟踪。  
□ 后端 `requirements-dev.txt`、`pytest.ini` 已被 git 跟踪。  
□ 后端 `app/**`、`tests/**`、`scripts/**`、`migrations/**` 已被 git 跟踪。  
□ `node_modules/dist/.vite/.venv/__pycache__/*.pyc/.env/lingyi_service.db/.pytest-postgresql.xml` 未被 git 跟踪。  
□ `02_源码/**` 未进入本次首个生产提交。  
□ 离线 snapshot 只由 `git ls-files` 生成。  
□ 离线 snapshot 中 `npm ci && npm run verify && npm audit --audit-level=high` 通过。  
□ 离线 snapshot 中后端 production 定向、全量 pytest、unittest、py_compile 通过。  
□ 离线 CI 模拟通过后才允许 commit。  
□ 证据文档完整记录 staged 文件数、commit SHA、离线 CI 结果。  
□ 未修改前端业务代码。  
□ 未修改后端业务代码。  
□ 未进入 TASK-005/TASK-006。  

【禁止事项】

- 禁止只提交 6 个文件就推送 GitHub。
- 禁止直接在原工作区跑验证后宣称 runner 可复现。
- 禁止跳过 `git ls-files` snapshot 验证。
- 禁止把 `node_modules`、`dist`、`.venv`、`__pycache__`、`.env`、sqlite db、pytest xml 放入 index。
- 禁止把 `02_源码/**` 混入首个生产提交。
- 禁止修改前端 production 业务代码。
- 禁止修改后端业务代码。
- 禁止进入 TASK-005/TASK-006。

【交付回报格式】

完成后按以下格式回复：

```text
TASK-004C8 已完成。

Git 跟踪范围：
- staged 文件数：...
- commit SHA：...
- package-lock/scripts/tsconfig/vite/src 已跟踪：是/否
- backend app/tests/scripts/migrations 已跟踪：是/否
- 生成物和 02_源码 未进入 index：是/否

离线 CI Snapshot：
- snapshot 路径：/tmp/lingyi-root-ci-snapshot
- npm ci：...
- npm run verify：...
- npm audit --audit-level=high：...
- 后端 production 定向 pytest：...
- 后端全量 pytest：...
- unittest discover：...
- py_compile：...

证据文件：
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录/TASK-004C8_根仓库首个提交与离线CI证据.md

未进入范围：
- 未修改前端业务代码
- 未修改后端业务代码
- 未进入 TASK-005/TASK-006
```
