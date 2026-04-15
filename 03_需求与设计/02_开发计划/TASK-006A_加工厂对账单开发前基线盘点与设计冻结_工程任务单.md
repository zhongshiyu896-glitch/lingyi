# TASK-006A 加工厂对账单开发前基线盘点与设计冻结工程任务单

- 任务编号：TASK-006A
- 模块：加工厂对账单
- 优先级：P0
- 版本：V1.0
- 更新时间：2026-04-15 17:09 CST
- 作者：技术架构师
- 前置依赖：TASK-002 外发加工管理已完成；TASK-005 已允许标记为本地封版完成
- 任务边界：只做开发前基线盘点和设计冻结；不得写后端业务实现、不得写前端页面、不得新增迁移、不得调用 ERPNext 创建应付草稿。

## 一、任务目标

完成加工厂对账单开发前基线盘点，冻结对账单的数据来源、金额口径、幂等规则、状态机、权限审计和 ERPNext 边界，为后续 TASK-006B 后端实现提供可审计契约。

## 二、必须先读文件

```text
/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/02_模块设计_外发加工管理.md
/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/07_模块设计_加工厂对账单.md
/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-002H_对账数据出口_工程任务单.md
/Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录.md
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/subcontract.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/subcontract_service.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/subcontract_settlement_service.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/subcontract.py
```

## 三、允许修改文件

```text
/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-006_加工厂对账单_开发前基线盘点.md
/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-006A_加工厂对账单开发前基线盘点证据.md
```

## 四、禁止修改文件

```text
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/**
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/**
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/**
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/**
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/**
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/**
/Users/hh/Desktop/领意服装管理系统/06_前端/**
/Users/hh/Desktop/领意服装管理系统/.github/**
/Users/hh/Desktop/领意服装管理系统/02_源码/**
```

## 五、输出文件要求

### 1. 基线盘点文档

创建：

```text
/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-006_加工厂对账单_开发前基线盘点.md
```

文档必须包含：

1. TASK-002 外发对账出口现状。
2. 可作为对账来源的表、字段、状态和金额字段。
3. 不可作为对账来源的演示字段、临时字段、旧公式或未审计字段。
4. 对账单明细来源粒度：按外发单、回料批次、验货记录或结算锁定记录，必须给出唯一选择和理由。
5. 可对账明细筛选条件：必须明确 `company / supplier / inspected_at 或 settled_at / status / statement_lock` 等条件。
6. 金额口径：加工费、扣款、实付金额、不合格率公式。
7. 幂等口径：`idempotency_key`、`request_hash`、重复提交 replay、冲突返回码。
8. 重复对账防护：同一来源明细不得进入多个未取消对账单。
9. 状态机：`draft / confirmed / cancelled / payable_draft_created` 的进入条件和禁止操作。
10. 权限口径：登录鉴权、动作权限、供应商资源权限、公司权限、ERPNext 权限源不可用 fail closed。
11. 审计口径：安全审计、操作审计、失败审计、日志脱敏。
12. ERPNext 边界：Supplier、Account、Cost Center 校验；Purchase Invoice 草稿生成是否走 outbox 或同步 REST，需要给出后续 TASK-006D 建议。
13. 风险清单：列出进入 TASK-006B 前仍需确认的风险。
14. 建议拆分：给出 TASK-006B/C/D/E/F 的建议任务边界。

### 2. 证据文档

创建：

```text
/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-006A_加工厂对账单开发前基线盘点证据.md
```

证据文档必须包含：

1. 本次只读检查的文件清单。
2. 是否修改业务代码：必须写“否”。
3. 对账来源字段确认表。
4. 金额公式确认表。
5. 权限与审计确认表。
6. ERPNext fail closed 确认表。
7. 禁改范围扫描结果。
8. 下一步是否建议进入 TASK-006B。

## 六、冻结业务规则

