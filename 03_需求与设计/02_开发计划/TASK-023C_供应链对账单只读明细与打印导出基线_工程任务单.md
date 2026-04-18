# TASK-023C 供应链对账单只读明细与打印导出基线 工程任务单

## 1. 基本信息

- 任务编号：TASK-023C
- 任务名称：供应链对账单只读明细与打印导出基线
- 角色：架构师
- 优先级：P1
- 状态：待审计
- 前置依赖：TASK-023A 审计通过（审计意见书第 215 份）；TASK-023B 任务单复核通过（审计意见书第 240 份）

## 2. 任务目标

基于 `TASK-023A` 已冻结的供应链协同边界，以及 `TASK-023B` 已完成的外发台账只读基线，输出供应链协同实现链第二张任务单，范围限定为“加工厂对账单列表 / 详情 / 打印 / 导出只读基线 + 普通前端去写化”收口：

1. 保留并收口加工厂对账单列表、详情、打印页、CSV 导出、`statement_status`、`payable_outbox_status`、`purchase_invoice_name`、明细行与操作日志等只读投影能力。
2. 明确普通前端当前只允许读取对账单事实与只读导出，不得继续暴露 `生成对账单草稿`、`确认对账单`、`取消对账单`、`生成应付草稿` 等候选写入口。
3. 明确 `POST /api/factory-statements/`、`/{statement_id}/confirm`、`/{statement_id}/cancel`、`/{statement_id}/payable-draft`、`/internal/payable-draft-sync/run-once` 仍属于冻结能力，不得在当前任务中被解释为对普通前端放行。
4. 本任务只形成可审计工程任务边界；在 `build_release_allowed=no` 条件下，不直接放行 B 实现。

## 2.1 当前门禁状态

1. `TASK-023A` 已于审计意见书第 215 份通过，允许进入供应链协同实现任务拆分。
2. `TASK-023B` 已于审计意见书第 240 份通过，外发台账、履约状态投影与普通前端去写化边界已完成正式任务单收口。
3. 当前 `build_release_allowed=no`，本任务仍需先交 C 复核边界、验收标准、允许 / 禁止范围；C 未 PASS 前不得进入 B 实现。
4. 即使 `TASK-023C` 任务单通过，也只表示供应链协同实现链第二张任务单拆分完成；除非后续 Context Pack 明确 `build_release_allowed=yes`，否则仍不得放行 B。

## 2.2 已确认的现状基础

