# 工程任务单：TASK-003K 生产 Dry-Run 禁用判断前置整改

- 任务编号：TASK-003K
- 模块：工票/车间管理
- 优先级：P1
- 任务类型：审计整改 / 调用顺序 / 外部依赖隔离
- 创建时间：2026-04-12 16:53 CST
- 作者：技术架构师
- 审计来源：TASK-003J 审计意见，生产 dry-run 禁用状态下仍先读取 ERPNext User Permission，权限源超时时返回 `PERMISSION_SOURCE_UNAVAILABLE` 而非 `WORKSHOP_DRY_RUN_DISABLED`

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-003K
模块：工票/车间管理
优先级：P1（审计整改，必须先于 TASK-003 总体验收）
════════════════════════════════════════════════════════════════════════════

【任务目标】
将生产环境 `dry_run=true` 禁用判断前移：在完成登录、动作权限、服务账号主体校验后，立即返回 `WORKSHOP_DRY_RUN_DISABLED`，不得再读取 ERPNext User Permission、服务账号资源策略或 outbox。

【问题背景】
TASK-003J 已补齐 dry-run 成功路径操作审计，并要求生产环境默认禁用 dry-run。但审计探针发现：生产环境 dry-run 禁用且 ERPNext 权限源超时时，接口当前返回 `PERMISSION_SOURCE_UNAVAILABLE`。这说明路由会先读取 ERPNext User Permission，再判断 `WORKSHOP_ENABLE_WORKER_DRY_RUN`。禁用开关属于本地配置门禁，不应依赖外部权限源可用性；否则生产环境禁用能力在权限源故障时会表现不稳定，也会额外放大外部依赖调用。

【涉及文件】
新建或修改：
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/workshop.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/workshop_job_card_sync_worker.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/service_account_policy.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/permission_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/audit_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/config.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/error_codes.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/exceptions.py`

测试文件：
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_workshop_worker_permissions.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_workshop_job_card_sync.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_security_audit.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_service_account_policy.py`

【接口清单】
| 接口名称 | HTTP 方法 | 路径 | 入参 | 出参 |
| --- | --- | --- | --- | --- |
| 内部 Job Card 同步 Worker 单次执行 | POST | `/api/workshop/internal/job-card-sync/run-once` | `batch_size`, `dry_run`, `include_forbidden_diagnostics` | `dry_run`, `would_process_count`, `processed_count`, `succeeded_count`, `failed_count`, `blocked_scope_count`, `forbidden_diagnostic_count` |

【目标调用顺序】
`dry_run=true` 请求必须按以下顺序处理：

1. 规范化 `request_id`。
2. 解析当前用户；未登录返回 `AUTH_UNAUTHORIZED`。
3. 校验内部 Worker 动作权限 `workshop:job_card_sync_worker`；无权限返回 `AUTH_FORBIDDEN`。
4. 校验调用主体是服务账号、系统级集成账号或 `System Manager`；不符合返回 `AUTH_FORBIDDEN`。
5. 如果 `APP_ENV=production` 且 `WORKSHOP_ENABLE_WORKER_DRY_RUN=false`，立即返回 `WORKSHOP_DRY_RUN_DISABLED`，并写安全审计。
6. 只有 dry-run 未被禁用时，才允许读取 ERPNext User Permission、解析服务账号资源策略、查询 outbox 候选。
7. dry-run 授权成功后，继续执行 TASK-003J 的操作审计规则。

【禁止调用顺序】
1. 禁止在判断 `WORKSHOP_ENABLE_WORKER_DRY_RUN` 前读取 ERPNext User Permission。
2. 禁止在 dry-run 禁用状态下解析服务账号 `allowed_companies/allowed_items`。
3. 禁止在 dry-run 禁用状态下查询或锁定 outbox。
4. 禁止在 dry-run 禁用状态下触发 forbidden diagnostics。
5. 禁止在 dry-run 禁用状态下调用 ERPNext Job Card 写接口。

【业务规则】
1. `WORKSHOP_ENABLE_WORKER_DRY_RUN=false` 是本地配置门禁，优先级高于服务账号资源策略读取。
2. 生产 dry-run 禁用时，返回必须稳定为 `403 + WORKSHOP_DRY_RUN_DISABLED`。
3. 即使 ERPNext User Permission 超时、失败或不可用，生产 dry-run 禁用时仍必须返回 `WORKSHOP_DRY_RUN_DISABLED`。
4. 生产 dry-run 禁用时，安全审计必须记录 `principal`、`dry_run=true`、`reason=WORKSHOP_DRY_RUN_DISABLED`、`request_id`。
5. 生产 dry-run 禁用时，不写操作审计，因为没有进入授权 dry-run 诊断执行阶段。
6. 生产 dry-run 禁用时，不得泄露 ERPNext 权限源错误细节。
7. 非 dry-run 正常 Worker 路径不受本任务影响，仍按 TASK-003G/H/I 的服务账号资源策略和 outbox 规则执行。
8. dry-run 开启时，仍必须读取 ERPNext User Permission 并执行服务账号资源校验；不得因为本任务跳过资源权限。
9. 未登录、无动作权限、非服务账号主体的请求，仍优先返回对应 `AUTH_UNAUTHORIZED/AUTH_FORBIDDEN`，不得用 dry-run disabled 掩盖身份权限问题。
10. 所有拒绝响应仍必须使用统一 `{code, message, data/detail}` 错误信封。

