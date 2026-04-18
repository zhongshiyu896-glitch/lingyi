# TASK-023D 供应链结算锁定释放与应付草稿内部同步门禁 C复核指令

## 1. 复核对象

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-023D_供应链结算锁定释放与应付草稿内部同步门禁_工程任务单.md`

## 2. 复核目标

请 C 仅复核 `TASK-023D` 任务单边界是否可审计、可执行、未越权，并给出 `PASS / NEEDS_FIX / BLOCKED` 正式结论。

## 3. 必核项

1. 是否严格锚定 `TASK-023A` 第 215 份、`TASK-023B` 第 240 份、`TASK-023C` 第 241 份通过事实，且未误把其他链路任务单或状态对账记录写成当前前置门禁。
2. 是否基于当前仓库真实存在的 `settlement-candidates / settlement-preview / settlement-locks / settlement-locks/release`、`payable-draft / internal/payable-draft-sync/run-once`、`FactoryStatementPayableOutboxService`、`FactoryStatementPayableWorker` 锚点收口，而不是臆造新的协同平台或外部门户。
3. 是否把范围限定在“候选结算锁定 / 释放门禁 + 应付草稿 outbox / 内部 worker 同步门禁 + 关闭当前普通前端 `payable-draft` 直调所需的最小前端改动”，没有越权回到 `TASK-023B` 的外发台账读侧、`TASK-023C` 的对账单读侧 / 打印导出，或扩到外部系统真实接入。
4. 是否明确 `settlement-candidates / preview` 仍是只读候选事实，`settlement-locks / release` 是受控候选门禁，不等于已放行真实结算写入。
5. 是否明确 `POST /api/factory-statements/{statement_id}/payable-draft` 只负责创建 outbox，不得直接创建 ERPNext 发票；`/internal/payable-draft-sync/run-once` 只允许内部 worker 主体调用；普通前端已识别的 `createFactoryStatementPayableDraft` 直调被纳入本任务闭合范围而非被写成“已闭合事实”。
6. 是否明确 `dry_run`、`claim_due / mark_succeeded / mark_failed / dead`、`event_key`、`idempotency_key`、追加式操作记录和租约语义。
7. 是否明确允许文件、禁止文件、验收标准和验证命令，且最小允许前端范围仅限 `06_前端/lingyi-pc/src/api/factory_statement.ts` 与 `06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementDetail.vue`，验证命令能验证该直调已闭合。
8. 是否明确当前 `build_release_allowed=no`，本轮只允许 C 对任务单本身做复核，不得放行 B。

## 4. 裁决要求

- 若任务单边界完整且可审计，输出 `PASS`，并将 `LOOP_STATE.md` 写回 `PASS / A Technical Architect / TASK-023D` 或按协议交回 A 决定下一步。
- 若任务单存在可修复问题，输出 `NEEDS_FIX`，并列明需要 A 修订的条目。
- 若发现主线不一致、范围越权、前置缺失或需要用户决策，输出 `BLOCKED`。

## 5. 禁止事项

- C 不得替 A 修改任务单正文。
- C 不得替 B 实现代码。
- C 不得把本任务通过直接解释为允许 B 实现。
- C 不得宣称 GitHub / Hosted Runner / Branch Protection / 生产发布闭环。
