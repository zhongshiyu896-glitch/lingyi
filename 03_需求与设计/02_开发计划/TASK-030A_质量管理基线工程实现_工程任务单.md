# TASK-030A 质量管理基线 工程任务单

## 1. 基本信息

- 任务编号：TASK-030A
- 任务名称：质量管理基线工程实现
- 角色：架构师
- 优先级：P0
- 状态：待审计
- 前置依赖：`TASK-012_质量管理基线设计.md` 设计冻结（HEAD `ab5ea7bb12b7f05904eccbdda4a6cecfd7bd0614`，对应 Sprint 4 文本中引用的 `TASK-012A`）；`TASK-007` 权限与审计基座（审计意见书第175份）

## 2. 任务目标

基于仓库中已存在的 `quality` 模块代码基础，对质量管理第一阶段做 Phase 1 收口：

1. 保留并校正只读能力：列表 / 详情 / 统计 / 导出。
2. 冻结现有写入口：创建 / 修改 / 确认 / 取消在本任务内不得继续向普通前端提供真实可用写能力。
3. 将 ERPNext 主数据读取从质量模块业务服务中的直接 `/api/resource` 调用收口到专用 fail-closed 适配层。
4. 让 `TASK-030A` 成为与 Sprint 3 四条主线同层级的“只读先行”基线任务，而不是绿地新建模块。

本任务只形成可审计工程实现边界；当前不直接放行 B 实现。

## 3. 设计依据

1. [`TASK-012_质量管理基线设计.md`](/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-012_质量管理基线设计.md) 已冻结质量管理 Phase 1 设计，包含数据模型、状态机、业务规则、权限动作、ERPNext fail-closed 和前端门禁要求。
2. `TASK-007`（审计意见书第175份）已建立 `quality:read/create/update/confirm/cancel/export/diagnostic` 动作权限规范。
3. 仓库现状已存在质量模块基础：
   - `07_后端/lingyi_service/app/models/quality.py`
   - `07_后端/lingyi_service/app/schemas/quality.py`
   - `07_后端/lingyi_service/app/services/quality_service.py`
   - `07_后端/lingyi_service/app/routers/quality.py`
   - `06_前端/lingyi-pc/src/api/quality.ts`
   - `06_前端/lingyi-pc/src/views/quality/QualityInspectionList.vue`
   - `06_前端/lingyi-pc/src/views/quality/QualityInspectionDetail.vue`
4. Sprint 4 规划草案（审计意见书第293份）已将质量管理列为最高优先级（P0）方向；`TASK-030A` 应沿用 Sprint 3 的“先只读基线，再拆写入口，再拆 ERPNext 写联动”节奏。

## 4. 允许范围

### 4.1 后端（FastAPI）

允许在现有质量模块基础上增量收口，不得重建并行质量模块：

1. 允许修改现有质量模型与服务：
   - `07_后端/lingyi_service/app/models/quality.py`
   - `07_后端/lingyi_service/app/schemas/quality.py`
   - `07_后端/lingyi_service/app/services/quality_service.py`
   - `07_后端/lingyi_service/app/routers/quality.py`
2. 允许新增或接入只读 ERPNext 适配层：
   - 允许新建 `07_后端/lingyi_service/app/services/erpnext_quality_adapter.py`
   - 或在现有 `erpnext_fail_closed_adapter.py` 体系上接入质量模块只读校验
3. 允许在必要时新增增量迁移：
   - `07_后端/lingyi_service/migrations/versions/task_030a_*.py`
   - 仅允许做字段 / 约束 / 索引增量修正；禁止重建 `ly_quality_*` 四张表
4. 允许在必要时微调权限映射落点：
   - `07_后端/lingyi_service/app/services/permission_service.py`
   - `07_后端/lingyi_service/app/core/permissions.py`
   - 仅限对齐 `quality:*` 既有动作和 Phase 1 冻结语义，不得扩展新动作

### 4.2 前端（现有质量页面与共享 API）

1. 允许修改现有共享 API：
   - `06_前端/lingyi-pc/src/api/quality.ts`
2. 允许收口现有质量页面写入口：
   - `06_前端/lingyi-pc/src/views/quality/QualityInspectionList.vue`
   - `06_前端/lingyi-pc/src/views/quality/QualityInspectionDetail.vue`
3. 禁止新建质量页面；禁止新增质量模块 router 路由；禁止扩展到非质量页面

### 4.3 测试文件

允许修改或补充质量模块测试，但必须落在现有质量测试集合：

- `07_后端/lingyi_service/tests/test_quality_api.py`
- `07_后端/lingyi_service/tests/test_quality_models.py`
- 允许新增 `07_后端/lingyi_service/tests/test_quality_*baseline.py`
- 允许新增 `07_后端/lingyi_service/tests/test_quality_*fail_closed.py`

## 5. 禁止范围

