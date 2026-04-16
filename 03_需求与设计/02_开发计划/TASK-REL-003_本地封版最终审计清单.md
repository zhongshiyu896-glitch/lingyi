# TASK-REL-003 本地封版最终审计清单

## 1. 基线信息
- 审计执行时间：2026-04-15 23:51:07 CST
- 当前 HEAD：`64eaeb7fad0fa6c7c26ba4f25323d2402eedd367`
- 本地封版白名单基线提交：`c5273f81bde9f52ba2d18bf2d44f4c8377fff3af`
- REL-002 docs-only 证据补提交：`64eaeb7fad0fa6c7c26ba4f25323d2402eedd367`
- 锚点一致性：当前 HEAD 与任务单要求一致，无偏差
- 是否 push：否（本任务未执行 push）
- 是否配置 remote：否（`git remote -v` 空输出）
- 是否生产发布：否（本任务仅本地封版审计）

## 2. 已封版项清单
1. TASK-005 款式利润报表：本地封版完成（仅本地语义），保持前端只读契约门禁，不开放创建快照入口。
2. TASK-006 加工厂对账单：本地封版审计通过（仅本地语义），不代表 ERPNext 生产联调完成。
3. TASK-REL-001：运行产物清理与白名单提交前置治理完成。
4. TASK-REL-002：本地封版白名单基线提交完成，docs-only 证据补提交完成。

## 3. 只读核验结果
### 3.1 仓库锚点与提交核验
- `git rev-parse HEAD`：`64eaeb7fad0fa6c7c26ba4f25323d2402eedd367`
- `git show --shortstat --oneline c5273f81...`：`123 files changed, 38111 insertions(+), 19 deletions(-)`
- `git show --shortstat --oneline 64eaeb7f...`：`2 files changed, 40 insertions(+)`
- `git diff --cached --name-only`：空
- `git diff --cached --check`：空

### 3.2 禁改边界核验
- `git diff --name-only -- '06_前端' '07_后端' '.github' '02_源码'`：空
- `git status --short -- '06_前端' '07_后端' '.github' '02_源码'`：
  - `?? 02_源码/`
  - `?? 07_后端/lingyi_service/tools/`
- 判定：上述为历史未跟踪目录，不属于 TASK-REL-003 新增改动，未纳入本任务输出。

### 3.3 运行产物核验
- `06_前端/lingyi-pc/dist`：`dist absent`
- `07_后端/lingyi_service/.pytest_cache`：`pytest_cache absent`
- `.pytest-postgresql-*.xml`：`postgresql junit xml absent`

### 3.4 基线提交禁入路径核验
- 对 `c5273f81...` 扫描禁入路径：无命中
- 对 `64eaeb7f...` 扫描 `06_前端/|07_后端/|.github/|02_源码/|...`：无命中

## 4. 生产前风险清单
1. 本地封版不等同生产发布。
2. ERPNext 生产联调与权限源复验未完成。
3. GitHub hosted runner / required check 未闭环。
4. `datetime.utcnow()` deprecation warnings 仍为历史风险。
5. failed/dead payable outbox 重建策略未实现，需独立任务设计。
6. 工作区仍可能存在历史未跟踪目录或运行产物，后续提交必须继续白名单暂存。

## 5. 下一阶段唯一入口冻结清单
1. 发布前治理入口：仅允许从 `TASK-REL-*` 继续推进。
2. failed/dead payable outbox 重建策略：必须新建独立任务，不得混入发布提交。
3. ERPNext 生产联调：必须新建生产专项任务，不得以本地封版替代。
4. 平台 required check：必须新建平台专项任务，不得在本地证据中声称完成。
5. 环境清理：`datetime.utcnow()` 等 deprecation 清理必须独立任务推进。

## 6. 禁止语义声明
- 本清单不是生产发布单。
- 本清单不是上线审批单。
- 本清单不是 ERPNext 生产联调通过证明。
- 本清单不是 GitHub required check 闭环证明。
- TASK-005 / TASK-006 的完成语义仅限本地封版。

## 7. 结论
结论：**建议**将 TASK-005 与 TASK-006 作为本地封版基线进入下一阶段发布前治理。

边界说明：
- 生产发布状态：未发布。
- GitHub required check 状态：未闭环。
- ERPNext 生产联调状态：未完成。
