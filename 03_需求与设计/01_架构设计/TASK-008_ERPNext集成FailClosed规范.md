# TASK-008 ERPNext 集成 Fail-Closed 规范

- 模块：ERPNext 集成 Fail-Closed Adapter
- 版本：V1.0（设计冻结）
- 更新时间：2026-04-16
- 前置：TASK-007 全链路完成（权限与审计统一基座）
- 适用范围：TASK-002 ~ TASK-006 既有 ERPNext 读写链路，以及 Sprint 2 后续模块

## 一、目标与边界

### 1.1 目标
统一 ERPNext 适配层（Adapter）在读取、写入、状态判定、错误语义、安全审计、返回契约方面的行为，确保所有跨系统交互默认 fail closed。

### 1.2 本文档边界
1. 只冻结设计规范，不包含业务代码实现。
2. 只定义 Adapter 层契约与行为，不改业务模块状态机。
3. Purchase Invoice 在本阶段只允许 draft 创建语义，不允许 submit/payment/GL。

---

## 二、现状梳理（当前 Adapter 职责与风险）

| Adapter | 当前职责 | 主要优点 | 当前风险点（需在 008B 收口） |
| --- | --- | --- | --- |
| `erpnext_permission_adapter.py` | User roles、User Permission、workflow transitions 读取；item/company/supplier/warehouse 判定 | `get_user_permissions` 支持 strict 模式并在异常时抛 `PermissionSourceUnavailable` | `get_user_roles` 在非 strict 下会回退本地 roles；`is_company_permitted/is_supplier_permitted/is_warehouse_permitted` 在“无对应 allowed 集合”时返回 `True`，存在语义漂移风险 |
| `erpnext_stock_entry_service.py` | Stock Entry 查询、创建、提交 | 对 event_key 重复命中有 fail closed（重复即阻断） | 创建/提交后未强制二次校验 docstatus 最终态；HTTP 语义与业务码映射分散 |
| `erpnext_job_card_adapter.py` | Job Card / Work Order / Employee / Item / Company 读取，Job Card completed_qty 写入 | 对 404 与服务不可用有区分；支持 service account 模式 | 多处对结构异常直接抛服务不可用，未统一 `ERPNEXT_RESPONSE_INVALID`；状态字段（status/disabled）判定在不同业务处重复 |
| `erpnext_production_adapter.py` | Sales Order / Work Order / Job Card 读取与 Work Order 创建提交流程 | 读写路径拆分清晰 | `_to_int(..., default=0)` 使 docstatus 缺失时退化为 draft，可能掩盖“字段缺失”异常；Job Card 列表空与异常的边界仍偏松 |
| `erpnext_purchase_invoice_adapter.py` | Account/Cost Center 校验；Purchase Invoice 按 event_key 查找与 draft 创建 | 对 docstatus 非法、重复 event_key 有阻断 | 创建 draft 后虽有回读，但未统一沉淀“docstatus 缺失/非法/非 0”判定契约；错误码仍偏模块化 |
| `erpnext_style_profit_adapter.py` | 销售发票/订单、SLE、本地 BOM/工票/外发来源聚合 | 对 ERP 不可用统一抛 `STYLE_PROFIT_SOURCE_UNAVAILABLE`，总体偏 fail closed | `_build_headers` 无鉴权头时仍可发请求；部分路径对 payload 结构异常返回空（如 valuation/item price），可能与“真实无数据”混淆 |

### 2.1 重复逻辑与可抽象点
1. `_request_json/_get_json` 在各 Adapter 重复实现。
2. 401/403/404/5xx/timeout 映射重复但不完全一致。
3. docstatus/status 判定散落在业务调用侧。
4. 服务账号 Header 构造重复实现。
5. 响应结构校验（`payload.data`）重复实现。

---

## 三、ERPNext 能力矩阵（冻结）

