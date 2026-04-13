# 工程任务单：TASK-003G 服务账号最小权限策略整改

- 任务编号：TASK-003G
- 模块：工票/车间管理
- 优先级：P1
- 任务类型：审计整改 / 服务账号权限 / 资源级权限闭环
- 创建时间：2026-04-12 15:40 CST
- 作者：技术架构师
- 审计来源：TASK-003F 审计意见，服务账号仍是“全模块全资源”硬编码授权，并跳过 item/company 资源校验

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-003G
模块：工票/车间管理
优先级：P1（审计整改，必须先于 TASK-003 总体验收）
════════════════════════════════════════════════════════════════════════════

【任务目标】
将 Job Card 同步 Worker 的服务账号权限从硬编码“全模块全资源”改为 ERPNext 驱动的最小权限策略，确保服务账号每处理一条 outbox 都必须通过 `item_code/company` 资源级校验。

【问题背景】
TASK-003F 已收紧 `/api/workshop/internal/job-card-sync/run-once`，普通车间角色不能直接触发内部 Worker。但审计发现服务账号本身仍被硬编码授予全模块全资源，并跳过 `item_code/company` 资源校验。这样会导致内部接口虽然只允许服务账号调用，但服务账号一旦被误用或泄露，仍可处理全部款式和全部公司下的 Job Card 同步，未达到最小权限原则。

【涉及文件】
新建或修改：
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/service_account_policy.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/permission_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/workshop_job_card_sync_worker.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/workshop.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/auth.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/permissions.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/error_codes.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/exceptions.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/audit_service.py`

测试文件：
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_service_account_policy.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_workshop_worker_permissions.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_workshop_job_card_sync.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_security_audit.py`

【接口清单】
| 接口名称 | HTTP 方法 | 路径 | 入参 | 出参 |
| --- | --- | --- | --- | --- |
| 内部 Job Card 同步 Worker 单次执行 | POST | `/api/workshop/internal/job-card-sync/run-once` | `batch_size`, `dry_run=false` | `processed_count`, `succeeded_count`, `failed_count`, `skipped_forbidden_count`, `dead_count` |
| 用户手动重试单个 Job Card 同步 | POST | `/api/workshop/job-cards/{job_card}/sync` | `job_card` | `outbox_id`, `status` |

【权限策略】
| 策略项 | 要求 |
| --- | --- |
| 服务账号身份来源 | ERPNext User + Role，不允许前端声明 |
| 服务账号角色 | 必须具备 `LY Integration Service` 或 `System Manager` |
| 动作权限 | 必须具备 `workshop:job_card_sync_worker` |
| 资源权限来源 | ERPNext `User Permission`，必须明确到 `Company` 和 `Item` |
| 默认行为 | 没有明确资源授权时 fail closed，不得当作全资源 |
| 全局资源 | 禁止硬编码 `*`、`all`、空数组表示全资源 |
| 权限源失败 | 返回 `PERMISSION_SOURCE_UNAVAILABLE`，不得处理 outbox |

【业务规则】
1. 删除或废弃服务账号“全模块全资源”硬编码授权。
2. 服务账号只能通过后端可信身份解析获得，不允许请求体、Header 或前端参数声明 `is_service_account=true`。
3. `workshop:job_card_sync_worker` 只证明服务账号可以运行 Worker，不证明它可以处理所有 outbox。
4. Worker 每处理一条 outbox 前，必须校验该 outbox 的 `company` 和 `item_code` 是否在服务账号 ERPNext User Permission 范围内。
5. 服务账号没有明确 Company 权限时，不得处理任何 outbox。
6. 服务账号没有明确 Item 权限时，不得处理任何带 `item_code` 的 outbox。
7. ERPNext User Permission 查询失败时，整个 Worker 调用返回 `503 + PERMISSION_SOURCE_UNAVAILABLE`，不得锁定、更新或重试 outbox。
8. outbox 缺少 `company` 或 `item_code` 时，禁止调用 ERPNext；该行记录为 `SERVICE_ACCOUNT_RESOURCE_SCOPE_REQUIRED`，并写安全审计。
9. 服务账号对某条 outbox 无资源权限时，禁止调用 ERPNext，禁止把该 outbox 标记为 `succeeded`。
10. 推荐实现：Worker 查询 pending outbox 时按服务账号允许的 `company/item_code` 过滤；未授权 outbox 保持原状态，不被当前服务账号锁定。
11. 如果实现需要返回跳过数量，响应中增加 `skipped_forbidden_count`，但不得把未授权 outbox 当作成功处理。
12. 成功处理 outbox 时，操作审计必须记录服务账号、outbox_id、job_card、item_code、company、request_id。
13. 未授权 outbox 跳过或拒绝时，安全审计必须记录服务账号、outbox_id、job_card、item_code、company、原因码，不得记录密钥明文。
14. 普通用户手动重试 `/api/workshop/job-cards/{job_card}/sync` 继续沿用用户自己的 `item_code/company` 资源级校验，不得复用服务账号全局权限。
15. 单元测试中不得通过 monkeypatch 全局授权绕过资源校验；测试假权限源必须明确返回 allowed_companies/allowed_items。

