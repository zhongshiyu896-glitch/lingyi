# TASK-Z007B-43-IMPL style 字段 readback 映射最小实现与回归报告

## 1. 任务与边界
- TASK_ID: `TASK-Z007B-43-IMPL`
- source_head: `fa5b8b036fd421ea8fe70af04dc7610def8b659f`
- selected_candidate_id: `Z007-CAND-004-S1`
- parent_candidate_id: `Z007-CAND-004`
- implementation option: `OPTION_B_READONLY_MAPPING`
- 约束执行：
  - 未触发任何业务写请求
  - 未创建真实业务数据
  - 未改动 allowlist 外文件
  - 未执行 stage/commit/push/PR/tag/release/cleanup/reset/restore/clean/delete

## 2. 最小实现内容
在只读 readback 链路中新增显式 style 语义字段，来源固定为 `item_code`：

1. `app/schemas/factory_statement.py`
   - 在 `FactoryStatementItemData` 增加 `style_code: str | None = None`。
2. `app/services/factory_statement_service.py`
   - 组装 detail item 时新增 `style_code=self._normalize_text(row.item_code)`。
3. `tests/fixtures/factory_statement_readback_contract_fixture.json`
   - `detail_contract_expected.item_optional_fields` 增加 `style_code`。
   - `cross_module_canonical_mapping.style` 从 blocked 更新为：
     - `warehouse_contract_fields=["item_code"]`
     - `factory_statement_contract_fields=["style_code"]`
     - `status="mapped_derived_from_item_code"`
     - `derived_from="item_code"`
4. `tests/test_factory_statement_readback_contract_fixture.py`
   - 调整 style 锚点断言：要求 `derived_from=item_code` 且 `style_code` 在 contract 字段内。
5. `tests/test_factory_statement_api.py`
   - detail 断言新增 `style_code` 存在且 `style_code == item_code`。
   - 为适配现有本地写 gate（仅测试环境内部），测试请求头与 payload 增加合法 scenario carrier。

## 3. 回归结果
在 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service` 执行：

1. `./.venv/bin/python -m pytest tests/test_factory_statement_readback_contract_fixture.py -q`
   - `6 passed`
2. `./.venv/bin/python -m pytest tests/test_warehouse_adapter_contract_fixture.py -q`
   - `10 passed`
3. `./.venv/bin/python -m pytest tests/test_warehouse_permission_mode_readback_matrix.py -q`
   - `6 passed`
4. `./.venv/bin/python -m pytest tests/test_factory_statement_api.py -q -k 'list or detail or evaluations'`
   - `2 passed, 8 deselected`

结论：
- `style_mapping_status=PASS`
- `style_source=derived_from_item_code`
- warehouse fixture/permission matrix 无回退。

## 4. 零副作用与门禁
- `allowed_write_hit=[]`
- `unexpected_write_request_count=0`
- `forbidden_write_request_count=0`
- `production_write_count=0`
- `erpnext_write_count=0`
- `worker_sync_internal_job_request_count=0`
- `git diff --cached --name-only` 为空
- `git diff --cached --check` PASS
- `git diff --check` PASS

## 5. 残余风险
- 本次仅完成 `style_code` 从 `item_code` 的只读语义映射，不等于 `style_name` 主数据实时解析。
- 不外推为生产 ERPNext 非 fallback readback 闭合，不外推为 go-live 闭合。
