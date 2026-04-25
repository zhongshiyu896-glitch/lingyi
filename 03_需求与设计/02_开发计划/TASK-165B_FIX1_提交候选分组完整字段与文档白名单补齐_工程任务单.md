# TASK-165B FIX1 提交候选分组完整字段与文档白名单补齐工程任务单

```text
STATUS: READY_FOR_BUILD
TASK_ID: TASK-165B
FIX_PASS: FIX1
ROLE: B Engineer

任务：提交候选分组完整字段与文档白名单补齐

背景：
- C 对 `TASK-165B` 返回结构化 `AUDIT_RESULT: FIX`。
- 原 `TASK-165B` 不关闭，不进入 `TASK-165C`。
- 本轮只修正 `TASK-165B` 报告，使其成为可审计的提交候选分组白名单输入。

C FINDINGS 必须逐条修复：
1. 报告未显式包含完整字段名：
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
2. `CANDIDATE_GROUP_DOCS_CONTROL` 与 `CANDIDATE_GROUP_AUDIT_TASK_REPORTS` 不能再使用“代表性最小集合”“示例”“必须继续细化到单文件”口径，必须改为完整单文件白名单。
3. 未来 staging 模板 H/I 不能再是示例模板；必须给出完整显式路径模板，或将不能完整冻结的条目标记为 `NOT_STAGE_CANDIDATE_YET` 并把 `DEFAULT_NEXT_ACTION` 改为 `FIX_REQUIRED_FOR_CANDIDATE_GROUP_LEDGER`。
4. 复核并更新当前 dirty ledger 数字，注明 A/C 派审后新增审计任务单导致的 untracked 计数变化。

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
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-165B_提交候选分组审计前置白名单冻结_工程任务单.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-165B_提交候选分组审计前置白名单冻结报告.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录/TASK-165B_提交候选分组审计前置白名单冻结_C审计任务单.md`
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
- `/Users/hh/Desktop/领意服装管理系统/.gitignore`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/vite.config.ts`
- 生产/GitHub 管理配置

禁止动作：
- 禁止执行 `git add`、`git commit`、`git push`、PR、tag、发布。
- 禁止运行 `git restore`、`git reset`、`git checkout --`、清理、删除、回滚、还原 dirty/untracked。
- 禁止写业务代码、后端代码、测试代码、CCC 代码。
- 禁止运行前端/后端测试、`npm run dev/build/verify`、typecheck、contract check。
- 禁止启动/停止/重载 CCC。
- 禁止调用 `/api/relay/start`、`/api/relay/stop`。
- 禁止把 parked blockers 当作已放行。

执行要求：
1. 仅修正原报告，不新建替代报告。
2. 报告必须包含并可被 `rg` 直接检索到以下字段名：
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
3. `CANDIDATE_GROUP_DOCS_CONTROL` 必须给出完整单文件白名单。每个文件必须包含：
   - 绝对路径
   - 归口 TASK_ID 或来源
   - C PASS 或任务来源锚点
   - `STAGE_CANDIDATE: YES/NO/NOT_STAGE_CANDIDATE_YET`
   - 风险说明
4. `CANDIDATE_GROUP_AUDIT_TASK_REPORTS` 必须给出完整单文件白名单。每个文件必须包含：
   - 绝对路径
   - 归口 TASK_ID 或来源
   - C PASS 或任务来源锚点
   - `STAGE_CANDIDATE: YES/NO/NOT_STAGE_CANDIDATE_YET`
   - 风险说明
5. 若任意文档项无法完整冻结：
   - 将该项标记为 `NOT_STAGE_CANDIDATE_YET`
   - 将 `DEFAULT_NEXT_ACTION` 改为 `FIX_REQUIRED_FOR_CANDIDATE_GROUP_LEDGER`
   - 不得建议进入 `TASK-165C`
6. `FUTURE_STAGE_TEMPLATES_NOT_EXECUTED` 中所有模板必须满足：
   - 仅供未来 A 明确授权后使用，本任务禁止执行
   - 只允许逐文件显式路径
   - 禁止出现 `git add .`
   - 禁止出现 `git add -A`
   - 禁止出现目录级 `git add <目录>`
   - H/I 模板不得再是示例，必须与白名单单文件清单一一对应；否则把对应文件标记为 `NOT_STAGE_CANDIDATE_YET`
7. 更新 `DIRTY_LEDGER`：
   - tracked diff count
   - untracked count
   - TASK-164/TASK-165/HomePage.vue 相关 untracked count
   - 明确 A/C 派审后新增 C 审计任务单导致的 untracked 计数变化
8. `BLOCKER_STATUS` 必须明确：
   - `TASK-152A` 仍 parked
   - `TASK-090I` 仍 parked
   - `TASK-110B` 仍 parked
   - 本任务不释放任何 parked blocker

必须验证：
- `git -C '/Users/hh/Desktop/领意服装管理系统' status --short --branch`
- `git -C '/Users/hh/Desktop/领意服装管理系统' diff --name-only | wc -l`
- `git -C '/Users/hh/Desktop/领意服装管理系统' ls-files --others --exclude-standard | wc -l`
- `git -c core.quotePath=false -C '/Users/hh/Desktop/领意服装管理系统' ls-files --others --exclude-standard | rg 'TASK-164|TASK-165|HomePage.vue' | wc -l`
- `rg -n 'CURRENT_CONTROL_PLANE|TASK_165A_PASS_ANCHOR|DIRTY_LEDGER|TRACKED_DIFF_GROUPS|UNTRACKED_GROUPS|CANDIDATE_GROUPS|EXCLUSION_LIST|FUTURE_STAGE_TEMPLATES_NOT_EXECUTED|BLOCKER_STATUS|VALIDATION|DEFAULT_NEXT_ACTION|RISK_NOTES' '/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-165B_提交候选分组审计前置白名单冻结报告.md'`
- `rg -n '代表性最小集合|示例，必须继续细化到单文件|必须继续细化到单文件' '/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-165B_提交候选分组审计前置白名单冻结报告.md'` 必须无命中；如有命中，只能出现在“原 C finding 已修复说明”中，且不得作为当前候选组口径。
- `rg -n 'git add \\.|git add -A|git add [^\\n]*/$' '/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-165B_提交候选分组审计前置白名单冻结报告.md'` 不得命中未来可执行模板；如命中，只能出现在禁止说明中。
- `git -C '/Users/hh/Desktop/领意服装管理系统' diff --check -- '03_需求与设计/02_开发计划/TASK-165B_提交候选分组审计前置白名单冻结报告.md' '03_需求与设计/02_开发计划/工程师会话日志.md'`

回交格式：

STATUS: READY_FOR_REVIEW
TASK_ID: TASK-165B
FIX_PASS: FIX1
ROLE: B Engineer

CHANGED_FILES:
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-165B_提交候选分组审计前置白名单冻结报告.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md`

