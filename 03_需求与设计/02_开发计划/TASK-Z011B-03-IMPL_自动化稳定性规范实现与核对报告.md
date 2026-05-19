# TASK-Z011B-03-IMPL 自动化稳定性规范实现与核对报告

- `task_id=TASK-Z011B-03-IMPL`
- `role=B Engineer`
- `mainline=TASK-Z011A-LOCAL-ACCEPTANCE-GAP-CLOSURE-MAINLINE`
- `selected_candidate_id=Z011-CAND-002`
- `source_head=44bed39c58dc68493a36cbb49391e458ea24a231`

## 产物

- `/Users/hh/Desktop/领意服装管理系统/04_测试与验收/测试证据/z008_local_acceptance_automation/Z011_自动化稳定性与复跑规范.md`
- `/Users/hh/Desktop/领意服装管理系统/04_测试与验收/测试证据/z008_local_acceptance_automation/z011_automation_stability_policy_matrix.json`
- `/Users/hh/Desktop/领意服装管理系统/04_测试与验收/测试证据/z008_local_acceptance_automation/z011_automation_stability_policy_matrix.tsv`

## 覆盖核对

- 已覆盖 timeout 建议分组：
  - 纯文件解析脚本
  - Git gate 脚本
  - pytest/contract matrix 脚本
  - browser GET-only smoke 脚本
  - orchestrator / regression gate 脚本
- 已覆盖输出目录隔离：
  - 默认 `/tmp/<run_id>/`
  - 不覆盖已提交证据
  - 排除截图、缓存、`__pycache__`、`.pyc` 等
- 已覆盖复跑命令一致性：
  - Python 使用 `python3`
  - Node 先 `node --check`
  - JSON/TSV 同步生成并对齐
- 已覆盖失败分类：
  - `PASS`
  - `BLOCKING`
  - `RESIDUAL`
  - `SKIPPED_BY_BOUNDARY`
- 已覆盖安全边界：
  - `write_request_count=0`
  - `production_account_used=false`
  - `remote_lifecycle_action_executed=false`
  - 不读取 `cookie/localStorage/sessionStorage/token`
- 已保留当前残余：
  - `full_browser_route_smoke_closed=false`
  - `Z008-SCRIPT-005` 需登录态满足后才可复跑闭合

## 范围约束遵守

- 未修改任何现有自动化脚本。
- 未修改 `06_前端` / `07_后端`。
- 未运行浏览器采样，未读取敏感存储，未使用生产账号。
- 未执行 stage/commit/push/PR/tag/release/reset/restore/clean/delete。

## 下一候选建议

- `recommended_next_candidate_id=Z011-CAND-003`
- `recommended_next_task_id=TASK-Z011B-04-IMPL`
