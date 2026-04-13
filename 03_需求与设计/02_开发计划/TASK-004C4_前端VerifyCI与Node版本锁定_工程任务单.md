# TASK-004C4 前端 Verify CI 与 Node 版本锁定工程任务单

- 任务编号：TASK-004C4
- 模块：生产计划集成 / 前端工程基建 / CI 门禁
- 优先级：P0
- 版本：V1.0
- 更新时间：2026-04-13 20:43 CST
- 作者：技术架构师
- 审计来源：审计意见书第 69 份，TASK-004C3 通过；最优先风险为 `npm run verify` 尚未固化进前端 CI，Node/npm 版本未形成团队级一致约束
- 前置依赖：TASK-004C3 已通过
- 架构依据：`/03_需求与设计/01_架构设计/05_模块设计_生产计划集成.md` V1.8；`ADR-066`
- 任务边界：只做前端 CI 门禁、Node/npm 版本锁定和验证说明；不新增业务功能，不修改后端业务逻辑，不进入 TASK-005/TASK-006

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-004C4
模块：前端 Verify CI 与 Node 版本锁定
优先级：P0（团队级质量门禁固化）
════════════════════════════════════════════════════════════════════════════

【任务目标】
把生产计划前端 `npm run verify` 固化进 GitHub Actions，并锁定 Node/npm 版本，确保契约扫描、反向测试、typecheck、build 在团队 CI 中稳定执行。

【模块概述】
TASK-004C3 已证明前端 production 契约脚本的关键规则具备独立反向测试，但目前这些门禁仍主要依赖本地执行。第 69 份审计指出，如果 `npm run verify` 没进入 CI，或者 Node/npm 版本不一致，团队合并代码时仍可能绕过契约门禁。本任务只补 CI 和版本一致性，不允许改变生产计划业务逻辑。

【涉及文件】

允许新建：
- /Users/hh/Desktop/领意服装管理系统/.github/workflows/frontend-verify.yml
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/.nvmrc
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/.npmrc

允许修改：
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/package.json
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/package-lock.json（仅允许因 `packageManager` 或 npm 版本锁定产生的必要元数据变化）
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/README.md（如不存在可新建，仅写前端验证说明）

