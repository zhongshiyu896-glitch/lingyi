# TASK-004C 前端最小构建与契约校验基建工程任务单

- 任务编号：TASK-004C
- 模块：生产计划集成 / 前端工程基建
- 优先级：P0
- 版本：V1.0
- 更新时间：2026-04-13 19:32 CST
- 作者：技术架构师
- 审计来源：审计意见书第 65 份，TASK-004B1 通过；最高风险为前端无 `package.json`，无法执行 typecheck/build，后续仍可能出现 DTO 漂移
- 前置依赖：TASK-004B1 已通过
- 架构依据：`/03_需求与设计/01_架构设计/05_模块设计_生产计划集成.md` V1.4；`ADR-062`
- 任务边界：只补前端最小构建、TypeScript 校验和 production 契约扫描基建；不新增业务功能，不改后端业务逻辑，不进入 TASK-005/TASK-006

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-004C
模块：前端最小构建与契约校验基建
优先级：P0（上线前质量门禁）
════════════════════════════════════════════════════════════════════════════

【任务目标】
为 `/06_前端/lingyi-pc` 补齐最小 Vue3 + TypeScript 构建基建，使生产计划前端可以执行 `npm run typecheck`、`npm run build` 和 production 契约扫描。

【模块概述】
当前前端目录只有 `src` 下的 API、router、store 和页面文件，没有 `package.json`、`tsconfig`、`vite.config`、`main.ts`、`App.vue`、`index.html` 等构建入口。审计第 65 份指出，这会导致前后端 DTO 漂移只能靠人工静态扫描发现，无法通过 TypeScript 编译自动拦截。本任务只补最小工程基建和契约校验脚本，不做 UI 重构，不新增业务页面，不修改后端主业务逻辑。

【涉及文件】

新建：
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/package.json
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/tsconfig.json
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/tsconfig.node.json
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/vite.config.ts
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/index.html
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/main.ts
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/App.vue
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/env.d.ts
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-production-contracts.mjs

允许修改：
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/production.ts（仅修 typecheck 暴露出的类型问题）
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/production/ProductionPlanList.vue（仅修 typecheck 暴露出的类型问题）
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/production/ProductionPlanDetail.vue（仅修 typecheck 暴露出的类型问题）
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/router/index.ts（仅修构建入口引用问题）
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/stores/permission.ts（仅修 typecheck 暴露出的类型问题）
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/auth.ts（仅允许将类型补齐到可通过 typecheck；是否统一 request 单独拆后续任务）

禁止修改：
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/production_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/production_work_order_worker.py
- 任意生产计划后端业务文件
- 任意 subcontract/workshop/BOM 后端业务文件
- 任意 TASK-005/TASK-006 文件

【package.json 要求】

必须提供以下 scripts：

```json
{
  "scripts": {
    "dev": "vite",
    "typecheck": "vue-tsc --noEmit -p tsconfig.json",
    "build": "vue-tsc --noEmit -p tsconfig.json && vite build",
    "check:production-contracts": "node scripts/check-production-contracts.mjs"
  }
}
```

依赖要求：
1. 必须使用 Vue3、Vue Router、Element Plus、TypeScript、Vite、@vitejs/plugin-vue、vue-tsc。
2. 如项目已有上级 package 管理文件，必须优先对齐上级版本策略；如无上级版本策略，使用当前稳定兼容版本。
3. 允许生成 lockfile，但不得提交 node_modules。
4. package name 建议：`lingyi-pc`。
5. `private` 必须为 true。

【TypeScript / Vite 要求】

`tsconfig.json` 必须支持：
1. Vue SFC。
2. `@/*` 指向 `src/*`。
3. `strict` 原则上开启；如现有页面临时无法全 strict，必须在交付回报中列出放宽项和原因。
4. 不允许通过 `skipLibCheck` 以外的大面积 `any` 或关闭类型检查来绕过错误。

`vite.config.ts` 必须支持：
1. Vue plugin。
2. `@` alias 指向 `/src`。
3. dev server 代理 `/api` 到本地 FastAPI 地址时，地址必须来自环境变量或默认 `http://localhost:8000`，不得写生产 token、Cookie、账号密码。

`src/main.ts` 必须：
1. 创建 Vue app。
2. 注册 router。
3. 注册 Element Plus。
4. 挂载到 `#app`。

`src/App.vue` 必须：
1. 提供最小布局和 `<router-view />`。
2. 不新增业务逻辑。
3. 不直接调用接口。

【契约扫描脚本要求】

新增 `scripts/check-production-contracts.mjs`，至少检查以下规则：

