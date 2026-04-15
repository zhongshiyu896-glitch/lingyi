# TASK-006G 加工厂对账单本地封版复审证据

## 1. 基本信息
- 复审时间：2026-04-15 22:17:21 CST
- 当前 HEAD：`1da795333d20ed8ecfb2308da623358668272458`
- 当前分支：`main`
- 复审人：Codex（工程复审执行）
- 结论：建议进入 TASK-006 本地封版审计

## 2. 任务链路与审计闭环

| 任务编号 | 任务目标 | 对应任务单路径 | 对应证据路径 | 审计意见书编号 | 审计结论 | 是否闭环 |
| --- | --- | --- | --- | --- | --- | --- |
| TASK-006A | 开发前基线盘点与设计冻结 | `03_需求与设计/02_开发计划/TASK-006A_加工厂对账单开发前基线盘点与设计冻结_工程任务单.md` | `03_需求与设计/02_开发计划/TASK-006A_加工厂对账单开发前基线盘点证据.md` | 第161份 | 通过 | 是 |
| TASK-006B | 后端模型迁移与草稿API | `03_需求与设计/02_开发计划/TASK-006B_加工厂对账单后端模型迁移与草稿API_工程任务单.md` | `03_需求与设计/02_开发计划/TASK-006B_加工厂对账单后端模型迁移与草稿API_交付证据.md` | 第162份 | 不通过 | 是（由006B1闭环） |
| TASK-006B1 | 重复防护与取消后重建约束整改 | `03_需求与设计/02_开发计划/TASK-006B1_对账草稿重复防护与取消后重建约束整改_工程任务单.md` | `03_需求与设计/02_开发计划/TASK-006B1_对账草稿重复防护与取消后重建约束整改_交付证据.md` | 第163份 | 通过 | 是 |
| TASK-006C | 确认/取消与active-scope语义收口 | `03_需求与设计/02_开发计划/TASK-006C_对账确认取消与ActiveScope冲突语义收口_工程任务单.md` | `03_需求与设计/05_审计记录.md`（第164份以006C1闭环） | 第164份（C1） | 通过（C1） | 是 |
| TASK-006C1 | create路由未知异常兜底修复 | `03_需求与设计/02_开发计划/TASK-006C1_Create路由未知异常兜底修复_工程任务单.md` | `03_需求与设计/02_开发计划/TASK-006C1_Create路由未知异常兜底修复_交付证据.md` | 第164份 | 通过 | 是 |
| TASK-006D | ERPNext应付草稿Outbox集成 | `03_需求与设计/02_开发计划/TASK-006D_ERPNext应付草稿Outbox集成_工程任务单.md` | `03_需求与设计/02_开发计划/TASK-006D_ERPNext应付草稿Outbox集成_交付证据.md` | 第165份 | 不通过 | 是（由006D1闭环） |
| TASK-006D1 | worker/outbox状态机安全整改 | `03_需求与设计/02_开发计划/TASK-006D1_WorkerOutbox状态机安全整改_工程任务单.md` | `03_需求与设计/05_审计记录.md`（第166份） | 第166份 | 通过 | 是 |
| TASK-006E | 前端联调与契约门禁 | `03_需求与设计/02_开发计划/TASK-006E_加工厂对账单前端联调与契约门禁_工程任务单.md` | `03_需求与设计/02_开发计划/TASK-006E_加工厂对账单前端联调与契约门禁_交付证据.md` | 第167份 | 不通过 | 是（由006E1/006E2闭环） |
| TASK-006E1 | 前后端契约与payable摘要整改 | `03_需求与设计/02_开发计划/TASK-006E1_前后端契约补齐与Payable摘要门禁整改_工程任务单.md` | `03_需求与设计/02_开发计划/TASK-006E1_前后端契约补齐与Payable摘要门禁整改_交付证据.md` | 第168份 | 不通过 | 是（由006E2闭环） |
| TASK-006E2 | 同statement active outbox防重 | `03_需求与设计/02_开发计划/TASK-006E2_PayableDraft同StatementActiveOutbox防重整改_工程任务单.md` | `03_需求与设计/02_开发计划/TASK-006E2_PayableDraft同StatementActiveOutbox防重整改_交付证据.md` | 第169份 | 通过 | 是 |
| TASK-006F | 打印导出与封版前证据盘点 | `03_需求与设计/02_开发计划/TASK-006F_打印导出与封版前证据盘点_工程任务单.md` | `03_需求与设计/02_开发计划/TASK-006F_打印导出与封版前证据盘点_交付证据.md` | 第170份 | 不通过 | 是（由006F1闭环） |
| TASK-006F1 | CSV公式注入防护整改 | `03_需求与设计/02_开发计划/TASK-006F1_CSV公式注入防护整改_工程任务单.md` | `03_需求与设计/02_开发计划/TASK-006F1_CSV公式注入防护整改_交付证据.md` | 第171份 | 通过 | 是 |

