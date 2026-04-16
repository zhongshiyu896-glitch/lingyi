# TASK-012B 质量管理后端模型接口基线交付证据

## 1. 任务结论

- 任务：TASK-012B 质量管理后端模型/接口基线实现
- 状态：待审计
- 当前语义：本地后端基线实现完成，不代表生产发布完成
- 是否提交：否
- 是否 push：否
- 是否配置 remote / PR：否

## 2. 实现范围

本次实现质量管理后端基线，覆盖模型、迁移、schema、服务、API、权限、错误码、审计与测试。

### 2.1 新增后端文件

- `07_后端/lingyi_service/app/models/quality.py`
- `07_后端/lingyi_service/app/schemas/quality.py`
- `07_后端/lingyi_service/app/services/quality_service.py`
- `07_后端/lingyi_service/app/routers/quality.py`
- `07_后端/lingyi_service/migrations/versions/task_012b_create_quality_tables.py`
- `07_后端/lingyi_service/tests/test_quality_api.py`
- `07_后端/lingyi_service/tests/test_quality_models.py`

### 2.2 修改后端文件

- `07_后端/lingyi_service/app/core/error_codes.py`
- `07_后端/lingyi_service/app/core/permissions.py`
- `07_后端/lingyi_service/app/main.py`
- `07_后端/lingyi_service/app/models/__init__.py`
- `07_后端/lingyi_service/app/services/permission_service.py`

## 3. 关键实现摘要

1. 新增质量管理 4 张表：
   - `ly_quality_inspection`
   - `ly_quality_inspection_item`
   - `ly_quality_defect`
   - `ly_quality_operation_log`

2. 新增质量管理 API：
   - `POST /api/quality/inspections`
   - `GET /api/quality/inspections`
   - `GET /api/quality/inspections/{inspection_id}`
   - `PATCH /api/quality/inspections/{inspection_id}`
   - `POST /api/quality/inspections/{inspection_id}/confirm`
   - `POST /api/quality/inspections/{inspection_id}/cancel`
   - `GET /api/quality/statistics`
   - `GET /api/quality/export`

3. 状态与数量约束：
   - `status`：`draft / confirmed / cancelled`
   - `result`：`pending / pass / fail / partial`
   - `accepted_qty + rejected_qty = inspected_qty`
   - `defect_qty <= inspected_qty`
   - 数量字段非负

4. ERPNext fail-closed 读取校验：
   - company、item、supplier、warehouse、source document 均通过 fail-closed 读取校验
   - ERPNext 不可用、返回异常、资源不存在、docstatus 不合法均失败
   - 本轮不写 ERPNext，不提交单据

5. 权限与审计：
   - 接入 `quality:read/create/update/confirm/cancel/export/diagnostic`
   - 写操作与导出写操作审计
   - 详情资源越权按防枚举策略返回不存在语义
   - 统一错误信封 `{code,message,data}`

## 4. 明确未进入范围

- 未修改前端 `06_前端/**`
- 未修改 `.github/**`
- 未修改 `02_源码/**`
- 未实现 ERPNext 写入
- 未实现 Purchase Invoice / Payment Entry / GL Entry
- 未实现 Stock Entry 创建或提交
- 未实现 outbox / worker
- 未实现自动扣减、返工、报废、评分
- 未进入生产发布、push、remote、PR

## 5. 验证结果

### 5.1 已执行并通过

- `pytest -q tests/test_quality_models.py tests/test_quality_api.py`：`13 passed, 1 warning`
- `pytest -q tests/test_quality*.py tests/test_permissions*.py tests/test_erpnext_fail_closed_adapter.py`：`41 passed, 1 warning`
- `pytest -q`：`847 passed, 13 skipped, 1164 warnings`
- `python -m unittest discover`：`Ran 752 tests ... OK (skipped=1)`

### 5.2 最终补充验证

- `python -m py_compile $(find app tests -name '*.py' -print)`：通过
- `git diff --name-only -- '06_前端' '.github' '02_源码'`：空输出，通过
- `git diff --name-only -- '07_后端/lingyi_service/migrations/versions'`：仅本任务新增迁移属于允许范围；命令在当前未暂存状态下无额外越界输出
- `git diff --cached --name-only`：空输出，未暂存
- `git diff --check`：空输出，通过
- 质量模块禁止能力扫描：未发现 outbox / worker / Purchase Invoice / Payment Entry / GL Entry / Stock Ledger Entry 写入实现
- 扫描命中说明：`Stock Entry` 与 `/api/resource` 仅出现在 `quality_service.py` 的 ERPNext 只读 fail-closed 校验路径；测试文件中的 `outbox/erpnext/worker` 为负向路由边界断言

## 6. 风险与说明

1. `datetime.utcnow()` deprecation warnings 为历史遗留，非本任务新增阻断项。
2. 本任务为本地后端基线，不等同生产 ERPNext 联调完成。
3. 工作区存在历史未跟踪/未提交文件，本任务不处理、不回退。
4. 后续若进入前端接入，必须接入 TASK-010 前端写入口公共门禁。
