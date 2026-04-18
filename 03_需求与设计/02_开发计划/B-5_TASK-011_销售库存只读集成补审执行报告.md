# B-5 TASK-011 销售库存只读集成补审执行报告

- 任务编号：B-5
- 任务名称：TASK-011 销售/库存只读集成补审
- 执行角色：工程师（补审执行）
- 执行时间：2026-04-17

## 一、5 个检查项逐项结论

### 检查项1：是否全链路只读
- 结论：✅ 通过
- 后端代码位置证据：
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/sales_inventory.py:138`、`:198`、`:249`、`:304`、`:368`、`:420`、`:460` 仅暴露 `@router.get(...)`。
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_sales_inventory_api.py:251`~`259` 明确断言销售库存路由方法集合仅允许 `GET/HEAD/OPTIONS`。
- 前端契约门禁证据：
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/sales_inventory.ts:132`~`190` 全部为 `request()` 的只读查询路径（无写方法声明）。
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-sales-inventory-contracts.mjs:90`、`:169`~`173` 明确禁止 `POST/PUT/PATCH/DELETE` 与裸 `fetch/axios`。

### 检查项2：Customer 资源权限是否 fail closed
- 结论：✅ 通过
- 后端代码位置证据：
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/sales_inventory.py:107`~`128` 在 `_scope_allowed` 中对 customer 维度执行权限过滤，空权限不放行。
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/sales_inventory.py:454`~`457` 对 customers 列表执行权限过滤并重算 `total`，无权限即返回空结果。
- 测试覆盖证据：
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_sales_inventory_permissions.py:116`~`127` `allowed_customers` 为空时 deny（fail closed）。
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_sales_inventory_api.py:179`~`206` customers 接口在空 customer 权限下返回 `items=[]`、`total=0`。

### 检查项3：销售订单详情是否防枚举
- 结论：✅ 通过
- 后端代码位置证据：
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/sales_inventory.py:73`~`82` 定义统一 not-found 错误信封（隐藏资源存在性）。
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/sales_inventory.py:241`~`245` 资源越权时转为同形态 404（`ERPNEXT_RESOURCE_NOT_FOUND`）。
- 测试覆盖证据：
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_sales_inventory_api.py:125`~`160` 验证越权详情返回 404 且写安全审计。
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_sales_inventory_api.py:161`~`178` 验证“资源不存在”与“越权隐藏”对外返回同形态。
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_sales_inventory_api.py:112`~`123` 验证动作权限拒绝优先于 ERPNext 读取。

### 检查项4：ERPNext SLE / SO / DN malformed 是否 fail closed
- 结论：✅ 通过（SO/SLE 已闭环；DN 当前未接入本模块读取链路）
- 后端代码位置证据：
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_sales_inventory_adapter.py:94`~`102` Sales Order 详情使用 `normalize_erpnext_response` + `require_submitted_doc`，`items` 类型非法即 fail closed。
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_sales_inventory_adapter.py:290`~`299` SLE 缺字段/非法字段行被丢弃，不伪成功。
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_sales_inventory_adapter.py:261`~`264` timeout/401/403/5xx/malformed 统一走异常映射 fail closed。
- 测试覆盖证据：
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_sales_inventory_adapter.py:14`~`25` SO `docstatus` 缺失/非法 fail closed。
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_sales_inventory_adapter.py:33`~`60` SLE 缺字段/非法数量 fail closed。
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_sales_inventory_api.py:208`~`222` ERPNext 不可用返回 `EXTERNAL_SERVICE_UNAVAILABLE`（503），无 200+空数据伪成功。
- DN 说明：
  - 当前 `sales_inventory` 只读实现未包含 Delivery Note 读取入口（代码检索无 DN 解析分支），因此不存在 DN malformed 被误判成功的执行路径。

### 检查项5：前端是否禁止写入口、diagnostic、ERPNext 直连
- 结论：✅ 通过
- 前端代码位置证据：
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/sales_inventory/SalesInventorySalesOrderList.vue:79`、`103`~`106`
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/sales_inventory/SalesInventorySalesOrderDetail.vue:65`、`77`~`80`
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/sales_inventory/SalesInventoryStockLedger.vue:102`、`131`~`134`
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/sales_inventory/SalesInventoryReferenceList.vue:96`、`110`~`114`、`131`~`135`
  - 上述页面均在无 `sales_inventory_read` 权限时 fail closed，不发读请求。
- 前端契约门禁证据：
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-sales-inventory-contracts.mjs:62`、`:94`、`:95`、`:190`、`:203`、`:209`、`:212` 强制禁止 `diagnostic/internal/run-once` 暴露与 `/api/resource` 直连。
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-sales-inventory-contracts.mjs:150`~`242` 反向用例覆盖写入口、diagnostic、internal、run-once、denylist 缺失等高危绕过。

## 二、测试命令与结果

执行目录（后端）：`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service`

1. 后端定向测试：
```bash
.venv/bin/python -m pytest -q \
  tests/test_sales_inventory_api.py \
  tests/test_sales_inventory_adapter.py \
  tests/test_sales_inventory_permissions.py
```
结果：`19 passed, 1 warning in 0.69s`

2. 后端扩展回归：
```bash
.venv/bin/python -m pytest -q \
  tests/test_sales_inventory*.py \
  tests/test_permissions*.py \
  tests/test_erpnext_fail_closed_adapter.py
```
结果：`47 passed, 1 warning in 0.68s`

3. 后端语法编译：
```bash
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
```
结果：通过（`PY_COMPILE_OK`）

执行目录（前端）：`/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc`

4. 销售库存契约：
```bash
npm run test:sales-inventory-contracts
```
结果：通过（`scenarios=13`）

5. 公共前端门禁引擎：
```bash
npm run test:frontend-contract-engine
```
结果：通过（`scenarios=25`）

6. 前端全量验证：
```bash
npm run verify
```
结果：通过（含 `style-profit scenarios=475`、`factory-statement scenarios=26`、`sales-inventory scenarios=13`、`quality scenarios=14`，并完成 typecheck/build）

7. 依赖安全审计：
```bash
npm audit --audit-level=high
```
结果：`found 0 vulnerabilities`

## 三、问题项统计
- 高：0
- 中：0
- 低：1
  - `pytest_asyncio` 在 Python 3.16 的弃用告警（DeprecationWarning），不影响本次只读集成补审结论。

## 四、结论
- 结论：提交审计
- 说明：本报告为工程师补审执行报告，不替代审计官正式审计意见书。
