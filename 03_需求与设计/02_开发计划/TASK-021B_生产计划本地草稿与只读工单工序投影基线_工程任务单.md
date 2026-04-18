# TASK-021B 生产计划本地草稿与只读工单工序投影基线 工程任务单

## 1. 基本信息

- 任务编号：TASK-021B
- 任务名称：生产计划本地草稿与只读工单工序投影基线
- 角色：架构师
- 优先级：P1
- 状态：审计通过（审计意见书第 232 份）
- 前置依赖：TASK-021A 审计通过（审计意见书第 212 份）

## 2. 任务目标

基于 `TASK-021A` 已冻结的生产管理边界，以及当前仓库中已存在的 `production` 模块代码，输出第一张生产管理实现子任务，范围限定为“本地生产计划草稿 + 只读工单 / 工序投影基线”收口：

1. 保留并收口本地生产计划的草稿创建、列表、详情和物料检查能力。
2. 允许 Work Order / Job Card 以只读投影形式出现在生产详情中，但不得把这些投影升级为 ERPNext 真实写入流程。
3. 明确 `create-work-order`、`sync-job-cards` 等候选写入口在当前任务中保持冻结，不得对普通前端路径放开真实执行。
4. 本任务只形成可审计工程任务边界；在 `build_release_allowed=no` 条件下，不直接放行 B 实现。

## 2.1 当前门禁状态

1. `TASK-021A` 已正式通过，允许进入生产管理实现任务拆分。
2. 用户已明确要求暂停移动端链路，切换到 `TASK-021B` 生产管理实现。
3. `TASK-021B` 已于审计意见书第 232 份通过任务单复核，但当前 `build_release_allowed=no`，本任务不等同于放行 B 实现；后续如继续推进生产管理实现链路，仍需由 A 单独分发下一张任务。

## 2.2 已确认的现状基础

当前仓库中生产管理基础代码已存在，不得按“从零新建模块”口径重复立项：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/production.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/production.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/production.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/production_service.py`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/production.ts`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/production/ProductionPlanList.vue`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/production/ProductionPlanDetail.vue`

因此本任务的核心是：

1. 按 `TASK-021A` 把现有生产模块收口到“本地草稿 + 只读投影”边界。
2. 冻结普通前端路径上的 Work Order / Job Card 写入口。
3. 保持 fail-closed、权限审计、脱敏和统一错误包络不被破坏。
4. 不触碰 ERPNext 真实写链路、Outbox worker 执行链和平台发布语义。

## 2.3 设计依据

1. `TASK-021A` 已冻结：Work Order / Job Card / BOM / Routing 写入默认冻结，真实写入必须后续单独放行。
2. `TASK-021A` 已明确：生产管理实现任务必须“单独设计、单独审计、单独放行”。
3. `TASK-021A` 已明确：`TASK-014C` 未完成前，不允许进入真实平台联调或生产发布。
4. 当前 `production` 模块已存在本地生产计划、物料检查、工单映射、工序映射和候选写入口代码，因此 `TASK-021B` 必须以“现有模块收口”为目标，而不是新开并行模块。

## 3. 允许范围

> 以下为后续 B 实现候选范围；本轮 A 仅输出任务单，不修改实现。

1. 允许修改以下后端文件：
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/production.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/production_service.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/production.py`
2. 允许修改以下前端文件：
   - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/production.ts`
   - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/production/ProductionPlanList.vue`
   - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/production/ProductionPlanDetail.vue`
3. 允许补充与生产计划读模型、物料检查、权限门禁、候选写入口冻结相关的最小测试：
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_production_plan.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_production_permissions.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_production_job_card_sync.py`
4. 允许同步更新当前任务单与 C 复核指令。

## 4. 禁止范围

1. 禁止新建并行生产管理模块、独立仓库、独立前端工程。
2. 禁止修改 `07_后端/lingyi_service/app/services/production_work_order_worker.py`、`07_后端/lingyi_service/app/services/production_work_order_outbox_service.py`、`07_后端/lingyi_service/app/services/erpnext_production_adapter.py`、`07_后端/lingyi_service/app/services/erpnext_job_card_adapter.py` 的真实写执行语义。
3. 禁止修改 `06_前端/lingyi-pc/src/router/**`、`.github/**`、`02_源码/**`。
4. 禁止引入 ERPNext / Frappe `/api/resource` 直连。
5. 禁止放开 `create-work-order`、`sync-job-cards` 到普通前端用户的真实执行路径。
6. 禁止新增 `POST`、`PUT`、`PATCH`、`DELETE` 的 ERPNext 真实写调用。
7. 禁止宣称生产管理已实现完成、ERPNext 联调完成、生产发布完成。
8. 禁止设置 `build_release_allowed=yes`、禁止放行 B、禁止 push / remote / PR / 生产发布。

## 5. 必须输出

1. 生产计划列表 / 详情 / 物料检查继续可用，并保持统一错误包络和 fail-closed 语义。
2. Work Order / Job Card 在详情页只能作为只读投影展示，不得触发真实写链路。
3. 普通前端路径上的 `create-work-order`、`sync-job-cards` 必须保持冻结：要么前端不展示按钮，要么后端返回受控冻结语义，但不得实际创建 outbox 或调用 ERPNext 写接口。
4. 生产模块权限继续严格使用 `production:*` 动作权限，不得降级到更宽权限。
5. 不得记录敏感凭据、服务账号密钥、ERPNext 凭据原文。

## 6. 验收标准

1. 任务实现候选范围不包含 worker、adapter 真实写执行文件、`.github/**`、`02_源码/**`。
2. 生产计划列表 / 详情 / 物料检查能力仍可用，且权限不足、资源不存在、上游异常时继续返回受控失败语义。
3. 普通前端路径不存在真实可点击的 Work Order 创建 / Job Card 同步写入口，或点击后只得到受控冻结语义。
4. 不存在 ERPNext / Frappe `/api/resource` 直连。
5. 不存在新增敏感凭据本地持久化或日志泄露。
6. C 对本任务单出具正式复核结论前，不得放行 B。

## 7. 验证命令

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

## 8. 完成回报

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
