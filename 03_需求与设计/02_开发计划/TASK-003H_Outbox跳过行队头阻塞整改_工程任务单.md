# 工程任务单：TASK-003H Outbox 跳过行队头阻塞整改

- 任务编号：TASK-003H
- 模块：工票/车间管理
- 优先级：P1
- 任务类型：审计整改 / Outbox 调度 / 队头阻塞修复
- 创建时间：2026-04-12 16:02 CST
- 作者：技术架构师
- 审计来源：TASK-003G 审计意见，`skipped_forbidden` outbox 保持 pending 且 `list_due(limit)` 固定按 id asc 取窗口，导致越权/缺 scope 行阻塞后续有权同步任务

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-003H
模块：工票/车间管理
优先级：P1（审计整改，必须先于 TASK-003 总体验收）
════════════════════════════════════════════════════════════════════════════

【任务目标】
修复 Job Card 同步 outbox 的队头阻塞问题，确保越权或缺 scope 的 pending 行不会长期占住 `limit` 处理窗口，后续有权 outbox 能被同一轮或下一轮 Worker 正常处理。

【问题背景】
TASK-003G 已要求服务账号按 ERPNext User Permission 校验 `company/item_code`。审计复现：第 1 条 outbox 越权、第 2 条 outbox 有权，`limit=1` 连续两轮 Worker 都只取到第 1 条并跳过，导致第 2 条有权 outbox 始终无法处理，ERPNext 调用 0 次。根因是 `skipped_forbidden` 行仍保持 `pending`，且 `list_due(limit)` 在权限过滤前按 `id asc` 固定取窗口。

【涉及文件】
新建或修改：
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/workshop_job_card_sync_worker.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/repositories/workshop_job_card_sync_outbox_repository.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/workshop.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/service_account_policy.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/permission_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/error_codes.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/audit_service.py`

测试文件：
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_workshop_job_card_sync.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_service_account_policy.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_workshop_worker_permissions.py`

【接口清单】
| 接口名称 | HTTP 方法 | 路径 | 入参 | 出参 |
| --- | --- | --- | --- | --- |
| 内部 Job Card 同步 Worker 单次执行 | POST | `/api/workshop/internal/job-card-sync/run-once` | `batch_size`, `dry_run=false` | `processed_count`, `succeeded_count`, `failed_count`, `skipped_forbidden_count`, `blocked_scope_count`, `dead_count` |

【核心设计决策】
1. 主处理查询必须先按服务账号 `allowed_companies/allowed_items` 做数据库层过滤，再执行 `order by` 和 `limit`。
2. `limit` 只能作用在“当前服务账号有权处理的 due outbox 候选集”上，不能先取全量窗口再逐行权限过滤。
3. 对当前服务账号越权的 outbox，不得被当前 Worker 锁定、更新 attempts、更新 next_retry_at 或标记成功。
4. 对当前服务账号越权的 outbox 可以保持 `pending`，因为可能由其他服务账号处理；但它不能进入当前服务账号的主处理窗口。
5. 缺少 `company` 或 `item_code` 的 outbox 不属于任何服务账号可处理范围，必须脱离 due pending 队列，避免永久阻塞。
6. 缺 scope 行推荐转为 `dead` 或新增 `blocked_scope` 状态，并写 `SERVICE_ACCOUNT_RESOURCE_SCOPE_REQUIRED` 安全审计；不得继续保持可被 `list_due` 反复取到的 pending due 状态。
7. 如果保留 `skipped_forbidden_count`，它只能来自独立诊断扫描，不得消费主处理 `limit`。
8. Worker 的 `processed_count` 只统计实际进入授权处理流程的 outbox，不统计越权跳过行。
9. Worker 的 `succeeded_count` 只统计 ERPNext Job Card 写同步成功的 outbox。
10. 权限来源不可用时仍必须 fail closed，返回 `503 + PERMISSION_SOURCE_UNAVAILABLE`，不得退回全量扫描。

【数据库查询要求】
主处理查询必须满足以下顺序：
1. 先限定 `status in ('pending', 'failed')`。
2. 再限定 `next_retry_at <= now()`。
3. 再限定 `company in allowed_companies`。
4. 再限定 `item_code in allowed_items`。
5. 再执行 `order by id asc`。
6. 最后执行 `limit batch_size`。

禁止实现：
1. 禁止先 `order by id asc limit batch_size` 再在 Python 中逐行过滤权限。
2. 禁止越权行保持 pending 且继续被同一个服务账号下一轮优先取到。
3. 禁止为了绕过阻塞而扩大服务账号资源权限。
4. 禁止权限来源失败时降级为不带资源过滤的查询。

【状态推进规则】
| outbox 场景 | 处理方式 | 是否调用 ERPNext | 是否占用主处理 limit |
| --- | --- | --- | --- |
| 当前服务账号有 `company/item_code` 权限 | 进入主处理流程 | 是 | 是 |
| 当前服务账号无 `company/item_code` 权限 | 不进入主处理查询或被独立诊断跳过 | 否 | 否 |
| outbox 缺少 `company` 或 `item_code` | 转为 `dead` 或 `blocked_scope`，写安全审计 | 否 | 否 |
| 权限来源不可用 | 整个 Worker fail closed | 否 | 否 |

