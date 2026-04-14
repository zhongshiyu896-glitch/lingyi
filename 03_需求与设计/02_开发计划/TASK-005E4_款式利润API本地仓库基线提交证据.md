# TASK-005E4 款式利润 API 本地仓库基线提交证据

- 任务编号：TASK-005E4
- 执行时间：2026-04-14
- 当前分支：`main`
- 提交前 HEAD：`758d003`
- TASK-005E3 审计结论：通过（详情接口鉴权前置，存在性枚举风险关闭）

## 验证结果

1. API 定向 pytest
- 命令：
  ```bash
  .venv/bin/python -m pytest -q tests/test_style_profit_api.py tests/test_style_profit_api_permissions.py tests/test_style_profit_api_audit.py tests/test_style_profit_api_errors.py tests/test_style_profit_api_postgresql.py
  ```
- 结果：`34 passed, 4 skipped, 1 warning`
- PostgreSQL skip 原因：`POSTGRES_TEST_DSN` 未设置，命中安全门禁后跳过 destructive 集成测试。

2. 全量 pytest
- 命令：` .venv/bin/python -m pytest -q `
- 结果：`596 passed, 9 skipped`

3. unittest discover
- 命令：` .venv/bin/python -m unittest discover `
- 结果：`Ran 585 tests, OK (skipped=1)`

4. py_compile
- 命令：` .venv/bin/python -m py_compile $(find app tests -name '*.py' -print) `
- 结果：通过

## 禁改边界扫描

1. `git diff --name-only -- 06_前端 .github 02_源码`
- 结果：无输出（通过）

2. `git diff --name-only -- 07_后端/lingyi_service/migrations`
- 结果：无输出（通过）

3. `git diff --name-only -- '03_需求与设计/02_开发计划' | grep 'TASK-006' || true`
- 结果：无输出（通过）

## 提交前工作区状态

`git status --short`：存在本任务相关改动与其他目录未跟踪内容，按白名单精确暂存，不使用 `git add .`。

## 白名单暂存清单

`git diff --cached --name-only`：

```text
03_需求与设计/01_架构设计/03_技术决策记录.md
03_需求与设计/01_架构设计/06_模块设计_款式利润报表.md
03_需求与设计/01_架构设计/架构师会话日志.md
03_需求与设计/02_开发计划/TASK-005E1_款式利润API权限审计基线实现_工程任务单.md
03_需求与设计/02_开发计划/TASK-005E2_款式利润API审计阻断整改_工程任务单.md
03_需求与设计/02_开发计划/TASK-005E3_款式利润详情接口鉴权前置整改_工程任务单.md
03_需求与设计/02_开发计划/TASK-005E4_款式利润API本地仓库基线提交_工程任务单.md
03_需求与设计/02_开发计划/TASK-005E4_款式利润API本地仓库基线提交证据.md
03_需求与设计/02_开发计划/TASK-005E_款式利润API权限与审计基线_工程任务单.md
03_需求与设计/02_开发计划/当前 sprint 任务清单.md
03_需求与设计/05_审计记录.md
03_需求与设计/05_审计记录/审计官会话日志.md
07_后端/lingyi_service/app/core/error_codes.py
07_后端/lingyi_service/app/core/permissions.py
07_后端/lingyi_service/app/main.py
07_后端/lingyi_service/app/routers/style_profit.py
07_后端/lingyi_service/app/schemas/style_profit.py
07_后端/lingyi_service/app/services/permission_service.py
07_后端/lingyi_service/app/services/style_profit_api_source_collector.py
07_后端/lingyi_service/tests/test_style_profit_api.py
07_后端/lingyi_service/tests/test_style_profit_api_audit.py
07_后端/lingyi_service/tests/test_style_profit_api_errors.py
07_后端/lingyi_service/tests/test_style_profit_api_permissions.py
07_后端/lingyi_service/tests/test_style_profit_api_postgresql.py
```

白名单校验结论：通过。
- 未出现 `06_前端/**`
- 未出现 `.github/**`
- 未出现 `02_源码/**`
- 未出现 `07_后端/lingyi_service/migrations/**`
- 未出现 `TASK-006*`

## 提交信息

- 提交后 HEAD：`见本次提交 SHA（与回报 commit 字段一致）`
- 是否 push：否
- 是否配置 remote/origin：否

## 范围声明

- 未修改前端
- 未修改 `.github`
- 未修改 `02_源码`
- 未修改 migrations
- 未进入 TASK-006
