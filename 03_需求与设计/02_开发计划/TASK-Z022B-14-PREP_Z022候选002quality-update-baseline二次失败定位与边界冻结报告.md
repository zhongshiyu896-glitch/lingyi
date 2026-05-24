# TASK-Z022B-14-PREP Z022-CAND-002 quality update baseline 二次失败定位与边界冻结报告

## 任务边界

- 角色：B Engineer
- 范围：仅对 B13 修复后 pytest 失败做只读定位与下一步边界冻结。
- 未运行 pytest/npm/browser/build/typecheck/verify。
- 未修改源码、测试、依赖或配置文件。
- 未 stage/commit/push。
- 未 cleanup/kill 服务。
- 未声明项目完成。

## B13 结果回读

- selected_candidate_id：Z022-CAND-002
- command：`.venv/bin/python -m pytest tests/test_quality_update_baseline.py -q`
- result：FAIL
- exit_code：1
- pytest_summary：`2 failed, 1 warning in 1.04s`
- B13 已按规则停止：`business_source_changed=false`，`backend_allowed_files_only=true`

## 二次失败用例

- `QualityUpdateBaselineTest.test_patch_confirmed_rejected_with_403_cancelled_rejected_with_409`
  - 期望：403
  - 实际：409
  - 错误码：`QUALITY_INVALID_SOURCE`
- `QualityUpdateBaselineTest.test_patch_draft_inspection_success`
  - 期望：200
  - 实际：409
  - 错误码：`QUALITY_INVALID_SOURCE`
  - 错误信息：`LOCAL_GATE_FAIL_CLOSED:non_local_dev`

## 只读定位结论

- B13 已补齐 `QualityInspectionUpdateRequest` 的必填 body 字段，但 `test_quality_update_baseline.py` 仍未提供本地写 gate 所需的隔离环境。
- `app/routers/quality.py` 的 `_ensure_local_dev_write_gate()` 要求 `APP_ENV=development` 且 `LINGYI_DB_URL=sqlite:///./lingyi_service.local.db`，否则抛出 `QUALITY_INVALID_SOURCE / LOCAL_GATE_FAIL_CLOSED:non_local_dev`。
- `app/routers/quality.py` 的 `_write_existing()` 在进入 confirmed/cancelled/draft 状态分支前先执行 `_validate_quality_existing_gate()`；因此 local gate 失败会先于确认态 403、取消态 409、草稿 200 分支返回。
- 当前 router gate 还要求 `source_doc` 与 `source_ref` 对齐，并要求 `request_id`/`X-Request-ID` 符合 `Z003-QUALITY-INSPECTION-...-QI-U-...` carrier 模式。B13 helper 尚未完成这些 carrier 合同。
- `app/services/quality_service.py` 的 `QualityService.update_inspection()` 在 local gate 失败时仍未触达；当前证据不足以指向业务源码缺陷。

结论：这是测试合同/fixture 未满足当前 local gate 与 carrier 合同，不是产品实现修复边界。

## 下一步边界冻结

- failure_classification：TEST_CONTRACT_UPDATE_ALLOWED
- allowed_fix_files：`07_后端/lingyi_service/tests/test_quality_update_baseline.py`
- recommended_next_task_id：TASK-Z022B-15-FIX
- single_regression_command：`.venv/bin/python -m pytest tests/test_quality_update_baseline.py -q`
- run_this_task：false
- stage_allowed：false
- commit_allowed：false
- push_allowed：false
- project_completion_claimed：false

允许的下一步修复范围仅限：

- 在测试文件内隔离补齐 `APP_ENV=development` 与 `LINGYI_DB_URL=sqlite:///./lingyi_service.local.db`。
- 在测试文件内对齐 `source_doc/source_ref` 与 `request_id/X-Request-ID` carrier 合同。
- 保留 confirmed 403、cancelled 409、draft 200 原语义断言。
