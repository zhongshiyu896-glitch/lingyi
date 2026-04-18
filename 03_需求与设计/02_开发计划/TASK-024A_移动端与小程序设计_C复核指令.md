# C复核指令

- 任务编号：`TASK-024A_C复核`
- 接收角色：`C Auditor`
- 更新时间：`2026-04-18 09:54 CST+8`
- 主线归属：`TASK-024A`

## 复核目标

对 `TASK-024A_移动端与小程序设计.md` 进行正式架构审计，给出 `PASS / NEEDS_FIX / BLOCKED` 结论，并明确是否允许 A 后续分发 `TASK-024B ~ TASK-024D`。

## 复核输入

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-024A_移动端与小程序设计.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-021A_生产管理边界设计.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-022A_成本核算边界设计.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-023A_供应链协同设计.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/Sprint3_主执行计划.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录/审计官会话日志.md`

## 必查项

1. `TASK-024A` 是否明确为渠道层设计，而不是旁路业务域。
2. 是否明确移动端 / 小程序不得直连 ERPNext `/api/resource`，读取继续走 `TASK-008`，候选写入继续走 `TASK-009`。
3. 是否明确继承 `TASK-007` 权限审计与 `TASK-010` 前端门禁。
4. 是否明确 `资源存在但越权` 与 `资源不存在` 统一 `not-found` 外部语义。
5. 是否明确 `TASK-014C` 继续冻结，且不得宣称 required checks / Hosted Runner / Branch Protection / 生产发布完成。
6. 是否明确 `TASK-024B ~ TASK-024D` 在 `TASK-024A` 通过前不得进入。

## 输出要求

C 必须明确给出：

- 审计对象：`TASK-024A`
- 审计意见书编号
- 结论：`PASS / NEEDS_FIX / BLOCKED`
- 问题项：`高 / 中 / 低`
- 是否允许 A 后续分发 `TASK-024B ~ TASK-024D`：`是 / 否`

## 当前禁止项

- 不得放行 `B Engineer`
- 不得进入实现
- 不得跳过正式审计直接认定 `TASK-024A` 通过
