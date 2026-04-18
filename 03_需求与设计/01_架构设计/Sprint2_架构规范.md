# Sprint 2 架构规范

- 规范版本：V1.0
- 更新时间：2026-04-16 08:26
- 作者：技术架构师
- 适用范围：Sprint 2 所有 P1 模块、后续新增前端页面、ERPNext 集成、outbox/worker、验收门禁
- 前置依据：Sprint 1 审计记录第 3 ~ 173 份、TASK-S-002 验收工具包、TASK-REL-001~003 本地封版链路

## 一、强制原则

1. 先冻结设计，再写代码。
2. 后端权限是最终权威，前端权限只做展示控制。
3. ERPNext 或权限源不可用时必须 fail closed。
4. 跨系统写入必须走 outbox，不得在本地业务事务中直接调用 ERPNext。
5. 前端新增模块必须有契约门禁和反向 fixture。
6. 审计证据必须与代码同阶段产出，不得封版后补口径。
7. 本地封版不得描述为生产发布完成。

## 二、前端写入口门禁统一方案

### 2.1 适用范围

所有 Vue3 前端模块，包括但不限于：销售、库存、质量、权限、仪表盘、报表、对账、生产、外发、工票。

### 2.2 模块门禁声明

每个模块必须声明一份前端契约文件或脚本配置，至少包含：

| 字段 | 要求 |
| --- | --- |
| module_key | 模块标识，如 `factory_statement`、`style_profit` |
| allowed_api_methods | 允许调用的 API 方法名 |
| allowed_http_methods | 允许 HTTP 方法，如只读模块仅 `GET` |
| forbidden_paths | 禁止路径，如 `/internal/`、`run-once`、ERPNext `/api/resource` |
| forbidden_actions | 禁止动作词，如 create/generate/recalculate/submit/delete/confirm/payable 等 |
| permission_actions | 允许权限动作，如 `xxx:read`、`xxx:create` |
| route_scope | 扫描 `views/components/router/stores/api/utils/scripts` 的范围 |
| fixtures | 正向 fixture 与反向 fixture 路径 |

### 2.3 默认禁止项

以下写入口在所有模块默认禁止，除非任务单和审计明确放行：

1. 裸 `fetch()`、未接入统一 API client 的 `axios`。
2. 前端直连 ERPNext `/api/resource`。
3. 调用 internal worker、`run-once`、diagnostic、dry-run 管理接口。
4. 未授权 POST/PUT/PATCH/DELETE。
5. 未经后端确认的按钮权限自造逻辑。
6. 动态 action key：`[ACTION_KEY]`、`[actionMap.onClick]`、`[getActionKey()]`。
7. runtime mutator：`Object.defineProperty`、`Object.assign`、`Reflect.set`、动态属性注入、别名/解构/命名空间/`call/apply/bind` 等价调用。
8. 运行时代码生成：`eval`、`Function`、`new Function`、constructor 链、字符串 `setTimeout/setInterval`。
9. 动态模块加载：`import(data:)`、Blob URL import、Worker/SharedWorker 的 data/blob/http(s)/unknown URL。
10. CSV/XLSX 导出未防公式注入。

### 2.4 AST 优先，不再正则堆叠

1. 新模块门禁必须优先使用 TypeScript AST。
2. 正则只允许作为补充扫描，不允许作为唯一判断。
3. 对无法静态证明安全的动态写入口，默认 fail closed。
4. 每个门禁新增规则必须有反向 fixture。
5. 反向 fixture 必须覆盖 direct、alias、destructure、call、apply、bind、computed key、runtime mutation、跨行、嵌套对象。

### 2.5 前端验收命令

每个模块必须接入：

```bash
npm run check:<module>-contracts
npm run test:<module>-contracts
npm run verify
npm audit --audit-level=high
```

`npm run verify` 必须包含所有模块契约门禁，不允许只跑当前模块。

## 三、ERPNext 集成 Fail-Closed 规范

### 3.1 适用对象

- Supplier
- Account
- Cost Center
- Item
- Sales Order
- Purchase Order
- Delivery Note
- Stock Entry
- Stock Ledger Entry
- Work Order
- Job Card
- Purchase Invoice
- User Permission
- Role / Permission 聚合接口

### 3.2 统一判断

| 场景 | 处理 |
| --- | --- |
| ERPNext 连接失败 | 返回 `503 + ERPNEXT_SERVICE_UNAVAILABLE` 或模块专用外部源不可用错误 |
| 权限源连接失败 | 返回 `503 + PERMISSION_SOURCE_UNAVAILABLE` |
| ERPNext 返回 5xx/超时 | fail closed，不落本地成功事实 |
| ERPNext 明确返回 404 | 按业务不存在处理，可返回 404/422，不得当作外部源不可用 |
| ERPNext 返回空 User Permission | 必须区分“明确无限制”和“查询失败” |
| 缺 `docstatus/status` | 默认 fail closed，不纳入业务计算 |
| draft/cancelled 文档 | 不得视为业务成功 |
| 本地 commit 失败 | 不得调用 ERPNext |
| ERPNext 调用成功、本地回写失败 | outbox 必须保留可重试/可追踪状态，不得吞错 |

### 3.3 权限与操作者

1. 所有写接口必须接入当前用户，不得使用 `operator="system"` 伪造操作者。
2. 服务账号必须有配置化最小权限策略，不得全模块全资源放开。
3. 资源权限必须校验 `company`、`item_code`、`supplier`、`warehouse`、`work_order` 等业务归属。
4. Company-only 权限不得自动推导为全 Item 权限。
5. 权限拒绝、权限源不可用、资源越权必须写安全审计。

