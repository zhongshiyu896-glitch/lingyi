# TASK-030G 来料检验自动触发 工程任务单

## 1. 基本信息
- 任务编号：`TASK-030G`
- 任务名称：来料检验自动触发
- 角色：`B Engineer`
- 优先级：`P2`
- 状态：`待执行（已放行）`
- 前置依赖：`TASK-030D` 审计通过（审计意见书第363份）；`TASK-030F` 审计通过（审计意见书第366份）；质量管理 create / confirm / outbox 链路已完成；Sprint 4 包内登记方向已满足激活条件

## 2. 任务目标
在 ERPNext 产生 `Purchase Receipt` 已提交事件后，自动在本地质量管理模块创建草稿质检单：

1. 接收或处理 `purchase_receipt_created` / `purchase_receipt_submitted` 事件。
2. 基于事件中的 `Purchase Receipt` 编号、公司、供应商、物料、数量、仓库生成 `draft` 状态质检单。
3. 只自动创建草稿，不自动 `confirm`，不自动 `cancel`。
4. 基于 `source_type="incoming_material"` + `source_id=<Purchase Receipt>` 去重，同一收货单不得重复创建质检单。
5. 自动创建必须复用质量服务层创建逻辑，不得绕过 FastAPI/Service 既有业务校验直接插入业务表。

## 3. 设计依据
1. `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-012_质量管理基线设计.md`
2. `TASK-030B`：质检单创建与草稿写入口已通过。
3. `TASK-030C`：质检单状态机已通过。
4. `TASK-030D`：质量 Outbox 已通过，本任务不得新增 ERPNext 写入。
5. `PKG-030-040-V1`：`TASK-030G` 登记方向为 `Purchase Receipt` 触发草稿质检单自动创建，约束为只创建 `draft`。

## 4. 允许范围
### 4.1 后端
允许新增：
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/quality_purchase_receipt_listener.py`

允许修改：
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/quality_service.py`（仅允许补充复用型去重/草稿创建辅助方法；不得改变现有确认、取消、outbox 语义）
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/quality.py`（仅当事件输入 schema 必需时）

### 4.2 测试
允许新增：
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_quality_auto_trigger.py`

允许修改：
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_quality_models.py`（仅允许补充与来料触发复用校验相关断言）

### 4.3 日志
允许修改：
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md`

