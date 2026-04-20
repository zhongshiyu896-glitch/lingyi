# TASK-040C 跨模块视图 工程任务单

## 1. 基本信息
- 任务编号：`TASK-040C`
- 任务名称：跨模块视图
- 角色：`B Engineer`
- 优先级：`P1`
- 状态：`待执行（已放行）`
- 前置依赖：`TASK-040B` 审计通过（审计意见书第368份）；`TASK-011_销售库存只读集成设计.md`；质量管理只读/写入/状态机链路已完成至 `TASK-030F`

## 2. 任务目标
构建跨模块只读联合视图，将生产、库存、质量、销售链路串联展示：

1. 生产-库存-质量联合视图：`Work Order -> Stock Entry/库存流水 -> Quality Inspection`
2. 销售-库存-质量联合视图：`Sales Order -> Delivery Note/库存交付事实 -> Quality Inspection`
3. 前端新增跨模块视图页面，以卡片 + 表格展示链路。
4. 全链路只读，不提供任何写操作能力。
5. 所有查询继续执行 `company` 范围过滤与资源权限过滤。

## 3. 设计依据
1. `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-011_销售库存只读集成设计.md`
2. `TASK-040A` 审计意见书第367份：销售库存聚合与满足率只读能力已成立。
3. `TASK-040B` 审计意见书第368份：库存过滤权限增强已通过。
4. 质量管理链 `TASK-030A~030F` 已提供质量检验只读、状态、统计和导出基础。
5. Sprint 3 生产管理只读与工单链路已存在，可复用 `production` 模块现有只读能力。

## 4. 允许范围
### 4.1 后端
允许新增：
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/cross_module_view.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/cross_module_view_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/cross_module_view.py`

允许修改：
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/main.py`（仅用于注册 `cross_module_view` router 与只读动作映射）

### 4.2 前端
允许新增：
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/cross_module.ts`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/cross_module/`

允许修改：
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/router/index.ts`（仅新增跨模块视图路由）

### 4.3 测试
允许新增：
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_cross_module_view.py`

### 4.4 日志
允许修改：
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md`

## 5. 禁止范围
1. 禁止新增任何写接口。
2. 禁止直接写入生产、销售、库存、质量任一业务表。
3. 禁止 ERPNext 写调用。
4. 禁止 outbox / worker / 定时任务。
5. 禁止修改 `.github/**`、`02_源码/**`、`04_生产/**`。
6. 禁止修改既有生产、销售库存、质量模块业务语义。
7. 禁止新增 localStorage 敏感凭据持久化。
8. 禁止 push / remote / PR。

## 6. 必须实现
### 6.1 后端接口
新增只读 router：`/api/cross-module`

#### A. 生产-库存-质量链路
`GET /api/cross-module/work-order-trail/{work_order_id}`

返回结构至少包含：
- `work_order`：工单基本信息
- `stock_entries`：关联库存流水/库存凭证事实列表
- `quality_inspections`：关联质检单列表
- `summary`：投料/产出/合格/不合格/缺陷数量汇总

要求：
- 以 `work_order_id` 为主键线索
- 从现有生产、库存、质量事实中只读聚合
- 找不到时返回统一 404/空链路，不得伪造数据

#### B. 销售-库存-质量链路
`GET /api/cross-module/sales-order-trail/{sales_order_id}`

返回结构至少包含：
- `sales_order`：销售订单基本信息
- `delivery_notes` 或交付/出库事实列表
- `quality_inspections`：关联成品质检/外发回料质检列表
- `summary`：订单数量/出库数量/质检数量/缺陷数量汇总

要求：
- 以 `sales_order_id` 为主键线索
- 从现有销售库存和质量事实中只读聚合
- 不要求新增 ERPNext 写入或同步逻辑

### 6.2 权限与范围
1. 所有接口必须认证。
2. 所有接口必须执行只读权限校验。
3. `company` 范围必须在所有维度生效。
4. 无权限资源不得通过 403/404 差异泄露业务存在性。
5. 权限源不可用时 fail closed。

### 6.3 前端页面
新增跨模块视图页面，至少包含：

1. 生产-库存-质量联合页：
   - 输入 `work_order_id`
   - 查询并展示工单、库存事实、质检记录、汇总卡片

2. 销售-库存-质量联合页：
   - 输入 `sales_order_id`
   - 查询并展示销售订单、交付/库存事实、质检记录、汇总卡片

3. 页面不得出现写操作按钮。
4. 页面必须通过统一 `request` 封装调用后端 API。

## 7. 验收标准
1. `GET /api/cross-module/work-order-trail/{work_order_id}` 返回生产-库存-质量链路。
2. `GET /api/cross-module/sales-order-trail/{sales_order_id}` 返回销售-库存-质量链路。
3. 所有返回数据均执行 `company` 范围过滤。
4. 前端跨模块页面可正常查询并渲染卡片 + 表格。
5. 前端不暴露任何写操作入口。
6. 后端无写接口、无 ERPNext 写调用、无 outbox。
7. `test_cross_module_view.py` 通过。
8. `npm run typecheck` 通过。

## 8. 必跑验证
```bash
cd /Users/hh/Desktop/领意服装管理系统

# 1. 后端跨模块文件存在
test -f 07_后端/lingyi_service/app/routers/cross_module_view.py
test -f 07_后端/lingyi_service/app/services/cross_module_view_service.py
test -f 07_后端/lingyi_service/app/schemas/cross_module_view.py

# 2. 路由存在
rg -n 'work-order-trail|sales-order-trail|APIRouter\(prefix="/api/cross-module"' \
  07_后端/lingyi_service/app/routers/cross_module_view.py

# 3. 前端入口存在
rg -n 'cross-module|work-order-trail|sales-order-trail|生产-库存-质量|销售-库存-质量' \
  06_前端/lingyi-pc/src/api/cross_module.ts \
  06_前端/lingyi-pc/src/views/cross_module \
  06_前端/lingyi-pc/src/router/index.ts

# 4. 后端测试
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest tests/test_cross_module_view.py -v --tb=short

# 5. 前端类型检查
cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc
npm run typecheck

# 6. 只读边界扫描
cd /Users/hh/Desktop/领意服装管理系统
! rg -n '@router\.(post|put|patch|delete)|requests\.(post|put|patch|delete)|httpx\.(post|put|patch|delete)|outbox|worker' \
  07_后端/lingyi_service/app/routers/cross_module_view.py \
  07_后端/lingyi_service/app/services/cross_module_view_service.py

# 7. 禁改目录检查
git -C /Users/hh/Desktop/领意服装管理系统 diff --name-only -- \
  .github 02_源码 04_生产
# 预期为空
```

## 9. 完成回报
完成后仅按以下格式回交，不要回任务单正文：

```md
STATUS: READY_FOR_AUDIT
TASK_ID: TASK-040C
CONTEXT_VERSION: 未提供
ROLE: B

CHANGED_FILES:
- 绝对路径1
- 绝对路径2

EVIDENCE:
- work-order-trail 后端实现：
- sales-order-trail 后端实现：
- company 范围过滤证据：
- 前端跨模块页面证据：
- 只读边界证据：
- 测试覆盖点：

VERIFICATION:
- pytest：
- npm run typecheck：
- 只读边界扫描：
- 禁改目录 diff：

RISKS:
- 无 / 具体残余风险

NEXT_ROLE: C Auditor
```
