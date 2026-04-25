# TASK-020A 权限治理设计

- 任务编号：TASK-020A
- 任务名称：权限治理设计冻结
- 文档状态：待审计
- 更新日期：2026-04-17
- 适用阶段：Sprint 3 设计冻结（不含实现）

## 1. 设计目标与冻结范围

冻结权限治理设计，统一角色权限配置、用户资源权限配置、安全审计查询、操作审计查询、权限变更审批与 TASK-007 基座回迁路径，作为后续权限治理模块实现的唯一前置设计。

本任务只做设计冻结，不实现权限治理功能，不改动权限与审计代码。

## 2. 权限治理总边界（5.1）

本任务仅冻结权限治理设计。
禁止实现权限配置页面。
禁止实现权限变更接口。
禁止修改 `permission_service.py`。
禁止修改 `permissions.py`。
禁止修改安全审计或操作审计代码。
禁止绕过 TASK-007 权限与审计统一基座。
TASK-014C 未完成前，不允许进入任何真实平台联调或生产发布。

补充边界：

冻结对象（本轮必须覆盖）：

1. 权限动作注册表。
2. 角色权限矩阵。
3. 用户资源权限配置。
4. 权限变更审批。
5. 安全审计查询。
6. 操作审计查询。
7. 权限诊断。
8. TASK-007 基座回迁路径。

1. 本文档不代表权限治理功能已实现。
2. 本文档不代表 Hosted Runner required checks / Branch Protection 已闭环。
3. 权限治理任何写能力必须单独任务、单独审计、单独放行。

## 3. 角色权限配置设计（5.2）

### 3.1 角色模型

1. 角色由“业务角色 + 管理角色 + 审计角色 + 系统角色”组成。
2. 角色定义必须与动作权限解耦，角色仅承载动作集合与资源范围模板。
3. 服务账号角色单独建模，禁止复用人工用户角色。

### 3.2 动作权限格式

统一格式：`module:action`。

约束：

1. `module` 使用稳定模块名（如 `permission`、`report`、`finance`）。
2. `action` 使用明确语义（read/create/update/export/diagnostic 等）。
3. 禁止模糊动作（如 `all`、`*`）直接赋予普通角色。

### 3.3 权限分类

1. 读权限：`*:read`。
2. 写权限：`*:create`、`*:update`、`*:confirm`、`*:cancel`。
3. 管理权限：`*:manage`、`*:role_update`。
4. 导出权限：`*:export`。
5. 干运行动作：`*:dry_run`。
6. 诊断权限：`*:diagnostic`（默认高危）。

### 3.4 角色继承策略

1. 允许受控继承（子角色继承父角色只读能力）。
2. 高危动作不可被自动继承，必须显式授权。
3. 继承链禁止循环依赖。

### 3.5 角色互斥规则

1. 审批角色与提交角色可配置互斥（如高危权限变更场景）。
2. 审计只读角色与高危运维角色默认互斥。
3. 紧急角色与常规角色并存时必须带有效期。

### 3.6 高危权限审批规则

1. `*:diagnostic`、`permission:approval`、`permission:rollback` 等归类为高危。
2. 高危权限必须审批后生效。
3. 高危权限默认要求双人审批。

### 3.7 生效时间与回滚

1. 权限变更支持“立即生效”与“定时生效”。
2. 变更必须保留版本号与生效区间。
3. 回滚必须可定位到具体版本并可追溯审批记录。

### 3.8 导入/导出边界

1. 角色权限配置允许模板化导入/导出（仅后续实现任务开放）。
2. 导入必须校验 schema、动作白名单与资源字段合法性。
3. 导出必须脱敏并受 `permission:export` 限制。

### 3.9 数据库直改禁令

1. 禁止直接编辑数据库绕过审批流。
2. 若紧急修复需 DB 介入，必须总调度批准并补全审计记录。

## 4. 用户资源权限配置设计（5.3）

资源 scope 覆盖：

- `company`
- `item_code`
- `supplier`
- `customer`
- `warehouse`
- `work_order`
- `sales_order`
- `purchase_order`
- `bom_id`
- `account`
- `cost_center`
- `batch_no`
- `serial_no`

