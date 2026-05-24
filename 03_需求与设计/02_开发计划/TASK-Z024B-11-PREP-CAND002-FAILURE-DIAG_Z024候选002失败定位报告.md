# TASK-Z024B-11-PREP-CAND002-FAILURE-DIAG Z024候选002失败定位报告

## 结论

- source_task_id：`TASK-Z024B-10-IMPL`
- selected_candidate_id：`Z024-CAND-002`
- B10 结果：FAIL
- B10 pytest summary：`6 failed, 2 passed, 1 warning in 0.42s`
- 失败分类：`TEST_CONTRACT_UPDATE_ALLOWED`
- 允许下一步修复文件：`07_后端/lingyi_service/tests/test_quality_models.py`
- 下一任务冻结：`TASK-Z024B-12-FIX-CAND002`
- 本轮不运行 pytest，不修复文件，不 stage，不 commit。

## 失败用例

1. `test_finished_goods_source_requires_item_evidence`
   - error_type：`AttributeError`
   - reason：`_OwnershipSourceValidator` 覆盖 `QualitySourceValidator.__init__` 后未初始化 `local_dev_mode`，而 `validate_for_payload` 先读取 `self.local_dev_mode`。

2. `test_incoming_material_source_requires_company_and_item_ownership`
   - error_type：`AttributeError`
   - reason：同上，测试 double 未满足当前 source validator 初始化合同。

3. `test_invalid_result_fails_closed`
   - error_type：`pydantic_core.ValidationError`
   - missing_fields：`request_id/idempotency_key/scenario_tag/source_ref/inspection_ref/operation`
   - reason：测试 helper `_request()` 未补齐当前 `QualityInspectionCreateRequest` 必填字段。

4. `test_qty_mismatch_fails_before_insert`
   - error_type：`pydantic_core.ValidationError`
   - missing_fields：`request_id/idempotency_key/scenario_tag/source_ref/inspection_ref/operation`
   - reason：同上。

5. `test_rates_are_zero_when_inspected_qty_is_zero`
   - error_type：`pydantic_core.ValidationError`
   - missing_fields：`request_id/idempotency_key/scenario_tag/source_ref/inspection_ref/operation`
   - reason：同上。

6. `test_source_unavailable_fails_closed`
   - error_type：`pydantic_core.ValidationError`
   - missing_fields：`request_id/idempotency_key/scenario_tag/source_ref/inspection_ref/operation`
   - reason：同上。

## 只读源码证据

- `app/schemas/quality.py` 当前 `QualityInspectionCreateRequest` 将 `request_id/idempotency_key/scenario_tag/source_ref/inspection_ref/operation` 定义为必填字段。
- `app/services/quality_service.py` 当前 `QualitySourceValidator.__init__` 负责初始化 `local_dev_mode`，`validate_for_payload` 在执行 source-specific validation 前读取该字段。
- `tests/test_quality_models.py` 当前 `_request()` 仅提供业务字段，未满足当前 schema/carrier 合同；`_OwnershipSourceValidator.__init__` 未调用父类初始化或显式设置 `local_dev_mode`。

## 边界

证据显示失败仅来自测试 helper / fixture / payload 与当前 schema/service 初始化合同不匹配；未发现需要业务源码修改或产品语义裁决的证据。因此下一步只允许修改目标测试文件。

## 禁止动作确认

- pytest/npm/browser/build/typecheck/verify run：NO
- code edits：NO
- target test edits：NO
- stage/commit/push：NO
- PR/tag/release/cleanup：NO
- production account / ERPNext production / real business write：NO
- parked blockers released：NO
