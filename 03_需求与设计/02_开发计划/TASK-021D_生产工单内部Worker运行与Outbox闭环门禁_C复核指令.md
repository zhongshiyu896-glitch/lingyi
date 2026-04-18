# TASK-021D 生产工单内部Worker运行与Outbox闭环门禁 C复核指令

## 1. 复核对象

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-021D_生产工单内部Worker运行与Outbox闭环门禁_工程任务单.md`

## 2. 复核目标

请 C 仅复核 `TASK-021D` 任务单边界是否可审计、可执行、未越权，并给出 `PASS / NEEDS_FIX / BLOCKED` 正式结论。

## 3. 必核项

1. 是否严格锚定 `TASK-021A` 第 212 份、`TASK-021B` 第 232 份、`TASK-021C` 第 234 份通过事实。
2. 是否把范围限定在“`/internal/work-order-sync/run-once` 内部 worker 运行 + 生产工单 outbox 闭环门禁”，没有越权回改普通前端 / 普通业务请求路径。
3. 是否明确 `run-once` 必须同时受 `PRODUCTION_WORK_ORDER_WORKER` 和 `is_internal_worker_principal(current_user)` 约束。
4. 是否明确 `dry_run=true` 不能产生 ERPNext 创建 / 提交和 outbox 状态副作用。
5. 是否明确 `claim_due / mark_succeeded / mark_failed / event_key / idempotency_key` 的闭环语义必须经由现有 worker / outbox service 受控完成，不得直接篡改状态。
6. 是否明确禁止修改 `production_service.py`、`outbox_state_machine.py`、ERPNext adapter、`core/auth.py`、前端路径、`.github/**`、`02_源码/**`。
7. 验证命令是否基于真实文件、真实路径，且不会因当前不存在的可选文件而误判失败。
8. 是否明确当前 `build_release_allowed=no`，本轮只允许 C 对任务单本身做复核，不得放行 B。

## 4. 裁决要求

- 若任务单边界完整且可审计，输出 `PASS`，并将 `LOOP_STATE.md` 写回 `PASS / A Technical Architect / TASK-021D` 或按协议交回 A 继续下一步分发。
- 若任务单存在可修复问题，输出 `NEEDS_FIX`，并列明需要 A 修订的条目。
- 若发现主线不一致、范围越权、前置缺失或需要用户决策，输出 `BLOCKED`。

## 5. 禁止事项

- C 不得替 A 修改任务单正文。
- C 不得替 B 实现代码。
- C 不得把本任务通过直接解释为允许 B 实现。
- C 不得宣称 GitHub / Hosted Runner / Branch Protection / 生产发布闭环。
