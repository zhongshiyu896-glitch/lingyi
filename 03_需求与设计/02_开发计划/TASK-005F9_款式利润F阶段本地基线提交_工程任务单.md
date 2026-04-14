# TASK-005F9 款式利润 F 阶段本地基线提交工程任务单

- 任务编号：TASK-005F9
- 模块：款式利润报表 / 外发加工管理 / PostgreSQL CI 门禁
- 版本：V1.0
- 更新时间：2026-04-14 16:26 CST
- 作者：技术架构师
- 优先级：P0
- 前置依赖：TASK-005F8 审计通过，审计意见书第 111 份
- 执行角色：后端工程师
- 审计要求：完成后必须提交审计官复审；复审通过前不得进入 TASK-005G、前端创建入口或 TASK-006

## 1. 任务目标

将 TASK-005F ~ TASK-005F8 的真实来源 Adapter、外发利润桥接字段、PostgreSQL 双门禁、证据文档和架构记录做一次本地白名单基线提交。

本任务只做 staging、复核、测试和本地 commit，不做新功能实现。

目标是避免以下关键成果停留在未跟踪或未提交状态：

1. TASK-005F2 外发利润桥接迁移。
2. TASK-005F8 settlement PostgreSQL schema 基线修复。
3. TASK-005F4~F8 PostgreSQL 双门禁脚本、workflow、测试和证据。
4. TASK-005F~F8 真实来源 Adapter、归属校验和防回退测试。
5. 架构文档、ADR、Sprint 清单、审计记录和会话日志。

## 2. 本任务边界

### 2.1 允许操作

- `git status`
- `git add` 白名单文件
- `git diff --cached --name-only`
- `git diff --cached --stat`
- 回归测试
- 本地 `git commit`

### 2.2 禁止操作

- 禁止修改业务代码
- 禁止修改测试代码
- 禁止修改迁移文件
- 禁止修改 `.github` 文件内容
- 禁止新增前端内容
- 禁止进入 TASK-005G
- 禁止进入 TASK-006
- 禁止 `git add .`
- 禁止 `git add -A`
- 禁止提交历史未跟踪大目录
- 禁止提交运行时生成的 `.pytest-postgresql-*.xml`
- 禁止 force push
- 禁止 amend 既有提交

如发现白名单之外仍有必须提交的文件，停止并回报，不得自行扩大范围。

## 3. 必须排除的路径

以下路径不得进入本次 commit：