| 资源字段 | 数据隔离语义 | 动作鉴权语义 | 空值处理 | 未知字段策略 | 权限源不可用策略 | 审计记录要求 |
|---|---|---|---|---|---|---|
| company | 公司级强隔离 | 所有动作先校验 company | 空值拒绝 | fail-closed | fail-closed | 记录 action+scope |
| item_code | 物料级隔离 | 物料相关读写必须校验 | 空值表示不过滤（受 company 约束） | fail-closed | fail-closed | 记录 item_code 摘要 |
| supplier | 供应商级隔离 | 采购/外发/应付校验 | 空值表示不过滤 | fail-closed | fail-closed | 记录 supplier |
| customer | 客户级隔离 | 销售/应收校验 | 空值表示不过滤 | fail-closed | fail-closed | 记录 customer |
| warehouse | 仓库级隔离 | 库存相关动作校验 | 空值表示不过滤 | fail-closed | fail-closed | 记录 warehouse |
| work_order | 工单级隔离 | 生产与质量动作校验 | 空值表示不过滤 | fail-closed | fail-closed | 记录 work_order |
| sales_order | 订单级隔离 | 销售与利润动作校验 | 空值表示不过滤 | fail-closed | fail-closed | 记录 sales_order |
| purchase_order | 订单级隔离 | 采购动作校验 | 空值表示不过滤 | fail-closed | fail-closed | 记录 purchase_order |
| bom_id | BOM 级隔离 | BOM 读写动作校验 | 空值拒绝（BOM 特定动作） | fail-closed | fail-closed | 记录 bom_id |
| account | 科目隔离 | 财务查询动作校验 | 空值表示不过滤 | fail-closed | fail-closed | 记录 account |
| cost_center | 成本中心隔离 | 财务查询动作校验 | 空值表示不过滤 | fail-closed | fail-closed | 记录 cost_center |
| batch_no | 批次隔离 | 库存追溯动作校验 | 空值表示不过滤 | fail-closed | fail-closed | 记录 batch_no |
| serial_no | 序列号隔离 | 库存追溯动作校验 | 空值表示不过滤 | fail-closed | fail-closed | 记录 serial_no |

通用规则：

1. 未知资源字段不得静默忽略，必须 fail-closed。
2. 权限源不可用不得降级为 unrestricted。
3. 审计源不可用必须 fail-closed，不得继续放行高危动作。
4. 资源权限变更必须写操作审计与安全审计（按场景）。

## 5. 权限变更审批流程（5.4）

### 5.1 发起与审批职责

1. 发起人：权限管理员（最小集合）。
2. 审批人：安全管理员/架构师授权角色。
3. 高危权限默认双人审批。

### 5.2 审批要素

1. 变更必须填写原因。
2. 高危权限必须设置有效期。
3. 可支持批量导入，但仅限受控模板与审批后执行。

### 5.3 生效与拒绝

1. 审批通过后按生效时间发布变更版本。
2. 审批拒绝必须记录拒绝原因、审批人、审批时间。
3. 拒绝单据保留审计链，不可删除。

### 5.4 过期与紧急权限

1. 到期权限自动回收，并写操作审计。
2. 紧急权限需最短有效期、强审计、到期强制回收。
3. 紧急权限申请与常规审批链分离，必须保留完整证据。

## 6. 安全审计日志查询设计（5.5）

安全审计与操作审计必须分轨，禁止混表混语义。

### 6.1 必须覆盖事件

- `401` 未认证
- `403` 禁止
- 资源越权
- 权限源不可用
- ERPNext 不可用
- internal API 访问
- request_id rejected
- unknown resource scope
- sensitive output blocked

### 6.2 查询设计要素

1. 查询条件：时间范围、事件类型、模块、用户、request_id、resource scope。
2. 查询权限：仅 `permission:audit_read` 或更高权限可访问。
3. 字段脱敏：token/cookie/authorization/password/secret 必须脱敏或不落库。
4. 导出边界：仅允许脱敏导出，且需 `permission:export`。
5. 留存周期：按合规策略配置（建议 180 天或更长策略化配置）。
6. 防篡改：日志写入后不可覆盖，仅追加；支持 hash/签名或等价校验链。
7. 异常峰值告警：同类安全事件短时激增需触发告警。
8. 安全审计导出必须防 CSV 公式注入并记录导出审计。

## 7. 操作审计日志查询设计（5.6）

### 7.1 必须覆盖事件

- create
- update
- confirm
- cancel
- export
- dry-run
- diagnostic
- permission change
- approval
- rollback

### 7.2 查询设计要素

1. 必须记录业务关联 ID（变更单号/审批单号/角色版本号）。
2. 记录操作人、操作时间、模块、动作。
3. 变更前后值需脱敏（敏感字段仅保留摘要或 hash）。
4. 查询权限必须独立控制，不得与普通 read 混用。
5. 导出权限独立校验并写导出审计。
6. 留存周期与安全审计协同配置。
7. 防篡改与追加写策略与安全审计一致。

## 8. TASK-007 基座回迁路径（5.7）

### 8.1 当前 TASK-007 基座能力清单

1. 统一动作权限命名规范。
2. 统一资源权限校验入口。
3. fail-closed 错误码与错误信封。
4. 安全审计与操作审计双轨。
5. request_id 标准化与拒绝策略。

### 8.2 能力归属策略

1. 继续保持为公共服务能力：动作权限校验、资源校验、安全审计、操作审计、错误信封。
2. 可迁入权限治理模块的能力：角色编排、审批编排、权限版本管理、批量导入导出编排。
3. 禁止重复实现：permission_service 核心鉴权逻辑、公共错误码、审计落库核心逻辑。