【错误码要求】
| 场景 | HTTP 状态 | code | 是否读取 ERPNext User Permission | 是否查询 outbox | 审计要求 |
| --- | --- | --- | --- | --- | --- |
| 未登录 dry-run | 401 | `AUTH_UNAUTHORIZED` | 否 | 否 | 安全审计 |
| 无内部 Worker 动作权限 dry-run | 403 | `AUTH_FORBIDDEN` | 否 | 否 | 安全审计 |
| 非服务账号主体 dry-run | 403 | `AUTH_FORBIDDEN` | 否 | 否 | 安全审计 |
| 生产 dry-run 禁用 | 403 | `WORKSHOP_DRY_RUN_DISABLED` | 否 | 否 | 安全审计 |
| 生产 dry-run 开启但权限源不可用 | 503 | `PERMISSION_SOURCE_UNAVAILABLE` | 是 | 否 | 安全审计 |
| dry-run 开启且授权成功 | 200 | `0` | 是 | 只读候选 | 操作审计 |

【验收标准】
□ `APP_ENV=production`、`WORKSHOP_ENABLE_WORKER_DRY_RUN=false`、ERPNext User Permission 超时时，`dry_run=true` 返回 `403 + WORKSHOP_DRY_RUN_DISABLED`。
□ 上述场景下 ERPNext User Permission 查询调用次数为 0。
□ 上述场景下服务账号资源策略解析调用次数为 0。
□ 上述场景下 outbox 查询调用次数为 0。
□ 上述场景下 ERPNext Job Card 写接口调用次数为 0。
□ 上述场景下写入 1 条安全审计，原因码为 `WORKSHOP_DRY_RUN_DISABLED`。
□ 上述场景下不写 `ly_audit_log` 操作审计。
□ 未登录 dry-run 仍返回 `AUTH_UNAUTHORIZED`，不被 `WORKSHOP_DRY_RUN_DISABLED` 覆盖。
□ 无内部 Worker 动作权限 dry-run 仍返回 `AUTH_FORBIDDEN`，不被 `WORKSHOP_DRY_RUN_DISABLED` 覆盖。
□ 非服务账号主体 dry-run 仍返回 `AUTH_FORBIDDEN`，不被 `WORKSHOP_DRY_RUN_DISABLED` 覆盖。
□ `WORKSHOP_ENABLE_WORKER_DRY_RUN=true` 时，dry-run 仍会读取 ERPNext User Permission 并执行服务账号资源策略。
□ `WORKSHOP_ENABLE_WORKER_DRY_RUN=true` 且 ERPNext User Permission 超时时，返回 `PERMISSION_SOURCE_UNAVAILABLE`。
□ TASK-003J 的 dry-run 成功操作审计、不改 outbox、不调用 ERPNext 写接口等回归测试继续通过。
□ 全量测试继续通过。

【测试要求】
必须新增或补齐以下测试：
1. `test_production_dry_run_disabled_returns_disabled_before_permission_source_lookup`
2. `test_production_dry_run_disabled_does_not_load_service_account_policy`
3. `test_production_dry_run_disabled_does_not_query_outbox`
4. `test_production_dry_run_disabled_writes_security_audit_only`
5. `test_production_dry_run_disabled_does_not_write_operation_audit`
6. `test_dry_run_disabled_does_not_leak_permission_source_timeout`
7. `test_unauthenticated_dry_run_still_returns_auth_unauthorized_before_disabled`
8. `test_non_worker_permission_dry_run_still_returns_auth_forbidden_before_disabled`
9. `test_non_service_account_dry_run_still_returns_auth_forbidden_before_disabled`
10. `test_dry_run_enabled_still_loads_permission_source_and_fails_closed_when_unavailable`

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
- TASK-003J：dry-run 操作审计与生产默认禁用已接入

【交付物】
1. dry-run 禁用判断前置实现。
2. 禁用场景不访问 ERPNext User Permission、不查 outbox 的测试。
3. 禁用场景安全审计。
4. dry-run 开启后权限源 fail closed 回归测试。
5. 全量测试结果。

【禁止事项】
1. 禁止生产 dry-run 禁用时读取 ERPNext User Permission。
2. 禁止生产 dry-run 禁用时解析服务账号资源策略。
3. 禁止生产 dry-run 禁用时查询 outbox 或 forbidden diagnostics。
4. 禁止用 `PERMISSION_SOURCE_UNAVAILABLE` 覆盖 `WORKSHOP_DRY_RUN_DISABLED`。
5. 禁止用 dry-run disabled 掩盖未登录、无动作权限、非服务账号主体问题。
6. 禁止削弱 dry-run 开启后的资源级权限校验。

════════════════════════════════════════════════════════════════════════════
