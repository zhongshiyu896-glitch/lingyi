# TASK-005H 款式利润全局只读边界门禁收口工程任务单

- 模块：款式利润报表 / 前端只读边界二次收口
- 任务编号：TASK-005H
- 优先级：P0
- 版本：V1.0
- 更新时间：2026-04-14 17:22 CST
- 作者：技术架构师
- 前置审计：审计意见书第 115 份，`TASK-005G` 通过
- 当前有效 HEAD：`154adc0d4e85df9a407c7f11bb1d3d4f25817d45`
- 架构依据：`/03_需求与设计/01_架构设计/06_模块设计_款式利润报表.md` V3.4；`ADR-110`

## 1. 任务目标

在 TASK-005G 已完成款式利润前端只读列表/详情的基础上，扩大前端契约扫描范围，防止 `style_profit:snapshot_create`、创建/生成/重算快照入口、裸 `fetch()`、ERPNext 直连从全局导航、公共组件、其他页面或 store 绕过只读边界。同时补齐详情页 `canRead` 前置反向测试，并治理普通财务视图中的内部审计字段展示。

本任务仍然只做前端只读边界收口，不开放利润快照创建入口，不进入 TASK-006。

## 2. 前置条件

1. `TASK-005G` 审计通过，审计意见书第 115 份。
2. 当前 HEAD 为 `154adc0d4e85df9a407c7f11bb1d3d4f25817d45`。
3. 前端只读接口已通过审计：
   - `GET /api/reports/style-profit/snapshots`
   - `GET /api/reports/style-profit/snapshots/{snapshot_id}`
4. `TASK-006` 未放行，不得进入加工厂对账单开发。

## 3. 允许修改文件

### 3.1 前端文件

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/style_profit/StyleProfitSnapshotDetail.vue`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/style_profit/StyleProfitSnapshotList.vue`（仅限配合门禁或权限提示小改）
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/router/index.ts`（仅限确认只读路由，不得新增写入口）
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/stores/permission.ts`（仅限 denylist/只读权限清零收口，不得暴露创建权限）
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/package.json`（仅当 verify 脚本需要调整时允许）
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/package-lock.json`（仅当 package.json 触发锁文件变化时允许）

### 3.2 文档证据

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005H_款式利润全局只读边界门禁收口_工程任务单.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005H_款式利润全局只读边界门禁收口证据.md`（交付时新建）
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/当前 sprint 任务清单.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/03_技术决策记录.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/06_模块设计_款式利润报表.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/架构师会话日志.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录/审计官会话日志.md`

## 4. 禁止修改文件与行为

1. 禁止修改 `/Users/hh/Desktop/领意服装管理系统/07_后端/**`。
2. 禁止修改 `/Users/hh/Desktop/领意服装管理系统/.github/**`。
3. 禁止修改 `/Users/hh/Desktop/领意服装管理系统/02_源码/**`。
4. 禁止创建或修改任何 `TASK-006*` 文件。
5. 禁止提交 `.pytest-postgresql-*.xml`。
6. 禁止新增 `POST /api/reports/style-profit/snapshots` 的前端调用。
7. 禁止新增、展示或映射 `style_profit:snapshot_create`。
8. 禁止新增 `snapshot_create`、`idempotency_key`、`createStyleProfitSnapshot`。
9. 禁止出现“新建快照 / 创建快照 / 生成快照 / 重算利润”等可被业务理解为写操作的文案。
10. 禁止裸 `fetch()`。
11. 禁止前端直连 ERPNext `/api/resource`。
12. 禁止使用 `git add .` 或 `git add -A`。

## 5. 必做整改

### 5.1 扩大 style-profit 契约扫描范围

`check-style-profit-contracts.mjs` 当前只扫描 style-profit API、style-profit 页面和 router。TASK-005H 必须扩展到：

1. `src/api/**`
2. `src/views/**`
3. `src/router/**`
4. `src/stores/**`
5. `src/App.vue`
6. `src/main.ts`
7. 后续若存在 `src/components/**`，必须自动纳入扫描。

扫描脚本必须支持目录不存在时跳过可选目录，但不得跳过已存在的核心目录。

### 5.2 白名单规则

允许白名单仅限：

1. `src/api/request.ts` 中的统一 `fetch()`。
2. `src/api/request.ts` 中的 `Authorization` 组装。
3. `src/stores/permission.ts` 中内部 denylist 常量，但不得包含 `style_profit:snapshot_create`。
4. 契约脚本和反向测试 fixture 中的违规字符串。

不得把业务页面、路由、App、main、store 普通逻辑加入宽泛白名单。

### 5.3 必须拦截的全局回潮

1. 任意前端业务文件出现裸 `fetch(`。
2. 任意前端业务文件出现 `/api/resource`。
3. 任意前端业务文件出现 `style_profit:snapshot_create`。
4. 任意前端业务文件出现 `snapshot_create`。
5. 任意前端业务文件出现 `createStyleProfitSnapshot`。
6. 任意前端业务文件出现 `idempotency_key`。
7. 任意 style-profit API/页面出现 `method: 'POST'` 或 `method: "POST"`。
8. 任意页面、App、router、store 出现“新建快照 / 创建快照 / 生成快照 / 重算利润”。
9. style-profit 列表页缺少 `loadModuleActions('style_profit')`。
10. style-profit 详情页缺少 `loadModuleActions('style_profit')`。
11. style-profit 详情页缺少 `canRead` 前置阻断。

