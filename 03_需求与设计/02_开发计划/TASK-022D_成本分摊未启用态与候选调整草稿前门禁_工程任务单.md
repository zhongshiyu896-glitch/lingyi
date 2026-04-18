# TASK-022D 成本分摊未启用态与候选调整草稿前门禁 工程任务单

## 1. 基本信息

- 任务编号：TASK-022D
- 任务名称：成本分摊未启用态与候选调整草稿前门禁
- 角色：架构师
- 优先级：P1
- 状态：待审计
- 前置依赖：TASK-022A 审计通过（审计意见书第 214 份）；TASK-022B 任务单复核通过（审计意见书第 236 份）；TASK-022C 任务单复核通过（审计意见书第 237 份）

## 2. 任务目标

基于 `TASK-022A` 已冻结的成本核算边界，以及 `TASK-022B`、`TASK-022C` 已完成的快照读侧和来源映射只读投影收口，输出成本核算实现链路第三张任务单，范围限定为“分摊未启用态、候选调整草稿未解锁态与权限 / 路由前门禁”：

1. 明确 `LyCostAllocationRule` 与快照 `allocation_status` 当前仅允许保持 `disabled / not_enabled` 未启用态，不得被解释为已解锁分摊实现。
2. 明确 `style_profit` 当前只允许快照列表 / 详情 / 创建三类入口，不得新增 `diagnostic / dry-run / adjustment_draft / candidate_journal` 等前门入口。
3. 明确普通前端与权限层当前不得暴露 `cost:diagnostic / cost:dry_run / cost:adjustment_draft` 或任何财务候选写入口。
4. 本任务只形成可审计工程任务边界；在 `build_release_allowed=no` 条件下，不直接放行 B 实现。

## 2.1 当前门禁状态

1. `TASK-022A` 已于审计意见书第 214 份通过，允许进入成本核算实现任务拆分。
2. `TASK-022B` 已于审计意见书第 236 份通过，成本快照创建、列表、详情和来源映射基线已完成正式任务单收口。
3. `TASK-022C` 已于审计意见书第 237 份通过，来源映射状态、暂估口径和 `allocation_status / include_provisional_subcontract` 只读投影边界已完成正式任务单收口。
4. 当前 `build_release_allowed=no`，本任务仍需先交 C 复核边界、验收标准、允许 / 禁止范围；C 未 PASS 前不得进入 B 实现。
5. 即使 `TASK-022D` 任务单通过，也只表示成本链路任务单拆分完成；除非后续 Context Pack 明确 `build_release_allowed=yes`，否则仍不得放行 B。

## 2.2 已确认的现状基础

当前仓库中与 `TASK-022D` 直接相关的真实代码锚点已经存在，不得按“从零新增成本权限系统或财务写入模块”口径重复立项：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/style_profit.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/permission_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/main.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/style_profit.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/style_profit.py`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/router/index.ts`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/style_profit.ts`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/style_profit/StyleProfitSnapshotList.vue`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/style_profit/StyleProfitSnapshotDetail.vue`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_models.py`

已核实的当前实现现状：

1. `LyStyleProfitSnapshot` 模型中 `allocation_status` 默认值为 `not_enabled`，`LyCostAllocationRule.status` 默认值为 `disabled`。
2. `test_style_profit_models.py` 已存在 `test_cost_allocation_rule_default_status_disabled`，当前默认语义已经有测试锚点。
3. `permission_service.py` 当前对 `style_profit` 只暴露 `STYLE_PROFIT_READ` 与 `STYLE_PROFIT_SNAPSHOT_CREATE` 相关权限检查，未发现 `cost:diagnostic / cost:dry_run / cost:adjustment_draft` 的普通前端放行逻辑。
4. `main.py` 的路由动作映射当前只识别 `/api/reports/style-profit/snapshots` 的 `GET / POST` 与单条快照 `GET`，未发现 `/diagnostic`、`/dry-run`、`adjustment_draft` 等入口映射。
5. 前端 `router/index.ts` 当前只注册了 `StyleProfitSnapshotList` 与 `StyleProfitSnapshotDetail` 两个页面路由，未发现成本诊断页、调整草稿页或财务候选写页。
6. 现有 `style_profit.ts` 与详情页仍以读侧为主，没有新增财务写入候选或内部诊断入口。

