# TASK-023C 供应链对账单只读明细与打印导出基线 C复核指令

## 1. 复核对象

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-023C_供应链对账单只读明细与打印导出基线_工程任务单.md`

## 2. 复核目标

请 C 仅复核 `TASK-023C` 任务单边界是否可审计、可执行、未越权，并给出 `PASS / NEEDS_FIX / BLOCKED` 正式结论。

## 3. 必核项

1. 是否严格锚定 `TASK-023A` 第 215 份与 `TASK-023B` 第 240 份通过事实，且未把其他链路任务单通过误写为当前前置门禁。
2. 是否基于当前仓库已存在的 `factory_statement` 列表 / 详情 / 打印、`statement_status`、`payable_outbox_status`、`purchase_invoice_name`、明细行和日志锚点收口，而不是臆造新的采购协同平台或外部门户。
3. 是否把范围限定在“对账单列表 / 详情 / 打印 / 导出只读基线 + 普通前端去写化”，没有越权扩到生成草稿、确认、取消、应付草稿、internal worker、subcontract settlement lock/release 或外部系统真实接入。
4. 是否明确普通前端不得新增或保留 `生成对账单草稿`、`确认对账单`、`取消对账单`、`生成应付草稿` 等候选写入口。
5. 是否明确 `/internal/payable-draft-sync/run-once`、`/{statement_id}/payable-draft`、`/{statement_id}/confirm`、`/{statement_id}/cancel` 在当前任务中保持冻结，不等于已放行。
6. 是否明确允许文件、禁止文件、验收标准和验证命令。
7. 验证命令是否基于真实文件、真实路径与现有测试资产，且对“只读投影保留”和“普通前端去写化”两类目标都有可执行校验。
8. 是否明确当前 `build_release_allowed=no`，本轮只允许 C 对任务单本身做复核，不得放行 B。

## 4. 裁决要求

- 若任务单边界完整且可审计，输出 `PASS`，并将 `LOOP_STATE.md` 写回 `PASS / A Technical Architect / TASK-023C` 或按协议交回 A 继续下一步分发。
- 若任务单存在可修复问题，输出 `NEEDS_FIX`，并列明需要 A 修订的条目。
- 若发现主线不一致、范围越权、前置缺失或需要用户决策，输出 `BLOCKED`。

## 5. 禁止事项

- C 不得替 A 修改任务单正文。
- C 不得替 B 实现代码。
- C 不得把本任务通过直接解释为允许 B 实现。
- C 不得宣称 GitHub / Hosted Runner / Branch Protection / 生产发布闭环。
