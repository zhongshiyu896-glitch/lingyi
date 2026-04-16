# Sprint2 本地封版复盘报告

- 报告版本：V1.0
- 复盘时间：2026-04-16
- 复盘角色：技术架构师
- 基线 HEAD：`1629f8ad9a3dac4ddaaf97b8201be2a2a2d0af48`
- 范围：Sprint 2 公共基座（TASK-007~010）+ P1 模块（TASK-011~012）
- 结论口径：**仅代表本地封版复盘结论，不代表生产发布完成，不代表 GitHub required check 闭环，不代表 ERPNext 生产联调完成**。

## 1. Sprint 2 总览

### 1.1 完成任务清单

| 任务 | 名称 | 当前状态 |
| --- | --- | --- |
| TASK-007 | 权限与审计统一基座 | 本地基线完成 |
| TASK-008 | ERPNext 集成 Fail-Closed Adapter | 本地基线完成 |
| TASK-009 | Outbox 公共状态机规范与模板 | 本地基线完成 |
| TASK-010 | 前端写入口门禁公共框架 | 本地基线完成 |
| TASK-011 | 销售/库存只读集成 | 本地基线完成 |
| TASK-012 | 质量管理基线 | 本地基线完成 |

### 1.2 公共基座完成情况

1. TASK-007 已形成统一权限动作、资源权限 fail-closed、安全审计/操作审计与错误信封基线。
2. TASK-008 已形成 ERPNext 统一 fail-closed 适配层，明确 timeout/5xx/401/403/404/docstatus/malformed 映射。
3. TASK-009 已形成 outbox 通用状态机模板（event_key、payload_hash、claim/lease、retry、dry-run/diagnostic）。
4. TASK-010 已形成前端写入口公共 contract engine 与模块化 wrapper，支持 fail-closed 配置校验与反向 fixture。

### 1.3 P1 业务模块完成情况

1. TASK-011 已完成销售/库存后端只读接口 + 前端只读接入 + 契约门禁接入。
2. TASK-012 已完成质量管理后端模型/迁移/接口 + 前端接入 + 契约门禁接入。

## 2. 审计轮次统计（TASK-007~012）

> 统计口径：基于 Sprint2 任务链、任务卡接力记录、交付证据文档与当前审计记录（含第175/176份及后续任务链审计结论）。

| 任务 | 审计轮次（阶段） | 主要整改点 | 最终状态 |
| --- | ---: | --- | --- |
| TASK-007 | 3 | 修复 `required_fields` 未知字段静默跳过；新增安全事件接入全局 fallback 审计 | 通过 |
| TASK-008 | 4 | docstatus 类型强转过宽（bool/float/非精确字符串）改为严格白名单 fail-closed | 通过 |
| TASK-009 | 4 | event_key 禁用字段补齐，新增运行态字段禁入（attempts/lease/status/error 等） | 通过 |
| TASK-010 | 6 | 公共 engine 配置 fail-closed（未知 scope、scannedFiles=0、fixture 强制）；移除 legacy fixture 白名单 | 通过 |
| TASK-011 | 5 | Customer 权限 fail-open 收口；销售订单详情 403/404 防枚举一致响应 | 通过 |
| TASK-012 | 5 | incoming_material/finished_goods 来源归属校验；`source_type/source_id` 纳入资源权限；diagnostic 动作与审计补齐 | 通过 |

## 3. 高危/中危问题分类复盘

### 3.1 架构设计遗漏

1. 早期任务对资源字段、状态机与 DTO 必填冻结不足，导致实现阶段多轮补口径。
2. 典型表现：source 归属字段、detail 防枚举策略、contract fixture 必填约束后置。

### 3.2 实现偏差

1. 典型偏差：fail-closed 规则实现不彻底（静默跳过、宽松强转、默认放行）。
2. 典型偏差：审计 fallback 与错误信封语义未与新增错误码同步。

### 3.3 fail-closed 缺口

1. docstatus 类型宽松会把异常输入误判为合法状态。
2. 权限源失败或资源字段缺失若未硬失败，会演化为隐性 fail-open。

### 3.4 前端门禁绕过

1. 配置层面的“假绿”风险（scope 拼写错误、扫描 0 文件、fixture 缺失）在 TASK-010B1/010D1 前是主要风险源。
2. legacy 模块 fixture 白名单导致旧模块可绕过统一门禁。

### 3.5 资源权限边界

1. Customer 维度权限空列表默认放行导致横向越权风险。
2. 详情接口若按 403/404 差异返回会泄露资源存在性。

