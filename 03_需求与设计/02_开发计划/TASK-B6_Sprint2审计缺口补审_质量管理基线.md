# 【补审任务卡】TASK-B6 Sprint2审计缺口补审 - 质量管理基线

- 任务编号：TASK-B6
- 任务名称：Sprint2 审计缺口补审（质量管理基线）
- 角色：审计官
- 优先级：P0
- 前置依赖：TASK-013C 审计通过；基线参考 HEAD `384970400f7a137e8384649bd73cab5ae2d33300`

## 补审范围
- 设计文档：`/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-012_质量管理基线设计.md`
- 后端：quality model/schema/service/router/migration/tests
- 前端：quality API/views/router/store/contracts
- 证据：`TASK-012B/B1/C/E/F` 系列交付证据

## 审计要点
1. 来源归属校验（incoming_material / finished_goods）与 fail closed。
2. 状态机：`draft -> confirmed -> cancelled`，confirmed 不可改关键事实，cancelled 不参与统计。
3. ERPNext 主数据校验 fail closed，malformed/unavailable 不得伪成功。
4. 严禁 ERPNext 写入、严禁 outbox/worker、严禁财务写入（PI/Payment/GL）。
5. 前端权限绑定完整，diagnostic 不暴露普通 UI，禁直连 `/api/resource`。

## 通过标准
- 高危（P1）= 0。
- 中危（P2）<= 1（若存在必须有明确整改计划）。
- P1/P2 必须整改并复审通过后方可闭环。
- 后端质量测试与前端契约测试通过。

## 执行说明
```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest -q tests/test_quality*.py tests/test_permissions*.py tests/test_erpnext_fail_closed_adapter.py

cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc
npm run check:quality-contracts
npm run test:quality-contracts
npm run verify
```
不通过下发 `TASK-B6A`。

## 禁止事项
- 禁止修改 `06_前端/**`、`07_后端/**`、`.github/**`、`02_源码/**`。
- 禁止 push / remote / PR。
- 禁止引入 AQL 深度算法、自动返工、自动扣款、自动报废入账等超范围功能。

## 完成后回复格式
```text
TASK-B6 执行完成。
审计结论：通过 / 有条件通过 / 不通过
问题项：高 X / 中 X / 低 X
是否允许进入下一任务：是 / 否
若否，整改任务：TASK-B6A
```
