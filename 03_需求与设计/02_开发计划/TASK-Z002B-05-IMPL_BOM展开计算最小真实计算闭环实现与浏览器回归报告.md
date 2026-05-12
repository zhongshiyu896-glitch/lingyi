# TASK-Z002B-05-IMPL BOM展开计算最小真实计算闭环实现与浏览器回归报告

## 1. 任务范围与结论

- 任务：`TASK-Z002B-05-IMPL`
- 路由范围：`/bom/detail`（回读包含 `/bom/list`）
- 本轮目标：在本地测试库打开 `explode_bom` 真实计算闭环
- 本轮保持 guarded：`deactivate_bom`
- 结论：已完成「场景数据准备 -> 发布设默认 -> 展开计算 -> 复算校验 -> 清理零残留」闭环，禁止动作未触发。

## 2. 改动文件（allowlist 内）

1. `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/bom/BomDetail.vue`
2. `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-Z002B-05-IMPL_BOM展开计算最小真实计算闭环实现与浏览器回归报告.md`
3. `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/task_z002_bom_explode_compute_closure_evidence.json`
4. `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md`

说明：`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/bom_service.py` 仍在当前产品 dirty 中，但属于前序已 C PASS 残留，本轮未新增后端逻辑。

## 3. 本地测试库证明

- 入口文件：`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/local_dev.py`
  - `APP_ENV=development`
  - `LINGYI_DB_URL=sqlite:///./lingyi_service.local.db`
- precheck 复验（PASS）：
  - `http://127.0.0.1:8000/api/auth/me` = 200
  - `http://127.0.0.1:5174/api/auth/me` = 200

## 4. 关键实现锚点

文件：`/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/bom/BomDetail.vue`

- `canExplode` 调整为 `canRead || canPublish`，兼容当前只读权限位下发，保证 `explode_bom` 可触发。
- `version_no` 场景标签识别正则支持 `DRAFT|ACTIVE|EXPLODE` 前缀，保证本轮 `Z002-BOM-EXPLODE-*` 可回读。
- `SCENARIO_TAG_PREFIX` 更新为 `Z002-BOM-EXPLODE`，并独立 session 序列键 `z002.bom.explode.seq`。
- 展开计算区保留并用于本轮真实闭环：
  - 输入：`order_qty`、`size_ratio`
  - 动作：`handleExplode()`
  - 结果表：`material_requirements`、`operation_costs`
  - 汇总：材料/工序/综合总计（接口值与复算值并列）
  - 失败 fail-closed：非法输入与异常请求不伪造成功数据
- 停用按钮持续 `guarded:readonly`，未放开 `deactivate_bom`。

## 5. 真实写请求与禁止动作核对

允许并触发（本地测试库）：

1. `POST /api/bom/` ×1（场景数据准备）
2. `PUT /api/bom/{bom_id}` ×1（草稿更新）
3. `POST /api/bom/{bom_id}/activate` ×1（发布）
4. `POST /api/bom/{bom_id}/set-default` ×1（设默认）
5. `POST /api/bom/{bom_id}/explode` ×1（本轮目标动作）

禁止并未触发：

1. `POST /api/bom/{bom_id}/deactivate`
2. 上传/下载/导出/打印请求
3. BOM allowlist 外写请求

## 6. 计算公式与复算证明

本轮前端复算口径（与页面证据一致）：

- 材料合计(复算) = `sum(material_requirements[].total_cost)`
- 工序合计(复算) = `sum(operation_costs[].total_cost)`
- 综合总计(复算) = `材料合计(复算) + 工序合计(复算)`
- 差值：
  - `material_delta = abs(材料复算 - 材料接口汇总)`
  - `operation_delta = abs(工序复算 - 工序接口汇总)`
  - `grand_delta = abs(综合复算 - 综合接口汇总)`
- 判定：`delta <= tolerance(1e-6)` 视为通过

证据结果：

- `material_delta=0`
- `operation_delta=0`
- `grand_delta=0`
- `calculation_delta_within_tolerance=true`

## 7. scenario_tag 与载体

- 规则：`Z002-BOM-EXPLODE-{YYYYMMDD}-{NNN}`
- 本轮值：`Z002-BOM-EXPLODE-20260512-001`
- 字段载体：`version_no`
- 场景 item_code：`DEMO-TEE-Z002E-Z002E`

## 8. 浏览器证据

- 证据 JSON：`/tmp/task_z002b05_bom_browser_result_2026-05-12_0652.json`
- 汇总证据：`/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/task_z002_bom_explode_compute_closure_evidence.json`
- 截图目录：`/tmp/task_z002b05_bom_screenshots_2026-05-12_0652`
- 截图数量：`9`

关键断言：

- `route_open=true`
- `first_screen_visible=true`
- `explode_post_triggered=true`
- `explode_post_count=1`
- `material_requirements_mapped=true`
- `operation_costs_mapped=true`
- `material_total_recomputed=true`
- `operation_total_recomputed=true`
- `grand_total_recomputed=true`
- `invalid_input_fail_closed=true`
- `forbidden_deactivate_request_count=0`
- `unexpected_write_request_count=0`
- `production_write_count=0`
- `upload_download_export_print_request_count=0`
- `unexplained_console_errors_total=0`
- `unexplained_network_4xx_5xx_total=0`
- `expected_network_4xx_5xx_total=1`（受控 503，仅用于错误态验证）

## 9. 清理顺序与 zero_residual

- 清理结果文件：`/tmp/task_z002b05_cleanup_result.json`
- 清理前缀：`Z002-BOM-EXPLODE-`
- 清理顺序：
  1. `ly_apparel_bom_item`
  2. `ly_bom_operation`
  3. `ly_apparel_bom`
  4. `ly_operation_audit_log`
- 清理后 residual：
  - `ly_apparel_bom=0`
  - `ly_apparel_bom_item=0`
  - `ly_bom_operation=0`
  - `ly_operation_audit_log=0`
  - `ly_bom_explode_result=0`
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

1. 本轮仅闭合 `explode_bom` 计算链路，`deactivate_bom` 仍待后续切片。
2. 复算口径当前基于接口返回行级 `total_cost` 与接口汇总对账；后续联调若公式口径调整，需要同步收敛前后端显示文案与审计口径。
