# TASK-005D4 利润快照服务本地仓库基线提交工程任务单

- 任务编号：TASK-005D4
- 模块：款式利润报表 / 利润快照服务本地仓库基线提交
- 优先级：P0
- 版本：V1.0
- 更新时间：2026-04-14 11:08 CST
- 作者：技术架构师
- 审计来源：审计意见书第 95 份，TASK-005D3 通过；审计建议进入 TASK-005E/API 前先做本地基线提交
- 前置依赖：TASK-005D~D3 审计链路完成，TASK-005D3 已通过；TASK-005E/API 层未放行；TASK-006 继续阻塞
- 架构依据：`/03_需求与设计/01_架构设计/06_模块设计_款式利润报表.md` V1.3；`ADR-089`
- 任务边界：只做本地白名单提交和证据记录；不修改业务逻辑；不注册 API；不改前端；不新增迁移；不进入 TASK-005E/TASK-006；不 push；不配置 remote

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-005D4
模块：利润快照服务本地仓库基线提交
优先级：P0（进入 API 前基线门禁）
════════════════════════════════════════════════════════════════════════════

【任务目标】
将 TASK-005D~D3 已通过审计的利润快照服务、DTO、来源映射调整、测试、任务文档、审计记录和证据文件按白名单纳入本地 git commit，形成进入 TASK-005E/API 前的稳定审计基线。

【禁止事项】
1. 禁止 `git add .`。
2. 禁止 `git add -A`。
3. 禁止 `git add --all`。
4. 禁止 stage `06_前端/**`。
5. 禁止 stage `.github/**`。
6. 禁止 stage `02_源码/**`。
7. 禁止 stage `07_后端/lingyi_service/app/main.py`。
8. 禁止 stage `07_后端/lingyi_service/app/routers/**`。
9. 禁止 stage `07_后端/lingyi_service/migrations/**`。
10. 禁止新增或修改任何 TASK-005E 文件。
11. 禁止新增或修改任何 TASK-006 文件。
12. 禁止 push。
13. 禁止配置 remote/origin。
14. 禁止修改业务代码来“顺手优化”；D4 只做验证、证据和提交。

【必须使用白名单 git add】
只能使用以下格式逐项添加：

```bash
git add -- <精确文件路径>
```

【允许纳入提交的后端文件】
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/style_profit.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/style_profit_source_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/style_profit_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_source_mapping.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_snapshot_calculation.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_snapshot_idempotency.py

【允许纳入提交的文档文件】
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005D_利润快照计算服务_工程任务单.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005D1_利润快照计算服务审计整改_工程任务单.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005D1_利润快照归属校验与事务兜底整改_工程任务单.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005D2_利润实际成本归属与事务兜底整改_工程任务单.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005D3_利润实际成本关键归属字段FailClosed整改_工程任务单.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005D4_利润快照服务本地仓库基线提交_工程任务单.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005D4_利润快照服务本地仓库基线提交证据.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/当前 sprint 任务清单.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/06_模块设计_款式利润报表.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/03_技术决策记录.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/架构师会话日志.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录/审计官会话日志.md

说明：两个 TASK-005D1 任务单均允许纳入提交。若工程师判断 `TASK-005D1_利润快照归属校验与事务兜底整改_工程任务单.md` 为历史命名稿，不得直接删除；必须在证据文件中说明保留/废弃判断，并交审计官确认。

【必须创建证据文件】
创建：
/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005D4_利润快照服务本地仓库基线提交证据.md

证据文件必须包含：
1. 当前分支。
2. 提交前 HEAD。
3. TASK-005D3 审计通过依据：审计意见书第 95 份。
4. 定向 pytest 结果。
5. 全量 pytest 结果。
6. unittest discover 结果。
7. py_compile 结果。
8. 禁改扫描结果。
9. `git status --short` 摘要。
10. `git diff --cached --name-only` 暂存文件清单。
11. 白名单核对结论。
12. 提交后 HEAD。
13. 明确声明：未 push，未配置 remote，未进入 TASK-005E，未进入 TASK-006。

【提交前验证命令】

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest -q tests/test_style_profit_models.py tests/test_style_profit_source_mapping.py tests/test_style_profit_service.py tests/test_style_profit_snapshot_calculation.py tests/test_style_profit_snapshot_idempotency.py
.venv/bin/python -m pytest -q
.venv/bin/python -m unittest discover
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
```

【提交前禁改扫描】

```bash
cd /Users/hh/Desktop/领意服装管理系统
git diff --name-only -- 06_前端 .github 02_源码
git diff --name-only -- 07_后端/lingyi_service/app/main.py 07_后端/lingyi_service/app/routers 07_后端/lingyi_service/migrations
git diff --name-only -- '03_需求与设计/02_开发计划' | grep 'TASK-005E' || true
git diff --name-only -- '03_需求与设计/02_开发计划' | grep 'TASK-006' || true
git diff --cached --name-only
```

要求：
1. 前两个禁改扫描必须无输出。
2. `TASK-005E` 扫描不得出现任何文件。
3. `TASK-006` 扫描不得出现任何文件。
4. `git diff --cached --name-only` 必须全部落在 D4 白名单内。

【本地提交】

提交信息固定为：

```bash
git commit -m "feat: add style profit snapshot service baseline"
```

【提交后验证】

```bash
git status --short
git log --oneline -3
git show --name-only --stat HEAD -- 06_前端 .github 02_源码 07_后端/lingyi_service/app/main.py 07_后端/lingyi_service/app/routers 07_后端/lingyi_service/migrations
```

要求：
1. `git show ... 禁止路径` 不得显示业务文件变更。
2. 工作区允许保留既有未跟踪资料目录，但本次 commit 不得包含它们。
3. 不得 push。
4. 不得配置 remote。

【验收标准】
□ 本地 commit 已形成。
□ commit message 为 `feat: add style profit snapshot service baseline`。
□ commit 内容只包含 D4 白名单文件。
□ TASK-005D~D3 的利润服务、DTO、来源映射调整和测试文件已纳入 commit。
□ TASK-005D~D4 任务文档、模块设计、ADR、Sprint 清单、架构师日志、审计记录、工程师日志和证据文件已纳入 commit。
□ 定向 pytest、全量 pytest、unittest、py_compile 全部通过。
□ 禁改扫描通过。
□ 未 push，未配置 remote。
□ 未注册 API，未修改前端，未新增迁移，未进入 TASK-005E/TASK-006。

【预计工时】
0.5 天

════════════════════════════════════════════════════════════════════════════
