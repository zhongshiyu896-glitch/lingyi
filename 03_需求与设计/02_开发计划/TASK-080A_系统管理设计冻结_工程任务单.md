# TASK-080A 系统管理设计冻结 工程任务单

## 1. 基本信息

- 任务编号：TASK-080A
- 任务名称：系统管理设计冻结
- 模块：系统管理 / 设计冻结
- 派发角色：A Technical Architect
- 执行角色：B Engineer
- 审计角色：C Auditor
- 优先级：P0
- 派发时间：2026-04-21 06:54 CST+8
- 前置依赖：TASK-070G 权限治理本地封版白名单提交审计通过（审计意见书第438份，本地 commit `1d7d2ff`）
- 当前定位：仅冻结系统管理模块设计边界，为后续 `TASK-080B` 只读实现任务提供合同；本任务不实现后端、前端、测试或生产发布动作。

> 本任务是 A -> B 的设计冻结任务，不是实现任务。禁止 push / PR / tag / 生产发布 / ERPNext 生产联调声明 / GitHub required check 闭环声明。

## 2. 背景依据

B 必须先阅读并基于以下文件形成设计冻结文档：

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-020_权限治理设计.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-020A_权限治理设计.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/Sprint3_总体规划.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-070G_权限治理本地封版提交证据.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录/审计官会话日志.md`

关键约束：

1. `TASK-020` 明确“审计通过后，仅允许继续系统管理设计冻结，不允许直接实现权限配置写入”。
2. `TASK-070G` 已完成权限治理本地封版，仅代表本地基线，不等同远端发布或生产发布。
3. 系统管理必须继承 `TASK-007` 权限审计基座、`TASK-010` 前端写入口门禁、权限治理 `permission:*` 已封版能力。

## 3. 本任务目标

生成系统管理设计冻结文档，明确后续系统管理实现的允许边界、禁止边界、权限动作、审计要求、接口草案、前端入口草案和验收标准。

必须输出：

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-080_系统管理设计.md`
- 追加 `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md`

## 4. 允许修改范围

