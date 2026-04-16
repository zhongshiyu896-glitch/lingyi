# TASK-011E 销售库存前端只读接入与契约门禁交付证据

## 1. 结论

TASK-011E 已完成前端只读接入与契约门禁落地，当前结论为：待审计。

本任务仅接入销售库存只读页面、只读 API client、只读路由、权限展示字段与前端契约门禁；未开放任何写入口，未进入 TASK-012。

## 2. 本次变更文件

### 2.1 前端只读业务文件

- `06_前端/lingyi-pc/src/api/sales_inventory.ts`
- `06_前端/lingyi-pc/src/views/sales_inventory/SalesInventorySalesOrderList.vue`
- `06_前端/lingyi-pc/src/views/sales_inventory/SalesInventorySalesOrderDetail.vue`
- `06_前端/lingyi-pc/src/views/sales_inventory/SalesInventoryStockLedger.vue`
- `06_前端/lingyi-pc/src/views/sales_inventory/SalesInventoryReferenceList.vue`
- `06_前端/lingyi-pc/src/router/index.ts`
- `06_前端/lingyi-pc/src/stores/permission.ts`

### 2.2 契约门禁文件

- `06_前端/lingyi-pc/scripts/check-sales-inventory-contracts.mjs`
- `06_前端/lingyi-pc/scripts/test-sales-inventory-contracts.mjs`
- `06_前端/lingyi-pc/package.json`

### 2.3 证据文件

- `03_需求与设计/02_开发计划/TASK-011E_销售库存前端只读接入与契约门禁_交付证据.md`

## 3. 只读接入口径

新增只读 API client 方法：

- `fetchSalesInventorySalesOrders`
- `fetchSalesInventorySalesOrderDetail`
- `fetchSalesInventoryStockSummary`
- `fetchSalesInventoryStockLedger`
- `fetchSalesInventoryWarehouses`
- `fetchSalesInventoryCustomers`

新增只读路由：

- `/sales-inventory/sales-orders`
- `/sales-inventory/sales-orders/detail`
- `/sales-inventory/stock-ledger`
- `/sales-inventory/references`

权限口径：

- 页面使用 `sales_inventory_read` 控制只读展示。
- `sales_inventory:diagnostic` 被加入前端非 UI 动作 denylist。
- `sales_inventory_diagnostic` 在按钮权限中强制清零，不暴露普通页面入口。

## 4. 契约门禁覆盖

新增脚本：

- `npm run check:sales-inventory-contracts`
- `npm run test:sales-inventory-contracts`

新增反向场景共 12 个，含成功场景共 13 个：

- API 出现 `POST` 时失败。
- 出现 ERPNext `/api/resource` 直连时失败。
- 出现 sales-inventory internal 路径时失败。
- 出现 `run-once` 时失败。
- 普通页面出现 `/api/sales-inventory/diagnostic` 时失败。
- 页面出现中文写动作语义时失败。
- 页面出现英文写动作语义时失败。
- 缺少必需只读 API 方法时失败。
- 缺少必需路由时失败。
- 路由暴露 diagnostic 等非只读路径时失败。
- 缺少 `sales_inventory:diagnostic` denylist 时失败。
- 缺少 `sales_inventory_diagnostic` 强制清零时失败。

## 5. 验证结果

### 5.1 前端销售库存定向门禁

```text
npm run check:sales-inventory-contracts
Sales inventory contract check passed.
Scanned files: 12
```

```text
npm run test:sales-inventory-contracts
Sales inventory contract reverse tests passed. scenarios=13
```

### 5.2 前端全链路验证

```text
npm run verify
通过

关键场景数：
- production contracts: scenarios=12
- style-profit contracts: scenarios=475
- factory-statement contracts: scenarios=26
- sales-inventory contracts: scenarios=13
- frontend-contract-engine: scenarios=25
- typecheck: 通过
- build: 通过
```

```text
npm audit --audit-level=high
found 0 vulnerabilities
```

### 5.3 后端只读回归

```text
.venv/bin/python -m pytest -q tests/test_sales_inventory*.py tests/test_permissions*.py tests/test_erpnext_fail_closed_adapter.py
47 passed, 1 warning
```

```text
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
通过
```

### 5.4 禁改与禁线扫描

```text
git diff --name-only -- '07_后端' '.github' '02_源码' '03_需求与设计/02_开发计划/TASK-012*'
空输出
```

```text
git diff --cached --name-only
空输出
```

```text
git diff --check
空输出
```

销售库存前端只读禁线扫描：

```text
rg -n "fetch\(|axios|/api/resource|/api/sales-inventory/.*/internal|run-once|diagnostic|method\s*:\s*['\"](?:POST|PUT|PATCH|DELETE)|生成|同步|提交|取消|重算|创建|新增|保存|删除|修改|编辑|发起|审批|Purchase Invoice|Payment Entry|GL Entry|Stock Entry|submitPurchaseInvoice|createPaymentEntry|createGlEntry|createStockEntry" \
  06_前端/lingyi-pc/src/api/sales_inventory.ts \
  06_前端/lingyi-pc/src/views/sales_inventory \
  06_前端/lingyi-pc/src/router/index.ts
无命中（exit code 1）
```

## 6. 边界声明

- 未修改 `07_后端/**`。
- 未修改 `.github/**`。
- 未修改 `02_源码/**`。
- 未修改 migrations。
- 未进入 `TASK-012*`。
- 未新增 POST/PUT/PATCH/DELETE。
- 未调用 ERPNext `/api/resource`。
- 未暴露 `/api/sales-inventory/diagnostic` 普通页面入口。
- 未暴露 internal/run-once。
- 未 push、未配置 remote、未创建 PR。

## 7. 后续建议

建议进入 TASK-011E 审计复核；审计通过后再决定是否进入 TASK-011F 本地基线提交或后续任务。TASK-012 继续阻塞。
