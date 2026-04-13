# TASK-001J Request ID 语义敏感词拦截与单测隔离整改任务单

- 任务编号：TASK-001J
- 模块：BOM 管理 / 请求追踪 / 日志安全 / 测试稳定性
- 优先级：P1
- 预计工时：0.5 天
- 更新时间：2026-04-12 12:07 CST
- 作者：技术架构师
- 审计来源：审计意见书第 13 份，`normalize_request_id()` 仅做字符白名单，仍放行语义敏感 request_id；单文件 unittest 在外部生产变量下注入失败

════════════════════════════════════════════════════════════════════

【任务目标】

升级 `normalize_request_id()`，在字符白名单基础上增加语义敏感词拦截，禁止 `token-password-secret-cookie-authorization`、`Bearer.abc123_token_secret` 等“字符合法但语义敏感”的 request_id 进入响应头、普通日志和审计表；同时修复 `tests/test_request_id_sanitization.py` 单文件 unittest 在外部生产变量下导入失败的问题。

════════════════════════════════════════════════════════════════════

【问题背景】

第 13 份审计发现：

1. `normalize_request_id()` 当前只校验字符白名单。
2. `X-Request-ID: token-password-secret-cookie-authorization` 会原样进入响应头和安全审计表。
3. `X-Request-ID: Bearer.abc123_token_secret` 这类值字符合法，但语义上明显包含敏感凭证关键词。
4. `tests/test_request_id_sanitization.py` 单文件 `unittest` 在外部 `APP_ENV=production LINGYI_PERMISSION_SOURCE=static` 注入下仍会导入失败。

本任务不改 BOM 业务功能，只收口 request_id 安全边界和测试隔离。

════════════════════════════════════════════════════════════════════

【涉及文件】

后端修改：

- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/request_id.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/main.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/logging.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/audit_service.py

测试修改：

- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_request_id_sanitization.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_logging_sanitization.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_bom_audit.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_env.py（建议新增）
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/conftest.py（如存在则同步）

════════════════════════════════════════════════════════════════════

【整改要求一：request_id 增加语义敏感词拦截】

1. `normalize_request_id()` 必须先做空值、长度、字符白名单校验，再做语义敏感词校验。

2. 字符白名单继续保留。

允许字符：

- A-Z
- a-z
- 0-9
- `_`
- `-`
- `.`

长度限制：

- 1 到 64 个字符

3. 新增语义敏感词黑名单。

必须大小写不敏感拦截以下关键词：

- authorization
- bearer
- token
- cookie
- set-cookie
- password
- passwd
- secret
- session
- sessionid
- api-key
- api_key
- access-key
- access_key
- access-token
- access_token
- refresh-token
- refresh_token

4. 命中语义敏感词时，必须整体丢弃原 request_id，并生成新的安全 request_id。

5. 禁止把敏感词替换、截断、mask 后继续作为 request_id 使用。

6. 生成的新 request_id 推荐使用：

- uuid.uuid4().hex

7. 生成的新 request_id 必须满足：

- 不包含敏感词
- 长度不超过 64
- 符合字符白名单

════════════════════════════════════════════════════════════════════

【整改要求二：响应头、日志、审计表只使用规范化 request_id】

1. main.py 中间件必须保证响应头 `X-Request-ID` 只返回规范化后的 request_id。

2. 如果外部传入 request_id 命中敏感词，响应头不得返回原值。

3. 普通日志不得记录原始 request_id。

4. ly_security_audit_log 不得记录原始 request_id。

5. ly_operation_audit_log 不得记录原始 request_id。

6. audit_service.py 和 logging.py 不得自行读取原始 `X-Request-ID`。

7. 如需记录替换原因，只能记录安全枚举值：

- request_id_was_invalid = true
- request_id_invalid_reason = sensitive_keyword
- request_id_source = generated

禁止记录原始非法 request_id。

════════════════════════════════════════════════════════════════════

【整改要求三：单文件 unittest 测试环境隔离】

1. 必须修复以下命令导入失败问题：

- APP_ENV=production LINGYI_PERMISSION_SOURCE=static .venv/bin/python -m unittest tests.test_request_id_sanitization

2. 注意：`python -m unittest tests.test_request_id_sanitization` 不会自动按 pytest 方式加载 `conftest.py`。

3. 推荐新增测试环境初始化文件：

- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_env.py

建议函数：

- configure_test_env()

函数必须强制覆盖：

- os.environ["APP_ENV"] = "test"
- os.environ["LINGYI_PERMISSION_SOURCE"] = "static"
- 其他测试必要环境变量

4. 所有会直接或间接 import app.main / app settings 的 unittest 测试文件，必须在导入业务模块前执行：

- from tests.test_env import configure_test_env
- configure_test_env()

5. 生产保护逻辑不能删除。

要求：

- 非测试入口下，APP_ENV=production 且 LINGYI_PERMISSION_SOURCE=static 仍必须启动失败。
- 测试入口下，测试环境初始化必须覆盖外部变量，确保单文件 unittest 可执行。

════════════════════════════════════════════════════════════════════

【必须覆盖的测试样例】

1. 字符合法但语义敏感：

输入：

