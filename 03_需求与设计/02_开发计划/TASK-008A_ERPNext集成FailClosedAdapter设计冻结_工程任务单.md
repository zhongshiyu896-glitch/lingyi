# TASK-008A ERPNext 集成 Fail-Closed Adapter 设计冻结工程任务单

- 任务编号：TASK-008A
- 角色：工程师
- 优先级：P1
- 前置依赖：TASK-007 全链路完成（HEAD: `fe3f5b7e23f355219f90f51c3245044e0973d578`）
- 任务类型：设计冻结（无代码实现）

## 一、任务目标

冻结 ERPNext 集成 Fail-Closed Adapter 的统一设计，形成可审计、可实现、可回归的规范基线，覆盖：
1. Supplier / Account / Cost Center / Item / Sales Order / Purchase Order / Delivery Note / Stock Entry / Stock Ledger Entry / Work Order / Job Card / Purchase Invoice / User Permission。
2. fail-closed 错误语义、docstatus/status 判定、统一返回契约。
3. TASK-002~006 的回迁路径与测试矩阵。

## 二、任务边界

### 2.1 允许输出
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-008_ERPNext集成FailClosed规范.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-008A_ERPNext集成FailClosedAdapter设计冻结_工程任务单.md`

### 2.2 允许读取（禁止修改）
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_permission_adapter.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_stock_entry_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_job_card_adapter.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_production_adapter.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_purchase_invoice_adapter.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_style_profit_adapter.py`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/Sprint2_架构规范.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-007_权限与审计统一基座设计.md`

### 2.3 禁止修改
- `/Users/hh/Desktop/领意服装管理系统/06_前端/**`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/**`
- `/Users/hh/Desktop/领意服装管理系统/.github/**`
- `/Users/hh/Desktop/领意服装管理系统/02_源码/**`

## 三、必须输出内容

1. 现状梳理
   - 每个 Adapter 的职责、输入输出、鉴权方式。
   - 当前 fail-open / fail-closed 风险点。
   - 重复逻辑与公共抽象建议。

2. ERPNext 能力矩阵
   - doctype
   - 读取/写入
   - 是否要求 docstatus
   - 是否允许 status-only
   - 失败错误码
   - 适用模块

3. Fail-Closed 错误码表（冻结）
   - `EXTERNAL_SERVICE_UNAVAILABLE`
   - `PERMISSION_SOURCE_UNAVAILABLE`
   - `ERPNEXT_DOCSTATUS_REQUIRED`
   - `ERPNEXT_DOCSTATUS_INVALID`
   - `ERPNEXT_RESOURCE_NOT_FOUND`
   - `ERPNEXT_RESPONSE_INVALID`
   - `ERPNEXT_TIMEOUT`
   - `ERPNEXT_AUTH_FAILED`

4. docstatus/status 判定矩阵
   - `docstatus=0/1/2` 语义
   - 缺字段 fail closed
   - status-only 白名单按 doctype 明确列出

5. Adapter 统一返回契约
   - read result
   - write result
   - docstatus result
   - unavailable result
   - not found result

6. TASK-002~006 回迁清单
   - 外发 Stock Entry
   - 工票 Job Card
   - 生产 Work Order
   - 款式利润（SLE/Sales/外发来源）
   - 加工厂对账 Purchase Invoice draft

7. 测试矩阵
   - 连接失败 / 超时 / ERPNext 5xx / 401/403 / 404
   - docstatus 缺失 / draft / cancelled / submitted
   - malformed response
   - token/cookie/secret 脱敏验证

## 四、审计前置要求

审计官必须确认：
1. 文档没有直接要求业务代码实现。
2. ERPNext 失败不会以“空数据成功”伪装。
3. docstatus 缺失默认 fail closed。
4. User Permission 查询失败不等于 unrestricted。
5. Purchase Invoice draft 不等于 submitted。
6. Adapter 不在本地事务提交前写 ERPNext。
7. TASK-008B 实现边界清晰，不跨任务。

## 五、验收标准

- [ ] 已输出 `TASK-008_ERPNext集成FailClosed规范.md`
- [ ] 已输出 `TASK-008A_ERPNext集成FailClosedAdapter设计冻结_工程任务单.md`
- [ ] 现有 Adapter 梳理完成
- [ ] 能力矩阵完成
- [ ] fail-closed 错误码表完成
- [ ] docstatus/status 矩阵完成
- [ ] Adapter 返回契约完成
- [ ] TASK-002~006 回迁清单完成
- [ ] 测试矩阵完成
- [ ] 未改业务代码、前端、后端、`.github`、`02_源码`

## 六、执行约束

1. 不实现 Adapter 代码。
2. 不改后端业务逻辑。
3. 不改 migrations。
4. 不进入 TASK-009 / TASK-010 / TASK-011 / TASK-012。
5. 不提交、不 push、不配置 remote。

## 七、交付回复格式

```text
TASK-008A 执行完成。
输出文件：
1. /03_需求与设计/01_架构设计/TASK-008_ERPNext集成FailClosed规范.md
2. /03_需求与设计/02_开发计划/TASK-008A_ERPNext集成FailClosedAdapter设计冻结_工程任务单.md
结论：待审计
是否写业务代码：否
是否修改前端/后端/.github/02_源码：否
```
