# 模块设计：BOM 管理（款式物料清单）

- 任务卡编号：TASK-001
- 版本：V1.11
- 更新时间：2026-04-12 12:07 CST
- 作者：技术架构师
- 责任模块：FastAPI `bom` + Vue3 `bom` 视图 + ERPNext `Item`
- 审计整改：统一 BOM 契约，冻结为 `ly_apparel_* + /api/bom/`；权限来源不可用时必须 fail closed；401/403 必须形成安全审计闭环；写接口异常必须分类返回；提交阶段数据库异常必须归类为 `DATABASE_WRITE_FAILED`；普通日志和审计日志必须脱敏；`request_id` 必须白名单规范化并拦截语义敏感词

## 1. 设计目标

BOM 管理模块负责款式物料清单、BOM 草稿、BOM 发布、默认 BOM、BOM 展开和工序成本计算，是外发加工、工票派工、生产计划和款式利润报表的基础输入。

目标包括：

1. 建立 `ly_apparel_bom / ly_apparel_bom_item / ly_bom_operation` 三张业务表。
2. 款式和物料事实源统一引用 ERPNext `Item`，不再新建 `ly_style` 款式事实表。
3. API 契约统一为 `/api/bom/` 资源风格，不再使用 `/api/bom/styles`、`/api/bom/style-boms`。
4. 固化 BOM 版本规则：发布后锁定，不可直接修改，只能复制生成新版本。
5. 固化默认 BOM 规则：同一 `item_code` 只能有一个 `is_default=true` 且 `status=active` 的 BOM。
6. 物料边界遵守 ERPNext：`item_code` 和 `material_item_code` 必须引用 ERPNext `Item` 有效记录。

## 2. 唯一契约冻结

| 项 | 冻结口径 | 废弃口径 |
| --- | --- | --- |
| BOM 主表 | `ly_schema.ly_apparel_bom` | `ly_schema.ly_style_bom` |
| BOM 物料明细 | `ly_schema.ly_apparel_bom_item` | `ly_schema.ly_style_bom_item` |
| BOM 工序明细 | `ly_schema.ly_bom_operation` | 无 |
| 款式主数据 | ERPNext `Item` | `ly_schema.ly_style` |
| BOM 版本记录 | `ly_apparel_bom.version_no` + 发布锁定规则 | `ly_schema.ly_style_bom_version` |
| API 前缀 | `/api/bom/` | `/api/bom/styles`、`/api/bom/style-boms` |
| 后端目录 | `/07_后端/lingyi_service/app/*/bom.py` | `/02_源码/fastapi_service/app/modules/bom/*` |
| 前端目录 | `/06_前端/lingyi-pc/src/views/bom/` | 历史 `pages/*.json` |

后续外发加工、生产计划、工票和利润模块引用 BOM 时，只允许引用本章节冻结口径。

## 3. 数据模型设计

### 3.1 表：`ly_schema.ly_apparel_bom`

用途：BOM 主表。

关键字段：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `id` | bigint | 是 | 主键 |
| `bom_no` | varchar(64) | 是 | BOM 编号，全局唯一 |
| `item_code` | varchar(140) | 是 | ERPNext `Item.name`，代表款式/成品 |
| `version_no` | varchar(32) | 是 | BOM 版本号 |
| `is_default` | boolean | 是 | 是否默认 BOM |
| `status` | varchar(32) | 是 | `draft/active/inactive/archived` |
| `effective_date` | date | 否 | 生效日期 |
| `created_at` | timestamptz | 是 | 创建时间 |
| `created_by` | varchar(140) | 是 | 创建人 |
| `updated_at` | timestamptz | 是 | 更新时间 |
| `updated_by` | varchar(140) | 是 | 更新人 |

索引与约束：

1. 主键：`pk_ly_apparel_bom(id)`。
2. 唯一索引：`uk_ly_apparel_bom_bom_no(bom_no)`。
3. 普通索引：`idx_ly_apparel_bom_status(status)`。
4. 普通索引：`idx_ly_apparel_bom_item_default(item_code, is_default)`。
5. PostgreSQL 部分唯一索引：`uk_ly_apparel_bom_one_active_default(item_code) WHERE is_default = true AND status = 'active'`。

