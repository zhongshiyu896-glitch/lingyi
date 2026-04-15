# TASK-006G 加工厂对账单本地封版复审交付证据

- 任务编号：TASK-006G
- 交付时间：2026-04-15 22:17:21 CST
- 当前 HEAD：`1da795333d20ed8ecfb2308da623358668272458`
- 结论：建议进入 TASK-006 本地封版审计

## 交付文件
1. `03_需求与设计/02_开发计划/TASK-006G_加工厂对账单本地封版复审证据.md`
2. `03_需求与设计/02_开发计划/TASK-006G_加工厂对账单本地封版复审_交付证据.md`

## 复跑结果摘要

### 后端
- 命令：`.venv/bin/python -m pytest -q tests/test_factory_statement*.py`
- 结果：`77 passed, 244 warnings`
- 命令：`.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)`
- 结果：通过

### 前端
- 命令：`npm run check:factory-statement-contracts`
- 结果：通过（`Scanned files: 8`）
- 命令：`npm run test:factory-statement-contracts`
- 结果：通过（`scenarios=26`）
- 命令：`npm run verify`
- 结果：通过
- 命令：`npm audit --audit-level=high`
- 结果：`found 0 vulnerabilities`

## 禁改与运行产物说明
- 本任务仅新增证据文档，未改动前端/后端业务代码、`.github`、`02_源码`。
- 工作区存在历史遗留改动与未跟踪文件；本任务未扩大该范围。
- `npm run verify` 产生 `dist/` 构建产物，已按运行产物处理，不纳入提交基线。

## 禁止能力结论
- 未发现 TASK-006 禁止能力被放开：
  - 未发现 Purchase Invoice submit / Payment Entry / GL Entry 实现。
  - 未发现前端 internal worker 调用或 ERPNext `/api/resource` 直连落地。
  - 未发现 failed/dead payable outbox 重建/reset 实现。

## 剩余风险
1. `datetime.utcnow()` deprecation warning 仍存在。
2. failed/dead outbox 重建策略未实现，需后续单任务处理。
3. 本地验证不等同生产 ERPNext 验证与平台 required checks 闭环。
4. 工作区历史未跟踪文件较多，后续提交必须白名单暂存。
