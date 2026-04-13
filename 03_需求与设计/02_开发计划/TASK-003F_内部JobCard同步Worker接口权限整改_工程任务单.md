# 工程任务单：TASK-003F 内部 Job Card 同步 Worker 接口权限整改

- 任务编号：TASK-003F
- 模块：工票/车间管理
- 优先级：P1
- 任务类型：审计整改 / 权限收口 / 内部接口保护
- 创建时间：2026-04-12 15:21 CST
- 作者：技术架构师
- 审计来源：TASK-003E 审计意见，内部 Worker 写同步接口可被普通车间管理角色触发

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-003F
模块：工票/车间管理
优先级：P1（审计整改，必须先于 TASK-003 总体验收）
════════════════════════════════════════════════════════════════════════════

【任务目标】
收紧 `/api/workshop/internal/job-card-sync/run-once` 内部 Worker 接口调用权限，确保只有受控服务账号或系统级集成账号可以触发 ERPNext Job Card 写同步，普通车间管理角色不得直接触发内部 Worker。

【问题背景】
TASK-003D/TASK-003E 已将 Job Card 写同步从工票登记事务内移到 outbox/worker 模式，并修复了 `event_key` 截断碰撞问题。当前剩余风险是内部 Worker 触发接口仍暴露在 FastAPI 路由层，如果普通车间管理角色可以调用 `/api/workshop/internal/job-card-sync/run-once`，就可能绕过正常调度边界，主动触发批量写 ERPNext Job Card。该接口属于内部运维/集成能力，不是普通业务按钮权限。

【涉及文件】
新建或修改：
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/workshop.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/workshop_job_card_sync_worker.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/permission_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/auth.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/permissions.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/error_codes.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/exceptions.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/audit_service.py`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/workshop.ts`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/stores/permission.ts`

测试文件：
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_workshop_worker_permissions.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_workshop_job_card_sync.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_security_audit.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_auth_actions.py`

【接口清单】
| 接口名称 | HTTP 方法 | 路径 | 入参 | 出参 |
| --- | --- | --- | --- | --- |
| 内部 Job Card 同步 Worker 单次执行 | POST | `/api/workshop/internal/job-card-sync/run-once` | `batch_size`, `dry_run=false` | `processed_count`, `succeeded_count`, `failed_count`, `dead_count` |
| 用户手动重试单个 Job Card 同步 | POST | `/api/workshop/job-cards/{job_card}/sync` | `job_card` | `outbox_id`, `status` |
| 查询当前用户动作权限 | GET | `/api/auth/actions?module=workshop` | `module=workshop` | 普通用户不得包含 `workshop:job_card_sync_worker` |

【权限动作】
| 权限码 | 用途 | 可授予对象 | 是否前端展示 |
| --- | --- | --- | --- |
| `workshop:job_card_sync` | 用户手动重试单个 Job Card 同步 | 车间主管/生产主管 | 是 |
| `workshop:job_card_sync_worker` | 内部 Worker 批量处理 outbox 并写 ERPNext Job Card | 服务账号、系统集成账号、System Manager | 否 |

【数据库表】
| 表名 | 用途 | 本任务要求 |
| --- | --- | --- |
| `ly_schema.ys_workshop_job_card_sync_outbox` | Job Card 待同步 outbox | 未授权调用内部接口时不得修改任何 outbox 状态、attempts、locked_by、locked_at |
| `ly_schema.ys_workshop_job_card_sync_log` | Worker 每次同步尝试日志 | 未授权调用内部接口时不得新增 sync_log |
| `ly_schema.ly_security_audit_log` | 安全审计 | 401/403/503/internal disabled 必须写入安全审计 |
| `ly_schema.ly_audit_log` | 操作审计 | 服务账号成功执行 Worker 时必须写操作审计 |

【业务规则】
1. `/api/workshop/internal/job-card-sync/run-once` 是内部接口，禁止普通业务用户、普通车间主管、普通生产主管调用。
2. 内部接口必须同时满足：已认证、具备 `workshop:job_card_sync_worker`、主体是服务账号或系统级集成账号。
3. 只有 `workshop:job_card_sync` 不得调用内部 Worker；该权限只能用于 `/api/workshop/job-cards/{job_card}/sync` 单个 Job Card 手动重试。
4. 服务账号判定必须来自后端可信来源，例如 ERPNext 用户类型/角色、后端 allowlist 或专用 service account 标记，禁止由前端参数声明。
5. 推荐允许角色：`LY Integration Service`、`System Manager`；普通 `Workshop Manager`、`Workshop User`、`Production Manager` 默认不得调用内部 Worker。
6. 生产环境如保留 HTTP 内部 Worker 接口，必须支持开关 `ENABLE_INTERNAL_WORKER_API`；未开启时返回 `INTERNAL_API_DISABLED`，不得处理 outbox。
7. 权限来源不可用时返回 `503 + PERMISSION_SOURCE_UNAVAILABLE`，不得 fail open，也不得处理 outbox。
8. 未登录返回 `401 + AUTH_UNAUTHORIZED`，不得处理 outbox。
9. 已登录但缺少内部 Worker 权限或不是服务账号，返回 `403 + AUTH_FORBIDDEN`，不得处理 outbox。
10. 内部 Worker 成功执行时必须写操作审计，记录 `principal`、`processed_count`、`succeeded_count`、`failed_count`、`dead_count`、`request_id`。
11. 权限拒绝、安全拒绝、内部接口关闭必须写安全审计。
12. 审计和日志不得记录 Authorization、Cookie、service token、secret、password 明文。
13. `/api/auth/actions?module=workshop` 面向普通用户返回时不得包含 `workshop:job_card_sync_worker`。
14. Vue 前端不得新增普通菜单、按钮或页面入口调用 `/api/workshop/internal/job-card-sync/run-once`。
15. Worker 处理逻辑仍沿用 TASK-003D/TASK-003E：after-commit/outbox、最终态覆盖、幂等重试、`event_key = wjc:<64位SHA-256>`。

