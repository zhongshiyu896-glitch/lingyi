# TASK-Z007B-52-IMPL 生产只读访问包与远端授权清单模板生成报告

## 1. 任务与边界
- TASK_ID: `TASK-Z007B-52-IMPL`
- MAINLINE: `TASK-Z007A-YISUAN-1TO1-LOCAL-PARITY-MAINLINE`
- source_head: `e8ddb2a93b90f333a91435b811d6c1c5a408e8d9`
- selected_candidate_id: `Z007-CAND-009-PROPOSED`

本轮仅生成模板产物，不执行任何生产请求与远端生命周期动作，不改 `06_前端` / `07_后端`。

## 2. 模板产物
已生成：
1. `task_z007b_52_production_readonly_access_packet_template.json`
2. `task_z007b_52_production_readonly_access_packet_template.tsv`
3. `task_z007b_52_remote_lifecycle_authorization_checklist.json`
4. `task_z007b_52_remote_lifecycle_authorization_checklist.tsv`

模板覆盖范围：
- `Z007-CAND-005`：warehouse non-fallback readback（权限、样本、字段、端点、request_id/source trace/replay consistency）
- `Z007-CAND-006`：factory statement payable real linkage（statement/payable_outbox/purchase_invoice 字段链路）
- `Z007-CAND-007`：production master data parity（customer/supplier/factory/fabric/style 五类对象差异矩阵）
- `Z007-CAND-008`：push/PR/tag/release 授权文本、审批条件、默认未授权状态

## 3. 固定状态字段
- `template_generated=true`
- `runtime_request_allowed=false`
- `runtime_request_count=0`
- `write_request_count=0`
- `production_account_used=false`
- `remote_lifecycle_action_executed=false`
- `default_remote_authorization_granted=false`
- `production_readback_ready=false`
- `go_live_ready=false`
- `project_completion_claimed=false`
- `remote_lifecycle_parked=true`

## 4. 推荐下一步
- `recommended_next_task_id=TASK-Z007B-53`
- 建议任务类型：对 B52 模板执行 freeze + commit-candidate ledger（仍保持只读与远端冻结）

## 5. 验证摘要
- 4 个 JSON 可解析：PASS
- 2 个 TSV 与对应 JSON 条目数量/顺序/核心字段一致：PASS
- 文本卫生（无 trailing whitespace，EOF 单换行）：PASS
- `git diff --cached --name-only` 为空：PASS
- `git diff --name-only -- 06_前端 07_后端` 为空：PASS
- `git diff --cached --check`：PASS
- `git diff --check`：PASS
- `tag_at_head` 为空：PASS
- `remote_contains_head` 为空：PASS
- `pr_list=[]`：PASS