## 3. 后端能力核验

### 已完成能力（基于第161~171份审计闭环 + 本轮复跑）
- 草稿生成：已覆盖。
- 同范围 active-scope 防重：已覆盖（含业务语义错误码收口）。
- 取消后重建：已覆盖。
- 确认：已覆盖。
- 取消释放 inspection：已覆盖。
- create 未知异常统一错误信封：已覆盖（`FACTORY_STATEMENT_INTERNAL_ERROR`）。
- payable outbox 创建：已覆盖。
- ERPNext Purchase Invoice 草稿创建 `docstatus=0`：已覆盖（worker 路径）。
- worker 服务账号权限：已覆盖。
- worker dry-run：已覆盖。
- worker claim due/lease 安全：已覆盖（D1整改闭环）。
- 同 statement active payable outbox 防重：已覆盖（E2整改闭环）。
- `event_key` 不含 `idempotency_key`：已覆盖（E2整改闭环）。
- 权限源 fail closed：已覆盖。
- 操作审计/安全审计：已覆盖。

### 本轮自测命令
```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest -q tests/test_factory_statement*.py
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
rg -n "submit\(|docstatus\s*=\s*1|Payment Entry|GL Entry|create_payment|submit_purchase_invoice|reset_payable|rebuild_payable|dead.*rebuild" app tests
```

### 本轮结果
- `pytest -q tests/test_factory_statement*.py`：`77 passed, 244 warnings`。
- `py_compile`：通过。
- 禁止能力扫描：
  - 命中主要来自：
    1. 非 `factory_statement` 既有模块（production/subcontract 领域）中的 `docstatus=1` 数据语义。
    2. `tests/test_factory_statement_payable_worker.py` 对 `docstatus=1` 的负向测试断言。
  - 未发现：`submit_purchase_invoice`、Payment Entry、GL Entry、`reset_payable/rebuild_payable` 业务实现落地。

## 4. 前端能力核验

### 已完成能力（基于第167~171份审计闭环 + 本轮复跑）
- 列表页：已覆盖。
- 详情页：已覆盖。
- 创建草稿 `company` 必填：已覆盖。
- 确认按钮权限：已覆盖。
- 取消按钮 active payable outbox fail closed：已覆盖。
- 生成应付草稿只创建 outbox：已覆盖。
- payable 状态展示：已覆盖。
- 打印页：已覆盖。
- CSV 导出：已覆盖。
- CSV 公式注入防护：已覆盖（F1闭环）。
- factory-statement contract 门禁：已覆盖。

### 本轮自测命令
```bash
cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc
npm run check:factory-statement-contracts
npm run test:factory-statement-contracts
npm run verify
npm audit --audit-level=high
rg -n "fetch\(|axios|/api/resource|factory-statements/internal|run-once|submitPurchaseInvoice|Payment Entry|GL Entry|createPaymentEntry|createGlEntry" src scripts
rg -n "parseFloat\(|Number\(" src/views/factory_statement src/utils scripts
```

### 本轮结果
- `check:factory-statement-contracts`：通过（`Scanned files: 8`）。
- `test:factory-statement-contracts`：通过（`scenarios=26`）。
- `verify`：通过（含 production/style-profit/factory-statement contract、typecheck、build）。
- `npm audit --audit-level=high`：`found 0 vulnerabilities`。

## 5. 禁止能力扫描

### 扫描命令
- 后端：
  - `rg -n "submit\(|docstatus\s*=\s*1|Payment Entry|GL Entry|create_payment|submit_purchase_invoice|reset_payable|rebuild_payable|dead.*rebuild" app tests`
- 前端：
  - `rg -n "fetch\(|axios|/api/resource|factory-statements/internal|run-once|submitPurchaseInvoice|Payment Entry|GL Entry|createPaymentEntry|createGlEntry" src scripts`
  - `rg -n "parseFloat\(|Number\(" src/views/factory_statement src/utils scripts`
