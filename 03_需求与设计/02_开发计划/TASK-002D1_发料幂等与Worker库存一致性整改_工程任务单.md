# TASK-002D1 发料幂等与 Worker 库存一致性整改工程任务单

- 任务编号：TASK-002D1
- 模块：外发加工管理
- 优先级：P0
- 版本：V1.0
- 更新时间：2026-04-13 10:33 CST
- 作者：技术架构师
- 审计来源：审计意见书第 39 份，TASK-002D 不通过，高 2 / 中 2
- 前置依赖：TASK-002D 已交付但审计不通过；继续遵守外发模块 V1.6 与 ADR-030/031/032/033/034/035
- 任务边界：只修 TASK-002D 发料 outbox 与 worker 库存一致性问题；不得进入 TASK-002E 回料、TASK-002F 验货、TASK-006 对账

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-002D1
模块：发料幂等与 Worker 库存一致性整改
优先级：P0（阻断修复）
════════════════════════════════════════════════════════════════════════════

【任务目标】
修复 TASK-002D 审计不通过的 4 个问题：发料幂等检查前置、event_key 找回 ERPNext Stock Entry 时校验/提交 docstatus、Worker claim 与 ERPNext 调用拆短事务、补齐失败/重试/dead/并发/日志脱敏测试。

【架构确认】
1. `event_key` 正式以“幂等事件”为单位生成，不包含易变 `issue_batch_no`。
2. `event_key` 推荐输入：`stock_action + subcontract_id + idempotency_key + stable_payload_hash`。
3. `issue_batch_no` 是本地发料批次号，只用于业务展示和 material 分组，不参与 event_key。
4. `ly_subcontract_stock_outbox` 是幂等权威表，保存 `idempotency_key/payload_hash/payload_json/event_key`。
5. `ly_subcontract_material` 以 `stock_outbox_id` 关联 outbox 查询幂等上下文；本任务不强制在 material 行冗余 `idempotency_key/payload_hash`。
6. 若当前代码已在 material 行保存 `idempotency_key/payload_hash`，允许保留，但审计验收以 `stock_outbox_id -> outbox` 关联为准。

【涉及文件】
修改：
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/subcontract_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/subcontract_stock_outbox_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/subcontract_stock_worker_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_stock_entry_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/subcontract.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/subcontract.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/subcontract.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/error_codes.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/exceptions.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_issue_outbox.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_stock_worker.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_stock_outbox_idempotency.py

【整改问题清单】
| 编号 | 严重程度 | 问题 | 必须结果 |
| --- | --- | --- | --- |
| P1-1 | 高 | 幂等判断发生在剩余数量校验之后，全量发料后同幂等键重试被误拒为 `SUBCONTRACT_MATERIAL_QTY_EXCEEDED` | 幂等检查必须前置，相同 key + 相同 payload 直接返回第一次 outbox 结果 |
| P1-2 | 高 | Worker 按 event_key 找回 ERPNext Stock Entry 时忽略 `docstatus`，draft 单也会被本地标记 succeeded | `docstatus=1` 才可本地成功；`docstatus=0` 必须 submit；`docstatus=2` 或异常状态不得成功 |
| P2-1 | 中 | Worker claim 后未提交，在持有数据库事务/行锁期间调用 ERPNext | claim/lease 短事务提交后再调用 ERPNext；回写结果使用新短事务 |
| P2-2 | 中 | TASK-002D 要求的失败、重试、dead、并发、event_key 恢复、日志脱敏测试未补齐 | 补齐任务单指定的 worker 风险测试 |

【发料幂等前置规则】
1. `issue-material` 收到请求后，在任何依赖当前剩余数量的校验之前，先构造稳定 payload。
2. 稳定 payload 必须剔除易变字段：`issue_batch_no`、`request_id`、`outbox_id`、`event_key`、创建时间、操作者显示名等。
3. 使用稳定 payload 计算 `payload_hash`。
4. 先按 `subcontract_id + stock_action='issue' + idempotency_key` 查询已有 outbox。
5. 已有 outbox 且 `payload_hash` 一致：直接返回第一次结果，包括 `outbox_id/issue_batch_no/sync_status/stock_entry_name`。
6. 已有 outbox 且 `payload_hash` 不一致：返回 `SUBCONTRACT_IDEMPOTENCY_CONFLICT`。
7. 只有不存在已有 outbox 时，才执行剩余可发数量校验、BOM 物料校验和新建 material/outbox。
8. 全量发料 `items=[]` 的稳定 payload 必须以“请求语义”计算，不得因第一次发料后剩余数量变化导致同 key 重试 hash 改变。
9. 相同幂等键重试不得增加 `issued_qty`、不得新增 material、不得新增 outbox、不得调用 ERPNext。