【错误码要求】
| 场景 | HTTP 状态 | code | 要求 |
| --- | --- | --- | --- |
| 服务账号无动作权限 | 403 | `AUTH_FORBIDDEN` | 不处理 outbox，写安全审计 |
| 服务账号无 Company/Item 策略 | 403 | `SERVICE_ACCOUNT_RESOURCE_FORBIDDEN` | 不处理 outbox，写安全审计 |
| 权限来源不可用 | 503 | `PERMISSION_SOURCE_UNAVAILABLE` | 不处理 outbox，写安全审计 |
| outbox 缺少 company/item_code | 409 | `SERVICE_ACCOUNT_RESOURCE_SCOPE_REQUIRED` | 不调用 ERPNext，写安全审计 |
| 单条 outbox 资源越权 | 200 | `0` | 跳过该行，`skipped_forbidden_count + 1`，不改成功状态 |
| 服务账号资源校验通过 | 200 | `0` | 正常处理 outbox，写操作审计 |

【数据库表】
| 表名 | 用途 | 本任务要求 |
| --- | --- | --- |
| `ly_schema.ys_workshop_job_card_sync_outbox` | Job Card 待同步 outbox | 必须使用 `company/item_code` 做服务账号资源过滤；未授权行不得被当前服务账号锁定或标记成功 |
| `ly_schema.ys_workshop_job_card_sync_log` | Worker 同步尝试日志 | 仅资源授权通过并实际尝试 ERPNext 同步时写入 |
| `ly_schema.ly_security_audit_log` | 安全审计 | 服务账号资源越权、权限源失败、scope 缺失必须写入 |
| `ly_schema.ly_audit_log` | 操作审计 | 服务账号成功处理 outbox 必须写入 |

【验收标准】
□ 代码中不存在服务账号默认 `all modules/all resources/*` 的硬编码授权。
□ 服务账号只有 `workshop:job_card_sync_worker` 但没有 Company/User Permission 时，调用 Worker 返回 `SERVICE_ACCOUNT_RESOURCE_FORBIDDEN` 或不处理任何 outbox。
□ 服务账号授权 `COMPANY-A + ITEM-B` 时，不能处理 `COMPANY-A + ITEM-A` 的 outbox。
□ 服务账号授权 `COMPANY-A + ITEM-B` 时，不能处理 `COMPANY-B + ITEM-B` 的 outbox。
□ 服务账号授权 `COMPANY-A + ITEM-B` 时，可以处理 `COMPANY-A + ITEM-B` 的 outbox。
□ 资源越权 outbox 不调用 ERPNext Job Card 写接口。
□ 资源越权 outbox 不新增成功 sync_log。
□ 资源越权 outbox 不被标记为 `succeeded`。
□ 权限来源不可用时返回 `503 + PERMISSION_SOURCE_UNAVAILABLE`，且不锁定、不更新、不重试 outbox。
□ outbox 缺少 `company` 或 `item_code` 时不调用 ERPNext，并写 `SERVICE_ACCOUNT_RESOURCE_SCOPE_REQUIRED` 安全审计。
□ 成功处理 outbox 的操作审计包含 `principal/outbox_id/job_card/item_code/company/request_id`。
□ 安全审计和普通日志不包含 Authorization、Cookie、token、secret、password 明文。
□ 既有 `Workshop Manager`、`Production Manager`、`Workshop Sync Operator` 仍不能获得 `workshop:job_card_sync_worker`。
□ TASK-003D/TASK-003E/TASK-003F 的既有回归测试继续通过。

【测试要求】
必须新增或补齐以下测试：
1. `test_service_account_policy_has_no_implicit_global_scope`
2. `test_service_account_without_company_permission_cannot_process_outbox`
3. `test_service_account_without_item_permission_cannot_process_outbox`
4. `test_service_account_with_company_a_item_b_skips_company_a_item_a`
5. `test_service_account_with_company_a_item_b_skips_company_b_item_b`
6. `test_service_account_with_company_a_item_b_processes_matching_outbox`
7. `test_service_account_permission_source_unavailable_fails_closed`
8. `test_outbox_missing_company_or_item_is_not_synced_to_erpnext`
9. `test_resource_forbidden_outbox_does_not_create_success_sync_log`
10. `test_service_account_resource_denial_writes_sanitized_security_audit`
11. `test_successful_service_account_sync_writes_operation_audit_with_resource_scope`
12. `test_no_hardcoded_service_account_all_resource_policy_in_production`

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
- TASK-003F：内部 Worker API 已限制为服务账号或系统级集成账号调用

【交付物】
1. 服务账号 policy 解析与资源级校验实现。
2. Worker 按服务账号 `company/item_code` scope 过滤或跳过 outbox。
3. 服务账号资源越权、scope 缺失、权限源失败的安全审计。
4. 成功同步的操作审计。
5. 新增测试与全量回归测试结果。

【禁止事项】
1. 禁止服务账号默认全模块全资源。
2. 禁止用 `*`、`all`、空数组代表服务账号全资源。
3. 禁止服务账号跳过 `item_code/company` 资源级校验。
4. 禁止权限源失败时继续处理 outbox。
5. 禁止资源越权 outbox 调用 ERPNext。
6. 禁止资源越权 outbox 被标记为成功。
7. 禁止在日志或审计中记录 service token、Authorization、Cookie、secret、password 明文。

════════════════════════════════════════════════════════════════════════════
