# TASK-Z030B-33-PREP-CAND004-FAILURE-DIAG 失败只读定位报告

## 结论

- 状态：READY_FOR_REVIEW
- 候选：Z030-CAND-004
- source task：TASK-Z030B-32-IMPL
- frozen command：.venv/bin/python -m pytest tests/test_subcontract_receive_outbox.py -q
- failed summary：13 failed, 2 passed, 1 warning in 1.21s
- classification：TEST_CONTRACT_UPDATE_ALLOWED
- allowed fix file：07_后端/lingyi_service/tests/test_subcontract_receive_outbox.py
- recommended next task：TASK-Z030B-34-FIX-CAND004
- run_this_task：false

## 失败模式

13 个失败均集中在 receive outbox 测试用例。旧测试 payload 只提供 `idempotency_key`、`receipt_warehouse`、`received_qty`、`uom`，当前 `ReceiveRequest` 继承 `SubcontractWriteCarrierBase`，需要 `request_id`、`scenario_tag`、`source_ref`、`subcontract_ref`、`supplier_ref`、`work_order_ref`、`operation`、`item_code`、`quantity`、`status_action` 等 carrier 字段。`_parse_receive_payload` 将 schema validation failure 统一映射为 `SUBCONTRACT_STOCK_OUTBOX_CONFLICT`，导致用例未进入原 `200/403/409/503` 业务分支。

## 关键差异摘要

- expected 200，observed 409：创建回料、ERPNext 不在事务内调用、fake stock entry、幂等重试、超收前置批次、outbox 返回、多批次回料等成功分支。
- expected 403，observed 409：仓库权限拒绝分支。
- expected 503，observed 409：权限源不可用 fail-closed 分支。
- expected 409 code，observed 409 code drift：blocked scope、draft、settled 等错误码被 schema/payload gate 的 `SUBCONTRACT_STOCK_OUTBOX_CONFLICT` 提前覆盖。

## source evidence

- 07_后端/lingyi_service/tests/test_subcontract_receive_outbox.py
- 07_后端/lingyi_service/app/routers/subcontract.py
- 07_后端/lingyi_service/app/schemas/subcontract.py
- 07_后端/lingyi_service/app/services/subcontract_stock_outbox_service.py
- 07_后端/lingyi_service/app/services/erpnext_stock_entry_service.py
- 07_后端/lingyi_service/app/models/subcontract.py
- source_evidence_missing：[]

## gate

- cached：空
- git diff --check：PASS
- target_test_dirty_diff：false
- pytest/npm/browser/build/typecheck/verify：未运行
- stage/commit/push/tag/PR/release：false
- cleanup/reset/checkout/stash：false
