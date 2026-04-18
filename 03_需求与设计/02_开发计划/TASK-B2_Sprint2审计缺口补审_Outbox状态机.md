# 【补审任务卡】TASK-B2 Sprint2审计缺口补审 - Outbox 状态机

- 任务编号：TASK-B2
- 任务名称：Sprint2 审计缺口补审（Outbox 公共状态机）
- 角色：审计官
- 优先级：P0
- 前置依赖：TASK-013C 审计通过；基线参考 HEAD `384970400f7a137e8384649bd73cab5ae2d33300`

## 补审范围
- 设计文档：`/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-009_Outbox公共状态机规范.md`
- 实现代码：`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/outbox_state_machine.py`
- 测试：`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_outbox_state_machine.py`
- 交付证据：`/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-009B_Outbox公共状态机模板实现_交付证据.md`、`/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-009B1_event_key运行态字段禁用整改_交付证据.md`

## 审计要点
1. `event_key` 禁止字段完整（含 idempotency_key、request_id、attempts、locked_by、status、error_*、external_doc* 等）。
2. `payload_hash` 稳定性（key 顺序无关、Decimal/date/datetime 序列化稳定）。
3. 状态机迁移严格（终态不可逆、非法迁移 fail closed）。
4. claim/lease/retry/dead 规则符合设计，stale claim 不得抢占有效 lease。
5. worker 外调前置校验要求在规范/实现中可落地。
6. dry-run/diagnostic 审计口径未回退。

## 通过标准
- 高危（P1）= 0。
- 中危（P2）<= 1（若存在必须有明确整改计划）。
- P1/P2 必须整改并复审通过后方可闭环。
- 定向测试通过：`test_outbox_state_machine.py`。

## 执行说明
```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest -q tests/test_outbox_state_machine.py
.venv/bin/python -m py_compile app/services/outbox_state_machine.py tests/test_outbox_state_machine.py
```
如不通过，下发整改任务 `TASK-B2A`，禁止进入下一补审。

## 禁止事项
- 禁止修改 `06_前端/**`、`07_后端/**`、`.github/**`、`02_源码/**`。
- 禁止 push / remote / PR。
- 禁止夹带新功能整改。

## 完成后回复格式
```text
TASK-B2 执行完成。
审计结论：通过 / 有条件通过 / 不通过
问题项：高 X / 中 X / 低 X
是否允许进入下一任务：是 / 否
若否，整改任务：TASK-B2A
```