### 5.4 补齐反向测试

`test-style-profit-contracts.mjs` 必须新增或补齐以下反向测试：

1. `App.vue` 暴露“生成利润快照”按钮时失败。
2. `src/views/bom/BomList.vue` 暴露 `style_profit:snapshot_create` 时失败。
3. `src/stores/permission.ts` 映射 `snapshot_create: true` 时失败。
4. `src/router/index.ts` 新增 `/reports/style-profit/create` 时失败。
5. `src/views/style_profit/StyleProfitSnapshotDetail.vue` 缺少 `canRead` 前置阻断时失败。
6. `src/api/style_profit.ts` 出现 `method: 'POST'` 时失败。
7. `src/api/request.ts` 中统一 `fetch()` 保持允许。
8. 合法最小 fixture 通过。

### 5.5 内部审计字段展示治理

`StyleProfitSnapshotDetail.vue` 如展示 `request_hash`、`idempotent_replay`、内部 payload hash 或技术调试字段，必须满足以下任一方案：

1. 移入“审计信息”折叠区，并标注文案“仅供审计复核”。
2. 或从普通财务详情页移除。

不得把内部 hash 字段作为普通业务摘要核心字段展示。

## 6. 必跑验证命令

前端：

```bash
cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc
npm run check:style-profit-contracts
npm run test:style-profit-contracts
npm run verify
npm audit --audit-level=high
```

后端只读回归，不允许改后端代码：

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest -q tests/test_style_profit_api.py tests/test_style_profit_api_permissions.py tests/test_style_profit_api_audit.py tests/test_style_profit_api_errors.py
.venv/bin/python -m pytest -q
.venv/bin/python -m unittest discover
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
```

静态禁线扫描：

```bash
rg -n "style_profit:snapshot_create|snapshot_create|createStyleProfitSnapshot|idempotency_key|生成利润快照|创建利润快照|新建快照|重算利润|/api/resource" \
  /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src
```

要求：除契约脚本 fixture 不在 `src` 内，因此 `src` 业务扫描不得命中以上禁线。

## 7. Git 提交要求

1. 禁止 `git add .`。
2. 禁止 `git add -A`。
3. 只允许显式白名单暂存。
4. 提交前必须执行：

```bash
git diff --cached --name-only
```

5. staged 文件不得包含：
   - `07_后端/**`
   - `.github/**`
   - `02_源码/**`
   - `.pytest-postgresql-*.xml`
   - `TASK-006*`
   - 历史未跟踪大目录

建议提交信息：

```bash
git commit -m "test: harden style profit read-only frontend gate"
```

## 8. 验收标准

- [ ] style-profit 契约扫描覆盖 `src/api/**`、`src/views/**`、`src/router/**`、`src/stores/**`、`src/App.vue`、`src/main.ts`。
- [ ] 全局前端业务文件不得出现 `style_profit:snapshot_create`。
- [ ] 全局前端业务文件不得出现 `snapshot_create`。
- [ ] 全局前端业务文件不得出现 `idempotency_key`。
- [ ] 全局前端业务文件不得出现创建/生成/重算利润快照入口文案。
- [ ] 详情页缺少 `canRead` 前置阻断时，反向测试失败。
- [ ] `src/api/request.ts` 中统一 `fetch()` 白名单仍可通过。
- [ ] 内部审计字段已移入“审计信息”折叠区或从普通业务摘要移除。
- [ ] `npm run check:style-profit-contracts` 通过。
- [ ] `npm run test:style-profit-contracts` 通过。
- [ ] `npm run verify` 通过。
- [ ] `npm audit --audit-level=high` 为 0 vulnerabilities。
- [ ] 后端 style-profit API 定向回归通过。
- [ ] 全量 pytest、unittest、py_compile 通过。
- [ ] commit 范围不包含后端、workflow、`02_源码`、JUnit 生成物或 TASK-006。

## 9. 交付证据要求

交付时新建：

`/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005H_款式利润全局只读边界门禁收口证据.md`

必须记录：

1. 提交前 HEAD。
2. 提交后 HEAD。
3. commit message。
4. `git diff --cached --name-only` 提交前清单。
5. `git show --stat --oneline --name-only HEAD`。
6. `npm run check:style-profit-contracts` 结果。
7. `npm run test:style-profit-contracts` 结果。
8. `npm run verify` 结果。
9. `npm audit --audit-level=high` 结果。
10. 后端定向与全量回归结果。
11. 静态禁线扫描结果。
12. 明确写出：未进入 TASK-006。
13. 明确写出：未开放创建/生成/重算利润快照入口。

## 10. 后续边界

1. `TASK-005H` 审计通过后，才允许评估 `TASK-005I` 是否进入只读 UI 体验优化或创建入口设计。
2. 创建入口仍需单独任务单、单独审计，不得由 TASK-005H 自动开放。
3. `TASK-006` 仍需单独架构放行，不得由 TASK-005H 自动启动。
