# TASK-004C12 C11 证据 SHA 口径修正工程任务单

- 任务编号：TASK-004C12
- 模块：生产计划集成 / GitHub 平台闭环 / SHA 证据口径
- 优先级：P0
- 版本：V1.0
- 更新时间：2026-04-13 21:59 CST
- 作者：技术架构师
- 审计来源：审计意见书第 77 份，TASK-004C11 有条件通过；最高风险为 C11 证据 SHA 口径不清，需明确 `fc0dc2c`、`62e70bd` 与“待推送 HEAD”的关系
- 前置依赖：TASK-004C11 有条件通过，但 GitHub 平台闭环未完成
- 当前本地基线：git root `/Users/hh/Desktop/领意服装管理系统`，branch `main`，当前本地 HEAD `62e70bd`，当前未配置 GitHub remote
- 架构依据：`/03_需求与设计/01_架构设计/05_模块设计_生产计划集成.md` V1.16；`ADR-074`
- 任务边界：只做 C11 证据 SHA 口径修正、最新审计记录入库、架构记录入库；不配置 remote，不 push，不修改前后端业务逻辑，不进入 TASK-005/TASK-006

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-004C12
模块：C11 证据 SHA 口径修正
优先级：P0（平台证据准确性整改）
════════════════════════════════════════════════════════════════════════════

【任务目标】
修正 TASK-004C11 平台闭环证据中的 SHA 口径，明确 `fc0dc2c`、`62e70bd` 与“待推送 HEAD”的关系，避免管理员后续配置 remote/push 时使用错误提交作为平台证据。

【必须明确的 SHA 关系】

当前本地提交链：

```text
62e70bd docs: record frontend ci platform closure
fc0dc2c docs: prepare frontend ci platform closure
b32585c docs: record frontend platform gate blocker
e4a3e4b chore: establish production repository baseline
```

口径定义：

1. `b32585c`：TASK-004C10 之前的基线提交，记录 C9 blocker docs。
2. `fc0dc2c`：TASK-004C11 文档准备提交，包含 C11 任务单、第 76 份审计后续架构记录等。
3. `62e70bd`：TASK-004C11 平台证据 docs-only 提交，当前本地 HEAD；因为尚未配置 remote，所以它仍是本地待推送 HEAD。
4. TASK-004C12 如果形成新的 docs-only 修正提交，则新的待推送 HEAD 是 C12 提交；`62e70bd` 变为其父提交，不再是最新待推送 HEAD。
5. GitHub Hosted Runner 后续应以“实际 push 到 GitHub 的 main HEAD”为准；Run URL 里的 Commit SHA 必须等于远端 main HEAD。

【允许修改或创建】

允许修改：
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录/TASK-004C11_GitHub平台最终闭环证据.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录/审计官会话日志.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/03_技术决策记录.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/05_模块设计_生产计划集成.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/架构师会话日志.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/当前 sprint 任务清单.md

允许新建：
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-004C12_C11证据SHA口径修正_工程任务单.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录/TASK-004C12_C11证据SHA口径修正证据.md