### 3.2 表：`ly_schema.ly_apparel_bom_item`

用途：BOM 物料明细。

关键字段：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `id` | bigint | 是 | 主键 |
| `bom_id` | bigint | 是 | 关联 `ly_apparel_bom.id` |
| `material_item_code` | varchar(140) | 是 | ERPNext `Item.name`，代表面料/辅料 |
| `color` | varchar(64) | 否 | 颜色 |
| `size` | varchar(64) | 否 | 尺码 |
| `qty_per_piece` | numeric(18,6) | 是 | 单件用量 |
| `loss_rate` | numeric(12,6) | 是 | 损耗率，默认 0 |
| `uom` | varchar(32) | 是 | 单位 |
| `remark` | text | 否 | 备注 |

索引与约束：

1. 主键：`pk_ly_apparel_bom_item(id)`。
2. 外键：`fk_ly_apparel_bom_item_bom_id(bom_id)`。
3. 普通索引：`idx_ly_apparel_bom_item_bom_id(bom_id)`。
4. 普通索引：`idx_ly_apparel_bom_item_material(material_item_code)`。
5. 校验：`qty_per_piece > 0`。
6. 校验：`loss_rate >= 0`。

### 3.3 表：`ly_schema.ly_bom_operation`

用途：BOM 工序明细。

关键字段：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `id` | bigint | 是 | 主键 |
| `bom_id` | bigint | 是 | 关联 `ly_apparel_bom.id` |
| `process_name` | varchar(100) | 是 | 工序名称 |
| `sequence_no` | bigint | 是 | 工序顺序 |
| `is_subcontract` | boolean | 是 | 是否外发工序 |
| `wage_rate` | numeric(18,6) | 否 | 本厂计件工价 |
| `subcontract_cost_per_piece` | numeric(18,6) | 否 | 外发单件成本 |
| `remark` | text | 否 | 备注 |

索引与约束：

1. 主键：`pk_ly_bom_operation(id)`。
2. 外键：`fk_ly_bom_operation_bom_id(bom_id)`。
3. 普通索引：`idx_ly_bom_operation_bom_process(bom_id, process_name)`。
4. 普通索引：`idx_ly_bom_operation_subcontract(is_subcontract)`。
5. 校验：`sequence_no > 0`。
6. 校验：`is_subcontract = true` 时 `subcontract_cost_per_piece` 必填且大于等于 0。
7. 校验：`is_subcontract = false` 时 `wage_rate` 必填且大于等于 0。

### 3.4 ERPNext 表：`public.tabItem`

用途：款式和物料事实源。

只读字段：

1. `name`
2. `item_code`
3. `item_name`
4. `stock_uom`
5. `item_group`
6. `disabled`

FastAPI 只读校验 `Item`，不直接更新 `public.tabItem`。

## 4. API 契约

所有接口返回统一结构：

```json
{
  "code": "0",
  "message": "success",
  "data": {}
}
```

错误响应结构：

```json
{
  "code": "BOM_ITEM_NOT_FOUND",
  "message": "物料不存在",
  "data": {}
}
```

### 4.1 创建 BOM

- 方法/路径：`POST /api/bom/`
- 入参：`item_code`、`version_no`、`bom_items[]`、`operations[]`
- 出参：`name`、`status`
- 校验：
  - `item_code` 在 ERPNext `Item` 中存在且未禁用。
  - `bom_items[].material_item_code` 在 ERPNext `Item` 中存在且未禁用。
  - `qty_per_piece > 0`。
  - `loss_rate >= 0`。

### 4.2 查询 BOM 列表

- 方法/路径：`GET /api/bom/`
- 入参：`item_code`、`status`、`page`、`page_size`
- 出参：`items`、`total`、`page`、`page_size`

### 4.3 获取 BOM 详情