因此本任务的核心是：

1. 把当前“未启用分摊 / 未解锁候选调整”作为正式门禁状态写清楚，避免后续误把模型字段和默认值理解成已开放能力。
2. 把权限、路由、前端页面三层的“未暴露”状态固定为可验证边界。
3. 明确未来若要进入 `cost:adjustment_draft / cost:dry_run / cost:diagnostic / 财务候选写入`，必须另起任务、另审、另放行。
4. 不触碰 `GL Entry / Journal Entry / Payment Entry / AP / AR` 候选写入、Adapter / Outbox 公共状态机、平台发布与权限扩权语义。

## 2.3 设计依据

1. `TASK-022A` 已明确：分摊规则必须版本化，当前仅冻结口径，不实现自动分摊写入。
2. `TASK-022A` 已明确：`cost:adjustment_draft`、`cost:dry_run`、`cost:diagnostic` 属于冻结动作权限，不得在普通前端开放。
3. `TASK-022A` 已明确：成本核算结果可作为“候选分录/候选调整”输出，但必须经后续独立任务与审计放行。
4. `TASK-022A` 已明确：`GL Entry / Payment Entry` 当前禁止直接写入。
5. `Sprint3_主执行计划.md` 明确成本核算实现子任务顺序为 `022B -> 022C -> 022D`。

## 3. 允许范围

> 以下为后续 B 实现候选范围；本轮 A 仅输出任务单，不修改实现。

1. 允许修改以下后端文件：
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/permission_service.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/main.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/style_profit.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/style_profit.py`
2. 允许修改以下前端文件：
   - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/router/index.ts`
   - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/style_profit.ts`
   - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/style_profit/StyleProfitSnapshotList.vue`
   - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/style_profit/StyleProfitSnapshotDetail.vue`
3. 允许补充与默认禁用态、路由未暴露、权限未扩权相关的最小测试：
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_models.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_api_permissions.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_api_audit.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_api.py`
4. 允许同步更新当前任务单与 C 复核指令。

## 4. 禁止范围

1. 禁止修改 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/style_profit.py`，当前任务不得引入模型变更、DDL、迁移或新表。
2. 禁止新增 `style_profit` 的 `/diagnostic`、`/dry-run`、`/adjustment-draft`、`/candidate-journal`、`/candidate-payment` 等前门接口。
3. 禁止新增或暴露 `cost:diagnostic`、`cost:dry_run`、`cost:adjustment_draft` 到普通前端路径。
4. 禁止新增成本分摊规则的可写 API、前端编辑页、批量执行入口或后台 worker。
5. 禁止修改任何财务写入候选或真实写入文件，包括但不限于 `GL Entry / Journal Entry / Payment Entry / AP / AR` 相关写链路。
6. 禁止修改 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/outbox_state_machine.py`、任何成本相关 worker、以及 `TASK-008` / `TASK-009` 的公共语义。
7. 禁止新增 ERPNext / Frappe `/api/resource` 直连。
8. 禁止修改 `.github/**`、`02_源码/**`、新增并行成本核算独立仓库或独立前端工程。
9. 禁止设置 `build_release_allowed=yes`、禁止放行 B、禁止 push / remote / PR / 生产发布。

## 5. 必须输出

1. 快照级 `allocation_status` 继续以 `not_enabled` 作为当前读侧事实，不得被解释为已启用分摊。
2. `LyCostAllocationRule` 继续保持默认 `disabled` 语义，且当前不得暴露可写入口。
3. `style_profit` 的后端路由动作映射继续只允许快照列表 / 详情 / 创建，不得新增诊断、dry-run、调整草稿或财务候选写入口。
4. 前端路由继续只允许列表 / 详情页面，不得新增成本诊断页、成本调整页、财务候选写页。
5. 权限层不得为普通前端新增 `cost:diagnostic / cost:dry_run / cost:adjustment_draft` 放行。
6. 所有“未启用 / 未解锁”状态必须 fail-closed，不得出现“入口存在但默认可试”的伪开放。

## 6. 验收标准

