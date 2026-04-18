# TASK-021B 派发给工程师的实现指令

## 1. 派发信息

- 任务编号：TASK-021B
- 任务名称：生产计划本地草稿与只读工单工序投影基线
- 派发角色：A Technical Architect
- 执行角色：B Engineer
- 派发时间：2026-04-18 18:45 CST+8
- 依据任务单：`/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-021B_生产计划本地草稿与只读工单工序投影基线_工程任务单.md`
- 审计依据：
  - `TASK-021A` 审计通过（审计意见书第 212 份）
  - `TASK-021B` 任务单复核通过（审计意见书第 232 份）

## 2. 派发目标

基于现有 `production` 模块，完成“本地生产计划草稿 + 只读工单 / 工序投影基线”的实现收口。你只能在 `TASK-021B` 已冻结边界内工作，不得把本任务扩展成 ERPNext 真实写入、Worker / Outbox 执行链、平台发布、或新的生产管理总包任务。

本次派发仅用于指导 B 本地实现与自验，不等同于 `build_release_allowed=yes`。如共享门禁仍为 `no`，你可以完成本地实现草稿和自验，但不得擅自放行、提交生产、或宣称发布闭环完成。

## 3. 实现范围

### 3.1 允许实现的内容

1. 保留并收口本地生产计划的草稿创建、列表、详情、物料检查能力。
2. 在生产计划详情中保留 Work Order / Job Card 的只读投影展示。
3. 对普通前端路径上的 `create-work-order`、`sync-job-cards` 做冻结收口：
   - 要么前端不展示；
   - 要么点击后只返回受控冻结语义；
   - 但不得进入真实写链路。
4. 继续保持统一错误包络、fail-closed 语义、权限约束与脱敏要求。
5. 在最小范围内补齐或修正测试，证明本任务闭合。

### 3.2 允许修改的文件

1. 后端：
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/production.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/production_service.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/production.py`
2. 前端：
   - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/production.ts`
   - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/production/ProductionPlanList.vue`
   - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/production/ProductionPlanDetail.vue`
