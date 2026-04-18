# Sprint 2 审计缺口补审计划

- 版本：V1.0
- 更新时间：2026-04-16
- 作者：技术架构师
- 状态：待审计
- 决策路径：路径 C（标注现状，继续 Sprint 3；生产发布前补审）

## 一、补审目标

本计划用于补齐 Sprint 2 中 TASK-008~012 的审计流程缺口，并补充 TASK-007 实现层审计确认。补审完成前，Sprint 2 代码只能维持“本地封版 + 审计阻塞”状态，不得进入生产发布、ERPNext 生产联调或对外完成声明。

## 二、补审优先级矩阵

| 优先级 | 模块 | 代码提交 SHA | 安全关键性 | Sprint 3 依赖 | 补审紧迫度 |
|---|---|---|---|---|---|
| 1 | TASK-008 ERPNext Fail-Closed Adapter | e468231 | 高 | TASK-015 ERPNext 联调 | 极高 |
| 2 | TASK-009 Outbox 公共状态机 | a5e6414 | 高 | TASK-015 / TASK-018 | 极高 |
| 3 | TASK-010 前端写入口门禁框架 | 8575b48 | 高 | 所有前端模块 | 高 |
| 4 | TASK-007 权限与审计统一基座 | fe3f5b7 | 极高 | TASK-016 财务管理 | 高 |
| 5 | TASK-011 销售/库存只读集成 | 434c9df / a50ac03 | 中 | TASK-015 | 中 |
| 6 | TASK-012 质量管理基线 | 007aea9 / f97d580 | 中 | TASK-015 | 中 |

说明：TASK-007 已通过设计审计（第 175-176 份），本计划补充其实现代码审计与提交链路复核。

## 三、模块补审要点

### 3.1 TASK-008 ERPNext Fail-Closed Adapter

补审范围：
- 设计文档：`TASK-008_ERPNext集成FailClosed规范.md`
- 实现代码：`erpnext_fail_closed_adapter.py`、相关异常与错误码
- 测试：`test_erpnext_fail_closed_adapter.py`

审计要点：
1. ERPNext timeout / 401 / 403 / 5xx 是否 fail closed。
2. docstatus 缺失、非法类型、非法值是否 fail closed。
3. malformed response 是否 fail closed。
4. 是否禁止 `detail=str(exc)` 泄露。
5. 是否禁止 200 + 空数据伪成功。

通过标准：高危 0，中危 ≤ 1，所有 P1/P2 必须整改复审。

### 3.2 TASK-009 Outbox 公共状态机

补审范围：
- 设计文档：`TASK-009_Outbox公共状态机规范.md`
- 实现代码：`outbox_state_machine.py`
- 测试：`test_outbox_state_machine.py`

审计要点：
1. `event_key` 是否禁止运行态字段。
2. `idempotency_key` 与 `event_key` 职责是否分离。
3. claim / lease / retry / dead 状态机是否安全。
4. 是否明确 worker 外调前置校验。
5. 是否保留 dry-run / diagnostic 审计要求。

通过标准：高危 0，中危 ≤ 1，event_key 或 lease 问题必须整改。

### 3.3 TASK-010 前端写入口门禁框架

补审范围：
- 设计文档：`TASK-010_前端写入口门禁公共框架设计.md`
- 实现代码：`frontend-contract-engine.mjs` 与各 wrapper
- 测试：`test-frontend-contract-engine.mjs`、各模块 contract tests

审计要点：
1. unknown scanScopes 是否 fail closed。
2. scannedFiles=0 是否 fail closed。
3. fixture.positive / fixture.negative 是否强制。
4. style-profit / factory-statement / sales-inventory / quality 门禁是否不回退。
5. dynamic import / Worker / runtime injection / CSV 公式注入等高危绕过是否覆盖。

通过标准：高危 0，中危 ≤ 1，前端绕过类问题必须整改。

### 3.4 TASK-007 权限与审计统一基座实现

补审范围：
- 设计文档：`TASK-007_权限与审计统一基座设计.md`
- 实现代码：`permission_service.py`、`permissions.py`、`main.py`、`error_codes.py`
- 测试：权限、审计、错误信封相关测试

审计要点：
1. 未知 resource scope 是否 fail closed。
2. 权限源不可用是否 fail closed。
3. 安全审计 fallback 是否覆盖新增安全事件。
4. 操作审计与安全审计是否脱敏。
5. 错误信封是否统一。

