# TASK-Z002B-03-IMPL BOM 创建草稿与保存草稿最小真实写入闭环实现与浏览器回归报告

## 1. 任务范围与结论

- 任务：`TASK-Z002B-03-IMPL`
- 路由范围：`/bom/list`、`/bom/detail`
- 本轮策略：仅放开 `create_bom` 与 `update_bom_draft` 两个真实写动作；`set_default/activate/deactivate/explode` 继续 guarded。
- 结论：在本地测试库完成了「创建草稿 -> 回读详情 -> 保存草稿 -> 列表/详情再回读」最小写入闭环，且禁止动作未触发、零导出下载打印副作用、清理后零残留。

## 2. 实际改动文件（allowlist 内）

1. `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/bom/BomDetail.vue`
2. `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/bom_service.py`
3. `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-Z002B-03-IMPL_BOM创建草稿与保存草稿最小真实写入闭环实现与浏览器回归报告.md`
4. `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/task_z002_bom_draft_write_closure_evidence.json`
5. `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md`

## 3. 本地测试库证明

本轮写入仅在 local_dev SQLite 执行，未连接生产环境。

- 入口文件证据：`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/local_dev.py`
  - `APP_ENV=development`
  - `LINGYI_DB_URL=sqlite:///./lingyi_service.local.db`
- precheck 证据（通过）：
  - `backend_auth_me` = `http://127.0.0.1:8000/api/auth/me` `200`
  - `frontend_auth_me` = `http://127.0.0.1:5174/api/auth/me` `200`

## 4. 关键实现锚点

## 4.1 前端

文件：`/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/bom/BomDetail.vue`

- `data-testid` 与动作锚点：
  - `bom-detail-field-scenario-tag`（场景标记展示）
  - `bom-detail-local-test-db-tip`（本地测试库提示）
  - `allowed:create_bom`、`allowed:update_bom_draft`
- 新增逻辑：
  - `handleCreateDraft()`：真实调用 `createBom`，成功后回读 `fetchBomList` + `fetchBomDetail`
  - `handleSaveDraft()`：真实调用 `updateBomDraft`，成功后回读 `fetchBomList` + `fetchBomDetail`
  - `SCENARIO_TAG_PREFIX='Z002-BOM-DRAFT'` 自动生成场景号
  - 失败 fail-closed：写入失败时设置 `loadError`，不伪造成功态

## 4.2 后端

文件：`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/bom_service.py`

- 新增 local_dev + sqlite 受控兼容逻辑：
  - `_is_local_sqlite_mode()`
  - `_next_manual_pk(...)`
- create/update 明细写入在 sqlite 下显式分配 `id`
- `_validate_item_exists(...)` 增加 local_dev fallback，避免本地无 ERPNext `tabItem` 时阻断最小闭环验证

## 5. 写动作与禁止动作核对

允许并已触发：

1. `POST /api/bom/`（createBom）
2. `PUT /api/bom/{bom_id}`（updateBomDraft）

继续 guarded/未触发：

1. `POST /api/bom/{bom_id}/set-default`
2. `POST /api/bom/{bom_id}/activate`
3. `POST /api/bom/{bom_id}/deactivate`
4. `POST /api/bom/{bom_id}/explode`
5. 上传/下载/导出/打印相关请求

## 6. 浏览器证据

- 证据 JSON：`/tmp/task_z002b03_bom_browser_result_2026-05-12_0333.json`
- 截图目录：`/tmp/task_z002b03_bom_screenshots_2026-05-12_0333`
- 截图数量：`9`

关键断言：

- `route_open=true`
- `first_screen_visible=true`
- `local_test_db_confirmed=true`
- `scenario_tag=Z002-BOM-DRAFT-20260512-001`
- `create_post_triggered=true`
- `detail_get_after_create=true`
- `update_put_triggered=true`
- `list_get_after_update=true`
- `detail_get_after_update=true`
- `approved_write_request_count=2`
- `unexpected_write_request_count=0`
- `forbidden_bom_action_request_count=0`
- `upload_download_export_print_request_count=0`
- `write_request_count=2`
- `unexplained_console_errors_total=0`
- `unexplained_network_4xx_5xx_total=0`

受控 expected 错误：

- `expected_network_4xx_5xx_total=1`（受控 503，用于错误态验证）
- `expected_console_errors_total=1`（对应上述受控错误）

## 7. scenario_tag 与字段载体

- 命名规则：`Z002-BOM-DRAFT-{YYYYMMDD}-{NNN}`
- 本轮值：`Z002-BOM-DRAFT-20260512-001`
- 载体字段：`version_no`（当前 schema 未单独暴露 scenario_tag 字段，因此使用冻结基线允许载体）
- 更新后版本号：`Z002-BOM-DRAFT-20260512-001-U1`

## 8. 测试数据清理与零残留

清理对象前缀：`Z002-BOM-DRAFT-`

清理顺序：

1. `ly_apparel_bom_item`（按 BOM id）
2. `ly_bom_operation`（按 BOM id）
3. `ly_apparel_bom`（按 scenario 前缀）
4. `ly_operation_audit_log`（module=bom 且记录包含 scenario 前缀）

清理后 residual 计数：

- `ly_apparel_bom=0`
- `ly_apparel_bom_item=0`
- `ly_bom_operation=0`
- `ly_operation_audit_log=0`

结论：`zero_residual=true`

## 9. 命令验证结果

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

## 10. 生命周期与越界核对

- 未执行 `git add/commit/push`
- 未执行 `PR/merge/tag/release`
- 未执行 `git reset/restore/clean/delete` 仓库清理
- 未连接生产环境、未回填真实主数据

## 11. 残余风险

1. 本轮仅放开 create/update 草稿；发布、停用、设默认、展开计算仍待后续分任务闭环。
2. local_dev sqlite 兼容分支仅用于本地测试验证，后续联调需再验证 MySQL/ERPNext 主数据口径一致性。
3. `scenario_tag` 目前承载于 `version_no`，如后续要独立字段需单独冻结 schema 迁移任务。
