# B-6 TASK-012 质量管理基线补审执行报告

- 任务编号：B-6
- 任务名称：TASK-012 质量管理基线补审
- 角色：工程师
- 执行日期：2026-04-17
- 结论：提交审计

## 一、检查项逐项结论

1. 来源归属校验是否完整：✅ 通过  
- 后端代码位置证据：  
  - `07_后端/lingyi_service/app/services/quality_service.py:103-107`（`incoming_material`/`finished_goods` 来源读取与校验入口）  
  - `07_后端/lingyi_service/app/services/quality_service.py:825-843`（`_validate_source_ownership` 对 `company/item_code/supplier` 做归属一致性校验）  
  - `07_后端/lingyi_service/app/routers/quality.py:385-386`、`646-647`、`702-703`、`780-781`（`source_type/source_id` 纳入 scope 上下文）  
- 测试证据：  
  - `07_后端/lingyi_service/tests/test_quality_models.py:164`（incoming_material 归属校验）  
  - `07_后端/lingyi_service/tests/test_quality_models.py:199`（finished_goods 归属校验）  
  - `07_后端/lingyi_service/tests/test_quality_api.py:258-277`（create scope 包含 `source_type/source_id`）

2. `confirmed / cancelled` 状态机是否正确：✅ 通过  
- 后端代码位置证据：  
  - `07_后端/lingyi_service/app/services/quality_service.py:216-257`（仅 `draft` 可更新）  
  - `07_后端/lingyi_service/app/services/quality_service.py:259-292`（`draft -> confirmed`）  
  - `07_后端/lingyi_service/app/services/quality_service.py:294-326`（`confirmed -> cancelled`）  
  - `07_后端/lingyi_service/app/services/quality_service.py:412`（统计排除 `cancelled`）  
  - `07_后端/lingyi_service/app/models/quality.py:37`（状态约束 `draft/confirmed/cancelled`）  
- 测试证据：  
  - `07_后端/lingyi_service/tests/test_quality_api.py`（confirm/cancel 相关 API 用例全通过）

3. ERPNext 主数据校验是否 fail closed：✅ 通过  
- 后端代码位置证据：  
  - `07_后端/lingyi_service/app/services/quality_service.py:110-115`（来源不可用/鉴权缺失直接 fail closed）  
  - `07_后端/lingyi_service/app/services/quality_service.py:145`（ERPNext 资源禁用 fail closed）  
  - `07_后端/lingyi_service/app/services/quality_service.py:494-514`（malformed/非法响应 fail closed）  
  - `07_后端/lingyi_service/app/services/quality_service.py:866-867`（错误码映射到 `QUALITY_SOURCE_UNAVAILABLE`/`QUALITY_INVALID_SOURCE`）  
- 测试证据：  
  - `07_后端/lingyi_service/tests/test_quality_api.py:205`（`confirm_source_unavailable_fails_closed`）  
  - `07_后端/lingyi_service/tests/test_quality_models.py:124`（来源不可用 fail closed）

4. 是否无 ERPNext 写入、无 outbox、无财务写入：✅ 通过  
- 后端代码与路由证据：  
  - `07_后端/lingyi_service/app/services/quality_service.py` 仅出现 `/api/resource/{doctype}/{name}` 只读校验路径（无 ERPNext 写调用）。  
  - `07_后端/lingyi_service/tests/test_quality_api.py:316`（`test_only_allowed_routes_do_not_expose_outbox_or_erpnext_write`）通过。  
- 关键字扫描结果：未发现本任务范围内新增 `outbox/worker/Payment Entry/GL Entry/Purchase Invoice` 写路径。

5. 前端写入口是否绑定权限且 diagnostic 不暴露：✅ 通过  
- 前端代码位置证据：  
  - `06_前端/lingyi-pc/src/views/quality/QualityInspectionList.vue:195-197`（`quality_read/create/export` 绑定）  
  - `06_前端/lingyi-pc/src/views/quality/QualityInspectionList.vue:356`（无 `quality_create` 权限不发起创建）  
  - `06_前端/lingyi-pc/src/views/quality/QualityInspectionDetail.vue:196-204`（`quality_update/confirm/cancel` 与状态联合门禁）  
  - `06_前端/lingyi-pc/src/stores/permission.ts:106`、`125`（`quality_diagnostic: false` 强制清零）  
  - `06_前端/lingyi-pc/src/router/index.ts:129-138`（仅 quality list/detail 路由，无 diagnostic/internal/run-once）  
- 前端契约门禁证据：  
  - `06_前端/lingyi-pc/scripts/check-quality-contracts.mjs:87-89`（禁止 `/api/resource`、diagnostic、internal/run-once）  
  - `06_前端/lingyi-pc/scripts/test-quality-contracts.mjs` 反向测试通过，`scenarios=14`。

## 二、迁移与索引证据

- 模型索引：  
  - `07_后端/lingyi_service/app/models/quality.py:31`：`idx_ly_quality_inspection_supplier_date`  
  - `07_后端/lingyi_service/app/models/quality.py:32`：`idx_ly_quality_inspection_source`  
- 迁移索引：  
  - `07_后端/lingyi_service/migrations/versions/task_012b_create_quality_tables.py:101`：创建 `idx_ly_quality_inspection_supplier_date`  
  - `07_后端/lingyi_service/migrations/versions/task_012b_create_quality_tables.py:102`：创建 `idx_ly_quality_inspection_source`

## 三、测试与验证结果

### 1) 后端验证（`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service`）

- 命令：`.venv/bin/python -m pytest -q tests/test_quality_models.py tests/test_quality_api.py`  
  结果：`18 passed, 1 warning in 0.73s`

- 命令：`.venv/bin/python -m pytest -q tests/test_quality*.py tests/test_permissions*.py tests/test_erpnext_fail_closed_adapter.py`  
  结果：`46 passed, 1 warning in 0.70s`

- 命令：`.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)`  
  结果：`PY_COMPILE_OK`

### 2) 前端验证（`/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc`）

- 命令：`npm run test:quality-contracts`  
  结果：通过（`scenarios=14`）

- 命令：`npm run test:frontend-contract-engine`  
  结果：通过（`scenarios=25`）

- 命令：`npm run verify`  
  结果：通过（含 typecheck/build 与全量 contracts）

- 命令：`npm audit --audit-level=high`  
  结果：通过（`found 0 vulnerabilities`）

## 四、边界与工作区检查

- `git diff --name-only -- "06_前端" "07_后端" ".github" "02_源码"`：空输出  
- `git diff --cached --name-only`：空输出

说明：本次仅输出补审文档，不修改业务代码，不暂存、不提交、不 push。

## 五、问题项统计

- 高：0
- 中：0
- 低：2
  - 后端 pytest 存在 `pytest_asyncio` deprecation warning（不影响结论）。
  - 前端 build 存在 chunk size warning（性能提示，非安全/门禁问题）。

## 六、最终结论

- 结论：提交审计官复核（通过建议）。
