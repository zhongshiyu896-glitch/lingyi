# 工程任务单：TASK-002B1 回料验货旧演示路径 Fail Closed 整改

- 任务编号：TASK-002B1
- 模块：外发加工管理
- 优先级：P1（TASK-002B 审计阻断修复）
- 任务类型：审计整改 / 阶段门禁 / 事务与异常边界
- 创建时间：2026-04-12 21:25 CST
- 作者：技术架构师
- 审计来源：TASK-002B 审计意见，回料和验货接口仍保留旧演示成功路径，越过 TASK-002B 边界

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-002B1
模块：外发加工管理
优先级：P1（必须修复后才允许 TASK-002B 复审，仍禁止进入 TASK-002C/D/E）
════════════════════════════════════════════════════════════════════════════

【任务目标】
关闭外发回料与验货旧演示成功路径：在 TASK-002B 阶段，`receive()` 和 `inspect()` 必须完成鉴权与资源权限校验后 fail closed，不得写本地回料/验货事实，不得推进状态，不得沿用旧金额公式，不得伪造库存成功。

【问题背景】
TASK-002B 的边界是权限、资源权限、安全审计、操作审计、统一错误信封和事务边界，不包含回料 outbox、ERPNext Stock Entry、验货金额口径实现。审计发现当前 `receive()` 仍会写本地回料事实并推进状态，`inspect()` 仍会完成验货并使用旧公式 `net_amount = inspected_qty - deduction_amount`。这会在没有 outbox 和正确金额口径前产生错误业务事实。

【涉及文件】
必须修改：
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/subcontract.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/subcontract_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/subcontract.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/error_codes.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/exceptions.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/audit_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/logging.py`

必须新增或补充测试：
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_permissions.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_audit.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_exception_handling.py`

【本任务边界】
只允许修复 TASK-002B 阶段越界问题：
1. 回料接口 fail closed。
2. 验货接口 fail closed。
3. 删除 `draft` 直接回料状态通道。
4. 写入异常分类为 `DATABASE_WRITE_FAILED`。
5. 回料接口校验顺序调整为鉴权优先。

禁止进入：
1. TASK-002C 数据模型迁移。
2. TASK-002D 发料 Stock Entry Outbox。
3. TASK-002E 回料 Stock Entry Outbox。
4. TASK-002F 验货扣款金额正式实现。
5. TASK-002G/H 前端状态联动和对账出口。

【核心整改要求】

## 一、回料接口必须 fail closed
`POST /api/subcontract/{id}/receive` 在 TASK-002B 阶段必须按以下顺序执行：

1. 规范化 `request_id`。
2. 解析当前用户；未登录返回 `AUTH_UNAUTHORIZED` 并写安全审计。
3. 校验动作权限 `subcontract:receive`；无权限返回 `AUTH_FORBIDDEN` 并写安全审计。
4. 读取目标外发单；读取失败返回 `DATABASE_READ_FAILED`。
5. 校验外发单 `company/item_code/supplier` 资源权限；无权限返回 `AUTH_FORBIDDEN` 并写安全审计。
6. 校验回料仓 `receipt_warehouse` 资源权限；当前 schema 没有回料仓字段时，必须返回 `SUBCONTRACT_WAREHOUSE_REQUIRED` 或等价 fail closed 错误。
7. 鉴权和资源权限通过后，由于 TASK-002E 尚未实现回料 outbox，返回 `SUBCONTRACT_OUTBOX_REQUIRED` 或等价未实现错误。
8. 不得新增 `ly_subcontract_receipt`。
9. 不得修改 `ly_subcontract_order.status`。
10. 不得新增 `ly_subcontract_status_log` 表示回料成功。
11. 不得伪造或返回 `stock_entry_name`。
12. 不得调用 ERPNext 写接口。

## 二、验货接口必须 fail closed
`POST /api/subcontract/{id}/inspect` 在 TASK-002B 阶段必须按以下顺序执行：

