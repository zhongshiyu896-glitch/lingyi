# TASK-Y105B-04-IMPL /bom/detail BOM详情真实只读交互首版实现与浏览器回归报告

## 1. 任务与范围
- TASK_ID: `TASK-Y105B-04-IMPL`
- 路由: `/bom/detail`
- 本轮仅修改 allowlist 文件：
  - `06_前端/lingyi-pc/src/views/bom/BomDetail.vue`
  - `03_需求与设计/02_开发计划/TASK-Y105B-04-IMPL_bom_detailBOM详情真实只读交互首版实现与浏览器回归报告.md`
  - `03_需求与设计/02_开发计划/工程师会话日志.md`
- 未修改禁止项：`api/bom.ts`、`backend bom router/schema/service`、测试文件、A 控制面文件、C 审计记录与其他页面。

## 2. 实现锚点

### 2.1 保留只读 GET 链路
- 保持详情读取链路：`fetchBomDetail` -> `GET /api/bom/{bom_id}`。
- `onMounted` 仍执行 `loadCurrentUser` + `loadBomActions/loadModuleActions`，在 `canRead=true` 且 `id` 合法时加载详情。

### 2.2 写入口全部收敛为 guarded/disabled/提示型
- 移除页面中所有真实写调用，不再调用：
  - `createBom`
  - `updateBomDraft`
  - `setDefaultBom`
  - `activateBom`
  - `deactivateBom`
  - `explodeBom`
- 新增统一 `guardedWriteAction(...)`，对“保存草稿/创建/设为默认/发布/停用/展开计算/新增或删除明细”全部只给提示，不触发写请求。

### 2.3 data-testid 与状态锚点补齐
- 页面与主区块：
  - `bom-detail-page`
  - `bom-detail-main-card`
  - `bom-detail-header`
  - `bom-detail-title`
  - `bom-detail-back`
- 主档与详情字段：
  - `bom-detail-main-fields`
  - `bom-detail-field-bom-no`
  - `bom-detail-field-item-code`
  - `bom-detail-field-version-no`
  - `bom-detail-status-tag`
- 明细区：
  - `bom-detail-material-section`
  - `bom-detail-material-table`
  - `bom-detail-operation-section`
  - `bom-detail-operation-table`
- 状态与反馈：
  - `bom-detail-missing-id-state`
  - `bom-detail-empty-state`
  - `bom-detail-error-state`
  - `bom-detail-permission-state`
  - `bom-detail-permission-or-disabled-state`
  - `bom-detail-guarded-feedback`

## 3. 浏览器回归证据
- result_json: `/tmp/task_y105b_04_impl_20260511T101525Z_browser_results.json`
- screenshots_dir: `/tmp/task_y105b_04_impl_20260511T101525Z_screenshots`
- screenshots_count: `8`

关键结果：
- `route_open=true`
- `first_screen_visible=true`
- `detail_get_triggered=true`
- `detail_fields_mapped=true`
- `status_tag_mapped=true`
- `material_table_mapped=true`
- `operation_table_mapped=true`
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
- 错误态通过受控 `GET /api/bom/1` 返回 `503` 验证，`expected_network_4xx_5xx_total=1`，并且 `expected_console_errors_total=1`，均未计入 unexplained。

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
- 未启动 `TASK-Y105B-05-IMPL` 或其他页面: YES
- 未释放 parked blockers: YES

## 6. 残余风险
- 错误态和部分禁用态来自浏览器受控桩验证，联调环境下提示文案可能与本地略有差异；不影响本轮“只读 GET + 零写请求”验收口径。
