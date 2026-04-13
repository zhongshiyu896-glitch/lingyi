# TASK-004C3 前端契约反向测试独立用例补齐工程任务单

- 任务编号：TASK-004C3
- 模块：生产计划集成 / 前端工程基建
- 优先级：P0
- 版本：V1.0
- 更新时间：2026-04-13 20:32 CST
- 作者：技术架构师
- 审计来源：审计意见书第 68 份，TASK-004C2 通过；最优先风险为 `work-order-sync/run-once` 和敏感关键字缺少独立 fixture 证明
- 前置依赖：TASK-004C2 已通过
- 架构依据：`/03_需求与设计/01_架构设计/05_模块设计_生产计划集成.md` V1.7；`ADR-065`
- 任务边界：只补前端契约反向测试的独立用例和验证输出；不新增业务功能，不修改后端业务逻辑，不进入 TASK-005/TASK-006

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-004C3
模块：前端契约反向测试独立用例补齐
优先级：P0（门禁规则逐条自证）
════════════════════════════════════════════════════════════════════════════

【任务目标】
补齐 `work-order-sync/run-once` 和敏感关键字的独立反向 fixture，证明每条契约规则单独有效，不被其他规则“顺带失败”掩盖。

【模块概述】
TASK-004C2 已新增 10 个契约脚本反向测试并通过审计，但第 68 份指出两个规则仍缺独立证明：`work-order-sync/run-once` 用例同时命中 `/api/production/internal`，即使 run-once 专项规则被删也可能仍失败；敏感关键字规则尚未有独立 fixture。本任务只补这两个盲点，让契约脚本的每条关键规则都有独立坏样例。

【涉及文件】

允许修改：
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-production-contracts.mjs
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-production-contracts.mjs（仅允许为错误信息更稳定做最小调整；禁止弱化规则）
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/package.json（如需调整脚本名称或输出；不得删除既有脚本）

禁止修改：
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/production.ts
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/production/ProductionPlanList.vue
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/production/ProductionPlanDetail.vue
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/router/index.ts
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/stores/permission.ts
- 任意后端业务文件
- 任意 TASK-005/TASK-006 文件

【必须新增反向用例】

## 用例 1：独立证明 `work-order-sync/run-once` 规则有效

要求：
1. 新增一个 fixture，只包含 `work-order-sync/run-once` 字符串。
2. 该 fixture 不得包含 `/api/production/internal`。
3. 该 fixture 不得包含 `/api/resource`。
4. 该 fixture 不得包含裸 `fetch(`。
5. 该 fixture 必须因 `work-order-sync/run-once` 专项规则失败。
6. 断言退出码非 0。
7. 断言错误输出包含 `work-order-sync/run-once` 或 `禁止出现 work-order-sync/run-once 调用路径`。

示例坏片段可放在 router fixture：

```ts
export const suspiciousPath = 'work-order-sync/run-once'
```

禁止使用：

```ts
'/api/production/internal/work-order-sync/run-once'
```

因为它会同时命中 internal 规则，不能证明 run-once 专项规则独立有效。

## 用例 2：独立证明敏感关键字规则有效

要求：
1. 新增一个 fixture，只包含一个敏感关键字。
2. 敏感关键字建议使用 `Authorization` 或 `password`。
3. 该 fixture 不得包含裸 `fetch(`。
4. 该 fixture 不得包含 `/api/production/internal`。
5. 该 fixture 不得包含 `work-order-sync/run-once`。
6. 该 fixture 不得包含 `/api/resource`。
7. 该 fixture 必须因敏感关键字规则失败。
8. 断言退出码非 0。
9. 断言错误输出包含 `敏感关键字` 或 `禁止业务文件出现敏感关键字硬编码`。

示例坏片段可放在 production view fixture：

```vue
<template><div>Authorization</div></template>
```

【必须保留既有反向用例】

