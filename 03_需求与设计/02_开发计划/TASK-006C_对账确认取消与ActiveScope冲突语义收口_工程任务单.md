# TASK-006C 对账确认取消与 Active Scope 冲突语义收口工程任务单

- 任务编号：TASK-006C
- 模块：加工厂对账单
- 优先级：P0
- 版本：V1.0
- 更新时间：2026-04-15 18:21 CST
- 作者：技术架构师
- 前置依赖：TASK-006B1 审计通过，允许进入 TASK-006C
- 任务边界：只做本地确认、取消释放、状态机、幂等操作记录和 active-scope 业务冲突语义收口；不得实现 ERPNext Purchase Invoice、payable-draft、前端页面、打印页面。

## 一、任务目标

在 TASK-006B/B1 本地草稿基础上，实现加工厂对账单本地状态机：

1. 草稿对账单确认：`draft -> confirmed`。
2. 草稿/已确认未应付对账单取消：`draft|confirmed -> cancelled`。
3. 取消时释放来源 `ly_subcontract_inspection`，允许后续重建。
4. 确认后锁定明细金额，禁止原地修改。
5. 补齐 confirm/cancel 幂等操作记录，避免重复点击造成状态混乱。
6. 将“同供应商同期间已有 active statement 且后续新增来源事实”的场景从数据库写失败收口为业务冲突错误。

## 二、继续冻结的边界

以下内容仍然禁止：

```text
POST /api/factory-statements/{id}/payable-draft
ERPNext Purchase Invoice 创建
ERPNext /api/resource/Purchase Invoice 调用
前端页面
打印页面
对账调整单
付款/Payment Entry/GL Entry
```

## 三、允许修改文件

```text
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/factory_statement.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/factory_statement.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/factory_statement.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/factory_statement_service.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/permissions.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/permission_service.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/audit_service.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/versions/task_006c_factory_statement_status_operations.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_factory_statement_confirm_cancel.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_factory_statement_active_scope.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_factory_statement_audit.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_factory_statement_permissions.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_factory_statement_idempotency.py
/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-006C_对账确认取消与ActiveScope冲突语义收口_交付证据.md
```

## 四、禁止修改文件

```text
/Users/hh/Desktop/领意服装管理系统/06_前端/**
/Users/hh/Desktop/领意服装管理系统/.github/**
/Users/hh/Desktop/领意服装管理系统/02_源码/**
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_*.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/scripts/**
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tools/**
```

## 五、接口范围

### 1. 确认对账单

```text
POST /api/factory-statements/{id}/confirm
```

入参：

```json
{
  "idempotency_key": "client-generated-key",
  "remark": "财务已核对"
}
```

出参：

```json
{
  "code": "0",
  "message": "success",
  "data": {
    "name": 1,
    "statement_no": "FS-202604-0001",
    "status": "confirmed",
    "confirmed_by": "current_user",
    "confirmed_at": "2026-04-15T18:21:00+08:00"
  }
}
```

实现要求：

1. 必须先登录鉴权。
2. 必须先校验 `factory_statement:confirm` 动作权限。
3. 必须查询 statement 后校验 `company + supplier` 资源权限。
4. 必须行锁锁定 statement。
5. 仅 `status='draft'` 可确认。
6. 确认前必须复核所有来源 inspection 仍为：
   - `settlement_status='statement_locked'`
   - `statement_id = 当前 statement.id`
   - `statement_no = 当前 statement.statement_no`
7. 确认前必须复核头表金额等于 items 汇总。
8. 确认时写入：
   - `status='confirmed'`
   - `confirmed_by=current_user`
   - `confirmed_at=now`
9. 不允许修改 `ly_factory_statement_item` 的数量和金额。
10. 不允许创建 ERPNext Purchase Invoice。

### 2. 取消对账单

```text
POST /api/factory-statements/{id}/cancel
```

入参：

```json
{
  "idempotency_key": "client-generated-key",
  "reason": "供应商重对账"
}
```

实现要求：

1. 必须先登录鉴权。
2. 必须先校验 `factory_statement:cancel` 动作权限。
3. 必须查询 statement 后校验 `company + supplier` 资源权限。
4. 必须行锁锁定 statement。
5. 允许取消状态：`draft`、`confirmed`。
6. 如果未来已有 `payable_draft_created` 或 `erpnext_purchase_invoice_name` 非空，必须返回 `FACTORY_STATEMENT_PAYABLE_ALREADY_CREATED`，不得取消。
7. 取消时写入：
   - `status='cancelled'`
   - `cancelled_by=current_user`
   - `cancelled_at=now`
   - `cancel_reason=reason`
