# TASK-005K1 K 证据本地基线提交工程任务单

- 任务编号：TASK-005K1
- 模块：款式利润报表
- 优先级：P0
- 任务类型：docs-only 本地基线提交
- 更新时间：2026-04-15 15:00 CST
- 作者：技术架构师
- 前置审计：审计意见书第 157 份，TASK-005K 通过
- 前置结论：TASK-005K 可进入 TASK-005 本地封版复审，但 K 证据文件仍未跟踪

## 一、任务目标

将 TASK-005K 封版盘点证据文件纳入本地 git 基线，形成 TASK-005 本地封版复审前的稳定证据点。

本任务只做 docs-only 白名单提交，不修改前端、后端、workflow、源码、审计记录，不进入 TASK-006。

## 二、允许提交文件

只允许提交以下 1 个文件：

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005K_款式利润模块封版盘点证据.md`

## 三、禁止提交文件

1. 禁止提交 `06_前端/**`。
2. 禁止提交 `07_后端/**`。
3. 禁止提交 `.github/**`。
4. 禁止提交 `02_源码/**`。
5. 禁止提交 `TASK-006*`。
6. 禁止提交 `03_需求与设计/05_审计记录.md`。
7. 禁止提交 `03_需求与设计/05_审计记录/审计官会话日志.md`。
8. 禁止提交 `.pytest-postgresql-*.xml`。
9. 禁止提交历史未跟踪目录。
10. 禁止使用 `git add .` 或 `git add -A`。

## 四、执行步骤

### 4.1 检查证据文件存在

```bash
cd /Users/hh/Desktop/领意服装管理系统
test -f "03_需求与设计/02_开发计划/TASK-005K_款式利润模块封版盘点证据.md"
```

### 4.2 检查当前工作区

```bash
cd /Users/hh/Desktop/领意服装管理系统
git status --short
```

要求：可以存在历史未跟踪文件，但本任务不得暂存它们。

### 4.3 白名单暂存

```bash
cd /Users/hh/Desktop/领意服装管理系统
git add -- "03_需求与设计/02_开发计划/TASK-005K_款式利润模块封版盘点证据.md"
```

### 4.4 暂存校验

```bash
cd /Users/hh/Desktop/领意服装管理系统
git diff --cached --name-only
```

要求输出只能是：

```text
03_需求与设计/02_开发计划/TASK-005K_款式利润模块封版盘点证据.md
```

如出现其他文件，立即停止并回报，不得提交。

### 4.5 提交

```bash
cd /Users/hh/Desktop/领意服装管理系统
git commit -m "docs: add task 005K closeout evidence"
```

## 五、提交后核验

```bash
cd /Users/hh/Desktop/领意服装管理系统
git show --stat --oneline --name-only HEAD
git status --short
git diff -- 06_前端/lingyi-pc/src/App.vue
```

## 六、验收标准

1. HEAD commit 存在。
2. commit message 为 `docs: add task 005K closeout evidence`。
3. commit 文件清单只包含 `TASK-005K_款式利润模块封版盘点证据.md`。
4. 未提交前端、后端、workflow、`02_源码`、审计记录、TASK-006 或运行产物。
5. `App.vue` 无 diff。
6. `.pytest-postgresql-*.xml` 未被提交。
7. TASK-006 继续阻塞，未放行。

## 七、交付回报格式

```text
TASK-005K1 K 证据本地基线提交完成。

Commit：<完整 commit hash>
提交文件：
- 03_需求与设计/02_开发计划/TASK-005K_款式利润模块封版盘点证据.md

核验：
- git show --name-only HEAD：仅 1 个白名单文件
- App.vue diff：无
- 运行产物：未提交

TASK-006 状态：继续阻塞，未放行。
```
