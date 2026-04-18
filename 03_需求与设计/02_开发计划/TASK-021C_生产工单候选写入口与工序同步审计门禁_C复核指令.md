# TASK-021C 生产工单候选写入口与工序同步审计门禁 C复核指令

## 1. 复核对象

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-021C_生产工单候选写入口与工序同步审计门禁_工程任务单.md`

## 2. 复核目标

请 C 仅复核 `TASK-021C` 任务单边界是否可审计、可执行、未越权，并给出 `PASS / NEEDS_FIX / BLOCKED` 正式结论。

## 3. 必核项

1. 是否严格锚定 `TASK-021A` 已通过的生产管理边界与 `TASK-021B` 第 232 份通过结论。
2. 是否把范围限定在“生产工单候选写入口 + 工序同步审计门禁”，没有越权扩到真实 ERPNext 写执行、worker run-once 放开或 Job Card 完工回写。
3. 是否明确 `create-work-order` 仅允许本地 outbox enqueue-or-reuse 语义，不得在普通请求路径直接驱动真实创建 / 提交。
4. 是否明确 `sync-job-cards` 仅允许本地工序投影同步，不得扩展为 Job Card completed_qty 写回。
5. 是否明确内部 worker 入口仍仅允许内部主体调用，不得暴露给普通前端路径。
6. 是否明确禁止修改 worker、outbox 公共状态机、adapter 真实执行文件、`.github/**`、`02_源码/**`。
7. 验证命令是否基于真实文件、真实路径，且不会把范围外文件误写入验收条件。
8. 是否明确当前 `build_release_allowed=no`，本轮只允许 C 对任务单本身做复核，不得放行 B。

## 4. 裁决要求

- 若任务单边界完整且可审计，输出 `PASS`，并将 `LOOP_STATE.md` 写回 `PASS / A Technical Architect / TASK-021C` 或按协议交回 A 继续下一步分发。
- 若任务单存在可修复问题，输出 `NEEDS_FIX`，并列明需要 A 修订的条目。
- 若发现主线不一致、范围越权、前置缺失或需要用户决策，输出 `BLOCKED`。

## 5. 禁止事项

- C 不得替 A 修改任务单正文。
- C 不得替 B 实现代码。
- C 不得把本任务通过直接解释为允许 B 实现。
- C 不得宣称 GitHub / Hosted Runner / Branch Protection / 生产发布闭环。