- 方法/路径：`GET /api/bom/{bom_id}`
- 入参：`bom_id`
- 出参：`bom`、`items`、`operations`

### 4.4 更新 BOM 草稿

- 方法/路径：`PUT /api/bom/{bom_id}`
- 入参：`version_no`、`bom_items[]`、`operations[]`
- 出参：`name`、`status`、`updated_at`
- 规则：仅 `draft` 状态允许更新，`active/inactive/archived` 不允许直接更新。

### 4.5 设置默认 BOM

- 方法/路径：`POST /api/bom/{bom_id}/set-default`
- 入参：`bom_id`
- 出参：`name`、`item_code`、`is_default`
- 规则：
  - 目标 BOM 必须存在。
  - 目标 BOM 必须为 `active`。
  - 同一 `item_code` 只允许一个 `active + is_default=true`。
  - 服务层必须在同一事务中锁定同款式 BOM 集合，并切换默认值。

### 4.6 发布 BOM

- 方法/路径：`POST /api/bom/{bom_id}/activate`
- 入参：`bom_id`
- 出参：`name`、`status`、`effective_date`
- 规则：发布后状态变为 `active`，发布后不可直接修改。

### 4.7 停用 BOM

- 方法/路径：`POST /api/bom/{bom_id}/deactivate`
- 入参：`bom_id`、`reason`
- 出参：`name`、`status`
- 规则：默认 BOM 停用前必须先切换默认 BOM，或由接口明确返回阻断错误。

### 4.8 展开 BOM

- 方法/路径：`POST /api/bom/{bom_id}/explode`
- 入参：`order_qty`、`size_ratio`
- 出参：`material_requirements`、`operation_costs`、`total_material_qty`、`total_operation_cost`

## 5. 公式口径

1. 含损耗用量：`qty_with_loss = qty_per_piece * (1 + loss_rate)`。
2. 尺码数量：`size_order_qty = order_qty * size_ratio`。
3. 物料需求数量：`required_qty = size_order_qty * qty_per_piece * (1 + loss_rate)`。
4. 物料合并维度：`material_item_code + color + size + uom`。
5. 本厂工序成本：`operation_cost = wage_rate * order_qty`。
6. 外发工序成本：`subcontract_operation_cost = subcontract_cost_per_piece * order_qty`。
7. 总工序成本：`total_operation_cost = sum(operation_cost + subcontract_operation_cost)`。

示例：

```text
order_qty = 100
qty_per_piece = 2
loss_rate = 0.05
required_qty = 100 * 2 * (1 + 0.05) = 210
```

## 6. 关键流程

1. 创建 BOM：
   - 校验 ERPNext `Item`。
   - 写入 `ly_apparel_bom`。
   - 写入 `ly_apparel_bom_item`。
   - 写入 `ly_bom_operation`。
   - 状态为 `draft`。
2. 更新 BOM：
   - 仅允许更新 `draft`。
   - 明细采用整包替换。
3. 发布 BOM：
   - 校验物料和工序完整。
   - 状态改为 `active`。
   - 发布后禁止直接修改。
4. 设置默认：
   - 校验目标 BOM 为 `active`。
   - 锁定同 `item_code` 的 BOM 集合。
   - 旧默认置为 false。
   - 目标 BOM 置为 true。
   - 数据库部分唯一索引兜底防并发。
5. 展开 BOM：
   - 按尺码比例计算尺码数量。
   - 按损耗率计算需求数量。
   - 按物料、颜色、尺码、单位聚合。
   - 同时输出本厂工序和外发工序成本。

## 7. ERPNext 边界

1. ERPNext `Item` 是款式和物料事实源。
2. FastAPI `ly_schema` 只保存 BOM 业务事实。
3. 本模块不创建 ERPNext 标准 `BOM`。
4. 本模块不创建 ERPNext `Work Order`。
5. 本模块不创建 ERPNext `Purchase Order`。
6. 本模块不创建 ERPNext `Stock Entry`。
7. 本模块不直接写 `Stock Ledger Entry`、`GL Entry`、`Payment Entry`。

