# TASK-070C_FIX1 权限治理审计导出写入边界修复 工程任务单

## 1. 基本信息

- 任务编号：TASK-070C_FIX1
- 任务名称：权限治理审计导出写入边界修复
- 模块：权限治理 / 审计导出 / 审计服务边界
- 角色：B Engineer
- 优先级：P0
- 触发来源：C Auditor 审计意见书第427份
- 修复类型：fix pass 1
- 前置任务：TASK-070C 权限治理审计脱敏CSV导出基线
- 当前定位：只修复第427份 P1 finding，不新增功能，不扩大导出能力，不改前端。

## 2. 第427份 P1 问题

`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/permission_governance.py` 中 `_commit_or_raise_audit_failure(...)` 直接调用：

```text
session.commit()
session.rollback()
```

这违反 TASK-070C 第4.7与8.4边界：

1. 导出操作审计必须通过项目现有 `AuditService` 或等价公共审计入口完成。
2. `permission_governance.py`、`permission_governance_service.py`、`permission_governance_export_service.py` 中不应出现直接 `session.add/delete/commit/rollback` 写入提交语义。
3. 若需要提交审计写入，应收敛在 `audit_service.py` 或等价公共审计 helper 内。

## 3. 修复目标

1. 移除 `permission_governance.py` 中 `_commit_or_raise_audit_failure(...)` 或等价直接提交函数。
2. 移除权限治理 router/service/export service 中的直接 `session.commit()` / `session.rollback()` / `session.add()` / `session.delete()`。
3. 将“记录导出审计 + 提交 + 失败 rollback + fail-closed”收敛到 `AuditService` 或等价公共审计入口。
4. 保持 TASK-070C 已通过能力不回退：
   - `permission:export` 仍独立校验。
   - 两条导出接口仍为 `GET`。
   - 成功导出仍记录操作审计。
   - 失败导出仍记录操作审计。
   - 审计写入失败仍 fail-closed，并返回 `AUDIT_WRITE_FAILED` 或项目统一等价错误。
   - CSV 表头、固定安全文件名、脱敏、公式注入防护、前端 `requestFile` 下载链路不得回退。

## 4. 允许修改范围

只允许修改以下文件。未列入文件一律不得改动。

### 4.1 后端实现

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/permission_governance.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/audit_service.py`

### 4.2 后端测试

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_permission_governance_audit_export.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_permissions_registry.py`（仅当权限注册断言需保持同步时允许）

### 4.3 日志

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md`

## 5. 禁止修改范围

本 fix pass 禁止修改：

```text
/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/permission_governance_service.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/permission_governance_export_service.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/permission_governance.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/permissions.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/main.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models
```

除非修复过程中证明不修改某个禁止文件无法达成第427份修复要求；若发生，立即停止并回交 BLOCKED，不得擅自扩大范围。

## 6. 实现要求

### 6.1 公共审计入口

在 `app/services/audit_service.py` 中新增或复用公共 helper，建议形态如下，名称可按项目风格调整：

```text
record_success_and_commit(...)
record_failure_and_commit(...)
```

或：

```text
record_operation_and_commit(...)
```

要求：

1. helper 内部调用现有 `record_success(...)` / `record_failure(...)` 或等价内部方法。
2. helper 内部负责 `session.commit()`。
3. helper 内部在提交异常时执行 `session.rollback()`。
4. helper 内部将提交异常统一转换为 `AuditWriteFailed`。
5. helper 不得写入 token、cookie、authorization、password、secret、dsn、DATABASE_URL、raw headers、raw payload。
6. helper 不得改变既有 `record_success(...)` / `record_failure(...)` 的调用兼容性，避免影响其它模块。

### 6.2 Router 调用

在 `app/routers/permission_governance.py` 中：

1. 删除 `_commit_or_raise_audit_failure(...)`。
2. `_record_export_audit(...)` 不得直接调用 `session.commit()` / `session.rollback()`。
3. `_record_export_audit(...)` 可以调用 `AuditService` 新公共 helper。
4. 仍需保持成功导出和失败导出均记录审计。
5. 仍需保持审计写入失败时 fail-closed。
6. 不得新增任何 `POST / PUT / PATCH / DELETE`。
7. 不得新增 ERPNext 访问、业务 DB 写入、outbox、worker、internal 能力。

### 6.3 测试要求

必须补强或调整 `test_permission_governance_audit_export.py`，至少覆盖：

1. 成功导出仍会生成操作审计记录。
2. 失败导出仍会生成失败操作审计记录。
3. 审计提交失败时导出 fail-closed，并返回 `AUDIT_WRITE_FAILED` 或项目统一等价错误。
4. `permission_governance.py`、`permission_governance_service.py`、`permission_governance_export_service.py` 中不再出现 `session.commit` / `session.rollback` / `session.add` / `session.delete`。
5. `AuditService` 或公共审计 helper 中存在提交/回滚职责。
6. TASK-070C 既有 CSV 表头、脱敏、公式注入防护、权限隔离测试不回退。

## 7. 必跑验证命令

### 7.1 后端 pytest

在 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service` 执行：

