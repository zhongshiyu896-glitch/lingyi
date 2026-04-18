# TASK-007B 权限与审计统一基座工程实现_工程任务单

- 任务编号：TASK-007B
- 任务名称：权限与审计统一基座工程实现（第一阶段）
- 角色：工程师
- 优先级：P1
- 前置依赖：TASK-007 文档层审计通过
- 更新时间：2026-04-16 10:25 CST
- 作者：技术架构师

════════════════════════════════════════════════════════════
【任务目标】
在不进入业务模块新功能开发的前提下，先落地 Sprint 2 权限与审计统一基座的第一阶段实现：

1. 统一动作权限注册与模块动作聚合入口。
2. 统一 fail-closed 错误信封（失败 `data=null`）。
3. 统一安全审计事件类型与最小必填字段。
4. 为 TASK-008~TASK-010 提供可复用的后端基线能力。

本任务是基座阶段任务，不进入 TASK-011/TASK-012 业务模块。

════════════════════════════════════════════════════════════
【任务边界】

允许：
- 权限动作常量/聚合逻辑收口。
- 权限源不可用、动作拒绝、资源越权等 fail-closed 错误信封收口。
- 安全审计事件分类与字段规范化。
- 相关单元/集成测试补齐。

禁止：
- 新增销售/库存/质量业务接口。
- 新增 ERPNext 写入能力。
- 改造 outbox 业务状态机（留给 TASK-009）。
- 修改前端页面与前端契约脚本（留给 TASK-010）。

════════════════════════════════════════════════════════════
【允许修改文件】

后端核心：
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/permissions.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/permission_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/audit_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/error_codes.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/exceptions.py

按需修改（仅限权限/审计/错误信封接入，不改业务语义）：
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/bom.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/subcontract.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/workshop.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/production.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/style_profit.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/factory_statement.py

测试：
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_permission_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_security_audit.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_audit_log.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_auth_actions.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_logging_sanitization.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_request_id_sanitization.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_service_account_policy.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_factory_statement_permissions.py

新增允许：
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_permission_audit_baseline.py
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-007B_权限与审计统一基座工程实现_交付证据.md

════════════════════════════════════════════════════════════
【禁止修改】
- /Users/hh/Desktop/领意服装管理系统/06_前端/**
- /Users/hh/Desktop/领意服装管理系统/.github/**
- /Users/hh/Desktop/领意服装管理系统/02_源码/**
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/**/TASK-008*
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/**/TASK-009*
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/**/TASK-010*
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/**/TASK-011*
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/**/TASK-012*
- dist、coverage、node_modules、.pytest_cache、.pytest-postgresql-*.xml

════════════════════════════════════════════════════════════
【实现要求】

### 1) 权限动作统一注册

1. `module:action` 动作常量继续集中在 `core/permissions.py`。
2. 动作别名规范化入口只保留一处（`normalize_actions` 或等价函数）。
3. 各模块动作集合必须能被统一按 `module` 过滤，不允许散落硬编码。
4. 新增/调整动作时必须有测试验证动作归属和别名归一。

### 2) 权限聚合与 fail-closed

1. `permission_service` 对 `permission source unavailable` 必须稳定返回 503 对应错误码。
2. 动作权限不足稳定返回 403，不得伪装 200 + 空数据。
3. 资源越权返回 403，并写安全审计。
4. 权限聚合失败路径不得吞异常后继续放行。

### 3) 错误信封统一

1. 统一错误信封：`{"code":"ERROR_CODE","message":"...","data":null}`。
2. 成功信封不在本任务统一改造（避免跨模块大改），但失败信封必须统一为 `data=null`。
3. 路由中 `_err/_app_err` 或等价路径必须遵循统一失败信封。
4. 未知异常不得返回敏感信息（SQL、Token、Cookie、Authorization、Secret、密码）。

### 4) 安全审计事件规范化

1. 至少统一以下事件类型并可查询到：
   - `AUTH_UNAUTHENTICATED`
   - `AUTH_FORBIDDEN`
   - `RESOURCE_ACCESS_DENIED`
   - `PERMISSION_SOURCE_UNAVAILABLE`
   - `INTERNAL_API_FORBIDDEN`
2. 安全审计字段最少包含：`event_type/module/action/resource_type/resource_id/user_id/request_id/ip`。
3. 继续保持敏感字段脱敏，禁止落库敏感头/密钥。
4. 审计写失败应走 `AUDIT_WRITE_FAILED` 路径，不得伪装为业务成功。

### 5) 服务账号最小权限

1. 保持并验证 internal worker 专用动作（如 `*:worker`）不暴露给普通角色。
2. `LY Integration Service` 角色动作集合不得扩散到业务写动作。
3. 新增测试覆盖服务账号权限边界。

════════════════════════════════════════════════════════════
【必须新增/调整测试】

1. 权限动作别名归一测试（含 BOM submit/cancel 兼容）。
2. 权限源不可用返回 503 + `PERMISSION_SOURCE_UNAVAILABLE`。
3. 动作拒绝返回 403 + `AUTH_FORBIDDEN`。
4. 资源越权返回 403 + `RESOURCE_ACCESS_DENIED`（如已有模块级错误码需映射一致）。
5. 失败错误信封 `data` 为 `null`（至少覆盖 3 个模块路由）。
6. 安全审计事件类型落库与字段完整性。
7. 安全审计/日志不泄露敏感字段。
8. 服务账号不能调用普通业务写动作。
9. 既有 TASK-001~006 权限相关回归测试不回潮。

════════════════════════════════════════════════════════════
【验证命令】

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service

.venv/bin/python -m pytest -q tests/test_permission_service.py tests/test_security_audit.py tests/test_audit_log.py tests/test_auth_actions.py tests/test_logging_sanitization.py tests/test_request_id_sanitization.py tests/test_service_account_policy.py tests/test_factory_statement_permissions.py tests/test_permission_audit_baseline.py

.venv/bin/python -m pytest -q

.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)

rg -n "Authorization|Cookie|token|secret|password" app/services/audit_service.py app/services/permission_service.py app/core tests

cd /Users/hh/Desktop/领意服装管理系统

git diff --name-only -- '06_前端' '.github' '02_源码'
```

════════════════════════════════════════════════════════════
【验收标准】

- 权限动作统一注册与归一逻辑可测试。
- 权限源不可用、动作拒绝、资源越权均 fail-closed。
- 失败错误信封统一为 `data=null`。
- 安全审计事件类型与字段规范化完成。
- 服务账号最小权限边界测试通过。
- TASK-001~006 权限与审计回归不回潮。
- 禁改扫描无前端/.github/02_源码修改。

════════════════════════════════════════════════════════════
【交付回复格式】

```text
TASK-007B 已完成。

已输出/修改：
- <文件清单>

验证：
- 定向 pytest：
- 全量 pytest：
- py_compile：
- 敏感字段扫描：
- 禁改扫描：

结论：建议/不建议进入 TASK-007C。
```

════════════════════════════════════════════════════════════
【门禁】
- TASK-007B 审计通过后，才允许进入 TASK-007C。
- 基座阶段未全通过前，不得进入 TASK-011/TASK-012。
