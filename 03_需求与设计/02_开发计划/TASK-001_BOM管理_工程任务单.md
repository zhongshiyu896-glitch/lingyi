# TASK-001 BOM 管理工程任务单

- 任务编号：TASK-001
- 模块：BOM 管理
- 优先级：P0（第一阶段核心）
- 预计工时：4-6 天
- 输出人：技术架构师
- 更新时间：2026-04-11 21:55 CST
- 适用工程目录：`/Users/hh/Desktop/领意服装管理系统/`
- 当前状态：待工程师开发

## 1. 任务目标

实现款式物料清单管理，支持尺码配比展开、含损耗的物料需求计算、工序定义，并区分本厂工序和外发工序。

## 2. 业务背景

款式 BOM 是服装工厂 ERP 的基础数据。一个款式在 ERPNext 中对应 `Item`，BOM 管理模块负责为该款式维护面料、辅料、用量、损耗率、尺码配比和加工工序。BOM 展开结果会被采购需求、生产计划、外发加工、工票派工和款式利润报表复用。本任务只做 BOM 管理，不实现外发单、工票、生产计划和利润报表。

## 3. 前置依赖

无。

工程师需要确认：

1. ERPNext 已有 `Item` 数据可供联调。
2. PostgreSQL 中可创建或迁移 `ly_schema` 下的自建表。
3. 后端服务目录为 `/07_后端/lingyi_service/`。
4. 前端服务目录为 `/06_前端/lingyi-pc/`。

## 4. 严格边界

本任务允许：

1. 新建 BOM 相关 FastAPI model、schema、router、service。
2. 新建 BOM 相关 Vue 页面和 API 封装。
3. 修改后端 `main.py` 注册 BOM 路由。
4. 修改前端 `router/index.ts` 注册 BOM 页面。
5. 只读校验 ERPNext `Item`。

本任务禁止：

1. 不修改 `/02_源码/lingyi_apparel/` 历史 app。
2. 不扩展已废弃的 `ys_approval_flow_*`。
3. 不直接写 ERPNext `public` schema 标准表。
4. 不实现外发加工、工票、生产计划、利润报表、加工厂对账。
5. 不把款式资料重复建成 FastAPI 事实表，款式事实源仍为 ERPNext `Item`。

## 5. 涉及文件

新建：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/bom.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/bom.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/bom.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/bom_service.py`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/bom/BomList.vue`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/bom/BomDetail.vue`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/bom.ts`

修改：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/main.py`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/router/index.ts`

