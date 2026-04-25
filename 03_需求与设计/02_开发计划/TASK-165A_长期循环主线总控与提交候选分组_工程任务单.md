# TASK-165A 长期循环主线总控与提交候选分组工程任务单

```text
STATUS: READY_FOR_BUILD
TASK_ID: TASK-165A
ROLE: B Engineer

任务：长期循环主线总控与提交候选分组

背景 / 当前整体进度：
1. `TASK-157A~163A` 已完成 CCC 自动接力基础能力：执行日志、日志轮转、最近事件只读查询、阶段门禁、C 审计任务单路由、结构化审计结果、嵌套回声抑制、helper/relay attribution、服务重载验证。
2. `TASK-164A~164I` 已完成 Lingyi 当前 dirty worktree 的业务/config 差异归口：164I 的 C 审计结论确认 `NO_REMAINING_UNOWNED_BUSINESS_DIFF_CLOSE_164_SERIES` 成立。
3. 当前本地仍是 dirty worktree：tracked diff 约 41 项，untracked 面很大；这些不是自动等于“未归口业务任务”，后续必须按已审计 baseline 分组处理，禁止重复把同一批 diff 当作新任务。
4. parked blockers 仍然存在且不得自动释放：
   - `TASK-152A`: `BLOCK_FOR_USER_ADMIN_APPROVAL_REL004_REL005`
   - `TASK-090I`: `EVIDENCE_CEILING_BLOCKED`
   - `TASK-110B`: `NO_LEGAL_TASK_110B`
5. 用户明确要求避免死循环，并要求重新梳理整体开发进度和内容，形成一个能长期维持循环的“大任务单”。

目标：
以只读/docs-only 方式输出一份长期循环主线总控报告，帮助 A 后续稳定地“发现新事实 -> 判断合法下一步 -> 派 B -> 送 C -> 关闭或进入下一队列”，而不是反复消费 PASS、IDLE、回声包或历史终态。

必须读取：
- `/Users/hh/.codex/AGENTS.md`
- `/Users/hh/Documents/Playground 2/AGENTS.md`
- `/Users/hh/Documents/Playground 2/CORE_MEMORY.md`
- `/Users/hh/Documents/Playground 2/AUTO_LOOP_PROTOCOL.md`
- `/Users/hh/Documents/Playground 2/LOOP_STATE.md`
- `/Users/hh/Documents/Playground 2/TASK_BOARD.md`
- `/Users/hh/Documents/Playground 2/HANDOVER_STATUS.md`
- `/Users/hh/Documents/Playground 2/INTERVENTION_QUEUE.md`
- `/Users/hh/Desktop/领意服装管理系统/00_交接与日志/HANDOVER_STATUS.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-164I_后164归口总账收口与剩余差异冻结报告.md`
- 最新架构师/工程师/审计官会话日志尾部

允许修改：
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-165A_长期循环主线总控与提交候选分组报告.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md`

