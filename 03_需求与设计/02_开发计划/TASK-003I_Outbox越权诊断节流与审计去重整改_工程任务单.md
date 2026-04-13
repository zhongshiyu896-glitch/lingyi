# 工程任务单：TASK-003I Outbox 越权诊断节流与审计去重整改

- 任务编号：TASK-003I
- 模块：工票/车间管理
- 优先级：P1
- 任务类型：审计整改 / Outbox 治理 / 安全审计去重
- 创建时间：2026-04-12 16:15 CST
- 作者：技术架构师
- 审计来源：TASK-003H 审计意见，越权 outbox 虽不再阻塞授权任务，但仍保持 due 状态并被每轮 run-once 重复枚举和写安全审计

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-003I
模块：工票/车间管理
优先级：P1（审计整改，必须先于 TASK-003 总体验收）
════════════════════════════════════════════════════════════════════════════

【任务目标】
为 Job Card 同步 outbox 的越权诊断增加节流、去重和状态治理，避免多公司、多服务账号场景下重复枚举越权行、重复写安全审计，导致审计表放大和 Worker 事务变重。

【问题背景】
TASK-003H 已修复队头阻塞：第 1 条越权、第 2 条有权、`limit=1` 时，Worker 能正确处理第 2 条授权 outbox。但审计发现越权 outbox 仍保持 due 状态，并且每轮 `run-once` 都会被重复枚举和写安全审计。越权 outbox 对当前服务账号可能无权，但对其他服务账号可能有权，因此不能简单全部置 dead；同时也不能让当前服务账号每轮都扫描和写审计。

【涉及文件】
新建或修改：
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/workshop.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/repositories/workshop_job_card_sync_outbox_repository.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/repositories/workshop_outbox_access_denial_repository.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/workshop_job_card_sync_worker.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/service_account_policy.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/audit_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/error_codes.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/config.py`

测试文件：
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_workshop_job_card_sync.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_service_account_policy.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_workshop_outbox_audit_throttle.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_security_audit.py`

【接口清单】
| 接口名称 | HTTP 方法 | 路径 | 入参 | 出参 |
| --- | --- | --- | --- | --- |
| 内部 Job Card 同步 Worker 单次执行 | POST | `/api/workshop/internal/job-card-sync/run-once` | `batch_size`, `dry_run=false`, `include_forbidden_diagnostics=false` | `processed_count`, `succeeded_count`, `failed_count`, `blocked_scope_count`, `forbidden_diagnostic_count` |

【数据库表设计】
| 表名 | 用途 | 关键字段 | 索引 |
| --- | --- | --- | --- |
| `ly_schema.ys_workshop_job_card_sync_outbox` | Job Card 待同步 outbox | `id`, `status`, `next_retry_at`, `company`, `item_code`, `last_error_code` | `idx_status_next_retry`, `idx_scope_status_retry(company,item_code,status,next_retry_at)` |
| `ly_schema.ys_workshop_outbox_access_denial` | 记录某服务账号对某 outbox 的资源拒绝诊断状态 | `outbox_id`, `principal`, `reason_code`, `scope_hash`, `first_seen_at`, `last_seen_at`, `last_audit_at`, `next_audit_at`, `seen_count` | `uk_outbox_principal_reason_scope`, `idx_next_audit_at` |
| `ly_schema.ly_security_audit_log` | 安全审计 | `event_type`, `principal`, `resource_type`, `resource_id`, `dedupe_key`, `created_at` | `idx_dedupe_key_created_at` |

【核心设计决策】
1. 默认 `run-once` 只查询当前服务账号有权处理的 outbox，不枚举越权 outbox。
2. 越权 outbox 对当前服务账号不得进入主处理窗口，也不得每轮写安全审计。
3. 若需要输出越权诊断，必须显式传入 `include_forbidden_diagnostics=true`，且该参数只允许服务账号或 System Manager 使用。
4. 越权诊断必须有上限，例如 `WORKSHOP_FORBIDDEN_DIAGNOSTIC_LIMIT`，禁止全量扫描。
5. 越权诊断必须写入 `ys_workshop_outbox_access_denial` 做去重和节流。
6. 同一 `outbox_id + principal + reason_code + scope_hash` 在冷却期内只能写 1 条安全审计。
7. 推荐冷却期：6 小时；生产环境可通过 `WORKSHOP_OUTBOX_DENIAL_AUDIT_COOLDOWN_SECONDS` 配置。
8. 冷却期内重复发现只更新 `seen_count/last_seen_at`，不得重复写 `ly_security_audit_log`。
9. scope 变化、reason 变化或冷却期到期，才允许再次写安全审计。
10. 缺少 `company/item_code` 的 outbox 仍按 TASK-003H 要求转 `dead` 或 `blocked_scope`，不参与越权诊断重复扫描。

