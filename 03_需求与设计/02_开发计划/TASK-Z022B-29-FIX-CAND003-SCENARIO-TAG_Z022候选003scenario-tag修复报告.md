# TASK-Z022B-29-FIX-CAND003-SCENARIO-TAG

## 任务边界

- 角色：B Engineer
- 候选：Z022-CAND-003
- 来源任务：TASK-Z022B-28-PREP-CAND003-FAILURE-DIAG
- 修复文件：`07_后端/lingyi_service/tests/test_quality_defect_baseline.py`
- 未修改 `06_前端`
- 未修改 `07_后端/lingyi_service/app`
- 未修改其他测试文件、既有证据产物、共享工程师日志、A/C 记录或生产配置
- 未 stage/commit/push/tag/PR/release

## 修复摘要

- 将测试合同中的 invalid `scenario_tag` 从 `quality-defect-baseline` 调整为合法格式：
  - `Z003-QUALITY-INSPECTION-20260524-003`
- 在测试内补齐 defects request carrier：
  - `X-Request-ID` 与 payload `request_id` 保持一致
  - request id 使用当前 router `Z003-QUALITY-INSPECTION-...-QI-D-...` carrier 格式
  - `source_ref` 与 `source_doc` 保持一致，并携带同一合法 scenario tag
  - 保持 `operation=defects`、`inspection_ref`、`source_type`、`item_code`、`result` 与当前 gate 合同一致
- 保留原断言语义：
  - 草稿创建用例仍断言 `201`
  - 非 draft 用例仍断言 `403` 与 `QUALITY_INVALID_STATUS`
- 未新增 skip/xfail，未删除用例，未弱化断言。

## 验证结果

- workdir：`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service`
- command：`.venv/bin/python -m pytest tests/test_quality_defect_baseline.py -q`
- command_run_count：1
- exit_code：0
- result：PASS
- pytest_summary：`2 passed, 1 warning in 1.14s`
- stdout：`03_需求与设计/02_开发计划/task_z022b_29_cand003_scenario_tag_fix_stdout.txt`

## 产物

- `03_需求与设计/02_开发计划/task_z022b_29_cand003_scenario_tag_fix_result.json`
- `03_需求与设计/02_开发计划/task_z022b_29_cand003_scenario_tag_fix_result.tsv`
- `03_需求与设计/02_开发计划/task_z022b_29_cand003_scenario_tag_fix_stdout.txt`
