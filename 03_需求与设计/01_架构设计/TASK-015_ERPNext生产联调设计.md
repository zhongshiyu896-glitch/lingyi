# TASK-015 ERPNext 生产联调设计

- 任务编号：TASK-015
- 任务名称：ERPNext 生产联调准备
- 文档版本：V1.0
- 日期：2026-04-17
- 状态：待审计
- 适用范围：TASK-015A 设计冻结、TASK-015B 只读联调、TASK-015C 沙箱写入联调

## 1. 调度边界

本设计在总调度豁免下输出，仅用于冻结 ERPNext 生产联调方案，不代表已经连接生产 ERPNext，不代表 Hosted Runner / Branch Protection 已闭环，不代表允许生产写入。

当前强制边界如下：

1. `TASK-014C` 及之后发布链路继续冻结等待。
2. 管理员平台证据包未到位前，不重复执行 `TASK-014B / TASK-014B2`。
3. 生产环境写入能力不得开放。
4. ERPNext 生产联调必须按只读优先、沙箱写入次之、生产写入最后且另行审批的顺序推进。
5. 所有联调证据必须脱敏，不得记录 Authorization、Cookie、token、password、secret、DSN。

## 2. 目标

TASK-015 的目标是建立 ERPNext 联调的安全证据链，确认系统与 ERPNext 的连接、权限、主数据、只读查询、沙箱写入路径均满足 fail-closed 和审计要求。

阶段目标：

1. TASK-015A：冻结联调方案、账号权限清单、主数据清单、证据模板。
2. TASK-015B：执行只读联调，仅验证 GET / read API，不产生 ERPNext 数据变更。
3. TASK-015C：在沙箱环境验证写入 adapter / outbox，不允许生产写入。

## 3. 前置依赖

| 依赖 | 要求 |
|---|---|
| TASK-007 | 权限与审计统一基座已本地封版，安全/操作审计可用 |
| TASK-008 | ERPNext Fail-Closed Adapter 已本地封版 |
| TASK-009 | Outbox 公共状态机已本地封版 |
| TASK-010 | 前端写入口公共门禁已本地封版 |
| TASK-014A | 管理员平台动作清单与 evidence 模板已输出 |
| TASK-014B/014C | 平台证据仍阻塞，不影响本设计冻结，但阻塞发布链路 |

## 4. 环境矩阵

| 环境 | 用途 | 写入权限 | 允许动作 |
|---|---|---|---|
| 本地开发 | adapter 行为验证 | 禁止生产写入 | mock / 测试替身 |
| ERPNext 沙箱 | 写入演练 | 允许受控沙箱写入 | Stock / Purchase Invoice / Payment 沙箱验证 |
| ERPNext 生产 | 最终只读/生产前验证 | 默认禁止写入 | 只读验证，生产写入需单独任务批准 |

## 5. 账号与权限清单

管理员需准备以下账号或凭据，但不得写入仓库：

| 账号类型 | 权限要求 | 用途 | 证据要求 |
|---|---|---|---|
| 只读 API 用户 | Item/Supplier/Warehouse/Sales Order/Stock Ledger Entry 只读 | TASK-015B | 权限截图或 API 权限清单 |
| 沙箱写入 API 用户 | 沙箱 Stock Entry / Purchase Invoice / Payment Entry 写入 | TASK-015C | 沙箱权限截图与撤销策略 |
| 生产写入 API 用户 | 默认不启用 | 后续独立任务 | 必须单独审计批准 |

## 6. 主数据清单

TASK-015B 前必须确认以下主数据存在且可读：

| 主数据 | 必填字段 | 校验方式 |
|---|---|---|
| Company | name, default_currency | read API |
| Item | item_code, item_name, stock_uom, disabled | read API + docstatus/状态校验 |
| Supplier | supplier_name, disabled | read API |
| Customer | customer_name, disabled | read API |
| Warehouse | warehouse_name, company, disabled | read API + company 归属 |
| Cost Center | company, disabled | read API + company 归属 |
| Account | company, account_type, disabled | read API + company 归属 |
| Sales Order | docstatus, company, customer, items | submitted only |
| Stock Ledger Entry | item_code, warehouse, actual_qty, valuation_rate | required fields fail closed |

## 7. 只读联调范围

TASK-015B 仅允许验证以下只读能力：

1. ERPNext health / connectivity 探测。
2. Item / Supplier / Customer / Warehouse / Account / Cost Center 读取。
3. Sales Order / Delivery Note / Stock Ledger Entry 读取。
4. 权限不足、404、5xx、timeout、malformed response 的 fail-closed 行为。
5. 审计日志、错误信封、脱敏输出。

禁止事项：

1. 禁止 POST / PUT / PATCH / DELETE ERPNext API。
2. 禁止 submit Purchase Invoice。
3. 禁止创建 Payment Entry / GL Entry。
4. 禁止把生产错误伪装成 `200 + 空数据`。

## 8. 沙箱写入联调范围

TASK-015C 仅允许在 ERPNext 沙箱验证：

1. Stock Entry 草稿创建与取消路径。
2. Purchase Invoice 草稿创建，不提交 docstatus=1。
3. Payment Entry 草稿或模拟路径，是否执行需由 TASK-016 进一步冻结。
4. Outbox 先提交本地状态再外调的顺序。
5. 重试、dead、幂等、event_key 稳定性。

## 9. Fail-Closed 要求

所有 ERPNext 联调必须继承 TASK-008 语义：

| 场景 | 期望 |
|---|---|
| timeout | fail closed，返回可审计错误码 |
| 401/403 | fail closed，写安全审计 |
| 404 | 根据业务语义返回 not-found 或 source unavailable，不得伪成功 |
| 5xx | fail closed，可标记 retryable |
| malformed response | fail closed |
| docstatus 缺失/非法 | fail closed |
| 敏感信息 | 必须脱敏 |

## 10. 证据模板

每次联调需回填：

1. 环境名称。
2. 执行时间。
3. 执行人。
4. ERPNext URL 脱敏标识。
5. API 用户权限截图或脱敏清单。
6. 请求类型与 endpoint 分类。
7. 结果：通过 / 不通过。
8. 错误码与审计日志 ID。
9. 敏感信息扫描结论。
10. 是否产生生产写入：必须为否，除非后续生产写入任务单单独放行。

## 11. 审计关注点

1. 是否错误声明生产联调完成。
2. 是否泄露 URL、token、password、DSN。
3. 是否跳过 fail-closed adapter。
4. 是否存在生产写入或 submit 行为。
5. 是否未通过 TASK-016 财务边界就创建 Payment Entry / GL Entry。

## 12. 结论

本设计建议进入 TASK-015A 审计。审计通过后，只允许进入 TASK-015B 只读联调；生产写入继续冻结。