1. 禁止把质量模块再次按“绿地新建”方式重做；禁止新建并行 `quality_v2` / `quality_baseline` 模块。
2. 禁止新增普通前端可用的创建 / 修改 / 确认 / 取消真实写能力。
3. 禁止新增或恢复 ERPNext Stock Entry / Purchase Receipt / Delivery Note 写入。
4. 禁止新增或恢复 ERPNext GL / Payment / Purchase Invoice 写入。
5. 禁止引入 outbox、自动扣款结算、自动返工工单、自动报废入账。
6. 禁止实现 AQL 抽样算法深度版本、供应商绩效评分。
7. 禁止在 `routers/quality.py`、`services/quality_service.py`、`src/api/quality.ts`、`src/views/quality/**` 中继续保留 ERPNext `/api/resource` 直连字面量；如需主数据只读校验，必须经专用 fail-closed adapter。
8. 禁止新增本地持久化 Authorization / Cookie / Token / Secret 明文。
9. 禁止新增或修改 `06_前端/lingyi-pc/src/router/**`、`.github/**`、`02_源码/**`、`04_生产/**`。
10. 禁止设置 `build_release_allowed=yes`、禁止以本任务单直接放行 B、禁止 push / remote / PR。
11. 禁止声明质量管理已完成生产联调、已发布完成。

## 6. 必须输出

### 6.1 既有数据模型收口（必须实现）

1. 以现有四张质量表模型为唯一基线，不得重建：
   - `LyQualityInspection`
   - `LyQualityInspectionItem`
   - `LyQualityDefect`
   - `LyQualityOperationLog`
2. 如与 Phase 1 要求有差异，仅允许增量修正字段 / 约束 / 索引。
3. 必须继续覆盖以下核心字段语义：
   - `company`
   - `inspection_no`
   - `source_type`
   - `source_id`
   - `item_code`
   - `supplier`
   - `warehouse`
   - `work_order`
   - `sales_order`
   - `inspection_date`
   - `inspected_qty`
   - `accepted_qty`
   - `rejected_qty`
   - `defect_qty`
   - `result`
   - `status`
   - `created_by`
   - `confirmed_by`
   - `confirmed_at`

### 6.2 后端接口收口（必须实现）

1. 以下 GET 接口必须保持可用，并继续执行资源过滤：
   - `GET /api/quality/inspections`
   - `GET /api/quality/inspections/{id}`
   - `GET /api/quality/statistics`
   - `GET /api/quality/export`
2. 现有写接口不得继续执行业务写逻辑。允许两种收口方式，但必须在代码与测试中固定其一：
   - 方案 A：从普通路由层移除 `POST / PATCH / confirm / cancel` 暴露；
   - 方案 B：路由保留，但统一返回冻结错误信封（建议错误码固定为 `QUALITY_WRITE_FROZEN`），且不得落库、不得写 ERPNext、不得记录成功审计。
3. 无论采用哪种收口方式，都必须确保 `TASK-030A` 结束后“普通前端 + 普通业务调用链”不再拥有真实可用的创建 / 修改 / 确认 / 取消能力。
4. `diagnostic` 入口不属于普通前端能力，本任务只允许保留既有高权限 / 内控语义，不得向普通页面新增暴露。

### 6.3 前端收口（必须实现）

1. `quality.ts` 对普通前端保留的导出函数仅允许：
   - `fetchQualityInspections`
   - `fetchQualityInspectionDetail`
   - `fetchQualityStatistics`
   - `exportQualityInspections`
2. `QualityInspectionList.vue` 必须收口为只读列表页：
   - 保留查询 / 导出 / 详情跳转
   - 移除“创建检验单”按钮与创建对话框
3. `QualityInspectionDetail.vue` 必须收口为只读详情页：
   - 保留基础信息、检验明细、缺陷记录、操作日志展示
   - 移除更新 / 确认 / 取消按钮与相关对话框
4. 禁止新增质量页面或改动 router 注册。

### 6.4 业务规则（必须继续满足）

1. `inspected_qty = accepted_qty + rejected_qty`
2. `accepted_qty + rejected_qty` 不得超过 `inspected_qty`
3. `accepted_qty / rejected_qty / defect_qty` 不得为负
4. `inspected_qty = 0` 时，`defect_rate = 0` 且 `rejected_rate = 0`
5. `confirmed` 记录数量字段不得再被修改
6. `cancelled` 状态不参与统计
7. 来源对象不可用必须 fail closed

## 7. 验收标准

1. `TASK-030A` 不再把现有 `quality` 模块误写为待新建基线；任务边界与仓库现状一致。
2. 质量模块仍以既有 `models / schemas / services / routers / api / views` 为唯一基线，无并行新模块。
3. 列表 / 详情 / 统计 / 导出四个 GET 能力保留且可验证。
4. 写入口完成冻结收口：
   - 普通前端不再出现创建 / 修改 / 确认 / 取消入口
   - 后端写接口要么不再暴露，要么统一冻结且无副作用
