# 历史红清理任务

任务编号：HISTORICAL-RED-CLEANUP-001

范围：清理全量 pytest 既有历史红，不混入 A/B 期功能主线交付。功能主线每次收口仍按定向测试、acceptance smoke、前端 typecheck/API smoke 证明新增失败为 0。

## 当前状态

状态：已清零，转为上线前回归守门。

最新复核：2026-06-20 在 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service` 执行：

- `.venv/bin/python -m pytest --lf -q --tb=short`
- `.venv/bin/python -m pytest -q`

两次结果均为：

- `1495 passed`
- `13 skipped`
- `0 failed`

## 历史登记来源

2026-06-18 曾执行 `.venv/bin/python -m pytest --lf -q --tb=short`，登记 19 个历史红。该清单截至 2026-06-20 已不再复现；`pytest --lf` 已无失败保留，并退化为全量通过。

原 19 项历史红保留如下，便于后续若回归时快速定位：

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

## 回归守门

- 不修改封板测试来假绿。
- 上线前继续要求全量 pytest 新增失败为 0。
- 若上述任一历史项回归，必须按单项修复并补定向证据，不混入功能主线回交。