8. 取消时必须释放来源 inspection：
   - `settlement_status='unsettled'`
   - `statement_id=NULL`
   - `statement_no=NULL`
   - `settlement_locked_by=NULL`
   - `settlement_locked_at=NULL`
9. 取消不删除 statement 和 items，保留历史快照用于审计。
10. 取消后同一验货记录允许进入新对账单。
11. 不允许创建 ERPNext Purchase Invoice。

## 六、幂等操作记录

必须新增或等价实现 append-only 操作记录，推荐表：

```text
ly_schema.ly_factory_statement_operation
```

字段建议：

| 字段 | 要求 |
| --- | --- |
| `id` | 主键。 |
| `statement_id` | 非空。 |
| `operation_type` | `confirm / cancel`。 |
| `idempotency_key` | 非空。 |
| `request_hash` | 非空。 |
| `result_snapshot_json` | 非空。 |
| `operator` | 非空。 |
| `created_at` | 非空。 |

约束：

```text
unique(operation_type, idempotency_key)
```

幂等规则：

1. 同一 `operation_type + idempotency_key + request_hash` 重试时 replay 首次结果。
2. 同一 `operation_type + idempotency_key` 但 request_hash 不同，返回 `FACTORY_STATEMENT_IDEMPOTENCY_CONFLICT`。
3. 并发唯一冲突时 reload operation 并 replay；不得裸 500。
4. confirm/cancel 操作记录必须与状态变更在同一事务内提交。

## 七、Active Scope 冲突语义收口

TASK-006B1 保留风险：同范围已有 active statement 且后续新增来源事实时，目前会 fail closed 返回 `FACTORY_STATEMENT_DATABASE_WRITE_FAILED`，错误语义不够精确。

TASK-006C 必须收口为业务语义：

1. 同一 `company + supplier + from_date + to_date` 已存在 `status <> 'cancelled'` 的 statement 时，不得创建第二张 active statement。
2. 如果是同一个 `idempotency_key + request_hash`，replay 原 statement。
3. 如果是不同幂等键或来源事实已变化，返回：

```text
FACTORY_STATEMENT_ACTIVE_SCOPE_EXISTS
```

4. 响应 detail 必须包含安全字段：`existing_statement_id`、`existing_statement_no`、`status`。
5. 不得把该业务冲突归类为 `DATABASE_WRITE_FAILED`。
6. 不得泄露 SQL 或异常明文。

## 八、权限动作

新增或补齐：

```text
factory_statement:confirm
factory_statement:cancel
```

角色建议：

