# TASK-006B1 对账草稿重复防护与取消后重建约束整改工程任务单

- 任务编号：TASK-006B1
- 模块：加工厂对账单
- 优先级：P0
- 版本：V1.0
- 更新时间：2026-04-15 18:04 CST
- 作者：技术架构师
- 前置依赖：TASK-006B 审计不通过，需修复第 162 份审计高危问题
- 任务边界：只修复 TASK-006B 两个阻断项；不得进入 TASK-006C；不得实现确认、取消、调整、ERPNext Purchase Invoice、前端页面。

## 一、任务目标

修复 TASK-006B 审计发现的两个高危问题：

1. 补齐同范围 active-scope 重复防护，阻止同一 `company + supplier + from_date + to_date + request_hash` 生成第二张未取消草稿。
2. 修正 `inspection_id` 无条件唯一约束，避免后续取消后重建被历史明细阻断。

## 二、审计来源

TASK-006B 审计结论：不通过，暂不建议进入 TASK-006C。

高危问题：

1. 同范围 active-scope 重复防护缺失。
2. `inspection_id` 无条件唯一约束阻断取消后重建。

审计定位：

```text
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/factory_statement_service.py:84
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/factory_statement_service.py:465
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/versions/task_006b_create_factory_statement_tables.py:91
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/factory_statement.py:85
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/versions/task_006b_create_factory_statement_tables.py:143
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_factory_statement_models.py:122
```

## 三、允许修改文件

```text
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/factory_statement.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/factory_statement_service.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/versions/task_006b_create_factory_statement_tables.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_factory_statement_api.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_factory_statement_models.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_factory_statement_idempotency.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_factory_statement_permissions.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_factory_statement_audit.py
/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-006B1_对账草稿重复防护与取消后重建约束整改_交付证据.md
```

如确有必要，允许补充一个迁移修正文件：

```text
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/versions/task_006b1_factory_statement_active_scope_constraints.py
```

## 四、禁止修改文件

```text
/Users/hh/Desktop/领意服装管理系统/06_前端/**
/Users/hh/Desktop/领意服装管理系统/.github/**
/Users/hh/Desktop/领意服装管理系统/02_源码/**
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/factory_statement.py  # 除非只调整错误码透传，不得新增接口
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_*.py
```

禁止新增或实现：

```text
POST /api/factory-statements/{id}/confirm
POST /api/factory-statements/{id}/cancel
POST /api/factory-statements/{id}/payable-draft
ERPNext Purchase Invoice 创建
前端页面或前端 API
```

## 五、整改要求一：active-scope 重复防护

### 业务规则

同一 `company + supplier + from_date + to_date + request_hash` 下，只允许存在一张未取消对账单。

由于 TASK-006B 当前只允许 `draft` 状态，因此 B1 阶段至少必须保证：

```text
company + supplier + from_date + to_date + request_hash + status=draft 唯一
```

为后续 TASK-006C 取消后重建预留口径：

```text
company + supplier + from_date + to_date + request_hash where status <> 'cancelled' 唯一
```

### 实现要求

1. 生成草稿时，在读取 eligible inspections 并计算 `request_hash` 后，必须先查询是否存在同 active scope 的非取消 statement。
2. 如果找到同 scope statement：
   - 如果请求范围完全一致，返回已存在 statement 的 replay 结果，不创建第二张。
   - 如果来源明细已变化但 scope hash 相同，不应出现；如出现必须 fail closed。
3. 数据库层必须补 active scope 唯一约束或可等价证明的唯一索引。
4. PostgreSQL 推荐使用 partial unique index：

```sql
CREATE UNIQUE INDEX uk_ly_factory_statement_active_scope
ON ly_schema.ly_factory_statement (company, supplier, from_date, to_date, request_hash)
WHERE status <> 'cancelled';
```

5. SQLite/测试环境若不支持 partial index，必须在 service 层和测试中覆盖等价防护。
6. 并发情况下，如果唯一约束触发，应 reload 已存在 statement 并返回 replay；不得返回裸 500。
7. 若唯一冲突无法 reload，应返回 `FACTORY_STATEMENT_DATABASE_WRITE_FAILED` 或明确错误信封，且不泄露 SQL。

## 六、整改要求二：inspection_id 取消后重建约束

### 业务规则

TASK-006A 冻结的是：同一来源明细不得进入多个未取消对账单。

这不等于 `inspection_id` 全局永远唯一。后续 TASK-006C 取消对账单后，业务允许同一验货记录释放后重新进入新对账单。

### 实现要求

1. 移除或废弃 `ly_factory_statement_item.inspection_id` 的无条件唯一约束。
2. 不得继续使用 `uk_ly_factory_statement_item_inspection` 这种全局唯一约束作为最终防重策略。
3. 防重应由以下组合完成：
   - 来源 `ly_subcontract_inspection.settlement_status` 锁定状态。
   - `ly_subcontract_inspection.statement_id / statement_no` 指向当前未取消 statement。
   - statement active-scope 唯一约束。
   - service 层行锁和状态校验。
