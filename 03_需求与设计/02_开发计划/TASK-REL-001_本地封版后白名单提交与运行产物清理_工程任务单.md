# TASK-REL-001 本地封版后白名单提交与运行产物清理_工程任务单

- 任务编号：TASK-REL-001
- 任务名称：本地封版后白名单提交与运行产物清理
- 模块：发布专项 / 本地基线治理
- 优先级：P0
- 前置依赖：TASK-005 本地封版完成、TASK-006 本地封版完成
- 更新时间：2026-04-15 22:55
- 作者：技术架构师

════════════════════════════════════════════════════════════
【任务目标】
在 TASK-005、TASK-006 本地封版后，固定本地仓库基线，清理或隔离运行产物，并通过白名单暂存方式避免历史 diff、缓存、构建产物、测试报告被误提交。

【重要边界】
1. 本任务只做本地仓库基线治理，不代表生产发布完成。
2. 本任务不得配置 remote，不得 push，不得创建 PR，不得声明 GitHub required check 已闭环。
3. 本任务不得使用 `git add .`、`git add -A`、`git clean -fd`、`git reset --hard`、`git checkout --`。
4. 本任务不得删除历史业务文件；如需清理，只允许处理本任务明确列出的运行产物。
5. 任何提交必须通过白名单路径逐个暂存。

【涉及文件】
新建：
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-REL-001_本地封版后白名单提交与运行产物清理_交付证据.md

可能修改：
- /Users/hh/Desktop/领意服装管理系统/.gitignore（仅当需要补充运行产物忽略规则时）
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/当前 sprint 任务清单.md（记录 REL-001 状态）
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/架构师会话日志.md（记录架构师/工程交付状态）