【业务规则】
1. `run-once` 默认路径不得调用“列出越权 outbox”的查询。
2. `include_forbidden_diagnostics=false` 时，响应中的 `forbidden_diagnostic_count` 必须为 0 或不返回。
3. `include_forbidden_diagnostics=true` 时，只允许执行节流后的诊断扫描，且扫描条数不得超过配置上限。
4. 越权诊断扫描必须排除已 `succeeded/dead/blocked_scope` 的 outbox。
5. 越权诊断扫描不得锁定 outbox，不得增加 attempts，不得更新 `next_retry_at`，不得调用 ERPNext。
6. 越权诊断发现同一拒绝事件时，必须 upsert `ys_workshop_outbox_access_denial`。
7. 首次发现拒绝事件时写安全审计，并设置 `next_audit_at = now + cooldown`。
8. 冷却期内重复发现拒绝事件时只增加 `seen_count`，不得重复写安全审计。
9. 冷却期后再次发现拒绝事件时允许写 1 条安全审计，并刷新 `next_audit_at`。
10. `dedupe_key` 必须由 `principal + outbox_id + reason_code + scope_hash` 生成，不得包含 token、cookie、authorization、secret、password。
11. `scope_hash` 必须基于规范化后的 `company/item_code/allowed_scope_version` 生成，禁止把完整权限列表写入普通日志。
12. 如果某 outbox 后续被授权服务账号成功处理为 `succeeded`，相关 denial 记录可保留为历史，不得影响成功处理。
13. 如果某 outbox 后续转为 `dead/blocked_scope`，诊断扫描必须不再重复枚举该 outbox。
14. 安全审计表写入失败仍按既有错误分类处理，不得吞掉系统级异常。
15. 本任务不得削弱 TASK-003H 的“先 scope 过滤再 limit”主处理查询规则。

【配置项】
| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `WORKSHOP_FORBIDDEN_DIAGNOSTIC_LIMIT` | `50` | 单次越权诊断最多扫描行数 |
| `WORKSHOP_OUTBOX_DENIAL_AUDIT_COOLDOWN_SECONDS` | `21600` | 同一拒绝事件安全审计冷却时间，默认 6 小时 |
| `WORKSHOP_ENABLE_FORBIDDEN_DIAGNOSTICS` | `false` | 生产默认关闭自动越权诊断，仅显式请求或运维任务开启 |

【错误码要求】
| 场景 | HTTP 状态 | code | 要求 |
| --- | --- | --- | --- |
| 普通用户请求 `include_forbidden_diagnostics=true` | 403 | `AUTH_FORBIDDEN` | 不执行诊断，写安全审计 |
| 越权诊断超过配置上限 | 200 | `0` | 只处理上限内记录，返回实际诊断数量 |
| denial 表写入失败 | 500 | `DATABASE_WRITE_FAILED` | 不伪装为业务失败 |
| 安全审计写入失败 | 500 | `AUDIT_WRITE_FAILED` | 不重复调用 ERPNext |

【验收标准】
□ 默认 `run-once` 不查询、不枚举当前服务账号越权 outbox。
□ 默认 `run-once` 不因越权 outbox 重复写 `ly_security_audit_log`。
□ 连续 3 次默认 `run-once`，同一越权 outbox 的安全审计新增数量为 0。
□ `include_forbidden_diagnostics=true` 首次发现某越权 outbox 时，新增 1 条安全审计。
□ 冷却期内连续 3 次 `include_forbidden_diagnostics=true`，同一拒绝事件不重复新增安全审计。
□ 冷却期内重复诊断只更新 `ys_workshop_outbox_access_denial.seen_count/last_seen_at`。
□ 冷却期到期后再次诊断同一拒绝事件，最多新增 1 条安全审计。
□ `dedupe_key` 不包含 Authorization、Cookie、token、secret、password 明文。
□ 越权诊断扫描不锁定 outbox、不增加 attempts、不更新 `next_retry_at`、不调用 ERPNext。
□ 缺 scope outbox 转为 `dead` 或 `blocked_scope` 后，不再被越权诊断重复枚举。
□ 第 1 条越权、第 2 条有权、`batch_size=1` 的 TASK-003H 队头阻塞回归用例仍通过。
□ 全量测试继续通过。

【测试要求】
必须新增或补齐以下测试：
1. `test_default_run_once_does_not_scan_forbidden_outbox`
2. `test_default_run_once_does_not_write_repeated_forbidden_security_audit`
3. `test_forbidden_diagnostics_requires_internal_permission`
4. `test_forbidden_diagnostics_first_seen_writes_one_security_audit`
5. `test_forbidden_diagnostics_repeated_within_cooldown_dedupes_audit`
6. `test_forbidden_diagnostics_updates_seen_count_within_cooldown`
7. `test_forbidden_diagnostics_after_cooldown_writes_one_more_audit`
8. `test_denial_dedupe_key_has_no_sensitive_plaintext`
9. `test_forbidden_diagnostics_does_not_lock_attempt_or_retry_outbox`
10. `test_blocked_scope_outbox_is_excluded_from_forbidden_diagnostics`
11. `test_head_of_line_fix_still_processes_authorized_second_row`
12. `test_diagnostic_limit_bounds_scan_size`

【回归命令】
在 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service` 下执行：

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m unittest discover
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
```

【前置依赖】
- TASK-003G：服务账号最小权限策略已接入
- TASK-003H：Outbox 队头阻塞已修复，主处理查询已先 scope 过滤再 limit

【交付物】
1. 越权诊断默认关闭或显式启用机制。
2. `ys_workshop_outbox_access_denial` 去重/节流记录能力，或等价实现。
3. 安全审计 dedupe key 与冷却期控制。
4. 重复扫描和审计放大的回归测试。
5. 全量测试结果。

【禁止事项】
1. 禁止默认 `run-once` 每轮扫描越权 outbox。
2. 禁止同一拒绝事件冷却期内重复写安全审计。
3. 禁止越权诊断锁定 outbox、增加 attempts、更新 `next_retry_at` 或调用 ERPNext。
4. 禁止通过把越权 outbox 全部置 dead 来规避多服务账号授权场景。
5. 禁止在 dedupe_key、日志、审计中记录 token、Authorization、Cookie、secret、password 明文。
6. 禁止削弱 TASK-003H 的先 scope 过滤再 limit 规则。

════════════════════════════════════════════════════════════════════════════
