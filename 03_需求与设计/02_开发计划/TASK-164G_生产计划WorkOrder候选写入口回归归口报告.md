# TASK-164G 生产计划 Work Order 候选写入口回归归口报告

## 1. 任务范围

- TASK_ID: `TASK-164G`
- 白名单文件：
  - `06_前端/lingyi-pc/src/router/index.ts`
  - `06_前端/lingyi-pc/src/views/production/ProductionPlanList.vue`
  - `06_前端/lingyi-pc/src/views/production/ProductionPlanDetail.vue`
  - `07_后端/lingyi_service/app/core/error_codes.py`
  - `07_后端/lingyi_service/app/routers/production.py`
  - `07_后端/lingyi_service/app/services/production_service.py`
  - `07_后端/lingyi_service/tests/test_production_plan.py`
- 文档输出：
  - `03_需求与设计/02_开发计划/TASK-164G_生产计划WorkOrder候选写入口回归归口报告.md`
  - `03_需求与设计/02_开发计划/工程师会话日志.md`

## 2. 七文件 diff 摘要（只读）

命令：

`git -C '/Users/hh/Desktop/领意服装管理系统' diff --stat -- '06_前端/lingyi-pc/src/router/index.ts' '06_前端/lingyi-pc/src/views/production/ProductionPlanList.vue' '06_前端/lingyi-pc/src/views/production/ProductionPlanDetail.vue' '07_后端/lingyi_service/app/core/error_codes.py' '07_后端/lingyi_service/app/routers/production.py' '07_后端/lingyi_service/app/services/production_service.py' '07_后端/lingyi_service/tests/test_production_plan.py'`

结果：

- `src/router/index.ts`: `+15/-1`
- `ProductionPlanList.vue`: `+58/-?`（净增方向）
- `ProductionPlanDetail.vue`: `+207/-?`（净增方向）
- `app/core/error_codes.py`: `+3`
- `app/routers/production.py`: `+3/-1`
- `app/services/production_service.py`: `+27/-?`
- `tests/test_production_plan.py`: `+66/-?`
- 合计：`7 files changed, 355 insertions(+), 24 deletions(-)`

## 3. 归属关系

- 历史任务链归属：
  - `TASK-004A / TASK-004B`
  - `TASK-015D ~ TASK-015F`
  - `TASK-021B ~ TASK-021D`
  - `TASK-100A ~ TASK-100D`
- 本轮为定向回归与归口冻结，不扩展到其他业务差异。

## 4. 定向验证结果

### 前端（`/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc`）

1. `npm run check:production-contracts` -> **PASS**
2. `npm run test:production-contracts` -> **PASS**（`scenarios=12`）
3. `npm run typecheck` -> **PASS**

### 后端（`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service`）

1. `python3 -m py_compile app/core/error_codes.py app/routers/production.py app/services/production_service.py tests/test_production_plan.py` -> **PASS**
2. `.venv/bin/python -m pytest tests/test_production_plan.py -v --tb=short` -> **PASS**（`17 passed, 18 warnings`）

结论：本轮无需在七文件内修复代码。

## 5. 静态业务锚点核对

- `src/router/index.ts`
  - 仅承载生产计划页面路由（`/production/plans`、`/production/plans/detail`）。
  - 未发现暴露 `/api/production/internal`、`work-order-sync/run-once` 或 worker 直跑路由。
- `ProductionPlanList.vue`
  - 保留列表/创建入口/状态展示与权限加载路径。
  - 保留普通 UI 边界，不直接跑内部 worker。
- `ProductionPlanDetail.vue`
  - 保留 `material-check`、`create-work-order` 候选写入口、outbox/link 状态与冻结提示。
  - 保留权限/状态 guard（含 `idempotency_key` 校验、状态白名单前置提示）。
- 前端三文件禁止项核对：
  - `fetch(`、`/api/resource`、`/api/method`、`frappe`、`/api/production/internal`、`work-order-sync/run-once` 全部 **无命中**。
- `error_codes.py` / `routers/production.py` / `production_service.py`
  - 覆盖 `material-check` 状态白名单与错误码 `PRODUCTION_MATERIAL_CHECK_STATUS_INVALID`。
  - 覆盖 `create-work-order` 本地 outbox candidate（`idempotency_key`、`event_key`、`pending`/状态边界）。
  - 详情承载 `write_entry_frozen_reason` 与 outbox/link 受控边界。
- `test_production_plan.py`
  - 覆盖生产计划 CRUD、`material-check`、`create-work-order` outbox candidate、详情 work_order/link 字段、仓库必填、状态白名单等关键场景。

静态核对结论：**PASS**。

## 6. 归口结论

- `CODE_CHANGED`: `NO`
- `can_reclassify_to`: `HISTORICAL_TASK_OUTPUT_VERIFIED`
- `remaining_unowned_business_diffs_excluded`: `YES`

本报告不覆盖 `warehouse / sales-inventory / factory-statement / style-profit / CCC` 等其他业务差异。

## 7. 收尾校验

1. `git -C '/Users/hh/Desktop/领意服装管理系统' diff --check -- '06_前端/lingyi-pc/src/router/index.ts' '06_前端/lingyi-pc/src/views/production/ProductionPlanList.vue' '06_前端/lingyi-pc/src/views/production/ProductionPlanDetail.vue' '07_后端/lingyi_service/app/core/error_codes.py' '07_后端/lingyi_service/app/routers/production.py' '07_后端/lingyi_service/app/services/production_service.py' '07_后端/lingyi_service/tests/test_production_plan.py'`
   - 结果：**PASS**（无输出）
2. `git -C '/Users/hh/Desktop/领意服装管理系统' diff --name-only -- '06_前端/lingyi-pc/src/router/index.ts' '06_前端/lingyi-pc/src/views/production/ProductionPlanList.vue' '06_前端/lingyi-pc/src/views/production/ProductionPlanDetail.vue' '07_后端/lingyi_service/app/core/error_codes.py' '07_后端/lingyi_service/app/routers/production.py' '07_后端/lingyi_service/app/services/production_service.py' '07_后端/lingyi_service/tests/test_production_plan.py' '03_需求与设计/02_开发计划/TASK-164G_生产计划WorkOrder候选写入口回归归口报告.md' '03_需求与设计/02_开发计划/工程师会话日志.md'`
   - 结果：见回交 `CHANGED_FILES` 与范围核对。

## 8. 风险与边界

- 未运行 `npm run dev/build/verify`
- 未运行后端全量测试
- 未触碰其他前端 src/scripts、后端非白名单文件、tests 非白名单文件、CCC、控制面、AGENTS、架构师日志、审计官日志、生产/GitHub 管理配置
- 不代表剩余 business tracked diff、REL-004/REL-005、生产联调、ERPNext 生产写入或业务功能放行
