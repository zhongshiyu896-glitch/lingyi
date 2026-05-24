# TASK-Z022B-12-PREP Z022-CAND-002 quality update baseline 失败定位与边界冻结报告

## 任务边界

- 角色：B Engineer
- 范围：仅对 B11 pytest 失败做只读定位与下一步边界冻结。
- 未运行 pytest/npm/browser/build/typecheck/verify。
- 未修改源码、测试、依赖或配置文件。
- 未 stage/commit/push。
- 未 cleanup/kill 服务。
- 未声明项目完成。

## B11 失败证据回读

- selected_candidate_id：Z022-CAND-002
- command：`.venv/bin/python -m pytest tests/test_quality_update_baseline.py -q`
- result：FAIL
- exit_code：1
- pytest_summary：`2 failed, 1 warning in 0.92s`

## 失败用例

- `QualityUpdateBaselineTest.test_patch_confirmed_rejected_with_403_cancelled_rejected_with_409`
  - 期望：403
  - 实际：422
  - 断言：`self.assertEqual(confirmed_resp.status_code, 403)`
- `QualityUpdateBaselineTest.test_patch_draft_inspection_success`
  - 期望：200
  - 实际：422
  - 断言：`self.assertEqual(response.status_code, 200, response.text)`
  - 缺失字段：`request_id`、`idempotency_key`、`scenario_tag`、`source_ref`、`inspection_ref`、`source_type`、`item_code`、`operation`

## 只读定位结论

- `07_后端/lingyi_service/tests/test_quality_update_baseline.py` 中两个 PATCH 请求仍使用旧合同 payload：草稿更新只发送数量/结果/备注，确认态与取消态只发送 `remark`。
- `07_后端/lingyi_service/app/schemas/quality.py` 的 `QualityInspectionUpdateRequest` 当前要求 `request_id`、`idempotency_key`、`scenario_tag`、`source_ref`、`inspection_ref`、`source_type`、`item_code`、`operation` 等必填字段。
- `07_后端/lingyi_service/app/routers/quality.py` 的 `update_quality_inspection` 先将 body 绑定为 `QualityInspectionUpdateRequest`，因此缺失字段会在进入 `_write_existing` 的状态检查和服务调用前返回 422。
- `07_后端/lingyi_service/app/services/quality_service.py` 的 `QualityService.update_inspection` 未在该失败中被有效触达；当前失败不是业务源码缺陷证据。

结论：测试合同缺少当前 schema 必填 carrier 字段，分类为 `TEST_CONTRACT_UPDATE_ALLOWED`。

## 下一步边界冻结

- failure_classification：TEST_CONTRACT_UPDATE_ALLOWED
- allowed_fix_files：`07_后端/lingyi_service/tests/test_quality_update_baseline.py`
- recommended_next_task_id：TASK-Z022B-13-FIX
- single_regression_command：`.venv/bin/python -m pytest tests/test_quality_update_baseline.py -q`
- run_this_task：false
- stage_allowed：false
- commit_allowed：false
- push_allowed：false
- project_completion_claimed：false
