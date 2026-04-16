# TASK-007 权限与审计统一基座设计

- 模块名：TASK-007 权限与审计统一基座
- 版本：V1.0
- 更新时间：2026-04-16 09:06
- 作者：技术架构师
- 前置依赖：Sprint2_架构规范.md 已审计确认
- 适用范围：Sprint 2 所有 P1 模块，含 TASK-008 ~ TASK-012

## 一、业务目标

统一后端动作权限、资源权限、安全审计、操作审计和错误信封，为 Sprint 2 所有 P1 模块提供公共权限基线。Sprint 1 审计中，BOM、外发、工票、生产计划、款式利润、加工厂对账单均多次出现权限、审计、错误信封和 fail-closed 分散实现问题。TASK-007 的目标是先冻结规范，再允许后续模块按同一标准实现。

## 二、现状梳理结论

| 文件/模块 | 当前职责 | Sprint 1 暴露问题 | TASK-007 收口要求 |
| --- | --- | --- | --- |
| /07_后端/lingyi_service/app/services/permission_service.py | 用户、角色、权限动作、资源权限解析 | 静态角色映射与 ERPNext/Auth 权限源边界多次被审计追问 | 明确开发临时权限源与生产权威权限源边界，权限源不可用必须 fail closed |
| /07_后端/lingyi_service/app/core/permissions.py | 权限动作与角色映射 | 多模块动作命名不完全统一，service account 曾过宽 | 统一 `module:action` 命名、服务账号最小权限策略 |
| /07_后端/lingyi_service/app/core/error_codes.py | 错误码集中定义 | 数据库写失败、审计写失败、未知异常分类不一致 | 统一 fail-closed 错误码和 HTTP 状态码 |
| TASK-001 BOM | BOM 读写、发布、停用、默认 BOM | 读接口未鉴权、权限源 fail-open、operator=system、request_id 泄露 | 回迁 current_user、资源级校验、安全审计、request_id 脱敏规范 |
| TASK-002 外发加工 | 外发单、发料、回料、验货、结算 | 旧演示路径、幂等、ERPNext Stock Entry、供应商/Item 资源权限反复整改 | 回迁 supplier/item/company/work_order 资源权限与操作审计规范 |
| TASK-003 工票/车间 | 工票、工价、Job Card 同步 | 资源越权、服务账号过宽、worker 内部 API 权限收口 | 回迁 service-account policy、internal API、dry-run/diagnostic 审计规范 |
| TASK-004 生产计划 | Production Plan、Work Order outbox | 前后端契约漂移、internal worker 禁线、CI 门禁 | 回迁生产计划权限动作和前端写入口禁线 |
| TASK-005 款式利润 | 利润快照、来源映射、只读前端 | 真实来源 fail-closed、前端写入口绕过大量出现 | 回迁 style_profit 权限动作、只读/创建边界、操作审计失败路径 |
| TASK-006 加工厂对账 | 对账单、确认/取消、payable outbox、导出 | 前端缺 company、payable 摘要缺失、CSV 公式注入、active outbox 防重 | 回迁 factory_statement 权限动作、export 审计、payable worker 权限 |

规范化方向：后端统一以 `current_user + action + resource_scope` 为鉴权入口；前端只负责按钮显示；所有 401/403/权限源不可用/资源越权必须写安全审计；所有业务状态变更、导出、dry-run、diagnostic 必须写操作审计或安全审计；所有错误响应必须保持统一错误信封。

### 2.1 代码级扫描补充（Sprint 1 基线）

1. 权限动作常量当前集中在 `app/core/permissions.py`；各业务模块并未独立维护 `permissions.py`，导致“模块权限边界定义”和“公共动作字典”耦合在同一处。
2. `permission_service.py` 目前按模块提供 `get_*_user_permissions` / `ensure_*_resource_permission`（workshop/subcontract/production/style_profit/factory_statement），BOM 仍保留 `get_actions` 聚合路径，存在历史双轨。
3. 错误信封在各 router 已基本统一为 `_ok/_err`（成功 `code=\"0\"`，失败 `code=错误码`），但失败时 `data` 结构在 `{}` 与 `null` 间仍有差异，需在 TASK-007B 统一。
4. 审计实现已沉淀为 `LyOperationAuditLog` 与 `LySecurityAuditLog` 双表模型，具备动作审计与安全审计分流能力；后续模块需统一事件类型与字段语义，不再自造字段。

