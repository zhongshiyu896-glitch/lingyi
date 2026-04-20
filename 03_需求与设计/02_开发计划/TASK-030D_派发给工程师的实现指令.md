# TASK-030D 派发给工程师的实现指令

## 1. 派发信息

- 任务编号：TASK-030D
- 任务名称：质量管理 ERPNext 库存写入联动（Outbox）
- 派发角色：A Technical Architect
- 执行角色：B Engineer
- 派发时间：2026-04-19 19:52 CST+8
- 依据任务单：`/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-030D_质量管理ERPNext库存写入联动Outbox_工程任务单.md`
- 审计依据：
  - `TASK-030D` 任务单复核通过（审计意见书第310份）
  - `TASK-030C` 实现审计通过（审计意见书第308份）
  - `TASK-030B` 实现审计通过（审计意见书第301份）
  - `TASK-030A` 实现审计通过（审计意见书第299份）
  - `TASK-012_质量管理基线设计.md` 设计冻结
  - `TASK-007` 权限与审计基座（审计意见书第175份）
- 当前门禁：`build_release_allowed=yes`，可进入实现；仍禁止 push / remote / PR / 生产发布

## 2. 派发目标

基于当前已完成的质量链本地状态机，补齐 `confirmed -> 本地 Outbox -> ERPNext Stock Entry` 的异步闭环。

本轮必须完成五件事：

1. 质检单 `confirm` 成功后，写入本地质量 Outbox 事件，不得同步直连 ERPNext。
2. 补齐质量 Outbox 模型、服务、Worker、质量专用 ERPNext 写适配层与 migration。
3. 新增 `POST /api/quality/internal/outbox-sync/run-once`，沿用现有内部 worker `run-once` 模式。
4. 新增 `GET /api/quality/inspections/{inspection_id}/outbox-status`，返回只读状态。
5. 补齐 outbox / worker 权限测试，确保 `quality:worker` 与内部主体门禁成立。

## 3. 继承基线

以下文件属于 `TASK-030A / TASK-030B / TASK-030C` 已通过审计但尚未封版的继承工作树基线。B 必须在其上继续实现，不得回退这些改动，也不得把它们误报为“本轮新增”：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/quality.py`
  - SHA-256：`3679c8ff41d0ab0c7f622ae77d467b2c81aafa6a41f39b9d54b5f794b9b903df`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/quality.py`
  - SHA-256：`38025cc0b16e81332c2ceccb9ad303050d3f3512cdb0ebe839f38030fc43ff1e`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/quality.py`
  - SHA-256：`11b261da50f18a48709e455d439cfc1e3b505f2e76a8a2395bf69ad5c59277f2`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/quality_service.py`
  - SHA-256：`a1767af629cd242dfa170826a1c1d38afe64e95fa36d1ffff3ae6de5e01cbf9a`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/quality.ts`
  - SHA-256：`d606500cb1fe76c51ada5334eb92f6c9082aaf0334d4efe57c144d11c4ca52f9`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/quality/QualityInspectionDetail.vue`
  - SHA-256：`2a8c1873e01337c1a1eb8f09f9efaf621ee9bb570f0a12ecf7414d206b443f43`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_quality_api.py`
  - SHA-256：`9191dd91b2a2b20a9d79f185602dcb632cba832cd56db5e27517b634c50467aa`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_quality_create_baseline.py`
  - SHA-256：`dffb6ed3893470e5a1c7296da142ae2b21f35af658f6f2211a37d94ac74a1e15`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_quality_update_baseline.py`
  - SHA-256：`87ea8f115be4a486abe03ff2cefbadb0f5d2599ffebcba6c89be7dcf014ba2ee`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_quality_defect_baseline.py`
  - SHA-256：`f2759cb71d89e9c06e883538abaf46deb0b451af9e9a2aa96a886b5ed6a0808b`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_quality_confirm_baseline.py`
  - SHA-256：`c7b79c9d729a1b36555c9adb0ee70791ddc2d1722f2b41ebe2540e0858d4fff5`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_quality_cancel_baseline.py`
  - SHA-256：`0beed0f44cb2594ecb295819ce42286aff6b91544f37926dd3b4faec9cfd5bda`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/versions/task_030c_add_quality_cancel_reason.py`
  - SHA-256：`fc64681a3cee6b7f1210000128f061b6cfb00454541f71ae1808422d32b607bf`

开始前必须核对上述哈希；只要任一不一致，或允许范围内出现来源不明脏文件，立即 `BLOCKED`，不要继续实现。

## 4. 实现范围

### 4.1 允许修改 / 新建的文件

1. 后端新建：
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/quality_outbox.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/quality_outbox.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/quality_outbox_service.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/quality_outbox_worker.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_quality_outbox_adapter.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/versions/task_030d_create_quality_outbox.py`
2. 后端允许修改：
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/quality_service.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/quality.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/quality.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/main.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/config.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/permission_service.py`
3. 测试：
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_quality_outbox.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_quality_worker_permissions.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_quality_confirm_baseline.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_quality_api.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_permissions_registry.py`
4. 交付记录：
   - `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md`

