# TASK-001I Request ID 白名单校验与脱敏整改任务单

- 任务编号：TASK-001I
- 模块：BOM 管理 / 请求追踪 / 日志安全 / 审计安全
- 优先级：P1
- 预计工时：0.5 天
- 更新时间：2026-04-12 11:54 CST
- 作者：技术架构师
- 审计来源：审计意见书第 12 份，`X-Request-ID/request_id` 未做统一白名单校验或脱敏

════════════════════════════════════════════════════════════════════

【任务目标】

新增统一 `normalize_request_id()`，对外部传入的 `X-Request-ID/request_id` 做白名单校验、长度限制和非法值替换，确保日志、审计表、错误响应上下文只使用规范化后的安全 request_id。

════════════════════════════════════════════════════════════════════

【问题背景】

审计发现 `X-Request-ID/request_id` 仍未做统一白名单校验或脱敏，会原样进入错误日志和审计上下文。

已发现风险位置：

- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/main.py:81
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/logging.py:126
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/audit_service.py:41

风险场景：

1. 恶意请求头注入换行，污染日志格式。
2. 恶意请求头伪造 `[SQL: ...]`，干扰安全审计判断。
3. 恶意请求头携带 Token / Cookie / password / secret，被写入普通日志或审计表。
4. 超长 request_id 导致日志膨胀或审计表异常。

════════════════════════════════════════════════════════════════════

【涉及文件】

后端修改：

- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/main.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/logging.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/audit_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/request_id.py（建议新增）

测试新增或修改：

- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_request_id_sanitization.py（建议新增）
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_logging_sanitization.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_bom_audit.py

════════════════════════════════════════════════════════════════════

【整改要求一：新增 normalize_request_id()】

1. 新增统一函数：

- normalize_request_id(raw_request_id: str | None) -> str

2. 白名单规则：

允许字符：

- A-Z
- a-z
- 0-9
- `_`
- `-`
- `.`

允许长度：

- 最小 1 个字符
- 最大 64 个字符

推荐正则：

- `^[A-Za-z0-9_.-]{1,64}$`

3. 处理规则：

- raw_request_id 为空：生成新的安全 request_id。
- raw_request_id 不符合白名单：丢弃原值，生成新的安全 request_id。
- raw_request_id 超长：丢弃原值，生成新的安全 request_id。
- raw_request_id 合法：使用原值。

4. 生成规则：

建议使用：

- uuid.uuid4().hex

要求生成值也必须符合白名单和长度规则。

5. 禁止对非法 request_id 做“部分清洗后继续使用”。

原因：部分清洗可能造成追踪 ID 碰撞或误导排查。

非法值必须整体丢弃并重新生成。

════════════════════════════════════════════════════════════════════

【整改要求二：统一 request_id 来源】

1. main.py 中请求中间件必须统一处理 request_id。

流程：

- 从请求头读取 `X-Request-ID`。
- 调用 `normalize_request_id()`。
- 将规范化后的 request_id 写入 `request.state.request_id`。
- 响应头 `X-Request-ID` 只返回规范化后的 request_id。

2. 后续所有模块只能读取：

- request.state.request_id

禁止后续模块再次读取原始请求头：

- request.headers.get("X-Request-ID")

3. logging.py 必须只接受规范化后的 request_id。

4. audit_service.py 必须只接受规范化后的 request_id。

5. 如果某处没有 request.state.request_id，必须生成新的安全 request_id，不得回退使用原始 header。

════════════════════════════════════════════════════════════════════

【整改要求三：日志与审计禁止记录原始 request_id】

1. 普通错误日志禁止记录原始 `X-Request-ID`。

2. ly_security_audit_log 禁止记录原始 `X-Request-ID`。

3. ly_operation_audit_log 禁止记录原始 `X-Request-ID`。

4. 如果 request_id 非法，可以记录以下安全字段：

- request_id_was_invalid = true
- request_id_source = generated

5. 禁止记录非法 request_id 原文。

尤其禁止出现：

- 换行符
- `[SQL:`
- `[parameters:`
- Authorization
- Cookie
- password
- secret
- SQL 语句
- JSON 注入片段
- HTML / script 片段

════════════════════════════════════════════════════════════════════

【恶意 request_id 测试样例】

必须至少覆盖以下输入：