【业务规则】
1. `list_due_for_service_account(policy, limit)` 必须替代原先无资源过滤的 `list_due(limit)` 用于内部 Worker 主流程。
2. `list_due_for_service_account` 必须在 SQLAlchemy 查询层完成 `company/item_code` 过滤。
3. 若 `allowed_companies` 或 `allowed_items` 为空，Worker 不得查询全量 outbox，应返回 `SERVICE_ACCOUNT_RESOURCE_FORBIDDEN` 或 `processed_count=0`，并写安全审计。
4. 对缺 scope 行必须有明确推进策略：转 `dead` 或 `blocked_scope`，并记录 `last_error_code=SERVICE_ACCOUNT_RESOURCE_SCOPE_REQUIRED`。
5. 如果新增 `blocked_scope` 状态，必须同步更新模型枚举、迁移、查询过滤、测试数据和运维说明。
6. 如果复用 `dead` 状态，必须通过 `last_error_code=SERVICE_ACCOUNT_RESOURCE_SCOPE_REQUIRED` 区分业务死信原因。
7. 越权 outbox 不得写成功 sync_log，不得标记 `succeeded`，不得增加 attempts。
8. 越权 outbox 不得阻塞同一服务账号有权处理的后续 outbox。
9. 服务账号权限过滤后的候选数量不足 `limit` 时，按实际候选数量处理，不得回退扫描未授权 outbox 补足 limit。
10. 审计记录必须能区分：资源越权跳过、缺 scope 阻断、权限源不可用、ERPNext 同步失败。

【错误码要求】
| 场景 | HTTP 状态 | code | 要求 |
| --- | --- | --- | --- |
| 服务账号无任何 Company/Item scope | 403 | `SERVICE_ACCOUNT_RESOURCE_FORBIDDEN` | 不查询全量 outbox，写安全审计 |
| 权限来源不可用 | 503 | `PERMISSION_SOURCE_UNAVAILABLE` | 不处理 outbox，写安全审计 |
| outbox 缺少 company/item_code | 200 或 409 | `SERVICE_ACCOUNT_RESOURCE_SCOPE_REQUIRED` | 脱离 due pending 队列，写安全审计 |
| 有权 outbox 同步成功 | 200 | `0` | 标记 succeeded，写 sync_log 和操作审计 |

【验收标准】
□ 第 1 条 outbox 越权、第 2 条 outbox 有权、`batch_size=1` 时，第一轮 Worker 必须处理第 2 条有权 outbox。
□ 连续两轮 Worker 不得重复只跳过同一条越权 outbox。
□ 上述场景下 ERPNext Job Card 写接口至少调用 1 次。
□ 主处理查询在数据库层包含 `company in allowed_companies` 和 `item_code in allowed_items` 过滤。
□ `limit` 应用于资源过滤后的候选集，而不是全量 pending due 集合。
□ 当前服务账号越权 outbox 不被锁定、不增加 attempts、不更新 `locked_by/locked_at`、不标记 `succeeded`。
□ 当前服务账号越权 outbox 不新增成功 sync_log。
□ 缺少 `company` 或 `item_code` 的 outbox 不会在后续 Worker 中反复占据 due pending 队头。
□ 缺 scope 行必须写 `SERVICE_ACCOUNT_RESOURCE_SCOPE_REQUIRED` 安全审计。
□ 服务账号没有任何 Company/Item scope 时，不得查询或处理全量 outbox。
□ 权限来源不可用时不执行任何 outbox 查询锁定和 ERPNext 调用。
□ TASK-003D/TASK-003E/TASK-003F/TASK-003G 既有回归测试继续通过。

【测试要求】
必须新增或补齐以下测试：
1. `test_worker_limit_applies_after_service_account_scope_filter`
2. `test_forbidden_head_row_does_not_block_authorized_second_row_with_limit_one`
3. `test_repeated_worker_runs_do_not_revisit_same_forbidden_head_for_same_account`
4. `test_forbidden_outbox_is_not_locked_or_attempted_by_unauthorized_service_account`
5. `test_forbidden_outbox_does_not_create_success_sync_log`
6. `test_missing_scope_outbox_is_moved_out_of_due_pending_queue`
7. `test_missing_scope_outbox_writes_security_audit`
8. `test_empty_service_account_scope_does_not_query_all_outbox`
9. `test_permission_source_unavailable_does_not_lock_or_query_candidates`
10. `test_authorized_outbox_after_forbidden_rows_calls_erpnext`

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
- TASK-003G：服务账号最小权限策略已接入

【交付物】
1. `list_due_for_service_account(policy, limit)` 或等价数据库层资源过滤查询。
2. 缺 scope outbox 的状态推进和安全审计。
3. 队头阻塞复现用例和修复用例。
4. 全量回归测试结果。

【禁止事项】
1. 禁止先 limit 再权限过滤。
2. 禁止越权 pending 行长期占住同一服务账号的处理窗口。
3. 禁止通过扩大服务账号权限解决队头阻塞。
4. 禁止权限来源失败时 fail open。
5. 禁止资源越权 outbox 调用 ERPNext。
6. 禁止资源越权 outbox 被标记为成功。

════════════════════════════════════════════════════════════════════════════
