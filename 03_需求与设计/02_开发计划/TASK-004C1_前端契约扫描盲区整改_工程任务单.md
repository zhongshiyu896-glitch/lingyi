# TASK-004C1 前端契约扫描盲区整改工程任务单

- 任务编号：TASK-004C1
- 模块：生产计划集成 / 前端工程基建
- 优先级：P0
- 版本：V1.0
- 更新时间：2026-04-13 20:08 CST
- 作者：技术架构师
- 审计来源：审计意见书第 66 份，TASK-004C 通过；最优先风险为 `check-production-contracts.mjs` 未把 `src/router`、`src/stores` 纳入同一脚本门禁
- 前置依赖：TASK-004C 已通过
- 架构依据：`/03_需求与设计/01_架构设计/05_模块设计_生产计划集成.md` V1.5；`ADR-063`
- 任务边界：只扩展前端 production 契约扫描脚本和验证范围；不新增业务功能，不修改后端业务逻辑，不进入 TASK-005/TASK-006

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-004C1
模块：前端契约扫描盲区整改
优先级：P0（质量门禁补强）
════════════════════════════════════════════════════════════════════════════

【任务目标】
扩展 `scripts/check-production-contracts.mjs`，把 `src/router`、`src/stores` 和 `src/api/production.ts` 纳入同一禁线扫描，防止内部 worker 入口、ERPNext 直连、敏感关键字从非页面文件回潮。

【模块概述】
TASK-004C 已补齐前端 `package.json/typecheck/build/check:production-contracts`，并通过审计。但审计指出契约脚本当前主要扫描 production API 和 production views，router/stores 依赖人工扫描；后续如果有人在路由、权限 store 中新增内部 worker 入口，脚本可能拦不住。本任务只补脚本扫描范围和对应反向测试，不改页面业务。

【涉及文件】

允许修改：
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-production-contracts.mjs
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/package.json（仅允许新增 verify 脚本，如需要）
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/stores/permission.ts（仅允许为契约脚本识别增加稳定注释或常量名，不改权限逻辑）

如需要新增测试脚本：
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-production-contracts.mjs

禁止修改：
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/production/ProductionPlanList.vue（除非只是删除误触发敏感词注释）
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/production/ProductionPlanDetail.vue（除非只是删除误触发敏感词注释）
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/production.ts（除非只是删除误触发敏感词注释）
- 任意后端业务文件
- 任意 TASK-005/TASK-006 文件

【扫描范围要求】

`check-production-contracts.mjs` 必须纳入以下路径：

1. `src/api/production.ts`
2. `src/views/production/**/*`
3. `src/router/**/*`
4. `src/stores/**/*`

如后续新增 `src/components/production`，建议一并纳入，但本任务不强制。

【必须拦截规则】

对 `src/api/production.ts`、`src/views/production/**/*`、`src/router/**/*`、`src/stores/**/*` 均必须拦截：

1. 裸 `fetch(`。
2. `/api/production/internal`。
3. `/api/resource`。
4. `Authorization`。
5. `Cookie`。
6. `token`。
7. `secret`。
8. `password`。
9. `work-order-sync/run-once`。
10. `production:work_order_worker` 出现在 UI 路由或视图中。

白名单要求：
1. `src/stores/permission.ts` 可以出现内部动作常量或 denylist，但必须同时存在强制清零逻辑。
2. 如敏感关键词只出现在 `check-production-contracts.mjs` 自身规则中，不应导致脚本失败。
3. 白名单必须集中定义，并附注释说明原因；禁止散落多个 if 绕过。

【必须保留规则】

原 TASK-004C 已有规则不得删除：

1. `src/api/production.ts` 必须包含 `planned_start_date`。
2. `src/api/production.ts` 必须包含 `fg_warehouse/wip_warehouse/start_date/idempotency_key`。
3. `ProductionPlanCreatePayload` 不得包含 `company`。
4. `permission store` 必须包含内部按钮权限清零逻辑。
5. `ProductionPlanDetail.vue` 不得用 Job Card `synced_at` 冒充 Work Order `last_synced_at`。

