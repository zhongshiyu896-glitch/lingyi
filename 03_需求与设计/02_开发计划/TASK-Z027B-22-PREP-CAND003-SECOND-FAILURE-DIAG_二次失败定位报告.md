# TASK-Z027B-22-PREP-CAND003-SECOND-FAILURE-DIAG 二次失败定位报告

## 范围

- 角色：B Engineer
- 候选：Z027-CAND-003
- 来源失败任务：TASK-Z027B-21-FIX-CAND003
- 上一边界任务：TASK-Z027B-20-PREP-CAND003-FAILURE-DIAG
- 本轮只读定位，未运行 pytest，未修改测试或源码，未 stage/commit/push。

## 核对

- current HEAD：`c46b8f5a74166eedf5cfac8c75bad232359a1f87`
- cached 区：空
- B21 result：`command_run_count=1`，`result=FAIL`
- B21 summary：`1 failed, 4 passed, 1 warning in 1.07s`
- `git diff --check`：PASS

## 剩余失败

- 用例：`SecurityAuditTest::test_workshop_resource_forbidden_writes_security_audit`
- 当前状态码：403
- 期望状态码：403
- 剩余断言差异：`row.resource_no`
- 期望：`ITEM-A`
- 实际：`DEMO-TEE`

## 只读定位

B21 已补齐 workshop register 的 schema/local gate carrier，使请求进入目标 403 security-audit 分支。剩余差异来自 fixture/resource expectation drift：

- `app/services/workshop_service.py` 在 local synthetic context 下，`resolve_job_card_resource` 使用默认 `WORKSHOP_LOCAL_DEFAULT_ITEM_CODE = "DEMO-TEE"`。
- `app/services/permission_service.py` 的 `ensure_workshop_resource_permission` 在 item 权限拒绝时，以实际 resolved `item_code` 记录 security audit `resource_no`。
- 因当前测试 payload 未提供 `item_code`，resolved item 为 `DEMO-TEE`，因此 audit row 的 `resource_no` 为 `DEMO-TEE`。

## 分类

- classification：`TEST_CONTRACT_UPDATE_ALLOWED`
- allowed_fix_file：`07_后端/lingyi_service/tests/test_security_audit.py`
- next_task：`TASK-Z027B-23-FIX-CAND003-SECOND`
- run_this_task：false

## 禁止动作确认

- code/test edits：NO
- tests/build/typecheck/npm/browser：NO
- stage/commit/push/tag/PR/release：NO
- reset/checkout/stash/cleanup：NO
- production readback/go-live/project completion：NO
