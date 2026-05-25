# TASK-Z028B-14-FIX-CAND002 factory statement idempotency 修复报告

## 范围

- candidate: `Z028-CAND-002`
- source failure task: `TASK-Z028B-13-PREP-CAND002-FAILURE-DIAG`
- classification: `TEST_CONTRACT_UPDATE_ALLOWED`
- allowed fix file: `07_后端/lingyi_service/tests/test_factory_statement_idempotency.py`
- 本轮未修改 backend app、前端、其他测试、共享工程师日志、candidate pool 或 B10-B13 既有产物。

## 修复内容

- 在目标测试内新增 confirm/cancel operation payload helper。
- confirm payload 补齐 scoped `idempotency_key`、`scenario_tag`、`company`、`supplier`、`statement_no`。
- cancel payload 补齐 scoped `idempotency_key`、`scenario_tag`、`company`、`supplier`、`statement_no`，并让 `reason` 携带同一 `scenario_tag`。
- race fixture 中预置 operation 的 `idempotency_key` 改为与请求相同的 scoped key。
- 5 个失败用例的目标 `200` 成功分支断言保留；冲突用例的 `409` 断言保留。
- 未使用 skip/xfail，未删除测试用例，未弱化断言为任意 2xx 或非 409。

## 验证

- command: `.venv/bin/python -m pytest tests/test_factory_statement_idempotency.py -q`
- workdir: `07_后端/lingyi_service`
- command_run_count: `1`
- exit_code: `0`
- result: `PASS`
- pytest_summary: `12 passed, 34 warnings in 1.12s`
- stdout_log: `03_需求与设计/02_开发计划/task_z028b_14_cand002_fix_stdout.txt`

## 门禁

- `git diff --cached --name-only`: empty
- historical dirty forbidden staged scan: `[]`
- `git diff --check`: PASS
- stage/commit/push/tag/PR/release: false
- remote lifecycle parked: true
- production readback/go-live/project completion: false

## Dirty 范围说明

- 本轮允许目标测试: `07_后端/lingyi_service/tests/test_factory_statement_idempotency.py`
- 本轮允许证据产物:
  - `03_需求与设计/02_开发计划/TASK-Z028B-14-FIX-CAND002_factory_statement_idempotency修复报告.md`
  - `03_需求与设计/02_开发计划/task_z028b_14_cand002_fix_result.json`
  - `03_需求与设计/02_开发计划/task_z028b_14_cand002_fix_result.tsv`
  - `03_需求与设计/02_开发计划/task_z028b_14_cand002_fix_stdout.txt`
- 已归因 historical dirty forbidden paths 仍未 staged，且不得纳入后续 CAND002 ledger YES。
