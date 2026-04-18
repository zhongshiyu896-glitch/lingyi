# 【补审任务卡】TASK-B3 Sprint2审计缺口补审 - 前端门禁框架

- 任务编号：TASK-B3
- 任务名称：Sprint2 审计缺口补审（前端写入口门禁公共框架）
- 角色：审计官
- 优先级：P0
- 前置依赖：TASK-013C 审计通过；基线参考 HEAD `384970400f7a137e8384649bd73cab5ae2d33300`

## 补审范围
- 设计文档：`/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-010_前端写入口门禁公共框架设计.md`
- 实现代码：`/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/frontend-contract-engine.mjs`
- wrapper：
  - `check-style-profit-contracts.mjs`
  - `check-factory-statement-contracts.mjs`
  - `check-sales-inventory-contracts.mjs`
  - `check-quality-contracts.mjs`
- 测试：`test-frontend-contract-engine.mjs` 及各模块 `test-*-contracts.mjs`

## 审计要点
1. unknown `scanScopes` 必须 fail closed。
2. `scannedFiles=0` 必须 fail closed。
3. `fixture.positive/negative` 强制非空，legacy 豁免不得存在。
4. 高危绕过覆盖（eval/Function/Worker/dynamic import/fetch/axios/internal/api_resource）。
5. 旧模块场景数不回退（style-profit >= 475，factory-statement >= 26，sales-inventory >= 13，quality >= 14，frontend-engine >= 25）。

## 通过标准
- 高危（P1）= 0。
- 中危（P2）<= 1（若存在必须有明确整改计划）。
- P1/P2 必须整改并复审通过后方可闭环。
- `npm run verify` 与 `npm audit --audit-level=high` 通过。

## 执行说明
```bash
cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc
npm run test:frontend-contract-engine
npm run test:style-profit-contracts
npm run test:factory-statement-contracts
npm run test:sales-inventory-contracts
npm run test:quality-contracts
npm run verify
npm audit --audit-level=high
```
不通过则下发 `TASK-B3A`，并明确回归风险。

## 禁止事项
- 禁止修改 `06_前端/**`、`07_后端/**`、`.github/**`、`02_源码/**`。
- 禁止 push / remote / PR。
- 禁止删除反向 fixture 以规避审计。

## 完成后回复格式
```text
TASK-B3 执行完成。
审计结论：通过 / 有条件通过 / 不通过
问题项：高 X / 中 X / 低 X
是否允许进入下一任务：是 / 否
若否，整改任务：TASK-B3A
```
