# TASK-Z022B-07-FIX Z022-CAND-001 quality-create-baseline 测试合同二次修复报告

- 任务：TASK-Z022B-07-FIX
- 角色：B Engineer
- 源任务：TASK-Z022B-06-PREP
- 候选：Z022-CAND-001
- failure_classification：TEST_CONTRACT_UPDATE_ALLOWED
- 唯一允许修改文件：`07_后端/lingyi_service/tests/test_quality_create_baseline.py`

## 修复内容

- 在测试文件内新增 `_local_gate_env()`，仅在两个请求用例的 `patch.dict("os.environ", ...)` 作用域内设置：
  - `APP_ENV=development`
  - `LINGYI_DB_URL=sqlite:///./lingyi_service.local.db`
- 环境补丁由 `patch.dict` 自动恢复，避免污染其他测试。
- 保留 B05 已补齐的 payload 必填字段，并补齐当前 router carrier 合同：
  - `scenario_tag` 使用 `Z003-QUALITY-INSPECTION-YYYYMMDD-NNN` 格式。
  - `source_doc` 与 `source_ref` 保持一致。
  - body `request_id` 与 header `X-Request-ID` 保持一致。
  - request carrier 根据 `idempotency_key/source_ref/inspection_ref/item_code/result` 生成。
- 未修改业务源码、router、schema、service、model、crud、前端、依赖或配置。
- 未删除用例，未添加 skip/xfail，未弱化原断言：
  - 权限用例仍断言 `403` 与 `AUTH_FORBIDDEN`。
  - 创建用例仍断言 `201`、`code=0`、`status=draft` 与操作日志。

## 单文件回归

- workdir：`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service`
- command：`.venv/bin/python -m pytest tests/test_quality_create_baseline.py -q`
- command_run_count：1
- exit_code：0
- result：PASS
- pytest_summary：`2 passed, 1 warning in 0.92s`
- stdout_log：`03_需求与设计/02_开发计划/task_z022b_07_quality_create_baseline_second_fix_stdout.txt`

## 禁止动作

- 未修改除允许测试文件外的任何源码、测试、依赖或配置文件。
- 未运行其他 pytest、全量 pytest、npm、browser、build、typecheck、verify。
- 未 stage/commit/push/PR/tag/release。
- 未 cleanup/kill 本地服务。
- 未释放 parked blockers，未声明项目完成。
