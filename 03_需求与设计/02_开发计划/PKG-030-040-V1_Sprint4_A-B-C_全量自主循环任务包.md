# PKG-030-040-V1 Sprint 4 A→B→C 全量自主循环任务包

- 输出角色：A Technical Architect（TASK-025A 续）
- 输出时间：2026-04-19 16:20 CST+8
- 包编号：PKG-030-040-V1
- 循环模式：默认 A→B→C 连续推进；遇到 `BLOCKED` 按 `AUTO_LOOP_PROTOCOL` 暂停并写入 `INTERVENTION_QUEUE`；用户在换线、全包完成或协议 stop condition 触发时介入

## 1. 任务包概览

| 任务编号 | 模块 | 任务名称 | 预期循环 | 计划审计编号 |
| --- | --- | --- | --- | --- |
| TASK-030C | 质量管理 | 质检单确认/取消状态机重启 | A→B→C ×1 | #302 |
| TASK-030D | 质量管理 | ERPNext 库存写入联动（Outbox） | A→B→C ×2 | #304 |
| TASK-030E | 质量管理 | 质量统计分析增强 | A→B→C ×1 | #306 |
| TASK-030F | 质量管理 | 质量导出 PDF / Excel 增强 | A→B→C ×1 | #308 |
| TASK-030G | 质量管理 | 来料检验自动触发 | A→B→C ×1 | #310 |
| TASK-040A | 销售库存 | 销售库存只读聚合增强 | A→B→C ×1 | #312 |
| TASK-040B | 销售库存 | 库存过滤权限增强 | A→B→C ×1 | #314 |
| TASK-040C | 销售库存 | 跨模块视图 | A→B→C ×1 | #316 |

说明：上表“计划审计编号”是本任务包的预期顺序编号，不代表当前已经存在正式审计结论。

## 2. 当前激活策略

1. 当前主线仅激活 `TASK-030C`。
2. `TASK-030D ~ TASK-040C` 作为已登记后续任务，等待前置门禁满足后再逐张激活。
3. 所有后续任务均沿用：
   - 不 push / remote / PR / 生产发布
   - 高风险任务先过 C 任务单复核，再派 B
   - 任一 `BLOCKED` 一经触发，立即按 `AUTO_LOOP_PROTOCOL` 写入 `INTERVENTION_QUEUE` 并暂停自动循环
   - `NEEDS_FIX` 才允许继续 A→B→C 修复循环；不得把 `BLOCKED` 误当作可直接交由 B 修复的状态

## 3. 链路顺序

### 3.1 质量管理链

1. `TASK-030C`：质检单确认 / 取消状态机重启
2. `TASK-030D`：ERPNext 库存写入联动（Outbox）
3. `TASK-030E`：质量统计分析增强
4. `TASK-030F`：质量导出 PDF / Excel 增强
5. `TASK-030G`：来料检验自动触发

### 3.2 销售库存链

1. `TASK-040A`：销售库存只读聚合增强
2. `TASK-040B`：库存过滤权限增强
3. `TASK-040C`：跨模块视图

## 4. 换线规则

| 场景 | 动作 |
| --- | --- |
| `TASK-030A~030G` 全部完成 | 用户 / 总调度决定是否进入 Sprint 5 或继续 Sprint 4 收尾 |
| `TASK-040A~040C` 全部完成 | Sprint 4 全包完成，用户 / 总调度决定是否进入正式封版 |
| 任一任务 C 审计返回 `BLOCKED` | A 立即按协议写入 `INTERVENTION_QUEUE`，将 `LOOP_STATE` 切到 `BLOCKED`，暂停自动循环，等待用户 / 总调度处理 |
| 任一任务 C 审计返回 `NEEDS_FIX` | A 修订任务单或安排 B fix pass 后继续；不得把 `BLOCKED` 降级为 `NEEDS_FIX` |
| 同一失败重复两次、fix pass 用尽或验证无法收敛 | A 按 `AUTO_LOOP_PROTOCOL` 升级为 `BLOCKED` 并请求用户 / 总调度介入 |

## 5. 当前激活任务说明

- 当前由 A 正式激活：`TASK-030C`
- 当前共享控制面：`READY_FOR_AUDIT / C Auditor / TASK-030C`
- 当前不放行 B；需先由 C 对 `TASK-030C` 工程任务单做正式复核

## 6. 未来任务说明

### 6.1 TASK-030D
- 前置：`TASK-030C` 实现审计通过后再激活
- 方向：confirmed 后 Outbox 异步写 ERPNext Stock Entry
- 约束：不得同步直连 ERPNext；失败不回滚质检单 confirmed 状态

### 6.2 TASK-030E
- 前置：`TASK-030C` 实现审计通过后再激活
- 方向：质量统计多维增强与趋势分析
- 约束：继续排除 cancelled，保持 company 范围过滤

### 6.3 TASK-030F
- 前置：`TASK-030C` 实现审计通过后再激活
- 方向：导出增强（csv/xlsx/pdf）
- 约束：由后端生成导出文件，不在前端本地拼装

### 6.4 TASK-030G
- 前置：优先等待 `TASK-030D` 完成后再决定是否激活
- 方向：Purchase Receipt 触发草稿质检单自动创建
- 约束：只自动创建 draft，不自动 confirm

### 6.5 TASK-040A~040C
- 前置：质量管理链至少完成 `TASK-030C`，再切入销售库存新方向
- 设计依据：`TASK-011_销售库存只读集成设计.md`
- 原则：优先增强现有销售库存只读基线，不盲目新建并行模块
