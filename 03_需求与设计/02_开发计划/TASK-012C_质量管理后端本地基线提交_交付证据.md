# TASK-012C 质量管理后端本地基线提交交付证据

## 1. 任务结论

- 任务：TASK-012C 质量管理后端本地基线提交
- 前置审计：TASK-012B1 审计通过
- 提交前 HEAD：`ab5ea7bb12b7f05904eccbdda4a6cecfd7bd0614`
- 状态：已提交
- 生产发布：未发生
- push / remote / PR：未发生

## 2. 本次拟入库范围

### 2.1 文档与证据

- `03_需求与设计/01_架构设计/TASK-012_质量管理基线设计.md`
- `03_需求与设计/02_开发计划/TASK-012A_质量管理基线设计冻结_工程任务单.md`
- `03_需求与设计/02_开发计划/TASK-012B_质量管理后端模型接口基线_交付证据.md`
- `03_需求与设计/02_开发计划/TASK-012B1_质量管理后端审计阻断整改_交付证据.md`
- `03_需求与设计/02_开发计划/TASK-012C_质量管理后端本地基线提交_交付证据.md`

### 2.2 后端代码、迁移与测试

- `07_后端/lingyi_service/app/core/error_codes.py`
- `07_后端/lingyi_service/app/core/permissions.py`
- `07_后端/lingyi_service/app/main.py`
- `07_后端/lingyi_service/app/models/__init__.py`
- `07_后端/lingyi_service/app/models/quality.py`
- `07_后端/lingyi_service/app/routers/quality.py`
- `07_后端/lingyi_service/app/schemas/quality.py`
- `07_后端/lingyi_service/app/services/permission_service.py`
- `07_后端/lingyi_service/app/services/quality_service.py`
- `07_后端/lingyi_service/migrations/versions/task_012b_create_quality_tables.py`
- `07_后端/lingyi_service/tests/test_quality_api.py`
- `07_后端/lingyi_service/tests/test_quality_models.py`

## 3. 审计阻断闭环摘要

- 来源归属校验：`incoming_material` / `finished_goods` 已校验 `company + item_code`，异常 fail closed。
- 资源 scope：`source_type/source_id` 已纳入权限字段与质量路由上下文。
- supplier 索引：`idx_ly_quality_inspection_supplier_date(supplier, inspection_date)` 已纳入模型与迁移。
- diagnostic：`GET /api/quality/diagnostic` 已实现，使用 `quality:diagnostic`，并有操作审计覆盖。

## 4. 验证结果

- `pytest -q tests/test_quality_models.py tests/test_quality_api.py`：`18 passed, 1 warning`
- `pytest -q tests/test_quality*.py tests/test_permissions*.py tests/test_erpnext_fail_closed_adapter.py`：`46 passed, 1 warning`
- `pytest -q`：`852 passed, 13 skipped, 1164 warnings`
- `python -m unittest discover`：`Ran 757 tests ... OK (skipped=1)`
- `python -m py_compile $(find app tests -name '*.py' -print)`：通过
- `git diff --check`：通过
- `git diff --name-only -- '06_前端' '.github' '02_源码'`：空输出，通过

## 5. 禁止能力确认

- 未实现 ERPNext 写入
- 未实现 Purchase Invoice / Payment Entry / GL Entry
- 未实现 outbox / worker
- 未修改前端
- 未修改 `.github/**`
- 未修改 `02_源码/**`

## 6. 提交后回填

- 提交 SHA：`007aea9d0b9f13efe856161f1853f5d93f9aa7c2`
- 提交信息：`feat: add quality management backend baseline`