| 能力对象 / Doctype | 读取 | 写入 | 是否强制 docstatus | 是否允许 status-only | 失败错误码（规范） | 适用模块 |
| --- | --- | --- | --- | --- | --- | --- |
| Supplier | 是 | 否 | 否（主数据） | 是（`disabled`） | `ERPNEXT_RESOURCE_NOT_FOUND` / `ERPNEXT_RESPONSE_INVALID` / `EXTERNAL_SERVICE_UNAVAILABLE` | TASK-002/006 |
| Account | 是 | 否 | 否（主数据） | 是（`disabled`,`is_group`） | 同上 | TASK-006 |
| Cost Center | 是 | 否 | 否（主数据） | 是（`disabled`,`is_group`） | 同上 | TASK-006 |
| Item | 是 | 否 | 否（主数据） | 是（`disabled`） | 同上 | TASK-002/003/005 |
| Sales Order | 是 | 否 | 是 | 可附加 `status`，不可仅 status | `ERPNEXT_DOCSTATUS_REQUIRED` / `ERPNEXT_DOCSTATUS_INVALID` / `ERPNEXT_RESOURCE_NOT_FOUND` / `EXTERNAL_SERVICE_UNAVAILABLE` | TASK-004/005 |
| Purchase Order | 是（预留） | 否 | 是 | 不建议 status-only | 同上 | Sprint 2 预留 |
| Delivery Note | 是（预留） | 否 | 是 | 不建议 status-only | 同上 | Sprint 2 预留 |
| Stock Entry | 是 | 是（create/submit） | 是 | 否 | `ERPNEXT_DOCSTATUS_REQUIRED` / `ERPNEXT_DOCSTATUS_INVALID` / `EXTERNAL_SERVICE_UNAVAILABLE` | TASK-002 |
| Stock Ledger Entry | 是 | 否 | 按白名单（见第 5 节） | 是（受限） | `ERPNEXT_RESPONSE_INVALID` / `EXTERNAL_SERVICE_UNAVAILABLE` | TASK-005 |
| Work Order | 是 | 是（create/submit） | 是 | 否 | `ERPNEXT_DOCSTATUS_REQUIRED` / `ERPNEXT_DOCSTATUS_INVALID` / `EXTERNAL_SERVICE_UNAVAILABLE` | TASK-004 |
| Job Card | 是 | 是（qty update） | 建议强制（见第 5 节） | 有限允许 | 同上 | TASK-003/004 |
| Purchase Invoice | 是 | 是（draft create） | 是 | 否 | `ERPNEXT_DOCSTATUS_REQUIRED` / `ERPNEXT_DOCSTATUS_INVALID` / `EXTERNAL_SERVICE_UNAVAILABLE` | TASK-006 |
| User Permission | 是 | 否 | 否（权限事实） | 否（结构化列表） | `PERMISSION_SOURCE_UNAVAILABLE` / `ERPNEXT_RESPONSE_INVALID` | TASK-001~012 |
| Role / 权限聚合结果 | 是 | 否 | 否 | 否 | `PERMISSION_SOURCE_UNAVAILABLE` / `ERPNEXT_AUTH_FAILED` / `EXTERNAL_SERVICE_UNAVAILABLE` | TASK-007 |

---

## 四、Fail-Closed 规则（冻结）

### 4.1 错误映射规则
1. 连接失败（DNS/网络中断） -> `EXTERNAL_SERVICE_UNAVAILABLE`（503）。
2. 超时 -> `ERPNEXT_TIMEOUT`（503，业务层可映射为 `EXTERNAL_SERVICE_UNAVAILABLE`）。
3. ERPNext 5xx -> `EXTERNAL_SERVICE_UNAVAILABLE`（503）。
4. 权限源不可用（User Permission/Role 聚合链路） -> `PERMISSION_SOURCE_UNAVAILABLE`（503）。
5. ERPNext 401/403（服务账号或调用者无权限） -> `ERPNEXT_AUTH_FAILED`（403/503 由业务语义决定，默认 503+阻断）。
6. 主数据不存在（Supplier/Account/Cost Center/Item 等） -> `ERPNEXT_RESOURCE_NOT_FOUND`（404/422，按业务选择）。
7. 响应结构不合法（非 JSON、字段类型错误） -> `ERPNEXT_RESPONSE_INVALID`（502/500，默认阻断）。
8. `docstatus/status` 缺失或非法 -> `ERPNEXT_DOCSTATUS_REQUIRED` / `ERPNEXT_DOCSTATUS_INVALID`。

