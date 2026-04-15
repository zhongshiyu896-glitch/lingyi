# TASK-006B 加工厂对账单后端模型迁移与草稿 API 交付证据

## 1. 任务与基线
- 任务编号：`TASK-006B`
- 前置：`TASK-006A`（审计意见书第 161 份已通过）
- 执行范围：仅后端模型/迁移/草稿 API/权限与审计/测试
- 当前 HEAD：`1da795333d20ed8ecfb2308da623358668272458`

## 2. 修改文件清单
### 新增
- `07_后端/lingyi_service/app/models/factory_statement.py`
- `07_后端/lingyi_service/app/schemas/factory_statement.py`
- `07_后端/lingyi_service/app/routers/factory_statement.py`
- `07_后端/lingyi_service/app/services/factory_statement_service.py`
- `07_后端/lingyi_service/migrations/versions/task_006b_create_factory_statement_tables.py`
- `07_后端/lingyi_service/tests/test_factory_statement_api.py`
- `07_后端/lingyi_service/tests/test_factory_statement_models.py`
- `07_后端/lingyi_service/tests/test_factory_statement_permissions.py`
- `07_后端/lingyi_service/tests/test_factory_statement_idempotency.py`
- `07_后端/lingyi_service/tests/test_factory_statement_audit.py`

### 按需修改
- `07_后端/lingyi_service/app/core/error_codes.py`
- `07_后端/lingyi_service/app/core/permissions.py`
- `07_后端/lingyi_service/app/services/permission_service.py`
- `07_后端/lingyi_service/app/main.py`
- `07_后端/lingyi_service/app/models/__init__.py`

## 3. 新增表与索引（迁移）
迁移文件：`migrations/versions/task_006b_create_factory_statement_tables.py`

### 3.1 `ly_factory_statement`
- 主字段：`statement_no/company/supplier/from_date/to_date/source_type/source_count/inspected_qty/rejected_qty/accepted_qty/gross_amount/deduction_amount/net_amount/rejected_rate/statement_status/idempotency_key/request_hash/created_by/created_at/updated_at`
- 关键约束/索引：
  - `uk_ly_factory_statement_no`
  - `uk_ly_factory_statement_company_idempotency`
  - `idx_ly_factory_statement_company_supplier_status_created`
  - `ck_ly_factory_statement_status`

### 3.2 `ly_factory_statement_item`
- 主字段：`statement_id/line_no/inspection_id/subcontract_id/.../gross_amount/deduction_amount/net_amount/rejected_rate/source_snapshot`
- 关键约束/索引：
  - `idx_ly_factory_statement_item_statement`
  - `uk_ly_factory_statement_item_inspection`（单 inspection 仅允许进入一个未取消对账单链路）
  - `idx_ly_factory_statement_item_company_supplier_time`

### 3.3 `ly_factory_statement_log`
- 主字段：`statement_id/company/supplier/from_status/to_status/action/operator/request_id/remark/operated_at`
- 关键索引：
  - `idx_ly_factory_statement_log_statement_time`
  - `idx_ly_factory_statement_log_company_statement`

## 4. 接口与权限动作
### 4.1 已实现接口
- `POST /api/factory-statements/`
- `GET /api/factory-statements/`
- `GET /api/factory-statements/{id}`

### 4.2 未实现（按任务禁线）
- `POST /api/factory-statements/{id}/confirm`
- `POST /api/factory-statements/{id}/cancel`
- `POST /api/factory-statements/{id}/payable-draft`

### 4.3 权限动作
- `factory_statement:read`
- `factory_statement:create`

并已接入：
- 动作权限校验
- `company + supplier` 资源权限校验
- 权限源不可用 fail closed（映射 `FACTORY_STATEMENT_PERMISSION_SOURCE_UNAVAILABLE`）

## 5. 冻结口径落实
- 对账来源粒度固定：`ly_subcontract_inspection`
- 来源过滤：`company/supplier/status=inspected/settlement_status=unsettled/inspected_at区间/net_amount>=0`
- 服务端事实生成：不信任前端明细金额
- 金额公式：
  - `gross_amount = sum(item.gross_amount)`
  - `deduction_amount = sum(item.deduction_amount)`
  - `net_amount = gross_amount - deduction_amount`
