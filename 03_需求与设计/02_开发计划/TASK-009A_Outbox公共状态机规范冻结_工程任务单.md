# TASK-009A Outbox 公共状态机规范冻结工程任务单

- 任务编号：TASK-009A
- 角色：工程师
- 优先级：P1
- 前置依赖：TASK-008D 审计通过（HEAD `e468231102e182faa85cb49f0bb8694bde65a650`）
- 任务类型：设计冻结（仅文档，不写代码）

## 一、任务目标

冻结 Outbox 公共状态机规范，统一 TASK-002 / TASK-003 / TASK-004 / TASK-006 中反复出现的 event_key、幂等、claim/lease、retry、dry-run、diagnostic、worker 前置校验和审计规则，为 TASK-009B 公共模板实现提供可审计前置契约。

## 二、任务边界

### 2.1 允许输出
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-009_Outbox公共状态机规范.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-009A_Outbox公共状态机规范冻结_工程任务单.md`

### 2.2 允许读取（禁止修改）
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/subcontract_stock_outbox_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/subcontract_stock_worker_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/workshop_outbox_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/workshop_job_card_sync_worker.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/production_work_order_outbox_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/production_work_order_worker.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/factory_statement_payable_outbox_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/factory_statement_payable_worker.py`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/Sprint2_架构规范.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/Sprint1_复盘报告.md`

### 2.3 禁止修改
- `/Users/hh/Desktop/领意服装管理系统/06_前端/**`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/**`
- `/Users/hh/Desktop/领意服装管理系统/.github/**`
- `/Users/hh/Desktop/领意服装管理系统/02_源码/**`

## 三、必须冻结内容

### 3.1 现有实现对比
输出四套 outbox 的统一对比表，至少覆盖：
1. 表名/模型
2. 服务类
3. worker 类
4. event_key 组成
5. claim 策略
6. retry 策略
7. dry-run/diagnostic 能力
8. 已知审计问题

### 3.2 标准字段
冻结以下标准字段与语义：
- `id`
- `event_key`
- `aggregate_type`
- `aggregate_id`
- `action`
- `status`
- `payload_json`
- `payload_hash`
- `request_hash`
- `idempotency_key`
- `attempts`
- `next_retry_at`
- `locked_by`
- `locked_until`
- `external_docname`
- `external_docstatus`
- `error_code`
- `error_message`
- `created_by`
- `created_at`
- `updated_at`

并给出类型建议、必填性、索引建议、审计用途。

### 3.3 标准状态机
必须冻结状态集合：
- `pending`
- `processing`
- `succeeded`
- `failed`
- `dead`
- `cancelled`

必须给出标准迁移图：
- `pending -> processing`
- `processing -> succeeded`
- `processing -> failed`
- `failed -> pending`
- `failed -> dead`
- `pending/failed -> cancelled`
- `cancelled` 终态

### 3.4 event_key 规范
必须冻结：
1. event_key 来自稳定业务事实。
2. 禁止包含 `idempotency_key/request_id/outbox_id/created_at/operator`。
3. 长字段先 hash 再拼接。
4. 禁止“拼接后截断 hash”。
5. 明确 event_key 与 idempotency_key 的职责分离。
6. 明确 active unique 防重规则。

### 3.5 claim/lease 规范
必须冻结：
1. due 条件包含 `pending/failed due` 与 `processing lease expired`。
2. 第二阶段 UPDATE 必须重复校验 due/lease。
3. PostgreSQL 优先 `FOR UPDATE SKIP LOCKED`。
4. claim 事务先提交，再调用 ERPNext。
5. stale id 不得抢占未过期 processing lease。

### 3.6 worker 前置校验规范
必须冻结：
1. 调 ERPNext 前重读 aggregate。
2. 校验 aggregate 状态。
3. 校验 payload_hash/金额/数量未漂移。
4. 校验服务账号动作权限与资源权限。
5. 校验 ERPNext docstatus。
6. aggregate cancelled 时禁止外调 ERPNext。

### 3.7 dry-run / diagnostic 规范
必须冻结：
1. 生产 dry-run 默认禁用。
2. dry-run 禁用判断先于外部权限源查询。
3. dry-run 成功/失败都写审计。
4. diagnostic 必须节流/去重。
5. internal worker API 不得暴露给普通业务角色。

### 3.8 测试矩阵
至少包含：
1. replay
2. conflict
3. active 防重
4. event_key 稳定性
5. stale claim
6. lease expired
7. cancelled aggregate
8. ERPNext draft/cancelled/docstatus missing
9. dry-run
10. diagnostic throttle
11. PostgreSQL non-skip 并发证据

### 3.9 回迁清单与实现边界
1. 输出 TASK-002~006 回迁清单。
2. 明确 TASK-009B 仅实现公共模板与最小示范接入。
3. 不强制一次性重构全部旧 outbox。
4. 旧模块仅做兼容映射，不破坏既有测试。

## 四、审计前置要求

审计官必须确认：
1. 文档只冻结规范，不写代码。
2. event_key 禁止易变字段口径明确。
3. claim 第二阶段 UPDATE 重复校验 due/lease 口径明确。
4. worker 调 ERPNext 前必须重校 aggregate。
5. dry-run/diagnostic 审计要求完整。
6. PostgreSQL non-skip 并发证据要求明确。
7. TASK-009B 边界清晰，无跨任务实现。

## 五、验收标准

- [ ] 已输出 `TASK-009_Outbox公共状态机规范.md`
- [ ] 已输出 `TASK-009A_Outbox公共状态机规范冻结_工程任务单.md`
- [ ] 现有 outbox 对比表完整
- [ ] 标准字段表完整
- [ ] 状态机图完整
- [ ] event_key 规范完整
- [ ] claim_due 规范完整
- [ ] worker 前置校验规范完整
- [ ] dry-run/diagnostic 审计规范完整
- [ ] TASK-002~006 回迁清单完整
- [ ] TASK-009B 边界完整
- [ ] 未修改业务代码
- [ ] 未修改前端/后端/.github/02_源码

## 六、执行约束

1. 不实现公共 outbox 代码。
2. 不改任何后端业务文件。
3. 不改前端。
4. 不改 migrations。
5. 不进入 TASK-010。
6. 不进入 TASK-011/012。
7. 不提交，不 push。

## 七、交付回复格式

```text
TASK-009A 执行完成。
输出文件：
1. /03_需求与设计/01_架构设计/TASK-009_Outbox公共状态机规范.md
2. /03_需求与设计/02_开发计划/TASK-009A_Outbox公共状态机规范冻结_工程任务单.md
结论：待审计
是否写业务代码：否
是否修改前端/后端/.github/02_源码：否
```
