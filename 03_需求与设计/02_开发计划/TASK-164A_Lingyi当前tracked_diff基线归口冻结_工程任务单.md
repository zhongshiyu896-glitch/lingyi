# TASK-164A Lingyi当前tracked diff基线归口冻结

STATUS: READY_FOR_BUILD
TASK_ID: TASK-164A
ROLE: B Engineer

## 任务

只读盘点 `/Users/hh/Desktop/领意服装管理系统` 当前 tracked diff baseline，并形成归口冻结报告，解决 `vite.config.ts` 与其他既有 tracked diff 在后续审计中反复被误判为当前任务范围风险的问题。

本任务是 docs-only/read-only 归口任务，不是代码实现任务、不是清理任务、不是回滚任务。

## 背景

- `TASK-163A` 已由 C 返回 `AUDIT_RESULT: PASS`，A 已关闭。
- C 残余风险指出：`vite.config.ts` 及其他既有前端 tracked diff 仍需 A 另行归口处理。
- A 只读核对当前仓存在约 40 个 tracked diff，且 untracked 面很大。后续任务如果不冻结 baseline，C 会继续把既有 dirty worktree 误判为当前任务改动。

## 允许修改

- 新增归口冻结报告：
  - `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-164A_Lingyi当前tracked_diff基线归口冻结报告.md`
- 追加工程师会话日志：
  - `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md`

## 禁止修改

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/vite.config.ts`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/**`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/**`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/**`
- `/Users/hh/Desktop/ccc/**`
- `/Users/hh/Documents/Playground 2/LOOP_STATE.md`
- `/Users/hh/Documents/Playground 2/TASK_BOARD.md`
- `/Users/hh/Documents/Playground 2/HANDOVER_STATUS.md`
- `/Users/hh/Documents/Playground 2/INTERVENTION_QUEUE.md`
- `/Users/hh/Documents/Playground 2/AUTO_LOOP_PROTOCOL.md`
- `/Users/hh/.codex/AGENTS.md`
- `/Users/hh/Documents/Playground 2/AGENTS.md`
- `/Users/hh/Desktop/领意服装管理系统/00_交接与日志/HANDOVER_STATUS.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/架构师会话日志.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录/**`
- `.gitignore`
- 任何生产/GitHub 管理配置

## 禁止动作

- 禁止清理、删除、回滚、还原、格式化任何现有 diff。
- 禁止运行前端命令：`npm` / `pnpm` / `yarn` / `vite` / `typecheck` / `build`。
- 禁止运行后端测试或会写缓存的业务命令。
- 禁止启动、停止、重载 CCC server。
- 禁止调用 `/api/relay/start` 或 `/api/relay/stop`。
- 禁止 push / PR / tag / 发布。
- 禁止把本任务结论外推为 REL-004/REL-005、生产联调、GitHub 管理配置、ERPNext 生产写入或 Lingyi 业务功能放行。

## 必须执行的只读核对

1. 记录当前 tracked diff 总数：
   - `git -C '/Users/hh/Desktop/领意服装管理系统' diff --name-only | wc -l`
2. 记录 tracked diff 清单：
   - `git -C '/Users/hh/Desktop/领意服装管理系统' diff --name-only`
3. 记录简要 diff stat：
   - `git -C '/Users/hh/Desktop/领意服装管理系统' diff --stat`
4. 单独核对 `vite.config.ts`：
   - `git -C '/Users/hh/Desktop/领意服装管理系统' diff -- '06_前端/lingyi-pc/vite.config.ts'`
   - `stat -f '%Sm %N' -t '%Y-%m-%d %H:%M:%S %z' '/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/vite.config.ts'`
5. 对 tracked diff 做归口分类：
   - `CONTROL_PLANE_OR_A_FLOW`：A 本轮或控制面流转文件。
   - `HISTORICAL_TASK_OUTPUT`：可从工程师/架构师/审计日志或任务报告追溯到既有 TASK 的文件。
   - `BUSINESS_CODE_TRACKED_DIFF_NEEDS_OWNER`：业务前后端源码/测试等仍需后续归口的 tracked diff。
   - `DEV_CONFIG_TRACKED_DIFF_NEEDS_OWNER`：如 `vite.config.ts`。
   - `UNKNOWN_OR_UNOWNED`：无法从现有日志归因的 diff。
6. 只统计 untracked 面，不展开大清单：
   - `git -C '/Users/hh/Desktop/领意服装管理系统' ls-files --others --exclude-standard | wc -l`
   - 按顶层目录聚合数量即可。

## 报告必须包含

在 `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-164A_Lingyi当前tracked_diff基线归口冻结报告.md` 中写明：

- 当前 tracked diff 总数。
- 当前 untracked 文件数量与顶层目录聚合。
- tracked diff 分类表，至少包含：
  - path
  - category
  - suspected_owner_or_source_task
  - evidence
  - next_action
- 对 `vite.config.ts` 的单独归口结论：
  - 当前 diff 内容摘要。
  - mtime。
  - 是否能归因到 TASK-157A~TASK-163A：预期为不能，除非只读证据相反。
  - 后续建议：开独立实现/审计任务、保留隔离、或需要 A 再裁决。
- 明确哪些 diff 只是当前 A/B/C 流转文件，不应在后续业务任务中重复当作 B 违规证据。
- 明确哪些 diff 仍不能放行，需要后续 TASK 继续处理。
- 明确本任务没有清理、回滚、修改任何既有 diff。

## 验证

本任务不要求运行代码测试。

必须验证：

- `git -C '/Users/hh/Desktop/领意服装管理系统' diff --name-only -- '03_需求与设计/02_开发计划/TASK-164A_Lingyi当前tracked_diff基线归口冻结报告.md' '03_需求与设计/02_开发计划/工程师会话日志.md'`
- 确认实际修改文件只包含允许的两类文件。
- 确认 `vite.config.ts` 未被本任务修改：记录本任务前后 mtime 或说明只读未写。

## REPORT_BACK_FORMAT

```text
STATUS: READY_FOR_REVIEW
TASK_ID: TASK-164A
ROLE: B Engineer

CHANGED_FILES:
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-164A_Lingyi当前tracked_diff基线归口冻结报告.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md

CODE_CHANGED:
- NO

TRACKED_DIFF_BASELINE:
- tracked_diff_count: ...
- untracked_count: ...
- categories:
  - CONTROL_PLANE_OR_A_FLOW: ...
  - HISTORICAL_TASK_OUTPUT: ...
  - BUSINESS_CODE_TRACKED_DIFF_NEEDS_OWNER: ...
  - DEV_CONFIG_TRACKED_DIFF_NEEDS_OWNER: ...
  - UNKNOWN_OR_UNOWNED: ...

VITE_CONFIG_ATTRIBUTION:
- mtime: ...
- diff_summary: ...
- related_to_TASK_157A_163A: YES/NO/INCONCLUSIVE
- recommended_next_action: ...

VALIDATION:
- only_allowed_files_changed: YES/NO
- vite_config_touched_in_TASK_164A: NO
- frontend_commands_run: NO
- backend_tests_run: NO
- ccc_start_stop_or_reload: NO

RISK_NOTES:
- ...

NEXT_ROLE: A Technical Architect
BLOCKERS:
- NONE 或具体阻塞
```