## 三、权限动作命名规范

统一格式：`module:action`。

命名规则：
1. `module` 使用小写下划线或既有稳定模块名。
2. `action` 使用小写动词或动词短语。
3. 读动作统一使用 `read`，列表和详情都归入 read。
4. 写动作按业务语义拆分，不用笼统 `write` 覆盖所有敏感操作。
5. worker/internal/dry-run/diagnostic 必须单独动作。

### 3.1 动作类型分类

| 类型 | 动作示例 | 说明 |
| --- | --- | --- |
| 读 | `read` | 列表、详情、只读报表、只读摘要 |
| 创建 | `create` | 创建业务主单、创建草稿 |
| 更新 | `update` | 修改未确认/草稿数据 |
| 确认 | `confirm` | 业务确认、审核、锁定 |
| 取消 | `cancel` | 取消、释放 |
| 导出 | `export` | CSV、Excel、打印快照导出 |
| 管理 | `manage` | 配置、补数、迁移、管理入口 |
| 干运行 | `dry_run` | 只读预演，不改业务事实 |
| 诊断 | `diagnostic` | 内部诊断、问题排查 |
| worker | `worker` | internal worker 触发、重试执行 |

### 3.2 Sprint 2 P1 模块预期动作

| 模块 | 模块 Key | 读动作 | 写动作 | 管理动作 | 导出动作 | 干运行动作 | 诊断动作 | Worker 动作 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 权限与审计统一基座 | `permission_audit` | `permission_audit:read` | — | `permission_audit:manage` | — | — | `permission_audit:diagnostic` | — |
| ERPNext 集成 Adapter | `erpnext_adapter` | `erpnext_adapter:read` | — | — | — | `erpnext_adapter:dry_run` | `erpnext_adapter:diagnostic` | — |
| Outbox 公共状态机 | `outbox` | `outbox:read` | `outbox:retry` | `outbox:manage` | — | `outbox:dry_run` | `outbox:diagnostic` | `outbox:worker` |
| 前端写入口门禁 | `frontend_contract` | `frontend_contract:read` | — | `frontend_contract:manage` | — | — | `frontend_contract:diagnostic` | — |
| 销售只读集成 | `sales` | `sales:read` | — | — | `sales:export` | — | `sales:diagnostic` | — |
| 库存只读集成 | `inventory` | `inventory:read` | — | — | `inventory:export` | — | `inventory:diagnostic` | — |
| 质量管理基线 | `quality` | `quality:read` | `quality:create`, `quality:update`, `quality:confirm`, `quality:cancel` | `quality:manage` | `quality:export` | `quality:dry_run` | `quality:diagnostic` | `quality:worker` |
| 仪表盘/首页 | `dashboard` | `dashboard:read` | — | — | — | — | — | — |

### 3.3 Sprint 1 既有模块动作回迁建议

| 模块 | 既有动作 | 回迁到公共规范 |
| --- | --- | --- |
| BOM | `bom:read`, `bom:create`, `bom:update`, `bom:publish`, `bom:disable`, `bom:set_default` | 保留，补动作类型归类和资源字段 `company/item_code/bom_id` |
| 外发加工 | `subcontract:read/create/update/issue_material/receive/inspect/settle` | 拆清 `confirm/cancel/export/worker/dry_run/diagnostic` |
| 工票/车间 | `workshop:read`, `workshop:ticket_register`, `workshop:ticket_reverse`, `workshop:wage_rate_manage`, `workshop:job_card_sync_worker` | 服务账号策略和 internal worker 权限回迁 |
| 生产计划 | `production:read/create/material_check/create_work_order`, `production:work_order_sync_worker` | worker/dry-run/diagnostic 单独动作 |
| 款式利润 | `style_profit:read`, `style_profit:snapshot_create` | 前端只读时不得暴露 create，后端 create 必须仅财务授权 |
| 加工厂对账 | `factory_statement:read/create/confirm/cancel/export/payable_draft/payable_draft_worker` | export、payable worker、active outbox 权限回迁 |

