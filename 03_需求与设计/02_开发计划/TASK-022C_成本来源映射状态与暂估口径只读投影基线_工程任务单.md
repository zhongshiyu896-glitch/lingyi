# TASK-022C 成本来源映射状态与暂估口径只读投影基线 工程任务单

## 1. 基本信息

- 任务编号：TASK-022C
- 任务名称：成本来源映射状态与暂估口径只读投影基线
- 角色：架构师
- 优先级：P1
- 状态：待审计
- 前置依赖：TASK-022A 审计通过（审计意见书第 214 份）；TASK-022B 任务单复核通过（审计意见书第 236 份）

## 2. 任务目标

基于 `TASK-022A` 已冻结的成本核算边界，以及 `TASK-022B` 已收口的“本地成本快照计算 + 只读列表 / 详情 / 来源映射基线”，输出成本核算实现链路第二张任务单，范围限定为“来源映射状态、暂估口径（provisional）与分摊状态（allocation_status）的只读投影收口”：

1. 在现有 `style_profit` 快照读侧基础上，补齐 `include_provisional_subcontract` 与 `allocation_status` 的 API / 前端只读投影。
2. 让现有来源映射中的 `source_status`、`mapping_status`、`include_in_profit`、`unresolved_reason`、`posting_date`、`warehouse` 在前端读侧可审计、可辨识，不得静默隐藏。
3. 明确 `provisional / settled / excluded / unresolved` 只能作为只读展示与审计线索，不得升级为财务写入事实。
4. 本任务只形成可审计工程任务边界；在 `build_release_allowed=no` 条件下，不直接放行 B 实现。

## 2.1 当前门禁状态

1. `TASK-022A` 已于审计意见书第 214 份通过，允许进入成本核算实现任务拆分。
2. `TASK-022B` 已于审计意见书第 236 份通过，成本快照创建、列表、详情和来源映射基线已形成正式任务单边界。
3. `TASK-021B` 的第 233 份仅为历史状态对账阻塞，已收敛，不构成当前成本链路前置门禁。
4. 当前 `build_release_allowed=no`，本任务仍需先交 C 复核边界、验收标准、允许 / 禁止范围；C 未 PASS 前不得进入 B 实现。
5. 即使 `TASK-022C` 任务单通过，也只表示读侧门禁定义完成；除非后续 Context Pack 明确 `build_release_allowed=yes`，否则仍不得放行 B。

## 2.2 已确认的现状基础

当前仓库中与 `TASK-022C` 直接相关的真实代码锚点已经存在，不得按“从零新增成本模块”口径重复立项：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/style_profit.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/style_profit_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/style_profit_source_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/style_profit.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/style_profit.py`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/style_profit.ts`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/style_profit/StyleProfitSnapshotList.vue`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/style_profit/StyleProfitSnapshotDetail.vue`

已核实的当前实现现状：

1. `LyStyleProfitSnapshot` 模型已存在 `allocation_status` 与 `include_provisional_subcontract` 字段，默认值分别为 `not_enabled` 与 `false`。
2. `StyleProfitSnapshotCreateRequest` 与 `StyleProfitSnapshotSelectorRequest` 已接收 `include_provisional_subcontract`，`style_profit_service.py` 在创建快照时也已写入该字段。
3. `style_profit_source_service.py` 已对来源映射区分 `mapped / unresolved / excluded`，并维护 `include_in_profit` 与 `unresolved_reason`。
4. `style_profit_service.py` 已在外发成本处理链路中区分 `provisional` 与 `settled`，并将诊断信息写入 `raw_ref`。
5. 前端详情页当前已展示 `mapping_status / include_in_profit / unresolved_reason`，但尚未把 `source_status / posting_date / warehouse` 以及快照级的 `allocation_status / include_provisional_subcontract` 明确投影到读侧界面。
6. 当前权限层只暴露 `STYLE_PROFIT_READ` 与 `STYLE_PROFIT_SNAPSHOT_CREATE`；未发现 `style_profit` 模块对普通前端开放 `cost:diagnostic / cost:dry_run / cost:adjustment_draft` 动作。

