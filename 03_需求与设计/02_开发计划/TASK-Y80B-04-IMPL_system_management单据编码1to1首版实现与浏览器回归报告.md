# TASK-Y80B-04-IMPL /system/management 单据编码1to1首版实现与浏览器回归报告

## 1. 任务与边界
- TASK_ID: `TASK-Y80B-04-IMPL`
- 路由: `/system/management`
- 来源: `TASK-Y79B-P1-04`（`Y1-113`，页面“单据编码”）
- baseline: `TASK-Y80B-04`（`document_code_semantics_already_present=false`、`allowlist_mismatch=NO`）
- 本轮允许产品改动范围（5 文件）：
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/system/SystemManagement.vue`
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/system_management.ts`
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/system_management.py`
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/system_management.py`
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/system_config_catalog_service.py`

## 2. 实现摘要
- 前端页面（`SystemManagement.vue`）新增“单据编码（TASK-Y79B-P1-04，只读）”区块：
  - `data-testid="document-code-section"`
  - 新增筛选项：单据类型、状态、关键词、更新开始、更新结束
  - 新增字段：编码编号、单据名称、单据类型、编码前缀、流水规则、当前流水号、状态、重置周期、负责人、更新时间、备注
  - 操作按钮：查看（只读）、新增/编辑/启停/预览/重置（guarded）、导出/打印（disabled）
  - 新增只读加载链路：`fetchSystemDocumentCodes` + `loadDocumentCodes`
- 前端 API（`system_management.ts`）新增只读方法：
  - `fetchSystemDocumentCodes`
  - `GET /api/system/document-codes`
- 后端 router（`system_management.py`）新增只读路由：
  - `GET /api/system/document-codes`
  - 权限动作复用 `SYSTEM_READ + SYSTEM_CONFIG_READ`
  - 支持查询参数：`document_type/status/keyword/updated_start_date/updated_end_date`
  - 支持 `keyword=__simulate_error__` 的受控错误注入
- 后端 schema/service 新增只读聚合：
  - schema: `SystemDocumentCodeActionData` / `SystemDocumentCodeItemData` / `SystemDocumentCodeData`
  - service: `_DOCUMENT_CODE_CATALOG` + `list_document_code_catalog(...)`
- route order 说明：
  - 当前 `system_management.py` 无 `/{id}` 动态详情路由，本轮新增静态 GET 路由不存在 route shadowing 风险
- 写路由新增：`NO`（未新增 POST/PUT/PATCH/DELETE）

## 3. preserved 检查
- `/system/management` 既有主语义 preserved: PASS
- 组织框架（Y75B-03）preserved: PASS
- 对接平台（Y75B-05）preserved: PASS
- 系统公告（Y80B-02）preserved: PASS
- 操作日志（Y80B-03）preserved: PASS
- 权限态、空态、错误态、禁用态 preserved: PASS
- guarded 写动作与上传/下载/导出/打印零副作用 preserved: PASS

## 4. 验证结果
- `python3 -m py_compile`（router/schema/service）: PASS
- `npm run precheck:dev-runtime`（`06_前端/lingyi-pc`）: PASS
- `npm run typecheck`（`06_前端/lingyi-pc`）: PASS
- `npm run verify`（`06_前端/lingyi-pc`）: PASS
- `git diff --cached --name-only`: 空
- `git diff --cached --check`: PASS
- `git diff --check`: PASS
- `git diff --name-only -- 06_前端 07_后端`：
  - 前序 dirty：`/permissions/governance` 5 文件 + `/system/management`（系统公告/操作日志）5 文件
  - 本轮仍在 `/system/management` allowlist 5 文件内累积，不涉及 allowlist 外产品路径

## 5. 浏览器回归证据
- 回归路由: `/system/management`
- script: `/tmp/task_y80b_04_impl_browser_check.mjs`
- result_json: `/tmp/task_y80b_04_impl_20260507T200049Z_browser_results.json`
- screenshots_dir: `/tmp/task_y80b_04_impl_20260507T200049Z_screenshots`
- screenshots_count: `6`
- 核心断言：
  - `route_open=true`
  - `first_screen_visible=true`
  - `filters_present=true`
  - `document_code_fields_mapped=true`
  - `buttons_mapped=true`
  - `status_tags_mapped=true`
  - `empty_state=true`
  - `error_state=true`
  - `permission_or_disabled_state=true`
  - `write_request_count=0`
  - `upload_download_export_print_request_count=0`
  - `unexplained_console_errors_total=0`
  - `unexplained_network_4xx_5xx_total=0`
- 说明：
  - 首次回归出现 `/api/system/document-codes` 404（后端旧进程未加载新路由），重启本地后端后复跑通过；最终证据以上述 result_json 为准

## 6. 禁止动作核对
- 未修改 `/permissions/governance` 前序 5 个产品文件: PASS
- 未修改测试代码: PASS
- 未修改 A 控制面文件: PASS
- 未修改 C 审计记录: PASS
- 未执行 `git add/commit/push`: PASS
- 未执行 `PR/merge/tag/release`: PASS
- 未执行 `cleanup/reset/restore/clean/delete`: PASS
- 未启动 `TASK-Y80B-05` 或后续页面: PASS
- 未释放 parked blockers: PASS
