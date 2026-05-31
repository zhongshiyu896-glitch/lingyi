# TASK-YISUAN-CONTRACT-B002-PREP-CAND001

## 任务结论
- `selected_candidate=CONTRACT-CAND-001`
- `next_task=TASK-YISUAN-CONTRACT-B003-IMPL-CAND001`
- 本次为 PREP/boundary only：未改产品代码，未运行 browser/typecheck/pytest，未 stage/commit。

## 基线核对
- repo: `/Users/hh/Desktop/领意服装管理系统`
- branch: `codex/sprint4-seal`
- HEAD: `0a0c6e36e9792a8fdde27360167c9e1c4e724995`
- `git diff --cached --name-only`: empty
- `git tag --points-at HEAD`: empty
- `git diff --check`: PASS
- B001 selected candidate: `CONTRACT-CAND-001`

## 继承冻结（精确继承 B001 selected candidate）
- `covered_contract_ids`: `["A001","A003"]`
- `contract_source_files`:
  - `04_测试与验收/测试证据/yisuan_business_shadow_capture/YISUAN_CAP_A001_evidence_coverage_matrix_20260520/evidence_coverage_matrix.json`
  - `04_测试与验收/测试证据/yisuan_business_shadow_capture/YISUAN_CAP_A003_ui_route_field_button_readonly_contract_20260520/ui_contract_development_input.json`
- `routes`:
  - `/sales-inventory/references`
  - `/foundation/warehouse`
  - `/warehouse`
- `allowed_files`:
  - `06_前端/lingyi-pc/src/views/sales_inventory/SalesInventoryReferenceList.vue`
  - `06_前端/lingyi-pc/src/views/warehouse/WarehouseDashboard.vue`
- `optional_support_files`: `[]`
- `business_contract_summary`: 基础资料字段、引用关系、只读态和按钮禁用态按 A001/A003 合同合并到页面实现。

## route_source_locations（冻结）
- `/sales-inventory/references` -> `06_前端/lingyi-pc/src/router/index.ts:180-182`
- `/foundation/warehouse` -> `06_前端/lingyi-pc/src/router/index.ts:233-234`（redirect `/warehouse?parity=foundation-warehouse`）
- `/warehouse` -> `06_前端/lingyi-pc/src/router/index.ts:186-188`

## 合同结构冻结
- key_fields：
  - 基础资料展示字段：协同状态、状态、简称、全称、客户等级、联系人、业务员、电话、结算方式、银行及账户、开票类型、开票信息、协同账号、地址
  - 引用字段：`customer:简称`、`supplier:简称`、`factory:简称`、`fabric:名称/类型/用量单位`
  - 仓库 parity/readback 与摘要状态展示字段
- validation_rules：
  - `ui_shell_only=true`
  - `can_use_for_action_logic=false`
  - 高风险按钮仅展示，不实现动作（新建/导入/导出/编辑/删除/保存/提交审核/审核/反审核/作废/生成类）
  - 高风险项必须标记 `BLOCKED/UNKNOWN`
- status_rules：
  - 页面状态标签：`状态`、`协同状态`、`停用默认为否`
  - 状态定义冻结：`VERIFIED/PARTIAL/UNKNOWN/NO-GO/BLOCKED`
- readonly/readback requirements：
  - 高风险按钮只读展示
  - readback 仅限展示层
  - 禁止启用 action logic
  - 必须可回读 contract source 与 covered_contract_ids

## B003 evidence requirement（冻结）
- routes HTTP 200：`/sales-inventory/references`、`/foundation/warehouse`、`/warehouse`
- `/foundation/warehouse` final_path: `/warehouse?parity=foundation-warehouse`
- screenshots: PNG 且 `1440x1200`
- contract source readback present
- covered_contract_ids 全量展示
- key_fields / validation_rules / status_rules 可定位
- `A001-A006 contract merge scope=true`
- `real_business_object_created=false`
- `linked_calculation_enabled=false`
- `production_write_requests=0`
- `erpnext_production_write_requests=0`
- `real_production_account_used=false`
- `npm run typecheck exit_code=0`
- `dev server started/stopped`

## 数据边界
- `data_classification=contract_merge_no_real_object`
- 默认：`test_data + scenario_tag`
- 本候选 PREP 记录：`test_data_used=false`
- `seed_data_used=false`
- `sqlite_not_formal_database=true`
- `sqlite_direct_reuse_for_production_forbidden=true`
- `rollback_zero_residual_requirement=required_if_local_auto_verification_or_write_loop_enabled`
- 禁止 ERPNext production / 真实生产账号 / 真实业务数据迁移

## 只读状态结果
- contract source files: exist
- allowed files: exist + clean
- optional support files: inherited empty
- `dirty_intersections=[]`
- `unknown_dirty=[]`
- `must_block_before_continue=[]`