4. 如需要数据库层保护，可设计 partial unique index 或冗余 `statement_status` 快照，但必须保证取消后可重建。
5. B1 不要求实现取消释放逻辑，但必须确保当前 DDL 不会永久阻断取消后重建。
6. 测试中必须显式断言：模型/迁移不再声明 `inspection_id` 无条件唯一。

## 七、测试要求

必须新增或调整以下测试：

1. `test_active_scope_prevents_second_draft_with_new_idempotency_key`：同 company/supplier/period/request_hash，换新幂等键不得创建第二张未取消草稿。
2. `test_active_scope_replays_existing_statement`：重复范围返回既有 statement。
3. `test_active_scope_unique_conflict_reloads_existing_statement`：模拟唯一冲突时 reload 并 replay。
4. `test_different_period_allows_new_statement`：不同日期范围允许生成新草稿。
5. `test_different_supplier_allows_new_statement`：不同 supplier 允许生成新草稿。
6. `test_unconditional_inspection_id_unique_constraint_removed`：模型和迁移不再有 `inspection_id` 无条件唯一。
7. `test_statement_item_allows_rebuild_after_cancel_contract`：用测试模拟历史 cancelled statement item 存在时，不应因 item 表 inspection_id 全局唯一阻断新草稿；B1 可通过 DDL/服务契约测试表达。
8. 原 TASK-006B 定向测试必须继续通过。
9. Purchase Invoice/payable-draft 禁入扫描必须继续通过。
10. 前端、workflow、`02_源码` 禁改扫描必须无输出。

## 八、错误码要求

保留 TASK-006B 已有错误码，并补齐以下语义：

| 错误码 | 场景 |
| --- | --- |
| `FACTORY_STATEMENT_ACTIVE_SCOPE_EXISTS` | 同范围已有未取消对账单且不能 replay。 |
| `FACTORY_STATEMENT_IDEMPOTENCY_CONFLICT` | 同一幂等键 request_hash 不一致。 |
| `FACTORY_STATEMENT_DATABASE_WRITE_FAILED` | 唯一冲突 reload 失败或数据库写入失败。 |

如果工程实现选择不新增 `FACTORY_STATEMENT_ACTIVE_SCOPE_EXISTS`，也必须在交付证据中说明使用哪个既有错误码承载该场景。

## 九、验证命令

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service

.venv/bin/python -m pytest -q tests/test_factory_statement_api.py tests/test_factory_statement_models.py tests/test_factory_statement_permissions.py tests/test_factory_statement_idempotency.py tests/test_factory_statement_audit.py
.venv/bin/python -m pytest -q
.venv/bin/python -m unittest discover
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)

rg -n "UniqueConstraint\([^\n]*inspection_id|unique=True.*inspection_id|uk_ly_factory_statement_item_inspection" app migrations tests
rg -n "Purchase Invoice|/api/resource/Purchase Invoice|payable-draft|payable_draft" app tests
cd /Users/hh/Desktop/领意服装管理系统
git diff --name-only -- '06_前端' '.github' '02_源码'
```

预期：

1. 定向测试通过。
2. 全量测试通过。
3. py_compile 通过。
4. `inspection_id` 无条件唯一扫描不得命中有效模型/迁移约束；允许命中测试中的“禁止回潮”断言。
5. Purchase Invoice/payable-draft 扫描不得出现业务实现入口。
6. 禁改目录扫描无输出。

## 十、交付证据要求

创建：

```text
/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-006B1_对账草稿重复防护与取消后重建约束整改_交付证据.md
```

证据必须包含：

1. 修改文件清单。
2. active-scope 防重实现说明。
3. `inspection_id` 无条件唯一约束移除说明。
4. 取消后重建约束预留说明。
5. 定向测试结果。
6. 全量测试结果。
7. `inspection_id` 唯一扫描结果。
8. Purchase Invoice/payable-draft 禁入扫描结果。
9. 前端、workflow、`02_源码` 禁改扫描结果。
10. 是否建议进入 TASK-006C。

## 十一、交付后回复格式

```text
TASK-006B1 已完成。

修复内容：
1. active-scope 重复防护：[说明]
2. inspection_id 无条件唯一约束：[说明]
3. 取消后重建预留：[说明]

验证：
- 定向 pytest：[结果]
- 全量 pytest：[结果]
- unittest：[结果]
- py_compile：[结果]
- inspection_id 唯一扫描：[结果]
- Purchase Invoice/payable-draft 禁入扫描：[结果]
- 前端/workflow/02_源码 禁改扫描：[结果]

结论：建议/不建议进入 TASK-006C。
```