3. 测试：
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_production_plan.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_production_permissions.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_production_job_card_sync.py`

## 4. 严禁范围

1. 禁止修改以下真实写执行链文件：
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/production_work_order_worker.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/production_work_order_outbox_service.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_production_adapter.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_job_card_adapter.py`
2. 禁止修改以下路径：
   - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/router/**`
   - `/Users/hh/Desktop/领意服装管理系统/.github/**`
   - `/Users/hh/Desktop/领意服装管理系统/02_源码/**`
3. 禁止新建并行生产管理模块、独立仓库、独立前端工程。
4. 禁止引入 ERPNext / Frappe `/api/resource` 直连。
5. 禁止向普通前端用户放开 `create-work-order`、`sync-job-cards` 的真实执行。
6. 禁止新增 POST / PUT / PATCH / DELETE 类型的 ERPNext 真实写调用。
7. 禁止记录敏感凭据、服务账号密钥、ERPNext 凭据原文。
8. 禁止设置 `build_release_allowed=yes`。
9. 禁止 push、远程发布、PR、生产发布表述。

## 5. 开始前必须完成的前置检查

1. 逐行阅读以下文件并确认边界：
   - `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-021B_生产计划本地草稿与只读工单工序投影基线_工程任务单.md`
   - `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-021A_生产管理边界设计.md`
2. 核对审计日志中存在以下正式结论：
   - `TASK-021A` 第 212 份通过
   - `TASK-021B` 第 232 份通过
3. 运行 `git -C /Users/hh/Desktop/领意服装管理系统 status --short --branch`，确认当前工作区确实存在大量未提交改动，但不得处理与本任务无关的文件。
4. 检查本任务允许文件当前是否已有他人未提交改动：
   - 如果允许文件内已有你无法确认来源的改动，立即停止，按 `BLOCKED` 回报，不要覆盖。
5. 检查是否需要修改任何禁止范围文件：
   - 只要发现必须改动禁止文件才能完成任务，立即停止，按 `BLOCKED` 回报。
6. 检查本地现状是否与任务单描述一致：
   - `production.py`、`production_service.py`、`production.ts`、`ProductionPlanList.vue`、`ProductionPlanDetail.vue` 必须存在。

## 6. 实现执行要求

1. 后端收口要求：
   - 保持生产计划列表 / 详情 / 物料检查可用。
   - 允许返回 Work Order / Job Card 的只读投影数据。
   - 对 `create-work-order`、`sync-job-cards` 保持冻结，不得创建 outbox，不得调用 ERPNext 真实写接口。
   - 保持统一错误包络与 fail-closed 语义。
   - 权限仍使用 `production:*` 相关动作，不得扩大。
2. 前端收口要求：
   - 保持生产计划列表 / 详情基本可用。
   - 详情页可以展示只读工单 / 工序投影，但不得提供真实写入口。
   - 如存在候选写按钮，必须隐藏、禁用或改为受控冻结提示。
   - 不得修改 router，不得扩展到其他页面。
3. 测试要求：
   - 仅在允许的三个测试文件内补充或修正用例。
   - 测试必须覆盖读侧可用、权限限制、候选写入口冻结语义。

## 7. 完成后必须自验的检查点

### 7.1 功能与边界检查

1. 生产计划列表 / 详情 / 物料检查仍可用。
2. Work Order / Job Card 仅为只读投影，不触发真实写链路。
3. 普通前端不存在真实可执行的 `create-work-order` / `sync-job-cards`。
4. 未引入 ERPNext / Frappe `/api/resource`。
5. 未写入或泄露敏感凭据。

### 7.2 文件范围检查

1. `git diff --name-only` 只应落在允许文件范围内。
2. 不得出现以下文件改动：
   - `production_work_order_worker.py`
   - `production_work_order_outbox_service.py`
   - `erpnext_production_adapter.py`
   - `erpnext_job_card_adapter.py`
   - `06_前端/lingyi-pc/src/router/**`
   - `.github/**`
   - `02_源码/**`

### 7.3 必跑命令

```bash
cd /Users/hh/Desktop/领意服装管理系统
rg -n "create-work-order|sync-job-cards|material-check|/api/production/plans" \
  '07_后端/lingyi_service/app/routers/production.py' \
  '06_前端/lingyi-pc/src/api/production.ts' \
  '06_前端/lingyi-pc/src/views/production/ProductionPlanDetail.vue'
rg -n "(/api/resource|localStorage\.getItem\('LY_AUTH_TOKEN'\)|localStorage\.getItem\('token'\))" \
  '06_前端/lingyi-pc/src/api' '06_前端/lingyi-pc/src/views/production'
pytest -q \
  '/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_production_plan.py' \
  '/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_production_permissions.py' \
  '/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_production_job_card_sync.py'
npm --prefix '06_前端/lingyi-pc' run typecheck
git diff --name-only -- \
  '07_后端/lingyi_service/app/routers/production.py' \
  '07_后端/lingyi_service/app/services/production_service.py' \
  '07_后端/lingyi_service/app/schemas/production.py' \
  '06_前端/lingyi-pc/src/api/production.ts' \
  '06_前端/lingyi-pc/src/views/production' \
  '07_后端/lingyi_service/app/services/production_work_order_worker.py' \
  '07_后端/lingyi_service/app/services/production_work_order_outbox_service.py' \
  '07_后端/lingyi_service/app/services/erpnext_production_adapter.py' \
  '.github' '02_源码'
```

## 8. 交付回报模板

请 B 完成后使用以下模板原样回报：

```text
STATUS: HANDOFF / NEEDS_FIX / BLOCKED
TASK_ID: TASK-021B
ROLE: B
CHANGED_FILES:
- 绝对路径 1
- 绝对路径 2

EVIDENCE:
- 已完成的实现点
- 对应文件与关键行/关键语义

VERIFICATION:
- 命令 1：通过 / 失败（附简要结果）
- 命令 2：通过 / 失败（附简要结果）
- 命令 3：通过 / 失败（附简要结果）

BLOCKERS:
- 若无写“无”

NEXT_ROLE: C
```

同时追加以下任务单要求的结论项：

```text
TASK-021B 执行完成。
结论：审计通过（审计意见书第 232 份）
是否仍限定为本地生产计划草稿 + 只读工单/工序投影：是 / 否
是否放开 create-work-order / sync-job-cards 真实执行：否
是否直连 ERPNext/Frappe：否
是否修改 worker/adapter 真实写执行文件：否
是否修改 .github / 02_源码：否
是否 push/remote/PR：否
```

## 9. 提交审计的触发条件

只有满足以下全部条件，才能提交给 C 审计：

1. 改动仅落在允许文件内。
2. 列表 / 详情 / 物料检查可用，且只读投影边界未破坏。
3. `create-work-order`、`sync-job-cards` 仍为冻结语义，不存在真实写入。
4. 所有验证命令已执行，并在回报中给出结果。
5. 未改动禁止文件，未引入 ERPNext / Frappe `/api/resource`。
6. 未设置 `build_release_allowed=yes`，未执行 push / PR / 发布动作。

## 10. 停止条件

出现以下任一情况，立即停止并按 `BLOCKED` 回报：

1. 需要改动禁止文件才能闭合任务。
2. 允许文件内已存在无法判定来源的未提交改动。
3. 需要引入真实 ERPNext 写链路、Worker、Outbox、Adapter 改动。
4. 需要修改 `.github/**`、`02_源码/**`、router 或新增并行模块。
5. 发现任务单边界与真实代码现状冲突，且无法在允许范围内收口。
6. 发现敏感凭据、服务账号、真实外部联调需求。

## 11. 当前派发结论

本指令已经满足“给 B 明确实现范围、前置检查、验收检查点、交付模板、提交审计触发条件”的派发要求。后续是否实际放行提交、是否解除更高层门禁，由总调度单独决定，不属于本指令范围。
