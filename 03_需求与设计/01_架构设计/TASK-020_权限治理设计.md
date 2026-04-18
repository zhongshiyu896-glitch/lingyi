# TASK-020 权限治理设计

- 任务编号：TASK-020
- 任务名称：权限治理与系统管理设计冻结
- 文档版本：V1.0
- 日期：2026-04-17
- 状态：待审计

## 1. 目标

冻结权限治理与系统管理设计，明确权限配置、角色矩阵、审计查询、系统配置、字典、健康检查的范围与禁止事项。

## 2. 总原则

1. 权限治理必须基于 TASK-007 权限与审计统一基座。
2. 所有未知权限动作、未知资源字段、权限源不可用均 fail closed。
3. 权限配置变更必须操作审计。
4. 安全事件查询不得泄露敏感信息。
5. 系统管理功能不得绕过业务模块的审计与门禁。

## 3. 权限治理范围

| 功能 | 本阶段定位 | 说明 |
|---|---|---|
| 权限动作注册表 | 设计 | 统一动作命名与分类 |
| 角色矩阵 | 设计 | 角色到权限动作映射 |
| 资源权限 | 设计 | company/customer/supplier/warehouse 等 |
| 审计查询 | 设计 | 安全审计/操作审计查询 |
| 权限诊断 | 设计 | 管理员诊断，必须审计 |
| 权限配置写入 | 后续任务 | 默认冻结 |

## 4. 权限动作分类

| 分类 | 示例 | 管控要求 |
|---|---|---|
| read | `module:read` | 可授予业务角色 |
| export | `module:export` | 必须操作审计 |
| create/update/cancel/confirm | 写动作 | 必须权限前置 + 操作审计 |
| diagnostic | 诊断 | 默认管理员，必须审计 |
| internal/worker | 内部 | 前端 denylist，禁止普通 token |
| admin | 管理 | 仅系统管理员 |

## 5. 角色矩阵建议

| 角色 | 说明 | 默认权限方向 |
|---|---|---|
| System Admin | 系统管理员 | admin/diagnostic/config |
| Finance Manager | 财务经理 | finance/factory statement/style profit |
| Sales Manager | 销售经理 | sales inventory/customer 只读 |
| Production Manager | 生产经理 | production/quality/warehouse 相关 |
| Purchase Manager | 采购经理 | purchase/supplier 相关 |
| Viewer | 只读观察者 | 最小只读，禁止导出默认开放 |

## 6. 资源字段注册

必须纳入统一注册表：

| 字段 | 说明 |
|---|---|
| company | 最高优先级资源边界 |
| customer | 客户权限 |
| supplier | 供应商权限 |
| warehouse | 仓库权限 |
| item_code | 物料/款式 |
| sales_order | 销售订单 |
| work_order | 生产工单 |
| source_type/source_id | 来源对象 |
| account/cost_center | 财务资源 |

未知字段不得静默忽略，必须 fail closed。

## 7. 审计查询设计

| 查询 | 权限 | 说明 |
|---|---|---|
| 安全审计列表 | `audit:security_read` | 401/403/权限源异常等 |
| 操作审计列表 | `audit:operation_read` | 创建/确认/取消/导出等 |
| 审计详情 | `audit:read` | 单条详情，敏感字段脱敏 |
| 审计导出 | `audit:export` | 必须防 CSV 公式注入 |
| 审计诊断 | `audit:diagnostic` | 管理员，必须审计 |

## 8. 系统管理范围

| 功能 | 本阶段定位 | 边界 |
|---|---|---|
| 系统配置 | 设计 | 禁止直接改生产配置 |
| 字典管理 | 设计 | 写入需审计 |
| 健康检查 | 设计 | 不泄露内部连接串 |
| 任务状态 | 设计 | 不展示敏感 payload |
| CI/平台状态 | 只读记录 | 不声明未闭环项已完成 |

## 9. 前端要求

1. 权限治理页面必须接入 TASK-010 公共门禁。
2. internal/worker 动作必须 denylist。
3. diagnostic 默认隐藏。
4. 无权限分支不得发请求。
5. 配置写入按钮必须有权限绑定与二次确认。

## 10. 后端要求

1. 所有管理接口必须权限前置。
2. 资源权限检查失败必须安全审计。
3. 配置变更必须操作审计。
4. 错误信封统一 `{code,message,data}`。
5. 敏感信息必须脱敏。

## 11. 审计关注点

1. 是否存在 hard-coded allow。
2. 是否权限源不可用仍放行。
3. 是否未知 resource scope 静默跳过。
4. 是否审计查询泄露 token/password/DSN。
5. 是否通过系统管理绕过业务模块禁止项。

## 12. 结论

本设计建议进入 TASK-020A 审计。审计通过后，仅允许继续系统管理设计冻结，不允许直接实现权限配置写入。