1. 规范化 `request_id`。
2. 解析当前用户；未登录返回 `AUTH_UNAUTHORIZED` 并写安全审计。
3. 校验动作权限 `subcontract:inspect`；无权限返回 `AUTH_FORBIDDEN` 并写安全审计。
4. 读取目标外发单；读取失败返回 `DATABASE_READ_FAILED`。
5. 校验外发单 `company/item_code/supplier` 资源权限；无权限返回 `AUTH_FORBIDDEN` 并写安全审计。
6. 鉴权和资源权限通过后，由于 TASK-002F 尚未实现验货扣款金额口径，返回 `SUBCONTRACT_INSPECTION_NOT_IMPLEMENTED` 或等价未实现错误。
7. 不得新增 `ly_subcontract_inspection`。
8. 不得修改 `ly_subcontract_receipt`。
9. 不得修改 `ly_subcontract_order.status` 为 `completed`。
10. 不得写入 `gross_amount/deduction_amount/net_amount`。
11. 不得计算或返回旧公式 `net_amount = inspected_qty - deduction_amount`。

## 三、删除 draft 直接回料通道
现有旧逻辑允许 `draft` 状态直接 `receive()`，必须删除。

要求：
1. `draft` 状态调用回料不得成功。
2. 如鉴权通过且进入业务状态校验，必须返回 `SUBCONTRACT_STATUS_INVALID` 或被 TASK-002B 阶段 fail closed 门禁拦截。
3. 无论返回哪一种错误，都不得写回料事实、状态日志或修改状态。

## 四、写入异常分类
所有外发写接口在 TASK-002B 阶段必须统一异常分类：

1. `session.flush()` / `session.commit()` / ORM 写入 `SQLAlchemyError` 返回 `DATABASE_WRITE_FAILED`。
2. 数据库读取外发单或资源信息失败返回 `DATABASE_READ_FAILED`。
3. 审计写入失败返回 `AUDIT_WRITE_FAILED`。
4. 未知异常返回 `SUBCONTRACT_INTERNAL_ERROR`。
5. 不得返回裸 `HTTP_ERROR`、`ValueError` 原文或 `SUBCONTRACT_INTERNAL_ERROR` 包住明确 DB 写失败。
6. rollback 失败只写脱敏日志，不覆盖原始错误码。

## 五、鉴权优先顺序
回料接口必须鉴权优先于业务字段校验。

验收顺序：
1. 未登录 + payload 字段缺失：返回 `AUTH_UNAUTHORIZED`，不是字段校验错误。
2. 无 `subcontract:receive` + payload 字段缺失：返回 `AUTH_FORBIDDEN`，不是字段校验错误。
3. 权限源不可用 + payload 字段缺失：返回 `PERMISSION_SOURCE_UNAVAILABLE`，不是字段校验错误。
4. 只有鉴权、动作权限、资源权限全部通过后，才允许进入仓库/数量/状态等业务校验或 TASK-002B fail closed 门禁。

【错误码要求】
必须补齐或复用：
- `SUBCONTRACT_OUTBOX_REQUIRED`：当前动作必须等待 outbox 能力实现，TASK-002B 阶段禁止旧演示成功路径。
- `SUBCONTRACT_INSPECTION_NOT_IMPLEMENTED`：验货扣款正式口径尚未实现，TASK-002B 阶段禁止旧演示成功路径。
- `SUBCONTRACT_WAREHOUSE_REQUIRED`：当前动作必须提供仓库，无法校验仓库资源权限时 fail closed。
- `SUBCONTRACT_STATUS_INVALID`
- `DATABASE_READ_FAILED`
- `DATABASE_WRITE_FAILED`
- `AUDIT_WRITE_FAILED`
- `AUTH_UNAUTHORIZED`
- `AUTH_FORBIDDEN`
- `PERMISSION_SOURCE_UNAVAILABLE`
- `SUBCONTRACT_INTERNAL_ERROR`

