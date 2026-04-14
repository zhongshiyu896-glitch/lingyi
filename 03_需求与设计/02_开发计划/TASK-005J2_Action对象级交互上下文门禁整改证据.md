# TASK-005J2 Action 对象级交互上下文门禁整改证据

## 1. 提交信息

- 提交前 HEAD：`5e5fd80e2a83f8b7e6a0099bf0e215f31e0067ba`
- 提交后 HEAD：`434fb529248b7e6cfb514a507cc8554de1b14bb9`
- commit message：`fix: detect long style profit action configs`

## 2. 提交前暂存清单

提交前 `git diff --cached --name-only`：

```text
06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs
06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs
```

## 3. 提交摘要

`git show --stat --oneline --name-only 434fb52`：

```text
434fb52 fix: detect long style profit action configs
06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs
06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs
```

## 4. Action 对象级检测方案

1. 在 `check-style-profit-contracts.mjs` 新增对象块解析：`collectObjectBlocks()`，支持跳过字符串与注释后提取 `{...}` block。
2. 新增对象级判断：
   - `findContainingObjectBlock()`
   - `hasReadonlyExplanationLabelInObject()`
   - `hasInteractiveActionObjectForPhrase()`
   - `isReadonlyExplanationObjectContext()`
3. 在同一对象内若同时出现“只读说明 label”与交互键（`onClick|handler|command|onSelect`），即使间隔超过 300/500/1000 字符也判定违规。
4. 固定窗口检测仅保留为辅助，不再作为 action 配置的唯一判断依据。

## 5. 新增长 action 反向测试清单

在 `test-style-profit-contracts.mjs` 已新增并通过反向失败断言：

1. `label` + `onClick`，`repeat(400)` 间隔。
2. `onClick` 在前、`label` 在后，`repeat(400)` 间隔。
3. `label: 利润率计算规则` + `handler`。
4. `label: 利润快照来源说明` + `command`。
5. `children` 节点 `label: 利润计算说明` + `onSelect`。
6. `label` + `handler`，`repeat(500)` 间隔。
7. `label` + `onSelect`，`repeat(1000)` 间隔。

## 6. 合法 action 成功 fixture

1. `{ label: '利润计算说明', description: '只读帮助文案' }`
2. `{ label: '返回', onClick: goBack }`
3. `{ label: '查询', onClick: loadRows }`
4. `{ label: '查看详情', onClick: goDetail }`

## 7. 门禁防回退说明

1. 未恢复 substring 白名单豁免（未使用 `segment.includes(readonlyPhrase)` 直接放行整段语义）。
2. 未继续依赖固定窗口作为 action 唯一判断。
3. TASK-005H / TASK-005I / TASK-005I1 / TASK-005J / TASK-005J1 既有反向测试仍保留并通过。
4. 未新增 `POST /api/reports/style-profit/snapshots` 前端调用。
5. 未开放创建/生成/重算利润快照入口。

## 8. 验证命令与结果

### 8.1 前端验证

1. `npm run check:style-profit-contracts`
   - 结果：通过（`Style-profit contract check passed. Scanned files: 24`）
2. `npm run test:style-profit-contracts`
   - 结果：通过（`All style-profit contract fixture tests passed. scenarios=34`）
3. `npm run verify`
   - 结果：通过（包含 production/style-profit 契约检查、typecheck、build）
4. `npm audit --audit-level=high`
   - 结果：通过（`found 0 vulnerabilities`）

### 8.2 后端只读回归（未改后端代码）

1. `.venv/bin/python -m pytest -q tests/test_style_profit_api.py tests/test_style_profit_api_permissions.py tests/test_style_profit_api_audit.py tests/test_style_profit_api_errors.py`
   - 结果：`34 passed, 1 warning`
2. `.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)`
   - 结果：通过

### 8.3 审计复现覆盖扫描

命令：

```bash
rg -n "repeat\(400\)|repeat\(500\)|repeat\(1000\)|onClick|handler|command|onSelect|children|利润计算说明|利润率计算规则|利润快照来源说明" \
  06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs
```

结果：命中新增反向测试关键字（含 `repeat(400|500|1000)`、`onClick/handler/command/onSelect/children`）。

### 8.4 业务禁线扫描

命令：

```bash
rg -n "款式利润报表计算|利润快照列表生成|利润金额重新计算|款式利润.{0,16}(新建|创建|生成|重算|重新计算|计算|核算|提交|保存)|((新建|创建|生成|重算|重新计算|计算|核算|提交|保存).{0,16}款式利润)|利润报表.{0,16}(新建|创建|生成|重算|重新计算|计算|核算|提交|保存)|((新建|创建|生成|重算|重新计算|计算|核算|提交|保存).{0,16}利润报表)|毛利核算|净利核算|利润一键生成|createProfit|generateProfit|recalculateProfit|createSnapshot|generateSnapshot|recalculateSnapshot|profitCreate|profitGenerate|profitRecalculate" \
  06_前端/lingyi-pc/src
```

结果：无命中（`src` 业务文件未出现写入口语义）。

## 9. 边界确认

1. 未进入 `TASK-006`。
2. 未开放利润快照创建入口。
3. 本次功能提交范围仅限前端契约脚本 2 个文件。

