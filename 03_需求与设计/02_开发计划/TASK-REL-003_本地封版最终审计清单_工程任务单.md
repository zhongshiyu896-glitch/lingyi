# TASK-REL-003 本地封版最终审计清单_工程任务单

- 任务编号：TASK-REL-003
- 任务名称：本地封版最终审计清单
- 模块范围：发布专项 / 本地封版审计清单 / 下一阶段入口冻结
- 前置任务：TASK-REL-002 本地封版白名单基线提交
- 前置状态：TASK-REL-002 已完成本地基线提交与 docs-only 证据补提交
- 任务类型：只读审计 / 清单固化 / 非生产发布
- 执行日期：2026-04-15

## 一、基线锚点

本任务必须以以下两个 commit 作为审计锚点，不得自行改写口径：

1. 本地封版白名单基线提交：`c5273f81bde9f52ba2d18bf2d44f4c8377fff3af`
2. REL-002 docs-only 证据补提交 / 当前审计锚点：`64eaeb7fad0fa6c7c26ba4f25323d2402eedd367`

如执行时 `git rev-parse HEAD` 不是 `64eaeb7fad0fa6c7c26ba4f25323d2402eedd367`，必须在最终清单中明确记录实际 HEAD 与偏差，不得静默继续写“已闭环”。

## 二、任务目标

对 TASK-005 款式利润报表与 TASK-006 加工厂对账单的本地封版结果做最终只读审计清单固化，形成一份可交给下一阶段使用的本地封版总清单。

本任务只确认“本地封版与本地基线可审计”，不代表生产发布完成，不代表 GitHub 平台 required check 闭环，不代表 ERPNext 生产环境联调通过。

## 三、唯一允许输出

执行本任务时，只允许新增或修改以下最终审计/清单文档：

```text
/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-REL-003_本地封版最终审计清单.md
```

除上述文件外，不得修改任何其他文件。若发现必须修改其他文件，必须停止并提审，不得自行扩大范围。

## 四、禁止修改边界

以下路径一律禁止修改、暂存和提交：

```text
/Users/hh/Desktop/领意服装管理系统/06_前端/**
/Users/hh/Desktop/领意服装管理系统/07_后端/**
/Users/hh/Desktop/领意服装管理系统/.github/**
/Users/hh/Desktop/领意服装管理系统/02_源码/**
```

以下行为一律禁止：

1. 禁止 `push`。
2. 禁止配置或修改 `remote`。
3. 禁止创建 PR。
4. 禁止写入“生产发布完成”“已上线”“生产环境已验证”等发布语义。
5. 禁止开放款式利润快照创建入口。
6. 禁止新增或调用内部 worker run-once 前端入口。
7. 禁止新增 ERPNext `Purchase Invoice submit`、`Payment Entry`、`GL Entry` 能力。
8. 禁止提交或暂存 `.pytest-postgresql-*.xml`、`dist/`、`node_modules/`、`.pytest_cache/` 等运行产物。
9. 禁止使用 `git add .` 或 `git add -A`。

## 五、必须执行的只读核验命令

### 1. 仓库锚点核验

```bash
cd /Users/hh/Desktop/领意服装管理系统
git rev-parse HEAD
git show --stat --oneline --name-only c5273f81bde9f52ba2d18bf2d44f4c8377fff3af
git show --stat --oneline --name-only 64eaeb7fad0fa6c7c26ba4f25323d2402eedd367
git status --short
git diff --cached --name-only
git diff --cached --check
```

### 2. 禁改边界核验

```bash
cd /Users/hh/Desktop/领意服装管理系统
git diff --name-only -- '06_前端' '07_后端' '.github' '02_源码'
git status --short -- '06_前端' '07_后端' '.github' '02_源码'
```

说明：若 `git status --short` 命中历史未跟踪目录或历史脏改动，必须在最终清单中标注“历史遗留，未纳入本任务输出”，不得把它们写成 TASK-REL-003 新增改动。

### 3. 运行产物核验

```bash
cd /Users/hh/Desktop/领意服装管理系统
test ! -d '06_前端/lingyi-pc/dist' && echo 'dist absent' || echo 'dist exists'
test ! -d '07_后端/lingyi_service/.pytest_cache' && echo 'pytest_cache absent' || echo 'pytest_cache exists'
ls '07_后端/lingyi_service'/.pytest-postgresql-*.xml 2>/dev/null || echo 'postgresql junit xml absent'
```

### 4. 基线提交禁入路径核验