### 3.6 审计/错误信封缺口

1. 新增安全事件未进入 `SECURITY_AUDIT_CODES` 时，fallback 审计会漏记。
2. 失败路径若未统一错误信封，易出现“业务失败但协议成功”的误导。

### 3.7 提交/基线治理问题

1. docs-only 与白名单暂存纪律需要持续执行，避免运行产物混入。
2. 本地封版链路已形成，但仍需与平台闭环链路分离管理。

## 4. 公共基座复盘

### 4.1 TASK-007（权限与审计统一基座）

- 价值：统一了动作权限、资源权限、审计事件、错误信封映射，显著降低后续模块“同类权限缺口”重复率。
- 仍需强化：新增模块接入时的“资源字段完整声明”自动校验（防漏字段）。

### 4.2 TASK-008（ERPNext fail-closed adapter）

- 价值：把 ERPNext 错误语义和 docstatus 校验统一下沉，减少模块内重复分支。
- 仍需强化：生产联调条件下的真实网络抖动、权限源波动与异常载荷验证。

### 4.3 TASK-009（Outbox 公共状态机）

- 价值：event_key、claim/lease、retry 判定、dry-run/diagnostic 具备统一模板，可复用性高。
- 仍需强化：对历史模块（TASK-002/003/004/006）的模板回迁与一致性收敛。

### 4.4 TASK-010（前端门禁公共框架）

- 价值：从“脚本散修”升级为公共 engine，fail-closed 默认策略明确。
- 仍需强化：AST 覆盖深度与动态语义检测精度持续迭代，避免新绕过面。

### 4.5 建议升级为 Sprint 3 强制前置条件

1. 任务卡必须先冻结权限动作和资源字段。
2. 所有 ERPNext 依赖必须走 fail-closed adapter。
3. 所有 outbox 必须遵循 TASK-009 状态机规范。
4. 所有前端模块必须接入 TASK-010 contract engine，fixture 不得缺省。

## 5. P1 业务模块复盘

### 5.1 TASK-011 销售/库存只读集成

- 完成范围：后端只读接口（GET）、前端只读页面与门禁、Customer 权限闭环、详情防枚举。
- 收益：验证了“只读模块 + 强门禁 + fail-closed”组合可稳定落地。

### 5.2 TASK-012 质量管理基线

- 完成范围：质量模型/迁移/状态机、后端 create/list/detail/update/confirm/cancel/statistics/export/diagnostic、前端接入与门禁。
- 收益：验证了写模块在 TASK-007~010 基座下可控推进，并保留 outbox/财务写入边界。

### 5.3 未进入生产发布与平台闭环原因

1. 本轮目标定义为本地封版，不包含生产变更窗口与上线流程。
2. GitHub required check 与 hosted runner 属平台侧闭环，需要单独任务链。
3. ERPNext 生产环境权限源、主数据与网络条件未在本轮完成实网复验。

## 6. 遗留风险清单

1. 未 push / 未配置 remote / 未创建 PR（本地基线语义）。
2. GitHub required check 未闭环。
3. ERPNext 生产联调未完成。
4. `.git/gc.log` 与 unreachable loose objects 历史维护告警需后续仓库治理。
5. 历史未跟踪目录仍存在，后续提交必须继续白名单。
6. `datetime.utcnow()` deprecation warning 仍存在。
7. `POSTGRES_TEST_DSN` 类真实数据库门禁仍需在生产前演练链路复验。
8. 生产权限矩阵（含服务账号最小权限）需在真实环境复验。

## 7. Sprint 3 建议

1. 生产联调专项：建立 ERPNext 生产联调任务链与回滚策略。
2. 平台 CI/required check 专项：补齐 hosted runner、artifact、required check 证据闭环。
3. ERPNext 权限源生产化：权限源高可用、超时、降级和审计基线。
4. 前端门禁 AST 深化：提升动态语义和跨文件别名分析能力。
5. outbox 模板回迁：将 TASK-009 规范回迁 TASK-002/003/004/006。
6. 质量管理增强：在不突破财务边界前提下补统计、规则配置、批次分析。
7. 销售/库存联动增强：只读联动升级为可审计写入口前的桥接能力。

## 8. 结论

Sprint 2 已完成“公共基座 + P1 模块”的本地封版链路，架构一致性相较 Sprint 1 明显提升。下一阶段应优先完成平台闭环与生产联调，再逐步开放更复杂的业务写入口。
