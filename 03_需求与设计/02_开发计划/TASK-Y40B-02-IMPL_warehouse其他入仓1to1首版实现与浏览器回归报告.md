# TASK-Y40B-02-IMPL `/warehouse` 其他入仓 1:1 首版实现与浏览器回归报告

## 1. 任务与范围
- TASK_ID: `TASK-Y40B-02-IMPL`
- 目标路由: `/warehouse`（shared route）
- 实现语义: `TASK-Y39B-P1-02` 其他入仓（只读）
- 前置基线: `task_y40b_02_warehouse_other_inbound_allowlist_baseline.json`
- 允许改动: `WarehouseDashboard.vue`、`warehouse.ts`、`routers/warehouse.py`、`schemas/warehouse.py`、`services/warehouse_service.py`
- 未触碰: 非 `/warehouse` 路由、`/bom/list`、`/production/plans`、测试代码、控制面文件、GitHub/生产配置

## 2. 实现内容（只读）
### 2.1 前端（`WarehouseDashboard.vue`）
- 新增区块: `物料进销存 / 其他入仓（TASK-Y39B-P1-02）`。
- 新增筛选项:
  - 入仓单号、供应商、物料、仓库、状态。
- 新增展示字段:
  - 入仓单号、供应商、物料编码、物料名称、入仓仓库、库位、入仓数量、入仓金额、入仓日期、来源单号、状态。
- 新增按钮语义（全部受控）:
  - 查询入仓、确认入仓、撤销入仓、导出、打印。
- 新增状态:
  - 空态（暂无其他入仓数据）
  - 错误态（其他入仓加载失败）
  - 权限/禁用态（写动作 guarded 提示）

### 2.2 前端 API（`warehouse.ts`）
- 新增只读 contract:
  - `WarehouseOtherInboundQuery`
  - `WarehouseOtherInboundItem`
  - `WarehouseOtherInboundData`
- 新增只读调用:
  - `fetchWarehouseOtherInbound(...) -> GET /api/warehouse/other-inbound`

### 2.3 后端（`warehouse.py` / `warehouse.py` schema / `warehouse_service.py`）
- 新增只读 schema:
  - `WarehouseOtherInboundItem`
  - `WarehouseOtherInboundData`
- 新增只读路由:
  - `GET /api/warehouse/other-inbound`
- 新增只读服务:
  - `list_other_inbound(...)`
  - 基于现有库存汇总数据做只读聚合映射，不新增写动作。
- 路由遮蔽检查:
  - `@router.get("/other-inbound")` 在 `@router.get("/batches/{batch_no}")` 之前（`738 < 1034`），不存在动态路由遮蔽。

## 3. preserved checks
- P0 成品库存 preserved: PASS
- `TASK-Y18B-05` 仓库管理 preserved: PASS
- `TASK-Y23B-05` 物料库存 preserved: PASS
- 既有权限态 preserved: PASS
- 既有错误态 preserved: PASS
- 既有 guarded 写动作 preserved: PASS
- `shared_route_scope_expanded`: `NO`

## 4. 本地验证
- `git -C '/Users/hh/Desktop/领意服装管理系统' diff --cached --name-only`: 空
- `git -C '/Users/hh/Desktop/领意服装管理系统' diff --check`: PASS（无输出）
- `npm run precheck:dev-runtime`: PASS
- `npm run typecheck`: PASS
- `npm run verify`: PASS

## 5. 浏览器回归（`/warehouse`）
- 脚本: `/tmp/task_y40b_02_impl_browser_check.mjs`
- result_json: `/tmp/task_y40b_02_impl_20260504T112731Z_browser_results.json`
- screenshots:
  - `/tmp/task_y40b_02_impl_20260504T112731Z_screenshots/01_overview_list.png`
  - `/tmp/task_y40b_02_impl_20260504T112731Z_screenshots/02_other_inbound_section.png`
  - `/tmp/task_y40b_02_impl_20260504T112731Z_screenshots/03_guarded_action.png`
  - `/tmp/task_y40b_02_impl_20260504T112731Z_screenshots/04_empty_state.png`
  - `/tmp/task_y40b_02_impl_20260504T112731Z_screenshots/05_error_state.png`
  - `/tmp/task_y40b_02_impl_20260504T112731Z_screenshots/06_permission_disabled_state.png`
- screenshots_count: `6`

### 5.1 结构与语义检查
- `route_open`: true
- `first_screen_visible`: true
- `filters_present`: true
- `other_inbound_fields_mapped`: true
- `buttons_mapped`: true
- `status_tags_mapped`: true
- `empty_state`: true
- `error_state`: true
- `permission_or_disabled_state`: true

### 5.2 preserved 检查
- `p0_finished_goods_preserved`: true
- `warehouse_management_preserved`: true
- `material_inventory_preserved`: true
- `permission_state_preserved`: true
- `error_state_preserved`: true
- `write_actions_guarded`: true

### 5.3 安全与副作用检查
- `write_request_count`: `0`
- `upload_download_export_print_request_count`: `0`
- `console_errors_total`: `0`
- `page_errors_total`: `0`
- `network_4xx_5xx_total`: `0`
- `unexplained_console_errors_total`: `0`
- `unexplained_network_4xx_5xx_total`: `0`

## 6. 禁止项核对
- 未执行 `git add/commit/push`
- 未执行 PR/merge/close/tag/release
- 未执行 cleanup/reset/restore/clean/delete
- 未启动 `TASK-Y39B-P1-03/04/05`
- 未修改 `/bom/list`
- 未修改 `/production/plans`
- 未新增 POST/PUT/PATCH/DELETE 写路由
- 未触发真实上传/下载/导出/打印/写请求
- 未触碰生产/GitHub 管理配置
- parked blockers 未释放
