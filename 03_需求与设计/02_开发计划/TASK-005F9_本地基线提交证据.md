# TASK-005F9 本地基线提交证据

- 任务编号：TASK-005F9
- 记录时间：2026-04-14 16:31 CST
- 提交前 HEAD：`e8654f93e5e056bf14199f3ba19431d34ac326b4`
- 提交后 HEAD：`81c3cfa25acc77b0a57ae00a282fecb8dca81550`
- commit message：`chore: baseline task 005f profit postgres gate`

## 1. staged 文件清单（提交内容）

- .github/workflows/backend-postgresql.yml
- 03_需求与设计/01_架构设计/03_技术决策记录.md
- 03_需求与设计/01_架构设计/06_模块设计_款式利润报表.md
- 03_需求与设计/01_架构设计/架构师会话日志.md
- 03_需求与设计/02_开发计划/TASK-005F1_利润SLE归属与外发来源阻断整改_工程任务单.md
- 03_需求与设计/02_开发计划/TASK-005F2_外发利润归属桥接字段与补数_工程任务单.md
- 03_需求与设计/02_开发计划/TASK-005F3_外发WorkOrder严格匹配与补数审计整改_工程任务单.md
- 03_需求与设计/02_开发计划/TASK-005F4_PostgreSQL非Skip证据.md
- 03_需求与设计/02_开发计划/TASK-005F4_外发利润查询下推与PostgreSQL证据_工程任务单.md
- 03_需求与设计/02_开发计划/TASK-005F5_PostgreSQL门禁目标恢复与双JUnit断言_工程任务单.md
- 03_需求与设计/02_开发计划/TASK-005F6_Workflow双JUnit上传与PG证据回填_工程任务单.md
- 03_需求与设计/02_开发计划/TASK-005F6_Workflow双JUnit上传证据.md
- 03_需求与设计/02_开发计划/TASK-005F7_PostgreSQL真实非Skip证据.md
- 03_需求与设计/02_开发计划/TASK-005F7_PostgreSQL真实非Skip证据闭环_工程任务单.md
- 03_需求与设计/02_开发计划/TASK-005F8_PostgreSQL外发Schema基线与双门禁复跑_工程任务单.md
- 03_需求与设计/02_开发计划/TASK-005F8_PostgreSQL外发Schema基线修复证据.md
- 03_需求与设计/02_开发计划/TASK-005F9_款式利润F阶段本地基线提交_工程任务单.md
- 03_需求与设计/02_开发计划/TASK-005F_款式利润真实服务端来源Adapter_工程任务单.md
- 03_需求与设计/02_开发计划/当前 sprint 任务清单.md
- 03_需求与设计/05_审计记录.md
- 03_需求与设计/05_审计记录/审计官会话日志.md
- 07_后端/lingyi_service/README.md
- 07_后端/lingyi_service/app/core/error_codes.py
- 07_后端/lingyi_service/app/models/subcontract.py
- 07_后端/lingyi_service/app/routers/style_profit.py
- 07_后端/lingyi_service/app/schemas/subcontract.py
- 07_后端/lingyi_service/app/services/erpnext_style_profit_adapter.py
- 07_后端/lingyi_service/app/services/style_profit_api_source_collector.py
- 07_后端/lingyi_service/app/services/style_profit_service.py
- 07_后端/lingyi_service/app/services/style_profit_source_service.py
- 07_后端/lingyi_service/app/services/subcontract_profit_scope_backfill_service.py
- 07_后端/lingyi_service/app/services/subcontract_service.py
- 07_后端/lingyi_service/migrations/versions/task_005f2_subcontract_profit_scope_bridge.py
- 07_后端/lingyi_service/scripts/run_postgresql_ci_gate.sh
- 07_后端/lingyi_service/tests/test_ci_postgresql_gate.py
- 07_后端/lingyi_service/tests/test_style_profit_api.py
- 07_后端/lingyi_service/tests/test_style_profit_api_source_adapter.py
- 07_后端/lingyi_service/tests/test_style_profit_service.py
- 07_后端/lingyi_service/tests/test_style_profit_snapshot_calculation.py
- 07_后端/lingyi_service/tests/test_style_profit_source_collector.py
- 07_后端/lingyi_service/tests/test_style_profit_source_mapping.py
- 07_后端/lingyi_service/tests/test_style_profit_subcontract_bridge.py
- 07_后端/lingyi_service/tests/test_style_profit_subcontract_postgresql.py
- 07_后端/lingyi_service/tests/test_subcontract_profit_scope_bridge.py
- 07_后端/lingyi_service/tests/test_subcontract_settlement_postgresql.py

## 2. 排除文件清单（未纳入提交）

