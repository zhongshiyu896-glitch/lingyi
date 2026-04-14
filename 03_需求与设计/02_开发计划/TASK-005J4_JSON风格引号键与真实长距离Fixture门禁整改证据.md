# TASK-005J4 JSON 风格引号键与真实长距离 Fixture 门禁整改证据

## 1. 任务与提交信息

- 任务：TASK-005J4
- 任务目标：修复 JSON 风格引号键绕过，并将长距离 fixture 从伪距离（源码文本 `repeat(1200)`）升级为真实距离。
- 提交前 HEAD：`4d31335`
- 功能提交后 HEAD：`f29b21b56e9f718d93aa6410a2f08e43645eaac0`
- 功能提交信息：`fix: detect quoted style profit action keys`

## 2. 修改文件

1. `06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
2. `06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`

本轮未修改：
- `07_后端/**`
- `.github/**`
- `02_源码/**`
- `TASK-006*`
- `.pytest-postgresql-*.xml`

## 3. 引号键识别实现

在 `check-style-profit-contracts.mjs` 中完成以下整改：

1. 交互键识别改为支持裸键 + 单引号键 + 双引号键：
   - `onClick:`
   - `'onClick':`
   - `"onClick":`
2. 交互字段集合保持并扩展适配：
   - `onClick/handler/action/command/onSelect/onCommand/callback/execute/submit`
3. 说明字段识别支持裸键 + 引号键：
   - `label/title/text/name/tooltip/description`
4. 祖先链规则保持不变：
   - 子对象出现说明文案时向上检查所有祖先对象；
   - 任一祖先含交互字段即判定违规；
   - 不依赖固定字符窗口。

## 4. 真实长距离 Fixture 整改

在 `test-style-profit-contracts.mjs` 中完成以下整改：

1. 删除伪距离写法 `filler: 'x'.repeat(1200)`（源码表达式写法）。
2. 改为真实字符串插入：
   - `const longFiller = 'x'.repeat(1200)`
   - `"filler": "${longFiller}"`
3. 增加真实距离断言（硬断言）：

```ts
Math.abs(content.indexOf('"label"') - content.indexOf('"onClick"')) > 1200
```

4. 增加辅助断言函数 `assertDistanceGreaterThan(...)`，防止距离回退。

## 5. 新增/调整反向测试（必须失败）

已覆盖并通过反向失败断言：

1. 双引号键：`"onClick"` + `"meta": { "label": "利润计算说明" }` + 真实 1200 字符 filler。
2. 单引号键：`'handler'` + `'props': { 'label': '利润率计算规则' }`。
3. 混合键：`"command"` + `extra: { "label": '利润快照来源说明' }`。
4. 双引号 children 树：`"onSelect"` 祖先 + `"meta": { "label": "利润计算说明" }` 后代。
5. 既有 J3 场景保持有效（未降级）。

## 6. 成功 fixture（必须通过）

以下场景保持通过：

1. 纯说明对象（无祖先交互字段）：
   - `readonlyHelp`（裸键）
   - `readonlyHelpJson`（双引号键）
2. 只读动作：`查看详情 / 查询 / 返回`（含双引号键版本 `readonlyActionsJson`）。

## 7. 验证命令与结果

### 7.1 前端

1. `npm run check:style-profit-contracts`
   - 结果：通过（`Style-profit contract check passed. Scanned files: 24`）
2. `npm run test:style-profit-contracts`
   - 结果：通过（`All style-profit contract fixture tests passed. scenarios=43`）
3. `npm run verify`
   - 结果：通过（production/style-profit 契约检查、typecheck、build 全通过）
4. `npm audit --audit-level=high`
   - 结果：通过（`found 0 vulnerabilities`）

### 7.2 后端只读回归（未改后端）

1. `.venv/bin/python -m pytest -q tests/test_style_profit_api.py tests/test_style_profit_api_permissions.py tests/test_style_profit_api_audit.py tests/test_style_profit_api_errors.py`
   - 结果：`34 passed, 1 warning`
2. `.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)`
   - 结果：通过

### 7.3 引号键与真实长距离覆盖扫描

命令：

```bash
rg -n '"onClick"|"label"|\x27onClick\x27|\x27label\x27|longFiller|indexOf\(.*onClick|indexOf\(.*label|repeat\(1200\)|真实 1200|利润计算说明|利润率计算规则|利润快照来源说明' \
  06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs
```

结果：命中引号键场景、`longFiller` 与 `indexOf` 真实距离断言。

### 7.4 禁止伪长距离扫描

命令：

```bash
rg -n "filler:\s*['\"]x['\"]\.repeat\(1200\)|['\"]x['\"]\.repeat\(1200\).*label|repeat\(1200\).*不是实际" \
  06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs
```

结果：无命中（已消除伪长距离写法）。

### 7.5 业务禁线扫描

命令：

```bash
rg -n "款式利润报表计算|利润快照列表生成|利润金额重新计算|款式利润.{0,16}(新建|创建|生成|重算|重新计算|计算|核算|提交|保存)|((新建|创建|生成|重算|重新计算|计算|核算|提交|保存).{0,16}款式利润)|利润报表.{0,16}(新建|创建|生成|重算|重新计算|计算|核算|提交|保存)|((新建|创建|生成|重算|重新计算|计算|核算|提交|保存).{0,16}利润报表)|毛利核算|净利核算|利润一键生成|createProfit|generateProfit|recalculateProfit|createSnapshot|generateSnapshot|recalculateSnapshot|profitCreate|profitGenerate|profitRecalculate" \
  06_前端/lingyi-pc/src
```

结果：无命中。

## 8. 提交摘要

`git show --stat --oneline --name-only f29b21b`：

```text
f29b21b fix: detect quoted style profit action keys
06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs
06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs
```

## 9. 结论

1. JSON 风格引号键绕过已修复。
2. 祖先对象链检测对裸键/单引号键/双引号键/混合键均生效。
3. 真实 1200 字符长距离 fixture 已建立并带硬断言。
4. 伪长距离写法已清除。
5. 未开放创建快照入口。
6. 未进入 TASK-006。