【建议新增 verify 脚本】

如改 `package.json`，建议新增：

```json
{
  "scripts": {
    "verify": "npm run check:production-contracts && npm run typecheck && npm run build"
  }
}
```

不得删除已有：
- `dev`
- `typecheck`
- `build`
- `check:production-contracts`

【反向测试要求】

如新增 `scripts/test-production-contracts.mjs`，必须覆盖以下临时 fixture 或 mock 逻辑：

1. router 中出现 `/api/production/internal/work-order-sync/run-once` 时脚本失败。
2. store 中出现未清零的 `work_order_worker` 时脚本失败。
3. production API 出现裸 `fetch(` 时脚本失败。
4. production view 出现 `/api/resource` 时脚本失败。
5. `ProductionPlanCreatePayload` 出现 `company` 字段时脚本失败。

如不新增反向测试脚本，工程师必须在交付回报中列出人工反向验证方式和结果。

【验证命令】

必须执行：

```bash
cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc
npm run check:production-contracts
npm run typecheck
npm run build
npm audit --audit-level=high
```

如新增 verify：

```bash
npm run verify
```

必须执行静态扫描：

```bash
rg "/api/production/internal|work-order-sync/run-once|/api/resource" src/api/production.ts src/views/production src/router src/stores
rg "fetch\\(" src/api/production.ts src/views/production src/router src/stores
```

后端回归必须执行：

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest -q tests/test_production_plan.py tests/test_production_work_order_outbox.py tests/test_production_job_card_sync.py
.venv/bin/python -m pytest -q
.venv/bin/python -m unittest discover
.venv/bin/python -m py_compile $(find app tests scripts -name '*.py' -print)
```

【验收标准】

□ `check-production-contracts.mjs` 扫描范围包含 `src/router`。  
□ `check-production-contracts.mjs` 扫描范围包含 `src/stores`。  
□ 脚本可拦截 router/stores 中的 `/api/production/internal`。  
□ 脚本可拦截 router/stores 中的 `/api/resource`。  
□ 脚本可拦截 router/stores 中的裸 `fetch(`。  
□ 脚本可拦截非白名单敏感关键字。  
□ permission store 内部按钮清零逻辑仍被检查。  
□ 原 planned_start_date、Work Order payload、company 禁止、last_synced_at 规则仍保留。  
□ `npm run check:production-contracts` 通过。  
□ `npm run typecheck` 通过。  
□ `npm run build` 通过。  
□ `npm audit --audit-level=high` 为 0 high vulnerabilities。  
□ 后端 production 定向回归通过。  
□ 后端全量 pytest/unittest/py_compile 通过。  
□ 未修改生产计划后端业务逻辑。  
□ 未进入 TASK-005/TASK-006。  

【禁止事项】

- 禁止为了通过扫描而删除既有 production 页面功能。
- 禁止把内部 worker API 加入白名单。
- 禁止把 `/api/resource` 加入白名单。
- 禁止白名单 `Authorization/Cookie/token/secret/password` 在业务文件中的出现。
- 禁止关闭 typecheck。
- 禁止提交 node_modules 或 dist。
- 禁止修改生产计划后端业务逻辑。
- 禁止进入 TASK-005/TASK-006。

【交付回报格式】

工程师完成后按以下格式回复：

```text
TASK-004C1 已完成。

实现内容：
1. 契约脚本扫描范围扩展：...
2. router/stores 禁线规则：...
3. 白名单策略：...
4. 反向测试/人工反向验证：...

涉及文件：
- ...

验证结果：
- npm run check:production-contracts：...
- npm run typecheck：...
- npm run build：...
- npm audit --audit-level=high：...
- 静态扫描：...
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
TASK-004C 通过。

【预计工时】
0.5 天

════════════════════════════════════════════════════════════════════════════
