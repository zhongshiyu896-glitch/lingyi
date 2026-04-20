# TASK-040A 销售库存只读聚合增强 工程任务单

## 1. 基本信息

- 任务编号：TASK-040A
- 任务名称：销售库存只读聚合增强
- 角色：架构师
- 优先级：P1
- 状态：待执行（已放行）
- 前置依赖：`TASK-030F` 实现审计通过（审计意见书第366份）；[`TASK-011_销售库存只读集成设计.md`](/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-011_销售库存只读集成设计.md) 设计冻结

## 2. 任务目标

基于现有 `sales_inventory` 只读集成基线，增强销售库存聚合与联动分析能力，保持“只读、不写 ERPNext、不新增业务写入口”的边界：

1. 新增库存聚合视图：按 `item_code + warehouse` 聚合 `actual_qty / ordered_qty / indented_qty`。
2. 新增销售订单满足率视图：关联 Sales Order Item 与库存可用量，计算 `fulfillment_rate`。
3. 新增库存预警字段：`safety_stock / reorder_level / is_below_safety / is_below_reorder`。
4. 保持 `company` 范围过滤与只读约束。

## 3. 设计依据

1. [`TASK-011_销售库存只读集成设计.md`](/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-011_销售库存只读集成设计.md) 已冻结 `sales_inventory` 为只读模块，禁止新增写能力。
2. 当前仓库已存在真实基线，不是绿地新建：
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/sales_inventory_service.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/sales_inventory.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/sales_inventory.py`
   - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/sales_inventory.ts`
   - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/sales_inventory/`
3. `TASK-040A` 只做只读聚合增强，不修改 `router/index.ts`，不新建跨模块写链路。

## 4. 允许范围

### 4.1 后端

允许修改：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/sales_inventory_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/sales_inventory.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/sales_inventory.py`

### 4.2 前端

允许修改：

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/sales_inventory.ts`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/sales_inventory/` 下现有页面

### 4.3 测试与记录

允许新增 / 修改：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_sales_inventory_enhanced.py`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md`

## 5. 禁止范围

1. 禁止新增任何写接口、写操作、Outbox、ERPNext 写调用。
2. 禁止修改：
   - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/router/**`
   - `/Users/hh/Desktop/领意服装管理系统/.github/**`
   - `/Users/hh/Desktop/领意服装管理系统/02_源码/**`
   - `/Users/hh/Desktop/领意服装管理系统/04_生产/**`
3. 禁止将 `sales_inventory` 从只读模块扩展为可写模块。
4. 禁止 push / remote / PR / 生产发布。

## 6. 必须实现

### 6.1 后端接口

新增或增强以下只读接口：

1. `GET /api/sales-inventory/aggregation`
   返回至少：
   - `item_code`
   - `warehouse`
   - `actual_qty`
   - `ordered_qty`
   - `indented_qty`
   - `safety_stock`
   - `reorder_level`
   - `is_below_safety`
   - `is_below_reorder`

2. `GET /api/sales-inventory/sales-order-fulfillment`
   返回至少：
   - `sales_order`
   - `item_code`
   - `ordered_qty`
   - `actual_qty`
   - `fulfillment_rate`

### 6.2 计算要求

1. `fulfillment_rate = min(1, actual_qty / ordered_qty)`；`ordered_qty <= 0` 时必须 fail-closed 或按 0 处理，不得产生非法值。
2. 所有聚合必须执行 `company` 过滤。
3. 保持只读，不得引入业务写语义。

### 6.3 前端

在现有 `sales_inventory` 页面内补齐：

1. 聚合视图
2. 销售满足率视图
3. `is_below_safety / is_below_reorder` 的高亮展示

### 6.4 测试

`test_sales_inventory_enhanced.py` 至少覆盖：

1. 聚合接口返回正确维度数据。
2. 满足率计算正确。
3. `company` 过滤生效。
4. 安全库存 / 补货阈值标记逻辑正确。

## 7. 验收标准

1. 聚合接口返回 `item_code + warehouse` 维度结果。
2. 满足率接口返回正确的 `fulfillment_rate`。
3. 前端正确展示库存预警高亮。
4. `company` 过滤生效。
5. `test_sales_inventory_enhanced.py` 通过。
6. `npm run typecheck` 通过。
7. 禁改路径无新增越界修改。

## 8. 验证命令

```bash
cd /Users/hh/Desktop/领意服装管理系统

# 1. 聚合 / 满足率接口存在
rg -n 'aggregation|sales-order-fulfillment|fulfillment_rate|safety_stock|reorder_level|is_below_safety|is_below_reorder' \
  07_后端/lingyi_service/app/services/sales_inventory_service.py \
  07_后端/lingyi_service/app/routers/sales_inventory.py \
  07_后端/lingyi_service/app/schemas/sales_inventory.py

# 2. 前端视图与高亮存在
rg -n 'aggregation|fulfillment|is_below_safety|is_below_reorder|safety_stock|reorder_level' \
  06_前端/lingyi-pc/src/api/sales_inventory.ts \
  06_前端/lingyi-pc/src/views/sales_inventory

# 3. 测试
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest tests/test_sales_inventory_enhanced.py -v --tb=short

# 4. 前端 typecheck
cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc
npm run typecheck

# 5. 禁改路径检查
cd /Users/hh/Desktop/领意服装管理系统
git diff --name-only -- \
  06_前端/lingyi-pc/src/router \
  .github \
  02_源码 \
  04_生产
# 应返回空
```
