# TASK-Z007B-37-IMPL 本地adapter_fixture_contract扩展最小实现与回归报告

## 任务锚点
- TASK_ID: `TASK-Z007B-37-IMPL`
- source_head: `0792e2972b9d4229392b3164462b03fd3e5bb12b`
- selected_candidate_id: `Z007-CAND-004`
- boundary_file: `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/task_z007b_36_adapter_fixture_contract_extension_boundary.json`
- allowed_write_endpoints_next: `[]`

## 本轮实现（allowlist 内）
- 新增 fixture：
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/fixtures/factory_statement_readback_contract_fixture.json`
- 新增测试：
  - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_factory_statement_readback_contract_fixture.py`
- 未改动 `factory_statement` router/service 与 `test_factory_statement_api.py`。

## contract_gap_matrix 结果
1. `factory_statement.list`：通过 fixture + schema contract 断言闭合（list data/list item 字段集合存在性）。
2. `factory_statement.detail`：通过 fixture + schema contract 断言闭合（header/items/logs/payable_outboxes 字段集合存在性）。
3. `factory_statement.readonly_sub_routes`：
   - `supplier/factory/customer evaluations`：通过 route(GET) + schema 字段 contract 断言。
   - `bank/report/reconciliation/summary`：通过 route(GET) 存在性 + item schema 字段 contract 断言。
4. `warehouse <-> factory_statement` 跨模块 canonical mapping：
   - `supplier/factory/material`：字段锚点已建立。
   - `customer`：标记为 `mapped_with_factory_statement_only`（warehouse 侧无 customer 字段锚点）。
   - `style`：标记为 `blocked_no_style_field_in_current_readback_contract`（当前 readback contract 无 style 字段，不外推闭合）。

## 测试执行
在目录 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service` 执行：
1. `uv run --with-requirements requirements-dev.txt pytest tests/test_warehouse_adapter_contract_fixture.py -q`
   - 结果：`10 passed, 1 warning`
2. `uv run --with-requirements requirements-dev.txt pytest tests/test_factory_statement_readback_contract_fixture.py -q`
   - 结果：`6 passed, 1 warning`
3. `uv run --with-requirements requirements-dev.txt pytest tests/test_warehouse_permission_mode_readback_matrix.py -q`
   - 结果：`6 passed, 1 warning`

## 零副作用门禁
- `allowed_write_hit=[]`
- `unexpected_write_request_count=0`
- `forbidden_write_request_count=0`
- `production_write_count=0`
- `erpnext_write_count=0`
- `worker_sync_internal_job_request_count=0`
- `allowed_read_endpoint_extra=[]`

## 状态
- 本轮仅完成本地 fixture/contract 证据补齐，不声明生产 readback 闭合，不声明 go-live 闭合，不声明项目完成。
