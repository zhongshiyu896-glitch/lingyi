# TASK-030B 质量管理写入口 工程任务单

## 1. 基本信息

- 任务编号：TASK-030B
- 任务名称：质检单创建 / 修改与缺陷录入
- 角色：架构师
- 优先级：P1
- 状态：待审计
- 前置依赖：`TASK-030A` 实现审计通过（审计意见书第299份）；`TASK-012_质量管理基线设计.md` 设计冻结；`TASK-007` 权限基座（审计意见书第175份）

## 2. 任务目标

基于 `TASK-030A` 已完成的只读基线与写口冻结，对质量管理写入口做受控重启：

1. 恢复质检单创建（POST）
2. 恢复草稿状态修改（PATCH）
3. 新增或显式开放缺陷录入入口（关联草稿质检单）
4. 所有写入口统一经过 FastAPI 路由层和权限校验，不得绕过路由直连数据库

本任务只形成可审计工程任务边界；当前不直接放行 B 实现，不设置 `build_release_allowed=yes`。

## 3. 设计依据

1. [`TASK-012_质量管理基线设计.md`](/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-012_质量管理基线设计.md) Phase 1 已允许“来料检验 / 外发回料检验 / 成品检验 / 缺陷记录 / 质检结果确认”能力分步落地。
2. `TASK-030A`（审计意见书第299份）已建立只读基线：列表 / 详情 / 统计 / 导出保留，普通前端写入口已移除，写路由统一返回 `QUALITY_WRITE_FROZEN`。
3. 当前仓库不是绿地质量模块：
   - 路由层已保留冻结中的写入口：[quality.py:302](/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/quality.py:302)、[quality.py:462](/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/quality.py:462)
   - 服务层已存在创建 / 修改主逻辑：[quality_service.py:120](/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/quality_service.py:120)、[quality_service.py:160](/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/quality_service.py:160)
   - 缺陷数据当前已通过服务层 `_replace_items_and_defects` 处理：[quality_service.py:460](/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/quality_service.py:460)
4. `TASK-030B` 不触发 ERPNext 写操作，不引入 outbox，不开放 confirm / cancel；`confirm / cancel` 留给后续 `TASK-030C`。
5. 写入口权限：`quality:create`（创建）、`quality:update`（修改草稿 / 录入缺陷）；均需 `company` 资源过滤，并保持 `item_code / supplier / source_type / source_id` 来源归属 fail-closed。

## 4. 允许范围

### 4.1 后端（FastAPI）

允许在既有 `quality` 模块基础上重启写入口，不得平行新建质量模块：

1. 允许恢复 / 修改路由：
   - `POST /api/quality/inspections`（创建质检单，返回 `draft`）
   - `PATCH /api/quality/inspections/{inspection_id}`（仅允许修改 `draft`）
   - `POST /api/quality/inspections/{inspection_id}/defects`（为草稿质检单录入缺陷记录）
2. 允许修改文件：
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/quality.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/quality_service.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/quality.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/quality.py`
3. 允许继续使用只读 ERPNext 校验适配层，不做写操作：
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_quality_adapter.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_fail_closed_adapter.py`
4. 允许在必要时微调权限落点：
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/permission_service.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/permissions.py`

### 4.2 前端

1. 允许修改共享 API：
   - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/quality.ts`
2. 允许在现有质量页面恢复受控写入口：
   - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/quality/QualityInspectionList.vue`
   - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/quality/QualityInspectionDetail.vue`
3. 允许恢复或新增以下普通前端 API 封装：
   - `createQualityInspection(draftData)`
   - `updateDraftInspection(inspectionId, patchData)`
   - `addDefectRecord(inspectionId, defectData)`
4. 禁止新增质量 router 页面；仅允许在既有页面内恢复写入口。

### 4.3 测试

1. 允许新增：
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_quality_create_baseline.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_quality_update_baseline.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_quality_defect_baseline.py`
2. 允许在必要时补充既有质量测试：
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_quality_api.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_quality_models.py`

## 5. 禁止范围

