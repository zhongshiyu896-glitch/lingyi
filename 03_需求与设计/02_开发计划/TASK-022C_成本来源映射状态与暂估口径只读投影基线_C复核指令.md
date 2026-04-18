# TASK-022C 成本来源映射状态与暂估口径只读投影基线 C复核指令

## 1. 复核对象

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-022C_成本来源映射状态与暂估口径只读投影基线_工程任务单.md`

## 2. 复核目标

请 C 仅复核 `TASK-022C` 任务单边界是否可审计、可执行、未越权，并给出 `PASS / NEEDS_FIX / BLOCKED` 正式结论。

## 3. 必核项

1. 是否严格锚定 `TASK-022A` 第 214 份与 `TASK-022B` 第 236 份通过事实，且未把 `TASK-021B` 第 233 份历史状态对账阻塞误写为当前前置门禁。
2. 是否基于当前仓库已存在的 `style_profit` 路由、服务、schema、前端 API 和视图锚点收口，而不是臆造新模块或新工程。
3. 是否把范围限定在“来源映射状态、暂估口径与分摊状态的只读投影”，没有越权扩到财务写链路、dry-run、诊断接口、调整草稿或 worker。
4. 是否明确 `allocation_status` 与 `include_provisional_subcontract` 作为快照级只读事实投影，而非模型迁移、DDL 或状态解冻。
5. 是否明确 `provisional / settled / excluded / unresolved` 必须显式可见、可审计，且普通前端不得新增 `cost:diagnostic / cost:dry_run / cost:adjustment_draft` 暴露。
6. 是否明确允许文件、禁止文件、验收标准和验证命令。
7. 验证命令是否基于真实文件、真实路径与现有测试资产。
8. 是否明确当前 `build_release_allowed=no`，本轮只允许 C 对任务单本身做复核，不得放行 B。

## 4. 裁决要求

- 若任务单边界完整且可审计，输出 `PASS`，并将 `LOOP_STATE.md` 写回 `PASS / A Technical Architect / TASK-022C` 或按协议交回 A 继续下一步分发。
- 若任务单存在可修复问题，输出 `NEEDS_FIX`，并列明需要 A 修订的条目。
- 若发现主线不一致、范围越权、前置缺失或需要用户决策，输出 `BLOCKED`。

## 5. 禁止事项

- C 不得替 A 修改任务单正文。
- C 不得替 B 实现代码。
- C 不得把本任务通过直接解释为允许 B 实现。
- C 不得宣称 GitHub / Hosted Runner / Branch Protection / 生产发布闭环。
