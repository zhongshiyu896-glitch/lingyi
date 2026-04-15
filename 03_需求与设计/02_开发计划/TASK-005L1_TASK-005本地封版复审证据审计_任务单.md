# TASK-005L1 TASK-005 本地封版复审证据审计任务单

- 任务编号：TASK-005L1
- 模块：款式利润报表
- 优先级：P0
- 任务类型：审计复核 / 本地封版判定 / 禁改边界核验
- 更新时间：2026-04-15 15:43 CST
- 作者：技术架构师
- 前置任务：TASK-005L 本地封版复审证据已输出
- 前置证据：`/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005L_TASK-005本地封版复审证据.md`
- 前置基线：`1da795333d20ed8ecfb2308da623358668272458`

## 一、任务目标

审计 TASK-005L 本地封版复审证据，判断是否允许将 TASK-005 款式利润报表标记为“本地封版完成”。

本任务只做审计复核，不做功能开发，不修改前端/后端业务代码，不提交代码，不放行 TASK-006。

## 二、审计对象

必须审计以下文件：

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005L_TASK-005本地封版复审证据.md`

必须参考以下文件：

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/06_模块设计_款式利润报表.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/03_技术决策记录.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录/审计官会话日志.md`

## 三、审计重点

1. TASK-005L 证据结论是否可以支撑“TASK-005 本地封版完成”。
2. 当前 HEAD 是否为 `1da795333d20ed8ecfb2308da623358668272458`，如不是，是否有合理说明。
3. K1 commit 是否只包含 `TASK-005K_款式利润模块封版盘点证据.md`。
4. 前端只读门禁证据是否完整：`check:style-profit-contracts`、`test:style-profit-contracts`、`verify`、`npm audit --audit-level=high`。
5. 后端 style-profit API 回归证据是否完整：`34 passed` 与 `py_compile`。
6. PostgreSQL 证据是否如实披露：本轮未重跑，不得伪造；历史 F8/F9 双 JUnit 证据是否可接受。
7. 禁改范围是否成立：未改 `06_前端/**`、`07_后端/**`、`.github/**`、`02_源码/**`、迁移、TASK-006。
8. `App.vue` 是否无探针残留。
9. `.pytest-postgresql-*.xml` 是否未被暂存、未被提交。
10. 证据是否明确本地封版不等同生产发布、不等同平台 required-check 闭环。
11. 证据是否明确 TASK-006 继续阻塞。

## 四、建议复核命令

### 4.1 Git 基线

```bash
cd /Users/hh/Desktop/领意服装管理系统
git rev-parse HEAD
git show --stat --oneline --name-only HEAD
git status --short
git diff -- 06_前端/lingyi-pc/src/App.vue
git diff --name-only -- '06_前端' '07_后端' '.github' '02_源码' '03_需求与设计/**/TASK-006*'
```

### 4.2 前端证据复验

```bash
cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc
npm run check:style-profit-contracts
npm run test:style-profit-contracts
npm run verify
npm audit --audit-level=high
```

### 4.3 后端证据复验

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest -q tests/test_style_profit_api.py tests/test_style_profit_api_permissions.py tests/test_style_profit_api_audit.py tests/test_style_profit_api_errors.py
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
```

### 4.4 PostgreSQL 证据判断

如无 `POSTGRES_TEST_DSN`，不得要求工程师伪造新 PostgreSQL 结果；应审计 TASK-005L 是否如实披露并引用 F8/F9 已审计证据。

如有一次性 PostgreSQL 测试库与安全门禁变量，可补跑：

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
./scripts/run_postgresql_ci_gate.sh
```

## 五、审计结论口径

审计结论只能使用以下之一：

1. `通过：允许 TASK-005 标记为本地封版完成；TASK-006 继续阻塞。`
2. `有条件通过：列出必须修复的问题；修复前不得标记 TASK-005 本地封版完成；TASK-006 继续阻塞。`
3. `不通过：列出阻断问题；TASK-005 不得封版；TASK-006 继续阻塞。`

不得写：

1. `生产发布完成`。
2. `平台 required-check 已闭环`，除非有真实平台证据。
3. `TASK-006 已放行`。

## 六、审计输出要求

审计完成后必须写入：

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录/审计官会话日志.md`

审计意见书必须包含：

1. 审计结论。
2. 问题项数量，按高/中/低分组。
3. 风险项数量。
4. 复核命令与结果。
5. 是否允许 TASK-005 标记为本地封版完成。
6. TASK-006 状态必须写：继续阻塞，未放行。

## 七、交付回报格式

```text
TASK-005L1 审计完成。

结论：通过 / 有条件通过 / 不通过

是否允许 TASK-005 标记为本地封版完成：是 / 否

问题项：高 X / 中 X / 低 X
风险项：X

已写入：
- /03_需求与设计/05_审计记录.md
- /03_需求与设计/05_审计记录/审计官会话日志.md

TASK-006 状态：继续阻塞，未放行。
```