### 4.2 必须实现的功能

1. `confirm_inspection()` 成功后仅 enqueue 本地 Outbox：
   - 事件状态初始为 `pending`
   - `attempts = 0`
   - `max_attempts = 3`
   - 同一 `inspection_id + event_type` 不得重复创建有效事件
2. 质量 Outbox 数据模型：
   - 至少包含 `inspection_id / company / event_key / event_type / payload_json or payload / payload_hash / status / attempts / max_attempts / next_retry_at / locked_by / locked_at / locked_until / last_error_code / last_error_message / stock_entry_name / created_at / updated_at / succeeded_at / failed_at / dead_at`
3. 质量 Worker：
   - `POST /api/quality/internal/outbox-sync/run-once`
   - 支持 `batch_size`、`dry_run`
   - 必须要求 `quality:worker`
   - 必须要求内部 worker principal / service account
   - 非法主体返回 403 且不消费 Outbox
4. 质量 ERPNext 写适配层：
   - 只能写 `Stock Entry`
   - `accepted_qty` / `rejected_qty` 按任务单口径映射目标仓
   - 非可重试 fail-closed 错误直接 `dead`
   - 可重试错误最多 3 次后 `dead`
5. 只读状态查询：
   - `GET /api/quality/inspections/{inspection_id}/outbox-status`
   - 返回 `inspection_id / status / attempts / max_attempts / next_retry_at / last_error_code / last_error_message / stock_entry_name`

## 5. 当前代码锚点

当前仓库不是绿地新建，必须沿用以下既有骨架继续实现：

- 质量确认路由已存在：
  - `quality.py:649`
- 质量确认服务已存在：
  - `quality_service.py:204`
- 质量服务当前仍保留只读来源校验：
  - `quality_service.py:99`
  - `quality_service.py:102`
- 同类内部 Worker `run-once` 参考：
  - `subcontract.py:1196`
  - `factory_statement.py:771`
- 统一路径动作映射参考：
  - `main.py:300`
  - `main.py:336`
- 质量 worker 动作权限锚点已存在：
  - `permission_service.py:1876`
- 共享 Outbox 状态机参考：
  - `outbox_state_machine.py`
- ERPNext Stock Entry 写服务参考：
  - `erpnext_stock_entry_service.py`

## 6. 严禁范围

