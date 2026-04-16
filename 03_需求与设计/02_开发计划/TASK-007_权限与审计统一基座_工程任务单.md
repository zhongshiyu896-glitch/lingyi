# TASK-007 权限与审计统一基座_工程任务单

- 任务编号：TASK-007
- 任务名称：权限与审计统一基座
- 角色：工程师
- 优先级：P1
- 前置依赖：Sprint2_架构规范.md 已审计确认
- 更新时间：2026-04-16 09:06
- 作者：技术架构师

════════════════════════════════════════════════════════════
【任务目标】
统一后端动作权限、资源权限、安全审计、操作审计和错误信封，为 Sprint 2 所有 P1 模块提供公共权限基线。

【任务范围】

1. 梳理现有实现
   - 梳理 `permission_service.py`、各模块 `permissions.py` 的现有权限逻辑。
   - 梳理 TASK-001~006 中的安全审计、操作审计实现。
   - 梳理现有错误信封（error envelope）格式。

2. 输出权限动作命名规范
   - 格式：`module:action`，如 `bom:read`、`bom:write`、`subcontract:confirm`。
   - 列出 Sprint 2 P1 模块所有预期动作。
   - 区分读、写、管理、导出、干运行、诊断、worker 动作。

3. 输出资源权限字段规范
   - 字段类型：`company / item_code / supplier / warehouse / work_order / sales_order / bom_id`。
   - 说明每种资源权限的过滤语义：数据隔离 vs 动作鉴权。
   - 列出 TASK-001~006 中需要回迁公共规范的点。

4. 输出安全审计事件规范
   - 事件类型：401 未认证、403 禁止、资源越权、权限源不可用、internal API 访问。
   - 日志字段：timestamp / user / event_type / resource / ip / request_id。
   - 禁止记录字段：Authorization / Cookie / Token / Secret / 密码。

5. 输出操作审计事件规范
   - 事件类型：create / update / confirm / cancel / export / dry-run / diagnostic。
   - 记录变更前后值（脱敏后）、操作人、时间戳、业务关联 ID。

6. 输出 fail-closed 错误码表
   - 权限源不可用：`PERMISSION_SOURCE_UNAVAILABLE` → HTTP 503。
   - 资源不存在：`RESOURCE_NOT_FOUND` → HTTP 404。
   - 资源越权：`RESOURCE_ACCESS_DENIED` → HTTP 403。
   - ERPNext 依赖不可用：`EXTERNAL_SERVICE_UNAVAILABLE` → HTTP 503 + 业务层阻断。
   - 禁止返回伪装成功的 `200 + 空数据`。

【涉及文件】

新建：
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-007_权限与审计统一基座设计.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-007_权限与审计统一基座_工程任务单.md

禁止修改：
- /Users/hh/Desktop/领意服装管理系统/06_前端/**
- /Users/hh/Desktop/领意服装管理系统/07_后端/**
- /Users/hh/Desktop/领意服装管理系统/.github/**
- /Users/hh/Desktop/领意服装管理系统/02_源码/**

【执行步骤】

1. 读取前置规范：
   - /Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/Sprint2_架构规范.md
   - /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/Sprint1_复盘报告.md

2. 读取 Sprint 1 关键审计记录：
   - /Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录.md
   - /Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录/审计官会话日志.md

3. 只做文档级交付，不写业务代码。

4. 对照 TASK-001~006 逐项补齐回迁清单：
   - BOM 权限与资源鉴权。
   - 外发加工供应商/Item/Company 权限。
   - 工票 service account 与 internal worker 权限。
   - 生产计划 Work Order outbox 权限。
   - 款式利润只读/创建边界与前端门禁。
   - 加工厂对账 payable worker、export、active outbox 防重。

5. 输出交付报告小节：
   - 现状梳理结论。
   - 规范草案。
   - 遗留清单。

【审计前置要求】

1. 审计官先审本文档和任务单，不得直接进入代码实现。
2. 审计重点包括：
   - 权限动作命名是否覆盖 Sprint 2 P1 模块。
   - 资源权限字段是否覆盖 TASK-001~006 的高危来源。
   - 安全审计是否覆盖 401/403/资源越权/权限源不可用/internal API。
   - 操作审计是否覆盖 dry-run/diagnostic/export/worker。
   - fail-closed 错误码是否禁止伪装成功。
   - 是否明确 static 权限源仅为开发临时方案。
3. 审计通过后，才允许拆分 TASK-007B 进入工程实现。

【验收标准】

□ 权限动作命名表完成，格式统一。
□ 资源权限字段表完成，隔离语义清晰。
□ 安全审计事件表完成。
□ 操作审计事件表完成。
□ fail-closed 错误码表完成。
□ 已列出 TASK-001~006 中需要回迁公共规范的点及回迁路径。
□ 文档包含：现状梳理结论 + 规范草案 + 遗留清单。
□ 文档可直接作为 TASK-008~012 的前置引用。
□ 未修改前端、后端、.github、02_源码。
□ 未声明生产发布完成、GitHub required check 闭环或 ERPNext 生产联调完成。

【禁止事项】

- 禁止写业务代码。
- 禁止修改后端权限实现。
- 禁止修改前端门禁脚本。
- 禁止修改数据库迁移。
- 禁止 push。
- 禁止配置 remote。
- 禁止创建 PR。
- 禁止将本任务描述为生产发布完成。

【完成后回复格式】

```text
TASK-007 执行完成。
输出文件：
1. /03_需求与设计/01_架构设计/TASK-007_权限与审计统一基座设计.md
2. /03_需求与设计/02_开发计划/TASK-007_权限与审计统一基座_工程任务单.md
结论：待审计 / 通过 / 不通过
是否写业务代码：否
是否修改前端/后端/.github/02_源码：否
```

════════════════════════════════════════════════════════════
