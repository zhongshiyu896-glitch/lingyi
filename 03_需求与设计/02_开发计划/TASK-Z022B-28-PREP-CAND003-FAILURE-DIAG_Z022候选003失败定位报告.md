# TASK-Z022B-28-PREP-CAND003-FAILURE-DIAG

## 任务边界

- 角色：B Engineer
- 候选：Z022-CAND-003
- 来源任务：TASK-Z022B-27-IMPL-CAND003-REVALIDATE
- 本轮动作：只读失败定位与下一步边界冻结
- 未运行 pytest/npm/browser/build/typecheck/verify
- 未修改 `06_前端`、`07_后端`、既有产物、共享工程师日志、A/C 记录或生产配置
- 未 stage/commit/push/tag/PR/release

## B27 失败证据回读

- B27 result：FAIL
- B27 pytest summary：`2 failed, 1 warning in 1.20s`
- 失败用例：
  - `tests/test_quality_defect_baseline.py::QualityDefectBaselineTest::test_add_defect_to_draft_returns_201`
  - `tests/test_quality_defect_baseline.py::QualityDefectBaselineTest::test_add_defect_to_non_draft_rejected_with_403`
- 实际错误：
  - 草稿创建用例期望 `201`，实际 `409 QUALITY_INVALID_SOURCE / LOCAL_GATE_FAIL_CLOSED:invalid_scenario_tag`
  - 非 draft 用例期望 `403`，实际 `409 QUALITY_INVALID_SOURCE / LOCAL_GATE_FAIL_CLOSED:invalid_scenario_tag`

## 只读定位

- 当前测试发送的 `scenario_tag` 为 `quality-defect-baseline`：
  - `07_后端/lingyi_service/tests/test_quality_defect_baseline.py:41`
  - `07_后端/lingyi_service/tests/test_quality_defect_baseline.py:98`
- router 当前合法规则来自：
  - `07_后端/lingyi_service/app/routers/quality.py:79`
  - 规则：`Z003-QUALITY-INSPECTION-\d{8}-\d{3}`
- router gate 顺序：
  - `_validate_quality_gate_common()` 先执行 `_ensure_local_dev_write_gate()`
  - 随后对 `scenario_tag` 做 `QUALITY_SCENARIO_TAG_PATTERN.fullmatch(...)`
  - 不匹配时抛出 `QUALITY_INVALID_SOURCE / LOCAL_GATE_FAIL_CLOSED:invalid_scenario_tag`
  - `_write_existing()` 在进入 defects 的 confirmed/draft 状态分支前调用 `_validate_quality_existing_gate()`
- 下游 request carrier 约束：
  - `QUALITY_REQUEST_ID_CARRIER_PATTERN` 要求 request id/header 携带同一 `Z003-QUALITY-INSPECTION-\d{8}-\d{3}` tag 与 operation/idempotency/source/inspection/item/result carrier
  - 当前 `_headers()` 仅返回 `X-LY-Dev-User` 与 `X-LY-Dev-Roles`，未携带 `X-Request-ID`
  - 当前失败还未进入 request carrier 校验，因为已先停在 `invalid_scenario_tag`
- 结论：本次失败发生在权限/状态分支之前，是测试合同中的 `scenario_tag`/carrier 与当前 router gate 合同不匹配，不是业务状态分支或业务源码实现缺陷。

## 范围风险核对

- quality defect backend app 精确核对无 dirty diff：
  - `07_后端/lingyi_service/app/routers/quality.py`
  - `07_后端/lingyi_service/app/schemas/quality.py`
  - `07_后端/lingyi_service/app/services/quality_service.py`
  - `07_后端/lingyi_service/app/models/quality.py`
  - `07_后端/lingyi_service/app/crud/quality.py`
- `07_后端/lingyi_service/app` 下存在无关历史 dirty diff：
  - `07_后端/lingyi_service/app/schemas/report.py`
  - `07_后端/lingyi_service/app/services/report_catalog_service.py`
  - `07_后端/lingyi_service/app/services/system_config_catalog_service.py`
- 当前 `test_quality_defect_baseline.py` dirty diff 仍为测试合同层：
  - 未新增 skip/xfail
  - 未删除测试用例
  - 未弱化断言为任意 2xx/4xx
  - 保留草稿创建 `201` 与非 draft `403` / `QUALITY_INVALID_STATUS` 语义断言

## 冻结结论

- failure classification：`TEST_CONTRACT_UPDATE_ALLOWED`
- 下一步允许修复文件：
  - `07_后端/lingyi_service/tests/test_quality_defect_baseline.py`
- 下一任务：`TASK-Z022B-29-FIX-CAND003-SCENARIO-TAG`
- 本轮不运行 pytest；下一步也不得扩大到业务源码、其他测试或控制面文件。

## 产物

- `03_需求与设计/02_开发计划/task_z022b_28_cand003_failure_diag_boundary.json`
- `03_需求与设计/02_开发计划/task_z022b_28_cand003_failure_diag_boundary.tsv`
