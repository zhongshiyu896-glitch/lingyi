# TASK-001G BOM 提交阶段数据库异常分类整改任务单

- 任务编号：TASK-001G
- 模块：BOM 管理 / 异常处理 / 测试稳定性
- 优先级：P0
- 预计工时：0.5-1 天
- 更新时间：2026-04-12 11:22 CST
- 作者：技术架构师
- 审计来源：审计意见书第 10 份，`session.commit()` 阶段数据库写入失败仍落到 `BOM_INTERNAL_ERROR`

════════════════════════════════════════════════════════════════════

【任务目标】

修复 BOM 写接口在 `session.commit()` 阶段发生数据库写入失败时错误归类为 `BOM_INTERNAL_ERROR` 的问题，统一归类为 `DATABASE_WRITE_FAILED`；同时收口审计快照异常信封和测试 import-time 环境变量顺序脆弱性。

════════════════════════════════════════════════════════════════════

【问题背景】

第 10 份审计确认 TASK-001F 已完成大部分异常分类整改，但仍保留 3 个问题：

1. `session.commit()` 阶段的数据库写入失败仍会落到 `BOM_INTERNAL_ERROR`。
2. 审计快照 `snapshot_resource()` 部分在 `try` 外，异常可能绕过统一错误信封。
3. 测试存在 import-time 环境变量顺序脆弱性。

其中第 1 项优先级最高：提交失败是主业务数据库写失败，不是未知异常，必须返回 `DATABASE_WRITE_FAILED`。

════════════════════════════════════════════════════════════════════

【涉及文件】

后端修改：

- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/bom_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/audit_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/exceptions.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/error_codes.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/bom.py

测试修改：

- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_bom_exception_handling.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_bom_audit.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/conftest.py（如存在）

════════════════════════════════════════════════════════════════════

【整改范围】

必须覆盖全部 BOM 写接口：

| 接口 | 方法 | 路径 |
| --- | --- | --- |
| 创建 BOM | POST | /api/bom/ |
| 更新 BOM 草稿 | PUT | /api/bom/{bom_id} |
| 发布 BOM | POST | /api/bom/{bom_id}/activate |
| 停用 BOM | POST | /api/bom/{bom_id}/deactivate |
| 设置默认 BOM | POST | /api/bom/{bom_id}/set-default |

════════════════════════════════════════════════════════════════════

【整改要求一：commit 阶段数据库写失败归类】

1. 所有 BOM 写接口中，`session.flush()`、`session.commit()`、事务上下文退出时触发的数据库异常，都必须归类为：

- code = DATABASE_WRITE_FAILED
- HTTP 状态 = 500

2. 以下异常类型必须进入数据库写失败分支：

- SQLAlchemyError
- IntegrityError
- OperationalError
- DBAPIError
- commit 时由数据库驱动抛出的异常

3. 唯一索引冲突需要特殊识别。

如果 `IntegrityError` 可识别为默认 BOM 唯一索引冲突：

- uk_ly_apparel_bom_one_active_default

则返回：

- code = BOM_DEFAULT_CONFLICT
- HTTP 状态 = 409

否则返回：

- code = DATABASE_WRITE_FAILED
- HTTP 状态 = 500

4. 禁止 commit 失败落到未知异常兜底。

以下结果不允许出现：

- session.commit() 失败返回 BOM_INTERNAL_ERROR
- session.commit() 失败返回 AUDIT_WRITE_FAILED
- session.commit() 失败返回 200

5. 事务回滚要求。

- commit 失败后必须 rollback。
- rollback 失败也不得覆盖原始错误码。
- 服务端日志需要记录原始异常类型、request_id、接口路径。

════════════════════════════════════════════════════════════════════

【整改要求二：snapshot_resource() 纳入统一错误信封】

1. BOM 审计快照函数 `snapshot_resource()` 不得放在统一异常处理之外。

2. 如果 `snapshot_resource()` 读取业务数据失败，应按场景分类：

- 数据库读取失败：DATABASE_READ_FAILED
- BOM 不存在：BOM_NOT_FOUND
- 未知快照异常：BOM_INTERNAL_ERROR

3. 如果 `snapshot_resource()` 是为了写审计前后快照，且快照失败导致审计无法完成：

- 不允许返回裸异常。
- 不允许绕过统一响应格式。
- 必须返回统一错误信封 `{code, message, data}`。

4. 客户端不得看到 Python traceback、SQL 原文、连接串、Token、Cookie。

════════════════════════════════════════════════════════════════════

【整改要求三：测试环境变量顺序稳定】

1. 测试依赖的环境变量必须在应用模块 import 前完成设置。

2. 禁止测试用例依赖“先 import app 再 monkeypatch env”的隐式顺序。

3. 推荐处理方式：

- 在 tests/conftest.py 顶部设置测试环境变量。
- 或提供 app factory，让测试在设置 env 后创建 app。
- 或将 settings 读取延迟到运行时，并提供测试专用 override。

4. 测试必须能重复执行。

要求以下命令连续执行两次结果一致：