因此本任务的核心是：

1. 在不引入任何财务写入候选、dry-run 或诊断入口的前提下，把现有快照与来源映射中的“暂估/已结算/排除/未解析”状态完整投影到只读界面。
2. 把 `allocation_status` 与 `include_provisional_subcontract` 作为快照级只读事实暴露给 API 和前端，确保审计可见。
3. 保持 `raw_ref` 的内部诊断语义不被普通前端放大为新的诊断功能入口。
4. 不触碰 `GL Entry / Journal Entry / Payment Entry / AP / AR` 候选写入、Outbox worker、平台发布与权限扩权语义。

## 2.3 设计依据

1. `TASK-022A` 已明确：外发成本分摊为“结算净额优先，验货 provisional 兜底”，且 `provisional` 与 `settled` 必须可区分、可审计。
2. `TASK-022A` 已明确：`cost:diagnostic`、`cost:dry_run`、`cost:adjustment_draft` 属于冻结动作权限，普通前端不得暴露 `cost:diagnostic`。
3. `TASK-022A` 已明确：成本结果当前只能作为本地快照和候选分析输出，不得直接成为财务事实。
4. `TASK-022B` 已明确：当前成本实现链路第一步已收口到“本地快照创建 + 列表 / 详情 / 来源映射基线”，后续子任务需继续沿 `022B -> 022C -> 022D` 推进。
5. `Sprint3_主执行计划.md` 明确成本核算实现子任务顺序为 `022B -> 022C -> 022D`。

## 3. 允许范围

> 以下为后续 B 实现候选范围；本轮 A 仅输出任务单，不修改实现。

1. 允许修改以下后端文件：
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/style_profit.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/style_profit_service.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/style_profit.py`
2. 允许修改以下前端文件：
   - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/style_profit.ts`
   - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/style_profit/StyleProfitSnapshotList.vue`
   - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/style_profit/StyleProfitSnapshotDetail.vue`
