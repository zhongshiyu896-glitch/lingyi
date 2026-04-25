# TASK-174A 前端未登录态 AuthMe 探测噪声收敛与浏览器 Smoke 回归报告

STATUS: READY_FOR_REVIEW
TASK_ID: TASK-174A
ROLE: B Engineer

CHANGED_FILES:
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/stores/permission.ts
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-174A_前端未登录态AuthMe探测噪声收敛与浏览器Smoke回归报告.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md

IMPLEMENTATION_SUMMARY:
- 仅在白名单内改动 `permission.ts`，新增未登录态 `auth/me` 探测短期会话缓存（15 秒）与并发去重，避免同一浏览器会话内页面切换重复触发 401 探测。
- 保留安全刷新路径：`loadCurrentUser({ force: true })` 与 `refreshCurrentUser()`，避免 guest 缓存永久阻断登录后真实用户恢复。
- 未改后端、CCC、控制面与其它前端业务文件。

ROOT_CAUSE:
- 多个页面在 `onMounted` 调用 `permissionStore.loadCurrentUser()`；未登录态每次都请求 `/api/auth/me`，导致“每页 1 次 401”重复噪声。
- 之前已有 guest fail-soft 语义，但缺少“会话内短期未登录探测记忆”与“并发去重”。

FIX_SUMMARY:
- 文件：`/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/stores/permission.ts`
- 新增：
  - `AUTH_ME_GUEST_CACHE_KEY` / `AUTH_ME_GUEST_CACHE_TTL_MS=15000`
  - `readGuestCacheUntil` / `writeGuestCacheUntil` / `clearGuestCache`
  - `applyGuestState`
  - `currentUserLoadPromise`（并发去重）
- 调整 `loadCurrentUser(options?: { force?: boolean })`：
  - 非 force 且 guest 缓存有效时直接走 guest fail-soft，不再请求 `/api/auth/me`
  - 非 force 且已有 in-flight 请求时复用 promise
  - 401 时写入短期 guest 缓存；成功时清缓存
- 新增 `refreshCurrentUser()` 强制刷新入口。

AUTH_ME_NOISE_RESULT:
- before_baseline: TASK-173A 真实浏览器 11 页总计 `auth_me_401_count=11`（每页 1 次）
- after_result: 本轮真实浏览器 11 页总计 `auth_me_401_count=1`
- auth_me_401_count: 1
- still_repeated_per_page: NO
- login_recovery_path_preserved: YES（存在 `force` 刷新路径，不是永久 guest 缓存）

SECURITY_BOUNDARY:
- guest_permission_granted: NO
- actions_empty_for_guest: YES
- button_permissions_all_false_for_guest: YES
- production_user_or_role_faked: NO

BROWSER_SMOKE_RESULT:
- PASS
- run_id: 20260425T162439
- base_url: http://127.0.0.1:5174
- result_json: /tmp/task174a_browser_results.json
- pages_checked:
  - /home | 200 | true | true | 1 | 0 | 1 | 1 | /tmp/task174a_20260425T162439_home.png
  - /production/plans | 200 | true | true | 0 | 0 | 0 | 0 | /tmp/task174a_20260425T162439_production_plans.png
  - /factory-statements/list | 200 | true | true | 0 | 0 | 0 | 0 | /tmp/task174a_20260425T162439_factory-statements_list.png
  - /sales-inventory/sales-orders | 200 | true | true | 0 | 0 | 0 | 0 | /tmp/task174a_20260425T162439_sales-inventory_sales-orders.png
  - /sales-inventory/stock-ledger | 200 | true | true | 0 | 0 | 0 | 0 | /tmp/task174a_20260425T162439_sales-inventory_stock-ledger.png
  - /warehouse | 200 | true | true | 0 | 0 | 0 | 0 | /tmp/task174a_20260425T162439_warehouse.png
  - /quality/inspections | 200 | true | true | 0 | 0 | 0 | 0 | /tmp/task174a_20260425T162439_quality_inspections.png
  - /reports/style-profit | 200 | true | true | 0 | 0 | 0 | 0 | /tmp/task174a_20260425T162439_reports_style-profit.png
  - /workshop/tickets | 200 | true | true | 0 | 0 | 0 | 0 | /tmp/task174a_20260425T162439_workshop_tickets.png
  - /workshop/daily-wages | 200 | true | true | 0 | 0 | 0 | 0 | /tmp/task174a_20260425T162439_workshop_daily-wages.png
  - /workshop/wage-rates | 200 | true | true | 0 | 0 | 0 | 0 | /tmp/task174a_20260425T162439_workshop_wage-rates.png

INTERACTION_RESULT:
- PASS
- interactions_checked:
  - /home 可见导航入口点击 2/2
  - /warehouse 只读切换 2/2
  - /workshop/tickets 筛选输入/清空 PASS
  - /workshop/daily-wages 筛选输入/清空 PASS
  - /workshop/wage-rates 筛选输入/清空 PASS
- write_actions_avoided: YES
- failures:
  - NONE

VALIDATION:
- git status precheck -> PASS
- staged area empty -> PASS
- static auth side-effect check -> PASS（`window.alert|location.href|/login` 无新增命中）
- guest permission static check -> PASS（guest 分支保持 `actions=[]` 与 `buttonPermissions=emptyButtonPermissions()`）
- npm run typecheck -> PASS
- npm run verify -> PASS
- Playwright smoke -> PASS（11 页）
- read-only interaction -> PASS
- dev server stopped -> PASS（本轮 5174 已停止；5173 为 pre-existing 进程）
- forbidden files untouched -> PASS
- git diff --check -> PASS

FORBIDDEN_ACTIONS:
- git add/commit/push/PR/tag/release: NO
- backend/CCC/control-plane edits: NO
- GitHub management config: NO
- production/ERPNext actions: NO
- parked blockers released: NO
- write business actions clicked: NO

NEXT_ROLE: A Technical Architect
BLOCKERS:
- NONE
