# 工程任务单：TASK-002B 外发权限与审计基线

- 任务编号：TASK-002B
- 模块：外发加工管理
- 优先级：P0（外发工程实现第一步）
- 任务类型：权限基线 / 审计基线 / 错误信封 / 事务边界整改
- 创建时间：2026-04-12 20:18 CST
- 下发人：Claude Codex（审计官窗口）
- 前置依赖：TASK-002A 已封版；审计意见书第 34 份通过；`02_模块设计_外发加工管理.md` V1.1；ADR-030

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-002B
模块：外发加工管理（权限与审计基线）
优先级：P0（未完成前禁止进入 TASK-002C/D/E 业务实现）
════════════════════════════════════════════════════════════════════════════

【任务目标】
将现有外发 `subcontract` 后端骨架接入生产级权限、审计、统一错误和事务边界，作为后续 TASK-002C~TASK-002H 的安全底座。

本任务只做“基线收口”，不实现最终外发数据模型迁移，不实现 ERPNext Stock Entry outbox，不实现发料/回料真实库存同步。

【关键原则】
1. 后端鉴权先行：所有 `/api/subcontract/*` 接口必须接入当前用户、动作权限和资源权限。
2. fail closed：认证失败、动作权限不足、资源权限不足、ERPNext 权限源不可用时，必须拒绝请求。
3. 审计可追溯：写操作、401、403、503、权限源不可用必须写审计。
4. 事务一致：写操作不得在 service 内私自 `commit()`；由路由或应用服务统一提交/回滚。
5. 禁止伪库存：不得继续生成 `STE-ISS-*` 或任何伪 `stock_entry_name` 作为库存落账。
6. 不越界：本任务不进入 TASK-002C/D/E 的 schema/outbox/ERPNext Stock Entry 实现。

【涉及文件】
必须审查并按需修改：
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/permissions.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/error_codes.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/exceptions.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/auth.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/subcontract.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/auth.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/subcontract.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/permission_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_permission_adapter.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/audit_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/subcontract_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/main.py`

必须新增或补充测试：
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_permissions.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_audit.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_exception_handling.py`
- 如修改 `/api/auth/actions`，补充现有 `test_auth_actions.py`。

前端本任务不强制改 UI；如为了类型兼容需要改 API 类型，可只做最小变更：
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/subcontract.ts`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/stores/permission.ts`

【一、权限动作冻结】
必须新增并暴露以下动作权限：
- `subcontract:read`
- `subcontract:create`
- `subcontract:issue_material`
- `subcontract:receive`
- `subcontract:inspect`
- `subcontract:cancel`
- `subcontract:stock_sync_retry`
- `subcontract:stock_sync_worker`

角色建议映射：
- `System Manager`：全部 `subcontract:*` 动作。
- `Subcontract Manager`：`read/create/issue_material/receive/inspect/cancel/stock_sync_retry`，不含 `stock_sync_worker`。
- `Subcontract Operator`：`read/create/issue_material/receive`。
- `Subcontract Inspector`：`read/inspect`。
- `Subcontract Viewer`：`read`。
- `LY Integration Service`：`subcontract:stock_sync_worker`（为后续 TASK-002D/E 预留，本任务不实现 worker）。

验收要求：
1. `/api/auth/actions?module=subcontract` 返回当前用户可用动作。
2. 普通业务角色不得获得 `subcontract:stock_sync_worker`。
3. `System Manager` 可获得全部动作，但后续内部 worker 仍必须受生产开关和审计约束。
4. `LINGYI_PERMISSION_SOURCE=static` 在生产环境仍不得启用。

【二、资源权限冻结】
资源维度必须按 V1.1 支持：
- `company`
- `item_code`
- `supplier`
- `warehouse`

