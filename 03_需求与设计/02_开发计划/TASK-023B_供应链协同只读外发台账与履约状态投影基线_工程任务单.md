# TASK-023B 供应链协同只读外发台账与履约状态投影基线 工程任务单

## 1. 基本信息

- 任务编号：TASK-023B
- 任务名称：供应链协同只读外发台账与履约状态投影基线
- 角色：架构师
- 优先级：P1
- 状态：待审计
- 前置依赖：TASK-023A 审计通过（审计意见书第 215 份）

## 2. 任务目标

基于 `TASK-023A` 已冻结的供应链协同边界，以及当前仓库中已存在的 `subcontract` 模块代码，输出供应链协同实现链第一张任务单，范围限定为“只读外发台账 + 履约状态投影 + 前端普通入口去写化”收口：

1. 保留并收口外发单列表 / 详情、供应商维度过滤、状态标签、`resource_scope_status`、发料/回料同步状态、回料批次和验货明细等只读投影能力。
2. 明确普通前端当前只允许供应链只读查看，不得继续暴露 `新建外发单`、`提交发料`、`登记回料`、`完成验货`、`重试同步` 等候选写入口。
3. 明确 `/internal/stock-sync/run-once`、`issue-material`、`receive`、`inspect`、`stock-sync/retry` 仍属于冻结能力，不得在当前任务中被解释为可对普通前端放行。
4. 本任务只形成可审计工程任务边界；在 `build_release_allowed=no` 条件下，不直接放行 B 实现。

## 2.1 当前门禁状态

1. `TASK-023A` 已于审计意见书第 215 份通过，允许进入供应链协同实现任务拆分。
2. `TASK-021B -> TASK-021D` 与 `TASK-022B -> TASK-022D` 已完成任务单审计收口，但当前并不构成供应链实现链的额外前置门禁。
3. 当前 `build_release_allowed=no`，本任务仍需先交 C 复核边界、验收标准、允许 / 禁止范围；C 未 PASS 前不得进入 B 实现。
4. 即使 `TASK-023B` 任务单通过，也只表示供应链协同实现链第一张任务单拆分完成；除非后续 Context Pack 明确 `build_release_allowed=yes`，否则仍不得放行 B。

## 2.2 已确认的现状基础

当前仓库中与 `TASK-023B` 直接相关的供应链协同基础代码已存在，不得按“从零新建模块”口径重复立项：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/subcontract.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/subcontract_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/subcontract.py`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/subcontract.ts`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/subcontract/SubcontractOrderList.vue`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/subcontract/SubcontractOrderDetail.vue`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_list_summary.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_permissions.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_audit.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_exception_handling.py`

已核实的当前真实现状：

1. 前端已存在 `/subcontract/list` 与 `/subcontract/detail` 路径，对应列表页与详情页。
2. `subcontract` 列表 / 详情读侧已暴露 `resource_scope_status`、`latest_issue_sync_status`、`latest_receipt_sync_status`、`receipts`、`inspections` 等只读投影字段。
3. 当前普通前端页面仍存在 `新建外发单`、`提交发料`、`登记回料`、`完成验货`、`重试同步` 等候选写入口，尚未按 `TASK-023A` 收口为只读协同基线。
4. 后端当前已存在 `POST /{order_id}/issue-material`、`POST /{order_id}/receive`、`POST /{order_id}/inspect`、`POST /{order_id}/stock-sync/retry` 与 `/internal/stock-sync/run-once` 等候选写 / worker 路径，本任务不得将这些路径解释为已开放给普通前端。

因此本任务的核心是：

1. 把现有 `subcontract` 模块收口到“只读外发台账 + 履约状态投影”边界。
2. 保留供应商、状态、同步状态、回料 / 验货事实的可见性，但不让普通前端继续触发写链路。
3. 保持 `resource_scope_status`、权限校验、fail-closed 和统一错误包络不被破坏。
4. 不触碰库存 / 财务写链路、Outbox worker 执行链、Factory Statement 应付草稿链路和平台发布语义。

## 2.3 设计依据

1. `TASK-023A` 已冻结：供应商协同、采购协同、物流跟踪当前只允许只读事实与协同状态投影，写入候选必须后续单独任务、单独审计、单独放行。
2. `TASK-023A` 已明确：所有 ERPNext 交互统一经 `TASK-008 Adapter`，所有写入候选统一经 `TASK-009 Outbox`，未放行能力保持冻结。
3. `TASK-023A` 已明确：普通前端禁止暴露 `diagnostic / worker / internal / run-once` 类入口，所有写入候选按钮默认隐藏。
4. `Sprint3_主执行计划.md` 明确供应链协同实现链路为 `023B -> 023C -> 023D`。

## 3. 允许范围

> 以下为后续 B 实现候选范围；本轮 A 仅输出任务单，不修改实现。

1. 允许修改以下后端文件：
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/subcontract.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/subcontract_service.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/subcontract.py`
2. 允许修改以下前端文件：
   - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/subcontract.ts`
   - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/subcontract/SubcontractOrderList.vue`
   - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/subcontract/SubcontractOrderDetail.vue`
3. 允许补充与只读列表 / 详情、权限门禁、异常包络和审计相关的最小测试：
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_list_summary.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_permissions.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_audit.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_exception_handling.py`
4. 允许同步更新当前任务单与 C 复核指令。

## 4. 禁止范围

