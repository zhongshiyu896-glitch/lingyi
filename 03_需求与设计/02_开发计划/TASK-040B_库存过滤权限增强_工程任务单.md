# TASK-040B 库存过滤权限增强 工程任务单

## 1. 基本信息
- 任务编号：`TASK-040B`
- 任务名称：库存过滤权限增强
- 角色：`B Engineer`
- 优先级：`P1`
- 状态：`待执行（已放行）`
- 前置依赖：`TASK-040A` 审计通过（审计意见书第367份）；`TASK-011_销售库存只读集成设计.md` 设计冻结

## 2. 任务目标
在 `TASK-040A` 已完成销售库存只读聚合增强的基础上，补齐销售库存链的过滤与权限边界：

1. 强化仓库级权限过滤：在 ERPNext 权限源模式下，基于 `allowed_warehouses` 收紧返回结果，防止越权看到无权限仓库数据。
2. 强化多参数组合过滤：对现有销售库存只读查询接口补齐 `company / item_code / warehouse / from_date / to_date` 等组合过滤能力。
3. 增加 `item_name` 模糊搜索：对存在物料行语义的接口支持 `item_name` 模糊匹配。
4. 保持全链路只读：不得新增任何写接口、ERPNext 写调用或本地事实写入。

## 3. 设计依据
1. `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-011_销售库存只读集成设计.md`
2. `TASK-040A` 审计意见书第367份：销售库存聚合接口、满足率接口与只读边界已成立。
3. 当前仓库现状锚点：`sales_inventory_service.py`、`sales_inventory.py`、`erpnext_sales_inventory_adapter.py`、`test_sales_inventory_api.py` 已存在可复用只读基线。

## 4. 允许范围
### 4.1 后端
允许修改：
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/sales_inventory_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/sales_inventory.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/sales_inventory.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_sales_inventory_adapter.py`

### 4.2 测试
允许修改或新增：
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_sales_inventory_api.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_sales_inventory_permissions.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_sales_inventory_permission.py`

### 4.3 日志
允许修改：
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md`

## 5. 禁止范围
1. 禁止修改 `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/router/**`
2. 禁止修改任何前端页面与前端 API（本轮仅做后端过滤与权限收口）
3. 禁止新增任何 POST / PUT / PATCH / DELETE
4. 禁止 ERPNext 写调用
5. 禁止新增 outbox / worker / 异步任务
6. 禁止修改 `.github/**`、`02_源码/**`、`04_生产/**`
7. 禁止 push / remote / PR
8. 禁止绕过现有权限服务直接在 router 内手写静态越权判断

## 6. 必须实现
### 6.1 仓库级权限过滤
在 `LINGYI_PERMISSION_SOURCE=erpnext` 且用户 `allowed_warehouses` 非空时，以下接口返回结果必须严格受仓库范围约束：
- `GET /api/sales-inventory/items/{item_code}/stock-summary`
- `GET /api/sales-inventory/items/{item_code}/stock-ledger`
- `GET /api/sales-inventory/aggregation`
- `GET /api/sales-inventory/sales-order-fulfillment`
- `GET /api/sales-inventory/warehouses`

要求：
1. 无权限仓库数据不得返回。
2. 若请求参数显式指定了无权限仓库，则返回空结果或被权限拒绝，但不得泄露越权仓库业务事实。
3. 仍保持 `company` 范围过滤与既有 fail-closed 语义。

### 6.2 多参数组合过滤
对下列接口补齐组合过滤能力：

#### A. 销售订单列表
`GET /api/sales-inventory/sales-orders`

至少支持：
- `company`
- `customer`
- `item_code`
- `item_name`
- `from_date`
- `to_date`

语义：
- `from_date / to_date` 作用于 `transaction_date`
- `item_name` 为模糊匹配
- 允许上述参数任意组合

#### B. 库存流水
`GET /api/sales-inventory/items/{item_code}/stock-ledger`

至少支持：
- `company`
- `warehouse`
- `from_date`
- `to_date`

语义：
- `from_date / to_date` 作用于 `posting_date`
- 允许与现有 `item_code`、分页参数组合

#### C. 库存聚合
`GET /api/sales-inventory/aggregation`

至少支持：
- `company`
- `item_code`
- `warehouse`

#### D. 销售订单满足率
`GET /api/sales-inventory/sales-order-fulfillment`

至少支持：
- `company`
- `item_code`
- `warehouse`
- `item_name`

语义：
- `item_name` 为模糊匹配
- `warehouse` 过滤在 fulfillment 行级生效

### 6.3 参数校验
1. `from_date > to_date` 必须 fail closed，返回 422 或等价参数错误，不得静默纠正。
2. 日期格式非法必须返回参数错误，不得 silently ignore。
3. 空白字符串视为未传。

## 7. 验收标准
1. 无权限仓库的数据不返回。
2. `warehouse` 显式指定为越权仓库时，不返回越权数据。
3. `sales-orders` 列表支持 `item_name` 模糊搜索。
4. `sales-orders` 列表支持 `from_date / to_date` 组合过滤。
5. `stock-ledger` 支持 `from_date / to_date` 组合过滤。
6. `sales-order-fulfillment` 支持 `item_code / warehouse / item_name / company` 过滤。
7. `from_date > to_date` 返回参数错误。
8. 只读边界不被破坏：无写接口、无 ERPNext 写调用、无前端越界修改。
9. 相关测试全部通过。

## 8. 必跑验证
```bash
cd /Users/hh/Desktop/领意服装管理系统

# 1. 过滤参数存在
rg -n "item_name|from_date|to_date|warehouse" \
  07_后端/lingyi_service/app/routers/sales_inventory.py \
  07_后端/lingyi_service/app/services/sales_inventory_service.py \
  07_后端/lingyi_service/app/services/erpnext_sales_inventory_adapter.py

# 2. 仓库权限过滤路径存在
rg -n "allowed_warehouses|is_warehouse_permitted|warehouse" \
  07_后端/lingyi_service/app/routers/sales_inventory.py \
  07_后端/lingyi_service/app/services/sales_inventory_service.py

# 3. 后端测试
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest \
  tests/test_sales_inventory_api.py \
  tests/test_sales_inventory_permissions.py \
  tests/test_sales_inventory_permission.py \
  -v --tb=short

# 4. 只读边界扫描
! rg -n "@router\.(post|put|patch|delete)|requests\.(post|put|patch|delete)|httpx\.(post|put|patch|delete)" \
  /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/sales_inventory.py \
  /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/sales_inventory_service.py \
  /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_sales_inventory_adapter.py

# 5. 禁改目录检查
git -C /Users/hh/Desktop/领意服装管理系统 diff --name-only -- \
  06_前端/lingyi-pc/src/router .github 02_源码 04_生产
# 预期为空
```

## 9. 完成回报
完成后仅按以下格式回交，不要回任务单正文：

```md
STATUS: READY_FOR_AUDIT
TASK_ID: TASK-040B
CONTEXT_VERSION: 未提供
ROLE: B

CHANGED_FILES:
- 绝对路径1
- 绝对路径2

EVIDENCE:
- 仓库权限过滤落点：
- 组合过滤落点：
- item_name 模糊搜索落点：
- from_date/to_date 校验落点：
- 测试覆盖点：

VERIFICATION:
- pytest：
- 只读边界扫描：
- 禁改目录 diff：

RISKS:
- 无 / 具体残余风险

NEXT_ROLE: C Auditor
```
