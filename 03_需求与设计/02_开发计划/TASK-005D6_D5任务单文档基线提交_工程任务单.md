# TASK-005D6 D5 任务单文档基线提交工程任务单

## 任务编号

TASK-005D6

## 任务名称

D5 任务单文档基线提交

## 任务目标

将已通过审计的 `TASK-005D5_D4证据提交后HEAD占位修正_工程任务单.md` 纳入本地文档基线，并将本次 D6 任务单及必要架构文档更新一并以 docs-only 方式提交，清理进入 `TASK-005E/API` 前的最后文档证据缺口。

## 审计来源

审计意见书第 97 份：`TASK-005D5` 已通过，D4 证据提交后 HEAD 已回填为 `47c1728a4eb2ca16549f6478d3bdb5af95b12b1a`；唯一建议是在启动 `TASK-005E` 前确认未跟踪的 D5 任务单是否需要纳入文档基线。

## 架构决策

需要纳入文档基线。

原因：D5 是 D4 证据链闭环任务单，如果不入库，后续 `TASK-005E/API` 审计只能看到 D4 证据修正结果，看不到修正任务的正式来源和执行边界，证据链不完整。

## 当前状态

- `TASK-005D5` 已通过。
- 本任务只做 docs-only 文档入库。
- 本任务通过审计后，才允许下发 `TASK-005E/API`。
- `TASK-006` 继续阻塞。

## 允许纳入提交的文件白名单

只允许 stage 以下文件：

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005D5_D4证据提交后HEAD占位修正_工程任务单.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005D6_D5任务单文档基线提交_工程任务单.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/当前 sprint 任务清单.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/06_模块设计_款式利润报表.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/03_技术决策记录.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/架构师会话日志.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录/审计官会话日志.md`

如果工程师日志、审计记录、审计官日志没有新增变化，则不要强行 stage。

## 禁止修改

- `/Users/hh/Desktop/领意服装管理系统/07_后端/**`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/**`
- `/Users/hh/Desktop/领意服装管理系统/.github/**`
- `/Users/hh/Desktop/领意服装管理系统/02_源码/**`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005E*`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-006*`

## 禁止操作

1. 禁止 `git add .`
2. 禁止 `git add -A`
3. 禁止 `git add --all`
4. 禁止修改业务代码。
5. 禁止修改后端。
6. 禁止修改前端。
7. 禁止修改 `.github`。
8. 禁止修改 `02_源码`。
9. 禁止新增或修改 `TASK-005E*`。
10. 禁止新增或修改 `TASK-006*`。
11. 禁止 push。
12. 禁止配置 remote/origin。
13. 禁止进入 `TASK-005E/API` 实现。
14. 禁止进入 `TASK-006`。

## 验证命令

进入项目根目录：

```bash
cd /Users/hh/Desktop/领意服装管理系统
```

确认 D5 任务单存在：

```bash
test -f '03_需求与设计/02_开发计划/TASK-005D5_D4证据提交后HEAD占位修正_工程任务单.md'
```

确认 D6 任务单存在：

```bash
test -f '03_需求与设计/02_开发计划/TASK-005D6_D5任务单文档基线提交_工程任务单.md'
```

确认未进入 TASK-005E / TASK-006：

```bash
git diff --name-only -- '03_需求与设计/02_开发计划' | grep 'TASK-005E\|TASK-006' || true
```

要求：无输出。

禁改边界扫描：

```bash
git diff --name-only -- 07_后端 06_前端 .github 02_源码
git diff --cached --name-only
```

要求：

1. 第一条命令无输出。
2. `git diff --cached --name-only` 只能出现白名单文件。

## 推荐提交方式

禁止批量 add，只允许精确 add：

```bash
git add -- '03_需求与设计/02_开发计划/TASK-005D5_D4证据提交后HEAD占位修正_工程任务单.md'
git add -- '03_需求与设计/02_开发计划/TASK-005D6_D5任务单文档基线提交_工程任务单.md'
git add -- '03_需求与设计/02_开发计划/当前 sprint 任务清单.md'
git add -- '03_需求与设计/01_架构设计/06_模块设计_款式利润报表.md'
git add -- '03_需求与设计/01_架构设计/03_技术决策记录.md'
git add -- '03_需求与设计/01_架构设计/架构师会话日志.md'
```

如以下文件有本轮新增变化，也允许精确 add：

```bash
git add -- '03_需求与设计/02_开发计划/工程师会话日志.md'
git add -- '03_需求与设计/05_审计记录.md'
git add -- '03_需求与设计/05_审计记录/审计官会话日志.md'
```

提交信息：

```bash
git commit -m "docs: baseline TASK-005D5 evidence task"
```

## 验收标准

- [ ] D5 任务单已纳入本地 git 跟踪。
- [ ] D6 任务单已纳入本地 git 跟踪。
- [ ] 本次提交只包含白名单文档。
- [ ] 未修改后端。
- [ ] 未修改前端。
- [ ] 未修改 `.github`。
- [ ] 未修改 `02_源码`。
- [ ] 未新增或修改 `TASK-005E*`。
- [ ] 未新增或修改 `TASK-006*`。
- [ ] 未 push。
- [ ] 未配置 remote/origin。
- [ ] 本地 docs-only commit 已形成。

## 交付回报格式

```text
TASK-005D6 已完成。

提交信息：
- commit: [本次 docs-only 提交 SHA]
- message: docs: baseline TASK-005D5 evidence task

验证结果：
- D5 任务单存在：[通过/不通过]
- D6 任务单存在：[通过/不通过]
- TASK-005E/TASK-006 禁入扫描：[通过/不通过]
- 禁改边界扫描：[通过/不通过]
- staged 白名单检查：[通过/不通过]

确认：
- 未修改后端
- 未修改前端
- 未修改 .github
- 未修改 02_源码
- 未进入 TASK-005E
- 未进入 TASK-006
- 未 push
- 未配置 remote/origin
```
