# TASK-030C 质检单确认取消状态机重启 工程任务单

## 1. 基本信息

- 任务编号：TASK-030C
- 任务名称：质检单确认 / 取消状态机重启
- 角色：架构师
- 优先级：P0
- 状态：待审计
- 前置依赖：`TASK-030B` 实现审计通过（审计意见书第301份）；`TASK-012_质量管理基线设计.md` 设计冻结（HEAD `ab5ea7bb12b7f05904eccbdda4a6cecfd7bd0614`）；`TASK-007` 权限基座（审计意见书第175份）

## 2. 任务目标

在 `TASK-030A` 只读基线与 `TASK-030B` 创建 / 草稿修改 / 缺陷录入链路已完成的基础上，重启质检单状态机核心写动作：

1. `POST /api/quality/inspections/{inspection_id}/confirm`：将 `draft` 变更为 `confirmed`，锁定数量字段，记录 `confirmed_by / confirmed_at`
2. `POST /api/quality/inspections/{inspection_id}/cancel`：仅允许将 `confirmed` 变更为 `cancelled`，记录 `cancelled_by / cancelled_at / cancel_reason`
3. 状态机硬约束：
   - `confirmed` 后不允许修改任何数量字段
   - `cancelled` 后不允许任何写操作
   - 不允许从 `cancelled` 逆向恢复
4. `quality:confirm / quality:cancel` 权限动作与 `company` 范围校验生效

本任务只形成可审计工程实现边界；当前不直接放行 B 实现，不设置 `build_release_allowed=yes`。

## 3. 设计依据

1. [`TASK-012_质量管理基线设计.md`](/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-012_质量管理基线设计.md) 已定义冻结状态机：`draft -> confirmed -> cancelled`；本任务严格按该口径收口，不在 Sprint 4 本轮放宽 `draft -> cancelled`
2. `TASK-030A`（审计意见书第299份）已建立只读基线并冻结普通写口
3. `TASK-030B`（审计意见书第301份）已恢复 `create / update draft / defect`，可提供 `draft` 状态来源
4. 当前仓库已存在 confirm / cancel 相关代码骨架，不是绿地新建：
   - 路由锚点：[quality.py:503](/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/quality.py:503)、[quality.py:522](/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/quality.py:522)
   - 服务锚点：[quality_service.py:204](/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/quality_service.py:204)、[quality_service.py:239](/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/quality_service.py:239)
   - 模型 / schema 锚点：[models/quality.py:76](/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/quality.py:76)、[models/quality.py:78](/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/quality.py:78)、[schemas/quality.py:171](/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/quality.py:171)、[schemas/quality.py:173](/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/quality.py:173)
5. 本任务不触发 ERPNext 写操作；ERPNext 库存写联动留给 `TASK-030D`

## 4. 允许范围

### 4.1 后端（FastAPI）

1. 允许修改：
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/quality.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/quality_service.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/quality.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/quality.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/versions/task_030c_add_quality_cancel_reason.py`
2. 允许恢复 / 修正路由：
   - `POST /api/quality/inspections/{inspection_id}/confirm`
   - `POST /api/quality/inspections/{inspection_id}/cancel`
3. 允许在必要时微调权限落点：
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/permission_service.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/permissions.py`

### 4.2 前端

1. 允许修改：
   - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/quality/QualityInspectionDetail.vue`
   - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/quality.ts`
2. 允许新增前端 API：
   - `confirmQualityInspection(inspectionId)`
   - `cancelQualityInspection(inspectionId, payload)`
3. 允许在详情页恢复以下受控入口：
   - `确认检验单`
   - `取消检验单`
4. 仅允许在现有质量详情页中恢复按钮，不允许新增 router 页面

### 4.3 测试

1. 允许新增：
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_quality_confirm_baseline.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_quality_cancel_baseline.py`
2. 允许在必要时补充既有质量测试：
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_quality_update_baseline.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_quality_api.py`

## 5. 禁止范围

1. 禁止实现 ERPNext Stock Entry / Purchase Receipt / Delivery Note 写入（由 `TASK-030D` 处理）
2. 禁止在 `confirmed` 记录上修改 `inspected_qty / accepted_qty / rejected_qty`
3. 禁止从 `cancelled` 逆向恢复为 `draft` 或 `confirmed`
4. 禁止引入 outbox、自动扣款结算、自动返工工单
5. 禁止修改 `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/router/**`
6. 禁止新增 localStorage 敏感凭据读取或持久化
7. 禁止越界修改 `.github/**`、`02_源码/**`、`04_生产/**`
8. 禁止设置 `build_release_allowed=yes`、禁止以本任务单直接放行 B、禁止 push / remote / PR

## 6. 必须实现

### 6.1 后端接口

1. `POST /api/quality/inspections/{inspection_id}/confirm`
   - 输入：`inspection_id` 由 URL 提供，`confirmed_by` 从会话主体获取
   - 前置：当前状态必须为 `draft`
   - 动作：`status -> confirmed`，记录 `confirmed_by / confirmed_at`，锁定数量字段
   - 返回：`200 + 更新后详情`
2. `POST /api/quality/inspections/{inspection_id}/cancel`
   - 输入：`inspection_id` 由 URL 提供，可选 `reason`
   - 前置：当前状态必须为 `confirmed`
   - 动作：`status -> cancelled`，记录 `cancelled_by / cancelled_at / cancel_reason`
   - 返回：`200 + 更新后详情`
