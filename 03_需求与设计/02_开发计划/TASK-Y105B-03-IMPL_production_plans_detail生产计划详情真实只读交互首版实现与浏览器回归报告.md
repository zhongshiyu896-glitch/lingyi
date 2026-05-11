# TASK-Y105B-03-IMPL /production/plans/detail 生产计划详情真实只读交互首版实现与浏览器回归报告

## 1. 任务与范围
- TASK_ID: `TASK-Y105B-03-IMPL`
- 路由: `/production/plans/detail`
- 本轮仅修改 allowlist 文件：
  - `06_前端/lingyi-pc/src/views/production/ProductionPlanDetail.vue`
  - `03_需求与设计/02_开发计划/TASK-Y105B-03-IMPL_production_plans_detail生产计划详情真实只读交互首版实现与浏览器回归报告.md`
  - `03_需求与设计/02_开发计划/工程师会话日志.md`
- 未修改禁止项：`api/production.ts`、router、后端 `production` router/schema/service、测试文件、控制面文件、C 审计记录与其他页面。

## 2. 实现锚点

### 2.1 保留只读 GET 详情链路
- 保持详情读取链路：`fetchProductionPlanDetail` -> `GET /api/production/plans/{plan_id}`。
- `onMounted` 仍按既有顺序加载 `loadCurrentUser`、`loadModuleActions('production')`，随后执行 `loadDetail()`。

### 2.2 写入口收敛为 guarded/disabled/提示型
- 移除页面内写 API 调用，不再调用：
  - `checkProductionMaterials`
  - `createProductionWorkOrder`
- 新增 `guardedWriteAction(...)`，`runMaterialCheck` 与 `submitCreateWorkOrder` 统一改为只读 guard 提示，不触发 POST。
- 物料检查与创建 Work Order 按钮均保留 `data-action-type="write"` 与 `data-write-guard="guarded:readonly"`，满足可审计写动作冻结语义。

### 2.3 data-testid 与状态锚点补齐
- 页面与头部：
  - `production-plan-detail-page`
  - `production-plan-detail-main-card`
  - `production-plan-detail-header`
  - `production-plan-detail-title`
  - `production-plan-detail-back`
- 主档字段与标签：
  - `production-plan-detail-main-fields`
  - `production-plan-detail-field-plan-no`
  - `production-plan-detail-field-company`
  - `production-plan-detail-field-item-code`
  - `production-plan-detail-status-tag`
- 只读映射区：
  - `production-plan-detail-work-order-mapping`
  - `production-plan-detail-material-snapshot-table`
  - `production-plan-detail-job-card-table`
- 状态锚点：
  - `production-plan-detail-missing-id-state`
  - `production-plan-detail-empty-state`
  - `production-plan-detail-error-state`
  - `production-plan-detail-permission-state`
  - `production-plan-detail-permission-or-disabled-state`
  - `production-plan-detail-guarded-feedback`

## 3. 浏览器回归证据
- result_json: `/tmp/task_y105b_03_impl_20260511T095312Z_browser_results.json`
- screenshots_dir: `/tmp/task_y105b_03_impl_20260511T095312Z_screenshots`
- screenshots_count: `8`

关键结果：
- `route_open=true`
- `first_screen_visible=true`
- `detail_get_triggered=true`
- `detail_fields_mapped=true`
- `status_tag_mapped=true`
- `work_order_mapped=true`
- `material_snapshot_mapped=true`
- `job_card_mapped=true`
- `missing_id_state=true`
- `empty_state=true`
- `error_state=true`
- `permission_or_disabled_state=true`
- `guarded_write_feedback=true`
- `write_request_count=0`
- `upload_download_export_print_request_count=0`
- `unexplained_console_errors_total=0`
- `unexplained_network_4xx_5xx_total=0`

说明：
- 错误态通过受控 `GET /api/production/plans/503` 验证，`expected_network_4xx_5xx_total=1`，未计入 unexplained。

## 4. 验证命令结果
- `npm run precheck:dev-runtime`: PASS
- `npm run typecheck`: PASS
- `npm run verify`: PASS
- `git diff --cached --name-only`: EMPTY
- `git diff --cached --check`: PASS
- `git diff --check`: PASS

## 5. 禁止动作核对
- 未执行 `git add / commit / push`: YES
- 未执行 `PR / merge / tag / release`: YES
- 未执行 `cleanup / reset / restore / clean / delete`: YES
- 未启动 `TASK-Y105B-04-IMPL` 或其他候选: YES
- 未释放 parked blockers: YES

## 6. 残余风险
- 本轮错误态与权限态使用浏览器受控桩响应做可审计验证；联调环境文案可能有差异，但不影响只读 GET 链路和零副作用约束。
