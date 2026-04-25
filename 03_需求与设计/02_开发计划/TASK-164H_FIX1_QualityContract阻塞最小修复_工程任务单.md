# TASK-164H FIX1 Quality Contract 阻塞最小修复工程任务单

```text
STATUS: READY_FOR_BUILD
TASK_ID: TASK-164H
FIX_PASS: FIX1
ROLE: B Engineer

任务：
修复 TASK-164H 必跑门禁 `npm run check:quality-contracts` 在 `src/api/quality.ts` 的红项，并重新完成 app shell router/HomePage 归口验证。

触发原因：
- B 对 TASK-164H 的回交结论为 BLOCKED。
- 必跑门禁 `npm run check:quality-contracts` 失败，失败文件为：
  /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/quality.ts
- 失败点：
  1. 裸 `fetch()`，必须走统一 request/requestFile 边界。
  2. `URL.createObjectURL()` 出现在 quality surface，触发动态加载门禁。
  3. quality API 缺少 `updateQualityInspection`。
  4. quality API 必须走统一 `request()`，禁止裸 fetch/axios。

必须读取：
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-164H_AppShellRouterHomePage回归归口_工程任务单.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-164H_AppShellRouterHomePage回归归口报告.md

允许修改：
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/quality.ts
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/HomePage.vue
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-164H_FIX1_QualityContract阻塞最小修复报告.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md

修改要求：
- `src/api/quality.ts` 必须清除裸 `fetch(`。
- `src/api/quality.ts` 必须清除 `URL.createObjectURL(` / `window.URL.createObjectURL(`。
- 必须提供 `updateQualityInspection` API 方法。
- 若已有 `updateDraftInspection` 被页面引用，必须保持兼容，不得破坏现有调用。
- export 路径必须继续只走受控 API 边界，不得新增 ERPNext `/api/resource`、`/api/method`、`frappe`、diagnostic/internal/run-once/worker 入口。
- HomePage.vue 仅允许保留或微调 TASK-164H 已做的最小会话文案修正，不得新增业务逻辑。

禁止修改：
- .gitignore
- vite.config.ts
- 06_前端/lingyi-pc/src/** 中除 `src/api/quality.ts` 与 `src/views/HomePage.vue` 之外的任何文件
- 06_前端/lingyi-pc/scripts/**
- 07_后端/**
- /Users/hh/Desktop/ccc/**
- LOOP_STATE / TASK_BOARD / HANDOVER_STATUS / INTERVENTION_QUEUE / AUTO_LOOP_PROTOCOL
- AGENTS、架构师日志、审计官日志、生产/GitHub 管理配置

必须验证：
- 在 /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc：
  - npm run check:quality-contracts
  - npm run test:quality-contracts
  - npm run typecheck
  - npm run check:production-contracts
  - npm run test:production-contracts
  - npm run check:sales-inventory-contracts
  - npm run test:sales-inventory-contracts
  - npm run check:factory-statement-contracts
  - npm run test:factory-statement-contracts
  - npm run check:style-profit-contracts
  - npm run test:style-profit-contracts
- git diff --check 限定：
  - 06_前端/lingyi-pc/src/api/quality.ts
  - 06_前端/lingyi-pc/src/router/index.ts
  - 06_前端/lingyi-pc/src/views/HomePage.vue
- 静态核对：
  - `quality.ts` 无裸 `fetch(`、无 `axios`、无 `URL.createObjectURL(`
  - `quality.ts` 存在 `updateQualityInspection`
  - `quality.ts` 不含 `/api/resource`、`/api/method`、`frappe`、`/api/quality/diagnostic`、`quality/internal`、`run-once`
  - router/HomePage 仍满足 TASK-164H 静态锚点
  - 未触碰禁止路径

禁止动作：
- 禁止 npm run dev/build/verify
- 禁止后端测试
- 禁止 CCC 启停/重载
- 禁止 /api/relay/start 或 /api/relay/stop
- 禁止 push / PR / tag / 发布
- 禁止外推为质量主链、剩余 business diff、REL-004/REL-005、生产联调或业务功能放行

REPORT_BACK_FORMAT:
STATUS: READY_FOR_REVIEW
TASK_ID: TASK-164H
FIX_PASS: FIX1
ROLE: B Engineer

CHANGED_FILES:
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/quality.ts
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-164H_FIX1_QualityContract阻塞最小修复报告.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md
- 如 HomePage.vue 本轮继续有变更，再列出

CODE_CHANGED_IN_FIX1:
- YES/NO

QUALITY_CONTRACT_FIX:
- fetch_removed: YES/NO
- create_object_url_removed: YES/NO
- updateQualityInspection_present: YES/NO
- updateDraftInspection_compat_preserved: YES/NO
- request_boundary_preserved: YES/NO

VALIDATION:
- npm run check:quality-contracts: PASS/FAIL
- npm run test:quality-contracts: PASS/FAIL
- npm run typecheck: PASS/FAIL
- npm run check:production-contracts: PASS/FAIL
- npm run test:production-contracts: PASS/FAIL
- npm run check:sales-inventory-contracts: PASS/FAIL
- npm run test:sales-inventory-contracts: PASS/FAIL
- npm run check:factory-statement-contracts: PASS/FAIL
- npm run test:factory-statement-contracts: PASS/FAIL
- npm run check:style-profit-contracts: PASS/FAIL
- npm run test:style-profit-contracts: PASS/FAIL
- static_business_anchors: PASS/FAIL
- git diff --check: PASS/FAIL
- forbidden_files_touched: NO/YES

OWNERSHIP_RESULT:
- related_scope: APP_SHELL_ROUTER_HOMEPAGE + QUALITY_CONTRACT_BLOCKER
- can_reclassify_to: HISTORICAL_TASK_OUTPUT_VERIFIED / NEEDS_FIX / BLOCKED
- remaining_unowned_business_diffs_excluded: YES

RISK_NOTES:
- 未运行 npm run dev/build/verify
- 未运行后端测试
- 未触碰其他前端 src/scripts、后端、CCC、控制面、AGENTS、架构师日志、审计官日志、生产/GitHub 管理配置
- 不代表质量主链整体放行、剩余 business tracked diff、REL-004/REL-005、生产联调、ERPNext 生产写入或业务功能放行

NEXT_ROLE: A Technical Architect
BLOCKERS:
- NONE 或具体阻塞
```