当前仓库中与 `TASK-023C` 直接相关的供应链对账单基础代码已存在，不得按“从零新建模块”口径重复立项：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/factory_statement.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/factory_statement_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/factory_statement.py`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/factory_statement.ts`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementList.vue`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementDetail.vue`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementPrint.vue`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/utils/factoryStatementExport.ts`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_factory_statement_api.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_factory_statement_permissions.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_factory_statement_audit.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_factory_statement_idempotency.py`

已核实的当前真实现状：

1. 前端已存在 `/factory-statements/list`、`/factory-statements/detail`、打印页路由，以及对应列表 / 详情 / 打印组件。
2. `factory_statement` 读侧已暴露 `statement_status`、`payable_outbox_status`、`purchase_invoice_name`、`items`、`logs`、`payable_outboxes` 等只读投影字段。
3. 当前普通前端页面仍存在 `生成对账单草稿`、`确认对账单`、`取消对账单`、`生成应付草稿` 等候选写入口，尚未按 `TASK-023A` 收口为只读协同基线。
4. 后端当前已存在 `POST /api/factory-statements/`、`POST /{statement_id}/confirm`、`POST /{statement_id}/cancel`、`POST /{statement_id}/payable-draft` 与 `/internal/payable-draft-sync/run-once` 等候选写 / worker 路径，本任务不得将这些路径解释为已开放给普通前端。

因此本任务的核心是：

1. 把现有 `factory_statement` 模块收口到“对账单列表 / 详情 / 打印 / 导出只读基线”边界。
2. 保留对账单状态、应付草稿同步状态、ERP 发票草稿名、明细行、日志与打印导出能力，但不让普通前端继续触发写链路。
3. 保持权限校验、fail-closed、CSV 导出安全处理和统一错误包络不被破坏。
4. 不触碰对账单草稿创建、确认 / 取消、应付草稿 outbox、内部 worker、Factory Statement payable 同步执行链和平台发布语义。

## 2.3 设计依据

1. `TASK-023A` 已冻结：供应链协同当前只允许只读事实、协同状态与受控导出；写入候选必须后续单独任务、单独审计、单独放行。
2. `TASK-023A` 已明确：普通前端禁止暴露 `diagnostic / worker / internal / run-once` 类入口，所有写入候选按钮默认隐藏。
3. `TASK-023A` 已明确：所有 ERPNext 交互统一经 `TASK-008 Adapter`，所有写入候选统一经 `TASK-009 Outbox`，未放行能力保持冻结。
4. `Sprint3_主执行计划.md` 明确供应链协同实现链路为 `023B -> 023C -> 023D`。

## 3. 允许范围

> 以下为后续 B 实现候选范围；本轮 A 仅输出任务单，不修改实现。

1. 允许修改以下后端文件：
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/factory_statement.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/factory_statement_service.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/factory_statement.py`
2. 允许修改以下前端文件：
   - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/factory_statement.ts`
   - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementList.vue`
   - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementDetail.vue`
   - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementPrint.vue`
   - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/utils/factoryStatementExport.ts`
3. 允许补充与只读列表 / 详情 / 打印 / 导出、权限门禁、异常包络和审计相关的最小测试：
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_factory_statement_api.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_factory_statement_permissions.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_factory_statement_audit.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_factory_statement_idempotency.py`
4. 允许同步更新当前任务单与 C 复核指令。

## 4. 禁止范围

1. 禁止修改 `07_后端/lingyi_service/app/services/factory_statement_payable_outbox_service.py`、`07_后端/lingyi_service/app/services/factory_statement_payable_worker.py`、`07_后端/lingyi_service/app/services/erpnext_purchase_invoice_adapter.py` 的真实写执行语义。
2. 禁止修改 `07_后端/lingyi_service/app/services/subcontract_settlement_service.py`、`07_后端/lingyi_service/app/routers/subcontract.py` 中的 `settlement-locks` / `release` 锁定语义；这些属于后续供应链子任务范围。
3. 禁止放开 `POST /api/factory-statements/`、`/{statement_id}/confirm`、`/{statement_id}/cancel`、`/{statement_id}/payable-draft` 到普通前端用户的真实执行路径。
4. 禁止放开 `/api/factory-statements/internal/payable-draft-sync/run-once` 到普通前端或非内部 worker 主体。
5. 禁止引入 ERPNext / Frappe `/api/resource` 直连。
6. 禁止新增供应商门户、物流服务商、采购协同中台真实外部集成。
7. 禁止修改 `.github/**`、`02_源码/**`、新增并行供应链独立仓库或独立前端工程。
8. 禁止设置 `build_release_allowed=yes`、禁止放行 B、禁止 push / remote / PR / 生产发布。

## 5. 必须输出

1. 对账单列表 / 详情 / 打印 / CSV 导出继续可用，并保持 `statement_status`、`payable_outbox_status`、`purchase_invoice_name`、明细行和操作日志等只读投影能力。
2. 权限不足、资源不存在、应付摘要缺失、上游异常时，继续保持 fail-closed 和受控错误语义，不得伪成功。
3. 普通前端路径不得再展示 `生成对账单草稿`、`确认对账单`、`取消对账单`、`生成应付草稿` 等候选写入口。
4. 普通前端不得直调 `/internal/payable-draft-sync/run-once`；`payable_outbox_status` 与 `purchase_invoice_name` 仅能作为只读投影呈现。
5. 导出与打印不得泄露敏感凭据、服务账号密钥、ERPNext 凭据原文，CSV 导出继续具备公式注入防护。

## 6. 验收标准