1. 对账单只允许从 TASK-002 已审计的外发验货/结算事实生成，不允许信任前端传入明细金额。
2. `gross_amount = sum(statement_item.gross_amount)`。
3. `deduction_amount = sum(statement_item.deduction_amount)`。
4. `net_amount = gross_amount - deduction_amount`。
5. `rejected_rate = total_rejected_qty / inspected_qty`，`inspected_qty=0` 的处理必须在基线文档中冻结。
6. 同一 `company + supplier + from_date + to_date + request_hash` 下，未取消对账单不得重复生成。
7. 同一外发来源明细不得进入多个未取消对账单。
8. 对账单确认后，不允许修改明细数量、加工费、扣款、实付金额。
9. 确认人必须来自当前登录用户，不允许使用前端传入的 `confirmed_by`。
10. ERPNext Supplier、Account、Cost Center 不可校验时必须 fail closed。
11. 未完成 TASK-006D 前，不允许实现 ERPNext `Purchase Invoice` 生产写入。

## 七、错误码要求

基线文档必须规划以下错误码：

| 错误码 | 场景 |
| --- | --- |
| `FACTORY_STATEMENT_PERMISSION_DENIED` | 动作权限或资源权限不足。 |
| `FACTORY_STATEMENT_PERMISSION_SOURCE_UNAVAILABLE` | ERPNext 权限源不可用。 |
| `FACTORY_STATEMENT_SUPPLIER_NOT_FOUND` | Supplier 不存在或不可用。 |
| `FACTORY_STATEMENT_SOURCE_NOT_FOUND` | 期间内无可对账来源明细。 |
| `FACTORY_STATEMENT_SOURCE_ALREADY_LOCKED` | 来源明细已进入未取消对账单。 |
| `FACTORY_STATEMENT_IDEMPOTENCY_CONFLICT` | 同一幂等键下请求 hash 不一致。 |
| `FACTORY_STATEMENT_STATUS_INVALID` | 当前状态不允许确认、取消或生成应付草稿。 |
| `FACTORY_STATEMENT_CONFIRMED_LOCKED` | 已确认对账单禁止改金额。 |
| `FACTORY_STATEMENT_ERPNEXT_UNAVAILABLE` | ERPNext 不可用。 |
| `FACTORY_STATEMENT_DATABASE_READ_FAILED` | 数据库读取失败。 |
| `FACTORY_STATEMENT_DATABASE_WRITE_FAILED` | 数据库写入失败。 |

## 八、验收标准

- [ ] 已创建 `TASK-006_加工厂对账单_开发前基线盘点.md`。
- [ ] 已创建 `TASK-006A_加工厂对账单开发前基线盘点证据.md`。
- [ ] 基线文档明确外发对账来源粒度，且不是“前端传入明细”。
- [ ] 基线文档明确金额公式，包含 `gross_amount / deduction_amount / net_amount / rejected_rate`。
- [ ] 基线文档明确幂等 replay 和冲突策略。
- [ ] 基线文档明确重复对账防护策略。
- [ ] 基线文档明确 confirmed 后金额锁定规则。
- [ ] 基线文档明确 ERPNext 不可用时 confirm/payable-draft 的 fail closed 策略。
- [ ] 基线文档明确 `Purchase Invoice` 草稿生成必须进入后续 TASK-006D，不得在 TASK-006A 实现。
- [ ] 证据文档说明未修改前端、后端、迁移、workflow、`02_源码`。
- [ ] 禁改范围扫描无业务代码改动。

## 九、建议验证命令

```bash
cd /Users/hh/Desktop/领意服装管理系统

git diff --name-only -- \
  '07_后端' \
  '06_前端' \
  '.github' \
  '02_源码'

find '03_需求与设计' -type f -name 'TASK-006*' | sort
```

预期：

1. 第一个命令无输出。
2. 第二个命令至少包含 TASK-006A 任务单、基线盘点文档和证据文档。

## 十、交付后回复格式

```text
TASK-006A 已完成。

已输出：
- /03_需求与设计/01_架构设计/TASK-006_加工厂对账单_开发前基线盘点.md
- /03_需求与设计/02_开发计划/TASK-006A_加工厂对账单开发前基线盘点证据.md

结论：建议/不建议进入 TASK-006B。

关键冻结口径：
1. 对账来源粒度：[填写]
2. 金额公式：[填写]
3. 幂等策略：[填写]
4. ERPNext 应付草稿边界：[填写]
5. 剩余风险：[填写]
```