## 四、资源权限字段规范

| 字段 | 适用模块 | 类型 | 过滤语义 | 动作鉴权语义 |
| --- | --- | --- | --- | --- |
| `company` | 全模块 | 必填主隔离字段 | 数据必须按公司隔离 | 无 company 或 company 空白默认拒绝 |
| `item_code` | BOM、外发、工票、生产、利润、库存、质量 | 款式/物料编码 | 限定用户可访问款式/物料 | Company-only 不等于全 Item 权限 |
| `supplier` | 外发、对账、采购相关 | 加工厂/供应商 | 限定可查看/操作供应商 | Supplier 权限不可由前端 payload 伪造 |
| `warehouse` | 库存、生产、发料/回料 | 仓库 | 限定仓库库存/单据 | 发料/回料必须校验仓库权限 |
| `work_order` | 工票、生产、外发、利润、质量 | 生产工单 | 限定工单事实归属 | 同 SO/Item 不等于同 Work Order |
| `sales_order` | 销售、生产、利润、质量 | 销售订单 | 限定订单事实归属 | 缺 company/item 时不得仅凭 sales_order 放行 |
| `bom_id` | BOM、生产、外发 | BOM 主键 | 限定 BOM 访问 | BOM item 必须与业务 item 一致 |

数据隔离与动作鉴权规则：
1. 列表查询必须在数据库层按资源权限过滤，不得查出后在 Python 中过滤敏感数据。
2. 详情、创建、确认、取消、导出、worker、dry-run、diagnostic 必须在执行业务前校验 action + resource。
3. 缺关键资源字段时默认 fail closed，不得用其它弱字段替代。
4. 前端传入资源字段只作为请求参数，最终资源归属必须以后端可信数据或 ERPNext 可信数据为准。

## 五、安全审计事件规范

| 事件类型 | 触发场景 | HTTP 建议 |
| --- | --- | --- |
| `AUTH_UNAUTHENTICATED` | 未登录、Token 缺失/无效 | 401 |
| `AUTH_FORBIDDEN` | 无动作权限 | 403 |
| `RESOURCE_ACCESS_DENIED` | 有动作权限但资源越权 | 403 |
| `PERMISSION_SOURCE_UNAVAILABLE` | 权限源不可用 | 503 |
| `INTERNAL_API_FORBIDDEN` | 普通用户访问 internal worker/diagnostic | 403 |
| `REQUEST_ID_REJECTED` | request_id 含敏感词或非法格式 | 400/替换为安全 ID |
| `EXTERNAL_SERVICE_UNAVAILABLE` | ERPNext/Auth 等外部依赖不可用且影响权限/事实 | 503 |

日志字段：`timestamp / user / event_type / resource / action / ip / request_id / reason_code / resource_scope`。

禁止记录字段：`Authorization / Cookie / Token / Secret / password / passwd / pwd / DSN / API Key / 私钥 / 原始敏感 SQL 参数`。

## 六、操作审计事件规范

| 事件类型 | 说明 |
| --- | --- |
| `create` | 创建业务事实 |
| `update` | 修改业务事实 |
| `confirm` | 确认、锁定、审核 |
| `cancel` | 取消、释放 |
| `export` | CSV/Excel/打印导出 |
| `dry_run` | 预演，不改业务事实 |
| `diagnostic` | 内部诊断、问题排查 |
| `worker_run` | internal worker 执行 |
| `retry` | outbox 重试 |

操作审计字段：`timestamp / operator / operation / module / business_id / request_id / before_snapshot / after_snapshot / result / error_code`。

快照规则：
1. 快照必须脱敏。
2. 大字段只记录摘要或 hash。
3. 失败操作也必须记录，除非审计系统本身不可用；审计写失败要有专用错误分类。
4. dry-run 成功路径也要有审计记录，不得因为不改数据就无痕。

## 七、Fail-Closed 错误码表