## 8. 异常与错误码

| 错误码 | 含义 |
| --- | --- |
| `BOM_NOT_FOUND` | BOM 不存在 |
| `BOM_ITEM_NOT_FOUND` | ERPNext `Item` 不存在或已禁用 |
| `BOM_INVALID_QTY` | 数量非法 |
| `BOM_INVALID_LOSS_RATE` | 损耗率非法 |
| `BOM_OPERATION_RATE_REQUIRED` | 工序工价缺失 |
| `BOM_PUBLISHED_LOCKED` | 已发布 BOM 禁止修改 |
| `BOM_DEFAULT_REQUIRES_ACTIVE` | 只有 active BOM 能设置默认 |
| `BOM_DEFAULT_CONFLICT` | 默认 BOM 并发冲突 |
| `BOM_STATUS_INVALID` | 当前状态不允许执行该动作 |
| `AUDIT_WRITE_FAILED` | 审计日志写入失败 |
| `DATABASE_WRITE_FAILED` | BOM 主业务数据库写入失败 |
| `DATABASE_READ_FAILED` | BOM 主业务数据库读取失败 |
| `BOM_INTERNAL_ERROR` | 未知程序异常 |

## 9. 并发与事务要求

1. 创建 BOM、更新 BOM、发布 BOM、设置默认 BOM 必须在事务内完成。
2. 设置默认 BOM 必须锁定同款式 BOM 集合，建议使用 `SELECT ... FOR UPDATE`。
3. 数据库必须增加 PostgreSQL 部分唯一索引：`UNIQUE(item_code) WHERE is_default = true AND status = 'active'`。
4. 如果触发唯一约束冲突，接口返回 `BOM_DEFAULT_CONFLICT`。
5. 写接口必须记录操作者，后续接入统一审计日志。

## 10. 鉴权、权限动作与审计要求

### 10.1 当前用户

所有 BOM 写接口必须通过 `Depends(get_current_user)` 解析真实当前用户。

要求：

1. 操作者必须来自 ERPNext 登录态、ERPNext Token 或受控服务账号。
2. 生产环境禁止信任前端直接传入的用户名。
3. 本地开发调试用户必须受环境变量开关控制。
4. BOM 写接口禁止使用 `operator="system"` 代表业务用户。

### 10.2 权限动作

| 动作 | 权限码 | 接口 |
| --- | --- | --- |
| 创建 BOM | `bom:create` | `POST /api/bom/` |
| 更新 BOM | `bom:update` | `PUT /api/bom/{bom_id}` |
| 发布 BOM | `bom:publish` | `POST /api/bom/{bom_id}/activate` |
| 停用 BOM | `bom:deactivate` | `POST /api/bom/{bom_id}/deactivate` |
| 设置默认 BOM | `bom:set_default` | `POST /api/bom/{bom_id}/set-default` |

权限要求：

1. 后端必须强制校验权限动作。
2. 前端按钮隐藏不能替代后端权限校验。
3. 未登录返回 `AUTH_UNAUTHORIZED`。
4. 无权限返回 `AUTH_FORBIDDEN`。

### 10.3 敏感操作审计

以下动作必须写入 `ly_schema.ly_operation_audit_log`：

1. `bom:create`
2. `bom:update`
3. `bom:publish`
4. `bom:deactivate`
5. `bom:set_default`

审计字段至少包含：

1. `module`
2. `action`
3. `operator`
4. `operator_roles`
5. `resource_type`
6. `resource_id`
7. `resource_no`
8. `before_data`
9. `after_data`
10. `result`
11. `error_code`
12. `request_id`
13. `ip_address`
14. `user_agent`
15. `created_at`

事务要求：

1. 业务写入成功但审计日志写入失败时，整个操作必须回滚。
2. 发布、停用、设默认必须记录操作前后快照。

### 10.4 ERPNext User Permission Fail Closed

BOM 读接口、详情接口、展开接口依赖 ERPNext `User Permission` 进行资源级权限判断。

权限来源不可用时的统一规则：