1. 禁止在 `quality_service.py` 或 `routers/quality.py` 中同步直连 ERPNext。
2. 禁止在 Outbox 失败时回滚质检单 `confirmed` 状态。
3. 禁止写入 ERPNext 以外实体：`GL Entry / Payment Entry / Purchase Invoice / Delivery Note / Purchase Receipt`。
4. 禁止修改前端任意文件：
   - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/**`
5. 禁止改写历史迁移：
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/versions/task_030c_add_quality_cancel_reason.py`
6. 禁止主动改写以下共享参考实现；若发现必须改它们才能完成任务，立即 `BLOCKED`：
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/outbox_state_machine.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_stock_entry_service.py`
7. 禁止修改：
   - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/router/**`
   - `/Users/hh/Desktop/领意服装管理系统/.github/**`
   - `/Users/hh/Desktop/领意服装管理系统/02_源码/**`
   - `/Users/hh/Desktop/领意服装管理系统/04_生产/**`
8. 禁止新增本地持久化 Authorization / Cookie / Token / Secret 明文。
9. 禁止 push / remote / PR / 生产发布。

## 7. 开始前必须完成的前置检查

1. 通读以下文件：
   - `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-030D_质量管理ERPNext库存写入联动Outbox_工程任务单.md`
   - `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-012_质量管理基线设计.md`
2. 核对审计日志：
   - `TASK-030D` 任务单复核通过（第310份）
   - `TASK-030C` 实现审计通过（第308份）
3. 运行以下命令并核对继承基线：
   - `git -C /Users/hh/Desktop/领意服装管理系统 status --short -- '07_后端/lingyi_service/app/models/quality.py' '07_后端/lingyi_service/app/routers/quality.py' '07_后端/lingyi_service/app/schemas/quality.py' '07_后端/lingyi_service/app/services/quality_service.py' '06_前端/lingyi-pc/src/api/quality.ts' '06_前端/lingyi-pc/src/views/quality/QualityInspectionDetail.vue' '07_后端/lingyi_service/tests/test_quality_api.py' '07_后端/lingyi_service/tests/test_quality_create_baseline.py' '07_后端/lingyi_service/tests/test_quality_update_baseline.py' '07_后端/lingyi_service/tests/test_quality_defect_baseline.py' '07_后端/lingyi_service/tests/test_quality_confirm_baseline.py' '07_后端/lingyi_service/tests/test_quality_cancel_baseline.py' '07_后端/lingyi_service/migrations/versions/task_030c_add_quality_cancel_reason.py'`
   - `shasum -a 256 <上述文件>`
4. 只要发现允许范围内已有无法解释来源的脏改动，立即 `BLOCKED`。

## 8. 必跑验证命令

```bash
cd /Users/hh/Desktop/领意服装管理系统

# 1. 继承基线保持不漂移
shasum -a 256 \
  /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/quality.py \
  /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/quality.py \
  /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/quality.py \
  /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/quality_service.py \
  /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/quality.ts \
  /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/quality/QualityInspectionDetail.vue \
  /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_quality_api.py \
  /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_quality_create_baseline.py \
  /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_quality_update_baseline.py \
  /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_quality_defect_baseline.py \
  /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_quality_confirm_baseline.py \
  /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_quality_cancel_baseline.py \
  /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/versions/task_030c_add_quality_cancel_reason.py

# 2. Outbox 文件存在
test -f 07_后端/lingyi_service/app/models/quality_outbox.py
test -f 07_后端/lingyi_service/app/services/quality_outbox_service.py
test -f 07_后端/lingyi_service/app/services/quality_outbox_worker.py
test -f 07_后端/lingyi_service/app/services/erpnext_quality_outbox_adapter.py
test -f 07_后端/lingyi_service/migrations/versions/task_030d_create_quality_outbox.py

# 3. Outbox 关键字段与状态机约定存在
rg -n 'event_key|payload_hash|status|pending|processing|succeeded|failed|dead|attempts|max_attempts|next_retry_at|stock_entry_name' \
  07_后端/lingyi_service/app/models/quality_outbox.py \
  07_后端/lingyi_service/app/services/quality_outbox_service.py

# 4. confirm 后创建 Outbox，且未在 quality_service / quality router 中同步直连 ERPNext
rg -n 'create_outbox|enqueue|event_key|quality_outbox' \
  07_后端/lingyi_service/app/services/quality_service.py
! rg -n 'requests\.(post|put|patch)|httpx\.(post|put|patch)|/api/resource/Stock%20Entry' \
  07_后端/lingyi_service/app/services/quality_service.py \
  07_后端/lingyi_service/app/routers/quality.py

# 5. quality Worker 内部 run-once 入口、main.py 映射与权限门禁存在
rg -n '@router.post\("/internal/outbox-sync/run-once"\)|require_internal_worker_principal|batch_size|dry_run' \
  07_后端/lingyi_service/app/routers/quality.py
rg -n '/internal/outbox-sync/run-once|quality:worker|QualityOutboxWorker|QUALITY_.*WORKER' \
  07_后端/lingyi_service/app/main.py \
  07_后端/lingyi_service/app/services/permission_service.py

# 6. outbox-status 路由存在
rg -n 'outbox-status|quality_outbox|stock_entry_name' \
  07_后端/lingyi_service/app/routers/quality.py \
  07_后端/lingyi_service/app/schemas/quality_outbox.py \
  07_后端/lingyi_service/app/schemas/quality.py

# 7. 测试
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest \
  tests/test_quality_outbox.py \
  tests/test_quality_worker_permissions.py \
  tests/test_quality_confirm_baseline.py \
  -q

# 8. 前端与禁改目录无越界修改
cd /Users/hh/Desktop/领意服装管理系统
git diff --name-only -- \
  06_前端/lingyi-pc/src \
  .github \
  02_源码 \
  04_生产
# 应返回空
```

## 9. 交付回报模板

```text
STATUS: HANDOFF / NEEDS_FIX / BLOCKED
TASK_ID: TASK-030D
ROLE: B

CHANGED_FILES:
- 绝对路径 1
- 绝对路径 2

EVIDENCE:
- confirm 后如何 enqueue 质量 Outbox
- quality Worker 如何通过 internal run-once + quality:worker + 内部主体门禁执行
- 如何保证非可重试错误直接 dead，可重试错误最多 3 次后 dead
- outbox-status 如何返回当前状态
- 为什么不存在同步 ERPNext 直连写入

VERIFICATION:
- 命令 1：通过 / 失败（附简要结果）
- 命令 2：通过 / 失败（附简要结果）
- 命令 3：通过 / 失败（附简要结果）
- 命令 4：通过 / 失败（附简要结果）
- 命令 5：通过 / 失败（附简要结果）
- 命令 6：通过 / 失败（附简要结果）
- 命令 7：通过 / 失败（附简要结果）
- 命令 8：通过 / 失败（附简要结果）

BLOCKERS:
- 无 / 具体阻塞

NEXT_ROLE: C Auditor
```