如项目已有 Alembic 或迁移目录，新增迁移文件：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/versions/task_001_create_bom_tables.py`

## 6. 数据库表设计

| 表名 | 用途 | 关键字段 | 索引 |
| --- | --- | --- | --- |
| `ly_schema.ly_apparel_bom` | BOM 主表 | `id`, `bom_no`, `item_code`, `version_no`, `is_default`, `status`, `effective_date`, `created_at`, `created_by`, `updated_at`, `updated_by` | `pk_ly_apparel_bom`, `uk_ly_apparel_bom_bom_no`, `idx_ly_apparel_bom_item_default`, `idx_ly_apparel_bom_status`, `uk_ly_apparel_bom_one_active_default` |
| `ly_schema.ly_apparel_bom_item` | BOM 物料明细 | `id`, `bom_id`, `material_item_code`, `color`, `size`, `qty_per_piece`, `loss_rate`, `uom`, `remark` | `pk_ly_apparel_bom_item`, `idx_ly_apparel_bom_item_bom_id`, `idx_ly_apparel_bom_item_material` |
| `ly_schema.ly_bom_operation` | BOM 工序明细 | `id`, `bom_id`, `process_name`, `sequence_no`, `is_subcontract`, `wage_rate`, `subcontract_cost_per_piece`, `remark` | `pk_ly_bom_operation`, `idx_ly_bom_operation_bom_process`, `idx_ly_bom_operation_subcontract` |
| `public.tabItem` | ERPNext 款式/物料事实源 | `name`, `item_code`, `item_name`, `stock_uom`, `item_group`, `disabled` | ERPNext 标准索引 |

字段约束：

1. `ly_apparel_bom.item_code` 对应 ERPNext `Item.name` 或 `Item.item_code`，工程实现时必须统一一种引用口径并写入注释。
2. `ly_apparel_bom.status` 枚举：`draft`、`active`、`inactive`、`archived`。
3. `ly_apparel_bom.is_default` 为布尔值，同一 `item_code` 只能有一个 `is_default=true` 且 `status=active` 的 BOM。
4. PostgreSQL 必须增加部分唯一索引：`CREATE UNIQUE INDEX uk_ly_apparel_bom_one_active_default ON ly_schema.ly_apparel_bom(item_code) WHERE is_default = true AND status = 'active';`
5. `set-default` 必须在事务内执行，并锁定同 `item_code` 的 BOM 集合，防止并发产生多个默认 BOM。
6. `qty_per_piece`、`loss_rate`、`wage_rate`、`subcontract_cost_per_piece` 必须使用 Decimal，不允许使用 float。
7. 所有金额和数量计算保留精度由后端统一处理，前端只展示结果。

## 7. 接口清单

| 接口名称 | HTTP 方法 | 路径 | 入参 | 出参 |
| --- | --- | --- | --- | --- |
| 创建 BOM | POST | `/api/bom/` | `item_code`, `version_no`, `bom_items`, `operations` | `code`, `message`, `data.name` |
| 查询 BOM 列表 | GET | `/api/bom/` | `item_code`, `status`, `page`, `page_size` | `items`, `total`, `page`, `page_size` |
| 获取 BOM 详情 | GET | `/api/bom/{bom_id}` | `bom_id` | `bom`, `items`, `operations` |
| 更新 BOM 草稿 | PUT | `/api/bom/{bom_id}` | `version_no`, `bom_items`, `operations` | `name`, `status`, `updated_at` |
| 设置默认 BOM | POST | `/api/bom/{bom_id}/set-default` | `bom_id` | `name`, `item_code`, `is_default` |
| 发布 BOM | POST | `/api/bom/{bom_id}/activate` | `bom_id` | `name`, `status`, `effective_date` |
| 停用 BOM | POST | `/api/bom/{bom_id}/deactivate` | `bom_id`, `reason` | `name`, `status` |
| 展开 BOM | POST | `/api/bom/{bom_id}/explode` | `order_qty`, `size_ratio` | `material_requirements`, `operation_costs`, `total_material_qty`, `total_operation_cost` |

统一响应：

```json
{
  "code": "0",
  "message": "success",
  "data": {}
}
```

分页响应的 `data` 必须为：

```json
{
  "items": [],
  "total": 0,
  "page": 1,
  "page_size": 20
}
```

## 8. 核心业务规则

1. 款式只能有一个生效的默认 BOM，设置新默认 BOM 时必须自动取消同款式旧默认 BOM。
2. 含损耗用量 = `qty_per_piece × (1 + loss_rate)`。
3. BOM 展开数量 = `尺码订单数量 × qty_per_piece × (1 + loss_rate)`。
4. BOM 展开后必须按 `material_item_code + color + size + uom` 合并物料需求。
5. 本厂工序成本 = `wage_rate × order_qty`。
6. 外发工序成本 = `subcontract_cost_per_piece × order_qty`。
7. BOM 发布后不可直接修改；如需调整，复制生成新版本。
8. `material_item_code` 必须在 ERPNext `Item` 中存在且未禁用。
9. `loss_rate` 必须大于等于 0；`qty_per_piece` 必须大于 0。
10. `is_subcontract=true` 时必须填写 `subcontract_cost_per_piece`；`is_subcontract=false` 时必须填写 `wage_rate`。
11. 禁止使用 `ly_style_*` 表和 `/api/bom/styles`、`/api/bom/style-boms` 接口，BOM 唯一契约为 `ly_apparel_* + /api/bom/`。

## 9. ERPNext 集成要求

| ERPNext 能力 | 调用方式 | 用途 |
| --- | --- | --- |
| `Item` | REST API `GET /api/resource/Item/{name}` | 校验款式和物料存在 |
| `Item` | REST API `GET /api/resource/Item` | BOM 页面选择款式、面料、辅料 |
| `Workflow` | 暂不开发写入，只预留字段 | 后续 BOM 发布审批使用 |

本任务不允许：

1. 不创建 ERPNext `BOM` 标准单据。
2. 不创建 ERPNext `Work Order`。
3. 不创建 ERPNext `Purchase Order`。
4. 不创建 ERPNext `Stock Entry`。

这些动作归后续 TASK-004、TASK-002 或采购模块处理。

## 10. 前端页面要求

页面：

1. `BomList.vue`：BOM 列表，支持按款式、状态筛选，支持分页。
2. `BomDetail.vue`：BOM 新建、编辑、查看、发布、设置默认、展开预览。

交互：

1. 物料明细支持新增、删除、编辑。
2. 工序明细支持新增、删除、编辑。
3. 展开预览必须展示物料需求和工序成本。
4. 默认 BOM 需要有明显标识。
5. 已发布 BOM 页面字段只读，不允许直接编辑。

接口调用：

1. `/src/api/bom.ts` 统一封装所有 BOM 接口。
2. 页面不直接拼接 ERPNext API。
3. 页面统一处理 `{code, message, data}`。

## 11. 开发顺序

1. 建立数据库模型和迁移。
2. 建立 Pydantic schema。
3. 建立 BOM service，先实现创建、查询、详情。
4. 实现设置默认、发布、停用。
5. 实现 BOM 展开算法。
6. 注册 FastAPI router。
7. 实现前端 API 封装。
8. 实现 BOM 列表页和详情页。
9. 补充后端单元测试和接口冒烟测试。
10. 补充前端基础联调验证。

## 12. 测试要求

后端至少覆盖：

1. 创建 BOM 成功。
2. 物料不存在时创建失败。
3. 设置默认 BOM 时旧默认 BOM 自动取消。
4. BOM 展开含损耗计算正确。
5. 外发工序和本厂工序成本计算正确。
6. 已发布 BOM 不允许直接修改。
7. 分页返回结构正确。

前端至少验证：

1. 列表页能显示 BOM 数据。
2. 详情页能新增物料明细和工序明细。
3. 展开预览能显示计算结果。
4. 接口错误时页面展示后端 `message`。

## 13. 验收标准

□ `POST /api/bom/` 能创建 BOM，并返回 `data.name`。

□ `GET /api/bom/` 支持 `page` 和 `page_size`，并返回 `items`、`total`、`page`、`page_size`。

□ `GET /api/bom/{bom_id}` 返回 BOM 主表、物料明细、工序明细。

□ `POST /api/bom/{bom_id}/set-default` 执行后，同一 `item_code` 只有一个默认 BOM。

□ 数据库存在 `uk_ly_apparel_bom_one_active_default` 部分唯一索引，防止并发产生多个 active 默认 BOM。

□ `POST /api/bom/{bom_id}/explode` 输入 `order_qty=100`、`qty_per_piece=2`、`loss_rate=0.05` 时，返回物料需求数量 `210`。

□ 已发布 BOM 调用更新接口时返回业务错误，不允许直接修改。

□ `material_item_code` 不存在于 ERPNext `Item` 时，创建接口返回错误码 `BOM_ITEM_NOT_FOUND`。

□ 前端 BOM 列表页能完成筛选、分页、进入详情。

□ 前端 BOM 详情页能完成保存草稿、设置默认、发布、展开预览。

□ 本任务不修改 `/02_源码/lingyi_apparel/`。

□ 本任务不新增或引用 `ly_style_*` 表、`/api/bom/styles`、`/api/bom/style-boms`。

## 14. 完成后交付物

工程师完成后需要回填：

1. 后端变更文件清单。
2. 前端变更文件清单。
3. 数据库迁移文件名。
4. 接口自测结果。
5. 关键计算样例截图或日志。
6. 未完成项和阻塞点。

## 15. 工程师回报模板

```text
TASK-001 BOM 管理开发完成

后端文件：
- ...

前端文件：
- ...

迁移文件：
- ...

自测结果：
- POST /api/bom/：通过/失败
- GET /api/bom/：通过/失败
- POST /api/bom/{bom_id}/explode：通过/失败

关键计算样例：
- order_qty=100, qty_per_piece=2, loss_rate=0.05, result=210

遗留问题：
- 无 / ...
```
