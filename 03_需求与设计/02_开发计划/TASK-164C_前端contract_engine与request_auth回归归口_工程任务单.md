# TASK-164C 前端contract engine与request auth回归归口

STATUS: READY_FOR_BUILD
TASK_ID: TASK-164C
ROLE: B Engineer

## 任务

对 `TASK-164A` baseline 中的前端 contract engine 与 request auth 三文件做定向回归验证、必要最小修复与归口冻结。

本任务只覆盖以下 3 个 tracked diff：

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/frontend-contract-engine.mjs`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-frontend-contract-engine.mjs`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/request.ts`

## 背景

- `TASK-164B` 已由 C 返回 `AUDIT_RESULT: PASS`，开发配置安全收敛完成。
- 剩余 business tracked diff 尚未归口完成。
- 本组三文件对应历史任务：
  - `TASK-153C`：前端 contract engine 同步数组迭代 callback sink 及 call/apply/Reflect.apply/bind 等价调用恢复。
  - `TASK-153F`：`src/api/request.ts` 鉴权请求头规范化回写 `Authorization`。
- 历史日志显示曾通过：
  - `npm run test:frontend-contract-engine`
  - `npm run test:style-profit-contracts`
  - `npm run check:style-profit-contracts`
  - `npm run typecheck`

## 允许修改

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/frontend-contract-engine.mjs`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-frontend-contract-engine.mjs`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/request.ts`
- 新增归口冻结报告：
  - `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-164C_前端contract_engine与request_auth回归归口报告.md`
- 追加工程师会话日志：
  - `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md`

## 禁止修改

- `/Users/hh/Desktop/领意服装管理系统/.gitignore`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/vite.config.ts`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/**` 中除 `src/api/request.ts` 之外的任何文件
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/**` 中除上述两个 scripts 文件之外的任何文件
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
- 任何生产/GitHub 管理配置

## 禁止动作

- 禁止清理、删除、回滚、还原其他既有 diff。
- 禁止运行 `npm run dev`。
- 禁止运行 `npm run build`。
- 禁止运行全量 `npm run verify`。
- 禁止运行后端测试。
- 禁止启动、停止、重载 CCC server。
- 禁止调用 `/api/relay/start` 或 `/api/relay/stop`。
- 禁止 push / PR / tag / 发布。
- 禁止把本任务结论外推为剩余 business tracked diff 放行、dirty worktree 清理完成、REL-004/REL-005、生产联调、GitHub 管理配置、ERPNext 生产写入或业务功能放行。

## 执行要求

1. 先只读核对三文件 diff：
   - `git -C '/Users/hh/Desktop/领意服装管理系统' diff -- '06_前端/lingyi-pc/scripts/frontend-contract-engine.mjs' '06_前端/lingyi-pc/scripts/test-frontend-contract-engine.mjs' '06_前端/lingyi-pc/src/api/request.ts'`
2. 执行定向验证：
   - 在 `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc` 下运行：
     - `npm run test:frontend-contract-engine`
     - `npm run check:style-profit-contracts`
     - `npm run test:style-profit-contracts`
     - `npm run typecheck`
3. 如验证全部通过：
   - 不修改三文件代码。
   - 新增归口冻结报告并追加工程师日志。
4. 如验证失败：
   - 先判断失败是否落在本任务 3 文件范围内。
   - 仅当失败可归因到这 3 文件时，允许在这 3 文件内做最小修复。
   - 若失败来自其他 dirty diff、依赖、环境、后端或非白名单文件，禁止扩大修改范围，回交 `BLOCKERS` 或 `RISK_NOTES`。

## 报告必须包含

在 `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-164C_前端contract_engine与request_auth回归归口报告.md` 中写明：

- 三文件 diff 摘要。
- 与 `TASK-153C / TASK-153F` 的归属关系。
- 每条验证命令结果。
- 若有修复，说明修复是否仅限 3 文件。
- 是否可将这三文件从 `BUSINESS_CODE_TRACKED_DIFF_NEEDS_OWNER` 收敛为 `HISTORICAL_TASK_OUTPUT_VERIFIED`。
- 明确本任务不覆盖 factory-statement / sales-inventory / warehouse / production / backend 等其他 business diff。

## 必须验证

- `git -C '/Users/hh/Desktop/领意服装管理系统' diff --check -- '06_前端/lingyi-pc/scripts/frontend-contract-engine.mjs' '06_前端/lingyi-pc/scripts/test-frontend-contract-engine.mjs' '06_前端/lingyi-pc/src/api/request.ts'`
- `git -C '/Users/hh/Desktop/领意服装管理系统' diff --name-only -- '06_前端/lingyi-pc/scripts/frontend-contract-engine.mjs' '06_前端/lingyi-pc/scripts/test-frontend-contract-engine.mjs' '06_前端/lingyi-pc/src/api/request.ts' '03_需求与设计/02_开发计划/TASK-164C_前端contract_engine与request_auth回归归口报告.md' '03_需求与设计/02_开发计划/工程师会话日志.md'`
- 确认未修改禁止范围文件。

## REPORT_BACK_FORMAT

```text
STATUS: READY_FOR_REVIEW
TASK_ID: TASK-164C
ROLE: B Engineer

CHANGED_FILES:
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-164C_前端contract_engine与request_auth回归归口报告.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md
- 如确有本任务内修复，再列出三文件中的实际修改文件

CODE_CHANGED:
- YES/NO

SCOPE_FILES:
- frontend-contract-engine.mjs
- test-frontend-contract-engine.mjs
- request.ts

OWNERSHIP_RESULT:
- related_tasks: TASK-153C / TASK-153F
- can_reclassify_to: HISTORICAL_TASK_OUTPUT_VERIFIED / NEEDS_FIX / BLOCKED
- remaining_unowned_business_diffs_excluded: YES

VALIDATION:
- npm run test:frontend-contract-engine: PASS/FAIL/NOT_RUN
- npm run check:style-profit-contracts: PASS/FAIL/NOT_RUN
- npm run test:style-profit-contracts: PASS/FAIL/NOT_RUN
- npm run typecheck: PASS/FAIL/NOT_RUN
- git diff --check: PASS/FAIL
- forbidden_files_touched: NO/YES

RISK_NOTES:
- 未运行 npm run dev/build/verify
- 未运行后端测试
- 未触碰其他前端 src/scripts、后端、CCC、控制面、AGENTS、架构师日志、审计官日志、生产/GitHub 管理配置
- 不代表剩余 business tracked diff、REL-004/REL-005、生产联调、ERPNext 生产写入或业务功能放行

NEXT_ROLE: A Technical Architect
BLOCKERS:
- NONE 或具体阻塞
```
