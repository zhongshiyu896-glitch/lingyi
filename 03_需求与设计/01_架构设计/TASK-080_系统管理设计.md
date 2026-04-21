# TASK-080 系统管理设计

- 任务编号：TASK-080
- 任务名称：系统管理设计冻结
- 文档状态：设计冻结（仅设计，不含实现）
- 版本：V1.0
- 更新时间：2026-04-21
- 继承基线：TASK-007 权限与审计基座、TASK-010 前端写入口门禁、TASK-020/TASK-020A 权限治理冻结、TASK-070G 本地封版证据

## 1. 目标与非目标

### 1.1 目标

1. 冻结系统管理模块边界，为后续 `TASK-080B~080G` 提供唯一合同。
2. 明确系统管理只读优先路线、权限动作、审计与安全要求。
3. 明确接口草案、前端入口草案与验收标准，防止实现阶段越界。

### 1.2 非目标

1. 本阶段不实现后端、前端、测试、migration。
2. 本阶段不实现系统配置写入。
3. 本阶段不实现数据字典写入。
4. 本阶段不实现权限配置写入。
5. 本阶段不实现平台管理动作。
6. 本阶段不声明远端发布、生产发布、GitHub required check 闭环或 ERPNext 生产联调完成。

## 2. 功能范围冻结

| 能力 | 本阶段定位 | 说明 |
| --- | --- | --- |
| 系统配置目录 | 只读设计 | 仅展示配置 key/分组/说明/来源/是否敏感；不展示敏感值 |
| 数据字典目录 | 只读设计 | 仅展示字典类型/编码/名称/状态/来源 |
| 系统健康检查 | 只读诊断设计 | 仅安全健康摘要；不泄露连接串、token、Cookie、password、secret、DSN |
| 任务状态 | 只读设计 | 仅展示安全摘要；不展示 payload 原文 |
| 平台状态 | 只读记录 | 可记录本地/远端/CI状态，但不得把未闭环项写成已完成 |
| 系统管理写入 | 后续任务冻结 | 写入必须另开任务，且满足权限前置、操作审计、二次确认 |

## 3. 权限动作冻结

### 3.1 本阶段定义动作

| 动作 | 用途 | 默认角色 | 前端可见性 |
| --- | --- | --- | --- |
| `system:read` | 系统管理模块入口只读能力 | System Manager | 可见 |
| `system:config_read` | 系统配置目录读取 | System Manager/运维只读角色 | 可见 |
| `system:dictionary_read` | 数据字典目录读取 | System Manager/治理只读角色 | 可见 |
| `system:diagnostic` | 系统健康诊断只读能力 | 仅 System Manager（高危） | 默认隐藏 |

### 3.2 默认冻结动作（后续不得在只读任务开放）

- `system:config_write`
- `system:dictionary_write`
- `system:platform_manage`
- `system:cache_refresh`
- `system:sync`
- `system:import`
- `system:export`

约束：`system:*` 不得由 `permission:*`、`dashboard:*`、`report:*`、`warehouse:*`、`inventory:*` 代替授权。

## 4. 后端接口草案（只读 GET）

> 仅为设计草案；实现任务中所有未知权限动作、未知资源字段、权限源不可用必须 fail closed。

### 4.1 `GET /api/system/configs/catalog`

- 所需权限：`system:read` + `system:config_read`
- 普通前端入口：允许（无权限不发请求）
- 管理员要求：否（但需有动作授权）
- 响应字段白名单：`module`、`config_key`、`config_group`、`description`、`source`、`is_sensitive`、`updated_at`
- fail closed 条件：权限源不可用、未知动作、未知 scope 字段、公司范围不匹配
- 敏感规则：不返回原始配置值；`is_sensitive=true` 仅作为标记
- 外部边界：不得访问 ERPNext 写接口

### 4.2 `GET /api/system/dictionaries/catalog`

