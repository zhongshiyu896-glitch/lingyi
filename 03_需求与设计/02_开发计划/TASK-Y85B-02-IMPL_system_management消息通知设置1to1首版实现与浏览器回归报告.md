# TASK-Y85B-02-IMPL /system/management 消息通知设置1to1首版实现与浏览器回归报告

## 1. 任务与边界
- TASK_ID: `TASK-Y85B-02-IMPL`
- 路由: `/system/management`
- 来源: `TASK-Y84B-P1-02`（`Y1-116`，页面“消息通知设置”）
- baseline: `TASK-Y85B-02`（`message_notification_settings_semantics_already_present=false`、`allowlist_mismatch=NO`）
- 本轮允许产品改动范围（5 文件）:
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/system/SystemManagement.vue`
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/system_management.ts`
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/system_management.py`
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/system_management.py`
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/system_config_catalog_service.py`

## 2. 实现摘要
- 前端页面（`SystemManagement.vue`）新增“消息通知设置（TASK-Y84B-P1-02，只读）”区块：
  - `data-testid="message-notification-settings-section"`
  - 新增筛选项：通知渠道、状态、目标范围、关键词、更新开始、更新结束
  - 新增字段：设置编号、设置名称、通知渠道、目标范围、推送模式、触发事件、状态、负责人、更新时间、备注
  - 操作按钮：查看（只读）、编辑/启停/测试发送（guarded）、导出/打印（disabled）
  - 新增只读加载链路：`fetchSystemMessageNotificationSettings` + `loadMessageNotificationSettings`
- 前端 API（`system_management.ts`）新增只读方法：
  - `fetchSystemMessageNotificationSettings`
  - `GET /api/system/message-notification-settings`
- 后端 router（`system_management.py`）新增只读路由：
  - `GET /api/system/message-notification-settings`
  - 权限动作复用 `SYSTEM_READ + SYSTEM_CONFIG_READ`
  - 支持查询参数：`channel/status/target_scope/keyword/updated_start_date/updated_end_date`
  - 支持 `keyword=__simulate_error__` 受控错误注入
- 后端 schema/service 新增只读聚合：
  - schema: `SystemMessageNotificationSettingActionData` / `SystemMessageNotificationSettingItemData` / `SystemMessageNotificationSettingsData`
  - service: `_MESSAGE_NOTIFICATION_SETTINGS_CATALOG` + `list_message_notification_settings_catalog(...)`
- route order 说明：
  - 当前 `system_management.py` 无 `/{id}` 动态详情 GET 路由，本轮新增静态 GET 不存在 route shadowing 风险
- 写路由新增: `NO`（未新增 POST/PUT/PATCH/DELETE）

## 3. preserved 检查
- `/system/management` 既有主语义 preserved: PASS
- 组织框架（Y75B-03）preserved: PASS
- 对接平台（Y75B-05）preserved: PASS
- 系统公告（Y80B-02）preserved: PASS
- 操作日志（Y80B-03）preserved: PASS
- 单据编码（Y80B-04）preserved: PASS
- 系统参数（Y85B-01）preserved: PASS
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

## 5. 浏览器回归证据
- 回归路由: `/system/management`
- script: `/tmp/task_y85b_02_impl_browser_check.mjs`
- result_json: `/tmp/task_y85b_02_impl_20260507T230119Z_browser_results.json`
- screenshots_dir: `/tmp/task_y85b_02_impl_20260507T230119Z_screenshots`
- screenshots_count: `6`
- 核心断言:
  - `route_open=true`
  - `first_screen_visible=true`
  - `filters_present=true`
  - `message_notification_settings_fields_mapped=true`
  - `buttons_mapped=true`
  - `status_tags_mapped=true`
  - `empty_state=true`
  - `error_state=true`
  - `permission_or_disabled_state=true`
  - `write_request_count=0`
  - `upload_download_export_print_request_count=0`
  - `unexplained_console_errors_total=0`
  - `unexplained_network_4xx_5xx_total=0`
- 说明:
  - 错误态通过 `keyword=__simulate_error__` 触发，`network_4xx_5xx_total=1` 与 `console_errors_total=1` 均为 expected，不计入 unexplained

## 6. 禁止动作核对
- 未修改 allowlist 外产品文件: PASS
- 未修改测试代码: PASS
- 未修改 A 控制面文件: PASS
- 未修改 C 审计记录: PASS
- 未执行 `git add/commit/push`: PASS
- 未执行 `PR/merge/tag/release`: PASS
- 未执行 `cleanup/reset/restore/clean/delete`: PASS
- 未启动 `TASK-Y85B-03` 或后续页面: PASS
- 未释放 parked blockers: PASS
