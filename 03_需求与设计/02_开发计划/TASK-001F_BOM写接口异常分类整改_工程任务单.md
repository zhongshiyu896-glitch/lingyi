# TASK-001F BOM 写接口异常分类整改任务单

- 任务编号：TASK-001F
- 模块：BOM 管理 / 审计服务 / 异常处理
- 优先级：P0
- 预计工时：0.5-1 天
- 更新时间：2026-04-12 11:01 CST
- 作者：技术架构师
- 审计来源：审计意见书第 9 份，BOM 写接口把所有未知异常统一返回为 `AUDIT_WRITE_FAILED`

════════════════════════════════════════════════════════════════════

【任务目标】

拆分 BOM 写接口异常分类，禁止把业务异常、数据库异常、未知异常统一包装成 `AUDIT_WRITE_FAILED`，确保错误码能准确反映真实失败原因，便于排障和审计复查。

════════════════════════════════════════════════════════════════════

【问题背景】

当前 BOM 写接口仍把所有未知异常统一返回为 `AUDIT_WRITE_FAILED`。

这会造成：

1. 业务校验失败被误判为审计写入失败。
2. 数据库写入失败被误判为审计写入失败。
3. 未知程序异常被误判为审计写入失败。
4. 审计意见无法判断到底是“审计系统失败”还是“业务系统失败”。
5. 工程排障会被错误码误导。

`AUDIT_WRITE_FAILED` 只能用于审计日志写入失败，不允许作为 BOM 写接口的通用兜底错误码。

════════════════════════════════════════════════════════════════════

【涉及文件】

后端修改：

- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/bom.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/bom_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/audit_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/exceptions.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/error_codes.py（如已有错误码文件则修改已有文件）

测试新增或修改：

- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_bom_exception_handling.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_bom_audit.py

════════════════════════════════════════════════════════════════════

【整改接口范围】

必须覆盖全部 BOM 写接口：

| 接口 | 方法 | 路径 | 异常分类要求 |
| --- | --- | --- | --- |
| 创建 BOM | POST | /api/bom/ | 区分业务校验、数据库异常、审计异常、未知异常 |
| 更新 BOM 草稿 | PUT | /api/bom/{bom_id} | 区分业务校验、数据库异常、审计异常、未知异常 |
| 发布 BOM | POST | /api/bom/{bom_id}/activate | 区分业务校验、数据库异常、审计异常、未知异常 |
| 停用 BOM | POST | /api/bom/{bom_id}/deactivate | 区分业务校验、数据库异常、审计异常、未知异常 |
| 设置默认 BOM | POST | /api/bom/{bom_id}/set-default | 区分业务校验、数据库异常、审计异常、未知异常 |

════════════════════════════════════════════════════════════════════

【错误码规范】

必须至少区分以下错误码：

| 错误码 | HTTP 状态 | 使用场景 |
| --- | --- | --- |
| BOM_NOT_FOUND | 404 | BOM 不存在 |
| BOM_ITEM_NOT_FOUND | 400 | ERPNext Item 不存在或已禁用 |
| BOM_INVALID_QTY | 400 | 数量非法 |
| BOM_INVALID_LOSS_RATE | 400 | 损耗率非法 |
| BOM_OPERATION_RATE_REQUIRED | 400 | 工序工价缺失 |
| BOM_PUBLISHED_LOCKED | 409 | 已发布 BOM 禁止修改 |
| BOM_DEFAULT_REQUIRES_ACTIVE | 400 | 非 active BOM 不能设默认 |
| BOM_DEFAULT_CONFLICT | 409 | 默认 BOM 并发冲突或唯一索引冲突 |
| AUTH_UNAUTHORIZED | 401 | 未登录或登录失效 |
| AUTH_FORBIDDEN | 403 | 无动作权限或资源权限 |
| PERMISSION_SOURCE_UNAVAILABLE | 503 | ERPNext 权限来源不可用 |
| AUDIT_WRITE_FAILED | 500 | 审计日志写入失败，且仅限审计写入失败 |
| DATABASE_WRITE_FAILED | 500 | BOM 主业务数据库写入失败 |
| DATABASE_READ_FAILED | 500 | BOM 主业务数据库读取失败 |
| BOM_INTERNAL_ERROR | 500 | 未知程序异常 |

要求：

- `AUDIT_WRITE_FAILED` 只能由 audit_service 写审计失败时抛出。
- SQLAlchemy / 数据库异常不得返回 `AUDIT_WRITE_FAILED`。
- 业务校验异常不得返回 `AUDIT_WRITE_FAILED`。
- 未知异常不得返回 `AUDIT_WRITE_FAILED`。

════════════════════════════════════════════════════════════════════

【异常处理规则】

1. 业务异常原样返回业务错误码。

示例：

- BOM 不存在：BOM_NOT_FOUND
- 已发布 BOM 修改：BOM_PUBLISHED_LOCKED
- 默认 BOM 冲突：BOM_DEFAULT_CONFLICT

2. 审计写入异常只在 audit_service 层产生。

要求：

- audit_service 写入 `ly_operation_audit_log` 或 `ly_security_audit_log` 失败时，抛出 `AuditWriteFailed`。
- 路由层或服务层捕获 `AuditWriteFailed` 后返回 `AUDIT_WRITE_FAILED`。
- 不允许其他异常伪装成 `AuditWriteFailed`。

3. 数据库异常必须单独分类。

建议：