不得删除 TASK-004C2 已有场景：
1. 最小合法 fixture 通过。
2. production API 裸 `fetch(` 失败。
3. production view `/api/resource` 失败。
4. router 内部完整 run-once path 失败。
5. store 非白名单内部动作失败。
6. create payload 含 company 失败。
7. 缺 `planned_start_date` 失败。
8. 缺 Work Order payload 字段失败。
9. detail 使用 `latestJobCardSyncedAt` 失败。
10. permission store 缺内部按钮清零失败。

新增后，`npm run test:production-contracts` 至少应显示 `scenarios=12` 或等效 12 个场景通过。

【输出要求】

`test-production-contracts.mjs` 最终输出必须包含：
1. 总场景数。
2. 成功场景数。
3. 失败场景数或失败用例数量。
4. 每个 case 的名称。

建议格式：

```text
PASS: minimal legal fixture
PASS: api contains bare fetch
...
All production contract fixture tests passed. scenarios=12
```

【验证命令】

前端必须执行：

```bash
cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc
npm run test:production-contracts
npm run check:production-contracts
npm run verify
npm run typecheck
npm run build
npm audit --audit-level=high
```

必须执行静态扫描：

```bash
rg "/api/production/internal|work-order-sync/run-once|/api/resource" src/api/production.ts src/views/production src/router src/stores
rg "fetch\\(" src/api/production.ts src/views/production src/router src/stores
rg "Authorization|Cookie|token|secret|password" src/api/production.ts src/views/production src/router src/stores
find . -maxdepth 2 -type d \( -name node_modules -o -name dist \) -print
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

□ 新增独立 `work-order-sync/run-once` fixture。  
□ 该 fixture 不包含 `/api/production/internal`，仍能失败。  
□ 该 fixture 错误信息命中 run-once 专项规则。  
□ 新增独立敏感关键字 fixture。  
□ 该 fixture 不包含其他禁线，仍能失败。  
□ 该 fixture 错误信息命中敏感关键字规则。  
□ TASK-004C2 既有 10 个场景全部保留。  
□ `npm run test:production-contracts` 至少 12 个场景通过。  
□ `npm run check:production-contracts` 通过。  
□ `npm run verify` 通过。  
□ `npm run typecheck` 通过。  
□ `npm run build` 通过。  
□ `npm audit --audit-level=high` 为 0 high vulnerabilities。  
□ 后端 production 定向回归通过。  
□ 后端全量 pytest/unittest/py_compile 通过。  
□ 未修改真实 production 页面/API/router/store 业务逻辑。  
□ 未修改生产计划后端业务逻辑。  
□ 未进入 TASK-005/TASK-006。  

【禁止事项】

- 禁止用完整 `/api/production/internal/work-order-sync/run-once` 代替 run-once 独立用例。
- 禁止让敏感关键字用例同时命中裸 fetch、internal、run-once 或 /api/resource。
- 禁止删除 TASK-004C2 既有反向测试。
- 禁止弱化 `check-production-contracts.mjs` 规则。
- 禁止把敏感关键字加入业务白名单。
- 禁止提交 node_modules 或 dist。
- 禁止修改生产计划后端业务逻辑。
- 禁止进入 TASK-005/TASK-006。

【交付回报格式】

工程师完成后按以下格式回复：

```text
TASK-004C3 已完成。

实现内容：
1. run-once 独立反向 fixture：...
2. 敏感关键字独立反向 fixture：...
3. 测试输出增强：...

涉及文件：
- ...

验证结果：
- npm run test:production-contracts：...
- npm run check:production-contracts：...
- npm run verify：...
- npm run typecheck：...
- npm run build：...
- npm audit --audit-level=high：...
- 静态扫描：...
- 后端 production 定向 pytest：...
- 后端全量 pytest：...
- unittest discover：...
- py_compile：...

未进入范围：
- 未修改真实 production 页面/API/router/store 业务逻辑
- 未修改生产计划后端业务逻辑
- 未修改外发结算
- 未修改工票计薪
- 未直接调用 ERPNext
- 未进入 TASK-005/TASK-006
```

【前置依赖】
TASK-004C2 通过。

【预计工时】
0.5 天

════════════════════════════════════════════════════════════════════════════
