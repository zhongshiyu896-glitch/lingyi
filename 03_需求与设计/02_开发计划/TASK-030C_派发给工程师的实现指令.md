# TASK-030C 派发给工程师的实现指令

## 1. 派发信息

- 任务编号：TASK-030C
- 任务名称：质检单确认 / 取消状态机重启
- 派发角色：A Technical Architect
- 执行角色：B Engineer
- 派发时间：2026-04-19 17:38 CST+8
- 修订时间：2026-04-19 18:31 CST+8
- 基线刷新时间：2026-04-19 18:39 CST+8
- 本轮重排时间：2026-04-19 18:57 CST+8
- 哈希二次刷新时间：2026-04-19 19:12 CST+8
- Fix pass：`2`（依据 C 审计意见书第306份；第1次 fix pass 已补齐代码落点，但真实库 migration 仍缺口）
- 依据任务单：`/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-030C_质检单确认取消状态机重启_工程任务单.md`
- 审计依据：
  - `TASK-030C` 任务单复核通过（审计意见书第303份）
  - `TASK-030B` 实现审计通过（审计意见书第301份）
  - `TASK-030A` 实现审计通过（审计意见书第299份）
  - `TASK-012_质量管理基线设计.md` 设计冻结
  - `TASK-007` 权限与审计基座（审计意见书第175份）
- 当前门禁：`build_release_allowed=yes`，可进入实现；仍禁止 push / remote / PR / 生产发布

## 1.1 第306份修复结论

C 第306份实现审计确认：第304份指出的代码级问题已经补齐，`cancel_reason` 现已进入实体、详情返回、服务映射与测试断言。

当前唯一剩余缺口是“真实库 migration 未补齐”：

1. 仓库已启用 `alembic`，但 `cancel_reason` 尚未进入任何质量模块 migration。
2. 当前测试使用 `metadata.create_all`，只能证明测试库新建表可用，不能证明真实迁移库已有该列。
3. 因此本轮 fix pass 只允许补一件事：新增 additive migration，把 `cancel_reason` 正式补进 `ly_quality_inspection`。
4. 不下调验收口径，不得把“测试库可用”冒充为“真实迁移库可用”。

## 1.2 第305份阻塞收敛说明

C 第305份阻塞并非新的实现问题，而是派发指令第 3 节登记的继承基线哈希已经落后于当前真实工作树。

本轮 A 只做一件事：

1. 将第 3 节 10 个继承基线哈希刷新为当前真实工作树真值。

该动作不新增产品范围，不改变 fix pass 目标，也不额外消耗新的 fix pass 次数。

## 1.3 第307份阻塞收敛说明

C 第307份阻塞不指向新的产品缺陷，而是 fix pass 2 的派发指令第 3 节仍残留 3 个旧哈希值，导致“当前真实工作树”与“派发门禁”不一致：

1. `quality_service.py`
2. `schemas/quality.py`
3. `models/quality.py`

A 已重新核对当前真实工作树，并将上述 3 个继承基线哈希刷新为最新真值。

从本次收敛开始，`TASK-030C` 的 migration-only 交付闭环应以“当前真实工作树 + 已新增 migration 文件”为审计基准；本轮不再要求 B 新增代码改动，下一步直接回交 C 做最终闭环裁决。

## 2. 派发目标

基于当前已完成的 `TASK-030C` 代码落点，本轮只做 migration 收口，不再重复改业务逻辑。

本轮必须完成三件事：

1. 新增 `task_030c_add_quality_cancel_reason.py`，把 `cancel_reason` 正式补入真实库 schema。
2. 确保该 migration 以 `task_012b_create_quality_tables` 为 `down_revision`，并采用 additive 方式加列。
3. 保持现有代码 / 测试落点不漂移，不得回退已通过的 `cancel_reason` 实体、详情返回与测试断言。

当前说明：