- 主业务写入失败：DATABASE_WRITE_FAILED
- 主业务读取失败：DATABASE_READ_FAILED
- 唯一索引冲突且能识别为默认 BOM 冲突：BOM_DEFAULT_CONFLICT

4. 未知异常必须返回 BOM_INTERNAL_ERROR。

要求：

- 捕获未知 Exception 时，返回 `BOM_INTERNAL_ERROR`。
- 服务端日志记录 exception_type、exception_message、request_id。
- 客户端响应不得暴露堆栈信息。

5. 事务规则。

- BOM 业务写入成功但操作审计写入失败：整体回滚，返回 `AUDIT_WRITE_FAILED`。
- BOM 业务写入失败：不得写成功审计，返回对应业务或数据库错误码。
- 权限拒绝审计失败：不得放行请求，至少写服务端 error 日志。

6. 错误响应格式不变。

统一返回：

{
  "code": "错误码",
  "message": "错误说明",
  "data": {}
}

════════════════════════════════════════════════════════════════════

【推荐实现结构】

1. 在 exceptions.py 中定义明确异常类：

- AppException
- BusinessException
- PermissionException
- PermissionSourceUnavailable
- AuditWriteFailed
- DatabaseReadFailed
- DatabaseWriteFailed
- BomInternalError

2. 在 audit_service.py 中只对审计写入失败抛 `AuditWriteFailed`。

3. 在 bom_service.py 中：

- 业务规则失败抛 BusinessException。
- 数据库读写失败抛 DatabaseReadFailed / DatabaseWriteFailed。
- 默认 BOM 唯一索引冲突转换为 BOM_DEFAULT_CONFLICT。

4. 在 routers/bom.py 中：

- 优先捕获 AppException，按异常自带 code/status 返回。
- 再捕获未知 Exception，返回 BOM_INTERNAL_ERROR。
- 禁止 `except Exception: raise AUDIT_WRITE_FAILED`。

════════════════════════════════════════════════════════════════════

【验收标准】

□ 模拟 audit_service 写操作审计失败时，POST /api/bom/ 返回 500，code = AUDIT_WRITE_FAILED。

□ 模拟 audit_service 写安全审计失败时，不放行原本应拒绝的请求，并写服务端 error 日志。

□ 模拟 BOM 主表数据库写入失败时，POST /api/bom/ 返回 500，code = DATABASE_WRITE_FAILED，不返回 AUDIT_WRITE_FAILED。

□ 模拟 BOM 主表数据库读取失败时，GET /api/bom/{bom_id} 返回 500，code = DATABASE_READ_FAILED，不返回 AUDIT_WRITE_FAILED。

□ 修改 active BOM 草稿时，PUT /api/bom/{bom_id} 返回 409，code = BOM_PUBLISHED_LOCKED。

□ 默认 BOM 唯一索引冲突时，POST /api/bom/{bom_id}/set-default 返回 409，code = BOM_DEFAULT_CONFLICT。

□ 模拟未知 RuntimeError 时，BOM 写接口返回 500，code = BOM_INTERNAL_ERROR，不返回 AUDIT_WRITE_FAILED。

□ 客户端错误响应不包含 Python traceback、SQL 原文、数据库连接串、Token、Cookie。

□ 使用 rg "AUDIT_WRITE_FAILED" /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app 检查，只有 audit_service 或 AuditWriteFailed 映射处使用该错误码。

□ 使用 rg "except Exception" /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/bom.py 检查，不存在把未知异常统一转成 AUDIT_WRITE_FAILED 的逻辑。

□ python -m py_compile 检查通过。

□ python -m pytest 或 python -m unittest 中异常分类测试可执行。

════════════════════════════════════════════════════════════════════

【禁止事项】

1. 禁止把所有 Exception 包装成 AUDIT_WRITE_FAILED。

2. 禁止把数据库异常包装成 AUDIT_WRITE_FAILED。

3. 禁止把业务校验异常包装成 AUDIT_WRITE_FAILED。

4. 禁止把未知异常返回给客户端原始堆栈。

5. 禁止为了通过测试删除审计写入失败时的事务回滚。

6. 禁止改变 BOM 接口路径和正常成功响应结构。

════════════════════════════════════════════════════════════════════

【完成后回复格式】

请工程师完成后按以下格式回复：

TASK-001F 已完成。

已修改文件：
- [列出实际修改文件]

核心整改：
- AUDIT_WRITE_FAILED 已限定为审计写入失败专用错误码
- 业务异常已返回业务错误码
- 数据库读写异常已返回 DATABASE_READ_FAILED / DATABASE_WRITE_FAILED
- 未知异常已返回 BOM_INTERNAL_ERROR
- 客户端不暴露 traceback / SQL / Token / Cookie

自测结果：
- 审计写入失败返回 AUDIT_WRITE_FAILED：通过 / 不通过
- 主业务数据库写入失败返回 DATABASE_WRITE_FAILED：通过 / 不通过
- 主业务数据库读取失败返回 DATABASE_READ_FAILED：通过 / 不通过
- 未知异常返回 BOM_INTERNAL_ERROR：通过 / 不通过
- active BOM 修改返回 BOM_PUBLISHED_LOCKED：通过 / 不通过
- 默认 BOM 唯一冲突返回 BOM_DEFAULT_CONFLICT：通过 / 不通过
- rg 检查无 except Exception -> AUDIT_WRITE_FAILED：通过 / 不通过
- python -m pytest 或 python -m unittest 可执行：通过 / 不通过

遗留问题：
- 无 / 有，说明原因
