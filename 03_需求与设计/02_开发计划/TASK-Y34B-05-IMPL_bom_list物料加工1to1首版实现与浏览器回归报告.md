# TASK-Y34B-05-IMPL `/bom/list` 物料加工 1:1 首版实现与浏览器回归报告

## 1. 任务与范围
- TASK_ID: `TASK-Y34B-05-IMPL`
- 目标路由: `/bom/list`（shared route）
- 实现语义: `TASK-Y33B-P1-05` 物料加工（只读）
- 前置基线: `task_y34b_05_bom_list_material_processing_allowlist_baseline.json`
- 允许改动: `BomList.vue`、`bom.ts`、`bom.py`、`schemas/bom.py`、`bom_service.py`
- 未触碰: 非 `/bom/list` 路由、`/production/plans`、测试/控制面/GitHub/生产配置

## 2. 实现内容（只读）
### 2.1 前端（`BomList.vue`）
- 新增区块: `物料加工（TASK-Y33B-P1-05）`
- 新增筛选项:
  - 款号、工序编号、工序名称、加工供应商、加工方式、状态
- 新增展示字段:
  - 工序编号、工序名称、加工供应商、加工方式、计划数量、完成数量、待完成数量、损耗数量、单位、计划完成日、款号、来源BOM、状态
- 新增按钮语义（全部受控）:
  - 新增加工、编辑、删除、提交审核、同步、导出、打印、查看
- 新增状态:
  - 空态（暂无物料加工数据）
  - 错误态（物料加工加载失败）
  - 权限/禁用态（写动作禁用 + guarded 提示）

### 2.2 前端 API（`bom.ts`）
- 新增只读 contract:
  - `BomMaterialProcessingQuery`
  - `BomMaterialProcessingItem`
  - `BomMaterialProcessingData`
- 新增只读调用:
  - `fetchBomMaterialProcessing(...) -> GET /api/bom/material-processing`

### 2.3 后端（`bom.py` / `schemas/bom.py` / `bom_service.py`）
- 新增只读 schema:
  - `BomMaterialProcessingQuery`
  - `BomMaterialProcessingItem`
  - `BomMaterialProcessingData`
- 新增只读路由:
  - `GET /api/bom/material-processing`
- 新增只读服务:
  - `list_material_processing(...)`
  - 基于 BOM 工序行聚合展示字段（工序编号、加工方式、供应商、计划/完成/待完成/损耗数量等），无写动作
- 路由顺序检查:
  - `GET /api/bom/material-processing` 位于 `GET /api/bom/{bom_id}` 前（`/{bom_id}` 在 `bom.py` 第 809 行）

## 3. preserved checks
- BOM 管理列表语义: PASS
- 物料图库语义: PASS
- 物料采购单语义: PASS
- 面料语义: PASS
- 辅料/包材语义: PASS
- 物料加工类型语义: PASS
- 物料类型语义: PASS
- 物料单位语义: PASS
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
- 脚本: `/tmp/task_y34b_05_impl_browser_check.mjs`
- result_json: `/tmp/task_y34b_05_impl_20260504T084733Z_browser_results.json`
- screenshots:
  - `/tmp/task_y34b_05_impl_20260504T084733Z_screenshots/01_overview_list.png`
  - `/tmp/task_y34b_05_impl_20260504T084733Z_screenshots/02_material_processing_section.png`
  - `/tmp/task_y34b_05_impl_20260504T084733Z_screenshots/03_guarded_action.png`
  - `/tmp/task_y34b_05_impl_20260504T084733Z_screenshots/04_error_state.png`
  - `/tmp/task_y34b_05_impl_20260504T084733Z_screenshots/05_detail_entry_preserved.png`
  - `/tmp/task_y34b_05_impl_20260504T084733Z_screenshots/06_permission_disabled_state.png`
- screenshots_count: `6`

### 5.1 结构与语义检查
- `route_open`: true
- `first_screen_visible`: true
- `filters_present`: true
- `material_processing_fields_mapped`: true
- `buttons_mapped`: true
- `status_tags_mapped`: true
- `empty_state`: true
- `error_state`: true（一次受控 503 注入验证）
- `permission_or_disabled_state`: true

### 5.2 preserved 检查
- `bom_list_preserved_check`: true
- `material_gallery_preserved_check`: true
- `purchase_order_preserved_check`: true
- `fabric_preserved_check`: true
- `accessories_packaging_preserved_check`: true
- `processing_type_preserved_check`: true
- `material_type_preserved_check`: true
- `material_unit_preserved_check`: true
- `bom_detail_entry_preserved_check`: true
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
- 未启动新 P1/P2 页面
- 未修改非 `/bom/list` 路由
- 未新增 POST/PUT/PATCH/DELETE 写路由
- 未触发真实上传/下载/导出/打印/写请求
- 未触碰生产/GitHub 管理配置
- parked blockers 未释放
