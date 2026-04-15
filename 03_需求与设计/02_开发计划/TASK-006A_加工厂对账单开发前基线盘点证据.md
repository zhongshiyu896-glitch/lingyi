# TASK-006A 加工厂对账单开发前基线盘点证据

- 任务编号：TASK-006A
- 证据日期：2026-04-15
- 任务性质：开发前基线盘点与设计冻结（文档任务）

## 1. 只读检查文件清单

1. `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/02_模块设计_外发加工管理.md`
2. `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/07_模块设计_加工厂对账单.md`
3. `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-002H_对账数据出口_工程任务单.md`
4. `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录.md`
5. `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/subcontract.py`
6. `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/subcontract_service.py`
7. `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/subcontract_settlement_service.py`
8. `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/subcontract.py`
9. `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-006A_加工厂对账单开发前基线盘点与设计冻结_工程任务单.md`

## 2. 是否修改业务代码

- 结论：**否**。
- 说明：本次仅新增文档，不修改 `06_前端/**`、`07_后端/**`、`.github/**`、`02_源码/**`。

## 3. 对账来源字段确认表

| 项 | 冻结结论 |
| --- | --- |
| 来源粒度 | `ly_subcontract_inspection` 验货记录粒度（唯一选择） |
| 来源主键 | `inspection.id`（并使用 `settlement_line_key` 做来源唯一标识） |
| 资源边界字段 | `company` + `supplier` |
| 日期口径 | 主筛选 `inspected_at`；`settled_at` 仅预留，不作为 006B 主筛选 |
| 状态口径 | 已验货、`settlement_status=unsettled`、未进入未取消对账单 |
| 锁定字段 | `settlement_status` + `statement_id/statement_no` |
| 禁止来源 | 前端传入明细金额、订单汇总金额、未审计临时字段 |

## 4. 金额公式确认表

| 指标 | 冻结公式 |
| --- | --- |
| `gross_amount` | `sum(statement_item.gross_amount)` |
| `deduction_amount` | `sum(statement_item.deduction_amount)` |
| `net_amount` | `gross_amount - deduction_amount` |
| `rejected_rate` | `total_rejected_qty / total_inspected_qty`，`total_inspected_qty=0` 时取 `0` |

验收算例：加工费 `5000`、扣款 `300`，则 `net_amount = 4700`。

## 5. 权限与审计确认表

| 项 | 冻结结论 |
| --- | --- |
| 动作权限 | `factory_statement:read/create/confirm/payable_draft/cancel` |
| 资源权限 | 必须 `company + supplier` 双维度校验 |
| 权限源不可用 | fail closed，不得放行敏感读写 |
| 确认人来源 | `confirmed_by` 必须来自当前登录用户，不信任前端 |
| 审计日志 | create/confirm/payable_draft/cancel 成功与失败均写审计，敏感信息脱敏 |

## 6. ERPNext Fail Closed 确认表

| 场景 | 冻结策略 |
| --- | --- |
| Supplier 不可校验 | fail closed |
| Account 不可校验 | fail closed |
| Cost Center 不可校验 | fail closed |
| ERPNext 服务不可用 | fail closed |
| 权限源不可用 | fail closed |
| Purchase Invoice 草稿创建 | 仅可在 TASK-006D 设计审计通过后实现；006A/006B/006C 禁止实现 |

## 7. 幂等与重复对账防护确认

1. `idempotency_key + request_hash` 作为幂等主口径。
2. replay：同幂等键且 hash 一致，返回第一次结果。
3. conflict：同幂等键但 hash 不一致，返回 `FACTORY_STATEMENT_IDEMPOTENCY_CONFLICT`。
4. 同一来源明细不得进入多个未取消对账单。
5. 同一 `company+supplier+from_date+to_date+request_hash` 不得重复生成未取消对账单。

## 8. 禁改范围扫描结果

执行命令：

```bash
cd /Users/hh/Desktop/领意服装管理系统
git diff --name-only -- '07_后端' '06_前端' '.github' '02_源码'
find '03_需求与设计' -type f -name 'TASK-006*' | sort
```

扫描结果：

1. `git diff --name-only -- '07_后端' '06_前端' '.github' '02_源码'` 输出为空（未修改禁改业务目录）。
2. `find ... TASK-006*` 包含：
   - `03_需求与设计/01_架构设计/TASK-006_加工厂对账单_开发前基线盘点.md`
   - `03_需求与设计/02_开发计划/TASK-006A_加工厂对账单开发前基线盘点与设计冻结_工程任务单.md`
   - `03_需求与设计/02_开发计划/TASK-006A_加工厂对账单开发前基线盘点证据.md`

## 9. 输出文件确认

1. `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-006_加工厂对账单_开发前基线盘点.md`
2. `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-006A_加工厂对账单开发前基线盘点证据.md`

## 10. 结论

- 结论：**建议进入 TASK-006B**（前提：TASK-006A 审计通过）。
- 说明：本次仅完成开发前口径冻结，不包含后端实现、前端实现、迁移和 ERPNext Purchase Invoice 写入。
