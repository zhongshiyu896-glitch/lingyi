# 【补审任务卡】TASK-B5 Sprint2审计缺口补审 - 销售库存只读

- 任务编号：TASK-B5
- 任务名称：Sprint2 审计缺口补审（销售/库存只读集成）
- 角色：审计官
- 优先级：P0
- 前置依赖：TASK-013C 审计通过；基线参考 HEAD `384970400f7a137e8384649bd73cab5ae2d33300`

## 补审范围
- 设计文档：`/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-011_销售库存只读集成设计.md`
- 后端：`sales_inventory` router/schema/service/adapter 及相关权限校验
- 前端：`sales_inventory` API/views/router/store/contracts
- 测试：`test_sales_inventory_api.py`、`test_sales_inventory_permissions.py`、`test_sales_inventory_adapter.py`、前端 contracts

## 审计要点
1. 全链路只读（GET-only，无 POST/PUT/PATCH/DELETE 写语义）。
2. Customer 权限 fail closed，不得空权限放开。
3. 详情防枚举（存在但越权对外不可区分）。
4. ERPNext malformed/unavailable fail closed，不得伪成功。
5. 前端禁写、禁 `/api/resource` 直连、禁 internal/run-once/diagnostic 普通入口。

## 通过标准
- 高危（P1）= 0。
- 中危（P2）<= 1（若存在必须有明确整改计划）。
- P1/P2 必须整改并复审通过后方可闭环。
- 后端与前端契约测试全部通过。

## 执行说明
```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest -q tests/test_sales_inventory*.py tests/test_permissions*.py tests/test_erpnext_fail_closed_adapter.py

cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc
npm run check:sales-inventory-contracts
npm run test:sales-inventory-contracts
npm run verify
```
不通过下发 `TASK-B5A`。

## 禁止事项
- 禁止修改 `06_前端/**`、`07_后端/**`、`.github/**`、`02_源码/**`。
- 禁止 push / remote / PR。
- 禁止引入任何 ERPNext 写入、outbox、财务写入。

## 完成后回复格式
```text
TASK-B5 执行完成。
审计结论：通过 / 有条件通过 / 不通过
问题项：高 X / 中 X / 低 X
是否允许进入下一任务：是 / 否
若否，整改任务：TASK-B5A
```