1. 任务实现候选范围不包含 payable outbox / worker / adapter 真实写执行文件、subcontract settlement lock/release、`.github/**`、`02_源码/**`。
2. 对账单列表 / 详情 / 打印 / 导出仍可用，且 `statement_status`、`payable_outbox_status`、`purchase_invoice_name`、明细行、操作日志仍可见。
3. 普通前端页面不存在 `生成对账单草稿`、`确认对账单`、`取消对账单`、`生成应付草稿` 的可触发按钮或表单弹窗入口。
4. 不存在 ERPNext / Frappe `/api/resource` 直连，不存在普通前端对 `/internal/payable-draft-sync/run-once` 的调用。
5. 不存在新增供应商门户 / 物流服务商 / 采购协同中台真实外部接入。
6. C 对本任务单出具正式复核结论前，不得放行 B。

## 7. 验证命令

```bash
cd /Users/hh/Desktop/领意服装管理系统
rg -n "/factory-statements/list|/factory-statements/detail|FactoryStatementPrint|statement_status|payable_outbox_status|purchase_invoice_name|logs|items|payable_outboxes" \
  '06_前端/lingyi-pc/src/router/index.ts' \
  '07_后端/lingyi_service/app/routers/factory_statement.py' \
  '07_后端/lingyi_service/app/services/factory_statement_service.py' \
  '07_后端/lingyi_service/app/schemas/factory_statement.py' \
  '06_前端/lingyi-pc/src/api/factory_statement.ts' \
  '06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementList.vue' \
  '06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementDetail.vue' \
  '06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementPrint.vue' \
  '06_前端/lingyi-pc/src/utils/factoryStatementExport.ts'
rg -n "生成对账单草稿|确认对账单|取消对账单|生成应付草稿|openCreateDialog|submitCreate|openConfirmDialog|submitConfirm|openCancelDialog|submitCancel|openPayableDialog|submitPayableDraft|/internal/payable-draft-sync/run-once|/payable-draft|/confirm|/cancel" \
  '06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementList.vue' \
  '06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementDetail.vue' \
  '07_后端/lingyi_service/app/routers/factory_statement.py' || true
rg -n "(/api/resource|worker|run-once|payable-draft-sync)" \
  '06_前端/lingyi-pc/src/api/factory_statement.ts' \
  '06_前端/lingyi-pc/src/views/factory_statement' || true
pytest -q \
  '/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_factory_statement_api.py' \
  '/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_factory_statement_permissions.py' \
  '/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_factory_statement_audit.py' \
  '/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_factory_statement_idempotency.py'
npm --prefix '06_前端/lingyi-pc' run typecheck
git diff --name-only -- \
  '07_后端/lingyi_service/app/routers/factory_statement.py' \
  '07_后端/lingyi_service/app/services/factory_statement_service.py' \
  '07_后端/lingyi_service/app/schemas/factory_statement.py' \
  '06_前端/lingyi-pc/src/api/factory_statement.ts' \
  '06_前端/lingyi-pc/src/views/factory_statement' \
  '06_前端/lingyi-pc/src/utils/factoryStatementExport.ts' \
  '07_后端/lingyi_service/app/services/factory_statement_payable_outbox_service.py' \
  '07_后端/lingyi_service/app/services/factory_statement_payable_worker.py' \
  '07_后端/lingyi_service/app/services/erpnext_purchase_invoice_adapter.py' \
  '07_后端/lingyi_service/app/services/subcontract_settlement_service.py' \
  '.github' '02_源码'
```

## 8. 完成回报

```text
TASK-023C 执行完成。
结论：待审计
是否仍限定为对账单列表/详情/打印/导出只读基线：是 / 否
普通前端是否仍显示生成草稿 / 确认 / 取消 / 生成应付草稿按钮：是 / 否
是否仍存在 statement_status / payable_outbox_status / purchase_invoice_name / 明细行 / 日志只读投影：是 / 否
是否直连 ERPNext/Frappe：否
是否放开 payable-draft/internal worker：否
是否修改 payable outbox / worker / adapter / settlement lock / .github / 02_源码：否
是否 push/remote/PR：否
```
