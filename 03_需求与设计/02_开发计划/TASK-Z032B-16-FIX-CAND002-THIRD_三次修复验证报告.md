# TASK-Z032B-16-FIX-CAND002-THIRD 三次修复验证报告

## 基本信息

- TASK_ID: TASK-Z032B-16-FIX-CAND002-THIRD
- ROLE: B Engineer
- candidate_id: Z032-CAND-002
- source task: TASK-Z032B-15-PREP-CAND002-THIRD-FAILURE-DIAG
- HEAD: bbc298a8e2423ea51d82de66ed058835182bcade
- allowed fix file: `07_后端/lingyi_service/tests/test_subcontract_settlement_export.py`

## 前置核对

- cached: empty
- `git diff --check`: PASS
- B15 classification: TEST_CONTRACT_UPDATE_ALLOWED
- B15 allowed_fix_file: `07_后端/lingyi_service/tests/test_subcontract_settlement_export.py`
- B15 remaining_failed_cases_count: 26
- B15 failure pattern: 409/outbox conflict 阻断原 settlement preview/lock/release 分支
- B14 `_settlement_request_id()` unexpected `quantity` TypeError: 已解决
- 当前目标测试 dirty diff: 限于授权测试文件

## 修复内容

仅修改授权目标测试文件：

- 引入 `SUBCONTRACT_LOCAL_DB_URL`。
- 在 `setUp` 中保存并设置本测试所需环境：
  - `APP_ENV=development`
  - `LINGYI_ALLOW_DEV_AUTH=true`
  - `LINGYI_PERMISSION_SOURCE=static`
  - `LINGYI_DB_URL=SUBCONTRACT_LOCAL_DB_URL`
- 在 `tearDown` 中恢复上述环境变量并恢复 `client.post`。

该修复只处理当前 router 本地写入 gate 的测试合同漂移，使 settlement preview/lock/release 请求进入原业务分支。未修改 backend app、前端、共享日志、candidate pool、其他测试或历史 dirty 文件。

## 单次验证

- workdir: `07_后端/lingyi_service`
- command: `.venv/bin/python -m pytest tests/test_subcontract_settlement_export.py -q`
- command_run_count: 1
- exit_code: 0
- result: PASS
- pytest summary: `35 passed, 29 warnings in 1.32s`
- stdout: `03_需求与设计/02_开发计划/task_z032b_16_cand002_third_fix_stdout.txt`

## 断言与范围

- helper_type_error_remains_resolved: true
- outbox_conflict_gate_addressed: true
- settlement_export_contract_addressed: true
- business_assertions_preserved: true
- assertions_weakened: false
- skip_xfail_deleted_cases: false
- backend_app_changed: false
- frontend_changed: false
- unrelated_tests_changed: false
- continued_after_fail: false
- rerun_performed: false

## 生命周期状态

- stage: false
- commit: false
- push: false
- tag: false
- PR: false
- release: false
- remote_lifecycle_parked: true
- production_readback: false
- go_live: false
- project_completion: false
- B16 产物 staged: false
