# TASK-005J3 Action 祖先对象链门禁整改证据

## 1. 任务与提交信息

- 任务：TASK-005J3 Action 祖先对象链门禁整改
- 提交前 HEAD：`b5da6c7`
- 功能提交后 HEAD：`590ed04e0e493df4d46e27a72a0072833b02127b`
- 功能提交信息：`fix: check style profit action ancestor chain`

## 2. 修改文件清单

1. `06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
2. `06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`

本轮未修改：
- `07_后端/**`
- `.github/**`
- `02_源码/**`
- `TASK-006*`

## 3. 祖先对象链检测整改说明

### 3.1 检测能力升级

在 `check-style-profit-contracts.mjs` 中将 action 检测从“最小对象 + 固定窗口辅助”升级为“对象祖先链检测”：

1. 扩展交互字段识别为：
   - `onClick`
   - `handler`
   - `action`
   - `command`
   - `onSelect`
   - `onCommand`
   - `callback`
   - `execute`
   - `submit`

2. 新增利润说明字段识别：
   - 直接字段：`label/title/text/name/tooltip/description`
   - 点路径字段：`meta.label`、`meta.title`、`props.label`、`extra.label`、`payload.label`

3. 新增祖先链解析与判定：
   - `collectAncestorObjectBlocks(...)`
   - `resolveExplanationObjectChain(...)`

4. 判定规则：
   - 只要利润说明文案出现在某对象及其祖先对象链中，且链上任意对象含交互字段，即判定违规。
   - 祖先交互字段与后代利润说明文案间隔超过 300/500/1000 字符时仍可识别，不依赖固定窗口距离。

### 3.2 防回退确认

1. 未恢复 substring 白名单豁免。
2. 未退化为只看最小子对象后直接放行。
3. 固定窗口仅作为辅助，不再作为 action 配置唯一判断。

## 4. 新增反向测试（必须失败）

在 `test-style-profit-contracts.mjs` 新增并通过以下反向场景：

1. 父 `onClick` + 子 `meta.label='利润计算说明'`。
2. 父 `handler` + 子 `props.label='利润率计算规则'`。
3. 父 `command` + 子 `extra.label='利润快照来源说明'`。
4. 父 `onClick` 与后代 `meta.label` 间隔 `repeat(1200)`。
5. `children` 菜单树中祖先 `onSelect` + 后代 `meta.label`。
6. 父 `execute` + 子 `payload.label`。
7. 父 `onCommand` + 子 `meta.title`。
8. 父 `callback` + 子 `payload.label`。
9. 父 `submit` + 子 `extra.description`。

## 5. 成功 fixture（必须通过）

保留并验证通过：

1. 纯说明对象（无祖先交互字段）：
   - `meta.label='利润计算说明'`
   - `description='只读帮助文案'`
2. 只读动作：`{ label: '查看详情', onClick: goDetail }`
3. 只读动作：`{ label: '查询', onClick: loadRows }`
4. 只读动作：`{ label: '返回', onClick: goBack }`

## 6. 验证命令与结果

### 6.1 前端验证

1. `npm run check:style-profit-contracts`
   - 结果：通过（`Style-profit contract check passed. Scanned files: 24`）

2. `npm run test:style-profit-contracts`
   - 结果：通过（`All style-profit contract fixture tests passed. scenarios=43`）

3. `npm run verify`
   - 结果：通过（production/style-profit 契约检查、typecheck、build 全通过）

4. `npm audit --audit-level=high`
   - 结果：通过（`found 0 vulnerabilities`）

### 6.2 后端只读回归（未改后端代码）

1. `.venv/bin/python -m pytest -q tests/test_style_profit_api.py tests/test_style_profit_api_permissions.py tests/test_style_profit_api_audit.py tests/test_style_profit_api_errors.py`
   - 结果：`34 passed, 1 warning`

2. `.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)`
   - 结果：通过

### 6.3 祖先链反向测试覆盖扫描

执行：

```bash
rg -n "meta|props|extra|payload|children|onClick|handler|command|onSelect|onCommand|callback|execute|利润计算说明|利润率计算规则|利润快照来源说明|repeat\(1200\)" \
  /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs
```

结果：命中新增祖先链场景（含 `meta/props/extra/payload/children`、`onCommand/callback/execute`、`repeat(1200)`）。

### 6.4 业务禁线扫描

执行：

```bash
rg -n "款式利润报表计算|利润快照列表生成|利润金额重新计算|款式利润.{0,16}(新建|创建|生成|重算|重新计算|计算|核算|提交|保存)|((新建|创建|生成|重算|重新计算|计算|核算|提交|保存).{0,16}款式利润)|利润报表.{0,16}(新建|创建|生成|重算|重新计算|计算|核算|提交|保存)|((新建|创建|生成|重算|重新计算|计算|核算|提交|保存).{0,16}利润报表)|毛利核算|净利核算|利润一键生成|createProfit|generateProfit|recalculateProfit|createSnapshot|generateSnapshot|recalculateSnapshot|profitCreate|profitGenerate|profitRecalculate" \
  /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src
```

结果：无命中（`src` 业务文件未出现写入口语义）。

## 7. 提交摘要

`git show --stat --oneline --name-only 590ed04`：

```text
590ed04 fix: check style profit action ancestor chain
06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs
06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs
```

## 8. 结论

1. 已完成 Action 祖先对象链门禁整改。
2. 父对象交互字段 + 子对象利润说明文案绕过已封堵。
3. 间隔超过 1000 字符场景仍可稳定识别。
4. 合法只读说明与只读动作未被误杀。
5. 未开放创建快照入口。
6. 未进入 TASK-006。