- B 本轮实现已完成。
- A 本轮只收敛哈希门禁与共享控制面。
- 本次回交目标是 `C Auditor` 的最终闭环复核，不再新增 B 侧开发动作。

## 3. 继承基线

以下文件属于 `TASK-030A / TASK-030B` 已通过审计但尚未封版的继承工作树基线，B 必须在其上继续实现，不得把这些已审计改动误回退，也不得把其来源描述成“本轮新增”：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/quality.py`
  - SHA-256：`38025cc0b16e81332c2ceccb9ad303050d3f3512cdb0ebe839f38030fc43ff1e`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/quality_service.py`
  - SHA-256：`a1767af629cd242dfa170826a1c1d38afe64e95fa36d1ffff3ae6de5e01cbf9a`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/quality.py`
  - SHA-256：`11b261da50f18a48709e455d439cfc1e3b505f2e76a8a2395bf69ad5c59277f2`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/quality.py`
  - SHA-256：`3679c8ff41d0ab0c7f622ae77d467b2c81aafa6a41f39b9d54b5f794b9b903df`
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

开始前必须先验证上述哈希；只要任一文件哈希不一致，或允许范围内出现额外来源不明脏文件，立即 `BLOCKED`，不要继续实现。

## 4. 实现范围

### 4.1 允许修改的文件

