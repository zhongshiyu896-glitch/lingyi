# TASK-006F 加工厂对账单封版前证据盘点

- 任务编号：TASK-006F
- 盘点时间：2026-04-15
- 盘点范围：TASK-006A ~ TASK-006F
- 结论口径：仅用于“进入本地封版审计”建议，不代表封版通过或生产发布完成。

## 1. TASK-006A~F 任务链路与审计结论

| 阶段 | 审计意见书 | 结论 | 说明 |
| --- | --- | --- | --- |
| TASK-006A 开发前基线盘点 | 第 161 份 | 通过 | 冻结对账来源、金额口径、幂等、权限与 ERPNext 边界 |
| TASK-006B 草稿模型/迁移/API | 第 162 份 | 不通过 | active-scope 防重与取消后重建约束缺失 |
| TASK-006B1 重复防护整改 | 第 163 份 | 通过 | active-scope 防重 + 取消后重建约束闭环 |
| TASK-006C1 create 路由兜底修复 | 第 164 份 | 通过 | 未知异常兜底不再 NameError，统一错误信封恢复 |
| TASK-006D ERPNext payable outbox | 第 165 份 | 不通过 | cancel/outbox 互斥与 worker claim/lease 存在安全缺口 |
| TASK-006D1 状态机安全整改 | 第 166 份 | 通过 | cancel 与 active outbox 互斥、worker 前置状态校验、claim 原子条件闭环 |
| TASK-006E 前端联调与契约门禁 | 第 167 份 | 不通过 | create 缺 company、payable 摘要契约不完整 |
| TASK-006E1 前后端契约补齐 | 第 168 份 | 不通过 | 同 statement 可重复创建 active outbox |
| TASK-006E2 同 statement active outbox 防重 | 第 169 份 | 通过 | 服务层 + DB 层双重防重、并发冲突收口为稳定业务响应 |
| TASK-006F 打印导出与封版前盘点 | 待审计 | 本文档盘点完成 | 本轮新增打印页、CSV 导出、前端契约门禁补强 |

## 2. 后端能力清单（已完成）

1. 对账草稿创建（来源固定为 `ly_subcontract_inspection`，服务端事实生成）。
2. 对账确认（confirm）与取消（cancel）状态机。
3. cancel 后 inspection 释放与可重建约束。
4. payable outbox 建模、幂等、event_key、active-scope 防重。
5. ERPNext Purchase Invoice 草稿创建链路（仅 docstatus=0）。
6. worker 运行前本地状态强校验、lease claim 原子条件与重试状态机。
7. 同 statement active outbox 防重（`pending/processing/succeeded` 仅允许一条）。

## 3. 前端能力清单（已完成）

1. 加工厂对账单列表页。
2. 加工厂对账单详情页。
3. 对账草稿创建、确认、取消、生成 payable outbox 入口（受权限与状态门禁控制）。
4. payable 摘要字段联动按钮 fail-closed 规则。
5. 打印视图：`/factory-statements/print?id=<id>`。
6. 详情快照 CSV 导出（当前单据、当前已加载明细）。
7. `factory-statement` 契约门禁与反向测试纳入 `npm run verify`。

## 4. 禁止能力清单（仍冻结）

1. 提交 ERPNext Purchase Invoice（docstatus=1）。
2. 创建 Payment Entry。
3. 创建 GL Entry。
4. 对账调整单与自动反冲/红冲。
5. failed/dead payable outbox 重建/reset 新能力。
6. 前端调用 `/api/factory-statements/internal/*` 或任意 run-once。
7. 前端直连 ERPNext `/api/resource`。

## 5. 测试命令与最近一次结果

### 5.1 本轮 TASK-006F 前端验证

执行目录：`/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc`

1. `npm run check:factory-statement-contracts`：通过（`Scanned files: 8`）。
2. `npm run test:factory-statement-contracts`：通过（`scenarios=19`）。
3. `npm run verify`：通过（包含 production/style-profit/factory-statement 契约、typecheck、build）。
4. `npm audit --audit-level=high`：通过（`found 0 vulnerabilities`）。

### 5.2 最新后端可追溯结果（沿用 TASK-006E2 已审计证据）

来源：`/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-006E2_PayableDraft同StatementActiveOutbox防重整改_交付证据.md`

1. 定向 pytest：`24 passed`。
2. 全 factory-statement pytest：`77 passed`。
3. `py_compile`：通过。

## 6. 剩余风险与待后续处理项

1. Python `datetime.utcnow` 未来兼容性 warning（非本轮前端任务范围，需在后续后端清理）。
2. failed/dead outbox 重建策略当前仍按冻结口径保守处理，未开放前端重试入口。
3. 生产环境 ERPNext 权限源、Supplier/Account/Cost Center 主数据可用性仍需上线前实网验收。
4. 当前仓库存在历史未跟踪与非本任务脏改动，封版审计需继续按白名单核对提交范围。

## 7. 结论

结论：**建议进入审计**。

说明：本结论仅表示 TASK-006F 的打印导出与封版前证据盘点已具备审计输入条件；不表示 TASK-006 已封版通过，不表示生产发布完成。