- `/Users/hh/Desktop/领意服装管理系统/00_交接与日志/**`
- `/Users/hh/Desktop/领意服装管理系统/01_需求与资料/**`
- `/Users/hh/Desktop/领意服装管理系统/02_源码/**`
- `/Users/hh/Desktop/领意服装管理系统/03_环境与部署/**`
- `/Users/hh/Desktop/领意服装管理系统/04_测试与验收/**`
- `/Users/hh/Desktop/领意服装管理系统/05_交付物/**`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/**`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/.pytest-postgresql-subcontract-settlement.xml`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/.pytest-postgresql-style-profit-subcontract.xml`
- 任何 `TASK-006*` 文件

说明：JUnit XML 是运行时产物，不直接提交；证据以 Markdown 文档提交。

## 4. 白名单文件

只允许 staging 以下文件。

### 4.1 CI / 门禁

- `.github/workflows/backend-postgresql.yml`
- `07_后端/lingyi_service/scripts/run_postgresql_ci_gate.sh`
- `07_后端/lingyi_service/README.md`

### 4.2 后端代码

- `07_后端/lingyi_service/app/core/error_codes.py`
- `07_后端/lingyi_service/app/models/subcontract.py`
- `07_后端/lingyi_service/app/routers/style_profit.py`
- `07_后端/lingyi_service/app/schemas/subcontract.py`
- `07_后端/lingyi_service/app/services/erpnext_style_profit_adapter.py`
- `07_后端/lingyi_service/app/services/style_profit_api_source_collector.py`
- `07_后端/lingyi_service/app/services/style_profit_service.py`
- `07_后端/lingyi_service/app/services/style_profit_source_service.py`
- `07_后端/lingyi_service/app/services/subcontract_profit_scope_backfill_service.py`
- `07_后端/lingyi_service/app/services/subcontract_service.py`

### 4.3 迁移

- `07_后端/lingyi_service/migrations/versions/task_005f2_subcontract_profit_scope_bridge.py`

### 4.4 测试

- `07_后端/lingyi_service/tests/test_ci_postgresql_gate.py`
- `07_后端/lingyi_service/tests/test_style_profit_api.py`
- `07_后端/lingyi_service/tests/test_style_profit_api_source_adapter.py`
- `07_后端/lingyi_service/tests/test_style_profit_service.py`
- `07_后端/lingyi_service/tests/test_style_profit_snapshot_calculation.py`
- `07_后端/lingyi_service/tests/test_style_profit_source_collector.py`
- `07_后端/lingyi_service/tests/test_style_profit_source_mapping.py`
- `07_后端/lingyi_service/tests/test_style_profit_subcontract_bridge.py`
- `07_后端/lingyi_service/tests/test_style_profit_subcontract_postgresql.py`
- `07_后端/lingyi_service/tests/test_subcontract_profit_scope_bridge.py`
- `07_后端/lingyi_service/tests/test_subcontract_settlement_postgresql.py`

### 4.5 架构 / 计划 / 审计文档

- `03_需求与设计/01_架构设计/03_技术决策记录.md`
- `03_需求与设计/01_架构设计/06_模块设计_款式利润报表.md`
- `03_需求与设计/01_架构设计/架构师会话日志.md`
- `03_需求与设计/02_开发计划/当前 sprint 任务清单.md`
- `03_需求与设计/05_审计记录.md`
- `03_需求与设计/05_审计记录/审计官会话日志.md`

### 4.6 TASK-005F 系列任务单与证据

- `03_需求与设计/02_开发计划/TASK-005F_款式利润真实服务端来源Adapter_工程任务单.md`
- `03_需求与设计/02_开发计划/TASK-005F1_利润SLE归属与外发来源阻断整改_工程任务单.md`
- `03_需求与设计/02_开发计划/TASK-005F2_外发利润归属桥接字段与补数_工程任务单.md`
- `03_需求与设计/02_开发计划/TASK-005F3_外发WorkOrder严格匹配与补数审计整改_工程任务单.md`
- `03_需求与设计/02_开发计划/TASK-005F4_外发利润查询下推与PostgreSQL证据_工程任务单.md`
- `03_需求与设计/02_开发计划/TASK-005F4_PostgreSQL非Skip证据.md`
- `03_需求与设计/02_开发计划/TASK-005F5_PostgreSQL门禁目标恢复与双JUnit断言_工程任务单.md`
- `03_需求与设计/02_开发计划/TASK-005F6_Workflow双JUnit上传与PG证据回填_工程任务单.md`
- `03_需求与设计/02_开发计划/TASK-005F6_Workflow双JUnit上传证据.md`
- `03_需求与设计/02_开发计划/TASK-005F7_PostgreSQL真实非Skip证据闭环_工程任务单.md`
- `03_需求与设计/02_开发计划/TASK-005F7_PostgreSQL真实非Skip证据.md`
- `03_需求与设计/02_开发计划/TASK-005F8_PostgreSQL外发Schema基线与双门禁复跑_工程任务单.md`
- `03_需求与设计/02_开发计划/TASK-005F8_PostgreSQL外发Schema基线修复证据.md`
- `03_需求与设计/02_开发计划/TASK-005F9_款式利润F阶段本地基线提交_工程任务单.md`

## 5. 推荐 staging 命令

在项目根目录执行：

```bash
cd /Users/hh/Desktop/领意服装管理系统

git add -- \
  .github/workflows/backend-postgresql.yml \
  '07_后端/lingyi_service/scripts/run_postgresql_ci_gate.sh' \
  '07_后端/lingyi_service/README.md' \
  '07_后端/lingyi_service/app/core/error_codes.py' \
  '07_后端/lingyi_service/app/models/subcontract.py' \
  '07_后端/lingyi_service/app/routers/style_profit.py' \
  '07_后端/lingyi_service/app/schemas/subcontract.py' \
  '07_后端/lingyi_service/app/services/erpnext_style_profit_adapter.py' \
  '07_后端/lingyi_service/app/services/style_profit_api_source_collector.py' \
  '07_后端/lingyi_service/app/services/style_profit_service.py' \
  '07_后端/lingyi_service/app/services/style_profit_source_service.py' \
  '07_后端/lingyi_service/app/services/subcontract_profit_scope_backfill_service.py' \
  '07_后端/lingyi_service/app/services/subcontract_service.py' \
  '07_后端/lingyi_service/migrations/versions/task_005f2_subcontract_profit_scope_bridge.py' \
  '07_后端/lingyi_service/tests/test_ci_postgresql_gate.py' \
  '07_后端/lingyi_service/tests/test_style_profit_api.py' \
  '07_后端/lingyi_service/tests/test_style_profit_api_source_adapter.py' \
  '07_后端/lingyi_service/tests/test_style_profit_service.py' \
  '07_后端/lingyi_service/tests/test_style_profit_snapshot_calculation.py' \
  '07_后端/lingyi_service/tests/test_style_profit_source_collector.py' \
  '07_后端/lingyi_service/tests/test_style_profit_source_mapping.py' \
  '07_后端/lingyi_service/tests/test_style_profit_subcontract_bridge.py' \
  '07_后端/lingyi_service/tests/test_style_profit_subcontract_postgresql.py' \
  '07_后端/lingyi_service/tests/test_subcontract_profit_scope_bridge.py' \
  '07_后端/lingyi_service/tests/test_subcontract_settlement_postgresql.py' \
  '03_需求与设计/01_架构设计/03_技术决策记录.md' \
  '03_需求与设计/01_架构设计/06_模块设计_款式利润报表.md' \
  '03_需求与设计/01_架构设计/架构师会话日志.md' \
  '03_需求与设计/02_开发计划/当前 sprint 任务清单.md' \
  '03_需求与设计/05_审计记录.md' \
  '03_需求与设计/05_审计记录/审计官会话日志.md' \
  '03_需求与设计/02_开发计划/TASK-005F_款式利润真实服务端来源Adapter_工程任务单.md' \
  '03_需求与设计/02_开发计划/TASK-005F1_利润SLE归属与外发来源阻断整改_工程任务单.md' \
  '03_需求与设计/02_开发计划/TASK-005F2_外发利润归属桥接字段与补数_工程任务单.md' \
  '03_需求与设计/02_开发计划/TASK-005F3_外发WorkOrder严格匹配与补数审计整改_工程任务单.md' \
  '03_需求与设计/02_开发计划/TASK-005F4_外发利润查询下推与PostgreSQL证据_工程任务单.md' \
  '03_需求与设计/02_开发计划/TASK-005F4_PostgreSQL非Skip证据.md' \
  '03_需求与设计/02_开发计划/TASK-005F5_PostgreSQL门禁目标恢复与双JUnit断言_工程任务单.md' \
  '03_需求与设计/02_开发计划/TASK-005F6_Workflow双JUnit上传与PG证据回填_工程任务单.md' \
  '03_需求与设计/02_开发计划/TASK-005F6_Workflow双JUnit上传证据.md' \
  '03_需求与设计/02_开发计划/TASK-005F7_PostgreSQL真实非Skip证据闭环_工程任务单.md' \
  '03_需求与设计/02_开发计划/TASK-005F7_PostgreSQL真实非Skip证据.md' \
  '03_需求与设计/02_开发计划/TASK-005F8_PostgreSQL外发Schema基线与双门禁复跑_工程任务单.md' \
  '03_需求与设计/02_开发计划/TASK-005F8_PostgreSQL外发Schema基线修复证据.md' \
  '03_需求与设计/02_开发计划/TASK-005F9_款式利润F阶段本地基线提交_工程任务单.md'
```

## 6. staged 文件复核

staging 后必须执行：

```bash
git diff --cached --name-only
```

输出必须只包含第 4 章白名单文件。

如果出现以下任一情况，必须立刻停止并 `git restore --staged <非白名单文件>`：

1. 出现 `00_交接与日志/`。
2. 出现 `01_需求与资料/`。
3. 出现 `02_源码/`。
4. 出现 `03_环境与部署/`。
5. 出现 `04_测试与验收/`。
6. 出现 `05_交付物/`。
7. 出现 `06_前端/`。
8. 出现 `.pytest-postgresql-*.xml`。
9. 出现 `TASK-006`。

## 7. 提交前验证

必须执行：

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service

.venv/bin/python -m pytest -q tests/test_ci_postgresql_gate.py
.venv/bin/python -m pytest -q tests/test_subcontract_settlement_postgresql.py tests/test_style_profit_subcontract_postgresql.py
.venv/bin/python -m pytest -q
.venv/bin/python -m unittest discover
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
```

必须记录 TASK-005F8 已有的真实 PostgreSQL 双 JUnit 结果：

- settlement：`tests=4, skipped=0, failures=0, errors=0`
- style-profit：`tests=4, skipped=0, failures=0, errors=0`

## 8. 提交命令

验证通过后，在项目根目录执行：

```bash
cd /Users/hh/Desktop/领意服装管理系统

git commit -m "chore: baseline task 005f profit postgres gate"
```

禁止 amend，禁止 force push。本任务只做本地 commit，不做远端 push。

## 9. 提交后验证

提交后必须执行：

```bash
git status --short

git show --stat --oneline --name-only HEAD
```

要求：

1. HEAD 提交范围只包含白名单文件。
2. `.pytest-postgresql-*.xml` 不在提交内。
3. 历史未跟踪大目录仍不得进入提交。
4. `TASK-006*` 不在提交内。
5. 如果工作区仍有未跟踪历史目录，可以保留，但必须在交付说明中声明“不属于本任务，未纳入 commit”。

## 10. 证据文档

新建或更新：

`/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005F9_本地基线提交证据.md`

必须记录：

1. 提交前 HEAD。
2. 提交后 HEAD。
3. commit message。
4. staged 文件清单。
5. 排除文件清单。
6. 回归测试结果。
7. 真实 PostgreSQL 双 JUnit 结果引用。
8. `git show --stat --name-only HEAD` 摘要。
9. `git status --short` 摘要。
10. 结论。

## 11. 验收标准

□ 未使用 `git add .` 或 `git add -A`。  
□ staged 文件只包含白名单。  
□ `.pytest-postgresql-*.xml` 未提交。  
□ 历史未跟踪大目录未提交。  
□ `06_前端/**` 未提交。  
□ `02_源码/**` 未提交。  
□ `TASK-006*` 未提交。  
□ 定向 pytest、全量 pytest、unittest、py_compile 通过。  
□ 本地 commit 成功。  
□ 提交后 HEAD 已记录。  
□ TASK-005F9 证据文件已记录提交范围。  
□ 审计官复审通过前不得进入 TASK-005G、前端创建入口或 TASK-006。  

## 12. 交付说明要求

工程师交付时必须说明：

1. commit hash。
2. commit message。
3. staged 文件数量。
4. 排除的未跟踪目录。
5. `.pytest-postgresql-*.xml` 是否未提交。
6. 回归测试结果。
7. 真实 PostgreSQL 双 JUnit 结果。
8. `git show --stat --name-only HEAD` 摘要。
9. 工作区剩余未跟踪项说明。
10. 明确未进入 TASK-005G、前端创建入口或 TASK-006。
