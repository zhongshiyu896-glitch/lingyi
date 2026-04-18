# B-2 TASK-009 Outbox 公共状态机补审执行报告

- 任务编号：B-2
- 模块：TASK-009 Outbox 公共状态机
- 执行时间：2026-04-17 14:15
- 执行角色：工程师（补审执行）

## 1. 检查项逐项结论

### 检查项 1：`event_key` 是否禁止运行态字段
- 结论：✅ 通过
- 代码位置证据：
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/outbox_state_machine.py:66` 定义 `FORBIDDEN_EVENT_KEY_FIELDS`，覆盖 `attempts/locked_by/locked_until/next_retry_at/status/error_*/external_doc*` 等运行态字段。
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/outbox_state_machine.py:179`~`216` 在 `normalize_event_key_parts` 中对禁用字段直接 fail-closed。
- 测试覆盖证据：
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_outbox_state_machine.py:103` `test_build_event_key_rejects_runtime_fields` 参数化覆盖运行态字段并断言拒绝。

### 检查项 2：`idempotency_key` 与 `event_key` 职责是否分离
- 结论：✅ 通过
- 代码位置证据：
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/outbox_state_machine.py:68` 将 `idempotency_key` 置入 `FORBIDDEN_EVENT_KEY_FIELDS`。
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/outbox_state_machine.py:219` `build_event_key` 仅基于稳定业务事实构建 hash。
- 设计位置证据：
  - `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-009_Outbox公共状态机规范.md:123` 明确 `idempotency_key` 负责“请求重放/冲突”，`event_key` 负责“业务事实防重”。
- 测试覆盖证据：
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_outbox_state_machine.py:74` `test_event_key_rejects_forbidden_mutable_fields` 覆盖 `idempotency_key`。

### 检查项 3：claim / lease / retry / dead 状态机是否安全
- 结论：✅ 通过
- 代码位置证据：
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/outbox_state_machine.py:121` 定义状态迁移矩阵（含 `dead/cancelled` 终态）。
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/outbox_state_machine.py:286`~`350` 覆盖 due、lease 过期与二阶段 claim guard 计算。
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/outbox_state_machine.py:385`~`423` 统一 retry/dead 决策。
- 测试覆盖证据：
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_outbox_state_machine.py:249` `test_processing_unexpired_lease_cannot_be_claimed_stale_guard`（防 stale 抢占）。
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_outbox_state_machine.py:238` `test_processing_lease_expired_can_be_claimed`（过期可重抢）。
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_outbox_state_machine.py:296`、`:307`（non-retryable 与 max attempts 进入 dead）。

### 检查项 4：worker 外调前置校验是否明确
- 结论：✅ 通过
- 设计位置证据：
  - `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-009_Outbox公共状态机规范.md:156`~`171` 明确 worker 外调前置校验（聚合存在/状态允许/权限有效/docstatus 校验等）。
  - `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-009_Outbox公共状态机规范.md:149`~`152` 明确“claim 事务先提交，再外调 ERPNext”。
- 说明：本检查项属于模板规范与流程要求，口径已保留且未回退。

### 检查项 5：dry-run / diagnostic 审计要求是否保留
- 结论：✅ 通过
- 代码位置证据：
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/outbox_state_machine.py:426`~`449` `build_dry_run_preview` 固定 `will_mutate=False`。
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/outbox_state_machine.py:452` `evaluate_diagnostic_window` 支持节流窗口。
- 设计位置证据：
  - `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-009_Outbox公共状态机规范.md:177`~`187` 明确 dry-run/diagnostic 审计与禁暴露要求。
- 测试覆盖证据：
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_outbox_state_machine.py:337` dry-run 不改状态。
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_outbox_state_machine.py:349`、`:358`、`:367` diagnostic cooldown/计数行为。

## 2. 测试命令与结果

### pytest
```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest -q tests/test_outbox_state_machine.py
```
结果：`59 passed, 1 warning in 0.05s`

### py_compile
```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m py_compile app/services/outbox_state_machine.py tests/test_outbox_state_machine.py
```
结果：通过（无报错，`PY_COMPILE_OK`）

## 3. 问题项
- 高：0
- 中：0
- 低：0

## 4. 结论
- 结论：提交审计
- 说明：本报告为补审执行报告，不替代审计官正式审计意见书。