1. `src/api/production.ts` 和 `src/views/production` 不得出现裸 `fetch(`。
2. `src/api/production.ts` 和 `src/views/production` 不得出现 `/api/production/internal`。
3. `src/api/production.ts` 和 `src/views/production` 不得出现 `/api/resource`。
4. `src/views/production` 不得出现 `Authorization`、`Cookie`、`token`、`secret`、`password` 等敏感词硬编码；如状态文本或注释误命中，必须改写。
5. `src/api/production.ts` 必须包含 `planned_start_date`。
6. `src/api/production.ts` 必须包含 `fg_warehouse`、`wip_warehouse`、`start_date`、`idempotency_key`。
7. `src/api/production.ts` 的创建计划 payload 类型不得包含 `company`。
8. `src/stores/permission.ts` 必须包含 `work_order_worker` 清零逻辑。
9. `src/views/production/ProductionPlanDetail.vue` 不得用 Job Card `synced_at` 冒充 Work Order `last_synced_at`。

脚本失败时必须输出清晰错误，并以非 0 退出码结束。

【构建入口要求】

`index.html` 必须：
1. 包含 `<div id="app"></div>`。
2. 引入 `/src/main.ts`。
3. 不包含外部 CDN、token、账号密码。

【业务边界】

1. 不新增生产计划业务接口。
2. 不新增后端字段。
3. 不新增页面功能。
4. 不改生产计划状态机。
5. 不改 Work Order outbox worker。
6. 不改外发、工票、BOM 业务逻辑。
7. 不进入 TASK-005/TASK-006。

【测试与验证要求】

必须执行：

```bash
cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc
npm install
npm run check:production-contracts
npm run typecheck
npm run build
```

后端回归必须执行，确保前端基建没有误改后端：

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest -q tests/test_production_plan.py tests/test_production_work_order_outbox.py tests/test_production_job_card_sync.py
.venv/bin/python -m pytest -q
.venv/bin/python -m unittest discover
.venv/bin/python -m py_compile $(find app tests scripts -name '*.py' -print)
```

静态扫描必须执行：

```bash
cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc
rg "fetch\\(" src/api/production.ts src/views/production
rg "/api/production/internal" src/api/production.ts src/views/production src/router src/stores
rg "/api/resource|Authorization|Cookie|token|secret|password" src/views/production src/api/production.ts
```

【验收标准】

□ 新增 `package.json`，包含 `dev/typecheck/build/check:production-contracts`。  
□ 新增 `tsconfig.json`、`tsconfig.node.json`、`vite.config.ts`。  
□ 新增 `index.html`、`src/main.ts`、`src/App.vue`、`src/env.d.ts`。  
□ 新增 `scripts/check-production-contracts.mjs`。  
□ `npm install` 成功。  
□ `npm run check:production-contracts` 通过。  
□ `npm run typecheck` 通过。  
□ `npm run build` 通过。  
□ production 前端无裸 fetch、无内部 worker 调用、无 ERPNext 直连。  
□ production 创建计划 payload 不包含 company。  
□ production planned_start_date 契约被脚本检查。  
□ 前端构建产物不包含明文 token、Cookie、Secret、完整 DSN。  
□ 后端 production 定向回归通过。  
□ 后端全量 pytest/unittest/py_compile 通过。  
□ 未修改生产计划后端业务逻辑。  
□ 未进入 TASK-005/TASK-006。  

【禁止事项】

- 禁止提交 node_modules。
- 禁止通过关闭 TypeScript 检查来让 typecheck 假通过。
- 禁止删除生产计划页面或 API 来规避类型错误。
- 禁止用 `any` 大面积吞掉 DTO 类型错误。
- 禁止新增内部 worker 页面。
- 禁止前端直连 ERPNext。
- 禁止写入生产 token、Cookie、账号密码、完整 DSN。
- 禁止修改生产计划后端业务逻辑。
- 禁止修改外发结算、工票计薪、BOM 主业务逻辑。
- 禁止进入 TASK-005/TASK-006。

【交付回报格式】

工程师完成后按以下格式回复：

```text
TASK-004C 已完成。

实现内容：
1. 前端 package/build 基建：...
2. TypeScript/Vite 配置：...
3. production 契约扫描脚本：...
4. typecheck/build 修复：...

涉及文件：
- ...

验证结果：
- npm install：...
- npm run check:production-contracts：...
- npm run typecheck：...
- npm run build：...
- production 静态扫描：...
- 后端 production 定向 pytest：...
- 后端全量 pytest：...
- unittest discover：...
- py_compile：...

未进入范围：
- 未修改生产计划后端业务逻辑
- 未修改外发结算
- 未修改工票计薪
- 未直接调用 ERPNext
- 未进入 TASK-005/TASK-006
```

【前置依赖】
TASK-004B1 通过。

【预计工时】
1 天

════════════════════════════════════════════════════════════════════════════
