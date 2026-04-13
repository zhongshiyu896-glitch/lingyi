# TASK-001H 服务端日志脱敏与测试环境隔离整改任务单

- 任务编号：TASK-001H
- 模块：BOM 管理 / 日志安全 / 测试稳定性
- 优先级：P0
- 预计工时：0.5-1 天
- 更新时间：2026-04-12 11:37 CST
- 作者：技术架构师
- 审计来源：审计意见书第 11 份，服务端普通错误日志泄露 SQLAlchemy 异常原文，测试环境变量隔离仍脆弱

════════════════════════════════════════════════════════════════════

【任务目标】

修复服务端普通错误日志直接记录 `str(exc)` 导致 SQL 原文泄露的问题，并修复测试环境变量 `setdefault()` 无法覆盖外部生产变量的问题，确保日志安全和测试可复现。

════════════════════════════════════════════════════════════════════

【问题背景】

第 11 份审计确认 TASK-001G 主线已基本闭环，但仍有 2 个必须收口的问题：

1. 数据库写失败、回滚失败、失败审计写入失败等日志仍直接记录 `str(exc)`。
2. 审计复验已在普通日志中看到 `[SQL: UPDATE ...]` 和 SQLAlchemy 异常原文。
3. 客户端响应没有泄露，但服务端普通错误日志仍泄露 SQL 细节。
4. 测试使用 `setdefault()` 设置环境变量，无法覆盖外部已有 `APP_ENV=production`、`LINGYI_PERMISSION_SOURCE=static`，导致测试导入阶段失败。

本任务只处理日志脱敏和测试环境隔离，不修改 BOM 接口路径，不修改业务功能。

════════════════════════════════════════════════════════════════════

【涉及文件】

后端修改：

- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/logging.py（如不存在则新建）
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/exceptions.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/bom_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/audit_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/permission_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/bom.py

测试修改：

- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/conftest.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_bom_exception_handling.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_bom_audit.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_logging_sanitization.py（建议新增）

════════════════════════════════════════════════════════════════════

【整改要求一：普通错误日志脱敏】

1. 禁止普通应用日志直接记录 `str(exc)`。

禁止模式：

- logger.error("... %s", exc)
- logger.error(f"... {exc}")
- logger.exception("... %s", exc)
- logger.exception(f"... {exc}")
- error_detail = str(exc) 后写入普通日志

2. 禁止普通应用日志记录 SQLAlchemy 原始异常文本。

普通日志中不得出现：

- `[SQL:`
- `[parameters:`
- `UPDATE ly_schema.`
- `INSERT INTO ly_schema.`
- `DELETE FROM ly_schema.`
- `SELECT ... FROM ly_schema.`
- 数据库连接串
- Authorization Token
- Cookie
- ERPNext API Secret
- password / passwd / secret 明文

3. 新增统一日志脱敏函数。

建议函数：

- sanitize_exception(exc) -> dict
- sanitize_log_message(message) -> str
- log_safe_error(logger, message, exc, request_id, extra)

普通日志只允许记录以下安全字段：

- error_code
- exception_type
- request_id
- module
- action
- resource_type
- resource_id
- resource_no
- user_id
- sqlstate（如可安全取得）
- db_driver_error_code（如可安全取得）

4. SQLAlchemy 异常日志规则。

当异常属于 SQLAlchemyError / DBAPIError / OperationalError / IntegrityError：

- 普通日志记录 exception_type。
- 可记录 SQLSTATE 或数据库错误码。
- 禁止记录 SQL statement。
- 禁止记录 SQL parameters。
- 禁止记录连接串。
- 禁止记录完整 traceback 中包含的 SQLAlchemy 异常原文。

5. rollback 失败日志也必须脱敏。

如果 rollback 失败：

- 不得记录 `str(rollback_exc)`。
- 不得覆盖原始错误码。
- 普通日志只记录 rollback_exception_type、request_id、原始 error_code。

6. 审计写入失败日志也必须脱敏。

如果 ly_operation_audit_log 或 ly_security_audit_log 写入失败：

- 普通日志不得记录 SQL 原文。
- 普通日志不得记录审计 payload 中的敏感字段原文。
- 返回错误码仍按既定规则处理。

7. 受限调试日志策略。

如确需保留原始异常详情，只允许满足全部条件：

- 仅 development / local 环境允许。
- 必须由显式环境变量开启，例如 `LINGYI_ALLOW_RAW_EXCEPTION_LOG=true`。
- production 环境强制禁止。
- 原始日志不得进入普通应用日志文件。
- 原始日志不得进入安全审计表。

════════════════════════════════════════════════════════════════════

【整改要求二：安全审计日志脱敏】

1. ly_security_audit_log 和 ly_operation_audit_log 不得写入完整异常原文。

2. 审计日志中异常字段只允许写：

- exception_type
- error_code
- sanitized_message
- request_id

3. sanitized_message 必须去除：

- SQL 原文
- SQL 参数
- Token
- Cookie
- password
- secret
- 数据库连接串

