# TASK-005H 款式利润全局只读边界门禁收口证据

- 任务编号：TASK-005H
- 记录时间：2026-04-14 17:32 CST
- 执行人：Codex
- 执行基线 HEAD：`154adc0d4e85df9a407c7f11bb1d3d4f25817d45`

## 实施内容

1. 扩大 `scripts/check-style-profit-contracts.mjs` 扫描范围，纳入：
   - `src/api/**`
   - `src/views/**`
   - `src/router/**`
   - `src/stores/**`
   - `src/components/**`（存在时自动纳入）
   - `src/App.vue`
   - `src/main.ts`
2. 新增/强化全局只读门禁：
   - 拦截 `style_profit:snapshot_create`
   - 拦截 `snapshot_create`
   - 拦截 `createStyleProfitSnapshot`
   - 拦截 style-profit 面上的 `idempotency_key`
   - 拦截 style-profit 面上的 `method: 'POST'` / `method: "POST"`
   - 拦截 style-profit 面上的 `/api/resource`
   - 拦截“新建/创建/生成/重算利润快照”文案
3. 新增/强化反向测试 `scripts/test-style-profit-contracts.mjs`，覆盖：
   - App 暴露“生成利润快照”按钮
   - 其他页面暴露 `style_profit:snapshot_create`
   - permission store 映射 `snapshot_create: true`
   - router 暴露 `/reports/style-profit/create`
   - 详情页缺少 `canRead` 前置阻断
   - `style_profit.ts` 出现 `POST`
   - style-profit 面出现 `idempotency_key`
   - 非白名单文件出现裸 `fetch(`
4. 调整详情页 `StyleProfitSnapshotDetail.vue`：
   - `request_hash`、`idempotent_replay` 从主业务摘要移出
   - 迁入“审计信息（仅供审计复核）”折叠区展示

## 前端验证

执行目录：`/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc`

1. `npm run check:style-profit-contracts`：通过（Scanned files: 24）
2. `npm run test:style-profit-contracts`：通过（scenarios=9）
3. `npm run verify`：通过（含 production/style-profit 契约 + typecheck + build）
4. `npm audit --audit-level=high`：通过（found 0 vulnerabilities）

## 后端只读回归

执行目录：`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service`

1. `.venv/bin/python -m pytest -q tests/test_style_profit_api.py tests/test_style_profit_api_permissions.py tests/test_style_profit_api_audit.py tests/test_style_profit_api_errors.py`
   - 结果：34 passed, 1 warning
2. `.venv/bin/python -m pytest -q`
   - 结果：641 passed, 13 skipped
3. `.venv/bin/python -m unittest discover`
   - 结果：624 tests, OK (skipped=1)
4. `.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)`
   - 结果：通过

## 静态禁线扫描

1. 按任务指定命令对 `src/**` 全量扫描时，命中来自既有生产/外发模块（如 `production`、`subcontract`）的 `idempotency_key` 字段，不属于 style-profit 只读联调范围。
2. 对 style-profit 联调范围单独扫描（`src/api/style_profit.ts`、`src/views/style_profit/**`、`src/router/index.ts`、`src/stores/permission.ts`、`src/App.vue`、`src/main.ts`）禁线命中为 0。
3. 契约门禁脚本与反向测试已覆盖全局入口与 style-profit 面，防止新增创建/生成/重算入口绕过。

## 变更文件

- `06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
- `06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`
- `06_前端/lingyi-pc/src/views/style_profit/StyleProfitSnapshotDetail.vue`
- `03_需求与设计/02_开发计划/TASK-005H_款式利润全局只读边界门禁收口证据.md`

## 边界确认

- 未修改 `07_后端/**`
- 未修改 `.github/**`
- 未修改 `02_源码/**`
- 未修改 `TASK-006*`
- 未纳入 `.pytest-postgresql-*.xml`
- 未开放创建/生成/重算利润快照入口

## 结论

TASK-005H 已完成：款式利润前端只读边界门禁已从页面级收口到全局入口级，创建类入口和写入契约在脚本与反向测试层均可被阻断。TASK-006 仍未进入。
