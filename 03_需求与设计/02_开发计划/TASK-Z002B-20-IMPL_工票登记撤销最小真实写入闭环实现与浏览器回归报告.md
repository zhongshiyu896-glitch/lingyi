# TASK-Z002B-20-IMPL 工票登记/撤销最小本地真实写入闭环实现与浏览器回归报告

## 1. 任务结论

- 任务状态：`READY_FOR_REVIEW`
- 任务编号：`TASK-Z002B-20-IMPL`
- 角色：`B Engineer`
- 范围结论：仅在 allowlist 内修改，未触碰 allowlist 外产品/后端/测试代码。
- 闭环结论：本地 `register/reversal` 双写入闭环成立，fail-closed 成立，cleanup 后 `zero_residual=true`。

## 2. 代码改动（allowlist 内）

1. `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/workshop/WorkshopTicketRegister.vue`
2. `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/workshop/WorkshopTicketList.vue`
3. `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/workshop.ts`
4. `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/workshop.py`
5. `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/workshop_service.py`

## 3. 实现要点

### 3.1 register/reversal 接口本地 gate

- `APP_ENV=development` 且 `LINGYI_DB_URL=sqlite:///./lingyi_service.local.db` 才允许写入。
- 统一校验 `scenario_tag` 载体一致性：`ticket_key`、`source_ref/reason`、`X-Request-ID`。
- 缺失或不一致时直接 fail-closed（409），且核心业务表无写入。

### 3.2 local synthetic 上下文

- 在本地 gate 下，`WorkshopService` 支持 local synthetic `company/item/wage/employee`，避免 ERPNext 依赖阻断。
- 写入仍走真实 DB 事务与 outbox 逻辑，保持业务链路可审计。

### 3.3 前端写按钮与标记

- 登记按钮标记：`allowed:workshop-ticket-register-local-only` + `workshop-ticket-register`。
- 撤销按钮标记：`allowed:workshop-ticket-reversal-local-only` + `workshop-ticket-reversal`。
- 按钮行为从 guarded 提示改为真实本地调用（仍受后端 gate 约束）。

## 4. 回归证据摘要

- scenario_tag：`Z002-WORKSHOP-TICKET-REGISTER-20260513-001`
- fail-closed：
  - 缺失 `X-Request-ID`：`409 WORKSHOP_IDEMPOTENCY_CONFLICT`
  - `X-Request-ID` 与 scenario_tag 不一致：`409 WORKSHOP_IDEMPOTENCY_CONFLICT`
  - 上述失败场景核心表写入增量：`0`
- 允许写请求：
  - `POST /api/workshop/tickets/register`：`200`
  - `POST /api/workshop/tickets/reversal`：`200`
- 回读：
  - register 后 list GET：`200`
  - reversal 后 list GET：`200`
- 重复/非法撤销：
  - `409 WORKSHOP_REVERSAL_EXCEEDS_REGISTERED`（fail-closed）
- 禁止路径：
  - `batch/sync/internal worker/ERPNext/production/export/print` 均未触发

## 5. rollback 与 zero_residual

- rollback 顺序执行：`outbox -> outbox_log -> daily_wage -> ticket -> operation_audit -> security_audit -> access_denial(if touched)`。
- 清理后残留计数均为 `0`：
  - `ys_workshop_ticket`
  - `ys_workshop_daily_wage`
  - `ys_workshop_job_card_sync_outbox`
  - `ys_workshop_job_card_sync_log`
  - `ys_workshop_outbox_access_denial`
  - `ly_operation_audit_log`
  - `ly_security_audit_log`

## 6. 产物路径

- 报告：`/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-Z002B-20-IMPL_工票登记撤销最小真实写入闭环实现与浏览器回归报告.md`
- evidence JSON：`/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/task_z002b_20_workshop_ticket_register_reversal_evidence.json`
- 浏览器证据：`/tmp/task_z002b20_browser_result.json`
- 清理证据：`/tmp/task_z002b20_cleanup.json`
- API 回归证据：`/tmp/task_z002b20_api_run.json`
- 截图目录：`/tmp/task_z002b20_screenshots`（`3` 张）

## 7. 禁止动作核对

- 未执行 `git add / commit / push`
- 未执行 `PR / merge / tag / release`
- 未执行 repo `cleanup / reset / restore / clean / delete`
- 未触发生产写入
- 未触发 ERPNext 写入