禁止修改：
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/production.ts
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/production/**
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/router/**
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/stores/**
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/**
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/**
- 任意 TASK-005/TASK-006 文件

【Node/npm 版本决策】

固定版本：
- Node：22.22.1
- npm：10.9.4

依据：
1. 当前本地前端验证环境为 Node `v22.22.1`、npm `10.9.4`。
2. Vite 7 的本地包声明要求 Node `^20.19.0 || >=22.12.0`，Node 22.22.1 满足要求。
3. CI、`.nvmrc`、`package.json engines`、`packageManager` 必须统一到同一版本，避免版本漂移。

【必须实现】

1. 新增 GitHub Actions workflow：`Frontend Verify Hard Gate`。
2. workflow job 名称固定为：`lingyi-pc-verify`。
3. workflow 必须支持 `workflow_dispatch`。
4. workflow 必须在 `pull_request` 时触发，路径至少覆盖：
   - `06_前端/lingyi-pc/**`
   - `.github/workflows/frontend-verify.yml`
5. workflow 必须在 `push` 到 `main` 时触发，路径至少覆盖：
   - `06_前端/lingyi-pc/**`
   - `.github/workflows/frontend-verify.yml`
6. workflow 必须使用 `actions/setup-node` 安装 Node `22.22.1`。
7. workflow 必须使用 `npm ci`，禁止使用 `npm install`。
8. workflow 必须执行版本断言：
   - `node -v` 必须等于 `v22.22.1`
   - `npm -v` 必须等于 `10.9.4`
9. workflow 必须执行：
   - `npm run verify`
   - `npm audit --audit-level=high`
10. `package.json` 必须新增或确认：
    - `packageManager: "npm@10.9.4"`
    - `engines.node: "22.22.1"`
    - `engines.npm: "10.9.4"`
11. `.nvmrc` 必须写入 `22.22.1`。
12. `.npmrc` 必须至少包含：
    - `engine-strict=true`
    - `package-lock=true`
13. README 必须写清本地执行顺序：
    - `nvm use`
    - `npm ci`
    - `npm run verify`
    - `npm audit --audit-level=high`
14. README 必须写清 required check 建议名称：`Frontend Verify Hard Gate / lingyi-pc-verify`。

【建议 workflow 结构】

```yaml
name: Frontend Verify Hard Gate

on:
  workflow_dispatch:
  pull_request:
    paths:
      - "06_前端/lingyi-pc/**"
      - ".github/workflows/frontend-verify.yml"
  push:
    branches:
      - main
    paths:
      - "06_前端/lingyi-pc/**"
      - ".github/workflows/frontend-verify.yml"

jobs:
  lingyi-pc-verify:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: "06_前端/lingyi-pc"
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: "22.22.1"
          cache: "npm"
          cache-dependency-path: "06_前端/lingyi-pc/package-lock.json"
      - name: Assert Node and npm versions
        run: |
          test "$(node -v)" = "v22.22.1"
          test "$(npm -v)" = "10.9.4"
      - name: Install dependencies
        run: npm ci
      - name: Run frontend verify
        run: npm run verify
      - name: Audit high vulnerabilities
        run: npm audit --audit-level=high
```

【验证命令】

前端必须执行：

```bash
cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc
node -v
npm -v
npm ci
npm run test:production-contracts
npm run check:production-contracts
npm run verify
npm run typecheck
npm run build
npm audit --audit-level=high
```

CI/workflow 静态检查必须执行：

```bash
cd /Users/hh/Desktop/领意服装管理系统
rg "Frontend Verify Hard Gate|lingyi-pc-verify|node-version: \"22.22.1\"|npm run verify|npm audit --audit-level=high|npm ci" .github/workflows/frontend-verify.yml
rg "npm install" .github/workflows/frontend-verify.yml
rg "22.22.1|10.9.4|packageManager|engine-strict" 06_前端/lingyi-pc/package.json 06_前端/lingyi-pc/.nvmrc 06_前端/lingyi-pc/.npmrc
```

production 禁线扫描必须执行：

```bash
cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc
rg "/api/production/internal|work-order-sync/run-once|/api/resource" src/api/production.ts src/views/production src/router src/stores
rg "fetch\\(" src/api/production.ts src/views/production src/router src/stores
rg "Authorization|Cookie|token|secret|password" src/api/production.ts src/views/production src/router src/stores
find . -maxdepth 2 -type d \( -name node_modules -o -name dist \) -print
```

后端回归必须执行，确认本任务未破坏后端：

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest -q tests/test_production_plan.py tests/test_production_work_order_outbox.py tests/test_production_job_card_sync.py
.venv/bin/python -m pytest -q
.venv/bin/python -m unittest discover
.venv/bin/python -m py_compile $(find app tests scripts -name '*.py' -print)
```

【验收标准】

□ `.github/workflows/frontend-verify.yml` 已创建。  
□ workflow 名称为 `Frontend Verify Hard Gate`。  
□ job 名称为 `lingyi-pc-verify`。  
□ workflow 包含 `workflow_dispatch`。  
□ pull_request/push main 均按前端路径触发。  
□ workflow 使用 Node `22.22.1`。  
□ workflow 断言 `node -v = v22.22.1`。  
□ workflow 断言 `npm -v = 10.9.4`。  
□ workflow 使用 `npm ci`，未使用 `npm install`。  
□ workflow 执行 `npm run verify`。  
□ workflow 执行 `npm audit --audit-level=high`。  
□ `.nvmrc` 写入 `22.22.1`。  
□ `.npmrc` 启用 `engine-strict=true`。  
□ `package.json` 写入 `packageManager: npm@10.9.4`。  
□ `package.json` 写入 `engines.node=22.22.1` 与 `engines.npm=10.9.4`。  
□ README 写清本地验证命令和 required check 建议名称。  
□ `npm run verify` 本地通过。  
□ `npm audit --audit-level=high` 本地 0 high vulnerabilities。  
□ `npm run test:production-contracts` 至少 12 个场景通过。  
□ production 禁线扫描无业务文件命中。  
□ 后端 production 定向回归通过。  
□ 后端全量 pytest/unittest/py_compile 通过。  
□ 未修改 production 页面/API/router/store 业务逻辑。  
□ 未修改后端业务逻辑。  
□ 未进入 TASK-005/TASK-006。  

【禁止事项】

- 禁止使用 `npm install` 作为 CI 安装命令。
- 禁止使用浮动 Node 版本，如 `22.x`、`latest`、`lts/*`。
- 禁止删除或弱化 `npm run verify` 中的任何子命令。
- 禁止绕过 `engine-strict=true`。
- 禁止提交 `node_modules`、`dist`、`.vite` 等构建产物。
- 禁止修改生产计划业务页面、业务 API、router、store。
- 禁止修改后端业务代码。
- 禁止进入 TASK-005/TASK-006。

【交付回报格式】

工程师完成后按以下格式回复：

```text
TASK-004C4 已完成。

实现内容：
1. GitHub Actions Frontend Verify Hard Gate：...
2. Node/npm 版本锁定：...
3. README 验证说明：...

涉及文件：
- ...

验证结果：
- node -v：...
- npm -v：...
- npm ci：...
- npm run test:production-contracts：...
- npm run check:production-contracts：...
- npm run verify：...
- npm run typecheck：...
- npm run build：...
- npm audit --audit-level=high：...
- workflow 静态检查：...
- production 禁线扫描：...
- 后端 production 定向 pytest：...
- 后端全量 pytest：...
- unittest discover：...
- py_compile：...

未进入范围：
- 未修改 production 页面/API/router/store 业务逻辑
- 未修改后端业务逻辑
- 未进入 TASK-005/TASK-006

管理员后续动作：
- 在 GitHub 平台将 Frontend Verify Hard Gate / lingyi-pc-verify 配置为主干 required check
```