4. 如果无法安全脱敏，则 sanitized_message 写固定文案：

- internal error, detail redacted

════════════════════════════════════════════════════════════════════

【整改要求三：测试环境变量强制隔离】

1. 测试环境变量必须强制覆盖，不允许使用 `setdefault()`。

禁止：

- os.environ.setdefault("APP_ENV", "test")
- os.environ.setdefault("LINGYI_PERMISSION_SOURCE", "static")

必须使用：

- os.environ["APP_ENV"] = "test"
- os.environ["LINGYI_PERMISSION_SOURCE"] = "static" 或测试所需值

2. 覆盖动作必须发生在应用模块 import 前。

推荐方案：

- 在 tests/conftest.py 文件顶部、任何 app 导入前设置。
- 或提供 create_app/settings factory，让测试先设置 env 再创建 app。

3. 测试必须对外部生产变量免疫。

以下命令必须通过：

- APP_ENV=production LINGYI_PERMISSION_SOURCE=static .venv/bin/python -m pytest -q tests/test_bom_exception_handling.py

4. 测试结束后如需恢复环境变量，必须在 fixture teardown 中恢复，不能影响其他测试。

5. 生产保护逻辑不能删除。

要求：

- 正常运行生产环境时，APP_ENV=production 且 LINGYI_PERMISSION_SOURCE=static 仍必须启动失败。
- 只有测试入口可以强制覆盖为 test 环境。

════════════════════════════════════════════════════════════════════

【验收标准】

□ 模拟数据库写失败时，普通错误日志不包含 `[SQL:`。

□ 模拟数据库写失败时，普通错误日志不包含 `[parameters:`。

□ 模拟数据库写失败时，普通错误日志不包含 `UPDATE ly_schema.` / `INSERT INTO ly_schema.` / `DELETE FROM ly_schema.`。

□ 模拟 rollback 失败时，普通错误日志不包含 rollback 异常的 SQL 原文。

□ 模拟审计写入失败时，普通错误日志不包含审计 SQL 原文和审计 payload 敏感字段。

□ 安全审计表中的异常信息不包含 SQL 原文、SQL 参数、Token、Cookie、password、secret。

□ 客户端错误响应仍保持 `{code, message, data}`，且不泄露 traceback、SQL、连接串、Token、Cookie。

□ 使用 caplog 或等价方式新增测试，断言日志中不存在 `[SQL:`、`[parameters:`、`Authorization`、`Cookie`、`password`、`secret`。

□ tests/conftest.py 或测试 app factory 中不再使用 `os.environ.setdefault()` 设置关键测试环境变量。

□ 执行 `APP_ENV=production LINGYI_PERMISSION_SOURCE=static .venv/bin/python -m pytest -q tests/test_bom_exception_handling.py` 通过。

□ 正常生产启动保护仍有效：非测试入口下 `APP_ENV=production` 且 `LINGYI_PERMISSION_SOURCE=static` 必须启动失败。

□ `.venv/bin/python -m pytest -q` 连续两次通过。

□ `.venv/bin/python -m unittest discover` 连续两次通过。

□ `.venv/bin/python -m py_compile` 检查通过。

════════════════════════════════════════════════════════════════════

【禁止事项】

1. 禁止普通日志直接记录 `str(exc)`。

2. 禁止普通日志记录 SQLAlchemy 原始异常文本。

3. 禁止普通日志记录 SQL statement、SQL parameters、数据库连接串。

4. 禁止普通日志记录完整 Authorization、Cookie、Token、password、secret。

5. 禁止为了让测试通过删除生产环境静态权限禁用保护。

6. 禁止测试继续使用 `os.environ.setdefault()` 作为关键环境变量设置方式。

7. 禁止修改 BOM 接口路径和正常成功响应结构。

════════════════════════════════════════════════════════════════════

【完成后回复格式】

请工程师完成后按以下格式回复：

TASK-001H 已完成。

已修改文件：
- [列出实际修改文件]

核心整改：
- 普通错误日志已禁止记录 str(exc)
- SQLAlchemy 异常日志已脱敏，不输出 SQL 原文和参数
- rollback 失败日志已脱敏
- 审计写入失败日志已脱敏
- 测试环境变量已从 setdefault 改为强制覆盖
- 生产环境静态权限禁用保护仍保留

自测结果：
- 数据库写失败日志不含 [SQL:]：通过 / 不通过
- rollback 失败日志不含 SQL 原文：通过 / 不通过
- 审计写入失败日志不含 SQL 原文：通过 / 不通过
- 安全审计表不含 Token/Cookie/password/secret：通过 / 不通过
- 外部 APP_ENV=production 注入下 pytest 指定文件通过：通过 / 不通过
- 生产启动保护仍有效：通过 / 不通过
- .venv/bin/python -m pytest -q 连续两次：通过 / 不通过
- .venv/bin/python -m unittest discover 连续两次：通过 / 不通过

遗留问题：
- 无 / 有，说明原因