禁止修改：
- `/Users/hh/Documents/Playground 2/LOOP_STATE.md`
- `/Users/hh/Documents/Playground 2/TASK_BOARD.md`
- `/Users/hh/Documents/Playground 2/HANDOVER_STATUS.md`
- `/Users/hh/Documents/Playground 2/INTERVENTION_QUEUE.md`
- `/Users/hh/Documents/Playground 2/AUTO_LOOP_PROTOCOL.md`
- `/Users/hh/Desktop/领意服装管理系统/00_交接与日志/HANDOVER_STATUS.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/架构师会话日志.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录/审计官会话日志.md`
- `/Users/hh/Desktop/ccc/**`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/**`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/**`
- `.gitignore`
- `vite.config.ts`
- 生产/GitHub 管理配置

禁止动作：
- 禁止写业务代码、后端代码、测试代码或 CCC 代码。
- 禁止启动/停止/重载 CCC 服务。
- 禁止调用 `/api/relay/start`、`/api/relay/stop` 或启动真实 A/B/C 自动发送循环。
- 禁止运行 `npm run dev`、`npm run build`、`npm run verify`。
- 禁止运行前端/后端测试，除非只是读取历史日志中已有结果。
- 禁止 `git add`、commit、push、PR、tag、发布、生产联调、ERPNext 生产写入。
- 禁止清理、删除、回滚、还原 untracked 或 dirty diff。

执行步骤：
1. 核对控制面：
   - 确认当前为 `READY_FOR_BUILD / B Engineer / TASK-165A`。
   - 确认 `TASK-164I` 已关闭且不可回放。
   - 确认 `TASK-152A / TASK-090I / TASK-110B` 仍为 parked blockers。
2. 核对当前 worktree 只读事实：
   - tracked diff 数量与清单。
   - untracked 数量。
   - `TASK-164A` baseline 与 `TASK-164I` 总账结论是否仍可作为后续审计参考。
3. 输出“整体开发进度梳理”：
   - 已关闭设计/docs 主链。
   - 已关闭 CCC 自动接力治理链。
   - 已关闭 164 dirty diff 归口链。
   - 已归口的业务/配置模块列表。
   - 仍未放行的 blocker 列表与原因。
4. 输出“长期循环协议”：
   - 新事实触发条件：新用户方向、新 TASK_ID、新审批事实、新 git diff、新验证失败、新 blocker 状态变化、新主队列。
   - 静默停止条件：重复 PASS、重复 IDLE、重复 A/NONE、过期 relay、空包、已关闭 TASK_ID 回声、无新文件/无新验证/无 blocker 变化。
   - A/B/C 分工：A 只派单与控面，B 只执行任务单，C 只结构化审计。
   - C 输出必须为 `AUDIT_RESULT: PASS/FIX/BLOCK` 结构化格式，禁止裸 `PASS`。
5. 输出“候选任务池与优先级”：
   - 本地安全 docs/control 任务。
   - 已审计 dirty diff 的提交候选分组任务。
   - 新业务代码任务触发条件。
   - 外部审批/管理员/生产联调类任务触发条件。
   - 不得推进的 parked blockers。
6. 输出“提交候选分组”：
   - 只分组，不 stage，不 commit。
   - 按已审计归口链将 dirty diff 分为：控制/文档流、CCC 工具链、开发配置、前端 contract/request、factory statement、sales inventory、warehouse、production、router/HomePage/quality、后端白名单、审计/任务报告。
   - 明确哪些 untracked 属任务/审计文档，哪些仍不得默认纳入提交。
7. 输出“下一步默认建议”：
   - 只能从以下值中选择一个：
     - `ALLOW_A_TO_DISPATCH_TASK165B_COMMIT_CANDIDATE_GROUP_AUDIT`
     - `ALLOW_A_TO_DISPATCH_TASK165B_RELEASE_PRECHECK_DOCS_ONLY`
     - `BLOCKED_BY_USER_APPROVAL_FOR_STAGE_COMMIT_PUSH`
     - `NO_LEGAL_LOCAL_B_TASK`
   - 必须说明选择理由。

必须验证：
- `git -C '/Users/hh/Desktop/领意服装管理系统' status --short --branch`
- `git -C '/Users/hh/Desktop/领意服装管理系统' diff --name-only | wc -l`
- `git -C '/Users/hh/Desktop/领意服装管理系统' ls-files --others --exclude-standard | wc -l`
- `git -C '/Users/hh/Desktop/领意服装管理系统' diff --stat`
- `git -C '/Users/hh/Desktop/领意服装管理系统' diff --check -- '03_需求与设计/02_开发计划/TASK-165A_长期循环主线总控与提交候选分组报告.md' '03_需求与设计/02_开发计划/工程师会话日志.md'`

报告必须包含字段：
- `CURRENT_CONTROL_PLANE`
- `OVERALL_PROGRESS_SUMMARY`
- `CLOSED_CHAINS`
- `PARKED_BLOCKERS`
- `DIRTY_WORKTREE_LEDGER`
- `LONG_LOOP_PROTOCOL`
- `NOISE_SUPPRESSION_RULES`
- `NEXT_FACT_TRIGGERS`
- `COMMIT_CANDIDATE_GROUPS`
- `NEXT_QUEUE_CANDIDATES`
- `DEFAULT_NEXT_ACTION`
- `VALIDATION`
- `RISK_NOTES`

回交格式：

STATUS: READY_FOR_REVIEW
TASK_ID: TASK-165A
ROLE: B Engineer

CHANGED_FILES:
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-165A_长期循环主线总控与提交候选分组报告.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md`

CODE_CHANGED:
- NO

OVERALL_PROGRESS_SUMMARY:
- ...

LONG_LOOP_PROTOCOL_RESULT:
- ...

COMMIT_CANDIDATE_RESULT:
- ...

DEFAULT_NEXT_ACTION:
- `ALLOW_A_TO_DISPATCH_TASK165B_COMMIT_CANDIDATE_GROUP_AUDIT` 或 `ALLOW_A_TO_DISPATCH_TASK165B_RELEASE_PRECHECK_DOCS_ONLY` 或 `BLOCKED_BY_USER_APPROVAL_FOR_STAGE_COMMIT_PUSH` 或 `NO_LEGAL_LOCAL_B_TASK`

VALIDATION:
- ...

RISK_NOTES:
- ...

NEXT_ROLE: A Technical Architect
BLOCKERS:
- NONE 或具体 blocker
```