| 角色 | confirm | cancel |
| --- | --- | --- |
| Finance Manager | 是 | 是 |
| Accounts User | 是 | 否 |
| Subcontract Manager | 否 | 否 |
| Production Manager | 否 | 否 |
| Workshop Manager | 否 | 否 |
| Sales Manager | 否 | 否 |
```

要求：

1. static 权限源和 ERPNext role 聚合口径必须同时补齐。
2. 生产环境不得因 static 权限源缺配置而放行。
3. Company-only 权限不能替代 Supplier 权限。
4. ERPNext User Permission 查询失败必须 fail closed。

## 九、错误码要求

必须新增或收口：

| 错误码 | 场景 |
| --- | --- |
| `FACTORY_STATEMENT_STATUS_INVALID` | 当前状态不允许确认或取消。 |
| `FACTORY_STATEMENT_SOURCE_LOCK_MISMATCH` | 来源 inspection 锁定关系不匹配。 |
| `FACTORY_STATEMENT_TOTAL_MISMATCH` | 头表金额与明细汇总不一致。 |
| `FACTORY_STATEMENT_ACTIVE_SCOPE_EXISTS` | 同 company/supplier/period 已有 active statement。 |
| `FACTORY_STATEMENT_PAYABLE_ALREADY_CREATED` | 已生成应付草稿后禁止取消。 |
| `FACTORY_STATEMENT_IDEMPOTENCY_CONFLICT` | 同幂等键 request_hash 不一致。 |
| `FACTORY_STATEMENT_DATABASE_WRITE_FAILED` | 数据库写入或 commit 失败。 |
| `FACTORY_STATEMENT_INTERNAL_ERROR` | 未知异常，响应不得泄露 SQL 或异常明文。 |

## 十、审计要求

1. 401 未登录必须写安全审计。
2. 403 动作权限拒绝必须写安全审计。
3. 403 资源权限拒绝必须写安全审计。
4. 503 权限源不可用必须写安全审计。
5. confirm 成功/失败必须写操作审计。
6. cancel 成功/失败必须写操作审计。
7. active-scope 业务冲突必须写操作失败审计。
8. 审计日志不得记录 Authorization、Cookie、密码、Secret、Token 明文。
9. `request_id` 必须使用既有归一化逻辑。

## 十一、测试要求

必须新增/覆盖：

1. `POST /api/factory-statements/{id}/confirm` 可将 draft 改为 confirmed。
2. confirm 写入 `confirmed_by=current_user`，不信任前端传入操作者。
3. confirm 前复核 source inspection 锁定关系，不匹配返回 `FACTORY_STATEMENT_SOURCE_LOCK_MISMATCH`。
4. confirm 前复核头表金额与 item 汇总，不一致返回 `FACTORY_STATEMENT_TOTAL_MISMATCH`。
5. confirmed 后 item 数量和金额不可变。
6. confirm 同 key 同 hash 重试 replay。
7. confirm 同 key 异 hash 返回 `FACTORY_STATEMENT_IDEMPOTENCY_CONFLICT`。
8. 无 confirm 权限返回 403 且不改状态。
9. 无 supplier 资源权限 confirm 返回 403 且不改状态。
10. `POST /api/factory-statements/{id}/cancel` 可取消 draft 并释放 inspections。
11. cancel 可取消 confirmed 且未生成 payable 的 statement，并释放 inspections。
12. cancel 后 statement/items 保留，inspection 回到 `unsettled` 且清空 statement 指针。
13. cancel 后同一 inspection 可重新生成新对账单。
14. payable 字段非空时 cancel 返回 `FACTORY_STATEMENT_PAYABLE_ALREADY_CREATED`。
15. cancel 同 key 同 hash 重试 replay。
16. cancel 同 key 异 hash 返回 `FACTORY_STATEMENT_IDEMPOTENCY_CONFLICT`。
17. 同 company/supplier/period 已有 active statement 且来源事实变化时，POST create 返回 `FACTORY_STATEMENT_ACTIVE_SCOPE_EXISTS`，不是 `DATABASE_WRITE_FAILED`。
18. active-scope conflict 响应不泄露 SQL。
19. Purchase Invoice/payable-draft 禁入扫描继续通过。
20. 前端、workflow、`02_源码` 禁改扫描无输出。

## 十二、验证命令

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service

.venv/bin/python -m pytest -q tests/test_factory_statement_confirm_cancel.py tests/test_factory_statement_active_scope.py tests/test_factory_statement_api.py tests/test_factory_statement_models.py tests/test_factory_statement_permissions.py tests/test_factory_statement_idempotency.py tests/test_factory_statement_audit.py
.venv/bin/python -m pytest -q
.venv/bin/python -m unittest discover
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)

rg -n "Purchase Invoice|/api/resource/Purchase Invoice|payable-draft|payable_draft" app tests
cd /Users/hh/Desktop/领意服装管理系统
git diff --name-only -- '06_前端' '.github' '02_源码'
```

预期：

1. 定向测试通过。
2. 全量测试通过。
3. unittest 通过。
4. py_compile 通过。
5. Purchase Invoice/payable-draft 扫描不得出现业务实现入口。
6. 禁改目录扫描无输出。

## 十三、交付证据要求

创建：

```text
/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-006C_对账确认取消与ActiveScope冲突语义收口_交付证据.md
```

证据必须包含：

1. 修改文件清单。
2. confirm 状态机实现说明。
3. cancel 释放 inspection 实现说明。
4. 幂等 operation 实现说明。
5. active-scope 业务冲突语义收口说明。
6. 权限和审计实现说明。
7. 定向测试结果。
8. 全量测试结果。
9. Purchase Invoice/payable-draft 禁入扫描结果。
10. 前端、workflow、`02_源码` 禁改扫描结果。
11. 是否建议进入 TASK-006D。

## 十四、交付后回复格式

```text
TASK-006C 已完成。

实现内容：
1. confirm 状态机：
2. cancel 释放来源：
3. 幂等 operation：
4. active-scope 业务冲突语义：

验证：
- 定向 pytest：
- 全量 pytest：
- unittest：
- py_compile：
- Purchase Invoice/payable-draft 禁入扫描：
- 前端/workflow/02_源码 禁改扫描：

结论：建议/不建议进入 TASK-006D。
```
