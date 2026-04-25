# TASK-173A 前端 Workshop 旧 401 副作用收敛与真实浏览器 Smoke 扩展报告

## STATUS
- TASK_ID: TASK-173A
- ROLE: B Engineer
- RESULT: READY_FOR_REVIEW

## CHANGED_FILES
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/workshop.ts
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-173A_前端Workshop旧401副作用收敛与真实浏览器Smoke扩展报告.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md

## IMPLEMENTATION_SUMMARY
- 仅在白名单内收敛 `workshop.ts` 旧 401 浏览器副作用，去除未登录自动弹窗与跳转副作用。
- 保持鉴权边界：未登录/无权限仍通过抛错与页面既有权限门禁处理，不授予 guest 业务权限。
- 使用 Playwright 扩展真实浏览器 smoke 覆盖：TASK-172A 原 8 页 + Workshop 3 页。

## ROOT_CAUSE
- `src/api/workshop.ts` 的 `handleAuthError` 在 401 时执行 `window.alert` 与 `window.location.href='/login'`，会引入未登录态页面链路不稳定。
- TASK-172A 后其余页面已稳定，但 Workshop API 仍沿用旧副作用实现，属于残余风险点。

## FIX_SUMMARY
- 文件：`/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/workshop.ts`
- 变更：
  - 删除 `window.alert('登录已失效，请重新登录')`
  - 删除 `window.location.href = '/login'`
  - 401 统一改为 `throw new Error('登录已失效，请重新登录')`
  - 403 继续 `throw new Error('无权执行该操作')`
- 安全边界说明：
  - 未登录不会获得业务权限（permission store 仍是 guest fail-soft）。
  - 未伪造用户/角色，未绕过按钮/接口权限。

## STATIC_AUTH_SIDE_EFFECT_CHECK
- workshop_alert_redirect_removed: YES
- workshop_guest_permission_granted: NO
- remaining_401_behavior: 未登录态仍可能出现 `/api/auth/me` 401（探测噪声），但不再触发 workshop API 的浏览器弹窗/跳转副作用

## BROWSER_SMOKE_RESULT
- RESULT: PASS
- run_id: `20260425T152637`
- base_url: `http://127.0.0.1:5174`
- result_json: `/tmp/task173a_browser_results.json`
- pages_checked:
  - /home | 200 | true | true | 1 | 0 | 1 | /tmp/task173a_20260425T152637_home.png
  - /production/plans | 200 | true | true | 1 | 0 | 1 | /tmp/task173a_20260425T152637_production_plans.png
  - /factory-statements/list | 200 | true | true | 1 | 0 | 1 | /tmp/task173a_20260425T152637_factory-statements_list.png
  - /sales-inventory/sales-orders | 200 | true | true | 1 | 0 | 1 | /tmp/task173a_20260425T152637_sales-inventory_sales-orders.png
  - /sales-inventory/stock-ledger | 200 | true | true | 1 | 0 | 1 | /tmp/task173a_20260425T152637_sales-inventory_stock-ledger.png
  - /warehouse | 200 | true | true | 1 | 0 | 1 | /tmp/task173a_20260425T152637_warehouse.png
  - /quality/inspections | 200 | true | true | 1 | 0 | 1 | /tmp/task173a_20260425T152637_quality_inspections.png
  - /reports/style-profit | 200 | true | true | 1 | 0 | 1 | /tmp/task173a_20260425T152637_reports_style-profit.png
  - /workshop/tickets | 200 | true | true | 1 | 0 | 1 | /tmp/task173a_20260425T152637_workshop_tickets.png
  - /workshop/daily-wages | 200 | true | true | 1 | 0 | 1 | /tmp/task173a_20260425T152637_workshop_daily-wages.png
  - /workshop/wage-rates | 200 | true | true | 1 | 0 | 1 | /tmp/task173a_20260425T152637_workshop_wage-rates.png

## WORKSHOP_INTERACTION_RESULT
- RESULT: PASS
- interactions_checked:
  - /workshop/tickets: 筛选输入 `SMOKE` 后清空 -> PASS
  - /workshop/daily-wages: 筛选输入 `SMOKE` 后清空 -> PASS
  - /workshop/wage-rates: 筛选输入 `SMOKE` 后清空 -> PASS
  - /home: 可见导航入口点击 2/2 -> PASS
  - /warehouse: 只读 tab 切换 2/2 -> PASS
- write_actions_avoided: YES
- failures: NONE

## VALIDATION
- git status precheck -> PASS
- staged area empty -> PASS
- static auth side-effect check -> PASS
- npm run typecheck -> PASS
- npm run verify -> PASS
- Playwright smoke (11 pages) -> PASS
- Workshop read-only interaction -> PASS
- dev server stopped -> PASS（仅停止本轮 5174；5173 pre-existing 进程保留）
- forbidden files untouched -> PASS（本轮未改后端/CCC/控制面/GitHub配置）
- git diff --check -> PASS

## FORBIDDEN_ACTIONS
- git add/commit/push/PR/tag/release: NO
- backend/CCC/control-plane edits: NO
- GitHub management config: NO
- production/ERPNext actions: NO
- parked blockers released: NO
- write business actions clicked: NO

## NEXT
- NEXT_ROLE: A Technical Architect
- BLOCKERS: NONE