实现要求：
1. 新增或复用 ERPNext User Permission 聚合能力，支持 `Company / Item / Supplier / Warehouse`。
2. 权限源查询成功且无资源限制时，语义为 unrestricted。
3. 权限源查询失败时抛 `PermissionSourceUnavailable`，统一返回 `503 + PERMISSION_SOURCE_UNAVAILABLE`。
4. 不得用 `return []` 掩盖权限源故障。
5. 列表接口必须按可读资源过滤；没有资源匹配时返回空列表，不泄露无权数据。
6. 写接口必须同时校验动作权限和资源权限。
7. 发料必须校验外发单资源和请求发料仓 `warehouse/issue_warehouse` 权限。
8. 回料必须校验外发单资源和请求回料仓 `receipt_warehouse` 权限；如当前 schema 缺少回料仓字段，必须补入 schema 或 fail closed，不得跳过仓库权限。
9. 验货必须校验外发单资源权限。

【三、接口接入范围】
本任务必须接管现有接口：
- `POST /api/subcontract/`：登录 + `subcontract:create` + `company/item_code/supplier` 资源权限 + 操作审计。
- `GET /api/subcontract/`：登录 + `subcontract:read` + 资源过滤。
- `POST /api/subcontract/{id}/issue-material`：登录 + `subcontract:issue_material` + 外发单资源权限 + 发料仓权限 + 操作/安全审计。
- `POST /api/subcontract/{id}/receive`：登录 + `subcontract:receive` + 外发单资源权限 + 回料仓权限 + 操作/安全审计。
- `POST /api/subcontract/{id}/inspect`：登录 + `subcontract:inspect` + 外发单资源权限 + 操作/安全审计。

可预留但不强制实现业务：
- `GET /api/subcontract/{id}`
- `POST /api/subcontract/{id}/cancel`
- `POST /api/subcontract/{id}/stock-sync/retry`
- `POST /api/subcontract/internal/stock-sync/run-once`

如果预留接口，请只做权限、错误信封和明确的未实现/fail closed 响应，不得伪造业务成功。

【四、审计要求】
写操作必须写操作审计：
- `subcontract:create`
- `subcontract:issue_material`
- `subcontract:receive`
- `subcontract:inspect`
- 预留接口如实现：`subcontract:cancel`、`subcontract:stock_sync_retry`、`subcontract:stock_sync_worker`

操作审计必须包含：
- `module=subcontract`
- `action`
- `operator`
- `resource_type=subcontract_order`
- `resource_id`
- `resource_no=subcontract_no`
- `before_data`
- `after_data`
- `request_id`

安全审计必须覆盖：
- 401 未登录。
- 403 动作权限不足。
- 403 资源权限不足，必须记录 `resource_type/resource_id/resource_no`，但不得泄露敏感字段。
- 503 权限源不可用。
- 内部接口禁用或 dry-run 禁用的预留路径（如本任务新增）。

审计失败规则：
1. 写操作的操作审计写入失败，必须返回 `500 + AUDIT_WRITE_FAILED`。
2. 审计失败不得放行业务成功。
3. 审计失败时必须回滚本地业务事务。
4. 审计和普通日志不得记录 `Authorization/Cookie/token/password/secret`，不得记录 SQL 原文/参数。

【五、统一错误与异常分类】
必须补齐外发错误码并接入 `HTTP_STATUS_BY_CODE` 与默认消息：
- `SUBCONTRACT_NOT_FOUND`：404
- `SUBCONTRACT_STATUS_INVALID`：409
- `SUBCONTRACT_SUPPLIER_INVALID`：400
- `SUBCONTRACT_ITEM_NOT_FOUND`：400
- `SUBCONTRACT_PROCESS_NOT_SUBCONTRACT`：400
- `SUBCONTRACT_BOM_ITEM_MISMATCH`：400
- `SUBCONTRACT_WAREHOUSE_INVALID`：400 或 403（无权限为 403）
- `SUBCONTRACT_INVALID_QTY`：400
- `SUBCONTRACT_RATE_REQUIRED`：400
- `SUBCONTRACT_IDEMPOTENCY_CONFLICT`：409（本任务可先冻结错误码，完整幂等实现由后续任务承接）
- `SUBCONTRACT_SETTLEMENT_LOCKED`：409
- `SUBCONTRACT_STOCK_SYNC_FAILED`：502
- `SUBCONTRACT_DRY_RUN_DISABLED`：403
- `SUBCONTRACT_INTERNAL_ERROR`：500
- 如需禁用旧库存动作，可新增 `SUBCONTRACT_STOCK_OUTBOX_REQUIRED` 或等价错误码，必须写明含义和测试。