【ERPNext event_key 找回与 docstatus 规则】
1. `ERPNextStockEntryService.find_by_event_key()` 必须返回结构化结果，至少包含 `name` 和 `docstatus`。
2. 未找到 Stock Entry：worker 可继续 create + submit。
3. 找到 `docstatus=1`：说明 ERPNext 已提交入账，worker 可以补本地 succeeded 回写。
4. 找到 `docstatus=0`：说明 ERPNext 只有 draft，worker 必须 submit 该原单；submit 成功后才能本地 succeeded。
5. 找到 `docstatus=2`：说明 ERPNext 单据已取消，worker 不得本地成功，必须标记 failed/dead 或返回 `ERPNEXT_STOCK_ENTRY_CANCELLED`。
6. 找到其他未知 docstatus：不得本地成功，返回 `ERPNEXT_STOCK_ENTRY_STATUS_INVALID`。
7. submit existing draft 失败时，outbox 必须按失败策略记录 `last_error_code/next_retry_at/attempts`，不得创建第二张 Stock Entry。
8. create 成功但 submit 失败留下 draft 时，下一次 worker 必须找到该 draft 并 submit，而不是重新 create。
9. ERPNext 查询返回多个相同 event_key 单据时，必须 fail closed，返回 `ERPNEXT_STOCK_ENTRY_DUPLICATE_EVENT_KEY`，不得任选一个成功。

【Worker 短事务规则】
1. Worker 必须拆成三个阶段：claim 短事务、ERPNext 网络调用、result 回写短事务。
2. claim 阶段只做 due 查询、资源 scope 过滤、锁定/租约、attempts 预处理，并立即 commit。
3. ERPNext create/find/submit 阶段不得持有数据库事务或行锁。
4. result 回写阶段重新开启短事务，按 outbox id/event_key 回写 succeeded/failed/dead 和 sync_log。
5. result 回写前必须校验 outbox lease 或版本，避免过期 worker 覆盖新 worker 结果。
6. result 回写失败时必须 rollback；下一轮 worker 必须能通过 event_key 从 ERPNext 找回已创建/已提交单据。
7. 并发 worker 不得重复处理同一 outbox；第二个 worker 应看到 locked/lease 或状态已变化。
8. claim 成功但 worker 崩溃时，`lease_until` 到期后 outbox 可重新被 claim。
9. dry-run 不得 claim、不得增加 attempts、不得写 lock/lease、不得调用 ERPNext。
10. 事务拆分后仍必须写操作审计和安全审计；审计失败按既有 `AUDIT_WRITE_FAILED` 策略处理。

【错误码】
必须新增或补齐：
- `SUBCONTRACT_IDEMPOTENCY_CONFLICT`
- `SUBCONTRACT_MATERIAL_QTY_EXCEEDED`
- `ERPNEXT_STOCK_ENTRY_CANCELLED`
- `ERPNEXT_STOCK_ENTRY_STATUS_INVALID`
- `ERPNEXT_STOCK_ENTRY_DUPLICATE_EVENT_KEY`
- `ERPNEXT_STOCK_ENTRY_SUBMIT_FAILED`
- `ERPNEXT_STOCK_ENTRY_CREATE_FAILED`
- `ERPNEXT_SERVICE_UNAVAILABLE`
- `DATABASE_READ_FAILED`
- `DATABASE_WRITE_FAILED`
- `AUDIT_WRITE_FAILED`
- `AUTH_UNAUTHORIZED`
- `AUTH_FORBIDDEN`
- `PERMISSION_SOURCE_UNAVAILABLE`

【验收标准】
□ 第一次全量发料成功后，第二次相同 `idempotency_key + payload` 返回第一次 outbox 结果。  
□ 第二次相同幂等键重试不返回 `SUBCONTRACT_MATERIAL_QTY_EXCEEDED`。  
□ 第二次相同幂等键重试不新增 material。  
□ 第二次相同幂等键重试不新增 outbox。  
□ 第二次相同幂等键重试不增加 `issued_qty`。  
□ `items=[]` 自动全量发料的幂等 hash 不受第一次发料后剩余数量变化影响。  
□ 相同幂等键不同 payload 仍返回 `SUBCONTRACT_IDEMPOTENCY_CONFLICT`。  
□ `event_key` 不包含 `issue_batch_no`，同一幂等事件重试 event_key 稳定不变。  
□ `find_by_event_key()` 返回 `docstatus=1` 时，worker 补本地 succeeded，不重复 create。  
□ `find_by_event_key()` 返回 `docstatus=0` 时，worker submit existing draft，submit 成功后本地 succeeded。  
□ `find_by_event_key()` 返回 `docstatus=0` 且 submit 失败时，outbox 进入 failed/retry，不得本地 succeeded。  
□ `find_by_event_key()` 返回 `docstatus=2` 时，outbox 不得本地 succeeded。  
□ 相同 event_key 查到多个 ERPNext 单据时，返回 `ERPNEXT_STOCK_ENTRY_DUPLICATE_EVENT_KEY` 或等价 fail closed。  
□ Worker claim 阶段 commit 后才调用 ERPNext。  
□ Worker ERPNext 调用期间不持有数据库事务/行锁。  
□ result 回写失败后，下一轮 worker 能通过 event_key 找回 ERPNext 已提交单据并补本地 succeeded。  
□ 并发 worker 不会重复处理同一 outbox。  
□ claim 后 worker 崩溃，lease 到期后 outbox 可被重新处理。  
□ Worker timeout/5xx 标记 failed 并设置 `next_retry_at`。  
□ 业务失败超过 `max_attempts` 后进入 `dead`。  
□ sync_log 记录成功、失败、submit draft、dead 等尝试。  
□ 日志和审计不泄露 SQL 原文、Authorization、Cookie、token、password、secret、ERPNext 敏感响应原文。  
□ `receive/inspect` 仍保持 fail closed，不新增回料/验货事实。  
□ 业务代码扫描不出现 `STE-ISS/STE-REC` 伪库存号回潮。  
□ 业务代码扫描不出现旧验货公式回潮。  
□ 全量 pytest、unittest、py_compile 通过。

