# TASK-005C4 利润模型本地仓库基线提交工程任务单

- 任务编号：TASK-005C4
- 模块：款式利润报表 / 本地仓库基线纳入
- 优先级：P0
- 版本：V1.0
- 更新时间：2026-04-14 07:21 CST
- 作者：技术架构师
- 审计来源：TASK-005C3 审计结论通过；审计建议 TASK-005C~C3 新增利润模型、服务、迁移和测试文件需纳入本地仓库基线/提交
- 前置依赖：TASK-005C3 已通过审计；ADR-083 生效
- 架构依据：`/03_需求与设计/01_架构设计/06_模块设计_款式利润报表.md` V0.8；`ADR-084`
- 任务边界：只做本地仓库白名单提交与证据记录；不得修改业务逻辑；不得进入 TASK-005D；不得进入 TASK-006；不得 push

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-005C4
模块：利润模型本地仓库基线提交
优先级：P0（交付基线）
════════════════════════════════════════════════════════════════════════════

【任务目标】
将 TASK-005C~C3 已通过审计的利润模型、schema、来源映射服务、迁移、测试和相关文档纳入本地 git 基线，形成可复验提交，避免 TASK-005D 开始后交付基线不完整。

【允许纳入提交的文件白名单】

后端利润模型与测试：
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/__init__.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/style_profit.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/style_profit.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/style_profit_source_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/versions/task_005c_create_style_profit_tables.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_models.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_source_mapping.py

任务单与架构文档：
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005C_利润模型迁移与来源映射设计_工程任务单.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005C1_利润来源映射审计字段与状态FailClosed整改_工程任务单.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005C2_利润来源默认不纳入与字段契约收口整改_工程任务单.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005C3_利润快照期间索引补齐_工程任务单.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005C4_利润模型本地仓库基线提交_工程任务单.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/当前 sprint 任务清单.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/06_模块设计_款式利润报表.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/03_技术决策记录.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/架构师会话日志.md

审计与工程日志：
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录/审计官会话日志.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md（仅当本轮已追加 TASK-005C4 执行记录时允许纳入）

证据文件：
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005C4_利润模型本地仓库基线提交证据.md

【禁止纳入提交】
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/**
- /Users/hh/Desktop/领意服装管理系统/.github/**
- /Users/hh/Desktop/领意服装管理系统/02_源码/**
- /Users/hh/Desktop/领意服装管理系统/00_交接与日志/**
- /Users/hh/Desktop/领意服装管理系统/01_需求与资料/**
- /Users/hh/Desktop/领意服装管理系统/03_环境与部署/**
- /Users/hh/Desktop/领意服装管理系统/04_测试与验收/**
- /Users/hh/Desktop/领意服装管理系统/05_交付物/**
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/main.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/**
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/style_profit_service.py
- 任意 TASK-005D / TASK-006 文件

【执行步骤】

## 1. 先跑验证

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest -q tests/test_style_profit_models.py tests/test_style_profit_source_mapping.py
.venv/bin/python -m pytest -q
.venv/bin/python -m unittest discover
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
```

## 2. 做禁改边界扫描

```bash
cd /Users/hh/Desktop/领意服装管理系统
git diff --name-only -- 06_前端 .github 02_源码
git diff --name-only -- 07_后端/lingyi_service/app/main.py 07_后端/lingyi_service/app/routers
```

要求：上述两个命令必须无输出。若有输出，停止，不得提交。

## 3. 创建证据文件

创建：
`/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005C4_利润模型本地仓库基线提交证据.md`

证据文件必须包含：
1. 当前分支。
2. 提交前 HEAD。
3. 允许纳入提交的文件清单。
4. 禁止纳入路径扫描结果。
5. 定向 pytest 结果。
6. 全量 pytest 结果。
7. unittest 结果。
8. py_compile 结果。
9. `git diff --cached --name-only` 结果。
10. 提交后 HEAD。
11. 明确写：未 push、未进入 TASK-005D、未进入 TASK-006。

## 4. 白名单 staged

禁止使用：
```bash
git add .
git add -A
git add --all
```

只能使用精确白名单路径执行 `git add -- <path>`。

推荐 staged 命令：

```bash
cd /Users/hh/Desktop/领意服装管理系统
git add -- \
  "07_后端/lingyi_service/app/models/__init__.py" \
  "07_后端/lingyi_service/app/models/style_profit.py" \
  "07_后端/lingyi_service/app/schemas/style_profit.py" \
  "07_后端/lingyi_service/app/services/style_profit_source_service.py" \
  "07_后端/lingyi_service/migrations/versions/task_005c_create_style_profit_tables.py" \
  "07_后端/lingyi_service/tests/test_style_profit_models.py" \
  "07_后端/lingyi_service/tests/test_style_profit_source_mapping.py" \
  "03_需求与设计/02_开发计划/TASK-005C_利润模型迁移与来源映射设计_工程任务单.md" \
  "03_需求与设计/02_开发计划/TASK-005C1_利润来源映射审计字段与状态FailClosed整改_工程任务单.md" \
  "03_需求与设计/02_开发计划/TASK-005C2_利润来源默认不纳入与字段契约收口整改_工程任务单.md" \
  "03_需求与设计/02_开发计划/TASK-005C3_利润快照期间索引补齐_工程任务单.md" \
  "03_需求与设计/02_开发计划/TASK-005C4_利润模型本地仓库基线提交_工程任务单.md" \
  "03_需求与设计/02_开发计划/TASK-005C4_利润模型本地仓库基线提交证据.md" \
  "03_需求与设计/02_开发计划/当前 sprint 任务清单.md" \
  "03_需求与设计/01_架构设计/06_模块设计_款式利润报表.md" \
  "03_需求与设计/01_架构设计/03_技术决策记录.md" \
  "03_需求与设计/01_架构设计/架构师会话日志.md" \
  "03_需求与设计/05_审计记录.md" \
  "03_需求与设计/05_审计记录/审计官会话日志.md"
```

如 `工程师会话日志.md` 已追加本轮执行记录，再单独 add：

```bash
git add -- "03_需求与设计/02_开发计划/工程师会话日志.md"
```

## 5. staged 白名单复核

执行：

```bash
git diff --cached --name-only | sort
git diff --cached --check
```

要求：
1. staged 文件只能在本任务白名单内。
2. 不得出现 `06_前端`、`.github`、`02_源码`、`app/main.py`、`app/routers`、`style_profit_service.py`。
3. `git diff --cached --check` 必须通过。

## 6. 本地提交

提交信息固定为：

```bash
git commit -m "feat: add style profit model source mapping baseline"
```

提交后记录：

```bash
git rev-parse --short HEAD
git status --short
```

要求：
1. 本任务只做本地 commit。
2. 不允许 push。
3. 不允许配置 remote。
4. 不允许进入 TASK-005D/TASK-006。

【验收标准】
□ TASK-005C~C3 利润模型、schema、来源映射服务、迁移、测试文件已纳入本地 git commit。
□ TASK-005C~C4 任务单、模块设计、ADR、Sprint 清单、架构师日志、审计记录已按白名单纳入提交。
□ 已输出 `TASK-005C4_利润模型本地仓库基线提交证据.md`。
□ 定向 pytest、全量 pytest、unittest、py_compile 通过。
□ staged 白名单检查通过。
□ 禁改边界扫描无输出。
□ 本地 commit message 为 `feat: add style profit model source mapping baseline`。
□ 未 push，未配置 remote，未进入 TASK-005D/TASK-006。

【预计工时】
0.25-0.5 天

════════════════════════════════════════════════════════════════════════════
