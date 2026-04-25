# TASK-164B 开发配置tracked diff安全收敛

STATUS: READY_FOR_BUILD
TASK_ID: TASK-164B
ROLE: B Engineer

## 任务

处理 `TASK-164A` 已冻结 baseline 中的两个配置类 tracked diff：

1. `.gitignore` 的 `UNKNOWN_OR_UNOWNED`
2. `06_前端/lingyi-pc/vite.config.ts` 的 `DEV_CONFIG_TRACKED_DIFF_NEEDS_OWNER`

目标是完成最小安全收敛：

- 保留本地运行态/本地 SQLite DB 忽略意图。
- 将 Vite dev proxy 的开发身份 header 注入改为显式 opt-in。
- 禁止默认注入任何用户或角色，尤其禁止默认注入 `System Manager`。

## 背景

`TASK-164A` 已由 C 审计通过，确认当前 40 个 tracked diff baseline 可作为后续审计参考，但 dirty worktree 仍未清理、未放行。

当前相关 diff：

- `.gitignore`
  - 新增 `.local_runtime/`
  - 新增 `07_后端/lingyi_service/lingyi_service.local.db`
- `vite.config.ts`
  - 新增 `VITE_LINGYI_DEV_USER / VITE_LINGYI_DEV_ROLES`
  - 新增 dev proxy 请求头 `X-LY-Dev-User / X-LY-Dev-Roles`
  - 当前问题：默认值为 `local.dev / System Manager`，会在开发代理下默认注入高权限身份。

## 允许修改

- `/Users/hh/Desktop/领意服装管理系统/.gitignore`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/vite.config.ts`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md`

## 禁止修改

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
- 任何业务前后端代码、测试、生产/GitHub 管理配置

## 禁止动作

- 禁止清理、删除、回滚、还原其他既有 diff。
- 禁止运行前端命令：`npm` / `pnpm` / `yarn` / `vite` / `typecheck` / `build` / `dev`。
- 禁止运行后端测试或会写缓存的业务命令。
- 禁止启动、停止、重载 CCC server。
- 禁止调用 `/api/relay/start` 或 `/api/relay/stop`。
- 禁止 push / PR / tag / 发布。
- 禁止把本任务结论外推为 REL-004/REL-005、生产联调、GitHub 管理配置、ERPNext 生产写入或业务功能放行。

## 实现要求

### `.gitignore`

1. 保留或整理以下忽略项：
   - `.local_runtime/`
   - `07_后端/lingyi_service/lingyi_service.local.db`
2. 不得删除既有忽略项。
3. 不得批量添加无关忽略规则。

### `vite.config.ts`

1. 保留 dev proxy header 注入能力，但必须显式 opt-in。
2. 新增一个明确开关，建议命名：
   - `VITE_LINGYI_DEV_AUTH_HEADERS=true`
3. 只有当 `VITE_LINGYI_DEV_AUTH_HEADERS === 'true'` 且对应值非空时，才允许设置：
   - `X-LY-Dev-User`
   - `X-LY-Dev-Roles`
4. `VITE_LINGYI_DEV_USER` 不得有默认值。
5. `VITE_LINGYI_DEV_ROLES` 不得有默认值。
6. 禁止默认注入 `System Manager`。
7. 禁止默认注入 `local.dev`。
8. 如果开关未启用，proxy 不得设置任何 `X-LY-Dev-*` header。
9. 保持 `VITE_API_PROXY_TARGET` 现有语义不变。

## 必须验证

只允许静态验证，不运行前端/后端命令。

必须执行：

1. 语法/格式静态检查：
   - `git -C '/Users/hh/Desktop/领意服装管理系统' diff --check -- '.gitignore' '06_前端/lingyi-pc/vite.config.ts'`
2. 内容断言：
   - `rg "VITE_LINGYI_DEV_AUTH_HEADERS" '/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/vite.config.ts'`
   - `rg "System Manager|local.dev" '/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/vite.config.ts'` 必须无命中
   - `rg "X-LY-Dev-User|X-LY-Dev-Roles" '/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/vite.config.ts'`
   - `rg "lingyi_service.local.db|\\.local_runtime/" '/Users/hh/Desktop/领意服装管理系统/.gitignore'`
3. 范围核对：
   - `git -C '/Users/hh/Desktop/领意服装管理系统' diff --name-only -- '.gitignore' '06_前端/lingyi-pc/vite.config.ts' '03_需求与设计/02_开发计划/工程师会话日志.md'`
   - 回交中明确未修改其他文件。

## 工程师日志

完成后追加到：

`/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md`

记录：

- `TASK-164B`
- `.gitignore` 处理结论
- `vite.config.ts` 安全收敛结论
- 是否仍默认注入 `System Manager`: 必须为 `NO`
- 是否默认注入 `local.dev`: 必须为 `NO`
- 是否运行前端命令：必须为 `NO`
- 是否运行后端测试：必须为 `NO`
- 是否触碰业务源码/测试/CCC/控制面：必须为 `NO`

## REPORT_BACK_FORMAT

```text
STATUS: READY_FOR_REVIEW
TASK_ID: TASK-164B
ROLE: B Engineer

CHANGED_FILES:
- /Users/hh/Desktop/领意服装管理系统/.gitignore
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/vite.config.ts
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md

IMPLEMENTATION_SUMMARY:
- ...

DEV_AUTH_HEADER_BEHAVIOR:
- opt_in_env: VITE_LINGYI_DEV_AUTH_HEADERS
- default_injects_headers: NO
- default_user: NONE
- default_roles: NONE
- system_manager_default_removed: YES
- local_dev_default_removed: YES

GITIGNORE_RESULT:
- local_runtime_ignored: YES/NO
- local_sqlite_db_ignored: YES/NO
- unrelated_ignore_rules_added: NO

VALIDATION:
- git diff --check: PASS/FAIL
- VITE_LINGYI_DEV_AUTH_HEADERS present: YES/NO
- System Manager/local.dev no longer in vite.config.ts: YES/NO
- X-LY-Dev headers still supported behind opt-in: YES/NO
- .gitignore local runtime/db rules present: YES/NO

RISK_NOTES:
- 未运行前端命令
- 未运行后端测试
- 未修改业务前后端源码/测试
- 未触碰 CCC、控制面、AGENTS、架构师日志、审计官日志、生产/GitHub 管理配置
- 不代表 REL-004/REL-005、生产联调、ERPNext 生产写入或业务功能放行

NEXT_ROLE: A Technical Architect
BLOCKERS:
- NONE 或具体阻塞
```