【验收标准】
□ `POST /api/subcontract/{id}/receive` 鉴权通过后返回 fail closed 错误，不新增 `ly_subcontract_receipt`。
□ `POST /api/subcontract/{id}/receive` 不修改外发单状态。
□ `POST /api/subcontract/{id}/receive` 不新增“回料成功”状态日志。
□ `POST /api/subcontract/{id}/receive` 不返回伪 `stock_entry_name`。
□ `POST /api/subcontract/{id}/inspect` 鉴权通过后返回 fail closed 错误，不新增验货事实。
□ `POST /api/subcontract/{id}/inspect` 不修改回料记录。
□ `POST /api/subcontract/{id}/inspect` 不将外发单状态改为 `completed`。
□ `POST /api/subcontract/{id}/inspect` 不计算或返回旧公式 `net_amount = inspected_qty - deduction_amount`。
□ `draft` 状态不能直接回料成功。
□ 回料接口未登录时，即使 payload 缺字段，也返回 `AUTH_UNAUTHORIZED`。
□ 回料接口无权限时，即使 payload 缺字段，也返回 `AUTH_FORBIDDEN`。
□ 权限源不可用时，即使 payload 缺字段，也返回 `PERMISSION_SOURCE_UNAVAILABLE`。
□ 回料/验货写入阶段 DB 异常返回 `DATABASE_WRITE_FAILED`。
□ 数据库读取异常返回 `DATABASE_READ_FAILED`。
□ 审计写入失败返回 `AUDIT_WRITE_FAILED`，业务回滚。
□ 响应和日志不泄露 SQL、Authorization、Cookie、token、password、secret。
□ 全量测试继续通过。

【测试要求】
必须新增或补齐以下测试：
1. `test_receive_fail_closed_after_auth_does_not_create_receipt`
2. `test_receive_fail_closed_after_auth_does_not_change_order_status`
3. `test_receive_fail_closed_after_auth_does_not_create_success_status_log`
4. `test_receive_fail_closed_after_auth_does_not_return_fake_stock_entry_name`
5. `test_inspect_fail_closed_after_auth_does_not_create_inspection`
6. `test_inspect_fail_closed_after_auth_does_not_update_receipt`
7. `test_inspect_fail_closed_after_auth_does_not_complete_order`
8. `test_inspect_fail_closed_does_not_use_legacy_net_amount_formula`
9. `test_draft_order_cannot_receive_successfully`
10. `test_receive_auth_is_checked_before_payload_validation_when_unauthorized`
11. `test_receive_permission_is_checked_before_payload_validation_when_forbidden`
12. `test_receive_permission_source_unavailable_before_payload_validation`
13. `test_receive_database_write_failure_returns_database_write_failed`
14. `test_inspect_database_write_failure_returns_database_write_failed`
15. `test_receive_audit_write_failed_rolls_back_business_changes`
16. `test_inspect_audit_write_failed_rolls_back_business_changes`
17. `test_subcontract_fail_closed_logs_are_sanitized`
18. `test_subcontract_no_fake_stock_entry_name_after_task_002b1`

【回归命令】
在 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service` 下执行：

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m unittest discover
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
rg "STE-ISS|net_amount = .*inspected_qty|operator=\"service_account\"|detail=str\(exc\)" app/routers app/services app/schemas tests
```

【前置依赖】
- TASK-002A：外发模块设计契约冻结已封版
- TASK-002B：权限与审计基线已开始但审计不通过

【交付物】
1. 回料接口 TASK-002B 阶段 fail closed 实现。
2. 验货接口 TASK-002B 阶段 fail closed 实现。
3. `draft` 直接回料通道关闭。
4. 回料/验货异常分类修复。
5. 鉴权优先于业务字段校验测试。
6. 全量测试结果。

【禁止事项】
1. 禁止在本任务中实现回料 Stock Entry outbox。
2. 禁止在本任务中实现验货正式金额口径。
3. 禁止在本任务中新增 TASK-002C/D/E 迁移或 outbox 表。
4. 禁止回料/验货继续写本地业务事实并返回成功。
5. 禁止继续使用旧公式 `net_amount = inspected_qty - deduction_amount`。
6. 禁止继续生成或返回伪 `STE-ISS-*` / `stock_entry_name`。
7. 禁止绕过鉴权先做 payload 字段校验。

════════════════════════════════════════════════════════════════════════════