- `inspected_qty = 0 => rejected_rate = 0`
- 幂等：`company + idempotency_key + request_hash`
  - 同 key 同 hash：replay 同一 statement
  - 同 key 异 hash：`FACTORY_STATEMENT_IDEMPOTENCY_CONFLICT`
- 事务内完成：创建 statement + items 快照 + log + inspection 锁定
- 锁定字段：`settlement_status=statement_locked`、`statement_id`、`statement_no`、`settlement_locked_by`、`settlement_locked_at`
- 详情读取快照：`ly_factory_statement_item`，不做实时重算覆盖

## 6. 错误码实现
已在 `app/core/error_codes.py` 实现并映射状态码/默认文案：
- `FACTORY_STATEMENT_PERMISSION_DENIED`
- `FACTORY_STATEMENT_PERMISSION_SOURCE_UNAVAILABLE`
- `FACTORY_STATEMENT_SUPPLIER_REQUIRED`
- `FACTORY_STATEMENT_COMPANY_REQUIRED`
- `FACTORY_STATEMENT_PERIOD_INVALID`
- `FACTORY_STATEMENT_SOURCE_NOT_FOUND`
- `FACTORY_STATEMENT_SOURCE_ALREADY_LOCKED`
- `FACTORY_STATEMENT_IDEMPOTENCY_CONFLICT`
- `FACTORY_STATEMENT_DATABASE_READ_FAILED`
- `FACTORY_STATEMENT_DATABASE_WRITE_FAILED`
- `FACTORY_STATEMENT_INTERNAL_ERROR`

## 7. 测试结果
### 7.1 定向 pytest
命令：
```bash
.venv/bin/python -m pytest -q tests/test_factory_statement_api.py tests/test_factory_statement_models.py tests/test_factory_statement_permissions.py tests/test_factory_statement_idempotency.py tests/test_factory_statement_audit.py
```
结果：`18 passed`

覆盖要点：
- 两条 inspection 生成草稿成功
- `5000 - 300 = 4700`
- `inspected_qty=0 => rejected_rate=0`
- inspection 生成后被锁定
- 幂等 replay / conflict
- 已锁定来源不可重复入单
- create/read 权限与资源权限拒绝
- 权限源不可用 503
- 详情“先鉴权后查 ID”
- commit 失败归类 `DATABASE_WRITE_FAILED`
- 审计日志脱敏

### 7.2 全量 pytest
命令：
```bash
.venv/bin/python -m pytest -q
```
结果：`659 passed, 13 skipped`

### 7.3 unittest
命令：
```bash
.venv/bin/python -m unittest discover
```
结果：`Ran 642 tests ... OK (skipped=1)`

### 7.4 py_compile
命令：
```bash
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
```
结果：通过

## 8. 禁入扫描
### 8.1 ERPNext Purchase Invoice / payable-draft 扫描
命令：
```bash
rg -n "Purchase Invoice|/api/resource/Purchase Invoice|payable-draft|payable_draft" app tests
```
结果：
- 命中 1 处：`app/models/factory_statement.py` 的状态枚举 `payable_draft_created`
- 未命中任何 `Purchase Invoice` 调用
- 未命中任何 `/payable-draft` 路由实现

补充扫描：
```bash
rg -n "factory-statements/.*/confirm|factory-statements/.*/cancel|factory-statements/.*/payable-draft|payable_draft|payable-draft" app/routers app/services tests
```
结果：无命中（exit code 1）

结论：`TASK-006B` 未实现 confirm/cancel/payable-draft 接口，未创建 ERPNext Purchase Invoice。

## 9. 禁改目录扫描
命令：
```bash
git diff --name-only -- '06_前端' '.github' '02_源码'
```
结果：空输出

结论：未修改 `06_前端/**`、`.github/**`、`02_源码/**`。

## 10. 任务边界确认
- 未新增前端页面或前端 API
- 未实现 confirm/cancel/payable-draft
- 未写入 ERPNext Purchase Invoice
- 仅完成 TASK-006B 后端草稿基线

## 11. 结论
结论：**建议进入 TASK-006C**。
