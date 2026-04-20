# TASK-030E 质量统计分析增强 工程任务单

## 1. 基本信息

- 任务编号：TASK-030E
- 任务名称：质量统计分析增强
- 角色：架构师
- 优先级：P1
- 状态：待审计
- 前置依赖：`TASK-030A` 实现审计通过（审计意见书第299份）；`TASK-030C` 实现审计通过（审计意见书第308份）；[`TASK-012_质量管理基线设计.md`](/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-012_质量管理基线设计.md) 设计冻结

## 2. 任务目标

在 `TASK-030A` 已完成的质量统计只读基线之上，补齐质量统计增强能力，保持“只读统计、不新增写入口”的边界：

1. 增强 `GET /api/quality/statistics`，补齐多维聚合与 Top N 统计。
2. 新增 `GET /api/quality/statistics/trend?period=monthly|weekly`，返回缺陷率与不良率趋势。
3. 在质量列表页新增“统计分析”页签，展示聚合结果与趋势数据。
4. 全链路继续排除 `cancelled` 记录，并保持 `company` 资源过滤。

本任务只形成可审计工程实现边界；不新增写路径，不放大到 Outbox、ERPNext 写入或状态机修改。

## 3. 设计依据

1. [`TASK-012_质量管理基线设计.md`](/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-012_质量管理基线设计.md) 已冻结质量统计与分析方向，统计口径须保持只读与 fail-closed 边界。
2. `TASK-030A`（审计意见书第299份）已收口 `GET /api/quality/statistics` 统计基线；`TASK-030E` 是其增强轮，不是绿地新建。
3. `TASK-030C`（审计意见书第308份）已收口质量状态机；本任务不得触碰 `confirm / cancel / patch` 等写语义。
4. 当前仓库已有真实增强落点锚点，可直接作为实现与审计边界：
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/quality_service.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/quality.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/quality.py`
   - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/quality.ts`
   - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/quality/QualityInspectionList.vue`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_quality_statistics_enhanced.py`

## 4. 允许范围

### 4.1 后端

允许修改：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/quality_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/quality.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/quality.py`

### 4.2 前端

允许修改：

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/quality.ts`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/quality/QualityInspectionList.vue`

### 4.3 测试与记录

允许新增 / 修改：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_quality_statistics_enhanced.py`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md`

## 5. 禁止范围

1. 禁止新增任何写接口或修改任何写路径：`create / update / defect / confirm / cancel / outbox worker` 均不在本任务范围内。
2. 禁止修改质量 Outbox、ERPNext 写适配层、migration、`main.py`、权限动作映射。
3. 禁止把 `cancelled` 记录重新纳入统计口径。
4. 禁止绕过 `company` 范围过滤返回跨公司数据。
5. 禁止修改：
   - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/router/**`
   - `/Users/hh/Desktop/领意服装管理系统/.github/**`
   - `/Users/hh/Desktop/领意服装管理系统/02_源码/**`
   - `/Users/hh/Desktop/领意服装管理系统/04_生产/**`
6. 禁止 push / remote / PR / 生产发布。

## 6. 必须实现

### 6.1 后端统计增强

`GET /api/quality/statistics` 在保留基线字段的同时，新增：

- `by_supplier`
- `by_item_code`
- `by_warehouse`
- `by_source_type`
- `top_defective_suppliers`
- `top_defective_items`

其中每个聚合项至少包含：

- `key`
- `label`
- `count`
- `total_inspected_qty`
- `total_accepted_qty`
- `total_rejected_qty`
- `defect_rate`

### 6.2 趋势接口

新增：`GET /api/quality/statistics/trend?period=monthly|weekly`

要求：

1. 支持 `monthly` 与 `weekly` 两种周期。
2. 返回每个周期点的：
   - `period_key`
   - `inspection_count`
   - `total_inspected_qty`
   - `total_rejected_qty`
   - `defect_rate`
   - `rejected_rate`
3. 趋势统计同样必须排除 `cancelled`，并执行 `company` 过滤。

### 6.3 前端统计分析页签

`QualityInspectionList.vue` 必须新增“统计分析”页签，至少展示：

1. 总体统计卡片。
2. 按供应商、物料、仓库的聚合表格。
3. Top N 缺陷供应商、Top N 缺陷物料。
4. 趋势数据视图（表格或图表均可，但必须可渲染并与接口对接）。

### 6.4 测试

`test_quality_statistics_enhanced.py` 至少覆盖：

1. 多维聚合字段返回完整。
2. `cancelled` 记录被排除。
3. `company` 过滤生效。
4. `monthly / weekly` 趋势接口返回正确。

## 7. 验收标准

1. `GET /api/quality/statistics` 响应包含全部增强字段，且保留基线字段。
2. `GET /api/quality/statistics/trend?period=monthly` 与 `weekly` 均返回有效结果。
3. 所有统计与趋势结果均排除 `cancelled` 记录。
4. 所有统计与趋势结果均执行 `company` 范围过滤。
5. 前端“统计分析”页签可正常渲染聚合结果与趋势数据。
6. `test_quality_statistics_enhanced.py` 通过。
7. `npm run typecheck` 通过。
8. 禁改目录无新增越界修改。

## 8. 验证命令

```bash
cd /Users/hh/Desktop/领意服装管理系统

# 1. 后端增强字段与趋势接口存在
rg -n 'by_supplier|by_item_code|by_warehouse|by_source_type|top_defective_suppliers|top_defective_items|statistics_trend' \
  07_后端/lingyi_service/app/services/quality_service.py \
  07_后端/lingyi_service/app/schemas/quality.py \
  07_后端/lingyi_service/app/routers/quality.py

# 2. cancelled 排除逻辑仍在
rg -n 'cancelled' \
  07_后端/lingyi_service/app/services/quality_service.py \
  07_后端/lingyi_service/tests/test_quality_statistics_enhanced.py

# 3. 前端统计分析页签与趋势调用存在
rg -n '统计分析|fetchQualityStatistics|fetchQualityStatisticsTrend|by_supplier|top_defective' \
  06_前端/lingyi-pc/src/api/quality.ts \
  06_前端/lingyi-pc/src/views/quality/QualityInspectionList.vue

# 4. 测试通过
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest tests/test_quality_statistics_enhanced.py -v --tb=short

# 5. 前端 typecheck
cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc
npm run typecheck

# 6. 禁改路径检查
cd /Users/hh/Desktop/领意服装管理系统
git diff --name-only -- \
  06_前端/lingyi-pc/src/router \
  .github \
  02_源码 \
  04_生产
# 应返回空
```

## 9. 完成回报

TASK-030E 执行完成。  
结论：待审计  
统计增强字段是否已补齐：是 / 否  
趋势接口是否已实现：是 / 否  
`cancelled` 排除是否生效：是 / 否  
`company` 过滤是否生效：是 / 否  
前端统计分析页签是否可用：是 / 否  
pytest 测试结果：[通过 / 失败]  
npm typecheck 结果：[通过 / 失败]

---

**C Auditor 备注（供总调度参考）：**

`TASK-030E` 是 `TASK-030A` 统计基线的增强轮，不是新建质量模块。  
若 B 已先行提交实现，只要 A 已补齐正式任务单并完成控制面对账，C 可直接按本任务单对现有实现做正式审计；不必因为“任务包规划项先于工程任务单落盘”而重复开发一轮。