### 4.2 严禁的 fail-open 行为
1. 查询失败返回空列表并当作“无权限限制”。
2. 权限源失败后回退为 unrestricted。
3. 将 draft/cancelled 文档当作成功事实。
4. 缺 docstatus 时使用默认值 0/1 并继续流程。
5. 吞异常后返回 `None` 导致业务误判“资源不存在”。

---

## 五、docstatus/status 判定矩阵（冻结）

### 5.1 通用规则
1. `docstatus=0`：draft，不得标记外部写入成功。
2. `docstatus=1`：submitted，才可作为“已提交事实”。
3. `docstatus=2`：cancelled，禁止作为成功事实。
4. 缺失 `docstatus`：默认 fail closed（`ERPNEXT_DOCSTATUS_REQUIRED`）。

### 5.2 status-only 白名单（按 doctype）
仅下列对象允许 status-only 判定，且必须补充对象级字段校验：
1. `Supplier`：`disabled != 1`。
2. `Account`：`disabled != 1` 且 `is_group != 1`。
3. `Cost Center`：`disabled != 1` 且 `is_group != 1`。
4. `Item`：`disabled != 1`。
5. `User Permission`：要求 `allow/for_value` 完整，不走 status。
6. `Stock Ledger Entry`：允许无 docstatus，但必须满足 `is_cancelled != 1`，并尽可能关联凭证层 docstatus。

### 5.3 不在白名单内的 doctype
`Sales Order / Purchase Order / Delivery Note / Stock Entry / Work Order / Job Card / Purchase Invoice` 必须有 docstatus，缺失即 fail closed。

---

## 六、Adapter 统一返回契约（冻结）

### 6.1 读结果（normalized read result）
```json
{
  "ok": true,
  "source": "erpnext",
  "doctype": "Sales Order",
  "name": "SO-0001",
  "docstatus": 1,
  "status": "Submitted",
  "payload": {"...": "normalized fields only"}
}
```

### 6.2 写结果（normalized write result）
```json
{
  "ok": true,
  "source": "erpnext",
  "doctype": "Purchase Invoice",
  "name": "PINV-0001",
  "docstatus": 0,
  "status": "Draft",
  "write_mode": "draft_create"
}
```

### 6.3 docstatus 判定结果
```json
{
  "ok": false,
  "code": "ERPNEXT_DOCSTATUS_INVALID",
  "message": "docstatus=2 is cancelled",
  "data": null
}
```

### 6.4 不可用结果（unavailable）
```json
{
  "ok": false,
  "code": "EXTERNAL_SERVICE_UNAVAILABLE",
  "message": "ERPNext timeout",
  "data": null
}
```

### 6.5 not found 结果
```json
{
  "ok": false,
  "code": "ERPNEXT_RESOURCE_NOT_FOUND",
  "message": "Supplier not found",
  "data": null
}
```

### 6.6 契约约束
1. 业务层不得直接消费 ERPNext 原始响应体。
2. Adapter 对外只返回 normalized 结果或结构化异常。
3. 错误日志和异常 message 必须脱敏，不含 token/cookie/Authorization/SQL/DSN。

---

## 七、统一错误码表（TASK-008）

| 错误码 | HTTP 建议 | 说明 |
| --- | --- | --- |
| `EXTERNAL_SERVICE_UNAVAILABLE` | 503 | ERPNext 连接失败、5xx、网络异常 |
| `PERMISSION_SOURCE_UNAVAILABLE` | 503 | User Permission / Role 源不可用 |
| `ERPNEXT_DOCSTATUS_REQUIRED` | 502/500 | docstatus 缺失（应有却无） |
| `ERPNEXT_DOCSTATUS_INVALID` | 409/422 | docstatus 非法或业务不可接受状态 |
| `ERPNEXT_RESOURCE_NOT_FOUND` | 404/422 | 主数据/单据不存在 |
| `ERPNEXT_RESPONSE_INVALID` | 502 | 响应结构不合法 |
| `ERPNEXT_TIMEOUT` | 503 | 调用超时 |
| `ERPNEXT_AUTH_FAILED` | 403/503 | 服务账号权限不足或认证失败 |

