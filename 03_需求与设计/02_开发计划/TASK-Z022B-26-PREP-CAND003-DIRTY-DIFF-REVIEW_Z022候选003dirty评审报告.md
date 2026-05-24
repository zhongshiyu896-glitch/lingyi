# TASK-Z022B-26-PREP-CAND003-DIRTY-DIFF-REVIEW dirty 评审报告

## Dirty Review

- current_head: c42a0c45a2b8f3c7c38fa2bdff57b224118fb8c6
- cached_area_empty: YES
- selected_candidate_id: Z022-CAND-003
- reanchor_json: 03_需求与设计/02_开发计划/task_z022b_25_cand003_reanchor_boundary.json
- preexisting_artifacts_classification: PREEXISTING_OUT_OF_TIGHTENED_MAINLINE
- test_quality_defect_baseline_dirty: YES
- quality_defect_backend_app_dirty: NO
- dirty_diff_test_contract_only: YES
- skip_xfail_added: NO
- tests_deleted: NO
- assertions_weakened: NO
- historical_b25_reused_as_pass: NO

## Diff 评审摘要

`07_后端/lingyi_service/tests/test_quality_defect_baseline.py` 的 dirty diff 仅限测试合同层：

- 新增 `unittest.mock.patch` import。
- 两个 defect POST 用例均使用 `patch.dict("os.environ", ...)` 隔离 `APP_ENV=development` 与 `LINGYI_DB_URL=sqlite:///./lingyi_service.local.db`。
- payload 补齐当前合同字段：`request_id`、`idempotency_key`、`scenario_tag`、`source_ref`、`inspection_ref`、`source_type`、`item_code`、`operation`、`result`。
- 保留草稿创建 `201` 断言。
- 保留非 draft `403` 与 `QUALITY_INVALID_STATUS` 断言。
- `rg` 检索 `skip|xfail|pytest.mark.skip|pytest.mark.xfail` 无匹配。
- 当前文件与 HEAD 均保留两个测试用例：`test_add_defect_to_draft_returns_201`、`test_add_defect_to_non_draft_rejected_with_403`。

当前 `07_后端/lingyi_service/app` 存在其他历史 dirty 文件，但 quality defect 直接 source evidence 中的 `routers/quality.py`、`services/quality_service.py`、`schemas/quality.py` 无 dirty diff，因此不构成本候选 backend app dirty 阻断。

## Boundary

- recommended_next_task_id: TASK-Z022B-27-IMPL-CAND003-REVALIDATE
- recommended_next_command: `.venv/bin/python -m pytest tests/test_quality_defect_baseline.py -q`
- run_pytest_this_task: NO
- allow_code_edit_next: NO
- allow_stage_commit_next: NO
- reason: dirty diff 已限定在 CAND003 测试合同层，未发现 backend app dirty、skip/xfail、删用例或断言弱化；下一步只能做单文件 readonly revalidate，不能进入修复或 ledger/stage/commit。

## Forbidden Actions

- pytest/npm/browser/build/typecheck/verify: NO
- product code edits: NO
- backend app edits: NO
- test edits: NO
- existing artifact edits: NO
- engineer shared log edit: NO
- stage/commit/push: NO
- reset/checkout/cleanup: NO
- PR/tag/release: NO
- production account / ERPNext production / real business write: NO
- parked blockers released: NO
- project completion claimed: NO