1. `abc\n[SQL: UPDATE ly_schema.ly_apparel_bom SET status='active']`

期望：丢弃原值，生成安全 request_id，日志和审计中不出现 `[SQL:`。

2. `Bearer abc.def.ghi`

期望：丢弃原值，日志和审计中不出现 `Bearer`。

3. `cookie=sessionid=abc123`

期望：丢弃原值，日志和审计中不出现 `cookie` 或 `sessionid`。

4. `password=123456`

期望：丢弃原值，日志和审计中不出现 `password`。

5. `<script>alert(1)</script>`

期望：丢弃原值，日志和审计中不出现 `<script>`。

6. 超过 64 字符的字符串。

期望：丢弃原值，生成安全 request_id。

7. 合法值 `req-20260412.ABC_001`

期望：保留原值。

════════════════════════════════════════════════════════════════════

【验收标准】

□ 新增或确认存在 `normalize_request_id()`，并由 main.py 请求中间件统一调用。

□ 合法 `X-Request-ID: req-20260412.ABC_001` 被保留，并写入 `request.state.request_id`。

□ 缺失 `X-Request-ID` 时，系统生成符合 `^[A-Za-z0-9_.-]{1,64}$` 的 request_id。

□ 含换行的恶意 `X-Request-ID` 被丢弃并重新生成。

□ 含 `[SQL:` 的恶意 `X-Request-ID` 不出现在普通日志中。

□ 含 `[SQL:` 的恶意 `X-Request-ID` 不出现在 ly_security_audit_log 中。

□ 含 Authorization / Bearer 的恶意 `X-Request-ID` 不出现在普通日志或审计表中。

□ 含 Cookie / password / secret 的恶意 `X-Request-ID` 不出现在普通日志或审计表中。

□ 超过 64 字符的 `X-Request-ID` 被丢弃并重新生成。

□ 响应头 `X-Request-ID` 只返回规范化后的 request_id。

□ logging.py 不再直接使用原始 request_id。

□ audit_service.py 不再直接使用原始 request_id。

□ 使用 `rg "headers.get\(.*X-Request-ID" /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app` 检查，除 main.py 中间件外无其他直接读取。

□ 使用 caplog 或等价方式验证日志不包含恶意 request_id 原文。

□ `.venv/bin/python -m pytest -q` 通过。

□ `.venv/bin/python -m unittest discover` 通过。

□ `.venv/bin/python -m py_compile` 检查通过。

════════════════════════════════════════════════════════════════════

【禁止事项】

1. 禁止原样信任外部 `X-Request-ID`。

2. 禁止非法 request_id 进入普通日志。

3. 禁止非法 request_id 进入 ly_security_audit_log 或 ly_operation_audit_log。

4. 禁止后续业务模块直接读取 `request.headers.get("X-Request-ID")`。

5. 禁止把非法 request_id 简单截断后继续使用。

6. 禁止为了通过测试删除响应头 `X-Request-ID`。

7. 禁止修改 BOM 接口路径和正常成功响应结构。

════════════════════════════════════════════════════════════════════

【完成后回复格式】

请工程师完成后按以下格式回复：

TASK-001I 已完成。

已修改文件：
- [列出实际修改文件]

核心整改：
- 已新增 normalize_request_id()
- main.py 中间件已统一规范化 X-Request-ID
- logging.py 只记录规范化 request_id
- audit_service.py 只记录规范化 request_id
- 非法 request_id 不进入普通日志和审计表
- 响应头 X-Request-ID 只返回规范化后的 request_id

自测结果：
- 合法 request_id 保留：通过 / 不通过
- 缺失 request_id 自动生成：通过 / 不通过
- 含换行 request_id 被替换：通过 / 不通过
- 含 [SQL:] request_id 不进日志：通过 / 不通过
- 含 Token/Cookie/password/secret request_id 不进日志和审计：通过 / 不通过
- 超长 request_id 被替换：通过 / 不通过
- rg 检查除 main.py 外无直接读取 X-Request-ID：通过 / 不通过
- .venv/bin/python -m pytest -q：通过 / 不通过
- .venv/bin/python -m unittest discover：通过 / 不通过
- .venv/bin/python -m py_compile：通过 / 不通过

遗留问题：
- 无 / 有，说明原因
