# TASK-164E 销售库存只读筛选与透传回归归口报告

## 1. 任务范围

- TASK_ID: `TASK-164E`
- 白名单文件：
  - `06_前端/lingyi-pc/src/api/sales_inventory.ts`
  - `06_前端/lingyi-pc/src/views/sales_inventory/SalesInventorySalesOrderList.vue`
  - `06_前端/lingyi-pc/src/views/sales_inventory/SalesInventoryStockLedger.vue`
- 本轮执行策略：
  - 先只读核对三文件 diff
  - 跑任务单指定三条前端验证命令
  - 做静态业务锚点核对
  - 验证通过后仅新增报告并追加工程师会话日志

## 2. 三文件 diff 摘要（只读）

命令：

`git -C '/Users/hh/Desktop/领意服装管理系统' diff --stat -- '06_前端/lingyi-pc/src/api/sales_inventory.ts' '06_前端/lingyi-pc/src/views/sales_inventory/SalesInventorySalesOrderList.vue' '06_前端/lingyi-pc/src/views/sales_inventory/SalesInventoryStockLedger.vue'`

结果：

- `sales_inventory.ts`: `+18/-2`
- `SalesInventorySalesOrderList.vue`: `+27`
- `SalesInventoryStockLedger.vue`: `+24`
- 合计：`3 files changed, 67 insertions(+), 2 deletions(-)`

## 3. 归属关系

- `TASK-140A`：冻结销售库存二期只读增强合同（sales order `item_name/from_date/to_date`、stock ledger `from_date/to_date`、fulfillment `company/item_code/warehouse` 透传）。
- `TASK-140B`：在上述三文件完成筛选与 query 参数透传实现。

本轮归属结论：

- 三文件属于 `TASK-140A/TASK-140B` 历史链路产物。
- 本轮定向验证无需修复，保持为历史实现回归归口。

## 4. 定向验证结果

执行目录：`/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc`

1. `npm run check:sales-inventory-contracts`
   - 结果：**PASS**
2. `npm run test:sales-inventory-contracts`
   - 结果：**PASS**（`scenarios=13`）
3. `npm run typecheck`
   - 结果：**PASS**

结论：本轮无需在三文件内做代码修复。

## 5. 静态业务锚点核对

- `sales_inventory.ts`：
  - 存在 sales order `item_name/from_date/to_date` query 支持与透传。
  - 存在 stock ledger `from_date/to_date` query 支持与透传。
  - 存在 fulfillment `company/item_code/warehouse` query 透传。
- `SalesInventorySalesOrderList.vue`：
  - 存在 `item_name/from_date/to_date` 筛选项。
  - 查询加载时透传 `item_name/from_date/to_date`。
- `SalesInventoryStockLedger.vue`：
  - 存在库存流水 `from_date/to_date` 筛选项与透传。
  - 存在 fulfillment 查询 `company/item_code/warehouse` 透传。

静态核对结论：**PASS**。

## 6. 收敛结论

- `CODE_CHANGED`: `NO`
- `can_reclassify_to`: `HISTORICAL_TASK_OUTPUT_VERIFIED`
- `remaining_unowned_business_diffs_excluded`: `YES`

本报告仅覆盖销售库存三文件，不覆盖 `factory-statement / warehouse / production / backend / CCC` 等其他差异。

## 7. 收尾校验

1. `git -C '/Users/hh/Desktop/领意服装管理系统' diff --check -- '06_前端/lingyi-pc/src/api/sales_inventory.ts' '06_前端/lingyi-pc/src/views/sales_inventory/SalesInventorySalesOrderList.vue' '06_前端/lingyi-pc/src/views/sales_inventory/SalesInventoryStockLedger.vue'`
   - 结果：**PASS**（无输出）
2. `git -C '/Users/hh/Desktop/领意服装管理系统' diff --name-only -- '06_前端/lingyi-pc/src/api/sales_inventory.ts' '06_前端/lingyi-pc/src/views/sales_inventory/SalesInventorySalesOrderList.vue' '06_前端/lingyi-pc/src/views/sales_inventory/SalesInventoryStockLedger.vue' '03_需求与设计/02_开发计划/TASK-164E_销售库存只读筛选与透传回归归口报告.md' '03_需求与设计/02_开发计划/工程师会话日志.md'`
   - 结果：见回交 `CHANGED_FILES` 与范围核对。

## 8. 风险与边界

- 未运行 `npm run dev/build/verify`
- 未运行后端测试
- 未触碰其他前端 `src/scripts`、后端、CCC、控制面、AGENTS、架构师日志、审计官日志、生产/GitHub 管理配置
- 不代表剩余 business tracked diff、REL-004/REL-005、生产联调、ERPNext 生产写入或业务功能放行
