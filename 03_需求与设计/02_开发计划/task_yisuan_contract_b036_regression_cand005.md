# TASK-YISUAN-CONTRACT-B036-REGRESSION-CAND005

## 基线
- HEAD: `e73e8d427fcc5ca03b417a31df02b9fcb276021f`
- branch: `codex/sprint4-seal`
- cached_count: `0`
- HEAD_tag_count: `0`
- code_modified_in_this_task: `false`
- git diff --check: `PASS`

## 变更归因
- changed_files_attribution（产品代码当前脏集）：
  - `06_前端/lingyi-pc/src/views/sales_inventory/SalesInventoryStockLedger.vue`
  - `06_前端/lingyi-pc/src/views/warehouse/WarehouseDashboard.vue`
- 本任务未新增产品代码改动，未触碰 `local_dev.py` / router / API / 后端。

## 路由与截图复验
- routes HTTP 200:
  - `/sales-inventory/stock-ledger` -> final_path=`/sales-inventory/stock-ledger`
  - `/warehouse` -> final_path=`/warehouse`
- route evidence:
  - `03_需求与设计/02_开发计划/evidence/yisuan_contract_b036_cand005_regression/route_probe.json`
- screenshots（均 1440x1200）:
  - `.../screenshots/stock_ledger.png`
  - `.../screenshots/warehouse.png`
  - manifest: `.../screenshot_manifest.json`

## 合同回读与边界复验
- covered_contract_ids=`["A001","A002","A003"]`
- contract_source_readback_present=`true`
- key_fields/validation_rules/status_rules/readonly_readback observed=`true`
- partial_unknown_blocked_fields_preserved=`true`
- partial_unknown_blocked_fields_claimed_as_confirmed=`false`
- disabled_or_readback_only_boundary=`true`
- disabled_or_readback_real_action_triggered=`false`
- not_claimed_as_business_action=`true`
- local_dev_draft_path_promoted_to_real_action=`false`
- real_business_object_created=`false`
- linked_calculation_enabled=`false`
- evidence:
  - `.../contract_source_readback.json`
  - `.../contract_fields_observation.json`
  - `.../local_dev_draft_path_observation.json`
  - `.../browser_evidence.json`

## 网络/写入与类型检查
- network:
  - `write_requests_observed_count=0`
  - `production_write_requests=0`
  - `erpnext_production_write_requests=0`
  - `request_methods_observed_only_GET=true`
  - `no_post_put_patch_delete_observed=true`
  - evidence: `.../network_write_observation.json`
- typecheck:
  - command: `npm run typecheck`
  - workdir: `06_前端/lingyi-pc`
  - exit_code: `0`
  - evidence: `.../typecheck_result.json`
- dev server:
  - started/stopped: `true/true`
  - evidence: `.../dev_server_evidence.json`

## dirty 分类
- tracked_dirty_count=`18`
- frontend_dirty_count=`5`
- backend_or_test_dirty_count=`10`
- log_control_dirty_count=`3`
- dirty_intersections=`[]`
- unknown_dirty=`[]`
- must_block_before_continue=`[]`

## 数据边界
- data_classification=`contract_merge_no_real_object`
- test_data_used=`false`
- seed_data_used=`false`
- sqlite_not_formal_database=`true`
- sqlite_direct_reuse_for_production_forbidden=`true`
- erpnext_production_connected=`false`
- production_readback=`false`
- go_live=`false`
- project_completion=`false`
- remote_lifecycle_parked=`true`

## 禁止动作确认
- 未改代码范围外文件，未 stage/commit/amend，未 push/PR/tag/release，未 reset/restore/clean/delete，未连接生产。

## 残余风险
- 库存流水仍保留历史 local-dev 草稿读取路径（GET）；本轮未观察到写请求，后续 ledger 需继续冻结为 not_claimed/disabled-readback-only。

NEXT_ROLE: `C Auditor`
