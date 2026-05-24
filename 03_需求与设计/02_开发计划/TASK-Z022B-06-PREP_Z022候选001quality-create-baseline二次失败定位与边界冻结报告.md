# TASK-Z022B-06-PREP Z022-CAND-001 quality-create-baseline 二次失败定位与边界冻结报告

- 任务：TASK-Z022B-06-PREP
- 角色：B Engineer
- 源任务：TASK-Z022B-05-FIX
- 候选：Z022-CAND-001
- 本轮性质：只读定位与下一步边界冻结

## B05 结果回读

- command：`.venv/bin/python -m pytest tests/test_quality_create_baseline.py -q`
- result：FAIL
- exit_code：1
- pytest_summary：`1 failed, 1 passed, 1 warning in 0.97s`
- 二次失败用例：`test_post_create_returns_201_and_draft`
- 期望 / 实际：expected `201`，actual `409`
- 错误码：`QUALITY_INVALID_SOURCE`
- 错误消息：`LOCAL_GATE_FAIL_CLOSED:non_local_dev`
- B05 已按规则停止，未修改业务源码。

## 只读定位

- `tests/test_quality_create_baseline.py:38-49` 创建用例仍保留 `201` 断言，当前失败来自请求返回 `409`。
- `tests/test_quality_api.py:70-74` 测试基类 fixture 将 `APP_ENV` 固定为 `test`，且未设置 `LINGYI_DB_URL` 为 quality 本地 DB。
- `app/routers/quality.py:338-342` 的 `_ensure_local_dev_write_gate()` 要求 `APP_ENV=development` 且 `LINGYI_DB_URL=sqlite:///./lingyi_service.local.db`，否则抛出 `LOCAL_GATE_FAIL_CLOSED:non_local_dev`。
- `app/routers/quality.py:617-621` 在进入 service create 前调用 `_validate_quality_create_gate()`，因此该 409 发生在业务创建逻辑之前。
- `app/core/error_codes.py:121` 定义 `QUALITY_INVALID_SOURCE`，`app/core/error_codes.py:300` 将其映射为 HTTP `409`。
- `app/schemas/quality.py:38-47` 已证明 payload 必须携带 quality 写入 carrier 字段；B05 已补齐必填字段，但 router 后续 carrier 合同还要求：
  - `APP_ENV/LINGYI_DB_URL` 满足本地 gate；
  - `X-Request-ID` header 与 body `request_id` 一致；
  - `scenario_tag` 命中 `Z003-QUALITY-INSPECTION-YYYYMMDD-NNN`；
  - `source_ref/source_doc/inspection_ref/idempotency_key/item_code/result` 与 request-id carrier 校验一致。

## 结论

- 二次失败不是 quality router/schema/service/model/crud 产品实现缺陷。
- 直接原因是测试合同/fixture 仍未满足当前 local gate 条件；B05 payload 中的 source carrier 也尚未完整符合 router 的 current contract。
- 可形成最小测试合同修复：仅在 `test_quality_create_baseline.py` 内为该测试构造本地 gate 环境、匹配的 `X-Request-ID` 与 carrier payload，并保留原 `201/403` 语义断言。

## 冻结边界

- failure_classification：TEST_CONTRACT_UPDATE_ALLOWED
- allowed_fix_files：`07_后端/lingyi_service/tests/test_quality_create_baseline.py`
- recommended_next_task_id：TASK-Z022B-07-FIX
- single_regression_command：`.venv/bin/python -m pytest tests/test_quality_create_baseline.py -q`
- run_this_task：false
- stage_allowed：false
- commit_allowed：false
- push_allowed：false
- project_completion_claimed：false

## 禁止动作

- 本轮未运行 pytest/npm/browser/build/typecheck/verify。
- 本轮未编辑任何源码、测试、依赖或配置文件。
- 本轮未 stage/commit/push/PR/tag/release。
- 本轮未 cleanup/kill 本地服务。
- 本轮未释放 parked blockers，未声明项目完成。