> 约束：以上错误均不得伪装为 `200 + 空数据`。

---

## 八、TASK-002 ~ TASK-006 回迁清单

| 任务 | 当前集成点 | 回迁到 TASK-008 规范的动作 |
| --- | --- | --- |
| TASK-002 外发 Stock Entry | `erpnext_stock_entry_service` | 统一请求封装、docstatus 强校验、submit 成功判定、错误码收口 |
| TASK-003 工票 Job Card | `erpnext_job_card_adapter` | 读取与更新路径的状态判定统一、结构异常统一映射 |
| TASK-004 生产 Work Order | `erpnext_production_adapter` | Work Order / Sales Order docstatus 严格化、默认值去 fail-open |
| TASK-005 款式利润来源 | `erpnext_style_profit_adapter` | SLE/status 白名单化、空数据 vs 源失败语义分离 |
| TASK-006 对账 Purchase Invoice Draft | `erpnext_purchase_invoice_adapter` | draft 仅 0 态成功；1/2/缺失 fail closed；event_key/回读策略统一 |

---

## 九、审计与可追踪性要求（冻结）

1. ERPNext 不可用必须写安全审计或操作失败审计（取决于调用路径）。
2. ERPNext 写入成功但本地回写失败，outbox 必须保留 failed/dead 可追踪状态。
3. Adapter 层不得吞异常后返回空列表伪装成功。
4. 服务账号调用必须具备最小权限，禁止全局放行。
5. request_id、operator、event_key、payload_hash 必须可关联问题链路。

---

## 十、测试矩阵（TASK-008B 实现前置）

| 场景 | 预期 | 错误码/断言 |
| --- | --- | --- |
| 连接失败 | fail closed | `EXTERNAL_SERVICE_UNAVAILABLE` |
| 超时 | fail closed | `ERPNEXT_TIMEOUT` |
| ERPNext 5xx | fail closed | `EXTERNAL_SERVICE_UNAVAILABLE` |
| 401/403 | fail closed | `ERPNEXT_AUTH_FAILED` |
| 404 主数据不存在 | 明确 not found | `ERPNEXT_RESOURCE_NOT_FOUND` |
| docstatus 缺失 | fail closed | `ERPNEXT_DOCSTATUS_REQUIRED` |
| docstatus=0 | 非成功事实 | 业务不得写“成功” |
| docstatus=2 | fail closed | `ERPNEXT_DOCSTATUS_INVALID` |
| docstatus=1 | 可作为提交事实 | 允许继续流程 |
| malformed response | fail closed | `ERPNEXT_RESPONSE_INVALID` |
| 权限源失败 | fail closed | `PERMISSION_SOURCE_UNAVAILABLE` |
| 日志脱敏 | 不泄露敏感信息 | 无 Authorization/Cookie/Token/Secret/password/DSN |

---

## 十一、TASK-008B 实现边界（预冻结）

1. 允许改 Adapter 层公共封装与返回契约。
2. 允许新增 Adapter 层测试与 mock fixture。
3. 不允许顺带改业务状态机（业务状态机变更需单独任务）。
4. 不允许引入“失败时自动放开权限”兼容逻辑。
5. 不允许把 draft 视为提交成功。

---

## 十二、遗留清单

1. 各 Adapter 仍有重复 `_request_json`，需在 008B 抽公共基类/工具。
2. 多模块错误码仍模块化（如 `FACTORY_STATEMENT_ERPNEXT_*`），需要统一映射层。
3. `status-only` 对 `Stock Ledger Entry` 的凭证级补校验需要在 008B 明确实现。
4. `get_user_roles` 的 fallback 语义需与权限源不可用策略统一，避免 fail-open 误解。
5. 本规范是本地封版设计，不代表 ERPNext 生产环境联调完成。

---

## 十三、结论

TASK-008A 设计冻结结论：
1. 已冻结能力清单、fail-closed 规则、docstatus/status 矩阵、返回契约、回迁清单、测试矩阵。
2. 可作为 TASK-008B 的唯一实现前置。
3. TASK-008B 开始前须先通过审计，严禁直接进入代码实现。