1. ERPNext `User Permission` 查询失败、超时、数据库异常、REST API 异常或返回结构异常时，必须拒绝访问。
2. `get_user_permissions()` 禁止用 `[]` 表示查询失败。
3. 空权限列表只能表示 ERPNext 查询成功且明确没有 `User Permission` 限制。
4. 权限查询失败时接口返回 `PERMISSION_SOURCE_UNAVAILABLE`，不得返回 BOM 数据。
5. `GET /api/bom/` 不得在权限来源不可用时返回全部 BOM 或空列表伪装成功。
6. `GET /api/bom/{bom_id}` 不得在权限来源不可用时返回 BOM 详情。
7. `POST /api/bom/{bom_id}/explode` 不得在权限来源不可用时返回展开结果。
8. `/api/auth/actions?module=bom` 不得在生产环境用静态权限兜底 ERPNext 权限失败。

### 10.5 权限拒绝安全审计

BOM 模块所有认证失败、权限拒绝、资源级越权和权限来源不可用事件必须形成安全审计闭环。

必须记录的事件：

1. 未登录访问 BOM 接口，记录 `AUTH_UNAUTHORIZED`。
2. 已登录但缺少动作权限，记录 `AUTH_FORBIDDEN`。
3. 已登录且有动作权限但无 `item_code` / `company` 资源权限，记录 `AUTH_FORBIDDEN`。
4. ERPNext 权限来源不可用，记录 `PERMISSION_SOURCE_UNAVAILABLE`。

审计记录至少包含：

1. `event_type`
2. `module`
3. `action`
4. `resource_type`
5. `resource_id`
6. `resource_no`
7. `user_id`
8. `user_roles`
9. `permission_source`
10. `deny_reason`
11. `request_method`
12. `request_path`
13. `request_id`
14. `ip_address`
15. `user_agent`
16. `created_at`

安全要求：

1. 审计日志禁止记录完整 `Authorization Token`、`Cookie`、密码、ERPNext API Secret。
2. 审计写入失败不得导致权限放行。
3. 权限来源不可用时必须返回 `503 + PERMISSION_SOURCE_UNAVAILABLE` 并记录安全审计。
4. 401/403 不得只返回客户端，必须留痕。

### 10.6 写接口异常分类

BOM 写接口禁止把所有未知异常统一返回为 `AUDIT_WRITE_FAILED`。

异常分类要求：

1. `AUDIT_WRITE_FAILED` 只能表示审计日志写入失败。
2. 业务校验失败必须返回对应 BOM 业务错误码。
3. 主业务数据库写入失败返回 `DATABASE_WRITE_FAILED`。
4. 主业务数据库读取失败返回 `DATABASE_READ_FAILED`。
5. 唯一索引冲突如能识别为默认 BOM 冲突，返回 `BOM_DEFAULT_CONFLICT`。
6. 未知程序异常返回 `BOM_INTERNAL_ERROR`。
7. 客户端响应不得暴露 Python traceback、SQL 原文、数据库连接串、Token、Cookie。

事务要求：

1. BOM 业务写入成功但操作审计写入失败时，整体回滚并返回 `AUDIT_WRITE_FAILED`。
2. BOM 业务写入失败时，不得写成功审计，应返回业务或数据库错误码。
3. 权限拒绝审计失败不得导致权限放行。

### 10.7 提交阶段数据库异常分类

BOM 写接口中 `session.flush()`、`session.commit()`、事务上下文退出时触发的数据库异常，均属于主业务数据库写入失败。

分类要求：

1. `session.commit()` 抛出 `SQLAlchemyError`、`DBAPIError`、`OperationalError`、`IntegrityError` 时，返回 `DATABASE_WRITE_FAILED`。
2. 默认 BOM 部分唯一索引 `uk_ly_apparel_bom_one_active_default` 冲突时，返回 `BOM_DEFAULT_CONFLICT`。
3. 提交阶段数据库异常禁止落入 `BOM_INTERNAL_ERROR`。
4. 提交阶段数据库异常禁止落入 `AUDIT_WRITE_FAILED`。
5. 提交失败后必须执行 `rollback`，且 `rollback` 失败不得覆盖原始错误码。
6. `snapshot_resource()` 必须纳入统一异常处理，禁止绕过 `{code, message, data}` 错误信封。
7. 测试环境变量必须在应用模块 import 前完成设置，避免 import-time 顺序脆弱性。

