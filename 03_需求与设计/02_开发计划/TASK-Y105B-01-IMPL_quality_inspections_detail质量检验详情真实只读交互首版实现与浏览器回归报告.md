# TASK-Y105B-01-IMPL /quality/inspections/detail 质量检验详情真实只读交互首版实现与浏览器回归报告

## 1. 任务与范围
- TASK_ID: `TASK-Y105B-01-IMPL`
- 路由: `/quality/inspections/detail`
- 本轮仅修改 allowlist 文件：
  - `06_前端/lingyi-pc/src/views/quality/QualityInspectionDetail.vue`
  - `03_需求与设计/02_开发计划/TASK-Y105B-01-IMPL_quality_inspections_detail质量检验详情真实只读交互首版实现与浏览器回归报告.md`
  - `03_需求与设计/02_开发计划/工程师会话日志.md`
- 未修改禁止项：`api/quality.ts`、`src/router`、后端 `quality` router/schema/service、测试文件、控制面文件、C 审计记录与其他页面。

## 2. 实现锚点

### 2.1 详情只读 GET 链路保留
- 保持详情读取链路：`fetchQualityInspectionDetail` -> `GET /api/quality/inspections/{inspection_id}`。
- `onMounted` 仍按既有顺序加载 `loadCurrentUser`、`loadModuleActions('quality')`，随后执行 `loadDetail()`。

### 2.2 写动作改为 guarded/disabled 提示型
- 移除详情页内所有写接口调用（不再调用 `updateDraftInspection`、`addDefectRecord`、`confirmQualityInspection`、`cancelQualityInspection`）。
- `submitUpdate/submitDefect/submitConfirm/submitCancel` 统一改为只读 guard，调用 `guardedWriteAction(...)`，仅提示，不发起写请求。
- 按状态与权限保留 fail-closed 语义：
  - `canUpdate`（草稿且有更新权限）
  - `canConfirm`（草稿且有确认权限）
  - `canCancel`（已确认且有取消权限）
- 保留契约所需绑定：`v-if=\"canUpdate/canConfirm/canCancel\"` 与 `:disabled=\"!canUpdate/!canConfirm/!canCancel\"`。

### 2.3 浏览器可审计 data-testid 补齐
- 页面与头部：
  - `quality-inspection-detail-page`
  - `quality-inspection-detail-header`
  - `quality-inspection-detail-title`
  - `quality-inspection-detail-back`
- 主档与标签：
  - `quality-inspection-detail-main-fields`
  - `quality-inspection-detail-field-inspection-no`
  - `quality-inspection-detail-status-tag`
  - `quality-inspection-detail-result-tag`
- 分区表格：
  - `quality-inspection-detail-items-table`
  - `quality-inspection-detail-defects-table`
  - `quality-inspection-detail-logs-table`
- 状态锚点：
  - `quality-inspection-detail-missing-id-state`
  - `quality-inspection-detail-empty-state`
  - `quality-inspection-detail-error-state`
  - `quality-inspection-detail-permission-state`
  - `quality-inspection-detail-permission-disabled-state`
  - `quality-inspection-detail-guarded-feedback`

## 3. 浏览器回归证据
- result_json: `/tmp/task_y105b_01_impl_20260511T083447Z_browser_results.json`
- screenshots_dir: `/tmp/task_y105b_01_impl_20260511T083447Z_screenshots`
- screenshots_count: `9`

关键结果：
- `route_open=true`
- `first_screen_visible=true`
- `detail_get_triggered=true`
- `detail_fields_mapped=true`
- `status_tag_mapped=true`
- `result_tag_mapped=true`
- `items_table_visible=true`
- `defects_table_visible=true`
- `logs_table_visible=true`
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
- 错误态通过受控 `GET /api/quality/inspections/503` 返回 503 验证，`expected_network_4xx_5xx_total=1`，未计入 unexplained。

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
- 未启动 `TASK-Y105B-02-IMPL` 或其他候选: YES
- 未释放 parked blockers: YES

## 6. 残余风险
- 本轮错误态与权限态使用浏览器受控桩响应进行可审计验证；联调环境下文案可能与本地桩数据不同，但不影响只读详情链路与零副作用约束。