1. 禁止目录均未纳入本次提交。
   - 00_交接与日志/**
   - 01_需求与资料/**
   - 02_源码/**
   - 03_环境与部署/**
   - 04_测试与验收/**
   - 05_交付物/**
   - 06_前端/**
   - TASK-006*
2. `.pytest-postgresql-*.xml` 运行产物未纳入本次提交。
3. 历史未跟踪大目录保持未提交状态。

## 3. 回归测试结果

在 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service` 执行如下命令。

1. `.venv/bin/python -m pytest -q tests/test_ci_postgresql_gate.py`：12 passed
2. `.venv/bin/python -m pytest -q tests/test_subcontract_settlement_postgresql.py tests/test_style_profit_subcontract_postgresql.py`：5 passed, 8 skipped
3. `.venv/bin/python -m pytest -q`：641 passed, 13 skipped
4. `.venv/bin/python -m unittest discover`：624 tests, OK (skipped=1)
5. `.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)`：通过

## 4. PostgreSQL 双 JUnit 非 Skip 结果引用

1. `07_后端/lingyi_service/.pytest-postgresql-subcontract-settlement.xml`
   - tests=4, skipped=0, failures=0, errors=0
2. `07_后端/lingyi_service/.pytest-postgresql-style-profit-subcontract.xml`
   - tests=4, skipped=0, failures=0, errors=0

说明：上述 JUnit XML 为本地运行时产物，未纳入 commit。

## 5. git show --stat --name-only HEAD 摘要

`81c3cfa chore: baseline task 005f profit postgres gate`

- .github/workflows/backend-postgresql.yml
- 03_需求与设计/01_架构设计/03_技术决策记录.md
- 03_需求与设计/01_架构设计/06_模块设计_款式利润报表.md
- 03_需求与设计/01_架构设计/架构师会话日志.md
- 03_需求与设计/02_开发计划/TASK-005F1_利润SLE归属与外发来源阻断整改_工程任务单.md
- 03_需求与设计/02_开发计划/TASK-005F2_外发利润归属桥接字段与补数_工程任务单.md
- 03_需求与设计/02_开发计划/TASK-005F3_外发WorkOrder严格匹配与补数审计整改_工程任务单.md
- 03_需求与设计/02_开发计划/TASK-005F4_PostgreSQL非Skip证据.md
- 03_需求与设计/02_开发计划/TASK-005F4_外发利润查询下推与PostgreSQL证据_工程任务单.md
- 03_需求与设计/02_开发计划/TASK-005F5_PostgreSQL门禁目标恢复与双JUnit断言_工程任务单.md
- 03_需求与设计/02_开发计划/TASK-005F6_Workflow双JUnit上传与PG证据回填_工程任务单.md
- 03_需求与设计/02_开发计划/TASK-005F6_Workflow双JUnit上传证据.md
- 03_需求与设计/02_开发计划/TASK-005F7_PostgreSQL真实非Skip证据.md
- 03_需求与设计/02_开发计划/TASK-005F7_PostgreSQL真实非Skip证据闭环_工程任务单.md
- 03_需求与设计/02_开发计划/TASK-005F8_PostgreSQL外发Schema基线与双门禁复跑_工程任务单.md
- 03_需求与设计/02_开发计划/TASK-005F8_PostgreSQL外发Schema基线修复证据.md
- 03_需求与设计/02_开发计划/TASK-005F9_款式利润F阶段本地基线提交_工程任务单.md
- 03_需求与设计/02_开发计划/TASK-005F_款式利润真实服务端来源Adapter_工程任务单.md
- 03_需求与设计/02_开发计划/当前 sprint 任务清单.md
- 03_需求与设计/05_审计记录.md
- 03_需求与设计/05_审计记录/审计官会话日志.md
- 07_后端/lingyi_service/README.md
- 07_后端/lingyi_service/app/core/error_codes.py
- 07_后端/lingyi_service/app/models/subcontract.py
- 07_后端/lingyi_service/app/routers/style_profit.py
- 07_后端/lingyi_service/app/schemas/subcontract.py
- 07_后端/lingyi_service/app/services/erpnext_style_profit_adapter.py
- 07_后端/lingyi_service/app/services/style_profit_api_source_collector.py
- 07_后端/lingyi_service/app/services/style_profit_service.py
- 07_后端/lingyi_service/app/services/style_profit_source_service.py
- 07_后端/lingyi_service/app/services/subcontract_profit_scope_backfill_service.py
- 07_后端/lingyi_service/app/services/subcontract_service.py
- 07_后端/lingyi_service/migrations/versions/task_005f2_subcontract_profit_scope_bridge.py
- 07_后端/lingyi_service/scripts/run_postgresql_ci_gate.sh
- 07_后端/lingyi_service/tests/test_ci_postgresql_gate.py
- 07_后端/lingyi_service/tests/test_style_profit_api.py
- 07_后端/lingyi_service/tests/test_style_profit_api_source_adapter.py
- 07_后端/lingyi_service/tests/test_style_profit_service.py
- 07_后端/lingyi_service/tests/test_style_profit_snapshot_calculation.py
- 07_后端/lingyi_service/tests/test_style_profit_source_collector.py
- 07_后端/lingyi_service/tests/test_style_profit_source_mapping.py
- 07_后端/lingyi_service/tests/test_style_profit_subcontract_bridge.py
- 07_后端/lingyi_service/tests/test_style_profit_subcontract_postgresql.py
- 07_后端/lingyi_service/tests/test_subcontract_profit_scope_bridge.py
- 07_后端/lingyi_service/tests/test_subcontract_settlement_postgresql.py

## 6. git status --short 摘要（提交后）

- `?? 00_交接与日志/`
- `?? 01_需求与资料/`
- `?? 02_源码/`
- `?? 03_环境与部署/`
- `?? 03_需求与设计/差异分析与修复计划.md`
- `?? 04_测试与验收/`
- `?? 05_交付物/`
- `?? 06_前端/lingyi-pc/README.md`
- `?? 07_后端/lingyi_service/.pytest-postgresql-style-profit-subcontract.xml`
- `?? 07_后端/lingyi_service/.pytest-postgresql-subcontract-settlement.xml`

说明：历史未跟踪目录与本地 JUnit 结果文件仍未提交。

## 7. 结论

1. 已按白名单完成 TASK-005F9 本地基线提交证据归档。
2. 本次证据修正明确记录：未使用 `git add .`、未使用 `git add -A`。
3. `.pytest-postgresql-*.xml` 为本地产物，未纳入版本库提交。
4. 禁止路径（`.github/**`、`07_后端/**`、`06_前端/**`、`02_源码/**`、历史大目录、`TASK-006*`）未纳入本次 docs-only 修正提交范围。
5. 审计官复审通过前，不进入 TASK-005G、前端创建入口或 TASK-006。