1. 后端：
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/versions/task_030c_add_quality_cancel_reason.py`
2. 交付记录：
   - `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md`

### 4.2 必须实现的功能

1. 新增 additive migration：
   - 文件名：`task_030c_add_quality_cancel_reason.py`
   - `revision` 使用新值
   - `down_revision = "task_012b_create_quality_tables"`
   - `upgrade()` 为 `ly_schema.ly_quality_inspection` 增加可空列 `cancel_reason`
   - `downgrade()` 删除该列
2. 保持既有代码落点不漂移：
   - `LyQualityInspection.cancel_reason` 保持存在
   - 取消成功返回与详情返回中的 `cancel_reason` 保持存在
   - `test_quality_cancel_baseline.py` 中对响应 / 实体 / 详情 / 日志 `remark` 的断言保持存在
3. 不改写历史迁移：
   - 严禁直接编辑 `task_012b_create_quality_tables.py`
   - 若发现本地链头并非 `task_012b_create_quality_tables`，立即 `BLOCKED` 回报，不得自作主张改写 `down_revision`

## 5. 当前代码锚点

当前仓库不是绿地新建，必须在以下既有骨架上继续实现：

- 路由锚点：
  - `quality.py:503`
  - `quality.py:522`
- 服务锚点：
  - `quality_service.py:204`
  - `quality_service.py:239`
- 当前缺口：
  - 代码级 `cancel_reason` 缺口已由 fix pass 1 补齐
  - 当前剩余唯一缺口是：`migrations/versions` 中仍无 `cancel_reason` 对应 migration
- `TASK-030B` 已通过的 draft 基线：
  - `quality.ts:223/230/237`
  - `QualityInspectionDetail.vue` 已有编辑草稿 / 缺陷录入入口
  - 三份基线测试已存在

## 6. 严禁范围

1. 禁止把 `cancel` 放宽到 `draft -> cancelled`。
2. 禁止实现 ERPNext Stock Entry / Purchase Receipt / Delivery Note 写入。
3. 禁止引入 outbox、自动扣款结算、自动返工工单、自动报废入账。
4. 禁止修改 `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/router/**`。
5. 禁止新增 localStorage 敏感凭据读取或持久化。
6. 禁止越界修改 `.github/**`、`02_源码/**`、`04_生产/**`。
7. 禁止 push / remote / PR / 生产发布。
8. 禁止直接改写历史迁移 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/versions/task_012b_create_quality_tables.py`。
9. 若本地 Alembic 链头与当前派发要求不一致，必须先 `BLOCKED`，不得自行扩大范围。

## 7. 开始前必须完成的前置检查

1. 通读以下文件：
   - `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-030C_质检单确认取消状态机重启_工程任务单.md`
   - `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-012_质量管理基线设计.md`
2. 核对审计日志：
   - `TASK-030B` 实现审计通过（第301份）
   - `TASK-030C` 任务单复核通过（第303份）
3. 运行以下命令并核对哈希：
   - `git -C /Users/hh/Desktop/领意服装管理系统 status --short -- '07_后端/lingyi_service/app/routers/quality.py' '07_后端/lingyi_service/app/services/quality_service.py' '07_后端/lingyi_service/app/schemas/quality.py' '07_后端/lingyi_service/app/models/quality.py' '06_前端/lingyi-pc/src/api/quality.ts' '06_前端/lingyi-pc/src/views/quality/QualityInspectionDetail.vue' '07_后端/lingyi_service/tests/test_quality_api.py' '07_后端/lingyi_service/tests/test_quality_create_baseline.py' '07_后端/lingyi_service/tests/test_quality_update_baseline.py' '07_后端/lingyi_service/tests/test_quality_defect_baseline.py'`
   - `shasum -a 256 <上述文件>`
4. 确认 migration 链头：
   - `rg -n '^revision\\s*=|^down_revision\\s*=' /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/versions`
   - 当前派发口径要求新 migration 接在 `task_012b_create_quality_tables`
5. 只要发现允许范围内已有无法解释来源的脏改动，立即 `BLOCKED`。

## 8. 必跑验证命令

```bash
cd /Users/hh/Desktop/领意服装管理系统

# 1. 继承基线保持不漂移
shasum -a 256 \
  /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/quality.py \
  /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/quality_service.py \
  /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/quality.py \
  /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/quality.py \
  /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/quality.ts \
  /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/quality/QualityInspectionDetail.vue \
  /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_quality_api.py \
  /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_quality_create_baseline.py \
  /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_quality_update_baseline.py \
  /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_quality_defect_baseline.py

# 2. 新 migration 存在且接在 task_012b_create_quality_tables
test -f /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/versions/task_030c_add_quality_cancel_reason.py
rg -n 'revision|down_revision|cancel_reason|add_column|drop_column|task_012b_create_quality_tables' \
  /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/versions/task_030c_add_quality_cancel_reason.py

# 3. 历史迁移未被改写
git -C /Users/hh/Desktop/领意服装管理系统 diff --name-only -- \
  07_后端/lingyi_service/migrations/versions/task_012b_create_quality_tables.py
# 应返回空

# 4. 代码级 cancel_reason 修复仍保持存在
rg -n 'cancel_reason' \
  /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/quality.py \
  /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/quality.py \
  /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/quality_service.py \
  /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_quality_cancel_baseline.py

# 5. 后端测试
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest \
  tests/test_quality_confirm_baseline.py \
  tests/test_quality_cancel_baseline.py \
  tests/test_quality_update_baseline.py \
  -q

# 6. 详情返回包含 cancel_reason（如测试里已有详情查询可复用）
rg -n 'cancel_reason' \
  /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_quality_cancel_baseline.py

# 7. 前端 typecheck
cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc
npm run typecheck

# 8. 越界检查
git -C /Users/hh/Desktop/领意服装管理系统 diff --name-only -- \
  '06_前端/lingyi-pc/src/router' '.github' '02_源码' '04_生产'
# 应返回空
```

## 9. 交付回报模板

```text
STATUS: HANDOFF / NEEDS_FIX / BLOCKED
TASK_ID: TASK-030C
ROLE: B

CHANGED_FILES:
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/versions/task_030c_add_quality_cancel_reason.py
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md

EVIDENCE:
- 新 migration 如何接在 `task_012b_create_quality_tables`
- migration 如何为 `ly_quality_inspection` 增加 `cancel_reason`
- 历史迁移为何未被改写
- 既有 `cancel_reason` 代码落点为何保持不漂移
- 继承基线是否保持不漂移

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
