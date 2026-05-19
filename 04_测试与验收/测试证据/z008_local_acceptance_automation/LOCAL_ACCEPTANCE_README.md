# LOCAL ACCEPTANCE README

- `task_id=TASK-Z011B-02-IMPL`
- `source_head=44bed39c58dc68493a36cbb49391e458ea24a231`
- `mainline=TASK-Z011A-LOCAL-ACCEPTANCE-GAP-CLOSURE-MAINLINE`

## 1. 当前本地结论

- Z008 本地验收自动化已形成并完成本地封存。
- Z009 orchestrator 已达到 `SKIP_AWARE_LOCAL_CLOSED_WITH_RESIDUAL`。
- Z010 文档化交接包已本地闭合并提交。

## 2. 最短运行入口

- Z009 orchestrator 脚本：`/Users/hh/Desktop/领意服装管理系统/04_测试与验收/测试证据/z008_local_acceptance_automation/verify_local_acceptance_orchestrator.py`
- post-orchestrator regression gate 脚本：`/Users/hh/Desktop/领意服装管理系统/04_测试与验收/测试证据/z008_local_acceptance_automation/verify_post_orchestrator_regression_gate.py`
- Z010 运行手册：`/Users/hh/Desktop/领意服装管理系统/04_测试与验收/测试证据/z008_local_acceptance_automation/Z010_本地验收运行手册.md`

## 3. 最短阅读入口

- 交接包总览：`/Users/hh/Desktop/领意服装管理系统/04_测试与验收/测试证据/z008_local_acceptance_automation/Z010_本地验收交接包总览.md`
- 证据索引与文件地图：`/Users/hh/Desktop/领意服装管理系统/04_测试与验收/测试证据/z008_local_acceptance_automation/Z010_本地证据索引与文件地图.md`
- 残余风险与外部阻断说明：`/Users/hh/Desktop/领意服装管理系统/04_测试与验收/测试证据/z008_local_acceptance_automation/Z010_残余风险与外部阻断说明.md`
- 浏览器登录态人工前置说明：`/Users/hh/Desktop/领意服装管理系统/04_测试与验收/测试证据/z008_local_acceptance_automation/Z010_浏览器登录态人工前置操作说明.md`

## 4. 当前不可外推

- `full_browser_route_smoke_closed=false`
- `Z008-SCRIPT-005=SKIPPED_BY_BOUNDARY`
- `production_readback_ready=false`
- `go_live_ready=false`
- `project_completion_claimed=false`
- `remote_lifecycle_parked=true`

## 5. 下一步安全动作

1. 用户完成本地登录态后，可在只读边界下复跑 browser route smoke。
2. 用户提供生产只读账号和受控样本后，才可执行生产 non-fallback readback。
3. 用户明确授权远端生命周期后，才可进入 push/PR/tag/release。

## 6. 边界说明

- 本入口只用于本地验收理解和执行路径收敛，不代表生产闭合。
- 不执行浏览器自动登录，不读取 cookie/localStorage/sessionStorage/token。
- 不执行写请求，不使用生产账号，不执行远端生命周期动作。
