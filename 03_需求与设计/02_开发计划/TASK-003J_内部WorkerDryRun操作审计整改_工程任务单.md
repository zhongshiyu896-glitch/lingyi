# 工程任务单：TASK-003J 内部 Worker Dry-Run 操作审计整改

- 任务编号：TASK-003J
- 模块：工票/车间管理
- 优先级：P1
- 任务类型：审计整改 / 内部诊断接口 / 操作审计闭环
- 创建时间：2026-04-12 16:37 CST
- 作者：技术架构师
- 审计来源：TASK-003I 审计意见，内部 Worker 的 `dry_run=true` 路径不写操作审计，敏感内部诊断接口存在不可追溯调用

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-003J
模块：工票/车间管理
优先级：P1（审计整改，必须先于 TASK-003 总体验收）
════════════════════════════════════════════════════════════════════════════

【任务目标】
补齐 `/api/workshop/internal/job-card-sync/run-once?dry_run=true` 的操作审计，或在生产环境默认禁用 dry-run，确保内部 Worker 诊断调用可追溯、可审计、不可静默执行。

【问题背景】
TASK-003I 已实现默认不扫描越权 outbox、显式诊断才触发、冷却期去重，避免安全审计放大。审计继续指出：`dry_run=true` 虽然不写 ERPNext、不锁定 outbox、不写成功 sync_log，但它仍会读取内部 outbox、服务账号 scope、诊断候选和敏感生产同步状态。如果 dry-run 调用不写操作审计，运维或服务账号可以反复探测内部同步数据而无操作留痕。

【涉及文件】
新建或修改：
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/workshop.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/workshop_job_card_sync_worker.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/audit_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/service_account_policy.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/config.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/error_codes.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/exceptions.py`

测试文件：
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_workshop_job_card_sync.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_workshop_worker_permissions.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_workshop_outbox_audit_throttle.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_security_audit.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_audit_log.py`

【接口清单】
| 接口名称 | HTTP 方法 | 路径 | 入参 | 出参 |
| --- | --- | --- | --- | --- |
| 内部 Job Card 同步 Worker 单次执行 | POST | `/api/workshop/internal/job-card-sync/run-once` | `batch_size`, `dry_run`, `include_forbidden_diagnostics` | `dry_run`, `would_process_count`, `processed_count`, `succeeded_count`, `failed_count`, `blocked_scope_count`, `forbidden_diagnostic_count` |

【核心设计决策】
1. `dry_run=true` 属于敏感内部诊断行为，即使不改业务数据，也必须写操作审计。
2. 生产环境默认禁用 dry-run，除非显式开启 `WORKSHOP_ENABLE_WORKER_DRY_RUN=true`。
3. 生产环境禁用 dry-run 时，接口返回 `WORKSHOP_DRY_RUN_DISABLED`，并写安全审计。
4. dry-run 授权仍沿用 TASK-003F/TASK-003G/TASK-003H/TASK-003I 的内部 Worker 权限、服务账号 scope、诊断节流和审计去重规则。
5. dry-run 只能读候选，不得锁定 outbox，不得增加 attempts，不得更新 `next_retry_at`，不得调用 ERPNext，不得写成功 sync_log。
6. dry-run 成功返回前必须写操作审计；操作审计失败必须返回 `AUDIT_WRITE_FAILED`，不得静默成功。
7. dry-run 操作审计必须记录：`principal`、`dry_run=true`、`batch_size`、`include_forbidden_diagnostics`、`would_process_count`、`forbidden_diagnostic_count`、`blocked_scope_count`、`request_id`。
8. 操作审计不得记录 Authorization、Cookie、service token、secret、password 明文。
9. 如果 dry-run 同时启用 forbidden diagnostics，安全审计去重仍按 TASK-003I 执行，操作审计仍必须写 1 条本次 dry-run 调用记录。
10. 普通用户、普通车间角色、无 `workshop:job_card_sync_worker` 的用户请求 dry-run 时，仍返回 `AUTH_FORBIDDEN` 并写安全审计。

【配置项】
| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `WORKSHOP_ENABLE_WORKER_DRY_RUN` | `false` | 生产环境是否允许内部 Worker dry-run |
| `WORKSHOP_DRY_RUN_AUDIT_REQUIRED` | `true` | dry-run 是否强制写操作审计，生产不可关闭 |

【业务规则】
1. `APP_ENV=production` 且 `WORKSHOP_ENABLE_WORKER_DRY_RUN=false` 时，`dry_run=true` 必须返回 `WORKSHOP_DRY_RUN_DISABLED`。
2. dry-run 被禁用时不得查询 outbox 候选，不得调用 ERPNext，不得写操作审计，但必须写安全审计。
3. dry-run 被允许且授权通过时，可以查询当前服务账号有权候选，但不得执行任何业务写操作。
4. dry-run 被允许且授权通过时，必须写操作审计。
5. dry-run 操作审计写入失败时，接口返回 `AUDIT_WRITE_FAILED`，不得返回成功响应。
6. dry-run 响应中的数量只能是统计值，不得返回完整 outbox payload、完整权限列表或敏感凭证。
7. dry-run 不得改变 `ys_workshop_job_card_sync_outbox.status/attempts/locked_by/locked_at/next_retry_at`。
8. dry-run 不得新增成功 `ys_workshop_job_card_sync_log`。
9. dry-run 不得调用 ERPNext Job Card 写接口。
10. dry-run 不得削弱 TASK-003H 的“先 scope 过滤再 limit”规则。
11. dry-run 不得绕过 TASK-003I 的 forbidden diagnostics 显式开关、扫描上限、冷却期和 dedupe 规则。
12. 每一次授权 dry-run 调用都必须有 1 条 `ly_audit_log` 操作审计记录，即使本次 `would_process_count=0`。

