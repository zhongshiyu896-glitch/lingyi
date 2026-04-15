# TASK-005G 款式利润前端只读联调工程任务单

- 模块：款式利润报表 / 前端只读页面联调
- 任务编号：TASK-005G
- 优先级：P0
- 版本：V1.0
- 更新时间：2026-04-14 17:02 CST
- 作者：技术架构师
- 前置审计：审计意见书第 114 份，`TASK-005F11` 通过
- 当前有效 HEAD：`0e124d3368e81df57ddcdf44bc4a8b2c93bd1ab6`
- 架构依据：`/03_需求与设计/01_架构设计/06_模块设计_款式利润报表.md` V3.3；`ADR-109`

## 1. 任务目标

实现款式利润报表前端只读联调：新增利润快照列表页、详情页和前端 API 封装，接入后端现有 `GET /api/reports/style-profit/snapshots` 与 `GET /api/reports/style-profit/snapshots/{snapshot_id}`，并补前端契约门禁，确保不出现裸 `fetch`、ERPNext 直连、创建快照入口或内部敏感动作泄露。

本任务只允许做只读查询。不得开放、隐藏实现或预留可点击的创建/生成利润快照入口。

## 2. 前置条件

1. `TASK-005F11` 审计通过，审计意见书第 114 份。
2. F9/F10/F11 证据链已闭环。
3. 后端款式利润 API 只读接口已存在并通过审计：
   - `GET /api/reports/style-profit/snapshots`
   - `GET /api/reports/style-profit/snapshots/{snapshot_id}`
4. `TASK-006` 未放行，不得进入加工厂对账单开发。

## 3. 允许修改文件

### 3.1 前端业务文件

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/style_profit.ts`（新建）
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/style_profit/StyleProfitSnapshotList.vue`（新建）
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/style_profit/StyleProfitSnapshotDetail.vue`（新建）
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/router/index.ts`（只允许新增两个只读路由）
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/stores/permission.ts`（仅当只读按钮权限需要字段映射时允许最小修改；不得暴露 `style_profit:snapshot_create`）

### 3.2 前端契约门禁文件

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`（新建）
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`（新建）
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/package.json`（只允许新增 style-profit 门禁脚本并接入 `npm run verify`）