统一响应要求：
- 成功：`{ "code": "0", "message": "success", "data": ... }`
- 失败：`{ "code": "...", "message": "...", "detail": ... }`
- 不再返回旧 `trace_id` 字段；request_id 由统一中间件和响应头处理。
- 不得把 `ValueError` 原文直接作为 HTTPException detail 暴露给前端。

异常分类要求：
1. 业务异常返回业务码。
2. 权限异常返回 `AUTH_FORBIDDEN` 或 `PERMISSION_SOURCE_UNAVAILABLE`。
3. 数据库读失败返回 `DATABASE_READ_FAILED`。
4. 数据库写失败返回 `DATABASE_WRITE_FAILED`。
5. 审计失败返回 `AUDIT_WRITE_FAILED`。
6. 未知异常返回 `SUBCONTRACT_INTERNAL_ERROR`，服务端记录脱敏日志。

【六、事务边界整改】
必须整改现有 service 内 `commit()` 问题：
1. `SubcontractService` 不得私自 `commit()`。
2. 写接口由路由或应用服务统一控制 `commit/rollback`。
3. `flush()` 可用于获取 id，但失败必须归类为 `DATABASE_WRITE_FAILED`。
4. rollback 失败只记录脱敏日志，不覆盖原始错误码。
5. 操作审计与业务事实必须在同一事务内提交；审计失败则业务回滚。
6. 权限拒绝不得写业务事实。

【七、禁止伪库存落账】
现有 `issue_material()` 生成 `STE-ISS-*` 的演示逻辑必须停用或改为 fail closed。

本任务验收必须证明：
1. 发料接口不会生成 `STE-ISS-*` 或其他伪 `stock_entry_name`。
2. 回料接口不会伪造 ERPNext Stock Entry 成功。
3. 如 outbox 尚未实现，stock-changing 接口不得返回库存落账成功。
4. 不得调用 ERPNext 写接口。
5. 不得写 `ly_subcontract_stock_outbox`，因为 outbox 表和迁移属于 TASK-002C/D/E。

【八、测试要求】
必须新增/补充以下测试：

权限测试：
1. 未登录访问 `GET /api/subcontract/` 返回 `401 + AUTH_UNAUTHORIZED` 并写安全审计。
2. 无 `subcontract:read` 返回 `403 + AUTH_FORBIDDEN`。
3. 无 `subcontract:create` 调创建返回 403。
4. 无 `subcontract:issue_material` 调发料返回 403。
5. 无 `subcontract:receive` 调回料返回 403。
6. 无 `subcontract:inspect` 调验货返回 403。
7. 有动作权限但无 `company/item_code/supplier/warehouse` 资源权限返回 403，并写资源级安全审计。
8. 权限源不可用返回 `503 + PERMISSION_SOURCE_UNAVAILABLE`，不得写业务事实。
9. 列表接口按可读资源过滤。
10. `/api/auth/actions?module=subcontract` 对普通用户不返回 `subcontract:stock_sync_worker`。

审计测试：
1. 创建成功写操作审计，operator 为真实当前用户，不得为 `service_account/system` 硬编码。
2. 发料/回料/验货的授权尝试写操作审计或失败审计，视最终 fail closed 策略而定。
3. 401/403/503 均写安全审计。
4. 审计字段不含 Authorization、Cookie、token、password、secret、SQL 原文/参数。
5. 操作审计写入失败时返回 `AUDIT_WRITE_FAILED` 且业务回滚。