只允许按白名单纳入的候选范围：
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/**
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/factory_statement*.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/factory_statement*.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/factory_statement*.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/factory_statement*.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/error_codes.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/permissions.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/permission_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/main.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/versions/*factory_statement*.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_factory_statement*.py
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/factory_statement.ts
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/factory_statement/**
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/utils/factoryStatementExport.ts
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/router/index.ts
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/stores/permission.ts
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/*factory-statement*.mjs
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/package.json
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/package-lock.json

【禁止提交清单】
以下文件或目录不得进入 staged，也不得进入 commit：
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/dist/
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/node_modules/
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/.pytest_cache/
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/.pytest-postgresql-*.xml
- 任意 __pycache__/
- 任意 .DS_Store
- 任意 .env、*.pem、*.key、包含密码/Token/DSN 的文件
- 02_源码/**，除非另有架构师单独任务单明确放行
- .github/**，除非另有平台门禁专项任务单明确放行
- 与 TASK-005/TASK-006 本地封版无关的历史草稿、临时探针、临时快照目录

【运行产物处理规则】
1. 先列出运行产物，不要直接删除。
2. 允许清理的运行产物仅限：
   - /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/dist/
   - /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/.pytest_cache/
   - /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/.pytest-postgresql-subcontract-settlement.xml
   - /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/.pytest-postgresql-style-profit-subcontract.xml
3. node_modules 默认只禁止提交，不要求删除；如要删除，必须在交付证据中说明原因。
4. 如新增或修改 .gitignore，只允许加入运行产物忽略规则，不得顺带忽略业务源码或文档目录。

【执行步骤】
1. 进入项目根目录：
   `cd /Users/hh/Desktop/领意服装管理系统`

2. 生成工作区盘点：
   `git status --short`
   `git diff --name-only`
   `git ls-files --others --exclude-standard`
   `find . -name '.pytest_cache' -o -name '.pytest-postgresql-*.xml' -o -name 'dist' -o -name 'node_modules'`

3. 生成候选白名单：
   - 将候选文件按 03_需求与设计、07_后端、06_前端 分组列出。
   - 标注每个文件对应 TASK-005、TASK-006、REL-001 或历史遗留。
   - 历史遗留不得默认纳入。

4. 清理或隔离运行产物：
   - 仅处理【运行产物处理规则】列出的路径。
   - 清理前后都要记录 `git status --short`。
   - 如不清理，只要确认未 staged，也可以通过。

5. 白名单暂存：
   - 只能使用 `git add -- <精确文件路径>`。
   - 禁止 `git add .`。
   - 禁止 `git add -A`。
   - 禁止用通配符一次性纳入大目录。

6. 暂存后检查：
   `git diff --cached --name-only`
   `git diff --cached --stat`
   `git status --short`

7. 禁止项扫描：
   - staged 中不得出现 dist、node_modules、.pytest_cache、.pytest-postgresql-*.xml。
   - staged 中不得出现 .env、密码、Token、DSN。
   - staged 中不得出现未放行的 02_源码/** 或 .github/**。

8. 必跑验证：
   后端：
   `cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service && .venv/bin/python -m pytest -q tests/test_factory_statement*.py`
   `cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service && .venv/bin/python -m py_compile $(find app tests -name '*.py' -print)`

   前端：
   `cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc && npm run verify`
   `cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc && npm audit --audit-level=high`
   `cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc && npm run test:factory-statement-contracts`
   `cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc && npm run test:style-profit-contracts`

9. 如执行 commit，提交信息建议：
   `chore: baseline local closeout artifacts`

10. 输出交付证据文件：
   `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-REL-001_本地封版后白名单提交与运行产物清理_交付证据.md`

【交付证据模板】
```markdown
# TASK-REL-001 本地封版后白名单提交与运行产物清理_交付证据

- 执行人：工程师
- 执行时间：YYYY-MM-DD HH:MM
- 当前 HEAD：<commit 或 未提交>
- 是否提交：是/否
- 提交 SHA：<如有>
- 结论：通过/需复审

## 1. 工作区盘点
- git status --short：<摘要>
- git diff --name-only：<摘要>
- untracked 文件分组：<摘要>

## 2. 运行产物处理
- dist/：已清理/未清理但未暂存
- .pytest_cache/：已清理/未清理但未暂存
- .pytest-postgresql-*.xml：已清理/未清理但未暂存
- node_modules/：未暂存/已说明处理方式

## 3. 暂存白名单
列出所有 staged 文件，每行一个路径。

## 4. 禁止项扫描结果
- dist：未暂存
- node_modules：未暂存
- .pytest_cache：未暂存
- .pytest-postgresql-*.xml：未暂存
- secret/env/token/dsn：未发现
- 02_源码：未暂存/如有说明
- .github：未暂存/如有说明

## 5. 验证结果
- 后端 factory statement pytest：通过/失败，结果摘要
- 后端 py_compile：通过/失败
- 前端 npm run verify：通过/失败
- 前端 npm audit：通过/失败
- factory-statement contracts：通过/失败，scenarios=X
- style-profit contracts：通过/失败，scenarios=X

## 6. 本任务不包含
- 不包含生产发布
- 不包含 ERPNext 生产联调
- 不包含 GitHub required check
- 不包含 push/PR

## 7. 遗留风险
1. <如有>
```

【验收标准】
□ 已输出完整工作区盘点，能看清 tracked diff、untracked 文件和运行产物。
□ staged 文件清单全部来自白名单路径。
□ staged 文件中不包含 dist、node_modules、.pytest_cache、.pytest-postgresql-*.xml。
□ staged 文件中不包含 .env、密码、Token、DSN、私钥。
□ 未使用 `git add .`、`git add -A`、`git clean -fd`、`git reset --hard`、`git checkout --`。
□ 后端 factory statement 定向测试通过。
□ 后端 py_compile 通过。
□ 前端 verify、audit、factory-statement contracts、style-profit contracts 通过。
□ 交付证据文件已写入指定路径。
□ 如已 commit，证据中写明 commit SHA；如未 commit，证据中明确“未提交”。
□ 证据明确声明：本任务不代表生产发布、不代表平台 required check 闭环。

【审计关注点】
1. 是否误提交运行产物。
2. 是否误提交历史未跟踪文件。
3. 是否误提交 02_源码、.github 或无关 TASK 文件。
4. 是否误将本地封版描述为生产发布。
5. 是否使用了非白名单暂存命令。
6. 是否遗漏 TASK-006 本地封版关键文件。

【预计工时】
0.5-1 天

════════════════════════════════════════════════════════════