## 5. 禁止范围
1. 禁止新增或修改前端文件。
2. 禁止新增或修改 FastAPI router。
3. 禁止修改 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/main.py`。
4. 禁止新增 migration。
5. 禁止新增 outbox、worker 注册、定时任务或后台调度入口。
6. 禁止自动确认质检单。
7. 禁止自动取消质检单。
8. 禁止 ERPNext 写调用，包括 `Stock Entry`、`Purchase Receipt`、`Delivery Note`、`GL Entry`、`Payment`、`Purchase Invoice` 写入。
9. 禁止直接绕过 `QualityService.create_inspection()` 语义向 `LyQualityInspection` / `LyQualityInspectionItem` 插入业务草稿。
10. 禁止修改 `.github/**`、`02_源码/**`、`04_生产/**`。
11. 禁止 push / remote / PR。

## 6. 必须实现
### 6.1 监听服务
新增 `quality_purchase_receipt_listener.py`，至少提供一个可被测试直接调用的处理入口，例如：

- `handle_purchase_receipt_event(session, event, actor=...)`
- 或 `QualityPurchaseReceiptListener.handle_event(event)`

事件输入至少支持以下字段：
- `event_type`：`purchase_receipt_created` 或 `purchase_receipt_submitted`
- `purchase_receipt_id` / `name`：ERPNext `Purchase Receipt` 编号
- `company`
- `supplier`
- `warehouse`
- `items`：明细数组，每行含 `item_code`、`qty`，可选 `item_name`、`warehouse`

### 6.2 草稿创建规则
1. `source_type` 固定为 `incoming_material`。
2. `source_id` 固定为 `Purchase Receipt` 编号。
3. 创建后的质检单状态必须为 `draft`。
4. 质检单明细行数量来自 `items[].qty`。
5. 草稿初始数量必须满足既有数量平衡规则：`inspected_qty = accepted_qty + rejected_qty`。
6. 默认初始值：`accepted_qty = inspected_qty`，`rejected_qty = 0`，除非现有质量服务已有更严格口径。
7. 自动草稿必须保留 `company`、`supplier`、`warehouse`、`item_code` 等来源字段。
8. 不得生成缺陷记录。
9. 不得触发 `confirm_inspection()`。
10. 不得生成质量 outbox 事件。

### 6.3 去重规则
1. 对同一 `company + source_type=incoming_material + source_id`，如果已存在非 `cancelled` 质检单，直接返回既有记录，不再创建新记录。
2. 重复事件必须幂等。
3. 如果既有记录为 `confirmed`，仍不得新建第二张草稿。
4. 如果既有记录为 `cancelled`，是否允许重新创建由现有业务规则决定；如实现不确定，必须 fail closed 并在回报中说明。

### 6.4 失败处理
1. 缺少 `purchase_receipt_id/name`、`company`、`supplier`、`items` 时 fail closed，不落库。
2. `items` 为空时 fail closed，不落库。
3. `qty <= 0` 时 fail closed，不落库。
4. 主数据校验失败时沿用 `QualityService.create_inspection()` 的异常语义，不吞错伪造成功。
5. ERPNext 不可达或来源校验不可达时不得绕过校验创建草稿。

## 7. 验收标准
1. `Purchase Receipt` 事件到达后自动生成一张 `draft` 质检单。
2. 自动生成的质检单 `source_type=incoming_material`，`source_id=<Purchase Receipt>`。
3. 自动生成的质检单明细行与事件 `items` 对应。
4. 同一 `Purchase Receipt` 重复事件不重复创建质检单。
5. 自动创建不会触发 `confirmed` 状态。
6. 自动创建不会生成质量 outbox 事件。
7. 无 ERPNext 写操作。
8. 无前端改动、无 router 改动、无 migration 改动。
9. `test_quality_auto_trigger.py` 通过。
10. 既有质量模型/创建路径测试不回归。

## 8. 必跑验证
```bash
cd /Users/hh/Desktop/领意服装管理系统

# 1. 监听服务存在
test -f 07_后端/lingyi_service/app/services/quality_purchase_receipt_listener.py

# 2. 自动触发核心语义存在
rg -n 'Purchase Receipt|purchase_receipt|incoming_material|source_id|create_inspection|draft' \
  07_后端/lingyi_service/app/services/quality_purchase_receipt_listener.py \
  07_后端/lingyi_service/app/services/quality_service.py

# 3. 去重逻辑存在
rg -n 'dedup|duplicate|existing|source_type.*source_id|source_id.*source_type' \
  07_后端/lingyi_service/app/services/quality_purchase_receipt_listener.py \
  07_后端/lingyi_service/app/services/quality_service.py

# 4. 禁止自动确认/取消/outbox
! rg -n 'confirm_inspection|cancel_inspection|LyQualityOutboxEvent|enqueue_quality_outbox|outbox' \
  07_后端/lingyi_service/app/services/quality_purchase_receipt_listener.py

# 5. 禁止 ERPNext 写调用
! rg -n 'requests\.(post|put|patch|delete)|httpx\.(post|put|patch|delete)|/api/resource/Stock Entry|/api/resource/Purchase Receipt|/api/resource/Delivery Note' \
  07_后端/lingyi_service/app/services/quality_purchase_receipt_listener.py \
  07_后端/lingyi_service/app/services/quality_service.py

# 6. 后端测试
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest \
  tests/test_quality_auto_trigger.py \
  tests/test_quality_models.py \
  -v --tb=short

# 7. 禁改目录与禁改层检查
cd /Users/hh/Desktop/领意服装管理系统
git diff --name-only -- \
  06_前端/lingyi-pc/src \
  07_后端/lingyi_service/app/routers \
  07_后端/lingyi_service/app/main.py \
  07_后端/lingyi_service/migrations \
  .github 02_源码 04_生产
# 预期为空；若存在继承脏基线，必须在回报中逐项说明哈希未变且非本轮新增
```

## 9. 完成回报
完成后仅按以下格式回交，不要回任务单正文：

```md
STATUS: READY_FOR_AUDIT
TASK_ID: TASK-030G
CONTEXT_VERSION: 未提供
ROLE: B

CHANGED_FILES:
- 绝对路径1
- 绝对路径2

EVIDENCE:
- Purchase Receipt 事件处理入口：
- 自动创建 draft 质检单证据：
- source_type/source_id 证据：
- 去重幂等证据：
- 未自动 confirm/cancel 证据：
- 未生成 outbox 证据：
- 无 ERPNext 写操作证据：

VERIFICATION:
- pytest：
- 禁止自动确认/取消/outbox 扫描：
- ERPNext 写调用扫描：
- 禁改目录 diff：

RISKS:
- 无 / 具体残余风险

NEXT_ROLE: C Auditor
```
