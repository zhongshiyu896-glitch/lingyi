# TASK-005I1 中文语义白名单绕过整改证据

- 任务编号：TASK-005I1
- 记录时间：2026-04-14 18:10 CST
- 执行人：Codex
- 执行基线 HEAD：`f0cc7e045a3293cb69b01c30900710e8396bae82`

## 问题复盘

`check-style-profit-contracts.mjs` 原先 `shouldIgnoreSemanticMatch()` 采用“匹配片段包含只读白名单词即忽略”的 substring 逻辑，存在绕过风险：
- 款式利润报表计算
- 利润快照列表生成
- 利润金额重新计算

上述模式都包含只读词，但同时包含写动作词，不能被豁免。

## 修复内容

### 1) 白名单判定收紧

文件：`06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`

修复后：
1. 新增 `hasSemanticWriteAction(segment)`：只要片段包含写动作词，立即视为违规，不进入白名单豁免。
2. 新增 `isPureReadonlyPhrase(segment)`：只允许“整段完全等于某个只读短语”时豁免。
3. `shouldIgnoreSemanticMatch()` 改为：
   - 先判定是否含写动作词：有则 `false`
   - 无写动作词时仅纯等值只读短语可 `true`

结果：不再按 substring 豁免整段语义匹配。

### 2) 新增反向测试（必须失败）

文件：`06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`

新增场景：
1. `<button>款式利润报表计算</button>`
2. `<button>利润快照列表生成</button>`
3. `<button>利润金额重新计算</button>`

并保持 TASK-005I 原有反向测试不降级：
- 款式利润计算
- 利润报表重算
- 毛利核算
- 利润一键生成
- openProfitCalculateDialog
- /reports/style-profit/calculate
- generateProfitSnapshot
- 以及 style-profit POST / idempotency_key / snapshot_create / create route / canRead 缺失 / 裸 fetch 等场景

## 审计复现扫描

命令：

```bash
rg -n "款式利润报表计算|利润快照列表生成|利润金额重新计算" /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs
```

结果：命中 3 组用例定义（名称与 fixture 注入行均可见）。

## 前端验证

执行目录：`/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc`

1. `npm run check:style-profit-contracts`
   - 结果：通过（Scanned files: 24）
2. `npm run test:style-profit-contracts`
   - 结果：通过（scenarios=19）
3. `npm run verify`
   - 结果：通过（production/style-profit 契约、typecheck、build 全通过）
4. `npm audit --audit-level=high`
   - 结果：通过（found 0 vulnerabilities）

## 后端只读回归

执行目录：`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service`

1. `.venv/bin/python -m pytest -q tests/test_style_profit_api.py tests/test_style_profit_api_permissions.py tests/test_style_profit_api_audit.py tests/test_style_profit_api_errors.py`
   - 结果：34 passed, 1 warning
2. `.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)`
   - 结果：通过

## 业务禁线扫描

命令：

```bash
rg -n "款式利润报表计算|利润快照列表生成|利润金额重新计算|款式利润.{0,16}(新建|创建|生成|重算|重新计算|计算|核算|提交|保存)|((新建|创建|生成|重算|重新计算|计算|核算|提交|保存).{0,16}款式利润)|利润报表.{0,16}(新建|创建|生成|重算|重新计算|计算|核算|提交|保存)|((新建|创建|生成|重算|重新计算|计算|核算|提交|保存).{0,16}利润报表)|毛利核算|净利核算|利润一键生成|createProfit|generateProfit|recalculateProfit|createSnapshot|generateSnapshot|recalculateSnapshot|profitCreate|profitGenerate|profitRecalculate" /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src
```

结果：无命中（exit code 1，stdout 为空）。

## 边界确认

- 未修改 `07_后端/**`
- 未修改 `.github/**`
- 未修改 `02_源码/**`
- 未修改 `TASK-006*`
- 未纳入 `.pytest-postgresql-*.xml`
- 未开放创建/生成/重算利润快照入口

## 结论

TASK-005I1 已完成：中文语义白名单绕过问题已关闭。白名单仅保护纯只读短语，不再允许“只读词 + 写动作词”组合绕过门禁。TASK-006 仍未进入。