### 10.8 日志脱敏与测试环境隔离

BOM 模块普通错误日志、安全审计日志、操作审计日志均不得记录敏感异常原文。

日志脱敏规则：

1. 普通应用日志禁止直接记录 `str(exc)`。
2. SQLAlchemy 异常日志禁止记录 `[SQL:]`、`[parameters:]`、SQL statement、SQL parameters、数据库连接串。
3. 认证与审计日志禁止记录完整 `Authorization Token`、`Cookie`、密码、ERPNext API Secret。
4. 普通日志只允许记录 `error_code`、`exception_type`、`request_id`、`module`、`action`、`resource_type`、`resource_id`、`resource_no`、`user_id`、`sqlstate`、数据库驱动错误码等安全字段。
5. 如无法安全脱敏，错误明细统一写为 `internal error, detail redacted`。
6. 生产环境禁止开启原始异常日志。

测试环境隔离规则：

1. 测试环境变量必须强制覆盖，不允许使用 `os.environ.setdefault()` 作为关键环境变量设置方式。
2. 测试环境变量设置必须发生在应用模块 import 前。
3. 测试入口必须对外部 `APP_ENV=production`、`LINGYI_PERMISSION_SOURCE=static` 注入免疫。
4. 生产保护逻辑不得删除：非测试入口下 `APP_ENV=production` 且 `LINGYI_PERMISSION_SOURCE=static` 必须启动失败。

### 10.9 Request ID 白名单校验

外部传入的 `X-Request-ID` 属于不可信输入，进入日志、审计表和响应头前必须统一规范化。

规范化要求：

1. 统一函数：`normalize_request_id(raw_request_id)`。
2. 允许字符：`A-Z`、`a-z`、`0-9`、`_`、`-`、`.`。
3. 允许长度：1 到 64 个字符。
4. 推荐正则：`^[A-Za-z0-9_.-]{1,64}$`。
5. 缺失、超长或不符合白名单时，丢弃原值并生成新的安全 `request_id`。
6. 非法 `request_id` 禁止截断后继续使用。
7. `main.py` 请求中间件负责唯一一次读取原始 `X-Request-ID`，并写入 `request.state.request_id`。
8. 后续 `logging.py`、`audit_service.py` 和业务模块只能使用 `request.state.request_id`。
9. 响应头 `X-Request-ID` 只返回规范化后的 `request_id`。
10. 普通日志和审计表禁止记录非法 `request_id` 原文。

### 10.10 Request ID 语义敏感词拦截

`request_id` 即使通过字符白名单，只要包含敏感语义关键词，也必须整体丢弃并重新生成。

必须大小写不敏感拦截以下关键词：

1. `authorization`
2. `bearer`
3. `token`
4. `cookie`
5. `set-cookie`
6. `password`
7. `passwd`
8. `secret`
9. `session`
10. `sessionid`
11. `api-key`
12. `api_key`
13. `access-key`
14. `access_key`
15. `access-token`
16. `access_token`
17. `refresh-token`
18. `refresh_token`

处理规则：

1. 命中敏感词的 `request_id` 禁止进入响应头。
2. 命中敏感词的 `request_id` 禁止进入普通日志。
3. 命中敏感词的 `request_id` 禁止进入 `ly_security_audit_log`。
4. 命中敏感词的 `request_id` 禁止进入 `ly_operation_audit_log`。
5. 禁止将敏感词 mask、截断或替换后继续作为 `request_id` 使用。
6. 允许记录安全枚举原因：`request_id_invalid_reason=sensitive_keyword`。
7. 单文件 `unittest` 必须能在外部生产变量注入下强制初始化测试环境。

