# TASK-Y34B-01-IMPL `/production/plans` 报价单 1:1 首版实现与浏览器回归报告

## 1. 任务与范围
- TASK_ID: `TASK-Y34B-01-IMPL`
- 目标路由: `/production/plans`（shared route）
- 实现语义: `TASK-Y33B-P1-01` 报价单（只读）
- 前置基线: `task_y34b_01_production_plans_quote_allowlist_baseline.json`
- 允许改动: `ProductionPlanList.vue`、`production.ts`、`production.py`、`schemas/production.py`、`production_service.py`
- 未触碰: 非 `/production/plans` 路由、`TASK-Y33B-P1-02/03/04/05`、测试/控制面/GitHub/生产配置

## 2. 实现内容（只读）
### 2.1 前端（`ProductionPlanList.vue`）
- 新增区块: `报价单（P1）`
- 新增筛选项:
  - 报价单号、订单、翻单号、款号、客户、关键字、状态、开始时间、结束时间
- 新增展示字段:
  - 报价单号、生产制单、订单信息、款号、客户、报价数量、报价单价(元)、报价金额(元)、报价日期、交期、状态
- 新增按钮语义（全部受控）:
  - 查看、打印、导出、确认、取消、列设置
- 新增状态:
  - 空态（暂无报价单数据）
  - 错误态（报价单加载失败）
  - 权限/禁用态（写动作禁用或提示）

### 2.2 前端 API（`production.ts`）
- 新增只读 contract:
  - `ProductionQuoteListQuery`
  - `ProductionQuoteListItem`
  - `ProductionQuoteListData`
- 新增只读调用:
  - `fetchProductionQuotes(...) -> GET /api/production/quotes`

### 2.3 后端（`production.py` / `schemas/production.py` / `production_service.py`）
- 新增只读 schema:
  - `ProductionQuoteQuery`
  - `ProductionQuoteListItem`
  - `ProductionQuoteListData`
- 新增只读路由:
  - `GET /api/production/quotes`
- 新增只读服务:
  - `list_quotes(...)`
  - 基于 `LyProductionPlan + BOM 物料估算` 聚合报价字段，未引入写动作
- 路由遮蔽检查:
  - `GET /api/production/quotes` 位于 `GET /api/production/plans/{plan_id}` 前，未被动态路由遮蔽

## 3. preserved checks
- P0 大货跟进 preserved: PASS
- P1 大货成本物料明细表 preserved: PASS
- P1 大货销售预测明细表 preserved: PASS
- `/production/plans/detail` 跟进入口 preserved: PASS
- permission/error state preserved: PASS
- write actions guarded: PASS
- `shared_route_scope_expanded`: `NO`

## 4. 本地验证
- `git -C '/Users/hh/Desktop/领意服装管理系统' diff --cached --name-only`: 空
- `git -C '/Users/hh/Desktop/领意服装管理系统' diff --check`: PASS（无输出）
- `npm run precheck:dev-runtime`: PASS
- `npm run typecheck`: PASS
- `npm run verify`: PASS

## 5. 浏览器回归（`/production/plans`）
- 脚本: `/tmp/task_y34b_01_impl_browser_check.mjs`
- result_json: `/tmp/task_y34b_01_impl_20260504T062805Z_browser_results.json`
- screenshot_dir: `/tmp/task_y34b_01_impl_20260504T062805Z_screenshots`
- screenshots_count: `6`

### 5.1 结构与语义检查
- `route_open`: true
- `first_screen_visible`: true
- `filters_present`: true
- `quote_fields_mapped`: true
- `buttons_mapped`: true
- `status_tags_mapped`: true
- `empty_state`: true
- `error_state`: true（一次受控 503 注入验证）
- `permission_or_disabled_state`: true

### 5.2 preserved 检查
- `p0_production_followup_preserved_check`: true
- `p1_material_cost_preserved_check`: true
- `p1_sales_forecast_preserved_check`: true
- `detail_or_followup_entry_preserved_check`: true
- `permission_or_error_state_preserved_check`: true
- `write_actions_guarded_check`: true

### 5.3 安全与副作用检查
- `write_request_count`: `0`
- `upload_download_export_print_request_count`: `0`
- `console_errors_total`: `1`
- `network_4xx_5xx_total`: `1`
- `expected_error_state_count`: `1`
- `unexplained_console_errors_total`: `0`
- `unexplained_network_4xx_5xx_total`: `0`

## 6. 禁止项核对
- 未执行 `git add/commit/push`
- 未执行 PR/merge/close/tag/release
- 未执行 cleanup/reset/restore/clean/delete
- 未启动 `TASK-Y33B-P1-02/03/04/05`
- 未修改非 `/production/plans` 路由
- 未新增 POST/PUT/PATCH/DELETE 写路由
- 未触发真实上传/下载/导出/打印/写请求
- 未触碰生产/GitHub 管理配置
- parked blockers 未释放
