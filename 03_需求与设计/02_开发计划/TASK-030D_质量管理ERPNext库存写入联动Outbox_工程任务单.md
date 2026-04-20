# TASK-030D 质量管理 ERPNext 库存写入联动（Outbox） 工程任务单

## 1. 基本信息

- 任务编号：TASK-030D
- 任务名称：质量管理 ERPNext 库存写入联动（Outbox）
- 角色：架构师
- 优先级：P0
- 状态：待审计
- 前置依赖：`TASK-030C` 实现审计通过（审计意见书第308份）；`TASK-012_质量管理基线设计.md` 设计冻结；`TASK-007` 权限基座（审计意见书第175份）

## 2. 任务目标

在 `TASK-030C` 已完成本地 `confirm / cancel` 状态机闭环的基础上，为质量管理补齐“确认后异步写 ERPNext Stock Entry”的受控链路：

1. `confirm` 成功后，仅在本地写入一条质量 Outbox 事件，不得同步直连 ERPNext。
2. 由独立 Worker 异步消费 Outbox，调用 ERPNext Stock Entry 写入。
3. 失败重试采用共享 Outbox 状态机约定；`max_attempts = 3`。
4. Outbox 失败不得回滚质检单 `confirmed` 状态。
5. 提供只读状态查询接口：`GET /api/quality/inspections/{inspection_id}/outbox-status`。

本任务只形成可审计工程实现边界；当前不直接放行 B 实现，不设置 `build_release_allowed=yes`。

## 3. 设计依据

1. [`TASK-012_质量管理基线设计.md`](/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-012_质量管理基线设计.md) 已将质量确认后的 ERPNext 联动定义为 fail-closed + Outbox 模式，而非同步直连。
2. `TASK-030C`（审计意见书第308份）已完成 `draft -> confirmed -> cancelled` 状态机本地闭环；本任务承接 `confirmed` 之后的异步联动。
3. 当前仓库已有可复用的 Outbox 参考实现，不是绿地新建：
   - 共享状态机：`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/outbox_state_machine.py`
   - 生产参考：`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/production.py`
   - 供应链参考：`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/subcontract.py`
   - 对账参考：`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/factory_statement_payable_outbox_service.py`
4. 当前仓库已有 ERPNext Stock Entry 写服务：`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_stock_entry_service.py`；本任务要求通过质量专用适配层封装，不允许在 `quality_service.py` 直接发起同步写入。
5. 本任务不修改前端，不开放新的用户写入口；普通前端仍停留在 `TASK-030C` 的本地状态机层。
6. 当前仓库同类 Outbox Worker 已采用统一的内部 `run-once` 安全模式，例如：
   - 外发库存同步：`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/subcontract.py`
   - 应付草稿同步：`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/factory_statement.py`
   本任务要求质量 Outbox 沿用同一模式，不允许临时发明绕开 `main.py` 动作映射或 `quality:worker` 权限门禁的旁路执行方式。

## 4. 允许范围

### 4.1 后端（FastAPI / Worker / Migration）

1. 允许新建：
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/quality_outbox.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/quality_outbox.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/quality_outbox_service.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/quality_outbox_worker.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_quality_outbox_adapter.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/versions/task_030d_create_quality_outbox.py`
2. 允许修改：
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/quality_service.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/quality.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/quality.py`（仅在需要复用响应定义时）
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/config.py`（仅新增 outbox worker 配置项时）
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/main.py`（仅为 `/api/quality/internal/outbox-sync/run-once` 增补动作映射时）
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/permission_service.py`（仅在 `quality:worker` 显式门禁或对应测试断言需要时）
3. 允许按需复用，但原则上不主动改写：
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/outbox_state_machine.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_stock_entry_service.py`

### 4.2 测试

1. 允许新增：
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_quality_outbox.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_quality_worker_permissions.py`
2. 允许按需补充：
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_quality_confirm_baseline.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_quality_api.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_permissions_registry.py`

### 4.3 控制文件 / 交付记录

1. 允许更新：
   - `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md`

## 5. 禁止范围

