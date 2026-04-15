# TASK-006B1 对账草稿重复防护与取消后重建约束整改 交付证据

## 1. 任务信息
- 任务编号：`TASK-006B1`
- 前置：`TASK-006B` 审计第 162 份不通过后的阻断修复
- 目标：
  1. 修复 active-scope 重复防护
  2. 移除 `inspection_id` 无条件全局唯一约束，避免取消后重建被历史明细永久阻断

## 2. 修改文件清单
- `07_后端/lingyi_service/app/models/factory_statement.py`
- `07_后端/lingyi_service/app/services/factory_statement_service.py`
- `07_后端/lingyi_service/migrations/versions/task_006b_create_factory_statement_tables.py`
- `07_后端/lingyi_service/migrations/versions/task_006b1_factory_statement_active_scope_constraints.py`（新增）
- `07_后端/lingyi_service/tests/test_factory_statement_api.py`
- `07_后端/lingyi_service/tests/test_factory_statement_models.py`
- `07_后端/lingyi_service/tests/test_factory_statement_idempotency.py`

## 3. 修复内容

### 3.1 active-scope 重复防护
实现位置：`app/services/factory_statement_service.py`

已实现：
1. 新增 active-scope 查询：
   - 维度：`company + supplier + from_date + to_date + request_hash`
   - 条件：`statement_status != 'cancelled'`
2. 生成草稿时，完成 `request_hash` 计算与来源读取后，优先检查 active-scope 已有草稿：
   - 命中时返回 replay，不创建第二张草稿。
3. 新增并发唯一冲突兜底：
   - 在 `flush` 触发 `IntegrityError` 时回滚当前事务态后，重新查询 idempotency / active-scope。
   - 若能找到既有记录，返回 replay。
   - 若无法重放，返回 `FACTORY_STATEMENT_DATABASE_WRITE_FAILED`（不泄露底层 SQL）。

数据库层约束：
- 在模型与迁移中新增 active-scope 唯一索引：
  - `uk_ly_factory_statement_active_scope`
  - 索引列：`company, supplier, from_date, to_date, request_hash`
  - 条件：`statement_status <> 'cancelled'`（PostgreSQL/SQLite partial unique）

### 3.2 inspection_id 无条件唯一约束移除
实现位置：
- `app/models/factory_statement.py`
- `migrations/versions/task_006b_create_factory_statement_tables.py`
- `migrations/versions/task_006b1_factory_statement_active_scope_constraints.py`

已实现：
1. 模型层移除 `inspection_id` 全局唯一索引：
   - 删除：`uk_ly_factory_statement_item_inspection`（unique）
   - 改为：`idx_ly_factory_statement_item_inspection`（非唯一）
2. 初始迁移同步移除该全局唯一定义。
3. 新增 B1 修复迁移，兼容已执行 006B 的环境：
   - 自动识别并删除 legacy 的 `inspection_id` 单列唯一索引（不依赖固定名字）。
   - 补建非唯一索引 `idx_ly_factory_statement_item_inspection`。
   - 补建 `uk_ly_factory_statement_active_scope`。

### 3.3 取消后重建预留
B1 不实现取消接口，但通过以下方式预留：
1. item 表不再对 `inspection_id` 做“全局永久唯一”硬限制。
2. active-scope 采用 `status <> 'cancelled'` 条件唯一，为后续取消后重建预留数据库语义。
3. 防重主链回归到：
   - `inspection.settlement_status` 锁定
   - `inspection.statement_id/statement_no` 绑定
   - active-scope 唯一约束
   - service 层状态校验与并发冲突重放

## 4. 新增/调整测试

### 4.1 active-scope 与 replay
- `test_active_scope_prevents_second_draft_with_new_idempotency_key`
- `test_active_scope_replays_existing_statement`
- `test_active_scope_unique_conflict_reloads_existing_statement`
- `test_different_period_allows_new_statement`
- `test_different_supplier_allows_new_statement`

### 4.2 约束与重建预留
- `test_unconditional_inspection_id_unique_constraint_removed`
- `test_statement_item_allows_rebuild_after_cancel_contract`
- `test_active_scope_unique_constraint_for_non_cancelled_statement`
- API 场景调整：`test_locked_source_in_different_scope_returns_source_locked`

## 5. 验证结果

### 5.1 定向 pytest
命令：
```bash
.venv/bin/python -m pytest -q tests/test_factory_statement_api.py tests/test_factory_statement_models.py tests/test_factory_statement_permissions.py tests/test_factory_statement_idempotency.py tests/test_factory_statement_audit.py
```
结果：`25 passed`

### 5.2 全量 pytest
命令：
```bash
.venv/bin/python -m pytest -q
```
结果：`666 passed, 13 skipped`

### 5.3 unittest
命令：
```bash
.venv/bin/python -m unittest discover
```
结果：`Ran 649 tests ... OK (skipped=1)`

### 5.4 py_compile
命令：
```bash
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
```
结果：通过

## 6. 扫描结果

### 6.1 inspection_id 无条件唯一扫描
命令：
```bash
rg -n "UniqueConstraint\([^\n]*inspection_id|unique=True.*inspection_id|uk_ly_factory_statement_item_inspection" app migrations tests
```
结果：
- `tests/test_factory_statement_models.py` 命中 2 处（禁止回潮断言）
- `app/models/subcontract.py` 命中 1 处 `uk_ly_subcontract_inspection_idempotency`（外发验货幂等约束，非 factory_statement item 唯一约束）
- 未命中 `factory_statement` 模型与迁移中的 `inspection_id` 无条件唯一约束实现

结论：B1 目标约束已移除，扫描命中为测试断言与其他模块历史约束，不属于本任务回潮。

### 6.2 Purchase Invoice / payable-draft 禁入扫描
命令：
```bash
rg -n "Purchase Invoice|/api/resource/Purchase Invoice|payable-draft|payable_draft" app tests
```
结果：
- 仅命中 `app/models/factory_statement.py` 的状态枚举值 `payable_draft_created`
- 无 `Purchase Invoice` 调用实现
- 无 `/payable-draft` 路由实现

### 6.3 禁改目录扫描
命令：
```bash
git diff --name-only -- '06_前端' '.github' '02_源码'
```
结果：空输出

## 7. 结论
结论：**建议进入 TASK-006C**。
