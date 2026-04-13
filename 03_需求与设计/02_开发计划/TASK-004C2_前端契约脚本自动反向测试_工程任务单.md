# TASK-004C2 前端契约脚本自动反向测试工程任务单

- 任务编号：TASK-004C2
- 模块：生产计划集成 / 前端工程基建
- 优先级：P0
- 版本：V1.0
- 更新时间：2026-04-13 20:21 CST
- 作者：技术架构师
- 审计来源：审计意见书第 67 份，TASK-004C1 通过；最优先风险为契约脚本目前靠人工反向验证证明有效，缺少脚本级自动反向测试
- 前置依赖：TASK-004C1 已通过
- 架构依据：`/03_需求与设计/01_架构设计/05_模块设计_生产计划集成.md` V1.6；`ADR-064`
- 任务边界：只新增/调整前端契约脚本自动反向测试与 npm 脚本；不新增业务功能，不修改后端业务逻辑，不进入 TASK-005/TASK-006

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-004C2
模块：前端契约脚本自动反向测试
优先级：P0（门禁自证能力）
════════════════════════════════════════════════════════════════════════════

【任务目标】
新增自动反向测试，证明 `check-production-contracts.mjs` 在注入坏样例时会失败，防止后续有人削弱契约门禁但 CI 仍通过。

【模块概述】
TASK-004C1 已把 `src/router`、`src/stores` 纳入 production 契约脚本，并通过审计。但第 67 份审计指出，当前脚本有效性主要靠人工反向验证。契约脚本本身也是代码，必须有自动反向测试：把裸 fetch、内部 worker API、ERPNext 直连、payload company、未清零 worker 按钮等坏样例注入临时 fixture，断言脚本返回非 0，并检查错误信息命中预期。

【涉及文件】

新建：
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-production-contracts.mjs

允许修改：
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-production-contracts.mjs（仅允许增加可测试入口、projectRoot 参数或更稳定输出；不得弱化规则）
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/package.json（新增 `test:production-contracts`，并把 `verify` 串入该测试）

禁止修改：
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/production/ProductionPlanList.vue
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/production/ProductionPlanDetail.vue
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/production.ts
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/router/index.ts
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/stores/permission.ts（除非脚本测试需要稳定注释，不得改权限逻辑）
- 任意后端业务文件
- 任意 TASK-005/TASK-006 文件

【脚本设计要求】

`check-production-contracts.mjs` 必须支持测试脚本对临时 fixture 项目执行，推荐方式二选一：

方案 A：支持参数
```bash
node scripts/check-production-contracts.mjs --project-root /tmp/fixture
```

方案 B：导出函数
```js
export function checkProductionContracts(projectRoot) { ... }
```

要求：
1. 默认不传参数时，行为必须与 TASK-004C1 保持一致。
2. 对真实项目运行仍输出 `Production contract check passed.`。
3. 对坏 fixture 运行必须返回非 0 或抛出可捕获错误。
4. 不得为了测试放宽真实项目扫描规则。

【自动反向测试要求】

`scripts/test-production-contracts.mjs` 必须自动创建临时 fixture，不得修改真实 `src` 文件来做反向测试。

必须覆盖以下失败场景：

1. production API 出现裸 `fetch(`，脚本必须失败。
2. production view 出现 `/api/resource`，脚本必须失败。
3. router 出现 `/api/production/internal/work-order-sync/run-once`，脚本必须失败。
4. store 出现未白名单的 `production:work_order_worker`，脚本必须失败。
5. `ProductionPlanCreatePayload` 出现 `company` 字段，脚本必须失败。
6. `src/api/production.ts` 缺少 `planned_start_date`，脚本必须失败。
7. `src/api/production.ts` 缺少 `fg_warehouse/wip_warehouse/start_date/idempotency_key` 任一字段，脚本必须失败。
8. `ProductionPlanDetail.vue` 出现 `latestJobCardSyncedAt`，脚本必须失败。
9. `permission.ts` 缺少 `work_order_worker: false` 清零逻辑，脚本必须失败。

必须覆盖一个成功场景：

1. 最小合法 fixture 通过契约检查。

测试要求：
1. 每个坏样例必须断言退出码非 0。
2. 每个坏样例必须断言 stderr/stdout 包含预期错误关键词。
3. 临时目录必须在测试结束后清理。
4. 测试不得依赖网络。
5. 测试不得读写真实业务源码，除非是读取脚本本身。
6. 测试必须可在 macOS / Linux 路径下执行。

【package.json 脚本要求】

新增：

```json
{
  "scripts": {
    "test:production-contracts": "node scripts/test-production-contracts.mjs"
  }
}
```

更新 `verify`：

```json
{
  "scripts": {
    "verify": "npm run check:production-contracts && npm run test:production-contracts && npm run typecheck && npm run build"
  }
}
```

不得删除已有：
- `dev`
- `typecheck`
- `build`
- `check:production-contracts`

【验证命令】

必须执行：

```bash
cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc
npm run check:production-contracts
npm run test:production-contracts
npm run typecheck
npm run build
npm run verify
npm audit --audit-level=high
```

后端回归必须执行：

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
rg "/api/production/internal|work-order-sync/run-once|/api/resource" src/api/production.ts src/views/production src/router src/stores
rg "fetch\\(" src/api/production.ts src/views/production src/router src/stores
find . -maxdepth 2 -type d \( -name node_modules -o -name dist \) -print
```

【验收标准】

□ 新增 `scripts/test-production-contracts.mjs`。  
□ `check-production-contracts.mjs` 支持临时 fixture 项目测试，默认真实项目行为不变。  
□ `test:production-contracts` 覆盖至少 9 个失败场景和 1 个成功场景。  
□ 每个失败场景断言退出码非 0。  
□ 每个失败场景断言错误关键词命中。  
□ 测试不修改真实 `src` 文件。  
□ 临时 fixture 测试结束后自动清理。  
□ `npm run check:production-contracts` 通过。  
□ `npm run test:production-contracts` 通过。  
□ `npm run typecheck` 通过。  
□ `npm run build` 通过。  
□ `npm run verify` 通过，且包含 `test:production-contracts`。  
□ `npm audit --audit-level=high` 为 0 high vulnerabilities。  
□ 后端 production 定向回归通过。  
□ 后端全量 pytest/unittest/py_compile 通过。  
□ 未修改生产计划后端业务逻辑。  
□ 未进入 TASK-005/TASK-006。  

【禁止事项】

- 禁止通过弱化 `check-production-contracts.mjs` 规则让反向测试通过。
- 禁止反向测试直接改真实业务源码。
- 禁止把内部 worker API 加入白名单。
- 禁止把 `/api/resource` 加入白名单。
- 禁止删除 planned_start_date、company 禁止、Work Order payload、last_synced_at 既有规则。
- 禁止关闭 typecheck。
- 禁止提交 node_modules 或 dist。
- 禁止修改生产计划后端业务逻辑。
- 禁止进入 TASK-005/TASK-006。

【交付回报格式】

工程师完成后按以下格式回复：

```text
TASK-004C2 已完成。

实现内容：
1. check-production-contracts 可测试化：...
2. 自动反向测试脚本：...
3. package.json 脚本：...
4. 成功/失败场景覆盖：...

涉及文件：
- ...

验证结果：
- npm run check:production-contracts：...
- npm run test:production-contracts：...
- npm run typecheck：...
- npm run build：...
- npm run verify：...
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
TASK-004C1 通过。

【预计工时】
0.5 天

════════════════════════════════════════════════════════════════════════════
