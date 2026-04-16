# REL-004D 平台管理员待办证据模板 工程任务单

- 任务编号：REL-004D
- 模块：平台 CI / Required Check 闭环
- 优先级：P0
- 版本：V1.0
- 更新时间：2026-04-16 CST
- 作者：Codex
- 前置依赖：REL-004C 审计通过，本地基线提交 `1818d971ef7062562845ff758b21d057d61ff244`
- 当前结论：仅准备平台管理员待办与证据模板，不执行 push，不配置 remote，不创建 PR，不宣称平台闭环

## 1. 任务目标

输出一份可交给仓库管理员 / DevOps 管理员执行的平台闭环待办证据模板，覆盖 GitHub Secret、remote / push、Hosted Runner、Required Check、artifact / JUnit、敏感信息扫描和最终审计回填字段。

## 2. 允许范围

1. 新增 REL-004D 管理员待办证据模板文档。
2. 新增 REL-004D 工程任务单。
3. 仅修改 `03_需求与设计/**` 文档。

## 3. 禁止范围

1. 禁止修改 `06_前端/**`。
2. 禁止修改 `07_后端/**`。
3. 禁止修改 `.github/**`。
4. 禁止修改 `02_源码/**`。
5. 禁止修改数据库迁移文件。
6. 禁止执行 `git push`。
7. 禁止配置或修改 `remote`。
8. 禁止创建 PR。
9. 禁止写入 GitHub token、密码、DSN、cookie、authorization 或 secret 值。
10. 禁止把模板完成写成 Hosted Runner / Required Check 已平台闭环。
11. 禁止宣称生产发布完成。

## 4. 必须输出

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/REL-004D_平台管理员待办证据模板.md`

## 5. 模板必须包含

1. 本地基线 commit：`1818d971ef7062562845ff758b21d057d61ff244`。
2. GitHub Secret 待配置项：`LINGYI_CI_POSTGRES_PASSWORD`。
3. remote / push 非强推流程。
4. 四个 Hosted Runner required check：
   - `Frontend Verify Hard Gate / lingyi-pc-verify`
   - `Backend Test Hard Gate / lingyi-service-test`
   - `Backend PostgreSQL Hard Gate / postgresql-non-skip-gate`
   - `Docs Boundary Gate / docs-boundary-check`
5. 每个 workflow 的 run URL、commit SHA、runner、artifact、结论字段。
6. PostgreSQL non-skip JUnit 四项指标：`tests/skipped/failures/errors`。
7. Branch protection / Ruleset 配置字段。
8. 敏感信息扫描字段。
9. 管理员回报格式。
10. 失败处理分支。
11. 明确“模板未回填不等于平台闭环”。

## 6. 验证命令

```bash
cd /Users/hh/Desktop/领意服装管理系统

test -f '03_需求与设计/02_开发计划/REL-004D_平台管理员待办证据模板.md'
test -f '03_需求与设计/02_开发计划/REL-004D_平台管理员待办证据模板_工程任务单.md'

git rev-parse HEAD
git diff --name-only -- '06_前端' '07_后端' '.github' '02_源码'
git diff --cached --name-only
git diff --check -- '03_需求与设计/02_开发计划/REL-004D_平台管理员待办证据模板.md' '03_需求与设计/02_开发计划/REL-004D_平台管理员待办证据模板_工程任务单.md'
```

## 7. 验收标准

1. REL-004D 模板文档存在。
2. REL-004D 工程任务单存在。
3. 模板覆盖 GitHub Secret、remote / push、Hosted Runner、Required Check、artifact、JUnit、敏感扫描和 branch protection / ruleset。
4. 模板不含真实凭据。
5. 未修改前端、后端、`.github`、`02_源码`。
6. 未暂存、未提交、未 push。
7. 未宣称平台闭环或生产发布完成。

## 8. 交付回报格式

```text
REL-004D 执行完成。
结论：待审计

已输出：
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/REL-004D_平台管理员待办证据模板.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/REL-004D_平台管理员待办证据模板_工程任务单.md

本次只输出文档模板。
未修改前端/后端/.github/02_源码。
未暂存、未提交、未 push。
Hosted Runner / branch protection required checks：未平台闭环。
```