### 3.4 错误信封

统一响应格式：

```json
{ "code": "ERROR_CODE", "message": "可读错误", "data": null }
```

禁止：

1. 将未知异常伪装成审计写入失败。
2. 将数据库写失败伪装成内部未知错误。
3. 将外部源不可用伪装成“无数据”。
4. 向客户端返回 SQL、Token、Cookie、Authorization、密码、DSN、Secret。

## 四、Outbox 状态机安全规范

### 4.1 标准字段

Outbox 表建议包含：

| 字段 | 说明 |
| --- | --- |
| id | 主键 |
| event_key | 稳定业务事件键，不含 idempotency_key/request_id/created_at/operator |
| aggregate_type | 业务聚合类型 |
| aggregate_id | 业务聚合 ID |
| action | 外部动作，如 `stock_issue`、`stock_receipt`、`purchase_invoice_draft` |
| status | `pending/processing/succeeded/failed/dead/cancelled` |
| payload_json | 最终外部请求 payload |
| payload_hash | 基于最终 payload 的 hash |
| request_hash | 幂等请求 hash |
| idempotency_key | 客户端幂等键 |
| attempts | 重试次数 |
| next_retry_at | 下次重试时间 |
| locked_by | worker 标识 |
| locked_until | lease 过期时间 |
| external_docname | ERPNext 文档名 |
| external_docstatus | ERPNext docstatus |
| error_code/error_message | 脱敏错误 |
| created_by/created_at/updated_at | 审计字段 |

### 4.2 event_key 规则

1. event_key 必须来自稳定业务口径。
2. 禁止包含 idempotency_key、request_id、outbox_id、created_at、operator。
3. 长字段必须先 hash，再拼短前缀，不允许拼接后截断 hash。
4. 同一业务事实重复提交必须命中同一 event_key。
5. active 唯一约束必须覆盖 pending/processing/succeeded 的业务防重。

### 4.3 claim_due 原子规则

1. 查询 due 数据时必须限制：`pending/failed due` 或 `processing lease expired`。
2. 第二阶段 UPDATE 必须重复校验同样 due/lease 条件。
3. PostgreSQL 优先使用 `FOR UPDATE SKIP LOCKED`。
4. claim 本地事务必须先提交，再调用 ERPNext。
5. stale id 不得抢占未过期 processing lease。

### 4.4 Worker 调用前置校验

worker 每次调用 ERPNext 前必须重新读取并校验：

1. aggregate 当前状态仍允许处理。
2. 金额/数量/payload_hash 未漂移。
3. 用户或服务账号仍有动作权限与资源权限。
4. ERPNext find-by-event-key 返回的文档必须校验 docstatus。
5. ERPNext draft 不得标记本地 succeeded，必须 submit 或继续处理为非成功状态。
6. aggregate 已 cancel 时不得调用 ERPNext。

### 4.5 dry-run / diagnostic

1. 生产环境 dry-run 默认禁用。
2. dry-run 禁用判断必须早于外部权限源和资源查询。
3. dry-run 成功/失败都要写操作审计或安全审计。
4. diagnostic 不得每轮重复放大审计日志，必须节流/去重。
5. internal worker API 不得暴露给普通业务角色。

### 4.6 必测矩阵

每个 outbox 模块必须覆盖：

- 同幂等键同 hash replay。
- 同幂等键异 hash conflict。
- 不同幂等键同业务事实 active 防重。
- event_key 不含易变字段。
- claim_due stale id 不抢占 lease。
- worker 调 ERPNext 前 aggregate 状态变化。
- ERPNext draft/cancelled/docstatus 缺失。
- 本地 commit 失败不调用 ERPNext。
- 外部调用失败进入 failed/dead。
- dry-run 不写外部系统。
- diagnostic 节流。
- PostgreSQL non-skip 并发证据。

## 五、TASK-S-002 验收工具规范

1. Sprint 2 所有模块必须接入本地冒烟回归或明确说明不适用。
2. 工具 case 必须扩展到 TASK-005/TASK-006 已封版接口，并新增 P1 模块 case。
3. 13 个接口 case 保留为基础 smoke，不得替代高危负向测试。
4. 每个模块至少提供：主路径 smoke、权限失败、资源越权、外部源不可用、幂等 replay/conflict。
5. 报告必须输出 `report.json/report.md`，Authorization/Token 必须脱敏。

## 六、任务卡前置审计模板

所有 Sprint 2 工程任务卡必须包含以下固定小节：

```text
【前置审计要求】
1. 架构文档已冻结字段、状态机、权限动作、ERPNext 边界。
2. API DTO 已列出必填字段和响应字段。
3. 数据库唯一约束、索引和迁移策略已列出。
4. ERPNext 依赖已列 fail-closed 错误码。
5. 如涉及 outbox，已引用 Sprint2 Outbox 状态机规范。
6. 如涉及前端，已引用 Sprint2 前端写入口门禁规范。
7. 如涉及并发，已说明 PostgreSQL non-skip 证据要求。
8. 如涉及导出，已说明 CSV/XLSX 公式注入防护。
9. 任务单通过审计后才允许写代码。
```

## 七、禁止事项

1. 禁止绕过任务单直接实现 P1 模块。
2. 禁止把本地封版描述为生产发布。
3. 禁止无审计地修改 `.github`、`02_源码` 或平台门禁。
4. 禁止业务事务内调用 ERPNext 写接口。
5. 禁止前端调用 internal worker 或 ERPNext `/api/resource`。
6. 禁止提交运行产物、JUnit XML、dist、node_modules、.pytest_cache。
7. 禁止用静态角色映射替代生产权限源，除非任务单明确限定为开发临时方案。
