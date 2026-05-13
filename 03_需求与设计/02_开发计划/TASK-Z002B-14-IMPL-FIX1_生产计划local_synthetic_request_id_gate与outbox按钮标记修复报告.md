# TASK-Z002B-14-IMPL-FIX1 修复报告

## 1. 任务结论

- `TASK_ID`: `TASK-Z002B-14-IMPL-FIX1`
- `ROLE`: `B Engineer`
- `CODE_CHANGED`: `YES`
- 本轮只修复 C 指定两项：
  1. `create_plan` local synthetic scenario gate 补齐 `request_id` 载体并 fail-closed。
  2. `create-work-order` 按钮从 guarded readonly 标记改为 allowlist 标记。

## 2. 代码修复

### 2.1 request_id gate

- 文件：
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/production.py`
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/production_service.py`
- 修复点：
  - `create_production_plan` 从 header 读取 `X-Request-ID`，并传入 `resolve_create_scope` 与 `create_plan`。
  - `ProductionService` 的 local synthetic 路径贯通 `request_id` 参数。
  - `_extract_local_synthetic_scenario_tag` 增加 request_id 约束：
    - 缺失：`PRODUCTION_IDEMPOTENCY_CONFLICT`（`request_id 不能为空`）
    - 格式不含合法 `scenario_tag`：冲突 fail-closed
    - 与其他 carrier 不一致：冲突 fail-closed

### 2.2 create-work-order 按钮标记

- 文件：
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/production/ProductionPlanDetail.vue`
- 修复点：
  - `data-write-guard="guarded:readonly"` 改为 `data-write-guard="allowed:create-work-order-outbox-only"`
  - 增加 `data-write-allowlist="create-work-order-outbox-only"`
  - 保留 `material-check` 的 guarded 标记不变，未扩大范围。

## 3. FIX1 证据

- 主证据：
  - `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/task_z002b_14_impl_fix1_evidence.json`
- API 验证结果：
  - `/tmp/task_z002b14_fix1_api_result.json`
  - `missing request_id` => `409/PRODUCTION_IDEMPOTENCY_CONFLICT`
  - `mismatched request_id` => `409/PRODUCTION_IDEMPOTENCY_CONFLICT`
  - `valid request_id` => `200`，并可继续 `create-work-order`（outbox-only）
- 浏览器/DOM 标记证据：
  - `/tmp/task_z002b14_fix1_browser_result.json`
- 清理证据：
  - `/tmp/task_z002b14_fix1_cleanup.json`
  - `rollback_cleanup_executed=true`
  - `zero_residual=true`
  - 残留表计数均为 0：`ly_production_work_order_outbox`、`ly_production_work_order_link`、`ly_production_job_card_link`、`ly_production_plan_material`、`ly_production_status_log`、`ly_production_plan`

## 4. 写入边界核对

- 允许写（仅本地测试库）：
  - `POST /api/production/plans`
  - `POST /api/production/plans/{plan_id}/create-work-order`
- 禁止写触发计数：
  - `material-check=0`
  - `sync-job-cards=0`
  - `internal-worker=0`
  - `erpnext-write=0`
  - `production-write=0`
  - `upload/download/export/print=0`
  - `unexpected_write_request_count=0`

## 5. 本轮变更文件

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/production.ts`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/production/ProductionPlanDetail.vue`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/production.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/production_service.py`

## 6. 禁止动作核对

- 未修改 `production_work_order_worker.py`、`erpnext_production_adapter.py`
- 未改测试代码
- 未改控制面 / A 日志 / C 审计记录
- 未执行 `git add/commit/push`
- 未执行 `PR/merge/tag/release`
- 未执行 `cleanup/reset/restore/clean/delete`