3. 允许补充与来源映射状态投影、暂估口径只读展示和 API 审计相关的最小测试：
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_api.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_snapshot_calculation.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_source_mapping.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_api_permissions.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_api_audit.py`
4. 允许同步更新当前任务单与 C 复核指令。

## 4. 禁止范围

1. 禁止修改 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/style_profit.py`，当前任务不得引入模型变更、DDL、迁移或新表。
2. 禁止修改任何财务写入候选或真实写入文件，包括但不限于 `GL Entry / Journal Entry / Payment Entry / AP / AR` 相关写链路。
3. 禁止修改 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/outbox_state_machine.py` 与任何成本相关 worker 的真实执行语义。
4. 禁止新增 `style_profit` 模块下的 `/diagnostic`、`/dry-run`、调整草稿、候选分录或候选财务写入入口。
5. 禁止新增或暴露 `cost:diagnostic`、`cost:dry_run`、`cost:adjustment_draft` 到普通前端路径。
6. 禁止新增 ERPNext / Frappe `/api/resource` 直连。
7. 禁止把 `provisional` 静默视为 `settled`，禁止把 `excluded / unresolved` 静默过滤。
8. 禁止修改 `.github/**`、`02_源码/**`、新增并行成本核算独立仓库或独立前端工程。
9. 禁止设置 `build_release_allowed=yes`、禁止放行 B、禁止 push / remote / PR / 生产发布。

## 5. 必须输出

1. 快照读侧继续保持统一错误包络和 fail-closed 语义。
2. `StyleProfitSnapshotResult` 与列表 / 详情投影必须显式暴露 `allocation_status`、`include_provisional_subcontract`。
3. 前端详情页必须显式展示来源映射的 `source_status`，并在有值时展示 `posting_date`、`warehouse`，不得只保留 `mapping_status` 而隐藏暂估 / 已结算语义。
4. 当 `include_provisional_subcontract=false` 时，`provisional` 来源必须继续显式体现为只读排除或未纳入利润的状态，不得静默吞掉。
5. 当 `include_provisional_subcontract=true` 时，`provisional` 只能作为只读快照事实被展示，不得升级为财务写入或结算完成语义。
6. 普通前端路径不得新增 `cost:diagnostic / cost:dry_run / cost:adjustment_draft` 暴露，不得新增内部诊断按钮或接口。

## 6. 验收标准

1. 任务实现候选范围仅限 `style_profit` 读侧投影，不包含模型迁移、财务写链路、worker、outbox 公共状态机、`.github/**`、`02_源码/**`。
2. API 与前端能显式展示 `allocation_status` 与 `include_provisional_subcontract`，且保持当前快照基线语义不变。
3. 来源映射读侧能显式辨识 `source_status / mapping_status / include_in_profit / unresolved_reason / posting_date / warehouse`，不存在“有暂估事实但 UI 无法识别”的伪成功。
4. `provisional / settled / excluded / unresolved` 语义继续可区分、可审计，不存在把 `provisional` 自动等价为 `settled` 的投影漂移。
5. 不存在新增 `style_profit` 诊断接口、dry-run 接口、调整草稿入口、财务写入口或普通前端诊断按钮。
6. C 对本任务单出具正式复核结论前，不得放行 B。

## 7. 验证命令

```bash
cd /Users/hh/Desktop/领意服装管理系统
test -f '03_需求与设计/02_开发计划/TASK-022C_成本来源映射状态与暂估口径只读投影基线_工程任务单.md'
rg -n "include_provisional_subcontract|allocation_status" \
  '07_后端/lingyi_service/app/schemas/style_profit.py' \
  '07_后端/lingyi_service/app/services/style_profit_service.py' \
  '06_前端/lingyi-pc/src/api/style_profit.ts' \
  '06_前端/lingyi-pc/src/views/style_profit/StyleProfitSnapshotList.vue' \
  '06_前端/lingyi-pc/src/views/style_profit/StyleProfitSnapshotDetail.vue'
rg -n "source_status|mapping_status|include_in_profit|unresolved_reason|posting_date|warehouse" \
  '07_后端/lingyi_service/app/schemas/style_profit.py' \
  '06_前端/lingyi-pc/src/api/style_profit.ts' \
  '06_前端/lingyi-pc/src/views/style_profit/StyleProfitSnapshotDetail.vue'
rg -n "/diagnostic|cost:diagnostic|cost:dry_run|cost:adjustment_draft|STYLE_PROFIT_.*DIAGNOSTIC" \
  '07_后端/lingyi_service/app/routers/style_profit.py' \
  '07_后端/lingyi_service/app/services/permission_service.py' \
  '06_前端/lingyi-pc/src' || true
pytest -q \
  '/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_api.py' \
  '/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_snapshot_calculation.py' \
  '/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_source_mapping.py' \
  '/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_api_permissions.py' \
  '/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_api_audit.py'
git diff --name-only -- \
  '07_后端/lingyi_service/app/routers/style_profit.py' \
  '07_后端/lingyi_service/app/services/style_profit_service.py' \
  '07_后端/lingyi_service/app/schemas/style_profit.py' \
  '06_前端/lingyi-pc/src/api/style_profit.ts' \
  '06_前端/lingyi-pc/src/views/style_profit/StyleProfitSnapshotList.vue' \
  '06_前端/lingyi-pc/src/views/style_profit/StyleProfitSnapshotDetail.vue' \
  '07_后端/lingyi_service/app/models/style_profit.py' \
  '07_后端/lingyi_service/app/services/outbox_state_machine.py' \
  '.github' '02_源码'
```

## 8. 完成回报

```text
TASK-022C 执行完成。
结论：待审计
是否继续限定为只读投影：是 / 否
是否显式展示 allocation_status：是 / 否
是否显式展示 include_provisional_subcontract：是 / 否
是否显式展示 provisional / settled / excluded / unresolved 状态：是 / 否
是否新增诊断 / dry-run / 调整草稿入口：否
是否写入 GL Entry / Journal Entry / Payment Entry / AP / AR：否
是否修改 style_profit 模型 / DDL：否
是否 push/remote/PR：否
```