- 聚焦 factory_statement 面扫描（补充）：
  - `rg ... src/api/factory_statement.ts src/views/factory_statement src/utils/factoryStatementExport.ts`
  - `rg ... app/models/factory_statement.py app/schemas/factory_statement.py app/routers/factory_statement.py app/services/factory_statement_service.py app/services/factory_statement_payable_outbox_service.py app/services/factory_statement_payable_worker.py app/services/erpnext_purchase_invoice_adapter.py tests/test_factory_statement*.py`

### 命中解释
- 前端广域扫描命中项为：
  1. `scripts/check-factory-statement-contracts.mjs` 与 `scripts/test-factory-statement-contracts.mjs` 中的门禁规则文本与反向 fixture（合法命中）。
  2. 非 factory_statement 范围的历史 API 文件中 `fetch`（如 `src/api/auth.ts`、`src/api/workshop.ts`、`src/api/bom.ts`），不属于本任务新增能力。
- 前端聚焦 `factory_statement` 范围扫描：无 forbidden 关键词命中。
- `parseFloat/Number` 扫描：
  - `src/utils/factoryStatementExport.ts` 无 `parseFloat/Number` 命中（满足金额不重算）。
  - `src/views/factory_statement/*.vue` 的 `Number(...)` 仅用于路由参数解析与展示格式化，不用于导出金额重算。
- 后端广域扫描命中：
  - 非 factory_statement 既有模块的 `docstatus=1` 语义。
  - `tests/test_factory_statement_payable_worker.py` 中 `docstatus=1` 负向测试。
- 后端聚焦 factory_statement 实现扫描：未发现 submit PI、Payment Entry、GL Entry、重建/reset payable 业务能力。

### 结论
- 禁止能力未发现新增实现回潮。
- 当前命中均可解释为门禁脚本/测试夹具/非本模块历史代码语义，不构成 TASK-006 新增禁入能力放开。

## 6. 打印/导出安全核验

- 打印数据来源：`FactoryStatementPrint.vue` 通过 `fetchFactoryStatementDetail` 读取详情快照；未新增导出后端接口。
- 打印触发：页面提供显式“打印”按钮，`window.print()` 仅在按钮点击后触发，无自动打印。
- CSV 金额不重算：`factoryStatementExport.ts` 直接使用后端返回字段（字符串/原值）并统一 `escapeCsvCell`，未使用 `parseFloat/Number` 进行金额重算。
- CSV 公式注入防护：
  - 使用 `FORMULA_INJECTION_PREFIX = /^[=+\-@\t\r\n]/`。
  - 命中前缀统一前置单引号再做 CSV 转义。
  - 兼容逗号/双引号/换行标准 CSV 转义。

## 7. 权限与审计核验

- 动作权限：`factory_statement:read/create/confirm/cancel/payable_draft_create/payable_draft_worker` 已在后端权限常量与权限服务映射。
- 资源权限：company + supplier 资源过滤/鉴权路径存在，权限源不可用走 fail closed（由历次审计与用例覆盖）。
- internal worker denylist：前端 `permission.ts` 将 `factory_statement_payable_draft_worker` 默认置 `false`，contract 脚本限制其仅可出现在 permission store denylist。
- 审计核验：
  - create/confirm/cancel/payable-draft/worker 失败路径均有统一错误信封与审计记录。
  - 未发现日志输出 Authorization/Cookie/Token/Secret/Password/SQL 原文证据。

## 8. 剩余风险

1. `datetime.utcnow()` 相关 deprecation warnings 仍存在（本轮测试仍有告警）。
2. failed/dead payable outbox 的重建策略未实现，需后续单独任务收口。
3. 本地验证不等同生产 ERPNext 环境连通性/主数据/权限真实性验证。
4. 本地验证不等同 GitHub hosted runner / required checks 平台闭环。
5. 工作区存在历史未跟踪文件与运行产物，后续提交必须白名单暂存。
6. 本轮 `npm run verify` 生成 `dist/`，属于运行产物，不得纳入提交。
7. 若后续引入 XLSX 或服务端导出能力，需重新进行公式注入与导出面复核。

## 9. 封版建议

建议进入 TASK-006 本地封版审计。