1. 禁止修改 `07_后端/lingyi_service/app/services/subcontract_stock_outbox_service.py`、`07_后端/lingyi_service/app/services/subcontract_stock_worker_service.py`、`07_后端/lingyi_service/app/services/erpnext_stock_entry_service.py` 的真实写执行语义。
2. 禁止修改 `07_后端/lingyi_service/app/routers/factory_statement.py`、`07_后端/lingyi_service/app/services/factory_statement_*`、`06_前端/lingyi-pc/src/api/factory_statement.ts` 与 `06_前端/lingyi-pc/src/views/factory_statement/**`，这些属于后续供应链子任务范围。
3. 禁止放开 `/api/subcontract/{order_id}/issue-material`、`/receive`、`/inspect`、`/stock-sync/retry` 到普通前端用户的真实执行路径。
4. 禁止放开 `/api/subcontract/internal/stock-sync/run-once` 到普通前端或非内部 worker 主体。
5. 禁止引入 ERPNext / Frappe `/api/resource` 直连。
6. 禁止新增供应商门户、物流服务商、采购协同中台真实外部集成。
7. 禁止修改 `.github/**`、`02_源码/**`、新增并行供应链独立仓库或独立前端工程。
8. 禁止设置 `build_release_allowed=yes`、禁止放行 B、禁止 push / remote / PR / 生产发布。

## 5. 必须输出

1. 外发单列表 / 详情继续可用，并保持供应商、状态、`resource_scope_status`、发料同步状态、回料同步状态、回料批次、验货明细等只读投影能力。
2. `resource_scope_status=blocked_scope`、权限不足、资源不存在、上游异常时，继续保持 fail-closed 和受控错误语义，不得伪成功。
3. 普通前端路径不得再展示 `新建外发单`、`提交发料`、`登记回料`、`完成验货`、`重试发料同步`、`重试回料同步` 等候选写入口。
4. 普通前端不得直调 `/internal/stock-sync/run-once`、`issue-material`、`receive`、`inspect`、`stock-sync/retry`；这些能力在当前任务中保持冻结。
5. 不得记录敏感凭据、服务账号密钥、ERPNext 凭据原文。

## 6. 验收标准

1. 任务实现候选范围不包含 worker / outbox / adapter 真实写执行文件、Factory Statement 应付草稿链路、`.github/**`、`02_源码/**`。
2. 外发单列表 / 详情与履约状态投影仍可用，且 `resource_scope_status`、同步状态、回料 / 验货事实仍可见。
3. 普通前端页面不存在 `新建外发单`、`提交发料`、`登记回料`、`完成验货`、`重试同步` 的可触发按钮或表单卡片。
4. 不存在 ERPNext / Frappe `/api/resource` 直连，不存在普通前端对 `/internal/stock-sync/run-once` 的调用。
5. 不存在新增供应商门户 / 物流服务商真实外部接入。
6. C 对本任务单出具正式复核结论前，不得放行 B。

## 7. 验证命令

```bash
cd /Users/hh/Desktop/领意服装管理系统
rg -n "/subcontract/list|/subcontract/detail|resource_scope_status|latest_issue_sync_status|latest_receipt_sync_status|receipt_batch_no|inspection_no" \
  '06_前端/lingyi-pc/src/router/index.ts' \
  '07_后端/lingyi_service/app/routers/subcontract.py' \
  '07_后端/lingyi_service/app/services/subcontract_service.py' \
  '07_后端/lingyi_service/app/schemas/subcontract.py' \
  '06_前端/lingyi-pc/src/api/subcontract.ts' \
  '06_前端/lingyi-pc/src/views/subcontract/SubcontractOrderList.vue' \
  '06_前端/lingyi-pc/src/views/subcontract/SubcontractOrderDetail.vue'
rg -n "新建外发单|提交发料|登记回料|完成验货|重试发料同步|重试回料同步|openCreateDialog|createOrder|issueMaterial|receive\(|inspect\(|retrySync|/internal/stock-sync/run-once|issue-material|stock-sync/retry|/receive|/inspect" \
  '06_前端/lingyi-pc/src/views/subcontract/SubcontractOrderList.vue' \
  '06_前端/lingyi-pc/src/views/subcontract/SubcontractOrderDetail.vue' \
  '07_后端/lingyi_service/app/routers/subcontract.py' || true
rg -n "(/api/resource|diagnostic|worker|run-once)" \
  '06_前端/lingyi-pc/src/api/subcontract.ts' \
  '06_前端/lingyi-pc/src/views/subcontract' || true
pytest -q \
  '/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_list_summary.py' \
  '/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_permissions.py' \
  '/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_audit.py' \
  '/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_exception_handling.py'
npm --prefix '06_前端/lingyi-pc' run typecheck
git diff --name-only -- \
  '07_后端/lingyi_service/app/routers/subcontract.py' \
  '07_后端/lingyi_service/app/services/subcontract_service.py' \
  '07_后端/lingyi_service/app/schemas/subcontract.py' \
  '06_前端/lingyi-pc/src/api/subcontract.ts' \
  '06_前端/lingyi-pc/src/views/subcontract' \
  '07_后端/lingyi_service/app/services/subcontract_stock_outbox_service.py' \
  '07_后端/lingyi_service/app/services/subcontract_stock_worker_service.py' \
  '07_后端/lingyi_service/app/services/erpnext_stock_entry_service.py' \
  '07_后端/lingyi_service/app/routers/factory_statement.py' \
  '06_前端/lingyi-pc/src/views/factory_statement' \
  '.github' '02_源码'
```

## 8. 完成回报

```text
TASK-023B 执行完成。
结论：待审计
是否仍限定为只读外发台账 + 履约状态投影：是 / 否
普通前端是否仍显示新建 / 发料 / 回料 / 验货 / 重试按钮：是 / 否
是否仍存在 resource_scope_status / 同步状态 / 回料批次 / 验货明细只读投影：是 / 否
是否直连 ERPNext/Frappe：否
是否放开 internal/worker/run-once：否
是否修改 worker/outbox/factory_statement/.github/02_源码：否
是否 push/remote/PR：否
```
