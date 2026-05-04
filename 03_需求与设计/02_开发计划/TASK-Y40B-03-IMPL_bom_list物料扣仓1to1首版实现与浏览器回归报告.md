# TASK-Y40B-03-IMPL `/bom/list` 物料扣仓 1:1 首版实现与浏览器回归报告

## 1. 任务与范围
- TASK_ID: `TASK-Y40B-03-IMPL`
- 目标路由: `/bom/list`（shared route）
- 实现语义: `TASK-Y39B-P1-03` 物料扣仓（只读）
- 前置基线: `task_y40b_03_bom_list_material_deduction_allowlist_baseline.json`
- 允许改动: `BomList.vue`、`bom.ts`、`routers/bom.py`、`schemas/bom.py`、`services/bom_service.py`
- 未触碰: 非 `/bom/list` 路由、`/warehouse`、`/production/plans`、测试代码、控制面文件、GitHub/生产配置

## 2. 实现内容（只读）
### 2.1 前端（`BomList.vue`）
- 新增区块: `物料扣仓（TASK-Y39B-P1-03）`
- 新增筛选项:
  - 款号、扣仓单号、物料编码、扣仓仓库、状态
- 新增展示字段:
  - 扣仓单号、工序编号、物料编码、扣仓仓库、应扣数量、已扣数量、待扣数量、扣仓日期、款号、来源BOM、状态
- 新增按钮语义（全部受控）:
  - 扣仓确认、扣仓冲销、同步、导出、打印
- 新增状态:
  - 空态（暂无物料扣仓数据）
  - 错误态（物料扣仓加载失败）
  - 权限/禁用态（写动作 guarded 提示）

### 2.2 前端 API（`bom.ts`）
- 新增只读 contract:
  - `BomMaterialDeductionItem`
  - `BomMaterialDeductionData`
- 新增只读调用:
  - `fetchBomMaterialDeduction(...) -> GET /api/bom/material-deduction`

### 2.3 后端（`bom.py` / `schemas/bom.py` / `bom_service.py`）
- 新增只读 schema:
  - `BomMaterialDeductionQuery`
  - `BomMaterialDeductionItem`
  - `BomMaterialDeductionData`
- 新增只读路由:
  - `GET /api/bom/material-deduction`
- 新增只读服务:
  - `list_material_deduction(...)`
  - 基于 `LyBomOperation + LyApparelBom + LyApparelBomItem` 聚合扣仓只读视图字段，未引入写动作
- 路由遮蔽检查:
  - `@router.get("/material-deduction")` 在 `@router.get("/{bom_id}")` 之前（`764 < 917`），无动态路由遮蔽

## 3. preserved checks
- BOM 管理列表 preserved: PASS
- `/bom/detail` 入口 preserved: PASS
- 物料图库 preserved: PASS
- 物料采购单 preserved: PASS
- 面料 preserved: PASS
- 辅料/包材 preserved: PASS
- 物料加工类型 preserved: PASS
- 物料类型 preserved: PASS
- 物料单位 preserved: PASS
- 物料加工 preserved: PASS
- 物料加工入仓 preserved: PASS
- write actions guarded: PASS
- `shared_route_scope_expanded`: `NO`

## 4. 本地验证
- `git -C '/Users/hh/Desktop/领意服装管理系统' diff --cached --name-only`: 空
- `git -C '/Users/hh/Desktop/领意服装管理系统' diff --check`: PASS（无输出）
- `npm run precheck:dev-runtime`: PASS
- `npm run typecheck`: PASS
- `npm run verify`: PASS

## 5. 浏览器回归（`/bom/list`）
- 脚本: `/tmp/task_y40b_03_impl_browser_check.mjs`
- result_json: `/tmp/task_y40b_03_impl_20260504T120125Z_browser_results.json`
- screenshots:
  - `/tmp/task_y40b_03_impl_20260504T120125Z_screenshots/01_overview_list.png`
  - `/tmp/task_y40b_03_impl_20260504T120125Z_screenshots/02_material_deduction_section.png`
  - `/tmp/task_y40b_03_impl_20260504T120125Z_screenshots/03_guarded_action.png`
  - `/tmp/task_y40b_03_impl_20260504T120125Z_screenshots/04_error_state.png`
  - `/tmp/task_y40b_03_impl_20260504T120125Z_screenshots/05_detail_entry_preserved.png`
  - `/tmp/task_y40b_03_impl_20260504T120125Z_screenshots/06_permission_disabled_state.png`
- screenshots_count: `6`

### 5.1 结构与语义检查
- `route_open`: true
- `first_screen_visible`: true
- `filters_present`: true
- `material_deduction_fields_mapped`: true
- `buttons_mapped`: true
- `status_tags_mapped`: true
- `empty_state`: true
- `error_state`: true（一次受控 503 注入验证）
- `permission_or_disabled_state`: true

### 5.2 preserved 检查
- `bom_list_preserved`: true
- `bom_detail_entry_preserved`: true
- `material_gallery_preserved`: true
- `purchase_order_preserved`: true
- `fabric_preserved`: true
- `accessories_packaging_preserved`: true
- `processing_type_preserved`: true
- `material_type_preserved`: true
- `material_unit_preserved`: true
- `material_processing_preserved`: true
- `material_processing_inbound_preserved`: true
- `write_actions_guarded`: true

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
- 未启动 `TASK-Y39B-P1-04/05`
- 未修改 `/warehouse`
- 未修改 `/production/plans`
- 未新增 POST/PUT/PATCH/DELETE 写路由
- 未触发真实上传/下载/导出/打印/写请求
- 未触碰生产/GitHub 管理配置
- parked blockers 未释放