```bash
.venv/bin/python -m pytest tests/test_permission_governance_audit_export.py tests/test_permission_governance_audit_readonly.py tests/test_permission_governance_readonly.py tests/test_permissions_registry.py -v --tb=short
```

### 7.2 Python 编译

```bash
.venv/bin/python -m py_compile app/routers/permission_governance.py app/services/audit_service.py app/services/permission_governance_service.py app/services/permission_governance_export_service.py app/schemas/permission_governance.py app/core/permissions.py app/main.py
```

### 7.3 前端类型检查

即使本 fix pass 不允许改前端，也必须复跑确保未回退：

```bash
cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc && npm run typecheck
```

### 7.4 写入边界扫描

在 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service` 执行：

```bash
rg -n "session\.(add|delete|commit|rollback)|insert\(|update\(|delete\(|bulk_update|execute\(" app/routers/permission_governance.py app/services/permission_governance_service.py app/services/permission_governance_export_service.py || true
rg -n "session\.(commit|rollback)|AuditWriteFailed|record_.*commit|commit_.*audit" app/services/audit_service.py
rg -n "@router\.(post|put|patch|delete)" app/routers/permission_governance.py || true
rg -n "requests\.|httpx\.|/api/resource|ERPNext|Stock Entry|Stock Reconciliation|GL Entry|Payment Entry|Purchase Invoice" app/routers/permission_governance.py app/services/audit_service.py app/services/permission_governance_service.py app/services/permission_governance_export_service.py || true
rg -n "authorization|cookie|token|secret|password|dsn|DATABASE_URL|raw headers|raw payload|before_data|after_data" app/routers/permission_governance.py app/services/audit_service.py app/services/permission_governance_export_service.py tests/test_permission_governance_audit_export.py || true
```

要求：

- 第一条扫描必须无命中，或仅有测试 fixture 注释不在被扫文件内；不得在 permission governance router/service/export service 中出现直接提交或写入语义。
- 第二条扫描必须显示提交/回滚职责只在 `audit_service.py` 的公共审计入口中。
- `before_data/after_data` 只允许作为参数名或脱敏测试语义出现，不得泄露原文到 CSV 或响应。

### 7.5 禁改目录检查

在 `/Users/hh/Desktop/领意服装管理系统` 执行：

```bash
git diff --name-only -- .github .ci-reports 01_需求与资料 02_源码 03_环境与部署 04_测试与验收 05_交付物
```

必须为空。

### 7.6 格式检查

```bash
git diff --check
```

必须通过。

## 8. 回交格式

B 完成后必须按以下格式回交 C：

```text
STATUS: READY_FOR_AUDIT
TASK_ID: TASK-070C_FIX1
ROLE: B Engineer

CHANGED_FILES:
- 逐项列出真实改动文件绝对路径

FIX_SUMMARY:
- 说明如何移除 permission_governance.py 中直接 session.commit/rollback
- 说明 AuditService 或公共 helper 如何负责提交/回滚/fail-closed
- 说明成功/失败导出审计记录如何保持

VERIFICATION:
- pytest 命令与结果
- py_compile 命令与结果
- npm run typecheck 结果
- 写入边界扫描结果
- ERPNext/高危语义扫描结果
- 禁改目录 diff 结果
- git diff --check 结果

RISKS:
- 如存在继承脏基线，说明路径、哈希或原因

NEXT_ROLE:
- C Auditor
```

## 9. 完成定义

本 fix pass 只有同时满足以下条件才算完成：

1. `permission_governance.py`、`permission_governance_service.py`、`permission_governance_export_service.py` 中不再出现直接 `session.add/delete/commit/rollback`。
2. 审计提交与 rollback 职责已收敛到 `AuditService` 或等价公共审计入口。
3. 成功导出与失败导出仍记录操作审计。
4. 审计写失败仍 fail-closed。
5. TASK-070C 已通过项不回退。
6. pytest、py_compile、前端 typecheck、边界扫描、禁改目录 diff、git diff check 全部通过。
7. 未执行 commit / push / PR / tag / 生产发布。