通过标准：高危 0，中危 ≤ 1，权限 fail-open 必须整改。

### 3.5 TASK-011 销售/库存只读集成

补审范围：
- 设计文档：`TASK-011_销售库存只读集成设计.md`
- 后端代码：sales_inventory router/schema/service/adapter
- 前端代码：sales_inventory API/views/router/permission/contracts
- 测试：sales inventory API / permissions / contracts

审计要点：
1. 是否全链路只读。
2. Customer 资源权限是否 fail closed。
3. 销售订单详情是否防枚举。
4. ERPNext SLE / SO / DN malformed 是否 fail closed。
5. 前端是否禁止写入口、diagnostic、ERPNext 直连。

通过标准：高危 0，中危 ≤ 1，任何写入口或资源枚举问题必须整改。

### 3.6 TASK-012 质量管理基线

补审范围：
- 设计文档：`TASK-012_质量管理基线设计.md`
- 后端代码：quality model/schema/service/router/migration
- 前端代码：quality API/views/router/permission/contracts
- 测试：quality API / model / contract tests

审计要点：
1. 来源归属校验是否完整。
2. confirmed/cancelled 状态机是否正确。
3. ERPNext 主数据校验是否 fail closed。
4. 是否无 ERPNext 写入、无 outbox、无财务写入。
5. 前端写入口是否绑定权限且 diagnostic 不暴露。

通过标准：高危 0，中危 ≤ 1，来源归属和状态机问题必须整改。

## 四、补审流程设计

1. 审计官按优先级从 TASK-008 开始补审。
2. 每个模块先审设计文档，再审代码实现，再审测试与提交证据。
3. 每个模块输出正式审计意见书。
4. 如发现高危或中危超标，工程师必须执行对应整改任务。
5. 整改完成后审计官复审。
6. 模块补审通过后，在本计划或审计日志中标记闭环。

## 五、补审与 Sprint 3 并行约束

1. 补审完成前，TASK-015（ERPNext 生产联调）禁止开始。
2. TASK-014（平台 CI）可与补审并行，因为不依赖业务代码。
3. TASK-013C（串行审计模板）可与补审并行，因为是元任务。
4. TASK-016 及之后的 P0 业务模块必须在补审通过后开始。
5. 若补审发现 TASK-008~010 公共基座高危问题，所有依赖该基座的新任务暂停。

## 六、补审时间估算

| 模块 | 设计文档审 | 代码审 | 整改 | 复审 | 合计 |
|---|---:|---:|---:|---:|---:|
| TASK-007 实现 | 0.5 天 | 1 天 | 0.5-1 天 | 0.5 天 | 2-3 天 |
| TASK-008 | 0.5 天 | 1 天 | 0.5-1 天 | 0.5 天 | 2-3 天 |
| TASK-009 | 0.5 天 | 1 天 | 0.5-1 天 | 0.5 天 | 2-3 天 |
| TASK-010 | 0.5 天 | 1.5 天 | 1-2 天 | 0.5 天 | 3-4.5 天 |
| TASK-011 | 0.5 天 | 1.5 天 | 1-2 天 | 0.5 天 | 3-4.5 天 |
| TASK-012 | 0.5 天 | 1.5 天 | 1-2 天 | 0.5 天 | 3-4.5 天 |

## 七、高危问题整改路径

1. 审计官输出 finding，标明 P1/P2/P3。
2. 架构师下发对应整改任务单。
3. 工程师只修复指定范围。
4. 审计官复审。
5. 复审通过后才允许继续下一个补审模块。

## 八、补审通过标准

1. 高危问题数必须为 0。
2. 中危问题数必须 ≤ 1；超过则必须整改。
3. 低危问题可接受，但必须记录风险和后续处理建议。
4. 安全关键路径不得有未解释风险。
5. 所有补审结论必须写入审计记录和审计官会话日志。

## 九、生产发布前置条件

1. TASK-007~012 补审全部通过。
2. GitHub required check 平台闭环完成。
3. ERPNext 生产联调完成。
4. 敏感信息扫描通过。
5. 总调度确认发布窗口。

## 十、当前结论

Sprint 2 可以继续保持“本地封版 + 审计阻塞”标注。Sprint 3 可继续规划和平台治理任务，但生产联调和 P0 业务扩展必须等待补审闭环。
