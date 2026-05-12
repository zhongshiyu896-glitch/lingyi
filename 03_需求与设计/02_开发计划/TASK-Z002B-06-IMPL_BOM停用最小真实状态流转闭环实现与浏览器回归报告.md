# TASK-Z002B-06-IMPL BOM停用最小真实状态流转闭环实现与浏览器回归报告

## 1. 任务范围与结论

- 任务：`TASK-Z002B-06-IMPL`
- 路由范围：`/bom/detail`（回读包含 `/bom/list`）
- 本轮目标：在本地测试库打开 `deactivate_bom` 最小真实状态流转闭环
- 结论：已完成「场景数据准备 -> 发布设默认 -> 停用 -> 详情/列表回读 -> 重复停用 fail-closed -> 清理零残留」闭环，禁止动作未触发。

## 2. 改动文件（allowlist 内）

1. `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/bom/BomDetail.vue`
2. `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-Z002B-06-IMPL_BOM停用最小真实状态流转闭环实现与浏览器回归报告.md`
3. `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/task_z002_bom_deactivate_closure_evidence.json`
4. `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md`

说明：`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/bom_service.py` 当前仍在产品 dirty 中，属于前序 `TASK-Z002B-03/04/05` 已 C PASS 残留，本轮未新增后端逻辑。

## 3. 本地测试库证明

- 入口文件：`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/local_dev.py`
  - `APP_ENV=development`
  - `LINGYI_DB_URL=sqlite:///./lingyi_service.local.db`
- precheck 复验（PASS）：
  - `http://127.0.0.1:8000/api/auth/me` = 200
  - `http://127.0.0.1:5174/api/auth/me` = 200

## 4. 关键实现锚点

文件：`/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/bom/BomDetail.vue`

- 新增 `deactivateBom` API 引入与 `deactivatingBom` 状态位。
- 新增 `canDeactivate` 权限判定，停用按钮由 guarded-only 改为受控真实写入：
  - `data-write-guard="allowed:deactivate_bom"`（无权限仍为 guarded）。
- 新增 `handleDeactivateBom()`：
  - 前置校验：权限、`bom_id`、当前状态必须可停用。
  - 执行 `POST /api/bom/{bom_id}/deactivate`。
  - 成功后触发详情回读与列表回读（`active/inactive`），并刷新状态与默认标记展示。
  - 重复停用或非法停用 fail-closed，不伪造成功。
- 停用进行中禁用 `set_default/activate/explode`，避免并发写动作。
- 本轮场景前缀切换：`SCENARIO_TAG_PREFIX=Z002-BOM-DEACTIVATE`，并沿用 `version_no` 作为场景载体。

## 5. 真实写请求与禁止动作核对

允许并触发（本地测试库）：

1. `POST /api/bom/` ×1（场景数据准备）
2. `PUT /api/bom/{bom_id}` ×1（草稿更新）
3. `POST /api/bom/{bom_id}/activate` ×1（发布）
4. `POST /api/bom/{bom_id}/set-default` ×1（设默认）
5. `POST /api/bom/{bom_id}/deactivate` ×1（本轮目标动作）

禁止并未触发：

1. BOM allowlist 外写请求
2. 上传/下载/导出/打印请求
3. 生产库写入

## 6. 状态流转与默认标记证明

- 停用前：scenario BOM 为 `active` 且可设为默认。
- 停用后：
  - `status_after_deactivate_mapped=true`
  - `default_cleared_or_ineligible_verified=true`
  - `detail_get_after_deactivate=true`
  - `list_get_after_deactivate=true`
- 重复停用或非法停用：
  - `repeated_or_invalid_deactivate_fail_closed=true`
  - 页面给出失败反馈，不伪造成功态。

## 7. scenario_tag 与载体

- 规则：`Z002-BOM-DEACTIVATE-{YYYYMMDD}-{NNN}`
- 本轮值：`Z002-BOM-DEACTIVATE-20260512-001`
- 字段载体：`version_no`

## 8. 浏览器证据

- 证据 JSON：`/tmp/task_z002b06_bom_browser_result_2026-05-12_162746.json`
- 汇总证据：`/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/task_z002_bom_deactivate_closure_evidence.json`
- 截图目录：`/tmp/task_z002b06_bom_screenshots_2026-05-12_162746`
- 截图数量：`8`

关键断言：

- `route_open=true`
- `first_screen_visible=true`
- `local_test_db_confirmed=true`
- `deactivate_post_triggered=true`
- `deactivate_post_count=1`
- `status_after_deactivate_mapped=true`
- `default_cleared_or_ineligible_verified=true`
- `detail_get_after_deactivate=true`
- `list_get_after_deactivate=true`
- `repeated_or_invalid_deactivate_fail_closed=true`
- `unexpected_write_request_count=0`
- `production_write_count=0`
- `upload_download_export_print_request_count=0`
- `unexplained_console_errors_total=0`
- `unexplained_network_4xx_5xx_total=0`

## 9. 清理顺序与 zero_residual

- 清理结果文件：`/tmp/task_z002b06_cleanup_result.json`
- 清理前缀：`Z002-BOM-DEACTIVATE-`
- 清理顺序：
  1. `ly_apparel_bom_item`
  2. `ly_bom_operation`
  3. `ly_operation_audit_log`
  4. `ly_apparel_bom`
- 清理后 residual：
  - `ly_apparel_bom=0`
  - `ly_apparel_bom_item=0`
  - `ly_bom_operation=0`
  - `ly_operation_audit_log=0`
- 结论：`rollback_cleanup_executed=true`，`zero_residual=true`

## 10. 命令验证结果

- `python3 -m py_compile app/routers/bom.py app/schemas/bom.py app/services/bom_service.py`：PASS
- `npm run precheck:dev-runtime`：PASS
- `npm run typecheck`：PASS
- `npm run verify`：PASS
- `git diff --cached --name-only`：EMPTY
- `git diff --cached --check`：PASS
- `git diff --check`：PASS
- `git diff --name-only -- 06_前端 07_后端`：仅
  - `06_前端/lingyi-pc/src/views/bom/BomDetail.vue`
  - `07_后端/lingyi_service/app/services/bom_service.py`

## 11. 生命周期与越界核对

- 未执行 `git add/commit/push`
- 未执行 `PR/merge/tag/release`
- 未执行 `git reset/restore/clean/delete`
- 未连接生产环境，未回填真实主数据

## 12. 残余风险

1. 本轮仅闭合 `deactivate_bom` 最小状态流转，更多业务规则（例如多版本协同停用策略）仍需后续切片明确。
2. 目前回归在本地 SQLite 测试库通过，联调到其他数据库方言时仍需复核状态枚举与唯一性约束行为一致性。
