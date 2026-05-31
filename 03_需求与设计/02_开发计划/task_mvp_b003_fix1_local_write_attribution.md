# TASK-MVP-B003-FIX1-LOCAL-WRITE-ATTRIBUTION

## SUMMARY
- head: `e9c2f052688af4acd0e31aaaa3723016013db279`
- branch: `codex/sprint4-seal`
- cached_empty: `true`
- blocker: `auth_401_on_local_sqlite_write_loop`
- root_cause: `HomePage.vue/saveLocalDraft` 触发 `POST /api/warehouse/stock-entry-drafts` 返回 `401`，导致 `draft_id` 未生成，后续 `cancel/readback` 连锁失败。
- next_task: `TASK-MVP-B003-FIX2-IMPL-PENDING-A-AUTH`

## FAILURE
- failing_request_url: `http://127.0.0.1:5174/api/warehouse/stock-entry-drafts`
- failing_request_method: `POST`
- failing_status: `401`
- caller_file: `06_前端/lingyi-pc/src/views/HomePage.vue`
- caller_handler: `saveLocalDraft -> createWarehouseStockEntryDraft`
- draft_id_created: `false`
- save_success: `false`
- cancel_success: `false`
- readback_success: `false`
- used_auth_protected_api: `true`
- used_erpnext_production_endpoint: `false`

## LOCAL_SUPPORT
- local_sqlite_support_found: `true`
- scenario_tag_support_found: `true`
- support_files_clean: `false`（`07_后端/lingyi_service/app/local_dev.py` 当前为 untracked）
- can_fix_with_original_allowed_files: `false`
- reason: 401 根因在鉴权/运行时门禁链路，超出 B003 既有两文件 allowlist 的可控范围。
- requested_allowlist_for_fix2:
  - `06_前端/lingyi-pc/src/views/HomePage.vue`
  - `06_前端/lingyi-pc/src/views/dashboard/DashboardOverview.vue`
- requested_additional_allowed_files:
  - `06_前端/lingyi-pc/vite.config.ts`（exists+clean）
  - `07_后端/lingyi_service/app/local_dev.py`（exists 但 untracked）

## SAFETY
- production_write_risk: `none_observed`
- erpnext_production_write_risk: `none_observed`
- real_account_risk: `medium_if_using_real_login_session`
- remote_lifecycle_parked: `true`
- go_live: `false`
- project_completion: `false`

## CHECKS
- product_code_changed_in_fix1: `false`
- validation_rerun: `false`
- staged_area_empty: `true`
- git_diff_check: `PASS`
- outputs_unstaged: `true`

## RESIDUAL_RISK
- B003 仍 blocked，直到 local write loop 真正成功
- remote_lifecycle_parked=true
- production_readback=false
- go_live=false
- project_completion=false
