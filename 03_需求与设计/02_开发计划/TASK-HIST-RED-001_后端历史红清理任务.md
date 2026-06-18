# TASK-HIST-RED-001 后端历史红清理任务

日期：2026-06-18

状态：已登记，功能主线外独立跟踪；上线前必须清零。

## 任务边界

本任务只处理当前后端全量 pytest 中遗留的 19 个历史红。它不属于 BOM、样衣、大货、采购、库存、报表等功能主线交付，不得混入 A/B 期功能闭环提交中“顺手改绿”。

清理原则：

- 不删除、不跳过、不 xfail 既有测试。
- 不为通过测试放宽鉴权、审计、幂等、权限 fail-closed、错误信封等底线。
- 不连接 ERPNext 9081。
- 每个清理批次单独备份、单独验证、单独回交。
- 收口标准为：对应定向测试通过，后端全量 pytest 失败数不增加，最终上线前全量 pytest 0 个历史红。

## 红名单对比结论

用户验收口径提出“旧 40 红名单 vs 现 19 红名单”。本地可复验材料中没有找到“40 个 pytest 红名单”的持久化失败清单；命中的 `TASK-164A baseline 原始 40 项` 是 tracked diff 基线，不是 pytest 红名单。

本次可执行对照采用 BOM 前基线 commit `966ef71` 与当前 commit `d745133`：

- 旧可执行基线：`966ef71 chore: checkpoint before material bom splice`
- 当前基线：`d745133 fix: support local material bom id allocation`
- 旧基线命令：在临时 worktree `/private/tmp/lingyi-old40-966ef71` 执行 `.venv/bin/python -m pytest -q`
- 当前命令：在 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service` 执行 `.venv/bin/python -m pytest -q`
- 旧基线结果：`24 failed, 1253 passed, 13 skipped`
- 当前结果：`19 failed, 1265 passed, 13 skipped`
- 包含关系：当前 19 完全包含于旧可执行基线 24；`comm -13 old current` 为空。
- 已修复旧红：5 个 `tests/test_ci_postgresql_gate.py` 失败项。
- 新增失败：0。

因此，本地可确认的是“旧可执行 24 红 -> 现 19 红，减少 5，且无原绿改红”。不能把 tracked diff 的“原始 40 项”冒充为 pytest 旧红名单，也不能据此声称“21 个 pytest 红为真修复”。如后续拿到旧 40 的实际 pytest 红名单文件，可复用本任务的集合对照方法重新校验。

## 当前 19 个历史红

1. `tests/test_logging_sanitization.py::LoggingSanitizationTest::test_database_write_failure_log_is_sanitized`
2. `tests/test_logging_sanitization.py::LoggingSanitizationTest::test_rollback_failure_log_is_sanitized`
3. `tests/test_logging_sanitization.py::LoggingSanitizationTest::test_semantic_sensitive_request_id_is_replaced_and_not_logged`
4. `tests/test_production_job_card_sync.py::ProductionJobCardSyncTest::test_sync_job_cards_forbidden_when_resource_scope_not_allowed`
5. `tests/test_production_job_card_sync.py::ProductionJobCardSyncTest::test_sync_job_cards_updates_local_projection_for_regular_path`
6. `tests/test_request_id_sanitization.py::RequestIdSanitizationTest::test_sensitive_request_id_is_not_written_raw_into_operation_audit`
7. `tests/test_sales_inventory_permissions.py::SalesInventoryPermissionTest::test_actions_registered`
8. `tests/test_subcontract_company_permission.py::SubcontractCompanyPermissionTest::test_blocked_scope_order_cannot_receive_or_inspect`
9. `tests/test_subcontract_company_permission.py::SubcontractCompanyPermissionTest::test_create_order_returns_backend_resolved_company`
10. `tests/test_subcontract_company_permission.py::SubcontractCompanyPermissionTest::test_create_subcontract_ambiguous_company_returns_company_ambiguous_envelope`
11. `tests/test_subcontract_company_permission.py::SubcontractCompanyPermissionTest::test_create_subcontract_erpnext_unavailable_returns_service_unavailable_envelope`
12. `tests/test_subcontract_company_permission.py::SubcontractCompanyPermissionTest::test_create_subcontract_unresolved_company_returns_company_unresolved_envelope`
13. `tests/test_subcontract_company_permission.py::SubcontractCompanyPermissionTest::test_inspect_forbidden_does_not_read_order_snapshot_before_resource_permission`
14. `tests/test_subcontract_company_permission.py::SubcontractCompanyPermissionTest::test_inspect_forbidden_when_local_company_not_allowed_before_payload_validation`
15. `tests/test_subcontract_company_permission.py::SubcontractCompanyPermissionTest::test_inspect_permission_source_unavailable_does_not_read_order_snapshot`
16. `tests/test_subcontract_company_permission.py::SubcontractCompanyPermissionTest::test_receive_forbidden_when_local_company_not_allowed_before_payload_validation`
17. `tests/test_subcontract_stock_outbox_idempotency.py::SubcontractStockOutboxIdempotencyTest::test_issue_material_empty_items_payload_hash_stable_after_issue`
18. `tests/test_subcontract_stock_outbox_idempotency.py::SubcontractStockOutboxIdempotencyTest::test_issue_material_idempotency_key_different_payload_returns_conflict`
19. `tests/test_subcontract_stock_outbox_idempotency.py::SubcontractStockOutboxIdempotencyTest::test_issue_material_idempotent_same_payload_returns_existing_result`

## 建议拆分

1. 日志与 request id 脱敏：4 项。
2. 生产工票同步权限与本地投影：2 项。
3. 销售库存权限动作注册：1 项。
4. 外发公司权限与错误信封：9 项。
5. 外发发料 outbox 幂等与冲突：3 项。

## 执行要求

每个子批次必须回交：

- 修改范围。
- 定向测试结果。
- 全量 pytest 零回退对照。
- 备份 commit 号。
- 是否仍属于“历史红清理”任务，不计入功能主线闭环完成率。