5. `company / item_code / supplier / warehouse / source_type / source_id` 的资源过滤 / 归属校验语义仍有效。
6. `quality_service.py` 与 `quality` 前端模块不再直接出现 ERPNext `/api/resource` 调用。
7. 不新增 localStorage 敏感凭据读取。
8. 质量测试集通过，并覆盖至少以下事实：
   - 只读 GET 正常
   - 写口冻结 / 不可写
   - ERPNext fail-closed
   - 统计排除 `cancelled`
9. 当前仍不放行 B。

## 8. 验证命令

```bash
cd /Users/hh/Desktop/领意服装管理系统

# 1. 现有质量模块基线文件存在
test -f 07_后端/lingyi_service/app/models/quality.py
test -f 07_后端/lingyi_service/app/schemas/quality.py
test -f 07_后端/lingyi_service/app/services/quality_service.py
test -f 07_后端/lingyi_service/app/routers/quality.py
test -f 06_前端/lingyi-pc/src/api/quality.ts
test -f 06_前端/lingyi-pc/src/views/quality/QualityInspectionList.vue
test -f 06_前端/lingyi-pc/src/views/quality/QualityInspectionDetail.vue

# 2. 只读 GET 路由仍存在
rg -n '@router.get\("/inspections"\)|@router.get\("/inspections/\{inspection_id\}"\)|@router.get\("/statistics"\)|@router.get\("/export"\)' \
  07_后端/lingyi_service/app/routers/quality.py

# 3. 写路由已冻结或已移除
rg -n '@router\.(post|patch)\("/inspections|/confirm|/cancel' \
  07_后端/lingyi_service/app/routers/quality.py || true
rg -n 'QUALITY_WRITE_FROZEN|disabled_by_design|pending_design|not_enabled' \
  07_后端/lingyi_service/app/routers/quality.py \
  07_后端/lingyi_service/app/services/quality_service.py

# 4. 普通前端不再暴露写入口
! rg -n 'createQualityInspection|updateQualityInspection|confirmQualityInspection|cancelQualityInspection' \
  06_前端/lingyi-pc/src/api/quality.ts \
  06_前端/lingyi-pc/src/views/quality/QualityInspectionList.vue \
  06_前端/lingyi-pc/src/views/quality/QualityInspectionDetail.vue
! rg -n '创建检验单|更新检验结果|确认检验单|取消检验单' \
  06_前端/lingyi-pc/src/views/quality/QualityInspectionList.vue \
  06_前端/lingyi-pc/src/views/quality/QualityInspectionDetail.vue

# 5. 质量模块主链路中无 ERPNext /api/resource 直连、无本地敏感凭据
! rg -n '/api/resource' \
  07_后端/lingyi_service/app/routers/quality.py \
  07_后端/lingyi_service/app/services/quality_service.py \
  06_前端/lingyi-pc/src/api/quality.ts \
  06_前端/lingyi-pc/src/views/quality
! rg -n 'localStorage.*token|localStorage.*AUTH|localStorage.*LY_AUTH_TOKEN' \
  06_前端/lingyi-pc/src/api/quality.ts \
  06_前端/lingyi-pc/src/views/quality

# 6. 质量测试集
ls 07_后端/lingyi_service/tests/test_quality*.py
pytest \
  07_后端/lingyi_service/tests/test_quality_api.py \
  07_后端/lingyi_service/tests/test_quality_models.py \
  -v --tb=short

# 7. git diff 确认无越界修改
git diff --name-only -- \
  06_前端/lingyi-pc/src/router \
  .github \
  02_源码 \
  04_生产
# 应返回空
```

## 9. 完成回报

TASK-030A 执行完成。
结论：待审计
质量管理 Phase 1 只读基线是否已收口：是
写接口状态：[已冻结 / 已移除]
普通前端写入口状态：[已移除]
是否存在 ERPNext 写操作：否
质量模块主链路是否仍有 `/api/resource` 直连：否
是否存在 views/router 越界修改：否
pytest 测试结果：[通过/失败]

## 10. 后续路径（仅供参考，非本任务单承诺）

`TASK-030A` 审计通过后，可继续拆分：
- `TASK-030B`：质检单创建 / 修改 / 缺陷录入（写入口重启）
- `TASK-030C`：质检单确认 / 取消（状态机重启）
- `TASK-030D`：ERPNext 库存写入联动（outbox，需单独立项）

---

**C Auditor 备注（供总调度参考）：**

`TASK-030A` 修订后的核心约束是：

- 以现有 `quality` 模块为基线，不再按绿地新建处理
- Phase 1 先做只读 / 统计 / 导出收口
- 现有写入口按“冻结 / 去写化”方式收口，不在本轮恢复真实可写
- ERPNext 写操作与 outbox 保持后置，不在 `TASK-030A` 范围内

这与 Sprint 3 四条主线的节奏一致：先把普通前门收口为可审计只读基线，再拆写入口与 ERPNext 写联动。