3. 状态机硬约束
   - `confirmed` 状态再次 `confirm`：返回 `409 Conflict`
   - `cancelled` 状态执行 `confirm / cancel / update / defect write`：返回 `409 Conflict`
   - `draft` 状态执行 `cancel`：返回 `409 Conflict`
4. 真实库迁移要求
   - 新增 additive migration：`task_030c_add_quality_cancel_reason.py`
   - `down_revision` 必须接在 `task_012b_create_quality_tables`
   - `upgrade()` 必须为 `ly_schema.ly_quality_inspection` 增加可空列 `cancel_reason`
   - `downgrade()` 必须删除该列
   - 禁止直接改写历史迁移 `task_012b_create_quality_tables.py`

### 6.2 前端

1. `QualityInspectionDetail.vue`
   - 状态为 `draft`：显示 `确认检验单` 按钮，隐藏 `取消检验单`
   - 状态为 `confirmed`：显示 `取消检验单` 按钮，并隐藏 `编辑草稿 / 录入缺陷 / 确认检验单`
   - 状态为 `cancelled`：隐藏所有写操作按钮，并显示 `已取消` 状态标签
2. 点击按钮需弹出确认对话框，防止误操作
3. 无 `quality:confirm / quality:cancel` 权限时，前端按钮不渲染；后端仍返回 403

## 7. 验收标准

1. `POST /api/quality/inspections/{inspection_id}/confirm` 在 `draft` 下返回 200，状态变更为 `confirmed`，且 `confirmed_by / confirmed_at` 已记录
2. `POST /api/quality/inspections/{inspection_id}/confirm` 在 `confirmed` 或 `cancelled` 下返回 409
3. `POST /api/quality/inspections/{inspection_id}/cancel` 在 `confirmed` 下返回 200，状态变更为 `cancelled`
4. `POST /api/quality/inspections/{inspection_id}/cancel` 在 `draft` 或 `cancelled` 下返回 409
5. `confirmed` 记录无法修改数量字段；后续 `PATCH` 返回 403 或等效拒绝
6. `cancelled` 记录无法进行任何写操作
7. `quality:confirm / quality:cancel` 权限与 `company` 范围校验生效
8. 前端确认 / 取消按钮在对应状态下正确渲染 / 隐藏
9. 真实库 migration 已补齐 `cancel_reason`，且历史迁移 `task_012b_create_quality_tables.py` 未被改写
10. `test_quality_confirm_baseline.py` 和 `test_quality_cancel_baseline.py` 通过
11. 无 ERPNext 写操作，无越界修改

## 8. 验证命令

```bash
cd /Users/hh/Desktop/领意服装管理系统

# 1. confirm/cancel 路由存在
rg -n '@router.post\("/inspections/\{inspection_id\}/(confirm|cancel)"\)' \
  07_后端/lingyi_service/app/routers/quality.py

# 2. 状态机硬约束存在
rg -n '409|Conflict|status != "draft"|cancelled' \
  07_后端/lingyi_service/app/services/quality_service.py \
  07_后端/lingyi_service/app/routers/quality.py

# 2.1 cancel_reason 已进入真实库 migration，且未改写历史建表迁移
test -f 07_后端/lingyi_service/migrations/versions/task_030c_add_quality_cancel_reason.py
rg -n 'revision|down_revision|cancel_reason|add_column|drop_column|task_012b_create_quality_tables' \
  07_后端/lingyi_service/migrations/versions/task_030c_add_quality_cancel_reason.py
git -C /Users/hh/Desktop/领意服装管理系统 diff --name-only -- \
  07_后端/lingyi_service/migrations/versions/task_012b_create_quality_tables.py
# 应返回空

# 3. 前端按钮与 API 存在
rg -n 'confirmQualityInspection|cancelQualityInspection|确认检验单|取消检验单' \
  06_前端/lingyi-pc/src/api/quality.ts \
  06_前端/lingyi-pc/src/views/quality/QualityInspectionDetail.vue

# 4. 无 ERPNext 写操作
! rg -n 'Stock Entry|Purchase Receipt|Delivery Note|StockEntry|DeliveryNote' \
  07_后端/lingyi_service/app/routers/quality.py \
  07_后端/lingyi_service/app/services/quality_service.py

# 5. 测试通过
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest \
  tests/test_quality_confirm_baseline.py \
  tests/test_quality_cancel_baseline.py \
  -q

# 6. typecheck
cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc
npm run typecheck

# 7. 越界修改检查
git -C /Users/hh/Desktop/领意服装管理系统 diff --name-only -- \
  '06_前端/lingyi-pc/src/router' '.github' '02_源码' '04_生产'
# 应返回空
```

## 9. 完成回报

TASK-030C 执行完成。  
结论：待审计  
质检单确认（confirm）是否已实现：是 / 否  
质检单取消（cancel，仅 `confirmed -> cancelled`）是否已实现：是 / 否  
真实库 migration 是否已补齐 `cancel_reason`：是 / 否  
confirmed / cancelled 状态机硬约束是否生效：是 / 否  
是否存在 ERPNext 写操作：否  
pytest 测试结果：[通过 / 失败]

---

**C Auditor 备注（供总调度参考）：**

`TASK-030C` 承接 `TASK-030B` 的 `draft` 来源，严格按冻结状态机恢复 `confirm` 与 `confirmed -> cancelled` 两个核心动作；ERPNext 库存写联动仍冻结在 `TASK-030D`，本任务只处理本地状态机与权限边界。