```bash
cd /Users/hh/Desktop/领意服装管理系统
git show --name-only --pretty=format: c5273f81bde9f52ba2d18bf2d44f4c8377fff3af | rg -n '^(\.github/|02_源码/|04_测试与验收/|05_交付物/|06_前端/lingyi-pc/(dist|node_modules|coverage)/|07_后端/lingyi_service/(\.pytest_cache|\.pytest-postgresql.*\.xml)|.*\.db$|.*\.sqlite$|.*\.log$|\.env)' || true
git show --name-only --pretty=format: 64eaeb7fad0fa6c7c26ba4f25323d2402eedd367 | rg -n '^(06_前端/|07_后端/|\.github/|02_源码/|.*\.pytest-postgresql.*\.xml|.*dist/|.*node_modules/)' || true
```

## 六、最终清单必须包含的内容

最终文档 `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-REL-003_本地封版最终审计清单.md` 至少包含以下章节：

### 1. 基线信息

必须列出：

- 审计执行时间。
- 当前 HEAD。
- 本地封版白名单基线提交：`c5273f81bde9f52ba2d18bf2d44f4c8377fff3af`。
- REL-002 docs-only 证据补提交：`64eaeb7fad0fa6c7c26ba4f25323d2402eedd367`。
- 是否 push：必须为否。
- 是否配置 remote：必须如实记录。
- 是否生产发布：必须为否。

### 2. 已封版项清单

必须至少列出：

1. TASK-005 款式利润报表：本地封版完成，仅只读前端，不开放创建快照入口。
2. TASK-006 加工厂对账单：本地封版审计通过，不代表生产 ERPNext 联调完成。
3. TASK-REL-001：运行产物清理与白名单提交前置治理完成。
4. TASK-REL-002：本地封版白名单基线提交完成，docs-only 证据补提交完成。

### 3. 生产前风险清单

必须至少列出：

1. 本地封版不等同生产发布。
2. ERPNext 生产联调与权限源复验未完成。
3. GitHub hosted runner / required check 未闭环。
4. `datetime.utcnow()` deprecation warnings 仍为历史风险。
5. failed/dead payable outbox 重建策略未实现，需独立任务设计。
6. 工作区仍可能存在历史未跟踪目录或运行产物，后续提交必须继续白名单暂存。

### 4. 下一阶段唯一入口冻结清单

必须冻结以下入口，不得从其他路径绕开：

1. 发布前治理入口：仅允许从 `TASK-REL-*` 继续推进。
2. failed/dead payable outbox 重建策略：必须新建独立任务，不得混入发布提交。
3. ERPNext 生产联调：必须新建生产专项任务，不得以本地封版替代。
4. 平台 required check：必须新建平台专项任务，不得在本地证据中声称完成。
5. 环境清理：`datetime.utcnow()` 等 deprecation 清理必须独立任务推进。

### 5. 禁止语义声明

必须逐条声明：

- 本清单不是生产发布单。
- 本清单不是上线审批单。
- 本清单不是 ERPNext 生产联调通过证明。
- 本清单不是 GitHub required check 闭环证明。
- TASK-005 / TASK-006 的完成语义仅限本地封版。

## 七、提交与暂存规则

如需要提交 TASK-REL-003 最终清单，必须遵守：

1. 只允许暂存：

```text
/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-REL-003_本地封版最终审计清单.md
```

2. 禁止暂存本任务单以外的任何新变更，除非另有审计指令。
3. 禁止使用 `git add .` / `git add -A`。
4. 提交前必须执行并通过：

```bash
git diff --cached --name-only
git diff --cached --check
```

5. 若提交，建议 commit message：

```text
docs: add local sealed closeout checklist
```

6. 不 push，不创建 PR。

## 八、验收标准

1. 最终清单文档存在且路径正确。
2. 最终清单包含基线信息、已封版项、生产前风险、下一阶段唯一入口冻结清单、禁止语义声明。
3. 未修改 `06_前端/**`、`07_后端/**`、`.github/**`、`02_源码/**`。
4. 未新增运行产物、缓存、Junit XML、数据库文件、环境变量文件。
5. 未把本地封版写成生产发布。
6. 未声明 GitHub required check 已闭环。
7. 未声明 ERPNext 生产联调已通过。
8. 如有历史未跟踪目录，仅在最终清单中如实记录，不纳入提交。

## 九、完成后回报格式

```text
TASK-REL-003 已完成。
结论：建议 / 不建议 将 TASK-005 与 TASK-006 作为本地封版基线进入下一阶段发布前治理。
生产发布状态：未发布。
GitHub required check 状态：未闭环。
ERPNext 生产联调状态：未完成。
输出文件：/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-REL-003_本地封版最终审计清单.md
```