禁止修改：
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/**
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/**
- /Users/hh/Desktop/领意服装管理系统/.github/workflows/**
- /Users/hh/Desktop/领意服装管理系统/02_源码/**
- 任意 TASK-005/TASK-006 文件

【必须执行步骤】

## 1. 确认本地提交链

```bash
cd /Users/hh/Desktop/领意服装管理系统
git rev-parse --show-toplevel
git branch --show-current
git log --oneline -6
git rev-parse --short HEAD
git remote -v || true
```

必须确认：

```text
HEAD = 62e70bd
origin = 未配置
```

如 HEAD 已不是 `62e70bd`，必须在证据中记录实际 HEAD，并解释是否已有 C12 之前的 docs commit。

## 2. 修正 C11 证据文件

修改：

```text
/Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录/TASK-004C11_GitHub平台最终闭环证据.md
```

必须新增章节：

```markdown
## SHA 口径修正

| SHA | 含义 | 是否已推送 | 与平台闭环关系 |
| --- | --- | --- | --- |
| b32585c | C10 前基线，C9 blocker docs commit | 否 | 平台闭环前置基线 |
| fc0dc2c | C11 文档准备提交 | 否 | 包含 C11 任务单和第 76 份后续架构记录 |
| 62e70bd | C11 平台证据 docs-only 提交 | 否 | 第 77 份审计时的本地待推送 HEAD |
| <C12提交后HEAD> | C12 SHA 口径修正提交 | 否 | 若形成 C12 commit，则它才是新的待推送 HEAD |

说明：GitHub Hosted Runner 后续必须以实际 push 后的远端 main HEAD 为准；Run URL 中的 Commit SHA 必须等于远端 main HEAD。
```

同时修正文档中原 `Commit SHA: fc0dc2c` 的歧义：

```text
C11 文档准备 commit：fc0dc2c
C11 平台证据 commit：62e70bd
当前待推送 HEAD：以 git rev-parse --short HEAD 为准
```

## 3. 创建 C12 证据文件

路径：

```text
/Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录/TASK-004C12_C11证据SHA口径修正证据.md
```

模板：

```markdown
# TASK-004C12 C11 证据 SHA 口径修正证据

- 任务编号：TASK-004C12
- 更新时间：YYYY-MM-DD HH:MM CST
- 执行人：
- 结论：通过/不通过

## 本地提交链

```text
粘贴 git log --oneline -6 输出
```

## SHA 口径

| SHA | 含义 | 是否已推送 | 说明 |
| --- | --- | --- | --- |
| b32585c | C10 前基线 | 否 | C9 blocker docs commit |
| fc0dc2c | C11 文档准备提交 | 否 | prepare frontend ci platform closure |
| 62e70bd | C11 平台证据提交 | 否 | record frontend ci platform closure |
| <C12提交后HEAD> | C12 口径修正提交 | 否 | 本任务形成后新的待推送 HEAD |

## 修正结果

- C11 证据文件已新增 SHA 口径修正章节：是/否
- C11 证据文件已消除 `Commit SHA: fc0dc2c` 歧义：是/否
- 当前 remote 状态：未配置 / 已配置
- 当前待推送 HEAD：

## 剩余平台动作

- 管理员提供 GitHub URL：未完成
- 配置 origin：未完成
- push main：未完成
- Hosted Runner 实跑：未完成
- Required Check 配置：未完成

## 敏感信息检查

- remote 输出无 token/password/secret/cookie：通过/不通过
- 证据文档无 token/password/secret/cookie/私钥：通过/不通过
```

## 4. docs-only stage

只允许 stage 以下文件：

```bash
cd /Users/hh/Desktop/领意服装管理系统
git add \
  '03_需求与设计/05_审计记录/TASK-004C11_GitHub平台最终闭环证据.md' \
  '03_需求与设计/05_审计记录/TASK-004C12_C11证据SHA口径修正证据.md' \
  '03_需求与设计/02_开发计划/TASK-004C12_C11证据SHA口径修正_工程任务单.md' \
  '03_需求与设计/05_审计记录.md' \
  '03_需求与设计/05_审计记录/审计官会话日志.md' \
  '03_需求与设计/01_架构设计/03_技术决策记录.md' \
  '03_需求与设计/01_架构设计/05_模块设计_生产计划集成.md' \
  '03_需求与设计/01_架构设计/架构师会话日志.md' \
  '03_需求与设计/02_开发计划/当前 sprint 任务清单.md'
```

## 5. 阻断误提交检查

```bash
git diff --cached --name-only | rg '^(00_交接与日志|01_需求与资料|02_源码|03_环境与部署|04_测试与验收|05_交付物|06_前端|07_后端|\.github)/' && exit 1 || true
git diff --cached --name-only | rg '(node_modules|dist/|\.venv|__pycache__|\.env|\.db$|\.xml$)' && exit 1 || true
git diff --cached | rg -i 'ghp_|github_pat_|authorization:|cookie:|password=|passwd=|secret=|token=' && exit 1 || true
git diff --cached --name-only
```

## 6. 提交

```bash
git commit -m "docs: clarify frontend ci platform sha lineage"
git rev-parse --short HEAD
```

提交后必须在 C12 证据里记录实际 commit SHA。如无法在同一提交内记录自身 SHA，则记录：

```text
C12 证据提交后，`git rev-parse --short HEAD` 的输出即为新的待推送 HEAD；推送前以命令输出为准。
```

【验收标准】

□ C11 证据已新增 SHA 口径修正章节。  
□ C11 证据明确 `fc0dc2c` 是 C11 文档准备提交。  
□ C11 证据明确 `62e70bd` 是 C11 平台证据提交。  
□ C11 证据明确 `62e70bd` 在第 77 份审计时是本地待推送 HEAD。  
□ C11 证据明确 C12 提交后新的待推送 HEAD 以 `git rev-parse --short HEAD` 为准。  
□ C12 证据文件已创建。  
□ docs-only commit 已形成，提交信息为 `docs: clarify frontend ci platform sha lineage`。  
□ 未配置 remote。  
□ 未 push。  
□ 未修改前端业务代码。  
□ 未修改后端业务代码。  
□ 未进入 TASK-005/TASK-006。  

【禁止事项】

- 禁止配置 remote。
- 禁止 push。
- 禁止修改前端业务代码。
- 禁止修改后端业务代码。
- 禁止修改 `.github/workflows/**`。
- 禁止提交 `02_源码/**`、`04_测试与验收/**`、`05_交付物/**`。
- 禁止提交生成物、缓存、数据库、环境变量、pytest xml。
- 禁止进入 TASK-005/TASK-006。

【交付回报格式】

完成后按以下格式回复：

```text
TASK-004C12 已完成。

SHA 口径：
- b32585c：C10 前基线 / C9 blocker docs commit
- fc0dc2c：C11 文档准备提交
- 62e70bd：C11 平台证据提交，第 77 份审计时的本地待推送 HEAD
- C12 后当前待推送 HEAD：...

修正文件：
- C11 证据 SHA 口径已修正：是/否
- C12 证据已创建：是/否

Docs commit：
- commit SHA：...
- commit message：docs: clarify frontend ci platform sha lineage

剩余平台动作：
- 管理员提供 GitHub URL
- 配置 origin
- push main
- Hosted Runner 实跑
- 配置 Frontend Verify required check

未进入范围：
- 未配置 remote
- 未 push
- 未修改前端业务代码
- 未修改后端业务代码
- 未进入 TASK-005/TASK-006
```
