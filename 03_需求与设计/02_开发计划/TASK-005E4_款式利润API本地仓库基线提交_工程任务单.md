# TASK-005E4 款式利润 API 本地仓库基线提交工程任务单

## 任务编号

TASK-005E4

## 任务名称

款式利润 API 本地仓库基线提交

## 任务目标

在 `TASK-005E3` 审计通过后，将 `TASK-005E~E3` 的款式利润 API、服务端来源采集器、权限审计修复、测试和任务文档纳入本地 git 稳定基线，避免后续前端联调或真实来源 adapter 开发时审计对象漂移。

## 审计来源

TASK-005E3 复审结论：通过。

已确认：

1. 详情接口已先执行 `style_profit:read` 动作权限，再查询 snapshot。
2. 无读权限用户访问存在 ID 和不存在 ID 均返回 `403 AUTH_FORBIDDEN`。
3. 存在性枚举风险已关闭。
4. API 定向 pytest：`34 passed, 1 warning`。
5. 全量 pytest：`596 passed, 9 skipped`。
6. unittest discover：`Ran 585 tests, OK (skipped=1)`。
7. py_compile 通过。

## 当前状态

- `TASK-005E1`：第 99 份审计不通过，已由 E2/E3 修复。
- `TASK-005E2`：有条件通过，4 个主阻断项已基本闭环。
- `TASK-005E3`：通过，详情存在性枚举风险已关闭。
- 本任务完成并通过审计后，才允许评估 `TASK-005F` 前端联调或真实来源 adapter 任务。
- `TASK-006` 继续阻塞。

## 严格边界

本任务只允许做本地白名单提交和证据整理。

禁止操作：

1. 禁止 `git add .`
2. 禁止 `git add -A`
3. 禁止 `git add --all`
4. 禁止修改业务代码。
5. 禁止修改前端。
6. 禁止修改 `.github`。
7. 禁止修改 `02_源码`。
8. 禁止修改 migrations。
9. 禁止新增或修改 `TASK-006*`。
10. 禁止 push。
11. 禁止配置 remote/origin。

## 允许纳入提交的后端文件白名单

只允许 stage 以下后端文件：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/main.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/style_profit.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/style_profit_api_source_collector.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/permissions.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/error_codes.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/permission_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/style_profit.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_api.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_api_permissions.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_api_audit.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_api_errors.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_api_postgresql.py`

## 允许纳入提交的文档文件白名单

只允许 stage 以下文档文件：

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005E_款式利润API权限与审计基线_工程任务单.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005E1_款式利润API权限审计基线实现_工程任务单.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005E2_款式利润API审计阻断整改_工程任务单.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005E3_款式利润详情接口鉴权前置整改_工程任务单.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005E4_款式利润API本地仓库基线提交_工程任务单.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005E4_款式利润API本地仓库基线提交证据.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/当前 sprint 任务清单.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/06_模块设计_款式利润报表.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/03_技术决策记录.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/架构师会话日志.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录/审计官会话日志.md`

如果工程师日志无本轮新增变化，不要强行 stage。

## 证据文件要求

创建证据文件：

`/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005E4_款式利润API本地仓库基线提交证据.md`

证据文件必须包含：

1. 当前分支。
2. 提交前 HEAD。
3. TASK-005E3 审计通过结论。
4. API 定向 pytest 结果。
5. 全量 pytest 结果。
6. unittest discover 结果。
7. py_compile 结果。
8. PostgreSQL 测试 skip 或非 skip 结果。
9. 禁改边界扫描结果。
10. `git status --short`。
11. `git diff --cached --name-only`。
12. 白名单校验结论。
13. 提交后 HEAD。
14. 明确声明：未 push、未配置 remote、未修改前端、未修改 `.github`、未修改 `02_源码`、未修改 migrations、未进入 TASK-006。

## 提交前验证命令

后端验证：

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service

.venv/bin/python -m pytest -q \
  tests/test_style_profit_api.py \
  tests/test_style_profit_api_permissions.py \
  tests/test_style_profit_api_audit.py \
  tests/test_style_profit_api_errors.py \
  tests/test_style_profit_api_postgresql.py

.venv/bin/python -m pytest -q
.venv/bin/python -m unittest discover
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
```

禁改扫描：

```bash
cd /Users/hh/Desktop/领意服装管理系统

git diff --name-only -- 06_前端 .github 02_源码
git diff --name-only -- 07_后端/lingyi_service/migrations
git diff --name-only -- '03_需求与设计/02_开发计划' | grep 'TASK-006' || true
git diff --cached --name-only
```

要求：

1. 前端、`.github`、`02_源码` 扫描无输出。
2. migrations 扫描无输出。
3. TASK-006 扫描无输出。
4. `git diff --cached --name-only` 只能出现白名单文件。

## 推荐提交方式

只允许精确 add，不允许批量 add。

提交信息：

```bash
git commit -m "feat: add style profit API permission audit baseline"
```

## 验收标准

- [ ] E~E3 API 文件和测试已纳入本地 git 跟踪。
- [ ] E~E4 任务文档已纳入本地 git 跟踪。
- [ ] E4 证据文件已创建。
- [ ] staged 文件全部属于白名单。
- [ ] API 定向 pytest 通过。
- [ ] 全量 pytest 通过。
- [ ] unittest discover 通过。
- [ ] py_compile 通过。
- [ ] PostgreSQL 测试结果已记录。
- [ ] 未修改前端。
- [ ] 未修改 `.github`。
- [ ] 未修改 `02_源码`。
- [ ] 未修改 migrations。
- [ ] 未进入 TASK-006。
- [ ] 未 push。
- [ ] 未配置 remote/origin。
- [ ] 本地 commit 已形成。

## 交付回报格式

```text
TASK-005E4 已完成。

提交信息：
- commit: [本次本地基线提交 SHA]
- message: feat: add style profit API permission audit baseline

验证结果：
- API 定向 pytest：[结果]
- 全量 pytest：[结果]
- unittest discover：[结果]
- py_compile：[结果]
- PostgreSQL 测试：[非 skip 结果或 skip 原因]
- 禁改扫描：[通过/不通过]
- staged 白名单检查：[通过/不通过]

证据文件：
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005E4_款式利润API本地仓库基线提交证据.md

确认：
- 未修改前端
- 未修改 .github
- 未修改 02_源码
- 未修改 migrations
- 未进入 TASK-006
- 未 push
- 未配置 remote/origin
```
