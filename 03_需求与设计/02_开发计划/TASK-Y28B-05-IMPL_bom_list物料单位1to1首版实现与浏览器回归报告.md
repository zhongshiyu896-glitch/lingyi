# TASK-Y28B-05-IMPL `/bom/list` 物料单位 1:1 首版实现与浏览器回归报告

## 1. 任务与范围
- TASK_ID: `TASK-Y28B-05-IMPL`
- 目标路由: `/bom/list`
- 实现语义: `TASK-Y27B-P1-05` 物料单位（只读）
- 前置基线: `task_y28b_05_bom_list_material_unit_allowlist_baseline.json`
- 允许改动: `BomList.vue`、`bom.ts`、`bom.py`、`schemas/bom.py`、`bom_service.py`
- 未触碰: 任何非 `/bom/list` 路由、`TASK-Y28B-05` 之外新页面

## 2. 实现内容（只读）
### 2.1 前端（`BomList.vue`）
- 新增区块: `物料单位（TASK-Y27B-P1-05）`
- 新增筛选:
  - 款号、物料编码、单位名称、状态
- 新增展示字段:
  - 单位编码、单位名称、基础单位、换算关系、精度、物料编码、款号、来源BOM、状态
- 新增按钮语义（全部 guarded）:
  - 查看、新增单位、编辑、停用、导出
- 新增状态:
  - 空态（暂无物料单位数据）
  - 错误态（物料单位加载失败）
  - 权限/禁用态（只读受控提示）

### 2.2 前端 API（`bom.ts`）
- 新增只读 contract:
  - `BomMaterialUnitItem`
  - `BomMaterialUnitData`
  - `fetchBomMaterialUnits(...) -> GET /api/bom/material-units`

### 2.3 后端（`bom.py` / `schemas/bom.py` / `bom_service.py`）
- 新增只读查询 schema:
  - `BomMaterialUnitQuery`
  - `BomMaterialUnitItem`
  - `BomMaterialUnitData`
- 新增只读路由:
  - `GET /api/bom/material-units`
- 新增只读服务:
  - `list_material_units(...)`
  - 基于 BOM item 派生单位视图，无写操作
- 路由顺序:
  - `GET /api/bom/material-units` 位于 `GET /api/bom/{bom_id}` 之前（已核对）

## 3. preserved checks
- BOM 管理列表主语义: PASS
- 物料图库语义: PASS
- 物料采购单语义: PASS
- 面料语义: PASS
- 辅料/包材语义: PASS
- 物料加工类型语义: PASS
- 物料类型语义: PASS
- `/bom/detail` 入口链路: PASS
- 写动作 guarded: PASS
- `shared_route_scope_expanded`: `NO`

## 4. 本地验证
- `git -C '/Users/hh/Desktop/领意服装管理系统' diff --cached --name-only`: 空
- `git -C '/Users/hh/Desktop/领意服装管理系统' diff --check`: PASS（无输出）
- `npm run precheck:dev-runtime`: PASS
- `npm run typecheck`: PASS
- `npm run verify`: PASS

## 5. 浏览器回归（`/bom/list`）
- 脚本: `/tmp/task_y28b_05_impl_browser_check.mjs`
- result_json: `/tmp/task_y28b_05_impl_20260504T041409Z_browser_results.json`
- screenshot_dir: `/tmp/task_y28b_05_impl_20260504T041409Z_screenshots`
- screenshots_count: `6`

### 5.1 结构与语义检查
- `route_open`: true
- `first_screen_visible`: true
- `filters_present`: true
- `structure_mapped`: true
- `fields_or_headers_mapped`: true
- `material_unit_fields_mapped`: true
- `buttons_mapped`: true
- `status_tags_mapped`: true
- `empty_state`: true
- `error_state`: true（一次受控 503 注入验证）
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