【错误码要求】
| 场景 | HTTP 状态 | code | 要求 |
| --- | --- | --- | --- |
| 生产环境 dry-run 未开启 | 403 | `WORKSHOP_DRY_RUN_DISABLED` | 写安全审计，不查询 outbox |
| 未登录调用 dry-run | 401 | `AUTH_UNAUTHORIZED` | 写安全审计 |
| 无内部 Worker 权限调用 dry-run | 403 | `AUTH_FORBIDDEN` | 写安全审计 |
| 服务账号无资源 scope | 403 | `SERVICE_ACCOUNT_RESOURCE_FORBIDDEN` | 写安全审计，不查询全量 outbox |
| 权限来源不可用 | 503 | `PERMISSION_SOURCE_UNAVAILABLE` | 写安全审计，不查询 outbox |
| dry-run 操作审计写入失败 | 500 | `AUDIT_WRITE_FAILED` | 不返回成功，不调用 ERPNext |
| dry-run 成功 | 200 | `0` | 写操作审计，不改业务状态 |

【数据库表】
| 表名 | 用途 | 本任务要求 |
| --- | --- | --- |
| `ly_schema.ly_audit_log` | 操作审计 | 每次授权 dry-run 成功必须新增 1 条 |
| `ly_schema.ly_security_audit_log` | 安全审计 | dry-run 禁用、未登录、无权限、权限源失败必须写入 |
| `ly_schema.ys_workshop_job_card_sync_outbox` | 同步 outbox | dry-run 不得更新状态、attempts、锁字段、重试时间 |
| `ly_schema.ys_workshop_job_card_sync_log` | 同步尝试日志 | dry-run 不得新增成功 sync_log |

【验收标准】
□ `APP_ENV=production` 且 `WORKSHOP_ENABLE_WORKER_DRY_RUN=false` 时，`dry_run=true` 返回 `WORKSHOP_DRY_RUN_DISABLED`。
□ dry-run 被生产禁用时，不查询 outbox、不调用 ERPNext、不写操作审计，但写安全审计。
□ `WORKSHOP_ENABLE_WORKER_DRY_RUN=true` 且服务账号授权通过时，`dry_run=true` 返回 `200/code=0`。
□ 授权 dry-run 成功时，新增 1 条 `ly_audit_log` 操作审计。
□ dry-run 操作审计包含 `principal/dry_run/batch_size/include_forbidden_diagnostics/would_process_count/request_id`。
□ dry-run 操作审计不包含 Authorization、Cookie、token、secret、password 明文。
□ dry-run 操作审计写入失败时，接口返回 `AUDIT_WRITE_FAILED`。
□ dry-run 不改变 outbox 的 `status/attempts/locked_by/locked_at/next_retry_at`。
□ dry-run 不新增成功 sync_log。
□ dry-run 不调用 ERPNext Job Card 写接口。
□ dry-run + `include_forbidden_diagnostics=true` 时，TASK-003I 的冷却期去重仍生效。
□ 普通用户或普通车间角色调用 dry-run 返回 `AUTH_FORBIDDEN` 并写安全审计。
□ 全量测试继续通过。

【测试要求】
必须新增或补齐以下测试：
1. `test_dry_run_disabled_in_production_writes_security_audit`
2. `test_dry_run_disabled_does_not_query_outbox_or_write_operation_audit`
3. `test_dry_run_allowed_writes_operation_audit`
4. `test_dry_run_operation_audit_contains_safe_summary_fields`
5. `test_dry_run_operation_audit_has_no_sensitive_plaintext`
6. `test_dry_run_audit_write_failure_returns_audit_write_failed`
7. `test_dry_run_does_not_mutate_outbox_state_or_attempts`
8. `test_dry_run_does_not_create_success_sync_log`
9. `test_dry_run_does_not_call_erpnext_job_card_write`
10. `test_dry_run_with_forbidden_diagnostics_keeps_dedupe_cooldown`
11. `test_workshop_manager_cannot_call_dry_run`
12. `test_dry_run_empty_candidate_still_writes_operation_audit`

【回归命令】
在 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service` 下执行：

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m unittest discover
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
```

【前置依赖】
- TASK-003F：内部 Worker API 已限制为服务账号或系统级集成账号调用
- TASK-003G：服务账号最小权限策略已接入
- TASK-003H：Outbox 队头阻塞已修复
- TASK-003I：越权诊断节流与审计去重已接入

【交付物】
1. dry-run 生产环境开关与禁用错误码。
2. dry-run 成功操作审计。
3. dry-run 禁用和拒绝的安全审计。
4. dry-run 不变更业务状态的回归测试。
5. 全量测试结果。

【禁止事项】
1. 禁止授权 dry-run 成功但不写操作审计。
2. 禁止生产环境默认开放 dry-run。
3. 禁止 dry-run 锁定 outbox、增加 attempts、更新重试时间或调用 ERPNext。
4. 禁止 dry-run 返回完整 outbox payload、完整权限列表或敏感凭证。
5. 禁止 dry-run 绕过 forbidden diagnostics 的节流和审计去重。
6. 禁止在日志或审计中记录 token、Authorization、Cookie、secret、password 明文。

════════════════════════════════════════════════════════════════════════════