【错误码要求】
| 场景 | HTTP 状态 | code | 要求 |
| --- | --- | --- | --- |
| 未登录调用内部 Worker | 401 | `AUTH_UNAUTHORIZED` | 写安全审计，不处理 outbox |
| 普通用户或普通车间角色调用内部 Worker | 403 | `AUTH_FORBIDDEN` | 写安全审计，不处理 outbox |
| 只有 `workshop:job_card_sync` 但无 `workshop:job_card_sync_worker` | 403 | `AUTH_FORBIDDEN` | 写安全审计，不处理 outbox |
| 权限来源不可用 | 503 | `PERMISSION_SOURCE_UNAVAILABLE` | 写安全审计，不处理 outbox |
| 生产环境内部接口未开启 | 403 或 404 | `INTERNAL_API_DISABLED` | 写安全审计，不处理 outbox |
| 服务账号授权通过 | 200 | `0` | 处理 outbox，写操作审计 |

【验收标准】
□ 普通 `Workshop Manager` 用户调用 `POST /api/workshop/internal/job-card-sync/run-once` 返回 `403 + AUTH_FORBIDDEN`。
□ 只有 `workshop:job_card_sync` 权限的用户调用内部 Worker 接口返回 `403 + AUTH_FORBIDDEN`。
□ 未登录调用内部 Worker 接口返回 `401 + AUTH_UNAUTHORIZED`。
□ 权限来源不可用时调用内部 Worker 接口返回 `503 + PERMISSION_SOURCE_UNAVAILABLE`。
□ 生产环境 `ENABLE_INTERNAL_WORKER_API=false` 时，内部 Worker 接口返回 `INTERNAL_API_DISABLED`，且不处理 outbox。
□ 未授权调用内部 Worker 后，`ys_workshop_job_card_sync_outbox.status/attempts/locked_by/locked_at` 无变化。
□ 未授权调用内部 Worker 后，不调用 ERPNext Job Card 写接口。
□ 未授权调用内部 Worker 后，不新增 `ys_workshop_job_card_sync_log`。
□ 未授权调用内部 Worker 后，新增一条 `ly_security_audit_log`，且不包含 Authorization/Cookie/token/secret/password 明文。
□ 服务账号同时具备 `workshop:job_card_sync_worker` 时，调用内部 Worker 接口返回 `200/code=0`，并处理 pending outbox。
□ 服务账号成功执行 Worker 后，新增操作审计，包含 `processed_count/succeeded_count/failed_count/dead_count/request_id`。
□ `GET /api/auth/actions?module=workshop` 对普通用户不返回 `workshop:job_card_sync_worker`。
□ Vue 前端没有普通菜单、按钮或页面调用 `/api/workshop/internal/job-card-sync/run-once`。
□ 既有 TASK-003D/TASK-003E 测试仍通过，Worker 不发生重复累加、不发生 event_key 碰撞回归。

【测试要求】
必须新增或补齐以下测试：
1. `test_internal_worker_requires_authentication`
2. `test_internal_worker_denies_workshop_manager`
3. `test_internal_worker_denies_job_card_sync_only_permission`
4. `test_internal_worker_denies_when_permission_source_unavailable`
5. `test_internal_worker_disabled_in_production_without_flag`
6. `test_internal_worker_service_account_can_process_outbox`
7. `test_internal_worker_denied_does_not_mutate_outbox_or_call_erpnext`
8. `test_internal_worker_denied_writes_security_audit_without_secrets`
9. `test_auth_actions_hide_job_card_sync_worker_for_normal_user`
10. `test_frontend_has_no_internal_worker_business_entry`

【回归命令】
在 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service` 下执行：

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m unittest discover
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
```

【前置依赖】
- TASK-003D：Job Card 同步 Outbox/After-Commit 架构已落地
- TASK-003E：Outbox `event_key` 截断碰撞已修复

【交付物】
1. 后端权限收口实现。
2. 内部 Worker 接口安全审计与操作审计。
3. 单元测试和回归测试通过记录。
4. 若存在前端误用内部接口，删除普通用户入口并保留接口封装隔离说明。

【禁止事项】
1. 禁止把 `workshop:job_card_sync_worker` 当成普通前端按钮权限。
2. 禁止普通 `Workshop Manager` 角色触发内部 Worker。
3. 禁止只依赖前端隐藏按钮作为权限控制。
4. 禁止权限源失败时继续处理 outbox。
5. 禁止未授权调用时锁定、更新、重试 outbox。
6. 禁止在日志或审计中记录 service token、Authorization、Cookie、secret、password 明文。

════════════════════════════════════════════════════════════════════════════
