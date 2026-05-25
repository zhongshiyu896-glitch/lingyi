# TASK-Z031B-32-FIX-CAND004 修复验证报告

## 前置核对

- 当前 HEAD: `0f783aa3b3f9a2cdc467c504840aa6caed55a56c`
- cached: empty
- `git diff --check`: PASS
- B31 classification: `TEST_CONTRACT_UPDATE_ALLOWED`
- B31 allowed_fix_file: `07_后端/lingyi_service/tests/test_subcontract_inspection.py`
- 授权修改文件: `07_后端/lingyi_service/tests/test_subcontract_inspection.py`

## 修复范围

仅调整目标测试中的 fixture/payload/direct request 构造：

- 为 inspect payload 补齐当前 carrier 必填字段：`request_id`、`scenario_tag`、`source_ref`、`subcontract_ref`、`supplier_ref`、`work_order_ref`、`operation`、`item_code`、`quantity`、`status_action`。
- 为 route 写入请求添加匹配的 `X-Request-ID` header。
- 将 direct `InspectRequest` 构造改为使用补齐 carrier 的 payload。
- 将测试环境切到本地写入 gate 允许的 development/local sqlite 配置。

原 `200/404/409` 状态码与业务错误码断言保留；未新增 skip/xfail，未删除失败用例，未改成任意 2xx/4xx 或任意错误码弱断言。

## 单次验证

- workdir: `07_后端/lingyi_service`
- command: `.venv/bin/python -m pytest tests/test_subcontract_inspection.py -q`
- command_run_count: 1
- exit_code: 0
- result: PASS
- pytest summary: `24 passed, 46 warnings in 1.22s`
- stdout: `03_需求与设计/02_开发计划/task_z031b_32_cand004_fix_stdout.txt`

## Gate

- changed_files: [`07_后端/lingyi_service/tests/test_subcontract_inspection.py`]
- target_test_dirty_diff: true
- inspect_carrier_contract_addressed: true
- business_status_assertions_preserved: true
- assertions_weakened: false
- skip_xfail_deleted_cases: false
- backend_app_changed: false
- frontend_changed: false
- unrelated_tests_changed: false
- continued_after_fail: false
- rerun_performed: false
- stage/commit/push/tag/PR/release: false
- remote_lifecycle_parked: true
- production_readback/go_live/project_completion: false
