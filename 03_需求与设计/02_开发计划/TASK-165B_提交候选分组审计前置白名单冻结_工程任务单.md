# TASK-165B 提交候选分组审计前置白名单冻结工程任务单

```text
STATUS: READY_FOR_BUILD
TASK_ID: TASK-165B
ROLE: B Engineer

任务：提交候选分组审计前置白名单冻结

背景：
- `TASK-165A` 已由 C 返回结构化 `AUDIT_RESULT: PASS`。
- `TASK-165A` 的审计通过范围仅证明长期循环主线总控报告合格，不代表 stage/commit/push/PR/tag/发布放行。
- 当前 worktree 仍为大规模 dirty baseline。下一步必须先把“未来可能提交的候选组”和“必须排除的文件/目录”冻结成可审计白名单，避免后续误用 `git add .` 或把无关 untracked 纳入提交。

目标：
以只读/docs-only 方式输出一份提交候选分组审计前置白名单冻结报告，为后续 A/C 判断是否进入实际 stage/commit 链提供精确输入。当前任务只做分组、白名单、排除清单、风险与后续门禁，不执行任何 git stage/commit/push。

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
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-165A_长期循环主线总控与提交候选分组报告.md`
- `TASK-164B~164I` 相关 C 审计任务单与报告（只读抽取 PASS 链与文件归口）
- 最新架构师/工程师/审计官会话日志尾部

允许修改：
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-165B_提交候选分组审计前置白名单冻结报告.md`
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
- 禁止执行 `git add`、`git commit`、`git push`、PR、tag、发布。
- 禁止运行 `git restore`、`git reset`、`git checkout --`、清理、删除、回滚、还原 dirty/untracked。
- 禁止写业务代码、后端代码、测试代码、CCC 代码。
- 禁止启动/停止/重载 CCC。
- 禁止调用 `/api/relay/start`、`/api/relay/stop`。
- 禁止运行 `npm run dev/build/verify`。
- 禁止运行前端/后端测试；本任务只读核对历史验证证据。
- 禁止把 parked blockers 当作已放行。

执行步骤：
1. 核对控制面：
   - 确认为 `READY_FOR_BUILD / B Engineer / TASK-165B`。
   - 确认 `TASK-165A` 已由 C 结构化 PASS。
   - 确认 `TASK-152A / TASK-090I / TASK-110B` 继续 parked。
2. 生成当前 dirty ledger：
   - tracked diff 完整清单。
   - untracked 总数。
   - TASK-164/TASK-165 相关 untracked 清单。
   - 明确哪些是业务代码、哪些是任务/审计文档、哪些应排除。
3. 输出提交候选组，不执行提交：
   - `CANDIDATE_GROUP_DOCS_CONTROL`
   - `CANDIDATE_GROUP_CONFIG`
   - `CANDIDATE_GROUP_FRONTEND_CONTRACT_REQUEST`
   - `CANDIDATE_GROUP_FACTORY_STATEMENT`
   - `CANDIDATE_GROUP_SALES_INVENTORY`
   - `CANDIDATE_GROUP_WAREHOUSE`
   - `CANDIDATE_GROUP_PRODUCTION`
   - `CANDIDATE_GROUP_ROUTER_HOMEPAGE_QUALITY`
   - `CANDIDATE_GROUP_BACKEND_SHARED`
   - `CANDIDATE_GROUP_AUDIT_TASK_REPORTS`
4. 对每组输出：
   - 文件清单（绝对路径）。
   - 归口来源 TASK_ID。
   - C 审计 PASS 锚点。
   - 建议是否可进入后续 stage 候选。
   - 是否包含 untracked。
   - 风险说明。
5. 输出明确排除清单：
   - 大规模 untracked 目录/缓存/探针/临时文件。
   - 未被 TASK-164/165 归口的 untracked。
   - 任意 node_modules/dist/.vite/cache/__pycache__/.pytest_cache 等缓存。
   - 任意生产/GitHub 管理配置。
6. 输出未来 staging 模板：
   - 只能给“命令模板”，不得执行。
   - 模板必须使用显式路径，不得出现 `git add .`、`git add -A`、`git add 目录/` 这类宽泛命令。
   - 每个模板前必须标注：`仅供未来 A 授权后使用，本任务禁止执行`。
7. 输出后续推荐：
   - 只能从以下值选择一个：
     - `ALLOW_A_TO_DISPATCH_TASK165C_C_AUDIT_COMMIT_CANDIDATE_GROUPS`
     - `FIX_REQUIRED_FOR_CANDIDATE_GROUP_LEDGER`
     - `BLOCKED_BY_UNOWNED_UNTRACKED_OR_DIFF_CONFLICT`
     - `BLOCKED_BY_USER_APPROVAL_FOR_STAGE_COMMIT_PUSH`

必须验证：
- `git -C '/Users/hh/Desktop/领意服装管理系统' status --short --branch`
- `git -C '/Users/hh/Desktop/领意服装管理系统' diff --name-only`
- `git -C '/Users/hh/Desktop/领意服装管理系统' diff --name-only | wc -l`
- `git -C '/Users/hh/Desktop/领意服装管理系统' ls-files --others --exclude-standard | wc -l`
- `git -C '/Users/hh/Desktop/领意服装管理系统' ls-files --others --exclude-standard | rg 'TASK-164|TASK-165|HomePage.vue'`
- `git -C '/Users/hh/Desktop/领意服装管理系统' diff --stat`
- `git -C '/Users/hh/Desktop/领意服装管理系统' diff --check -- '03_需求与设计/02_开发计划/TASK-165B_提交候选分组审计前置白名单冻结报告.md' '03_需求与设计/02_开发计划/工程师会话日志.md'`

报告必须包含字段：
- `CURRENT_CONTROL_PLANE`
- `TASK_165A_PASS_ANCHOR`
- `DIRTY_LEDGER`
- `TRACKED_DIFF_GROUPS`
- `UNTRACKED_GROUPS`
- `CANDIDATE_GROUPS`
- `EXCLUSION_LIST`
- `FUTURE_STAGE_TEMPLATES_NOT_EXECUTED`
- `BLOCKER_STATUS`
- `VALIDATION`
- `DEFAULT_NEXT_ACTION`
- `RISK_NOTES`

回交格式：

STATUS: READY_FOR_REVIEW
TASK_ID: TASK-165B
ROLE: B Engineer

CHANGED_FILES:
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-165B_提交候选分组审计前置白名单冻结报告.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md`

CODE_CHANGED:
- NO

COMMIT_CANDIDATE_SUMMARY:
- ...

EXCLUSION_SUMMARY:
- ...

FUTURE_STAGE_TEMPLATES_NOT_EXECUTED:
- ...

DEFAULT_NEXT_ACTION:
- `ALLOW_A_TO_DISPATCH_TASK165C_C_AUDIT_COMMIT_CANDIDATE_GROUPS` 或 `FIX_REQUIRED_FOR_CANDIDATE_GROUP_LEDGER` 或 `BLOCKED_BY_UNOWNED_UNTRACKED_OR_DIFF_CONFLICT` 或 `BLOCKED_BY_USER_APPROVAL_FOR_STAGE_COMMIT_PUSH`

VALIDATION:
- ...

RISK_NOTES:
- ...

NEXT_ROLE: A Technical Architect
BLOCKERS:
- NONE 或具体 blocker
```