## 11. 验收对应关系

1. 数据模型：三张 BOM 自建表 + ERPNext `Item` 只读边界已落地。
2. API：8 个接口路径与任务卡一致。
3. 契约：不存在 `ly_style_*` 和 `/api/bom/styles`、`/api/bom/style-boms` 新契约。
4. 版本规则：发布锁定与默认唯一规则在服务层和数据库层都有约束。
5. 公式规则：`required_qty=order_qty * qty_per_piece * (1 + loss_rate)` 可被测试复算。
6. 边界：不写 ERPNext 标准库存、财务、采购、生产单据。
7. 审计整改：外发、生产、工票、利润模块只允许引用 `ly_apparel_bom.id`。
8. 权限整改：BOM 写接口必须使用真实当前用户和权限动作校验。
9. 审计整改：BOM 敏感写操作必须写入 `ly_operation_audit_log`。
10. 权限整改：ERPNext `User Permission` 查询失败必须 fail closed，不允许当作无资源限制。
11. 安全审计：BOM 401/403/503 权限拒绝必须写入安全审计日志或持久化审计记录。
12. 异常整改：BOM 写接口必须区分审计写入失败、业务异常、数据库异常和未知异常。
13. 异常整改：BOM 写接口 `flush/commit/事务退出` 阶段数据库异常必须归类为 `DATABASE_WRITE_FAILED`。
14. 日志整改：普通日志和审计日志不得记录 SQL 原文、SQL 参数、Token、Cookie、密码、Secret。
15. 测试整改：测试环境变量必须强制隔离，避免外部生产变量污染测试导入。
16. 日志整改：`X-Request-ID/request_id` 必须白名单规范化，非法原文不得进入普通日志或审计表。
17. 日志整改：`request_id` 命中 token、password、secret、cookie、authorization、bearer 等语义敏感词时必须整体替换。

## 12. 版本记录

| 版本 | 更新时间 | 作者 | 说明 |
| --- | --- | --- | --- |
| V1.0 | 2026-04-11 | 技术架构师 | 初版模块设计，存在 `ly_style_*` 契约 |
| V1.1 | 2026-04-11 21:55 CST | 技术架构师 | 审计整改：统一为 `ly_apparel_* + /api/bom/` 契约 |
| V1.2 | 2026-04-12 00:00 CST | 技术架构师 | 审计整改：补充 BOM 写接口鉴权、权限动作和敏感操作审计要求 |
| V1.3 | 2026-04-12 09:49 CST | 技术架构师 | 审计整改：明确静态权限映射仅为 Sprint 临时方案，生产前升级 ERPNext 权限来源 |
| V1.4 | 2026-04-12 10:05 CST | 技术架构师 | 审计整改：补充 BOM 读接口和展开接口 `bom:read` 后端资源级鉴权要求 |
| V1.5 | 2026-04-12 10:23 CST | 技术架构师 | 审计整改：明确 ERPNext `User Permission` 查询失败必须 fail closed |
| V1.6 | 2026-04-12 10:35 CST | 技术架构师 | 审计整改：补充 BOM 权限拒绝安全审计闭环要求 |
| V1.7 | 2026-04-12 11:01 CST | 技术架构师 | 审计整改：补充 BOM 写接口异常分类与 `AUDIT_WRITE_FAILED` 使用边界 |
| V1.8 | 2026-04-12 11:22 CST | 技术架构师 | 审计整改：补充提交阶段数据库异常分类、审计快照错误信封和测试环境变量稳定性要求 |
| V1.9 | 2026-04-12 11:37 CST | 技术架构师 | 审计整改：补充服务端日志脱敏和测试环境变量强制隔离要求 |
| V1.10 | 2026-04-12 11:54 CST | 技术架构师 | 审计整改：补充 `X-Request-ID/request_id` 白名单校验与脱敏要求 |
| V1.11 | 2026-04-12 12:07 CST | 技术架构师 | 审计整改：补充 `request_id` 语义敏感词拦截和单文件 unittest 环境隔离要求 |
