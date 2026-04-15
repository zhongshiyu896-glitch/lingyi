# TASK-006E1 前后端契约补齐与 Payable 摘要门禁整改交付证据

- 任务编号：TASK-006E1
- 前置审计：审计意见书第 167 份（2 个 P1 阻断）
- 交付时间：2026-04-15

## 1. 修改文件清单

前端：
- `06_前端/lingyi-pc/src/api/factory_statement.ts`
- `06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementList.vue`
- `06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementDetail.vue`
- `06_前端/lingyi-pc/scripts/check-factory-statement-contracts.mjs`
- `06_前端/lingyi-pc/scripts/test-factory-statement-contracts.mjs`

后端：
- `07_后端/lingyi_service/app/schemas/factory_statement.py`
- `07_后端/lingyi_service/app/services/factory_statement_service.py`
- `07_后端/lingyi_service/tests/test_factory_statement_api.py`
- `07_后端/lingyi_service/tests/test_factory_statement_payable_api.py`

## 2. company 契约修复说明

- `FactoryStatementCreatePayload.company` 已改为必填（`company: string`）。
- 创建弹窗新增 company 输入，提交前校验 company 非空；为空时前端阻止提交。
- `submitCreate` 已显式提交 `company: createForm.company.trim()`。
- 未使用硬编码 company，未从 token/localStorage 推断 company。

## 3. payable outbox 摘要字段清单

已在 list/detail 契约补齐并由后端返回：
- `payable_outbox_id`
- `payable_outbox_status`
- `purchase_invoice_name`
- `payable_error_code`
- `payable_error_message`

detail 额外补齐：
- `payable_outboxes[]`
- `logs[]`

`payable_outboxes[]` 最少字段：
- `id`
- `status`
- `erpnext_purchase_invoice`
- `erpnext_docstatus`
- `erpnext_status`
- `last_error_code`
- `last_error_message`
- `created_at`
- `updated_at`

`logs[]` 最少字段：
- `action`
- `operator`
- `operated_at`
- `remark`

摘要选择规则已落地：按 `created_at desc, id desc` 选最新 outbox。

## 4. list/detail 后端响应样例

### list item 样例

```json
{
  "id": 101,
  "statement_no": "FS202604150001",
  "company": "LY",
  "supplier": "S001",
  "from_date": "2026-04-01",
  "to_date": "2026-04-15",
  "net_amount": "4700.00",
  "statement_status": "confirmed",
  "payable_outbox_id": 5001,
  "payable_outbox_status": "pending",
  "purchase_invoice_name": null,
  "payable_error_code": null,
  "payable_error_message": null
}
```

### detail 样例（关键字段）

```json
{
  "statement_id": 101,
  "statement_no": "FS202604150001",
  "statement_status": "confirmed",
  "payable_outbox_id": 5001,
  "payable_outbox_status": "pending",
  "purchase_invoice_name": null,
  "payable_error_code": null,
  "payable_error_message": null,
  "logs": [
    {
      "action": "create",
      "operator": "u_admin",
      "operated_at": "2026-04-15T11:58:00",
      "remark": "create draft"
    }
  ],
  "payable_outboxes": [
    {
      "id": 5001,
      "status": "pending",
      "erpnext_purchase_invoice": null,
      "erpnext_docstatus": null,
      "erpnext_status": null,
      "last_error_code": null,
      "last_error_message": null,
      "created_at": "2026-04-15T12:00:00",
      "updated_at": "2026-04-15T12:00:00"
    }
  ]
}
```

## 5. 前端按钮 fail-closed 规则说明

详情页已改为 fail closed：
- 若 `payable_outbox_status/purchase_invoice_name` 摘要缺失，则视为摘要未就绪，不放行取消/生成应付草稿按钮。
- `pending/processing/succeeded` 视为 active payable outbox：
  - 取消按钮禁用
  - 生成应付草稿按钮禁用
- 摘要缺失时页面展示告警提示（摘要缺失）。

## 6. 契约门禁新增规则与反向测试场景数

`check-factory-statement-contracts.mjs` 新增/强化：
- 校验 `FactoryStatementCreatePayload` 中 company 必填，禁止 `company?`。
- 校验 list 创建表单存在 company 字段且提交 payload 包含 company。
- 校验 detail/list 类型包含 `payable_outbox_status/purchase_invoice_name`。
- 校验详情页存在 fail-closed 片段，禁止摘要缺失时默认放行。
- 继续保留禁止 internal worker、run-once、/api/resource、裸 fetch、submit PI、Payment Entry、GL Entry 等规则。

`test-factory-statement-contracts.mjs`：
- 反向 fixture 场景总数：`15`
- 新增覆盖：
  - company 可选/缺失
  - 创建弹窗无 company
  - detail 缺 payable 摘要字段
  - 详情页缺 fail-closed 守卫

## 7. 前端自测命令与结果

执行目录：`06_前端/lingyi-pc`

- `npm run check:factory-statement-contracts`：通过
- `npm run test:factory-statement-contracts`：通过（`scenarios=15`）
- `npm run verify`：通过
  - 含 `check/test-production-contracts` 通过
  - 含 `check/test-style-profit-contracts` 通过（`scenarios=475`）
  - 含 `check/test-factory-statement-contracts` 通过
  - `typecheck` 通过
  - `build` 通过
- `npm audit --audit-level=high`：`found 0 vulnerabilities`

前端禁入关键词扫描：
- 在 `src/api/factory_statement.ts`、`src/views/factory_statement/*` 目标文件中，
  `factory-statements/internal|payable-draft-sync/run-once|run-once|/api/resource|submitPurchaseInvoice|Payment Entry|GL Entry|fetch(` 无命中。

## 8. 后端自测命令与结果

执行目录：`07_后端/lingyi_service`

- `.venv/bin/python -m pytest -q tests/test_factory_statement*.py`：`71 passed`
- `.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)`：通过
- `rg -n "submit\(|docstatus\s*=\s*1|Payment Entry|GL Entry|create_payment|submit_purchase_invoice" app tests`
  - factory statement 相关命中仅测试用例中的 `docstatus=1` 异常分支模拟；
  - 未发现 submit、Payment Entry、GL Entry、create_payment、submit_purchase_invoice 实现入口。

## 9. 合规声明

- 未调用 internal worker 接口。
- 未前端直连 ERPNext `/api/resource`。
- 未提交 Purchase Invoice。
- 未创建 Payment Entry / GL Entry。
- `git diff --name-only -- .github 02_源码` 输出为空（未修改 `.github`、`02_源码`）。

## 10. 结论

TASK-006E1 的两个审计阻断项（company 契约缺失、payable 摘要缺失导致门禁误判）已完成修复并通过前后端验证。

结论：建议进入 TASK-006E1 审计复核；是否进入 TASK-006F 需由架构师单独下发，不自动推进。
