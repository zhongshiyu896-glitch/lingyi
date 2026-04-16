# TASK-012B1 质量管理后端审计阻断整改交付证据

## 1. 任务结论

- 任务：TASK-012B1 质量管理后端审计阻断整改
- 状态：待审计
- 是否提交：否
- 是否 push：否
- 是否配置 remote / PR：否

## 2. 对应审计问题与整改结果

### 2.1 高：来源对象归属校验不完整

整改结果：已修复。

- `incoming_material` 的 `Purchase Receipt` 来源现在必须校验：
  - `company` 与请求一致
  - 来源行或来源字段包含请求 `item_code`
  - 若来源存在 `supplier` 且请求传入 `supplier`，必须一致
- `finished_goods` 的 `Stock Entry` 来源现在必须校验：
  - `company` 与请求一致
  - 来源行或来源字段包含请求 `item_code`
- 缺失可验证 item 归属证据时 fail closed，返回 `QUALITY_INVALID_SOURCE`。

涉及文件：
- `07_后端/lingyi_service/app/services/quality_service.py`
- `07_后端/lingyi_service/tests/test_quality_models.py`

### 2.2 中：资源权限字段未覆盖 source_type/source_id

整改结果：已修复。

- `RESOURCE_SCOPE_FIELD_NAMES` 已补入：
  - `source_type`
  - `source_id`
- 质量路由构造资源 scope 时已传入：
  - create payload
  - list/statistics/export/diagnostic filter scope
  - detail/update/confirm/cancel row scope
- 已新增测试证明创建 scope 中包含 `source_type/source_id`。

涉及文件：
- `07_后端/lingyi_service/app/services/permission_service.py`
- `07_后端/lingyi_service/app/routers/quality.py`
- `07_后端/lingyi_service/tests/test_quality_api.py`

### 2.3 中：缺少 supplier 维度索引

整改结果：已修复。

- 模型新增索引：`idx_ly_quality_inspection_supplier_date(supplier, inspection_date)`
- 迁移新增同名索引创建
- 测试新增索引存在性与字段顺序断言

涉及文件：
- `07_后端/lingyi_service/app/models/quality.py`
- `07_后端/lingyi_service/migrations/versions/task_012b_create_quality_tables.py`
- `07_后端/lingyi_service/tests/test_quality_models.py`

### 2.4 中：quality:diagnostic 动作未实现接口与审计路径

整改结果：已修复。

- 新增接口：`GET /api/quality/diagnostic`
- 权限动作：`quality:diagnostic`
- 成功路径写操作审计
- 失败路径复用统一失败审计与错误信封
- `main.py` 全局安全审计 target inference 已识别 diagnostic action
- 新增测试覆盖 diagnostic 成功与无权限拒绝路径

涉及文件：
- `07_后端/lingyi_service/app/routers/quality.py`
- `07_后端/lingyi_service/app/services/quality_service.py`
- `07_后端/lingyi_service/app/schemas/quality.py`
- `07_后端/lingyi_service/app/main.py`
- `07_后端/lingyi_service/tests/test_quality_api.py`

## 3. 本轮修改文件

- `07_后端/lingyi_service/app/models/quality.py`
- `07_后端/lingyi_service/app/schemas/quality.py`
- `07_后端/lingyi_service/app/services/quality_service.py`
- `07_后端/lingyi_service/app/routers/quality.py`
- `07_后端/lingyi_service/app/services/permission_service.py`
- `07_后端/lingyi_service/app/main.py`
- `07_后端/lingyi_service/migrations/versions/task_012b_create_quality_tables.py`
- `07_后端/lingyi_service/tests/test_quality_api.py`
- `07_后端/lingyi_service/tests/test_quality_models.py`

## 4. 验证结果

- `pytest -q tests/test_quality_models.py tests/test_quality_api.py`：`18 passed, 1 warning`
- `pytest -q tests/test_quality*.py tests/test_permissions*.py tests/test_erpnext_fail_closed_adapter.py`：`46 passed, 1 warning`
- `pytest -q`：`852 passed, 13 skipped, 1164 warnings`
- `python -m unittest discover`：`Ran 757 tests ... OK (skipped=1)`
- `python -m py_compile $(find app tests -name '*.py' -print)`：通过

## 5. 禁改与禁止能力扫描

- `git diff --name-only -- '06_前端' '.github' '02_源码'`：空输出，通过
- `git diff --cached --name-only`：空输出，未暂存
- `git diff --check`：空输出，通过
- 质量模块关键字扫描：未发现 Purchase Invoice / Payment Entry / GL Entry / outbox / worker 写入或接口实现
- 扫描命中说明：`Stock Entry` 与 `/api/resource` 仅用于 ERPNext 只读 fail-closed 校验；测试中的 `outbox/worker` 为负向路由边界断言

## 6. 未进入范围

- 未修改前端 `06_前端/**`
- 未修改 `.github/**`
- 未修改 `02_源码/**`
- 未实现 ERPNext 写入
- 未实现 outbox / worker
- 未实现自动扣减、返工、报废、评分
- 未提交、未 push、未发布