| 错误码 | HTTP | 触发场景 | 响应原则 |
| --- | ---: | --- | --- |
| `AUTH_UNAUTHENTICATED` | 401 | 未登录或凭证无效 | 写安全审计 |
| `AUTH_FORBIDDEN` | 403 | 无动作权限 | 写安全审计 |
| `RESOURCE_ACCESS_DENIED` | 403 | 资源越权 | 写安全审计，不泄露资源是否存在 |
| `PERMISSION_SOURCE_UNAVAILABLE` | 503 | 权限源不可用 | fail closed，不降级为全量访问 |
| `RESOURCE_NOT_FOUND` | 404 | 资源确认不存在 | 不泄露越权资源存在性 |
| `EXTERNAL_SERVICE_UNAVAILABLE` | 503 | ERPNext/Auth/主数据源不可用 | 阻断业务，不落成功事实 |
| `DATABASE_READ_FAILED` | 500 | 主数据库读取失败 | 回滚并脱敏日志 |
| `DATABASE_WRITE_FAILED` | 500 | 主数据库写入/commit 失败 | 回滚，不调用外部系统 |
| `AUDIT_WRITE_FAILED` | 500 | 审计写入失败 | 仅用于审计写入失败，不得泛化 |
| `INTERNAL_ERROR` | 500 | 未知异常 | 脱敏，不返回 str(exc) |

禁止返回 `200 + 空数据` 来伪装权限源失败、ERPNext 不可用、数据库失败或资源越权。

## 八、统一错误信封

成功：

```json
{ "code": 0, "message": "success", "data": {} }
```

失败：

```json
{ "code": "ERROR_CODE", "message": "可读错误", "data": null }
```

分页：

```json
{ "code": 0, "message": "success", "data": { "items": [], "total": 0, "page": 1, "page_size": 20 } }
```

错误详情如需返回，必须脱敏，且不得包含 SQL、Token、Cookie、Authorization、DSN、Secret、密码。

## 九、TASK-001~006 回迁公共规范清单

| 来源任务 | 回迁内容 | 回迁路径建议 |
| --- | --- | --- |
| TASK-001 BOM | current_user、动作权限、资源级 read/write、敏感审计、request_id 规范化 | 抽为公共 `require_action + require_resource_scope + audit_security_event` 规范 |
| TASK-002 外发 | supplier/item/company/work_order 资源权限、ERPNext Stock Entry docstatus、幂等冲突、安全审计 | 回迁到 ERPNext fail-closed 与 outbox 规范 |
| TASK-003 工票 | service account 最小权限、internal worker 权限、dry-run/diagnostic 审计、历史数据补数 fail closed | 回迁到服务账号策略和 internal API 审计规范 |
| TASK-004 生产 | 前端契约门禁、internal worker 禁入、Work Order outbox 权限 | 回迁到前端写入口门禁和 outbox 规范 |
| TASK-005 款式利润 | source_map include 默认 false、来源缺状态 fail closed、前端只读写入口门禁 | 回迁到 fail-closed、操作审计和前端 AST 门禁规范 |
| TASK-006 加工厂对账 | active outbox 防重、payable worker 权限、export 审计、CSV 公式注入 | 回迁到 outbox、防重、export 安全审计规范 |

## 十、遗留清单

1. 现有模块权限动作命名不完全统一，需在后续实现任务中逐步映射到公共动作表。
2. 生产权限权威源仍需明确由 ERPNext Role/User Permission 或 `/api/auth/` 聚合接口提供，static role 只能作为开发临时方案。
3. 审计日志表结构是否统一尚需 TASK-007 后续实现阶段确认。
4. 历史模块中的错误码仍存在模块私有命名，需要建立兼容映射，不宜一次性破坏 API。
5. failed/dead outbox 重建策略不是 TASK-007 范围，后续由 outbox 专项处理。
6. 本文档仅冻结权限与审计规范，不代表生产发布完成。

## 十一、交付报告摘要

### 现状梳理结论

Sprint 1 已证明权限、审计和错误信封不能继续按模块分散演进。多个模块最终都修到了相似模式：当前用户、动作权限、资源权限、fail-closed、安全审计、操作审计、脱敏错误信封。

### 规范草案

本文冻结四类规范：动作权限命名、资源权限字段、安全/操作审计事件、fail-closed 错误码。TASK-008~012 必须引用本文。

### 遗留清单

主要遗留是现有代码回迁、生产权限源权威性、审计表结构统一、历史错误码兼容。后续必须拆成工程任务，不得在 TASK-007 设计阶段直接改业务代码。