1. 禁止开放 `confirm / cancel`（由 `TASK-030C` 处理）。
2. 禁止 ERPNext Stock Entry / Purchase Receipt / Delivery Note 写入。
3. 禁止 ERPNext GL / Payment / Purchase Invoice 写入。
4. 禁止自动扣款结算、自动返工工单、自动报废入账。
5. 禁止 outbox。
6. 禁止绕过 FastAPI 路由从前端、脚本或服务侧直接落库。
7. 禁止修改 `confirmed / cancelled` 状态记录的业务字段。
8. 禁止修改：
   - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/router/**`
   - `/Users/hh/Desktop/领意服装管理系统/.github/**`
   - `/Users/hh/Desktop/领意服装管理系统/02_源码/**`
   - `/Users/hh/Desktop/领意服装管理系统/04_生产/**`
9. 禁止设置 `build_release_allowed=yes`、禁止以本任务单直接放行 B、禁止 push / remote / PR。
10. 禁止新增 localStorage 敏感凭据持久化。

## 6. 必须输出

### 6.1 业务规则（强制校验）

1. 新建质检单状态必须为 `draft`。
2. `confirmed / cancelled` 记录禁止 PATCH 修改，返回 403 或等效拒绝错误信封。
3. `inspected_qty = accepted_qty + rejected_qty`。
4. `accepted_qty + rejected_qty` 不得超过 `inspected_qty`。
5. `accepted_qty / rejected_qty / defect_qty` 不得为负。
6. 缺陷录入必须关联已有草稿质检单；质检单不存在或非 `draft` 状态则拒绝。
7. 来源校验：来源对象不可用时 fail closed。
8. 缺陷录入必须经过 `quality:update` 权限与 `company` 资源过滤。

### 6.2 权限动作

- `quality:create`：创建草稿质检单（`draft`）
- `quality:update`：修改 `draft` 质检单、录入缺陷
- 列表 / 详情 / 统计 / 导出保持只读（已由 `TASK-030A` 保证）

## 7. 验收标准

1. `POST /api/quality/inspections` 返回 201 + 草稿质检单，状态为 `draft`。
2. `PATCH /api/quality/inspections/{inspection_id}` 对 `confirmed / cancelled` 记录返回 403，不落库。
3. `POST /api/quality/inspections/{inspection_id}/defects` 返回 201 + 已关联缺陷记录。
4. `quality:create / quality:update` 权限拒绝场景返回 403。
5. `company / item_code / supplier / source_type / source_id` 资源过滤 / 来源校验在写接口生效。
6. 数量平衡、负数、来源校验在写路径强制校验。
7. 不存在 ERPNext 写操作。
8. 三份新增测试全部通过；必要时既有质量测试更新后也通过。
9. 当前不修改 `confirm / cancel` 语义，不越权触碰 `TASK-030C`。

## 8. 验证命令

```bash
cd /Users/hh/Desktop/领意服装管理系统

# 1. 写路由存在
rg -n '@router.post\("/inspections"\)|@router.patch\("/inspections/\{inspection_id\}"\)|@router.post\("/inspections/\{inspection_id\}/defects"\)' \
  07_后端/lingyi_service/app/routers/quality.py

# 2. draft 才允许修改，confirmed/cancelled 拒绝
rg -n 'status != "draft"|QUALITY_WRITE_FROZEN|403' \
  07_后端/lingyi_service/app/routers/quality.py \
  07_后端/lingyi_service/app/services/quality_service.py

# 3. 无 ERPNext 写操作
! rg -n 'stock_entry|purchase_receipt|delivery_note|purchase_invoice|gl_entry|payment_entry' \
  07_后端/lingyi_service/app/routers/quality.py \
  07_后端/lingyi_service/app/services/quality_service.py

# 4. 前端写入口已恢复
rg -n 'createQualityInspection|updateDraftInspection|addDefectRecord' \
  06_前端/lingyi-pc/src/api/quality.ts \
  06_前端/lingyi-pc/src/views/quality/QualityInspectionList.vue \
  06_前端/lingyi-pc/src/views/quality/QualityInspectionDetail.vue

# 5. 测试
pytest \
  07_后端/lingyi_service/tests/test_quality_create_baseline.py \
  07_后端/lingyi_service/tests/test_quality_update_baseline.py \
  07_后端/lingyi_service/tests/test_quality_defect_baseline.py \
  -v --tb=short

# 6. 无越界修改
git diff --name-only -- \
  06_前端/lingyi-pc/src/router \
  .github \
  02_源码 \
  04_生产
# 应返回空
```

## 9. 完成回报

TASK-030B 执行完成。  
结论：待审计  
质检单创建（POST）是否已实现：是 / 否  
草稿修改（PATCH）是否已实现：是 / 否  
缺陷录入是否已实现：是 / 否  
confirmed 拒绝是否生效：是 / 否  
是否存在 ERPNext 写操作：否  
pytest 测试结果：[通过 / 失败]

---

**C Auditor 备注（供总调度参考）：**

`TASK-030B` 是 `TASK-030A` 写口冻结后的重启轮：`TASK-030A` 先把普通前端写口和后端写路由冻结，`TASK-030B` 在现有 `quality` 模块基线上恢复一把受控的“创建 / 修改 draft / 缺陷录入”钥匙。  

`TASK-030B` 完成后，下一步是 `TASK-030C`（confirm / cancel 状态机）。`TASK-030D`（ERPNext 库存写入 + outbox）需单独立项，不在本任务范围内。
