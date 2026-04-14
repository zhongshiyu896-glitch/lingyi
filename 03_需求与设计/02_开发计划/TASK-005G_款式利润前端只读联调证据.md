# TASK-005G 款式利润前端只读联调证据

- 任务编号：TASK-005G
- 记录时间：2026-04-14 17:30 CST
- 执行人：Codex
- 执行基线 HEAD：`0e124d3368e81df57ddcdf44bc4a8b2c93bd1ab6`

## 实现范围

1. 新增只读 API 文件：`src/api/style_profit.ts`
2. 新增只读页面：
   - `src/views/style_profit/StyleProfitSnapshotList.vue`
   - `src/views/style_profit/StyleProfitSnapshotDetail.vue`
3. 新增路由：
   - `/reports/style-profit`
   - `/reports/style-profit/detail`
4. 新增契约门禁脚本：
   - `scripts/check-style-profit-contracts.mjs`
   - `scripts/test-style-profit-contracts.mjs`
5. `package.json` 增加：
   - `check:style-profit-contracts`
   - `test:style-profit-contracts`
   - `verify` 已串联 style-profit 契约检查与反向测试

## 只读约束核对

- 仅接入 GET：
  - `GET /api/reports/style-profit/snapshots`
  - `GET /api/reports/style-profit/snapshots/{snapshot_id}`
- 未实现 POST 创建接口调用。
- 页面未暴露创建/生成/重算入口。
- 前端未出现 `style_profit:snapshot_create`、`snapshot_create`、`idempotency_key`、`createStyleProfitSnapshot`。
- 列表页 company/item_code 为空时阻断请求。
- 无 `style_profit:read` 权限时列表/详情均不发请求。
- `unresolved_count > 0` 时详情页提示：`存在未解析来源，请财务复核后使用`。

## 前端验证结果

执行目录：`/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc`

1. `npm run check:style-profit-contracts`：通过
2. `npm run test:style-profit-contracts`：通过（9 个反向场景）
3. `npm run verify`：通过（含 production/style-profit 契约 + typecheck + build）
4. `npm audit --audit-level=high`：通过（found 0 vulnerabilities）

## 后端只读回归结果

执行目录：`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service`

1. `.venv/bin/python -m pytest -q tests/test_style_profit_api.py tests/test_style_profit_api_permissions.py tests/test_style_profit_api_audit.py tests/test_style_profit_api_errors.py`
   - 结果：34 passed, 1 warning
2. `.venv/bin/python -m pytest -q`
   - 结果：641 passed, 13 skipped
3. `.venv/bin/python -m unittest discover`
   - 结果：624 tests, OK (skipped=1)
4. `.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)`
   - 结果：通过

## 变更边界确认

- 未修改 `07_后端/**` 业务代码。
- 未修改 `.github/**`。
- 未修改 `02_源码/**`。
- 未修改 `TASK-006*`。
- 未提交 `.pytest-postgresql-*.xml`。

## 结论

- TASK-005G 前端只读联调已完成。
- 当前仅完成只读查询联调，未开放任何利润快照写入口。
- TASK-006 仍未进入。