- .venv/bin/python -m pytest -q
- .venv/bin/python -m unittest discover

════════════════════════════════════════════════════════════════════

【错误码边界】

| 场景 | 正确错误码 | 禁止错误码 |
| --- | --- | --- |
| session.commit() 数据库写失败 | DATABASE_WRITE_FAILED | BOM_INTERNAL_ERROR / AUDIT_WRITE_FAILED |
| session.flush() 数据库写失败 | DATABASE_WRITE_FAILED | BOM_INTERNAL_ERROR / AUDIT_WRITE_FAILED |
| 默认 BOM 唯一索引冲突 | BOM_DEFAULT_CONFLICT | DATABASE_WRITE_FAILED / BOM_INTERNAL_ERROR |
| snapshot_resource() 数据库读取失败 | DATABASE_READ_FAILED | 裸异常 / BOM_INTERNAL_ERROR |
| snapshot_resource() 未知异常 | BOM_INTERNAL_ERROR | 裸异常 |
| 审计日志写入失败 | AUDIT_WRITE_FAILED | DATABASE_WRITE_FAILED / BOM_INTERNAL_ERROR |

════════════════════════════════════════════════════════════════════

【验收标准】

□ 模拟 `session.commit()` 抛 SQLAlchemyError 时，POST /api/bom/ 返回 500，code = DATABASE_WRITE_FAILED。

□ 模拟 `session.commit()` 抛 SQLAlchemyError 时，PUT /api/bom/{bom_id} 返回 500，code = DATABASE_WRITE_FAILED。

□ 模拟 `session.commit()` 抛 SQLAlchemyError 时，POST /api/bom/{bom_id}/activate 返回 500，code = DATABASE_WRITE_FAILED。

□ 模拟 `session.commit()` 抛 SQLAlchemyError 时，POST /api/bom/{bom_id}/deactivate 返回 500，code = DATABASE_WRITE_FAILED。

□ 模拟 `session.commit()` 抛 SQLAlchemyError 时，POST /api/bom/{bom_id}/set-default 返回 500，code = DATABASE_WRITE_FAILED。

□ 模拟默认 BOM 部分唯一索引冲突 `uk_ly_apparel_bom_one_active_default` 时，返回 409，code = BOM_DEFAULT_CONFLICT。

□ 模拟 `snapshot_resource()` 数据库读取失败时，返回统一错误信封，code = DATABASE_READ_FAILED。

□ 模拟 `snapshot_resource()` 未知异常时，返回统一错误信封，code = BOM_INTERNAL_ERROR。

□ 所有错误响应均为 `{code, message, data}` 结构。

□ 错误响应不包含 traceback、SQL 原文、数据库连接串、Token、Cookie。

□ commit 失败后执行 rollback，且 rollback 失败不覆盖原始 DATABASE_WRITE_FAILED。

□ `.venv/bin/python -m pytest -q` 通过。

□ `.venv/bin/python -m unittest discover` 通过。

□ 连续两次执行测试结果一致，不受 import-time 环境变量顺序影响。

□ 使用 `rg "BOM_INTERNAL_ERROR" /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app` 检查，commit 数据库异常未被归入 BOM_INTERNAL_ERROR。

════════════════════════════════════════════════════════════════════

【禁止事项】

1. 禁止 `session.commit()` 失败返回 `BOM_INTERNAL_ERROR`。

2. 禁止 `session.commit()` 失败返回 `AUDIT_WRITE_FAILED`。

3. 禁止为了通过测试删除 commit 或跳过数据库写入。

4. 禁止 `snapshot_resource()` 抛出裸异常给客户端。

5. 禁止客户端响应暴露 traceback、SQL 原文、数据库连接串、Token、Cookie。

6. 禁止测试依赖不可控的 import 顺序。

7. 禁止修改 BOM 接口路径和正常成功响应结构。

════════════════════════════════════════════════════════════════════

【完成后回复格式】

请工程师完成后按以下格式回复：

TASK-001G 已完成。

已修改文件：
- [列出实际修改文件]

核心整改：
- session.commit() 阶段数据库写失败已归类为 DATABASE_WRITE_FAILED
- 默认 BOM 唯一索引冲突已归类为 BOM_DEFAULT_CONFLICT
- snapshot_resource() 已纳入统一错误信封
- 测试 import-time 环境变量顺序已稳定

自测结果：
- commit 失败返回 DATABASE_WRITE_FAILED：通过 / 不通过
- 默认 BOM 唯一索引冲突返回 BOM_DEFAULT_CONFLICT：通过 / 不通过
- snapshot_resource() 数据库读取失败返回 DATABASE_READ_FAILED：通过 / 不通过
- snapshot_resource() 未知异常返回 BOM_INTERNAL_ERROR：通过 / 不通过
- 错误响应不暴露敏感信息：通过 / 不通过
- .venv/bin/python -m pytest -q：通过 / 不通过
- .venv/bin/python -m unittest discover：通过 / 不通过
- 连续两次测试结果一致：通过 / 不通过

遗留问题：
- 无 / 有，说明原因
