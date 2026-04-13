# TASK-005A1 利润盘点文档证据链补提交工程任务单

- 任务编号：TASK-005A1
- 模块：款式利润报表 / 文档证据链
- 优先级：P0
- 版本：V1.0
- 更新时间：2026-04-13 23:29 CST
- 作者：技术架构师
- 审计来源：审计意见书第 80 份，TASK-005A 有条件通过；阻塞点为 TASK-005A 关键文档未进入 git 提交链，且不得误解为 TASK-005B 可开工
- 前置依赖：TASK-005A 有条件通过；TASK-004C13 GitHub 平台闭环仍未完成
- 架构依据：`/03_需求与设计/01_架构设计/06_模块设计_款式利润报表.md` V0.2；`ADR-077`
- 任务边界：只做 TASK-005A 文档证据链补提交和门禁说明；不写前端代码，不写后端代码，不建迁移，不注册接口，不进入 TASK-005B/TASK-006

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-005A1
模块：利润盘点文档证据链补提交
优先级：P0（审计证据链整改）
════════════════════════════════════════════════════════════════════════════

【任务目标】
把 TASK-005A 的任务单、基线盘点报告、模块设计、ADR、Sprint 状态、审计记录和会话日志纳入 docs-only 白名单提交链，并明确该提交只代表“盘点证据入库”，不代表 TASK-005B 工程实现放行。

【当前事实】
1. TASK-005A 作为只读开发前基线盘点已经有条件通过。
2. TASK-004C13 平台闭环仍未完成：无 GitHub URL、无 `origin`、无 push、无 Hosted Runner、无 required check。
3. TASK-005A 关键文档当前尚未进入 git 提交链。
4. TASK-005B/TASK-006 继续阻塞。

【允许 stage 的白名单】

只允许 stage 以下文件：

```text
03_需求与设计/02_开发计划/TASK-005A_款式利润报表开发前基线盘点_工程任务单.md
03_需求与设计/01_架构设计/06_模块设计_款式利润报表.md
03_需求与设计/01_架构设计/TASK-005_款式利润报表_开发前基线盘点.md
03_需求与设计/01_架构设计/03_技术决策记录.md
03_需求与设计/01_架构设计/架构师会话日志.md
03_需求与设计/02_开发计划/当前 sprint 任务清单.md
03_需求与设计/02_开发计划/工程师会话日志.md
03_需求与设计/05_审计记录.md
03_需求与设计/05_审计记录/审计官会话日志.md
03_需求与设计/02_开发计划/TASK-005A1_利润盘点文档证据链补提交_工程任务单.md
```

如果其中某个文件不存在，先在报告中说明，不得改用 `git add .`。

【禁止 stage】

```text
06_前端/**
07_后端/**
.github/workflows/**
02_源码/**
04_测试与验收/**
05_交付物/**
node_modules/**
dist/**
.venv/**
__pycache__/**
*.db
*.sqlite
.env
.env.*
```

【必须执行步骤】

## 1. 确认仓库状态

```bash
cd /Users/hh/Desktop/领意服装管理系统
git rev-parse --show-toplevel
git branch --show-current
git log --oneline -8
git remote -v || true
git status --short
```

必须记录：
1. 当前 branch。
2. 当前 HEAD。
3. remote 是否为空。
4. 是否存在前端/后端业务代码变更。

## 2. 确认 TASK-005A 报告存在

```bash
test -f '03_需求与设计/01_架构设计/TASK-005_款式利润报表_开发前基线盘点.md'
```

如果不存在：停止，回复“TASK-005A 基线盘点报告不存在，无法做证据链补提交”。

## 3. 白名单 stage

只能显式执行：

```bash
git add \
  '03_需求与设计/02_开发计划/TASK-005A_款式利润报表开发前基线盘点_工程任务单.md' \
  '03_需求与设计/01_架构设计/06_模块设计_款式利润报表.md' \
  '03_需求与设计/01_架构设计/TASK-005_款式利润报表_开发前基线盘点.md' \
  '03_需求与设计/01_架构设计/03_技术决策记录.md' \
  '03_需求与设计/01_架构设计/架构师会话日志.md' \
  '03_需求与设计/02_开发计划/当前 sprint 任务清单.md' \
  '03_需求与设计/02_开发计划/工程师会话日志.md' \
  '03_需求与设计/05_审计记录.md' \
  '03_需求与设计/05_审计记录/审计官会话日志.md' \
  '03_需求与设计/02_开发计划/TASK-005A1_利润盘点文档证据链补提交_工程任务单.md'
```

禁止：

```bash
git add .
git add -A
git add 06_前端 07_后端 .github 02_源码
```

## 4. stage 后阻断检查

```bash
git diff --cached --name-only
```

必须人工确认只包含白名单。若出现禁止路径，立即执行：

```bash
git restore --staged <误加入文件>
```

不得 revert 用户或他人改动。

## 5. 业务代码变更检查

```bash
git diff --cached --name-only -- '06_前端' '07_后端' '.github' '02_源码'
```

必须无输出。

## 6. 敏感信息扫描

对 staged 文档执行：

```bash
git diff --cached -- '03_需求与设计' | rg -n 'token|password|secret|cookie|Authorization|BEGIN (RSA|OPENSSH|PRIVATE) KEY|postgres://|mysql://|redis://' -i || true
```

如果命中真实凭据，停止并脱敏后重新检查。普通规则文字命中必须人工标注为非真实凭据。

## 7. 形成 docs-only commit

```bash
git commit -m "docs: record style profit baseline evidence"
git rev-parse --short HEAD
```

记录新 HEAD 为 `TASK_005A_EVIDENCE_HEAD`。

## 8. 输出交付说明

必须回复：

```text
TASK-005A1 完成。
TASK_005A_EVIDENCE_HEAD=<新提交SHA>
本提交只代表 TASK-005A 只读盘点证据入库，不代表 TASK-005B 可开工。
TASK-004C13 平台闭环未完成前，TASK-005B/TASK-006 继续阻塞。
```

【验收标准】
□ TASK-005A 基线盘点报告已存在。
□ TASK-005A 任务单、基线盘点报告、模块设计、ADR、Sprint、审计记录、会话日志已进入 docs-only commit。
□ `git diff --cached --name-only -- 06_前端 07_后端 .github 02_源码` 无输出。
□ 未 stage 前端、后端、workflow、02_源码、测试交付大目录。
□ 敏感信息扫描无真实凭据。
□ commit message 为 `docs: record style profit baseline evidence`。
□ 输出 `TASK_005A_EVIDENCE_HEAD`。
□ 明确 TASK-005B/TASK-006 继续阻塞。

【预计工时】
0.5 天

════════════════════════════════════════════════════════════════════════════
