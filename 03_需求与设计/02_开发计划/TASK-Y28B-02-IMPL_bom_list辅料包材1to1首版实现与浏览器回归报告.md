# TASK-Y28B-02-IMPL `/bom/list` 辅料/包材 1:1 首版实现与浏览器回归报告

## 1. 任务与范围
- TASK_ID: `TASK-Y28B-02-IMPL`
- 目标路由: `/bom/list`
- 实现语义: `TASK-Y27B-P1-02` 辅料/包材（只读）
- 前置基线: `task_y28b_02_bom_list_accessories_packaging_allowlist_baseline.json`
- 允许改动: `BomList.vue`、`bom.ts`、`bom.py`、`schemas/bom.py`、`bom_service.py`
- 未触碰: 任何非 `/bom/list` 路由、任何 P1-03/P1-04/P1-05 语义

## 2. 实现内容（仅只读语义）
### 2.1 前端（`BomList.vue`）
- 新增区块: `辅料/包材（TASK-Y27B-P1-02）`
- 新增筛选:
  - 款号、物料编码、物料名称、分类（辅料/包材）、供应商、状态
- 新增展示字段:
  - 物料编码、物料名称、分类、款号、颜色、规格、供应商、单件用量、损耗率、单位、来源BOM、状态
- 新增按钮语义（全部 guarded）:
  - 查看、选用、上传、导出
- 新增状态:
  - 空态（暂无辅料/包材数据）
  - 错误态（辅料/包材加载失败）
  - 权限/禁用态（只读受控提示）

### 2.2 前端 API（`bom.ts`）
- 新增只读 contract:
  - `BomAccessoriesPackagingItem`
  - `BomAccessoriesPackagingData`
  - `fetchBomAccessoriesPackaging(...) -> GET /api/bom/accessories-packaging`

### 2.3 后端（`bom.py` / `schemas/bom.py` / `bom_service.py`）
- 新增只读查询 schema:
  - `BomAccessoriesPackagingQuery`
  - `BomAccessoriesPackagingItem`
  - `BomAccessoriesPackagingData`
- 新增只读路由:
  - `GET /api/bom/accessories-packaging`
- 新增只读服务:
  - `list_accessories_packaging(...)`
  - 仅从 BOM item 派生辅料/包材视图，无写操作
- 路由顺序:
  - 新增静态路由位于 `/{bom_id}` 动态路由之前，避免动态路由误匹配

## 3. preserved checks
- BOM 管理列表主语义: PASS
- 物料图库语义: PASS
- 物料采购单语义: PASS
- 面料语义: PASS
- `/bom/detail` 入口链路: PASS

## 4. 本地验证
- `git diff --cached --name-only`: 空
- `git diff --check`（本轮允许文件）: PASS（无输出）
- `npm run precheck:dev-runtime`: PASS
- `npm run typecheck`: PASS
- `npm run verify`: PASS

> 说明：首次浏览器回归发现 `422`（旧 runtime 未加载新增静态路由），重启本地 `8000` dev runtime 后复跑闭合。

## 5. 浏览器回归（`/bom/list`）
- 脚本: `/tmp/task_y28b_02_impl_browser_check.mjs`
- result_json: `/tmp/task_y28b_02_impl_20260504T021734Z_browser_results.json`
- screenshot_dir: `/tmp/task_y28b_02_impl_20260504T021734Z_screenshots`
- screenshots_count: `6`

### 5.1 结构与语义检查
- `route_open`: true
- `first_screen_visible`: true
- `filters_present`: true
- `structure_mapped`: true
- `fields_or_headers_mapped`: true
- `accessories_packaging_fields_mapped`: true
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