CODE_CHANGED_IN_FIX1:
- NO

FIELDS_COMPLETED:
- `CURRENT_CONTROL_PLANE`: YES/NO
- `TASK_165A_PASS_ANCHOR`: YES/NO
- `DIRTY_LEDGER`: YES/NO
- `TRACKED_DIFF_GROUPS`: YES/NO
- `UNTRACKED_GROUPS`: YES/NO
- `CANDIDATE_GROUPS`: YES/NO
- `EXCLUSION_LIST`: YES/NO
- `FUTURE_STAGE_TEMPLATES_NOT_EXECUTED`: YES/NO
- `BLOCKER_STATUS`: YES/NO
- `VALIDATION`: YES/NO
- `DEFAULT_NEXT_ACTION`: YES/NO
- `RISK_NOTES`: YES/NO

DOCS_CONTROL_WHITELIST_RESULT:
- complete_single_file_whitelist: YES/NO
- not_stage_candidate_items: ...

AUDIT_TASK_REPORTS_WHITELIST_RESULT:
- complete_single_file_whitelist: YES/NO
- not_stage_candidate_items: ...

FUTURE_STAGE_TEMPLATES_RESULT:
- explicit_single_file_paths_only: YES/NO
- no_git_add_dot_or_add_A: YES/NO
- templates_h_i_complete_or_downgraded: YES/NO

DIRTY_LEDGER_RESULT:
- tracked_diff_count: ...
- untracked_count: ...
- task164_165_homepage_untracked_count: ...
- ac_audit_task_delta_explained: YES/NO

DEFAULT_NEXT_ACTION:
- `ALLOW_A_TO_DISPATCH_TASK165C_C_AUDIT_COMMIT_CANDIDATE_GROUPS`
  或 `FIX_REQUIRED_FOR_CANDIDATE_GROUP_LEDGER`
  或 `BLOCKED_BY_UNOWNED_UNTRACKED_OR_DIFF_CONFLICT`
  或 `BLOCKED_BY_USER_APPROVAL_FOR_STAGE_COMMIT_PUSH`

VALIDATION:
- ...

RISK_NOTES:
- ...

NEXT_ROLE: A Technical Architect
BLOCKERS:
- NONE 或具体 blocker
```
