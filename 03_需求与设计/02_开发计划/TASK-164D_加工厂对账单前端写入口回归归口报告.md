# TASK-164D 加工厂对账单前端写入口回归归口报告

## 1. 任务范围

- TASK_ID: `TASK-164D`
- 白名单业务文件：
  - `06_前端/lingyi-pc/src/api/factory_statement.ts`
  - `06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementList.vue`
  - `06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementDetail.vue`
- 文档输出：
  - `03_需求与设计/02_开发计划/TASK-164D_加工厂对账单前端写入口回归归口报告.md`
  - `03_需求与设计/02_开发计划/工程师会话日志.md`

## 2. 三文件 diff 摘要（只读）

命令：

`git -C '/Users/hh/Desktop/领意服装管理系统' diff --stat -- '06_前端/lingyi-pc/src/api/factory_statement.ts' '06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementList.vue' '06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementDetail.vue'`

结果：

- `factory_statement.ts`: `+106`
- `FactoryStatementList.vue`: `+137`
- `FactoryStatementDetail.vue`: `+187`
- 合计：`3 files changed, 430 insertions(+)`

## 3. 归属关系

- 与历史任务关系：
  - `TASK-120C`：冻结“列表页创建 + 详情页确认/取消 + API 最小承载”可放行边界
  - `TASK-120B`：落地创建/确认/取消入口、权限/状态/payable guard、`idempotency_key` 与 API 封装
- 本轮归口结论：
  - 三文件属于 `TASK-120C/TASK-120B` 链路上的历史产物
  - 本轮定向验证发现 API 合同缺口后已在白名单内做最小修复并回归通过

## 4. 定向验证结果

执行目录：`/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc`

1. `npm run check:factory-statement-contracts`
   - 结果：**PASS**
2. `npm run test:factory-statement-contracts`
   - 结果：**PASS**（`scenarios=26`）
3. `npm run typecheck`
   - 结果：**PASS**

## 5. 静态业务锚点核对

- `factory_statement.ts`：
  - 存在 `createFactoryStatement` / `confirmFactoryStatement` / `cancelFactoryStatement`
  - 存在 `createFactoryStatementPayableDraft`
  - 相关 payload 含 `idempotency_key`
- `FactoryStatementList.vue`：
  - 存在创建入口
  - 存在 `factory_statement_create` 权限 guard
  - 存在日期范围校验（`from_date <= to_date`）
  - 存在 `idempotency_key` 生成与提交
- `FactoryStatementDetail.vue`：
  - 存在确认/取消入口
  - 存在 `factory_statement_confirm` / `factory_statement_cancel` 权限 guard
  - 存在状态 guard（`isDraftStatus` / `isCancelStatusAllowed`）
  - 存在 payable/outbox 阻断（`hasActivePayableOutbox` / `summaryMissing`）
  - 确认/取消提交 payload 含 `idempotency_key`

## 6. 必要最小修复说明

- 触发点：
  - 首轮 `npm run check:factory-statement-contracts` 失败，报错缺少 `createFactoryStatementPayableDraft`
- 修复范围：
  - 仅修改白名单文件 `src/api/factory_statement.ts`
- 修复内容：
  - 补齐 `FactoryStatementPayableDraftCreatePayload` / `FactoryStatementPayableDraftCreateData`
  - 补齐 `createFactoryStatementPayableDraft(statementId, payload)` API 封装
- 修复后回归：
  - 三条任务单必跑命令全部通过

## 7. 收敛结论

- `CODE_CHANGED`: `YES`（仅白名单 3 文件内改动）
- `can_reclassify_to`: `HISTORICAL_TASK_OUTPUT_VERIFIED`
- `remaining_unowned_business_diffs_excluded`: `YES`

本报告仅覆盖 factory statement 三文件，不覆盖 sales-inventory / warehouse / production / backend / CCC 等其他差异。

## 8. 收尾校验

1. `git -C '/Users/hh/Desktop/领意服装管理系统' diff --check -- '06_前端/lingyi-pc/src/api/factory_statement.ts' '06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementList.vue' '06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementDetail.vue'`
   - 结果：**PASS**（无输出）
2. `git -C '/Users/hh/Desktop/领意服装管理系统' diff --name-only -- '06_前端/lingyi-pc/src/api/factory_statement.ts' '06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementList.vue' '06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementDetail.vue' '03_需求与设计/02_开发计划/TASK-164D_加工厂对账单前端写入口回归归口报告.md' '03_需求与设计/02_开发计划/工程师会话日志.md'`
   - 结果：见回交 `CHANGED_FILES` 与范围核对

## 9. 风险与边界

- 未运行 `npm run dev/build/verify`
- 未运行后端测试
- 未触碰其他前端 `src/scripts`、后端、CCC、控制面、AGENTS、架构师日志、审计官日志、生产/GitHub 管理配置
- 不代表剩余 business tracked diff、REL-004/REL-005、生产联调、ERPNext 生产写入或业务功能放行