- token-password-secret-cookie-authorization

期望：

- 被替换为新 request_id。
- 响应头不包含原值。
- 普通日志不包含原值。
- ly_security_audit_log 不包含原值。

2. Bearer + token + secret：

输入：

- Bearer.abc123_token_secret

期望：

- 被替换为新 request_id。
- 响应头不包含 Bearer。
- 日志和审计表不包含 token / secret 原文组合。

3. session / cookie：

输入：

- sessionid.cookie.abc123

期望：

- 被替换为新 request_id。
- 日志和审计表不包含 sessionid / cookie。

4. password / passwd：

输入：

- passwd.password.123456

期望：

- 被替换为新 request_id。
- 日志和审计表不包含 password / passwd。

5. 合法业务 request_id：

输入：

- req-20260412.ABC_001

期望：

- 如未命中敏感词，允许保留。

6. 缺失 request_id：

输入：

- 无 X-Request-ID

期望：

- 自动生成安全 request_id。

7. 外部生产变量注入下单文件 unittest：

命令：

- APP_ENV=production LINGYI_PERMISSION_SOURCE=static .venv/bin/python -m unittest tests.test_request_id_sanitization

期望：

- 测试通过。
- 不在导入阶段失败。

════════════════════════════════════════════════════════════════════

【验收标准】

□ `normalize_request_id("token-password-secret-cookie-authorization")` 不返回原值。

□ `normalize_request_id("Bearer.abc123_token_secret")` 不返回原值。

□ `normalize_request_id("sessionid.cookie.abc123")` 不返回原值。

□ `normalize_request_id("passwd.password.123456")` 不返回原值。

□ `normalize_request_id("req-20260412.ABC_001")` 返回原值。

□ 恶意敏感词 request_id 进入接口后，响应头 `X-Request-ID` 不包含原始值。

□ 恶意敏感词 request_id 触发错误日志后，普通日志不包含原始值，也不包含 token / password / secret / cookie / authorization / bearer 原文组合。

□ 恶意敏感词 request_id 触发安全审计后，ly_security_audit_log 不包含原始值。

□ 恶意敏感词 request_id 触发操作审计后，ly_operation_audit_log 不包含原始值。

□ logging.py 和 audit_service.py 只接收规范化后的 request_id，不直接读取原始 header。

□ 使用 `rg "headers.get\(.*X-Request-ID" /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app` 检查，除 main.py 中间件外无其他直接读取。

□ `APP_ENV=production LINGYI_PERMISSION_SOURCE=static .venv/bin/python -m unittest tests.test_request_id_sanitization` 通过。

□ `APP_ENV=production LINGYI_PERMISSION_SOURCE=static .venv/bin/python -m pytest -q tests/test_request_id_sanitization.py` 通过。

□ 默认 `.venv/bin/python -m pytest -q` 通过。

□ 默认 `.venv/bin/python -m unittest discover` 通过。

□ `.venv/bin/python -m py_compile` 检查通过。

□ 非测试入口下生产保护仍有效：APP_ENV=production 且 LINGYI_PERMISSION_SOURCE=static 直接 import app.main 必须失败。

════════════════════════════════════════════════════════════════════

【禁止事项】

1. 禁止仅靠字符白名单判断 request_id 安全。

2. 禁止语义敏感 request_id 原样进入响应头。

3. 禁止语义敏感 request_id 原样进入普通日志。

4. 禁止语义敏感 request_id 原样进入 ly_security_audit_log 或 ly_operation_audit_log。

5. 禁止把敏感词 mask 后继续作为 request_id 使用。

6. 禁止测试继续依赖 pytest 的 conftest 来保证 unittest 单文件导入。

7. 禁止删除生产环境静态权限禁用保护。

8. 禁止修改 BOM 接口路径和正常成功响应结构。

════════════════════════════════════════════════════════════════════

【完成后回复格式】

请工程师完成后按以下格式回复：

TASK-001J 已完成。

已修改文件：
- [列出实际修改文件]

核心整改：
- normalize_request_id 已增加语义敏感词拦截
- token/password/secret/cookie/authorization/bearer 等 request_id 会被整体替换
- 响应头 X-Request-ID 只返回规范化后的 request_id
- 普通日志和审计表不记录原始敏感 request_id
- tests/test_request_id_sanitization.py 单文件 unittest 已可在外部生产变量下注入运行
- 生产环境静态权限禁用保护仍保留

自测结果：
- token-password-secret-cookie-authorization 被替换：通过 / 不通过
- Bearer.abc123_token_secret 被替换：通过 / 不通过
- sessionid.cookie.abc123 被替换：通过 / 不通过
- passwd.password.123456 被替换：通过 / 不通过
- req-20260412.ABC_001 保留：通过 / 不通过
- 响应头不返回原始敏感 request_id：通过 / 不通过
- 日志和审计表不记录原始敏感 request_id：通过 / 不通过
- 外部生产变量下 unittest 单文件通过：通过 / 不通过
- 外部生产变量下 pytest 单文件通过：通过 / 不通过
- 默认 pytest/unittest/py_compile 通过：通过 / 不通过

遗留问题：
- 无 / 有，说明原因