### 3.3 测试与文档证据

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005G_款式利润前端只读联调_工程任务单.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005G_款式利润前端只读联调证据.md`（交付时新建）
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
7. 禁止新增 `style_profit:snapshot_create`、`snapshot_create`、`idempotency_key` 到前端 style-profit 文件。
8. 禁止裸 `fetch()`，必须走 `src/api/request.ts` 的统一 `request()`。
9. 禁止前端直连 ERPNext `/api/resource`。
10. 禁止在 UI、router、store 中出现内部 worker 或生产诊断入口。
11. 禁止使用 `git add .` 或 `git add -A`。

## 5. 接口契约

### 5.1 快照列表

| 项目 | 契约 |
| --- | --- |
| 接口 | 查询利润快照列表 |
| 方法 | `GET` |
| 路径 | `/api/reports/style-profit/snapshots` |
| 必填入参 | `company`, `item_code`, `page`, `page_size` |
| 可选入参 | `sales_order`, `from_date`, `to_date`, `snapshot_status` |
| 响应结构 | `{ code, message, data: { items, total, page, page_size } }` |

前端规则：

1. `company` 和 `item_code` 必填，未填写不得调用接口。
2. `page` 默认为 1，`page_size` 默认为 20。
3. 查询前必须确认 `canRead === true`。
4. 无读权限时展示 `el-empty` 或等价空状态，不得发起列表请求。

### 5.2 快照详情

| 项目 | 契约 |
| --- | --- |
| 接口 | 查询利润快照详情 |
| 方法 | `GET` |
| 路径 | `/api/reports/style-profit/snapshots/{snapshot_id}` |
| 入参 | `snapshot_id` |
| 响应结构 | `{ code, message, data: { snapshot, details, source_maps } }` |

前端规则：

1. 详情页只允许根据列表返回的 `id` 跳转。
2. 详情页加载前必须调用 `loadModuleActions('style_profit')` 并确认 `canRead === true`。
3. 无读权限不得调用详情接口。
4. `403`、`401`、`503` 继续由统一 `request()` 转换成用户可读错误。

## 6. 前端页面要求

### 6.1 列表页

文件：`/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/style_profit/StyleProfitSnapshotList.vue`

必须包含：

1. 筛选区：公司、款式、销售订单、开始日期、结束日期、快照状态。
2. 查询按钮：无 `style_profit:read` 权限时禁用。
3. 表格列：快照号、公司、款式、销售订单、期间、收入、实际总成本、利润、利润率、未解析数、状态、公式版本、创建时间。
4. 操作列：只允许“详情”。
5. 未解析数大于 0 时，必须用醒目标签提示“存在未解析来源”。
6. 不得出现“新建快照 / 生成快照 / 创建快照 / 重算利润”等按钮或菜单。

### 6.2 详情页

文件：`/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/style_profit/StyleProfitSnapshotDetail.vue`

必须包含：

1. 快照摘要：快照号、公司、款式、销售订单、期间、收入、实际总成本、标准总成本、利润、利润率、状态、未解析数。
2. 利润明细表：成本类型、来源类型、来源名称、物料/款式、数量、单价、金额、公式、是否未解析、未解析原因。
3. 来源追溯表：source_system、source_doctype、source_status、source_name、source_line_no、qty、unit_rate、amount、mapping_status、include_in_profit、unresolved_reason。
4. 对 `unresolved_count > 0` 的快照展示风险提示：利润快照仍存在未解析来源，请财务复核后使用。
5. 不得出现创建、重算、删除、结算或导出应付相关操作。

## 7. API 封装要求

文件：`/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/style_profit.ts`

必须实现：

1. `fetchStyleProfitSnapshots(params)`：只调用 `GET /api/reports/style-profit/snapshots`。
2. `fetchStyleProfitSnapshotDetail(snapshotId)`：只调用 `GET /api/reports/style-profit/snapshots/{snapshot_id}`。
3. TypeScript 类型必须覆盖：
   - `StyleProfitSnapshotListItem`
   - `StyleProfitSnapshotListData`
   - `StyleProfitSnapshotResult`
   - `StyleProfitDetailItem`
   - `StyleProfitSourceMapItem`
   - `StyleProfitSnapshotDetailData`
4. 必须使用 `request()`。
5. 不允许导出 `createStyleProfitSnapshot` 或任何 POST 创建方法。

## 8. 路由要求

文件：`/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/router/index.ts`

新增路由：

1. `/reports/style-profit`
   - name: `StyleProfitSnapshotList`
   - component: `@/views/style_profit/StyleProfitSnapshotList.vue`
   - meta: `{ module: 'style_profit' }`
2. `/reports/style-profit/detail`
   - name: `StyleProfitSnapshotDetail`
   - component: `@/views/style_profit/StyleProfitSnapshotDetail.vue`
   - meta: `{ module: 'style_profit' }`

## 9. 权限要求

1. 页面进入时调用 `permissionStore.loadModuleActions('style_profit')`。
2. 只使用 `buttonPermissions.read` 控制只读入口。
3. 不新增 `snapshot_create` 按钮权限。
4. 不在前端主动判断角色名称。
5. 不在前端硬编码 `Finance Manager`、`Sales Manager`、`Production Manager` 作为授权依据。
6. 权限来源以 `/api/auth/actions?module=style_profit` 返回结果为准。

## 10. 前端契约门禁

新增脚本：

1. `scripts/check-style-profit-contracts.mjs`
2. `scripts/test-style-profit-contracts.mjs`

`check-style-profit-contracts.mjs` 必须扫描：

1. `src/api/style_profit.ts`
2. `src/views/style_profit/**`
3. `src/router/**`
4. `src/stores/**`

必须拦截：

1. 裸 `fetch(`。
2. `/api/resource`。
3. `style_profit:snapshot_create`。
4. `snapshot_create`。
5. `createStyleProfitSnapshot`。
6. `idempotency_key`。
7. `method: 'POST'` 或 `method: "POST"` 出现在 style-profit API/视图文件。
8. “新建快照 / 创建快照 / 生成快照 / 重算利润”等创建入口文案。
9. 详情页或列表页未调用 `loadModuleActions('style_profit')`。
10. style-profit API 文件未使用统一 `request()`。

`test-style-profit-contracts.mjs` 必须包含反向测试：

1. 合法最小 fixture 通过。
2. 裸 `fetch()` 会失败。
3. `/api/resource` 会失败。
4. `style_profit:snapshot_create` 会失败。
5. `createStyleProfitSnapshot` 会失败。
6. `idempotency_key` 会失败。
7. `method: 'POST'` 会失败。
8. “生成快照”按钮文案会失败。
9. 缺少 `loadModuleActions('style_profit')` 会失败。
10. style-profit API 未使用 `request()` 会失败。

`package.json` 必须新增脚本：

```json
{
  "check:style-profit-contracts": "node scripts/check-style-profit-contracts.mjs",
  "test:style-profit-contracts": "node scripts/test-style-profit-contracts.mjs"
}
```

`npm run verify` 必须包含：

```bash
npm run check:production-contracts && npm run test:production-contracts && npm run check:style-profit-contracts && npm run test:style-profit-contracts && npm run typecheck && npm run build
```

## 11. 必跑验证命令

前端：

```bash
cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc
npm run check:style-profit-contracts
npm run test:style-profit-contracts
npm run verify
npm audit --audit-level=high
```

后端只读回归，不允许改代码：

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest -q tests/test_style_profit_api.py tests/test_style_profit_api_permissions.py tests/test_style_profit_api_audit.py tests/test_style_profit_api_errors.py
.venv/bin/python -m pytest -q
.venv/bin/python -m unittest discover
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
```

静态禁线扫描：

```bash
rg -n "fetch\(|/api/resource|style_profit:snapshot_create|snapshot_create|createStyleProfitSnapshot|idempotency_key|生成快照|创建快照|新建快照|重算利润" \
  /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/style_profit.ts \
  /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/style_profit \
  /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/router \
  /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/stores
```

要求：除契约脚本白名单常量或测试 fixture 外，业务文件不得命中。

## 12. Git 提交要求

1. 禁止 `git add .`。
2. 禁止 `git add -A`。
3. 只允许显式白名单暂存：

```bash
git add -- \
  '06_前端/lingyi-pc/src/api/style_profit.ts' \
  '06_前端/lingyi-pc/src/views/style_profit/StyleProfitSnapshotList.vue' \
  '06_前端/lingyi-pc/src/views/style_profit/StyleProfitSnapshotDetail.vue' \
  '06_前端/lingyi-pc/src/router/index.ts' \
  '06_前端/lingyi-pc/src/stores/permission.ts' \
  '06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs' \
  '06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs' \
  '06_前端/lingyi-pc/package.json' \
  '06_前端/lingyi-pc/package-lock.json' \
  '03_需求与设计/02_开发计划/TASK-005G_款式利润前端只读联调_工程任务单.md' \
  '03_需求与设计/02_开发计划/TASK-005G_款式利润前端只读联调证据.md' \
  '03_需求与设计/02_开发计划/当前 sprint 任务清单.md' \
  '03_需求与设计/01_架构设计/03_技术决策记录.md' \
  '03_需求与设计/01_架构设计/06_模块设计_款式利润报表.md' \
  '03_需求与设计/01_架构设计/架构师会话日志.md' \
  '03_需求与设计/05_审计记录.md' \
  '03_需求与设计/05_审计记录/审计官会话日志.md'
```

如果某个允许文件未修改，`git add --` 报错时可去掉该文件，但不得扩大范围。

提交前必须执行：

```bash
git diff --cached --name-only
```

确认 staged 文件不包含：

1. `07_后端/**`
2. `.github/**`
3. `02_源码/**`
4. `.pytest-postgresql-*.xml`
5. `TASK-006*`
6. 历史未跟踪大目录

建议提交信息：

```bash
git commit -m "feat: add style profit read-only frontend"
```

## 13. 验收标准

- [ ] `src/api/style_profit.ts` 只封装列表和详情 GET 接口。
- [ ] 列表页可按 company、item_code、sales_order、期间和状态查询利润快照。
- [ ] company 和 item_code 为空时，前端不调用列表接口。
- [ ] 无 `style_profit:read` 权限时，列表页不调用接口并展示无权限空状态。
- [ ] 详情页可展示 snapshot、details、source_maps。
- [ ] 无 `style_profit:read` 权限时，详情页不调用详情接口。
- [ ] 页面不出现创建/生成/重算利润快照入口。
- [ ] 前端未出现 `style_profit:snapshot_create`、`snapshot_create`、`idempotency_key`。
- [ ] 前端未出现裸 `fetch()`。
- [ ] 前端未直连 ERPNext `/api/resource`。
- [ ] `npm run check:style-profit-contracts` 通过。
- [ ] `npm run test:style-profit-contracts` 通过，且包含反向测试输出。
- [ ] `npm run verify` 通过。
- [ ] `npm audit --audit-level=high` 为 0 vulnerabilities。
- [ ] 后端 style-profit API 定向回归通过。
- [ ] 全量 pytest、unittest、py_compile 通过。
- [ ] commit 范围不包含后端、workflow、`02_源码`、JUnit 生成物或 TASK-006。

## 14. 交付后证据要求

交付时新建：

`/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005G_款式利润前端只读联调证据.md`

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
13. 明确写出：未开放创建/生成利润快照入口。

## 15. 后续边界

1. `TASK-005G` 审计通过后，才允许评估 `TASK-005H` 是否开放“创建利润快照”前端入口。
2. `TASK-006` 仍需单独架构放行，不得因 `TASK-005G` 自动启动。
3. 如果审计发现前端创建入口、POST 调用或权限泄露，必须先整改，不得继续推进。