1. 任务实现候选范围仅限 `style_profit` 默认禁用态和前门门禁收口，不包含模型迁移、财务写链路、worker、outbox 公共状态机、`.github/**`、`02_源码/**`。
2. `LyCostAllocationRule.status=disabled` 与 `allocation_status=not_enabled` 的默认语义继续存在且可测试。
3. `main.py` 与 `router/index.ts` 不出现新的 `style_profit diagnostic / dry-run / adjustment draft` 暴露。
4. `permission_service.py` 不为普通前端新增 `cost:diagnostic / cost:dry_run / cost:adjustment_draft` 放行。
5. 不存在 `GL Entry / Journal Entry / Payment Entry / AP / AR` 候选写入口或财务候选提交。
6. C 对本任务单出具正式复核结论前，不得放行 B。

## 7. 验证命令

```bash
cd /Users/hh/Desktop/领意服装管理系统
test -f '03_需求与设计/02_开发计划/TASK-022D_成本分摊未启用态与候选调整草稿前门禁_工程任务单.md'
rg -n "allocation_status|LyCostAllocationRule|status.*disabled|not_enabled" \
  '07_后端/lingyi_service/app/models/style_profit.py' \
  '07_后端/lingyi_service/tests/test_style_profit_models.py' \
  '07_后端/lingyi_service/app/schemas/style_profit.py'
rg -n "/api/reports/style-profit|STYLE_PROFIT_READ|STYLE_PROFIT_SNAPSHOT_CREATE|cost:diagnostic|cost:dry_run|cost:adjustment_draft" \
  '07_后端/lingyi_service/app/main.py' \
  '07_后端/lingyi_service/app/services/permission_service.py' \
  '07_后端/lingyi_service/app/routers/style_profit.py' \
  '06_前端/lingyi-pc/src/router/index.ts' \
  '06_前端/lingyi-pc/src/api/style_profit.ts' \
  '06_前端/lingyi-pc/src/views/style_profit'
# 负向扫描只核对 style_profit 自身路径 / 动作模式与成本权限键，避免误命中其他模块既有 /diagnostic。
rg -n "/api/reports/style-profit/.+(diagnostic|dry-run|dry_run|adjustment-draft|adjustment_draft|candidate-journal|candidate_journal|candidate-payment|candidate_payment)|STYLE_PROFIT_(DIAGNOSTIC|DRY_RUN|ADJUSTMENT_DRAFT|CANDIDATE(_JOURNAL|_PAYMENT)?)" \
  '07_后端/lingyi_service/app/main.py' \
  '07_后端/lingyi_service/app/routers/style_profit.py' || true
rg -n "cost:diagnostic|cost:dry_run|cost:adjustment_draft|candidate-journal|candidate_journal|candidate-payment|candidate_payment|adjustment-draft|adjustment_draft|dry-run|dry_run" \
  '07_后端/lingyi_service/app/services/permission_service.py' \
  '06_前端/lingyi-pc/src/router/index.ts' \
  '06_前端/lingyi-pc/src/api/style_profit.ts' \
  '06_前端/lingyi-pc/src/views/style_profit' || true
pytest -q \
  '/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_models.py' \
  '/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_api_permissions.py' \
  '/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_api_audit.py' \
  '/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_api.py'
git diff --name-only -- \
  '07_后端/lingyi_service/app/services/permission_service.py' \
  '07_后端/lingyi_service/app/main.py' \
  '07_后端/lingyi_service/app/routers/style_profit.py' \
  '07_后端/lingyi_service/app/schemas/style_profit.py' \
  '06_前端/lingyi-pc/src/router/index.ts' \
  '06_前端/lingyi-pc/src/api/style_profit.ts' \
  '06_前端/lingyi-pc/src/views/style_profit' \
  '07_后端/lingyi_service/app/models/style_profit.py' \
  '07_后端/lingyi_service/app/services/outbox_state_machine.py' \
  '.github' '02_源码'
```

## 8. 完成回报

```text
TASK-022D 执行完成。
结论：待审计
是否继续保持 allocation_status=not_enabled：是 / 否
是否继续保持 LyCostAllocationRule.status=disabled：是 / 否
是否新增 style_profit 诊断 / dry-run / 调整草稿入口：否
是否新增普通前端权限暴露：否
是否写入 GL Entry / Journal Entry / Payment Entry / AP / AR：否
是否修改 style_profit 模型 / DDL：否
是否 push/remote/PR：否
```
