# TASK-030F 质量导出 PDF / Excel 增强 工程任务单

## 1. 基本信息

- 任务编号：TASK-030F
- 任务名称：质量导出 PDF / Excel 增强
- 角色：架构师
- 优先级：P1
- 状态：待执行（已放行）
- 前置依赖：`TASK-030E` 实现审计通过（审计意见书第365份）；`TASK-030C` 实现审计通过（审计意见书第308份）；[`TASK-012_质量管理基线设计.md`](/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-012_质量管理基线设计.md) 设计冻结

## 2. 任务目标

在现有质量导出快照基线之上，增强导出能力，保持“后端生成文件、只读导出、不新增写语义”的边界：

1. 现有 `GET /api/quality/export` 从快照 JSON 导出增强为支持 `csv / xlsx / pdf`。
2. 支持单张导出与批量导出：`inspection_id` 可选；无 `inspection_id` 时按当前过滤条件批量导出。
3. Excel 导出必须覆盖检验单、检验明细、缺陷记录。
4. PDF 导出必须覆盖质检报告单视图；批量 PDF 允许打包为 ZIP。
5. 导出继续排除 `cancelled`，继续执行 `company` 过滤。

## 3. 设计依据

1. `TASK-030A` 已建立质量导出快照基线，当前仓库已有真实导出锚点，不是绿地新建：
   - `GET /api/quality/export`
   - `QualityService.export_rows()`
   - `QualityExportRow / QualityExportData`
   - `QualityInspectionList.vue` 中“导出快照”按钮
2. `TASK-030E` 已完成统计增强，本任务只处理导出增强，不触碰统计逻辑本身。
3. 包内规划项对 `TASK-030F` 的约束已明确：由后端生成导出文件，不在前端本地拼装。
4. 当前详情数据模型已具备导出所需细节源：`items / defects / logs` 可复用。

## 4. 允许范围

### 4.1 后端

允许新建：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/quality_export_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_quality_export_enhanced.py`

允许修改：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/quality.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/quality_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/quality.py`

### 4.2 前端

允许修改：

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/quality.ts`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/quality/QualityInspectionList.vue`

### 4.3 记录

允许修改：

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md`

## 5. 禁止范围

1. 禁止新增或修改任何质量写接口：`create / update / defect / confirm / cancel / outbox` 不在本任务范围内。
2. 禁止在前端本地拼装 Excel / PDF；文件必须由后端生成。
3. 禁止把 `cancelled` 记录纳入导出结果。
4. 禁止修改 Outbox / Worker / ERPNext 写链路。
5. 禁止修改：
   - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/router/**`
   - `/Users/hh/Desktop/领意服装管理系统/.github/**`
   - `/Users/hh/Desktop/领意服装管理系统/02_源码/**`
   - `/Users/hh/Desktop/领意服装管理系统/04_生产/**`
6. 禁止 push / remote / PR / 生产发布。

## 6. 必须实现

### 6.1 后端导出协议

`GET /api/quality/export` 增强为支持：

- `format=csv|xlsx|pdf`
- `inspection_id=<id>` 可选

要求：

1. 无 `inspection_id` 时，按当前过滤条件批量导出。
2. 单张导出时，至少包含检验单基本信息、检验明细、缺陷记录、操作日志。
3. 仍执行 `company / item_code / supplier / warehouse / source_type / source_id / status / from_date / to_date` 筛选。
4. 导出结果必须排除 `cancelled`。

### 6.2 Excel 导出

Excel 至少包含以下 Sheet：

1. `检验单`
2. `检验明细`
3. `缺陷记录`

字段至少覆盖：

- 检验单号
- 公司
- 来源类型 / 来源单号
- 物料
- 供应商
- 仓库
- 检验日期
- inspected_qty
- accepted_qty
- rejected_qty
- defect_qty
- defect_rate
- rejected_rate
- result
- status
- 明细行信息
- 缺陷记录信息
- 操作日志信息

### 6.3 PDF 导出

1. 单张 PDF：输出可打印的质检报告单。
2. 批量 PDF：允许打包为 ZIP 返回。
3. PDF 继续执行 `company` 过滤与 `cancelled` 排除。

### 6.4 前端

`QualityInspectionList.vue` 的导出入口增强为：

- 保留当前导出能力
- 新增“导出 Excel”
- 新增“导出 PDF”

`quality.ts` 必须支持传递 `format` 与可选 `inspection_id`。

### 6.5 测试

`test_quality_export_enhanced.py` 至少覆盖：

1. `format=xlsx` 返回有效结果。
2. `format=pdf` 返回有效结果。
3. 批量导出排除 `cancelled`。
4. `company` 过滤生效。
5. 单张导出能包含详情 / 缺陷 / 日志所需内容。

## 7. 验收标准

1. `GET /api/quality/export?format=xlsx` 可返回有效 Excel 导出结果。
2. `GET /api/quality/export?format=pdf` 可返回有效 PDF 导出结果。
3. Excel 至少包含 `检验单 / 检验明细 / 缺陷记录` 三个 Sheet。
4. 批量导出不包含 `cancelled` 记录。
5. `company` 过滤在导出路径生效。
6. 前端可选择 Excel / PDF 导出。
7. `test_quality_export_enhanced.py` 通过。
8. `npm run typecheck` 通过。
9. 禁改目录无新增越界修改。

## 8. 验证命令

```bash
cd /Users/hh/Desktop/领意服装管理系统

# 1. 导出增强入口存在
rg -n 'format=|xlsx|pdf|inspection_id|QualityExport|quality_export_service' \
  07_后端/lingyi_service/app/routers/quality.py \
  07_后端/lingyi_service/app/services/quality_service.py \
  07_后端/lingyi_service/app/services/quality_export_service.py \
  07_后端/lingyi_service/app/schemas/quality.py

# 2. 前端导出选项存在
rg -n '导出 Excel|导出 PDF|format|inspection_id|exportQualityInspections' \
  06_前端/lingyi-pc/src/api/quality.ts \
  06_前端/lingyi-pc/src/views/quality/QualityInspectionList.vue

# 3. cancelled 排除逻辑仍在
rg -n 'cancelled' \
  07_后端/lingyi_service/app/services/quality_service.py \
  07_后端/lingyi_service/app/services/quality_export_service.py \
  07_后端/lingyi_service/tests/test_quality_export_enhanced.py

# 4. 测试
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest tests/test_quality_export_enhanced.py -v --tb=short

# 5. 前端 typecheck
cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc
npm run typecheck

# 6. 禁改路径检查
cd /Users/hh/Desktop/领意服装管理系统
git diff --name-only -- \
  06_前端/lingyi-pc/src/router \
  .github \
  02_源码 \
  04_生产
# 应返回空
```