仅允许新增或修改以下文件：

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-080_系统管理设计.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md`

如发现必须修改其他文件，立即 `BLOCKED`，不得自行扩大范围。

## 5. 禁止修改范围

禁止修改以下任何路径或文件：

- `/Users/hh/Documents/Playground 2/LOOP_STATE.md`
- `/Users/hh/Documents/Playground 2/INTERVENTION_QUEUE.md`
- `/Users/hh/Desktop/领意服装管理系统/00_交接与日志/HANDOVER_STATUS.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/架构师会话日志.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录/审计官会话日志.md`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/**`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/**`
- `/Users/hh/Desktop/领意服装管理系统/.github/**`
- `/Users/hh/Desktop/领意服装管理系统/.ci-reports/**`
- `/Users/hh/Desktop/领意服装管理系统/01_需求与资料/**`
- `/Users/hh/Desktop/领意服装管理系统/02_源码/**`
- `/Users/hh/Desktop/领意服装管理系统/03_环境与部署/**`
- `/Users/hh/Desktop/领意服装管理系统/04_测试与验收/**`
- `/Users/hh/Desktop/领意服装管理系统/05_交付物/**`

禁止执行：

- 后端实现、前端实现、测试实现、migration/model/router/service/schema 改动
- `git add .`、`git add -A`
- commit / push / PR / tag / 生产发布
- ERPNext 生产联调声明
- GitHub required check / branch protection 闭环声明

## 6. 设计冻结必须覆盖的内容

`TASK-080_系统管理设计.md` 必须至少包含以下章节。

### 6.1 目标与非目标

必须明确：

- 本阶段只做系统管理设计冻结。
- 后续实现优先只读基线。
- 不实现生产配置写入。
- 不实现字典写入。
- 不实现权限配置写入。
- 不实现平台管理动作。
- 不声明远端发布、生产发布或 required check 闭环。

### 6.2 功能范围冻结

至少覆盖以下系统管理能力，并标明本阶段定位：

| 能力 | 本阶段定位 | 说明 |
|---|---|---|
| 系统配置目录 | 只读设计 | 仅展示配置 key、分组、说明、来源、是否敏感，不展示敏感值 |
| 数据字典目录 | 只读设计 | 仅展示字典类型、编码、名称、状态、来源 |
| 系统健康检查 | 只读诊断设计 | 安全健康摘要，不泄露连接串、token、cookie、密码、DSN |
| 任务状态 | 只读设计 | 只展示安全摘要，不展示 payload 原文 |
| 平台状态 | 只读记录 | 可记录本地/远端/CI 状态，但不得宣称未闭环项已完成 |
| 系统管理写入 | 后续任务冻结 | 写入必须单独任务、权限前置、操作审计、二次确认 |

### 6.3 权限动作冻结

至少定义以下动作并说明用途、默认角色、前端可见性：

- `system:read`
- `system:config_read`
- `system:dictionary_read`
- `system:diagnostic`

必须明确以下动作默认冻结，不得在后续只读实现中开放：

- `system:config_write`
- `system:dictionary_write`
- `system:platform_manage`
- `system:cache_refresh`
- `system:sync`
- `system:import`
- `system:export`

### 6.4 后端接口草案

只允许设计 GET 只读接口草案，例如：

- `GET /api/system/configs/catalog`
- `GET /api/system/dictionaries/catalog`
- `GET /api/system/health/summary`
- `GET /api/system/tasks/status`
- `GET /api/system/platform/status`

每个接口必须说明：

- 所需权限动作
- 是否允许普通前端入口
- 是否需要管理员角色
- 响应字段白名单
- fail-closed 条件
- 敏感信息脱敏规则
- 不得访问 ERPNext 或外部系统写接口

### 6.5 前端入口草案

必须说明：

- 后续只读页面建议路径，例如 `/system/management`。
- `meta.module = system`。
- 无权限不得发请求。
- diagnostic 默认隐藏，仅管理员或显式权限可见。
- 不得出现普通用户可见的写入、导入、导出、同步、刷新缓存、平台管理按钮。

### 6.6 审计与安全要求

必须明确：

- 诊断类访问必须安全审计或至少可追踪。
- 后续任何写入必须操作审计。
- 响应不得包含 token、Authorization、Cookie、password、secret、DSN、DATABASE_URL、raw headers、raw payload。
- 权限源不可用、未知权限动作、未知资源字段必须 fail closed。
- 不得复用 `permission:*`、`dashboard:*`、`report:*`、`warehouse:*`、`inventory:*` 权限替代 `system:*`。

### 6.7 后续任务拆分建议

至少拆出后续候选任务：

- `TASK-080B` 系统配置只读目录基线
- `TASK-080C` 数据字典只读目录基线
- `TASK-080D` 系统健康检查只读诊断基线
- `TASK-080E` 系统管理本地收口验证
- `TASK-080F` 系统管理本地封版复审
- `TASK-080G` 系统管理本地封版白名单提交

必须明确：写入类任务不在 `TASK-080B~080G` 默认范围内，除非 A 另开任务单。

## 7. 必须执行验证

### 7.1 文件范围验证

```bash
cd /Users/hh/Desktop/领意服装管理系统
git diff --name-only -- \
  06_前端 \
  07_后端 \
  .github \
  .ci-reports \
  01_需求与资料 \
  02_源码 \
  03_环境与部署 \
  04_测试与验收 \
  05_交付物
```

要求：空输出。

### 7.2 设计文档关键字验证

```bash
rg -n "system:read|system:config_read|system:dictionary_read|system:diagnostic|system:config_write|system:dictionary_write|system:platform_manage|fail closed|敏感|token|DSN|/api/system/configs/catalog|/api/system/dictionaries/catalog|/api/system/health/summary" \
  /Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-080_系统管理设计.md
```

要求：上述关键权限、冻结动作、安全边界和接口草案均有命中。

### 7.3 Markdown 格式验证

```bash
cd /Users/hh/Desktop/领意服装管理系统
git diff --check -- \
  03_需求与设计/01_架构设计/TASK-080_系统管理设计.md \
  03_需求与设计/02_开发计划/工程师会话日志.md
```

要求：通过。

## 8. 回交格式

B 完成后按以下格式回交，不得省略验证结果：

```text
STATUS: READY_FOR_AUDIT
TASK_ID: TASK-080A
ROLE: B Engineer

CHANGED_FILES:
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-080_系统管理设计.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md

EVIDENCE:
- 说明系统管理设计冻结文档已覆盖目标与非目标、功能范围、权限动作、后端接口草案、前端入口草案、审计安全要求、后续任务拆分。
- 说明未修改后端、前端、测试、控制面、审计日志、架构日志、禁改目录。

VERIFICATION:
- 文件范围验证结果：...
- 设计文档关键字验证结果：...
- git diff --check 结果：...

BLOCKERS:
- 无 / 或列明阻塞

NEXT_ROLE:
- C Auditor
```

## 9. 完成定义

满足以下条件才算完成：

1. `TASK-080_系统管理设计.md` 已落盘。
2. 仅修改允许范围内的设计文档和工程师日志。
3. 设计文档完整覆盖第 6 节所有要求。
4. 验证命令全部执行并记录结果。
5. 未修改后端、前端、测试、控制面、审计日志、架构日志、禁改目录。
6. 未执行 commit / push / PR / tag / 生产发布。
