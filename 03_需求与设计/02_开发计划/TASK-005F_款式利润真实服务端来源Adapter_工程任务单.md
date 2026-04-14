# TASK-005F 款式利润真实服务端来源 Adapter 工程任务单

- 任务编号：TASK-005F
- 模块：款式利润报表
- 版本：V1.0
- 更新时间：2026-04-14 13:20 CST
- 作者：技术架构师
- 优先级：P0
- 前置依赖：TASK-005E4 审计通过，当前 API 权限审计基线 HEAD `e8654f9`
- 执行角色：后端工程师
- 审计要求：完成后必须提交审计官复审，复审通过前不得进入前端创建入口或 TASK-006

## 1. 任务目标

实现款式利润报表的真实服务端来源 Adapter，让 `POST /api/reports/style-profit/snapshots` 从可信后端事实采集收入、BOM、库存、工票、外发来源，而不是继续停留在 fail-closed 空采集器状态。

本任务只做后端来源采集 Adapter 和测试，不做前端页面，不做 TASK-006 加工厂对账单，不改变 TASK-005B/ADR-079 已冻结的利润公式。

## 2. 背景说明

TASK-005E4 已通过审计，款式利润 API 的登录鉴权、动作权限、资源权限、安全审计、操作审计、统一错误信封和本地提交基线已经稳定。

但当前 `StyleProfitApiSourceCollector` 仍是 fail-closed 基线：所有 `_load_*` 来源方法返回空列表。这样可以保证安全，但不能真正生成可用利润快照。下一步必须实现真实服务端来源 Adapter，并继续保持“来源不可用时 fail closed、来源为空时明确 unresolved、禁止信任前端 payload”的原则。

## 3. 本任务允许修改范围