【测试要求】
必须新增或补齐以下测试：
1. `test_issue_material_full_issue_idempotent_retry_returns_existing_outbox`
2. `test_issue_material_full_issue_idempotent_retry_does_not_check_remaining_qty_first`
3. `test_issue_material_empty_items_payload_hash_stable_after_issue`
4. `test_issue_material_same_key_different_payload_still_conflicts`
5. `test_issue_material_event_key_excludes_issue_batch_no`
6. `test_stock_worker_find_existing_docstatus_1_marks_succeeded_without_create`
7. `test_stock_worker_find_existing_docstatus_0_submits_draft_then_succeeds`
8. `test_stock_worker_find_existing_docstatus_0_submit_failed_marks_retry`
9. `test_stock_worker_find_existing_docstatus_2_does_not_succeed`
10. `test_stock_worker_duplicate_event_key_fails_closed`
11. `test_stock_worker_claim_commits_before_erpnext_call`
12. `test_stock_worker_erpnext_call_does_not_hold_db_lock`
13. `test_stock_worker_result_write_failure_recovered_by_event_key_next_run`
14. `test_stock_worker_concurrent_run_does_not_double_process_outbox`
15. `test_stock_worker_lease_expiry_allows_reclaim_after_crash`
16. `test_stock_worker_erpnext_timeout_marks_failed_with_retry`
17. `test_stock_worker_business_validation_dead_after_max_attempts`
18. `test_stock_worker_sync_log_records_success_failure_and_dead`
19. `test_stock_worker_filters_due_outbox_by_service_account_scope_before_limit`
20. `test_subcontract_stock_logs_are_sanitized_for_worker_failures`
21. `test_task_002d1_does_not_restore_receive_or_inspect_success_path`

【回归命令】
在 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service` 下执行：

```bash
.venv/bin/python -m pytest -q tests/test_subcontract_issue_outbox.py tests/test_subcontract_stock_worker.py tests/test_subcontract_stock_outbox_idempotency.py
.venv/bin/python -m pytest -q
.venv/bin/python -m unittest discover
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
rg "STE-ISS|STE-REC|net_amount = .*inspected_qty|detail=str\(exc\)|Authorization|Cookie|password|secret" app migrations tests
```

【与 ERPNext 的接口】
| ERPNext 能力 | 调用方式 | 用途 |
| --- | --- | --- |
| `Stock Entry` 查找 | REST API GET | 按 `custom_ly_outbox_event_key` 查询 name/docstatus，防重复落账 |
| `Stock Entry` 提交 | REST API submit | 对 `docstatus=0` 的 existing draft 执行 submit |
| `Stock Entry` 创建 | REST API create + submit | 未找到 event_key 时创建并提交 Material Issue |
| `User Permission` | ERPNext 权限聚合 | 服务账号按 company/item/supplier/warehouse 过滤 outbox |

【前置依赖】
- TASK-002D：已交付但审计不通过。
- ADR-035：发料幂等必须前置，ERPNext event_key 找回必须校验 docstatus。

【交付物】
1. 发料幂等前置实现。
2. event_key 不包含 `issue_batch_no` 的稳定事件键实现或确认。
3. ERPNext `find_by_event_key()` 返回 name/docstatus 的结构化结果。
4. existing draft submit 与 docstatus fail closed 实现。
5. Worker claim/ERPNext/result 回写短事务拆分。
6. 失败、重试、dead、并发、event_key 恢复、日志脱敏测试。
7. 定向测试与全量测试结果。

【禁止事项】
1. 禁止进入 TASK-002E 回料 `Material Receipt`。
2. 禁止进入 TASK-002F 验货扣款金额口径。
3. 禁止同幂等键重试先做剩余数量校验。
4. 禁止把 ERPNext draft Stock Entry 当成已入账成功。
5. 禁止在持有数据库事务/行锁期间调用 ERPNext。
6. 禁止重复创建相同 event_key 的 ERPNext Stock Entry。
7. 禁止恢复 `receive/inspect` 成功路径。
8. 禁止日志、审计、响应中泄露 SQL 原文或敏感凭证。

【预计工时】
1-2 天

════════════════════════════════════════════════════════════════════════════
