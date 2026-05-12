# TASK-Z002B-04-IMPL BOM发布与设为默认最小真实状态流转闭环实现与浏览器回归报告

## 1. 任务范围与结论

- 任务：`TASK-Z002B-04-IMPL`
- 路由范围：`/bom/list`、`/bom/detail`
- 本轮放开真实写动作：`activate_bom`、`set_default_bom`
- 本轮保持 guarded：`deactivate_bom`、`explode_bom`
- 结论：在本地测试库完成「创建草稿 -> 发布 -> 设默认 -> 同款默认唯一性切换 -> 回读验证 -> 清理零残留」闭环，且禁止动作未触发。

## 2. 实际改动文件（allowlist 内）

1. `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/bom/BomDetail.vue`
2. `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/bom_service.py`
3. `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-Z002B-04-IMPL_BOM发布与设为默认最小真实状态流转闭环实现与浏览器回归报告.md`
4. `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/task_z002_bom_activate_default_closure_evidence.json`
5. `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md`

## 3. 本地测试库证明

- 入口文件：`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/local_dev.py`
  - `APP_ENV=development`
  - `LINGYI_DB_URL=sqlite:///./lingyi_service.local.db`
- precheck 复验（PASS）：
  - `http://127.0.0.1:8000/api/auth/me` = 200
  - `http://127.0.0.1:5174/api/auth/me` = 200

## 4. 关键实现锚点

### 4.1 前端

文件：`/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/bom/BomDetail.vue`

- 写动作放开：
  - `handleActivateBom()`：真实调用 `activateBom`
  - `handleSetDefault()`：真实调用 `setDefaultBom`
- 权限兼容：
  - `canSetDefault = set_default || publish`（兼容当前权限位下发）
- 场景与审计锚点：
  - `bom-detail-default-tag`
  - `bom-detail-field-scenario-tag`
  - `bom-detail-field-scenario-tags`
  - `bom-detail-local-test-db-tip`
  - `bom-detail-action-feedback`
- guarded 保持：
  - 停用、展开计算等按钮继续 `guarded:readonly`
- 失败 fail-closed：
  - `activate/set-default` 异常时写入 `loadError`，不伪造成功态

### 4.2 后端

文件：`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/bom_service.py`

- `create_bom()` 入口增加 sqlite 语义修正：
  - `_ensure_local_sqlite_partial_default_index()`
- `_is_local_sqlite_mode()` 调整为按 `dialect == sqlite` 判断
- 新增 `_ensure_local_sqlite_partial_default_index()`：
  - 将 sqlite 上 `uk_ly_apparel_bom_one_active_default` 修正为 partial unique：
  - `WHERE is_default = 1 AND status = 'active'`
- 目的：保证「同 item_code 仅 active+default 唯一」语义与生产数据库一致。

## 5. 本轮真实写动作与禁止动作核对

允许并触发（本地测试库）：

1. `POST /api/bom/`（准备测试草稿 2 条）
2. `POST /api/bom/{bom_id}/activate`（2 次）
3. `POST /api/bom/{bom_id}/set-default`（2 次）

禁止并未触发：

1. `POST /api/bom/{bom_id}/deactivate`
2. `POST /api/bom/{bom_id}/explode`
3. 上传、下载、导出、打印相关请求
4. BOM allowlist 之外写请求

## 6. 浏览器证据

- 证据 JSON：`/tmp/task_z002b04_bom_browser_result_2026-05-12_0557.json`
- 截图目录：`/tmp/task_z002b04_bom_screenshots_2026-05-12_0557`
- 截图数量：`12`

关键断言：

- `route_open=true`
- `first_screen_visible=true`
- `local_test_db_confirmed=true`
- `production_write_count=0`
- `scenario_tags=[Z002-BOM-ACTIVE-20260512-001, Z002-BOM-ACTIVE-20260512-002]`
- `create_post_count=2`
- `activate_post_count=2`
- `set_default_post_count=2`
- `approved_write_request_count=6`
- `same_item_default_uniqueness_verified=true`
- `second_set_default_clears_first=true`
- `active_status_visible=true`
- `default_badge_visible=true`
- `forbidden_bom_action_request_count=0`
- `unexpected_write_request_count=0`
- `upload_download_export_print_request_count=0`
- `unexplained_console_errors_total=0`
- `unexplained_network_4xx_5xx_total=0`
- `expected_network_4xx_5xx_total=1`（受控 503，用于错误态验证）
- `expected_console_errors_total=1`（对应受控 503）

## 7. scenario_tag 与字段载体

- 命名规则：`Z002-BOM-ACTIVE-{YYYYMMDD}-{NNN}`
- 本轮值：
  - `Z002-BOM-ACTIVE-20260512-001`
  - `Z002-BOM-ACTIVE-20260512-002`
- 载体字段：`version_no`（当前 schema 未提供独立 scenario_tag 字段）

## 8. 默认唯一性证据

- 场景：同一 `item_code` 下创建两条 BOM（A、B），均发布为 active。
- 顺序：
  1. A 设默认
  2. B 设默认
- 回读结果：
  - B：`is_default=true`
  - A：默认标记被解除
- 断言：`same_item_default_uniqueness_verified=true`

## 9. 清理与零残留

- 清理结果文件：`/tmp/task_z002b04_cleanup_result.json`
- 清理前缀：`Z002-BOM-ACTIVE-`

清理顺序：

1. `ly_apparel_bom_item`
2. `ly_bom_operation`
3. `ly_apparel_bom`
4. `ly_operation_audit_log`

清理后 residual：

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

1. 本轮仅放开 `activate/set-default`，`deactivate/explode` 仍待后续切片。
2. local_dev sqlite 兼容语义已校正并通过本地验证，仍需后续联调验证目标数据库一致性。
3. 本轮 `scenario_item_code` 来源于历史前缀叠加样本，虽不影响默认唯一性验证，但后续建议统一场景款号归一策略。
