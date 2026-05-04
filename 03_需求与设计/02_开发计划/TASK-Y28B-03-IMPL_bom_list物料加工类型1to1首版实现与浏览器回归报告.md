# TASK-Y28B-03-IMPL `/bom/list` 物料加工类型 1:1 首版实现与浏览器回归报告

## 1. 任务与范围
- TASK_ID: `TASK-Y28B-03-IMPL`
- 目标路由: `/bom/list`
- 实现语义: `TASK-Y27B-P1-03` 物料加工类型（只读）
- 前置基线: `task_y28b_03_bom_list_processing_type_allowlist_baseline.json`
- 允许改动: `BomList.vue`、`bom.ts`、`bom.py`、`schemas/bom.py`、`bom_service.py`
- 未触碰: 非 `/bom/list` 路由与 `TASK-Y27B-P1-04/05` 语义

## 2. 实现内容（仅只读语义）
### 2.1 前端（`BomList.vue`）
- 新增区块: `物料加工类型（TASK-Y27B-P1-03）`
- 新增筛选:
  - 款号、加工类型、工序名称、委外类型、计价方式、状态
- 新增展示字段:
  - 加工类型编码、加工类型、工序名称、工序顺序、委外类型、计价方式、单价/工价、来源BOM、状态
- 新增按钮语义（全部 guarded）:
  - 查看、配置、启停、导出
- 新增状态:
  - 空态（暂无物料加工类型数据）
  - 错误态（物料加工类型加载失败）
  - 权限/禁用态（只读受控提示）

### 2.2 前端 API（`bom.ts`）
- 新增只读 contract:
  - `BomProcessingTypeItem`
  - `BomProcessingTypeData`
  - `fetchBomProcessingTypes(...) -> GET /api/bom/processing-types`

### 2.3 后端（`bom.py` / `schemas/bom.py` / `bom_service.py`）
- 新增只读查询 schema:
  - `BomProcessingTypeQuery`
  - `BomProcessingTypeItem`
  - `BomProcessingTypeData`
- 新增只读路由:
  - `GET /api/bom/processing-types`
- 新增只读服务:
  - `list_processing_types(...)`
  - 仅基于 BOM 工序/主档派生加工类型视图，无写操作
- 路由顺序:
  - 静态路由位于 `/{bom_id}` 动态路由之前，避免动态误匹配

## 3. preserved checks
- BOM 管理列表主语义: PASS
- 物料图库语义: PASS
- 物料采购单语义: PASS
- 面料语义: PASS
- 辅料/包材语义: PASS
- `/bom/detail` 入口链路: PASS

## 4. 本地验证
- `git diff --cached --name-only`: 空
- `git diff --check`（本轮允许文件）: PASS（无输出）
- `npm run precheck:dev-runtime`: PASS
- `npm run typecheck`: PASS
- `npm run verify`: PASS

## 5. 浏览器回归（`/bom/list`）
- 脚本: `/tmp/task_y28b_03_impl_browser_check.mjs`
- result_json: `/tmp/task_y28b_03_impl_20260504T025707Z_browser_results.json`
- screenshot_dir: `/tmp/task_y28b_03_impl_20260504T025707Z_screenshots`
- screenshots_count: `6`

### 5.1 结构与语义检查
- `route_open`: true
- `first_screen_visible`: true
- `filters_present`: true
- `structure_mapped`: true
- `fields_or_headers_mapped`: true
- `processing_type_fields_mapped`: true
- `buttons_mapped`: true
- `status_tags_mapped`: true
- `empty_state`: true
- `error_state`: true（通过一次受控 503 注入验证）
- `permission_or_disabled_state`: true

### 5.2 安全与副作用检查
- `write_actions_guarded_check`: true
- `write_request_count`: `0`
- `upload_download_export_print_request_count`: `0`
- `unexplained_console_errors_total`: `0`
- `unexplained_network_4xx_5xx_total`: `0`

## 6. 禁止项核对
- 未执行 `git add/commit/push`
- 未执行 PR/merge/close/tag/release
- 未执行 cleanup/reset/restore/clean/delete
- 未新增真实 POST/PUT/PATCH/DELETE 写路由
- 未放宽 BOM 写权限
- 未触发真实上传/下载/导出/打印请求
- 未触碰生产/GitHub 管理配置
- parked blockers 未释放