- 所需权限：`system:read` + `system:dictionary_read`
- 普通前端入口：允许（无权限不发请求）
- 管理员要求：否
- 响应字段白名单：`dict_type`、`dict_code`、`dict_name`、`status`、`source`、`updated_at`
- fail closed 条件：权限源不可用、未知动作、未知资源字段
- 敏感规则：不返回内部凭据或脱敏前字段
- 外部边界：不得访问 ERPNext 写接口

### 4.3 `GET /api/system/health/summary`

- 所需权限：`system:read` + `system:diagnostic`
- 普通前端入口：默认不暴露
- 管理员要求：是（或显式授予 `system:diagnostic`）
- 响应字段白名单：`module`、`status`、`check_name`、`check_result`、`generated_at`
- fail closed 条件：权限源不可用、内部检查异常、未知请求参数
- 敏感规则：不得返回 token、Authorization、Cookie、password、secret、DSN、DATABASE_URL、raw headers、raw payload
- 外部边界：不得访问 ERPNext 写接口

### 4.4 `GET /api/system/tasks/status`

- 所需权限：`system:read`
- 普通前端入口：允许（无权限不发请求）
- 管理员要求：否
- 响应字段白名单：`task_key`、`task_status`、`last_updated`、`summary`
- fail closed 条件：权限源不可用、未知过滤参数
- 敏感规则：仅摘要，不返回任务 payload 明文
- 外部边界：不得访问 ERPNext 写接口

### 4.5 `GET /api/system/platform/status`

- 所需权限：`system:read`
- 普通前端入口：允许（无权限不发请求）
- 管理员要求：否
- 响应字段白名单：`local_branch`、`local_head`、`audit_state`、`ci_state`、`release_gate_state`
- fail closed 条件：权限源不可用、请求方 scope 不满足
- 敏感规则：不返回凭据、token、密钥、连接串
- 外部边界：不得访问 ERPNext 写接口

## 5. 前端入口草案

1. 建议页面路径：`/system/management`。
2. `meta.module = system`。
3. 无权限时禁止发请求，采用静默降级或 403 提示。
4. `system:diagnostic` 默认隐藏，只有管理员或显式授权可见诊断入口。
5. 页面禁止出现写入按钮：创建、更新、删除、导入、导出、同步、缓存刷新、平台管理。
6. 保留“只读可视化 + 状态摘要”模式，不允许直接触发配置发布。

## 6. 审计与安全要求

1. 诊断类访问必须安全审计或可追踪记录（至少 request_id、actor、module、action）。
2. 后续任何写入（若另开任务）必须操作审计，并记录变更前后摘要。
3. 返回数据禁止包含敏感字段：token、Authorization、Cookie、password、secret、DSN、DATABASE_URL、raw headers、raw payload。
4. 权限源不可用、未知权限动作、未知资源字段必须 fail closed。
5. 不得通过系统管理模块绕过业务模块门禁与审计链路。

## 7. 后续任务拆分建议

1. `TASK-080B`：系统配置只读目录基线。
2. `TASK-080C`：数据字典只读目录基线。
3. `TASK-080D`：系统健康检查只读诊断基线。
4. `TASK-080E`：系统管理本地收口验证。
5. `TASK-080F`：系统管理本地封版复审。
6. `TASK-080G`：系统管理本地封版白名单提交。

说明：`TASK-080B~080G` 默认不包含写入类能力；如需开放写入（配置写、字典写、平台管理），必须由 A 单独派发新任务单并走独立审计。

## 8. 验收标准（设计冻结）

1. 目标与非目标明确且不可歧义。
2. 功能范围、权限动作、接口草案、前端入口、安全与审计要求完整覆盖。
3. 明确写入冻结与高危动作冻结，不与权限治理既有模块混用授权。
4. 明确 fail closed 语义与敏感字段保护边界。
5. 后续任务拆分可直接用于 A->B 派发，不依赖隐含上下文。