### 8.3 回迁顺序

1. 梳理能力边界与依赖映射。
2. 抽离“治理编排层”并保持调用 TASK-007 公共能力。
3. 接入审批流与版本机制。
4. 补齐回归测试与审计验证。
5. 冻结旧入口并完成迁移切换。

### 8.4 回迁验证要求

1. 未知 resource scope 仍 fail-closed。
2. 权限源不可用仍 fail-closed。
3. 安全审计与操作审计事件不回退。
4. 错误信封结构不回退。

### 8.5 兼容与回滚策略

1. 迁移期间采用双轨兼容（旧入口只读/新入口治理编排）。
2. 发现 P1/P2 问题可回滚到旧入口，并保留审计证据。
3. 回滚动作必须审批并记录操作审计。

### 8.6 回迁审计要求

1. 回迁前设计审计。
2. 回迁实现审计。
3. 回迁提交审计。
4. 任一阶段不通过即停止推进。

## 9. 前端门禁要求（5.8）

1. 权限治理页面属于高危管理界面。
2. 普通用户不得看到权限治理菜单。
3. `permission:diagnostic` 不得暴露给普通前端菜单。
4. 前端禁止直连权限源或 ERPNext。
5. 前端禁止裸 `fetch/axios` 绕过 API client。
6. 权限配置导出必须防公式注入。
7. 必须接入 TASK-010 前端写入口门禁公共框架。
8. 必须提供 positive / negative fixtures。
9. 无权限分支必须前置 return，不得发起请求。

## 10. 权限动作注册表与命名（5.9）

至少覆盖：

- `permission:read`
- `permission:export`
- `permission:role_create`
- `permission:role_update`
- `permission:role_disable`
- `permission:user_scope_update`
- `permission:approval`
- `permission:rollback`
- `permission:audit_read`
- `permission:diagnostic`

动作命名约束：

1. 必须遵循 `module:action`。
2. 新增动作需先审计后落地。
3. 禁止以 `permission:manage_all` 等宽泛动作替代细粒度动作。

## 11. fail-closed 统一拒绝条件（5.10）

下列场景必须统一拒绝，不得降级放行：

1. 未知动作。
2. 未知资源字段。
3. 权限源不可用。
4. 审计源不可用。
5. 高危权限审批状态不明。

## 12. 三层能力冻结统一矩阵（5.11）

| 冻结对象/动作 | 只读能力 | 候选写能力 | 生产写能力 |
| --- | --- | --- | --- |
| 权限动作注册表 | 可查询动作定义、模块映射、历史版本 | 可提出新增/收敛动作方案（仅设计） | 未放行 |
| 角色权限矩阵 | 可查询角色与动作映射 | 可提出角色增改停用方案（仅设计） | 未放行 |
| 用户资源权限配置 | 可查询 scope 配置与命中结果 | 可提出 scope 调整方案（仅设计） | 未放行 |
| 权限变更审批 | 可查询审批流与审批记录 | 可提出审批编排与回滚方案（仅设计） | 未放行 |
| 安全审计查询 | 可查询 401/403/越权/权限源异常等事件 | 不适用 | 未放行 |
| 操作审计查询 | 可查询 create/update/confirm/cancel/export/diagnostic/rollback 轨迹 | 不适用 | 未放行 |
| 权限诊断 `permission:diagnostic` | 仅管理员/内部受控可见 | 可提出诊断范围与脱敏策略（仅设计） | 未放行 |
| Purchase/Production/Warehouse 业务资源字段授权（`company/item_code/supplier/customer/warehouse/work_order/sales_order/purchase_order/bom_id/account/cost_center/batch_no/serial_no`） | 可做只读鉴权与查询过滤 | 可提出写前校验与审批门禁方案（仅设计） | 未放行 |

统一约束：

1. 候选写能力不等于允许实现。
2. 生产写能力当前全部冻结。
3. 未经后续单独任务与单独审计，不得进入代码实现。

## 13. 生产发布前置条件（5.12）

1. `TASK-014C` 完成。
2. Hosted Runner required checks 平台闭环。
3. Branch Protection 已配置。
4. TASK-007 基座补审已通过。
5. 权限治理设计审计通过。
6. 权限治理实现必须单独任务、单独审计、单独放行。
7. 高危权限变更必须经过总调度批准。

## 14. 结论边界与下一步门禁

1. 本文档仅冻结权限治理设计，不包含权限治理实现。
2. 本文档不代表平台 required checks 已闭环。
3. 本文档不代表生产联调完成。
4. 本文档不代表生产发布完成。
5. `TASK-020A` 通过后仅允许进入 `TASK-020B` 系统管理设计冻结。
6. 不允许直接进入任何权限治理实现任务。
7. 不允许直接进入联调、提测、上线或生产发布。
