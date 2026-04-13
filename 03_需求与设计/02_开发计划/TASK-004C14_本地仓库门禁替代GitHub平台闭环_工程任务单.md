# TASK-004C14 本地仓库门禁替代 GitHub 平台闭环工程任务单

- 任务编号：TASK-004C14
- 模块：生产计划集成 / 本地仓库门禁 / 平台闭环替代
- 优先级：P0
- 版本：V1.0
- 更新时间：2026-04-13 23:58 CST
- 作者：技术架构师
- 触发原因：项目当前没有 GitHub 仓库，长期等待无凭据 GitHub URL 会造成流程死循环
- 前置状态：TASK-005A/A1/A2 文档问题已闭环，当前本地 HEAD 为 `59a55ec`；`origin` 为空
- 架构依据：`/03_需求与设计/01_架构设计/05_模块设计_生产计划集成.md` V1.18；`ADR-078`
- 任务边界：只做本地门禁替代方案、验证证据和文档入库；不配置 GitHub，不 push，不修改前后端业务代码，不进入 TASK-005B/TASK-006 实现

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-004C14
模块：本地仓库门禁替代 GitHub 平台闭环
优先级：P0（解除 GitHub URL 等待死循环）
════════════════════════════════════════════════════════════════════════════

【任务目标】
把 TASK-004C13 的 GitHub 平台硬门禁改为“本地仓库 + 本地验证证据”门禁，停止等待不存在的 GitHub URL，并形成可审计的本地闭环证据。

【核心决策】
1. 当前项目按本地仓库交付，不再把 GitHub URL 作为继续工作的硬前提。
2. `origin` 为空是当前可接受状态，不再视为阻塞项。
3. Hosted Runner / Required Check 改为“未来接入 GitHub 时再启用”的增强项。
4. 当前阶段以本地 `main`、本地 commit、可复现验证命令、审计记录作为门禁依据。
5. TASK-005B 是否放行，必须等待 TASK-004C14 本地门禁证据通过审计后再决定。
6. TASK-006 仍需单独架构放行，不因本任务自动启动。

【当前基线】

```text
git root: /Users/hh/Desktop/领意服装管理系统
branch: main
当前本地 HEAD: 59a55ec docs: correct style profit baseline timeline
remote: 空
```

【允许修改或创建】

允许修改：
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/05_模块设计_生产计划集成.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/03_技术决策记录.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/架构师会话日志.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/当前 sprint 任务清单.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录/审计官会话日志.md

允许新建：
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-004C14_本地仓库门禁替代GitHub平台闭环_工程任务单.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录/TASK-004C14_本地仓库门禁闭环证据.md

禁止修改：
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/**
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/**
- /Users/hh/Desktop/领意服装管理系统/.github/workflows/**
- /Users/hh/Desktop/领意服装管理系统/02_源码/**
- 任意 TASK-005B/TASK-006 实现文件

【必须执行步骤】

## 1. 确认本地仓库状态

```bash
cd /Users/hh/Desktop/领意服装管理系统
git rev-parse --show-toplevel
git branch --show-current
git log --oneline -10
git rev-parse --short HEAD
git remote -v || true
git status --short
```

必须记录：
1. 本地 root。
2. branch。
3. 当前 HEAD。
4. remote 为空。
5. 是否存在未提交文档或审计记录。

## 2. 执行本地验证门禁

后端验证：

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest -q
.venv/bin/python -m unittest discover
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
```

前端验证：

```bash
cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc
npm ci
npm run verify
npm audit --audit-level=high
```

如果当前机器缺依赖，必须记录失败原因和缺失依赖，不得伪造通过。

## 3. 形成本地门禁证据

创建：

```text
/Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录/TASK-004C14_本地仓库门禁闭环证据.md
```

证据必须包含：
1. 本地仓库 root。
2. branch。
3. 本地 HEAD。
4. remote 为空的确认。
5. 后端 pytest 结果。
6. 后端 unittest 结果。
7. 后端 py_compile 结果。
8. 前端 npm ci 结果。
9. 前端 npm run verify 结果。
10. 前端 npm audit 结果。
11. 未触碰前端/后端业务代码的确认。
12. GitHub/Hosted Runner/Required Check 改为未来增强项的说明。
13. 是否建议放行 TASK-005B 的结论：只能写“待审计官复审决定”，不得自行放行。

## 4. docs-only 白名单提交

只允许 stage：

```bash
git add \
  '03_需求与设计/02_开发计划/TASK-004C14_本地仓库门禁替代GitHub平台闭环_工程任务单.md' \
  '03_需求与设计/05_审计记录/TASK-004C14_本地仓库门禁闭环证据.md' \
  '03_需求与设计/01_架构设计/05_模块设计_生产计划集成.md' \
  '03_需求与设计/01_架构设计/03_技术决策记录.md' \
  '03_需求与设计/01_架构设计/架构师会话日志.md' \
  '03_需求与设计/02_开发计划/当前 sprint 任务清单.md' \
  '03_需求与设计/05_审计记录.md' \
  '03_需求与设计/05_审计记录/审计官会话日志.md'
```

禁止：

```bash
git add .
git add -A
git add 06_前端 07_后端 .github 02_源码
```

检查：

```bash
git diff --cached --name-only
git diff --cached --name-only -- '06_前端' '07_后端' '.github' '02_源码'
```

提交：

```bash
git commit -m "docs: replace github gate with local delivery gate"
git rev-parse --short HEAD
```

记录新 HEAD 为 `LOCAL_GATE_HEAD`。

【验收标准】
□ 不再要求提供 GitHub 仓库 URL。
□ `origin` 为空被记录为当前本地交付模式的事实，而不是阻塞项。
□ 本地后端验证结果已记录，失败时有真实原因。
□ 本地前端验证结果已记录，失败时有真实原因。
□ `TASK-004C14_本地仓库门禁闭环证据.md` 已创建。
□ docs-only 提交已形成，commit message 为 `docs: replace github gate with local delivery gate`。
□ 未 stage 或修改前端、后端、workflow、02_源码。
□ 未进入 TASK-005B/TASK-006。
□ 是否放行 TASK-005B 交由审计官复审结论决定。

【预计工时】
0.5-1 天

════════════════════════════════════════════════════════════════════════════