### 3.1 允许新建

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_style_profit_adapter.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_api_source_adapter.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_source_collector.py`

### 3.2 允许修改

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/style_profit_api_source_collector.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/error_codes.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/style_profit.py`（仅限补充来源 DTO 字段或错误响应需要）
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_api.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_api_errors.py`

### 3.3 禁止修改

- 禁止修改 `/Users/hh/Desktop/领意服装管理系统/06_前端/**`
- 禁止修改 `/Users/hh/Desktop/领意服装管理系统/.github/**`
- 禁止修改 `/Users/hh/Desktop/领意服装管理系统/02_源码/**`
- 禁止修改 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/**`
- 禁止修改或新增任何 `TASK-006*` 文件
- 禁止改动利润计算公式，只允许把可信来源行喂给现有 `StyleProfitSourceService`
- 禁止从前端 payload 接收收入、成本、工票、外发、SLE 明细

## 4. 需要实现的来源 Adapter

### 4.1 ERPNext Style Profit Adapter

新建 `ERPNextStyleProfitAdapter`，负责从 ERPNext REST API 读取利润来源事实。

必须遵守：

1. 使用当前请求用户上下文或现有 ERPNext 接入封装，不允许用全局超级管理员绕过用户权限。
2. ERPNext 服务不可用、认证失败、超时、返回结构不可信时，必须 fail closed，抛出统一业务错误。
3. 不得把 ERPNext 异常原文、SQL、Token、Cookie、Authorization 写入响应或普通日志。
4. 只读取已提交或有效状态的数据，草稿、取消、未知状态一律不得纳入利润。
5. Adapter 返回的是标准化 `dict` 列表，不直接写数据库。

### 4.2 ERPNext 数据源

| 来源 | ERPNext DocType | 纳入口径 | 必需过滤 |
| --- | --- | --- | --- |
| 实际收入 | `Sales Invoice` / `Sales Invoice Item` | 优先收入来源 | `docstatus=1`、`company`、`sales_order`、`item_code`、日期范围 |
| 订单收入 | `Sales Order` / `Sales Order Item` | 无已提交 SI 时的订单口径来源 | `docstatus=1` 或明确已审批状态、`company`、`sales_order`、`item_code` |
| 实际材料成本 | `Stock Ledger Entry` | 实际材料成本唯一主来源 | `company`、日期范围、BOM 允许物料编码、销售/生产桥接字段 |
| 采购参考 | `Purchase Receipt` / `Purchase Receipt Item` | 只做参考和异常追溯，不直接计入实际材料成本 | `docstatus=1`、`company`、日期范围、物料编码 |
| 物料主数据 | `Item` | 物料名称、UOM、估值参考 | `item_code` 精确匹配 |

## 5. 本地 FastAPI 数据源

### 5.1 BOM 来源

从本地 BOM 表读取：

- `ly_schema.ly_apparel_bom`
- `ly_schema.ly_apparel_bom_item`
- `ly_schema.ly_bom_operation`

要求：

1. 必须只读取 `item_code` 对应的 active + default BOM。
2. 找不到 active/default BOM 时返回 `STYLE_PROFIT_BOM_REQUIRED`，不得创建快照。
3. BOM 物料行必须生成 `bom_material_rows`。
4. BOM 工序行必须生成 `bom_operation_rows`。
5. BOM 物料编码必须生成 `allowed_material_item_codes`，供 SLE 过滤使用。
6. BOM 读取数据库异常返回 `DATABASE_READ_FAILED`。

### 5.2 工票来源

从本地工票表读取：

- `ys_workshop_ticket` 或当前模型对应表

要求：

1. 只允许纳入能可信匹配 `company + item_code + sales_order/work_order/job_card` 的工票。
2. 缺 `company` 或缺 `item_code/style_item_code` 时，不得仅凭 `sales_order` 纳入利润。
3. 无法可信归属的工票必须生成 unresolved 来源或不纳入利润，并在 source_map 中留下可追溯原因。
4. 工票撤销必须按净数量口径，不得把撤销数量当正向成本。
5. 不得改变 TASK-005D 已冻结的工票成本计算公式。

### 5.3 外发来源

从本地外发表读取：

- `ly_subcontract_order`
- `ly_subcontract_inspection`
- 必要时读取外发结算/锁定相关表

要求：

1. 必须按 `company + item_code + sales_order/work_order` 做可信归属。
2. 如果外发数据缺少销售订单或生产桥，必须 fail closed 为 unresolved，不得硬计入当前利润。
3. 结算金额优先；无结算时按验货净额兜底，并受 `include_provisional_subcontract` 控制。
4. 已释放、已取消、跨公司、跨款式的外发事实不得纳入利润。
5. 不得进入 TASK-006 对账单实现。

## 6. 统一错误码要求

如现有错误码已存在，优先复用；不存在时补充到 `error_codes.py`。

| 场景 | HTTP | code | 要求 |
| --- | --- | --- | --- |
| ERPNext 来源服务不可用 | 503 | `STYLE_PROFIT_SOURCE_UNAVAILABLE` | 不落半成品 snapshot |
| 收入来源不存在 | 422 | `STYLE_PROFIT_REVENUE_SOURCE_REQUIRED` | 无 SI 且无有效 SO 时返回 |
| active/default BOM 不存在 | 422 | `STYLE_PROFIT_BOM_REQUIRED` | 不创建 snapshot |
| 来源归属不可信 | 422 或 source_map unresolved | `STYLE_PROFIT_SOURCE_UNRESOLVED` | 视是否阻断创建而定，必须可追溯 |
| 数据库读取失败 | 500 | `DATABASE_READ_FAILED` | 不吞异常、不继续生成快照 |
| 客户端提交来源明细 | 400 | 沿用现有客户端来源拒绝错误码 | 禁止信任前端 payload |

## 7. Collector 输出契约

`StyleProfitApiSourceCollector.collect()` 必须返回 `StyleProfitSnapshotCreateRequest`，并满足：

1. `sales_invoice_rows` 来自 ERPNext 已提交 SI。
2. `sales_order_rows` 来自 ERPNext 已提交或已审批 SO。
3. `bom_material_rows` 来自本地 active/default BOM。
4. `bom_operation_rows` 来自本地 active/default BOM 工序。
5. `stock_ledger_rows` 来自 ERPNext SLE，且物料编码必须落在 `allowed_material_item_codes` 内。
6. `purchase_receipt_rows` 只做参考，不直接计入 `actual_material_cost`。
7. `workshop_ticket_rows` 只包含可信归属工票；不可信来源必须 unresolved。
8. `subcontract_rows` 只包含可信归属外发成本；不可信来源必须 unresolved。
9. `allowed_material_item_codes` 必须稳定排序，避免 request_hash 因顺序漂移。
10. 输出中不得包含 `request_id`、当前时间、outbox_id、created_at、operator 等易变字段。

## 8. 幂等与 request_hash 要求

1. 相同 `company + idempotency_key + 完全相同来源输入` 必须 replay 首次响应。
2. 相同 `company + idempotency_key` 但任一来源金额、数量、状态、source_name、source_status、include_in_profit 变化，必须返回幂等冲突，不得 replay 旧快照。
3. 来源行排序必须稳定。
4. request_hash 不得包含请求时间、操作者、request_id、数据库自增 id 等易变字段。
5. 必须补测试证明真实 Adapter 输出参与 request_hash。

## 9. 安全与审计要求

1. API 鉴权、动作权限、资源权限沿用 TASK-005E4，不得回退。
2. Collector fail closed 必须写创建失败操作审计。
3. ERPNext 来源不可用必须写创建失败操作审计，但不得泄露凭据。
4. 资源权限拒绝必须写安全审计。
5. 数据库读取失败必须返回统一错误信封。
6. 任何失败不得写入半成品 snapshot、detail 或 source_map。

## 10. 测试要求

必须补齐以下自动化测试：

1. 已提交 Sales Invoice 优先于 Sales Order。
2. 无 Sales Invoice 时，已提交或已审批 Sales Order 可作为订单收入来源。
3. Draft/Cancelled/未知状态 SI/SO 不得纳入利润。
4. ERPNext 服务不可用时返回 `STYLE_PROFIT_SOURCE_UNAVAILABLE`，不创建 snapshot。
5. 无 SI 且无有效 SO 时返回 `STYLE_PROFIT_REVENUE_SOURCE_REQUIRED`。
6. active/default BOM 存在时，生成 BOM 物料、工序和 `allowed_material_item_codes`。
7. active/default BOM 不存在时返回 `STYLE_PROFIT_BOM_REQUIRED`，不创建 snapshot。
8. SLE 只允许 BOM 物料编码进入实际材料成本来源。
9. SLE 查询不可用时 fail closed，不创建 snapshot。
10. Purchase Receipt 行只进入参考 source_map，不直接进入实际材料成本。
11. 工票缺 `company` 或缺 `item_code/style_item_code` 时，不得仅凭 `sales_order` 纳入利润。
12. 外发缺可信销售/生产桥时，不得纳入当前利润。
13. 客户端传入来源明细仍被拒绝，不能绕过服务端采集。
14. 相同幂等键不同来源输入返回幂等冲突。
15. Collector 输出排序稳定，request_hash 稳定。
16. 失败路径不写半成品 snapshot/detail/source_map。
17. API 定向 pytest、全量 pytest、unittest、py_compile 全部通过。

## 11. 建议命令

在 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service` 执行：

```bash
.venv/bin/python -m pytest -q tests/test_style_profit_api.py tests/test_style_profit_api_errors.py tests/test_style_profit_api_source_adapter.py tests/test_style_profit_source_collector.py
.venv/bin/python -m pytest -q
.venv/bin/python -m unittest discover
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
```

## 12. 禁改扫描要求

交付前必须确认以下目录没有本任务无关改动：

```bash
git status --short -- 06_前端 .github 02_源码 07_后端/lingyi_service/migrations 03_需求与设计/02_开发计划/TASK-006*
```

预期：无 TASK-005F 以外改动。

## 13. 验收标准

□ `StyleProfitApiSourceCollector` 不再是空采集器，至少收入、BOM、SLE、工票、外发来源路径具备真实读取或明确 fail-closed 行为。  
□ `POST /api/reports/style-profit/snapshots` 在可信 SI/SO + active/default BOM 存在时，可生成非空来源快照。  
□ ERPNext 来源不可用时返回 `503 + STYLE_PROFIT_SOURCE_UNAVAILABLE`，不创建 snapshot。  
□ 无收入来源时返回 `STYLE_PROFIT_REVENUE_SOURCE_REQUIRED`，不创建 snapshot。  
□ 无 active/default BOM 时返回 `STYLE_PROFIT_BOM_REQUIRED`，不创建 snapshot。  
□ SLE 实际材料成本只使用 BOM 允许物料编码。  
□ Purchase Receipt 不直接计入 actual material cost。  
□ 工票和外发缺关键归属字段时不被纳入利润。  
□ 客户端来源明细仍被拒绝。  
□ 相同幂等键不同来源输入返回冲突。  
□ 失败路径写操作审计或安全审计，且不泄露敏感信息。  
□ 定向 pytest、全量 pytest、unittest、py_compile 通过。  
□ 禁改扫描通过，未触碰前端、`.github`、`02_源码`、migrations、TASK-006。  
□ 审计官复审通过后，才允许评估 TASK-005G 前端只读/创建入口联调。  

## 14. 交付物

1. 后端 Adapter 和 Collector 代码。
2. 新增/更新测试。
3. 工程师交付说明，必须列出：
   - 修改文件清单
   - 真实来源支持矩阵
   - fail-closed 场景
   - 验证命令与结果
   - 禁改扫描结果
4. 不需要提交前端页面。
5. 不需要提交 TASK-006 任何内容。