异常与事务测试：
1. 数据库读取失败返回 `DATABASE_READ_FAILED`。
2. 数据库写入/commit/flush 失败返回 `DATABASE_WRITE_FAILED`。
3. 未知异常返回 `SUBCONTRACT_INTERNAL_ERROR`，响应不暴露 traceback/SQL/Token/Cookie。
4. rollback 失败不覆盖原始错误码。
5. service 层不再直接 `commit()`，可通过 monkeypatch 或事务回滚测试验证。
6. 发料接口不再生成 `STE-ISS-*`，不返回伪库存成功。
7. `rg "STE-ISS|trace_id|HTTPException\(.*detail=str|operator=\"service_account\"" app/routers app/services app/schemas` 不应在外发正向实现中命中；若命中，必须说明是测试或禁止说明。

回归命令：
- `cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service && .venv/bin/python -m pytest -q`
- `cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service && .venv/bin/python -m unittest discover`
- `cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service && .venv/bin/python -m py_compile $(find app tests -name '*.py' -print)`

【非目标 / 禁止事项】
1. 禁止在 TASK-002B 中实现最终外发表结构迁移；迁移属于 TASK-002C。
2. 禁止在 TASK-002B 中实现发料 Stock Entry outbox；属于 TASK-002D。
3. 禁止在 TASK-002B 中实现回料 Stock Entry outbox；属于 TASK-002E。
4. 禁止继续使用伪 `stock_entry_name` 充当库存落账。
5. 禁止只做前端按钮隐藏，不做后端权限。
6. 禁止权限源异常时降级为静态权限或空权限列表。
7. 禁止把审计失败当作普通业务成功。
8. 禁止把数据库异常、SQL、Token、Cookie、Authorization 暴露给客户端或写入日志/审计。
9. 禁止同一交付中启动 TASK-002C/D/E。

【验收标准】
□ `subcontract:*` 权限动作已定义并可通过 `/api/auth/actions?module=subcontract` 查询。  
□ 现有外发接口全部要求登录。  
□ 现有外发接口全部接入动作权限。  
□ 外发列表按资源权限过滤。  
□ 外发写接口接入资源权限校验。  
□ 401/403/503 写安全审计。  
□ 写操作写操作审计，operator 为真实用户。  
□ 审计失败返回 `AUDIT_WRITE_FAILED` 且业务回滚。  
□ 数据库读/写/未知异常按统一错误码返回。  
□ 成功/失败响应使用统一信封，不再返回旧 `trace_id`。  
□ `SubcontractService` 不再直接 `commit()`。  
□ 发料/回料不再生成伪 `STE-ISS-*`，不伪造 ERPNext 库存成功。  
□ 权限源不可用 fail closed，不写业务事实。  
□ 日志和审计不泄露 Authorization/Cookie/token/password/secret/SQL。  
□ 新增 subcontract 权限、审计、异常测试并全量回归通过。  

【完成后回报格式】
请按以下格式回报：

═══════════════════════════════════════════════════════════
【交付报告】第 X 份
模块：外发加工管理（权限与审计基线）
工程师：Claude Codex（工程师窗口）
完成时间：YYYY-MM-DD
═══════════════════════════════════════════════════════════

【任务卡编号】
TASK-002B

【修改文件】
- ...

【核心整改】
- 权限动作：完成 / 未完成
- 资源权限：完成 / 未完成
- 安全审计：完成 / 未完成
- 操作审计：完成 / 未完成
- 统一错误信封：完成 / 未完成
- 事务边界：完成 / 未完成
- 禁止伪库存：完成 / 未完成

【自测结果】
- ...

【遗留问题】
- 无 / ...

【未解决问题（需架构师或审计官决策）】
- 无 / ...

═══════════════════════════════════════════════════════════
