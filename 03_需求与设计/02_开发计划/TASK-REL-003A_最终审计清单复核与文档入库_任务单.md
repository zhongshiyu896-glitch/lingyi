# TASK-REL-003A 最终审计清单复核与文档入库_任务单

- 任务编号：TASK-REL-003A
- 任务名称：最终审计清单复核与文档入库
- 模块：发布专项 / 本地封版收口
- 优先级：P0
- 前置依赖：TASK-REL-002 已通过，TASK-REL-003 最终审计清单已生成
- 更新时间：2026-04-16 00:18
- 作者：技术架构师

════════════════════════════════════════════════════════════
【任务目标】
对 `TASK-REL-003_本地封版最终审计清单.md` 做一次最终复核；复核通过后，将 REL-003 任务单、最终审计清单和必要日志以 docs-only 方式纳入本地仓库基线。

【当前锚点】
- 当前已知 HEAD：64eaeb7fad0fa6c7c26ba4f25323d2402eedd367
- REL-002 基线提交：c5273f81bde9f52ba2d18bf2d44f4c8377fff3af
- REL-002 证据补提交：64eaeb7fad0fa6c7c26ba4f25323d2402eedd367

【待复核文件】
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-REL-003_本地封版最终审计清单_工程任务单.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-REL-003_本地封版最终审计清单.md

【允许修改 / 提交文件白名单】
仅允许 docs-only 文件：
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-REL-003_本地封版最终审计清单_工程任务单.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-REL-003_本地封版最终审计清单.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-REL-003A_最终审计清单复核与文档入库_任务单.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md（如需记录本任务）
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/架构师会话日志.md（如需记录架构任务）
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录.md（仅审计官复核时允许）
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录/审计官会话日志.md（仅审计官复核时允许）

【禁止修改 / 禁止提交】
- /Users/hh/Desktop/领意服装管理系统/06_前端/**
- /Users/hh/Desktop/领意服装管理系统/07_后端/**
- /Users/hh/Desktop/领意服装管理系统/.github/**
- /Users/hh/Desktop/领意服装管理系统/02_源码/**
- dist/
- node_modules/
- .pytest_cache/
- .pytest-postgresql-*.xml
- 任意 .env、Token、DSN、私钥、密码文件

【复核内容】
1. 确认最终审计清单明确写明：
   - TASK-005：本地封版完成。
   - TASK-006：本地封版完成。
   - TASK-REL-001：通过。
   - TASK-REL-002：通过。
   - 生产发布：未完成。
   - GitHub required check：未闭环。
   - ERPNext 生产联调：未完成。

2. 确认最终审计清单不得出现以下误导语义：
   - “生产发布完成”
   - “已上线”
   - “GitHub required check 已闭环”
   - “ERPNext 生产联调已完成”
   - “可直接生产使用”

3. 确认最终审计清单必须包含剩余风险：
   - 当前仅为本地封版，不等于生产发布。
   - 平台 required check 未闭环。
   - ERPNext 生产联调未完成。
   - `datetime.utcnow()` warnings 仍为技术债。
   - failed/dead payable outbox 重建策略未实现。
   - 工作区仍有历史未跟踪目录，后续提交必须继续白名单暂存。

4. 确认本任务没有触碰前端、后端、`.github`、`02_源码`。

【必须执行命令】
在项目根目录执行：

```bash
cd /Users/hh/Desktop/领意服装管理系统

git rev-parse HEAD
git status --short
git diff --name-only -- 06_前端 07_后端 .github 02_源码
git diff --cached --name-only
git diff --cached --check
rg -n "生产发布完成|已上线|required check 已闭环|ERPNext 生产联调已完成|可直接生产使用" 03_需求与设计/02_开发计划/TASK-REL-003_本地封版最终审计清单.md
```

说明：最后一条如果只命中“禁止语义声明 / 本清单不是……”段落，可以判定为说明性命中；如命中结论段，则必须修正。

【暂存规则】
只允许逐文件暂存：

```bash
git add -- 03_需求与设计/02_开发计划/TASK-REL-003_本地封版最终审计清单_工程任务单.md
git add -- 03_需求与设计/02_开发计划/TASK-REL-003_本地封版最终审计清单.md
git add -- 03_需求与设计/02_开发计划/TASK-REL-003A_最终审计清单复核与文档入库_任务单.md
```

如审计官已追加审计记录，再逐文件暂存：

```bash
git add -- 03_需求与设计/05_审计记录.md
git add -- 03_需求与设计/05_审计记录/审计官会话日志.md
```

禁止：
```bash
git add .
git add -A
git clean -fd
git reset --hard
git checkout -- <path>
```

【提交前回显】
提交前必须回显并等待确认：

```bash
git diff --cached --name-only
git diff --cached --check
git status --short
```

【建议提交信息】
```text
docs: add REL-003 final closeout checklist
```

【验收标准】
□ REL-003 最终审计清单已复核通过。
□ 清单明确 TASK-005、TASK-006、REL-001、REL-002 状态。
□ 清单明确生产发布未完成、GitHub required check 未闭环、ERPNext 生产联调未完成。
□ 未修改前端、后端、`.github`、`02_源码`。
□ 未提交运行产物、缓存、JUnit XML、node_modules、dist。
□ 暂存清单全部为 docs-only 白名单文件。
□ `git diff --cached --check` 为空输出。
□ 如 commit，记录 commit SHA。
□ 不 push、不配置 remote、不创建 PR。

【完成后回复格式】
```text
TASK-REL-003A 执行完成。
结论：通过 / 不通过
当前 HEAD：<SHA>
是否 commit：是/否
commit SHA：<如有>
暂存区：空/非空
禁改路径扫描：通过/失败
生产发布：未完成
GitHub required check：未闭环
ERPNext 生产联调：未完成
```

════════════════════════════════════════════════════════════