1. 禁止在 `confirm_inspection()` 中同步调用 ERPNext；必须先落本地 Outbox 再返回。
2. 禁止在 Outbox 失败时回滚或改写质检单 `confirmed` 状态。
3. 禁止写入 ERPNext 以外实体：`GL Entry / Payment Entry / Purchase Invoice / Delivery Note / Purchase Receipt`。
4. 禁止修改前端：
   - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/**`
5. 禁止修改 `.github/**`、`02_源码/**`、`04_生产/**`。
6. 禁止新增本地持久化 Authorization / Cookie / Token / Secret 明文。
7. 禁止绕过质量专用适配层直接从 `quality_service.py` 发 HTTP 到 ERPNext。
8. 禁止 push / remote / PR / 生产发布。
9. 禁止把 quality Worker 暴露为普通用户接口；内部执行入口必须同时满足 `quality:worker` 动作权限与内部 worker principal / service account 门禁。

## 6. 必须实现

### 6.1 Outbox 数据模型

新增质量 Outbox 事件表，沿用仓库既有 Outbox 状态机约定：`pending / processing / succeeded / failed / dead`。

最小字段集：

- `id`
- `inspection_id`
- `company`
- `event_key`
- `event_type`
- `payload_json` 或等价 payload 存储
- `payload_hash`
- `status`
- `attempts`
- `max_attempts`（固定为 `3`）
- `next_retry_at`
- `locked_by`
- `locked_at`
- `locked_until`
- `last_error_code`
- `last_error_message`
- `stock_entry_name` 或等价外部单号字段
- `created_at`
- `updated_at`
- `succeeded_at`
- `failed_at`
- `dead_at`

约束要求：

1. `event_key` 唯一，防止重复 enqueue。
2. `attempts >= 0`，`max_attempts > 0`。
3. `inspection_id + event_type` 必须能唯一指向本轮质量确认联动。

### 6.2 confirm 后 enqueue

1. `quality_service.py` 中 `confirm_inspection()` 本地状态切换成功后，立即创建一条质量 Outbox 事件：
   - `status = pending`
   - `attempts = 0`
   - `max_attempts = 3`
2. enqueue 成功后立即返回 `confirmed` 结果，不等待 ERPNext。
3. 若同一 `inspection_id` 已存在同类有效事件，不得重复创建。
4. payload 至少包含：`inspection_id / company / item_code / warehouse / accepted_qty / rejected_qty / confirmed_by / confirmed_at`。

### 6.3 Worker 与适配层

1. `quality_outbox_worker.py` 周期性消费 due 事件。
2. 消费必须通过 `quality_outbox_service.py` + 共享 `outbox_state_machine.py` 完成 claim / success / fail / dead 转移。
3. `erpnext_quality_outbox_adapter.py` 负责把质量确认结果映射为 ERPNext Stock Entry：
   - `accepted_qty` 进入质量合格仓或既定目标仓
   - `rejected_qty` 进入不合格品仓
4. 非可重试的 fail-closed 错误（如 401 / 403 / 配置缺失 / 主数据缺失）不得继续重试，应直接进入 `dead`。
5. 可重试错误采用指数退避；达到 `max_attempts = 3` 后进入 `dead`。
6. 成功后记录 `stock_entry_name`（或等价 ERPNext 单号）。
7. Worker 触发方式必须沿用现有内部 `run-once` 模式，不允许只在测试内偷偷消费 Outbox：
   - 路由：`POST /api/quality/internal/outbox-sync/run-once`
   - 允许参数：`batch_size`、`dry_run`
   - 必须通过 `quality:worker` + `require_internal_worker_principal()` 或等价 service account 校验
   - 必须在 `app/main.py` 中登记到质量模块动作映射，避免绕过统一权限入口
   - 非内部主体或无 `quality:worker` 权限时返回 `403`，且不得消费任何 Outbox 事件

### 6.4 状态查询接口

新增：`GET /api/quality/inspections/{inspection_id}/outbox-status`

返回最小字段集：

- `inspection_id`
- `status`
- `attempts`
- `max_attempts`
- `next_retry_at`
- `last_error_code`
- `last_error_message`
- `stock_entry_name`

### 6.5 边界要求

1. `TASK-030D` 不新增普通前端按钮，不新增页面，不新增前端 router 注册；质量 Worker 的内部 `run-once` 入口仅允许落在既有 `routers/quality.py` 与 `app/main.py` 动作映射内。
2. `TASK-030D` 不修改 `TASK-030C` 已通过的本地 confirm / cancel 语义。
3. `TASK-030D` 不引入与质量无关的通用 Outbox 重构；仅允许在质量链路内复用现有状态机能力。

## 7. 验收标准

1. 质检单 `confirm` 后自动生成 1 条质量 Outbox 事件，状态为 `pending`。
2. Worker 成功处理后，Outbox 状态为 `succeeded`，并记录 `stock_entry_name`。
3. 可重试错误在 3 次尝试内执行退避；超过后状态为 `dead`。
4. 非可重试 fail-closed 错误直接进入 `dead`，不反复重试。
5. Outbox 失败不影响质检单 `confirmed` 状态。
6. `GET /api/quality/inspections/{inspection_id}/outbox-status` 返回正确状态与错误信息。
7. `test_quality_outbox.py` 通过；必要时被补充的 confirm / API 测试也通过。
8. `quality_service.py` 中不存在同步 ERPNext Stock Entry 直连写调用。
9. `POST /api/quality/internal/outbox-sync/run-once` 受 `quality:worker` 与内部主体门禁保护；非 worker 主体返回 `403` 且无副作用。
10. `app/main.py` 中存在质量 Worker 的路径动作映射，不绕开统一权限路由。
11. 前端无改动，禁改目录 diff 为空。

## 8. 验证命令

```bash
cd /Users/hh/Desktop/领意服装管理系统

# 1. Outbox 文件存在
test -f 07_后端/lingyi_service/app/models/quality_outbox.py
test -f 07_后端/lingyi_service/app/services/quality_outbox_service.py
test -f 07_后端/lingyi_service/app/services/quality_outbox_worker.py
test -f 07_后端/lingyi_service/app/services/erpnext_quality_outbox_adapter.py
test -f 07_后端/lingyi_service/migrations/versions/task_030d_create_quality_outbox.py

# 2. Outbox 关键字段与状态机约定存在
rg -n 'event_key|payload_hash|status|pending|processing|succeeded|failed|dead|attempts|max_attempts|next_retry_at|stock_entry_name' \
  07_后端/lingyi_service/app/models/quality_outbox.py \
  07_后端/lingyi_service/app/services/quality_outbox_service.py

# 3. confirm 后创建 Outbox，且未在 quality_service / quality router 中同步直连 ERPNext
rg -n 'create_outbox|enqueue|event_key|quality_outbox' \
  07_后端/lingyi_service/app/services/quality_service.py
! rg -n 'requests\.(post|put|patch)|httpx\.(post|put|patch)|/api/resource/Stock%20Entry' \
  07_后端/lingyi_service/app/services/quality_service.py \
  07_后端/lingyi_service/app/routers/quality.py

# 4. quality Worker 内部 run-once 入口、main.py 映射与权限门禁存在
rg -n '@router.post\("/internal/outbox-sync/run-once"\)|require_internal_worker_principal|batch_size|dry_run' \
  07_后端/lingyi_service/app/routers/quality.py
rg -n '/internal/outbox-sync/run-once|quality:worker|QualityOutboxWorker|QUALITY_.*WORKER' \
  07_后端/lingyi_service/app/main.py \
  07_后端/lingyi_service/app/services/permission_service.py

# 5. outbox-status 路由存在
rg -n 'outbox-status|quality_outbox|stock_entry_name' \
  07_后端/lingyi_service/app/routers/quality.py \
  07_后端/lingyi_service/app/schemas/quality_outbox.py \
  07_后端/lingyi_service/app/schemas/quality.py

# 6. 测试
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest \
  tests/test_quality_outbox.py \
  tests/test_quality_worker_permissions.py \
  tests/test_quality_confirm_baseline.py \
  -q

# 7. 前端与禁改目录无越界修改
cd /Users/hh/Desktop/领意服装管理系统
git diff --name-only -- \
  06_前端/lingyi-pc/src \
  .github \
  02_源码 \
  04_生产
# 应返回空
```

## 9. 完成回报

TASK-030D 执行完成。  
结论：待审计  
confirm 后 Outbox 是否已入库：是 / 否  
Worker 是否可消费并写入 ERPNext Stock Entry：是 / 否  
失败重试与 dead 终态是否生效：是 / 否  
outbox-status 查询是否可用：是 / 否  
内部 run-once 门禁是否生效：是 / 否  
是否存在同步 ERPNext 直连写入：否  
pytest 测试结果：[通过 / 失败]

---

**C Auditor 备注（供总调度参考）：**

`TASK-030D` 是质量管理链第一次真正触碰 ERPNext 写操作的阶段，因此必须显式走 Outbox，不允许把 `confirm` 直接升级为同步 ERPNext 写入。  
本任务通过后，质量链路的本地状态机与异步库存联动才算闭合；统计增强（`TASK-030E`）与导出增强（`TASK-030F`）仍属于读侧扩展，可在其后继续推进。
