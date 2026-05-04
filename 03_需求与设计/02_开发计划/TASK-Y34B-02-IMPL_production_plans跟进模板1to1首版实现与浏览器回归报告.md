# TASK-Y34B-02-IMPL `/production/plans` 跟进模板 1:1 首版实现与浏览器回归报告

## 1. 任务与范围
- TASK_ID: `TASK-Y34B-02-IMPL`
- 目标路由: `/production/plans`（shared route）
- 实现语义: `TASK-Y33B-P1-02` 跟进模板（只读）
- 前置基线: `task_y34b_02_production_plans_followup_template_allowlist_baseline.json`
- 允许改动: `ProductionPlanList.vue`、`production.ts`、`production.py`、`schemas/production.py`、`production_service.py`
- 未触碰: 非 `/production/plans` 路由、`TASK-Y33B-P1-03/04/05`、测试/控制面/GitHub/生产配置

## 2. 实现内容（只读）
### 2.1 前端（`ProductionPlanList.vue`）
- 新增区块: `跟进模板（P1）`
- 新增筛选项:
  - 模板编号、模板名称、模板类型、款号、关键字、状态、开始时间、结束时间
- 新增展示字段:
  - 模板编号、模板名称、模板类型、触发节点、跟进角色、跟进频次、SLA(小时)、款号、公司、状态、更新时间
- 新增按钮语义（全部受控）:
  - 查看、编辑、打印、导出、新增、启用、停用、列设置
- 新增状态:
  - 空态（暂无跟进模板数据）
  - 错误态（跟进模板加载失败）
  - 权限/禁用态（写动作禁用 + guarded 提示）

### 2.2 前端 API（`production.ts`）
- 新增只读 contract:
  - `ProductionFollowupTemplateListQuery`
  - `ProductionFollowupTemplateListItem`
  - `ProductionFollowupTemplateListData`
- 新增只读调用:
  - `fetchProductionFollowupTemplates(...) -> GET /api/production/followup-templates`

### 2.3 后端（`production.py` / `schemas/production.py` / `production_service.py`）
- 新增只读 schema:
  - `ProductionFollowupTemplateQuery`
  - `ProductionFollowupTemplateListItem`
  - `ProductionFollowupTemplateListData`
- 新增只读路由:
  - `GET /api/production/followup-templates`
- 新增只读服务:
  - `list_followup_templates(...)`
  - 基于 `LyProductionPlan` 聚合模板展示字段，未引入写动作
- 路由遮蔽检查:
  - `GET /api/production/followup-templates` 位于 `GET /api/production/plans/{plan_id}` 前，未被动态路由遮蔽

## 3. preserved checks
- P0 大货跟进 preserved: PASS
- P1 大货成本物料明细表 preserved: PASS
- P1 大货销售预测明细表 preserved: PASS
- P1 报价单 preserved: PASS
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
- result_json: `/tmp/task_y34b_02_impl_20260504T070026Z_browser_results.json`
- screenshots:
  - `/tmp/task_y34b_02_impl_20260504T070026Z_01_overview.png`
  - `/tmp/task_y34b_02_impl_20260504T070026Z_02_followup_template.png`
  - `/tmp/task_y34b_02_impl_20260504T070026Z_03_guarded_action.png`
  - `/tmp/task_y34b_02_impl_20260504T070026Z_04_error_state.png`
  - `/tmp/task_y34b_02_impl_20260504T070026Z_05_permission_state.png`
- screenshots_count: `5`

### 5.1 结构与语义检查
- `route_open`: true
- `first_screen_visible`: true
- `filters_present`: true
- `followup_template_fields_mapped`: true
- `buttons_mapped`: true
- `status_tags_mapped`: true
- `empty_state`: true
- `error_state`: true
- `permission_or_disabled_state`: true

### 5.2 preserved 检查
- `p0_production_followup_preserved_check`: true
- `p1_material_cost_preserved_check`: true
- `p1_sales_forecast_preserved_check`: true
- `p1_quote_preserved_check`: true
- `detail_or_followup_entry_preserved_check`: true
- `permission_or_error_state_preserved_check`: true
- `write_actions_guarded_check`: true

### 5.3 安全与副作用检查
- `write_request_count`: `0`
- `upload_download_export_print_request_count`: `0`
- `unexplained_console_errors_total`: `0`
- `unexplained_network_4xx_5xx_total`: `0`

## 6. 禁止项核对
- 未执行 `git add/commit/push`
- 未执行 PR/merge/close/tag/release
- 未执行 cleanup/reset/restore/clean/delete
- 未启动 `TASK-Y33B-P1-03/04/05`
- 未修改非 `/production/plans` 路由
- 未新增 POST/PUT/PATCH/DELETE 写路由
- 未触发真实上传/下载/导出/打印/写请求
- 未触碰生产/GitHub 管理配置
- parked blockers 未释放
