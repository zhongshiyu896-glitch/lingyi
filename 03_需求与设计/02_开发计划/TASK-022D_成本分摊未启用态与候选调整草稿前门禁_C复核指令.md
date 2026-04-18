# TASK-022D 成本分摊未启用态与候选调整草稿前门禁 C复核指令

## 1. 复核对象

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-022D_成本分摊未启用态与候选调整草稿前门禁_工程任务单.md`

## 2. 复核目标

请 C 仅复核 `TASK-022D` 任务单边界是否可审计、可执行、未越权，并给出 `PASS / NEEDS_FIX / BLOCKED` 正式结论。

## 3. 必核项

1. 是否严格锚定 `TASK-022A` 第 214 份、`TASK-022B` 第 236 份与 `TASK-022C` 第 237 份通过事实，且未把 `TASK-021B` 第 233 份历史状态对账阻塞误写为当前前置门禁。
2. 是否基于当前仓库已存在的 `LyCostAllocationRule`、`allocation_status`、`permission_service.py`、`main.py`、前端路由和现有 `style_profit` 读侧页面锚点收口，而不是臆造新的成本权限系统或财务写模块。
3. 是否把范围限定在“未启用分摊 / 未解锁候选调整”的权限与前门门禁，没有越权扩到财务写链路、诊断接口、dry-run、调整草稿、worker 或模型迁移。
4. 是否明确 `allocation_status=not_enabled` 与 `LyCostAllocationRule.status=disabled` 只是当前默认禁用态，不等于功能开放。
5. 是否明确普通前端不得新增 `cost:diagnostic / cost:dry_run / cost:adjustment_draft` 暴露，也不得新增 `style_profit` 诊断页、调整页或财务候选写页。
6. 是否明确允许文件、禁止文件、验收标准和验证命令。
7. 验证命令是否基于真实文件、真实路径与现有测试资产，且负向扫描已经收敛到 `style_profit` 自身路径 / 动作模式与 `cost:*` 权限键，不会被其他模块既有 `/diagnostic` 误命中。
8. 是否明确当前 `build_release_allowed=no`，本轮只允许 C 对任务单本身做复核，不得放行 B。

## 4. 裁决要求

- 若任务单边界完整且可审计，输出 `PASS`，并将 `LOOP_STATE.md` 写回 `PASS / A Technical Architect / TASK-022D` 或按协议交回 A 继续下一步分发。
- 若任务单存在可修复问题，输出 `NEEDS_FIX`，并列明需要 A 修订的条目。
- 若发现主线不一致、范围越权、前置缺失或需要用户决策，输出 `BLOCKED`。

## 5. 禁止事项

- C 不得替 A 修改任务单正文。
- C 不得替 B 实现代码。
- C 不得把本任务通过直接解释为允许 B 实现。
- C 不得宣称 GitHub / Hosted Runner / Branch Protection / 生产发布闭环。
