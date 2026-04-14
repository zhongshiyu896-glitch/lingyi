# TASK-005J 款式利润只读说明文案防误杀与门禁基线证据

- 任务编号：TASK-005J
- 记录时间：2026-04-14 18:09 CST
- 执行人：Codex
- 执行基线 HEAD：`9146f0cea171aff488aa907f373bbc0864648bbc`

## 本次整改目标

在不恢复 substring 白名单绕过的前提下，补齐“合法只读说明文案”成功 fixture，并引入“位置敏感”反向门禁，防止说明文字出现在按钮/菜单/路由/函数等交互入口。

## 实施内容

修改文件：
1. `06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
2. `06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`
3. `03_需求与设计/02_开发计划/TASK-005J_款式利润只读说明文案防误杀与门禁基线证据.md`

### 1) 门禁逻辑增强（位置敏感）

- 新增只读说明短语集合（8 条）：
  - 利润计算说明
  - 利润率计算规则
  - 实际成本计算口径说明
  - 标准成本计算口径说明
  - 款式利润报表查看说明
  - 利润快照来源说明
  - 利润金额展示规则
  - 未解析来源处理说明
- 新增交互上下文识别：
  - `<el-button>` / `<button>` / `<el-menu-item>` / `<menu-item>`
  - `@click` / `onClick`
  - `router.push`
  - `path:` / `name:`
  - `function`、`const/let/var ... =` 等函数或变量定义上下文
- 新增范围匹配：只读说明短语的匹配范围收集 `collectExplanationRanges()`。
- 新增判定：
  - 语义命中若位于只读说明短语范围且不在交互上下文，允许通过。
  - 只读说明短语若出现在交互上下文，直接失败：`只读说明文案不得出现在交互入口上下文`。

### 2) 成功 fixture（防误杀）

在 base fixture 的只读详情模板中新增 8 条说明文案，验证纯说明文本可以通过门禁。

### 3) 新增反向测试（必须失败）

新增并通过反向失败断言：
1. `<el-button>利润计算说明</el-button>`
2. `<button>利润率计算规则</button>`
3. 带 `@click` 的菜单项 `利润快照来源说明`

并保留且继续通过 TASK-005H / I / I1 既有反向场景（未删除、未降级）。

## 验证结果

执行目录：`/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc`

1. `npm run check:style-profit-contracts`
   - 结果：通过（Scanned files: 24）
2. `npm run test:style-profit-contracts`
   - 结果：通过（scenarios=22）
3. `npm run verify`
   - 结果：通过（production/style-profit 契约、typecheck、build 全通过）
4. `npm audit --audit-level=high`
   - 结果：通过（found 0 vulnerabilities）

执行目录：`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service`

5. `.venv/bin/python -m pytest -q tests/test_style_profit_api.py tests/test_style_profit_api_permissions.py tests/test_style_profit_api_audit.py tests/test_style_profit_api_errors.py`
   - 结果：34 passed, 1 warning
6. `.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)`
   - 结果：通过

## 任务要求扫描

### 成功 fixture 文案检查

命令：

```bash
rg -n "利润计算说明|利润率计算规则|实际成本计算口径说明|标准成本计算口径说明|款式利润报表查看说明|利润快照来源说明|利润金额展示规则|未解析来源处理说明" /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs
```

结果：8 条说明文案均存在于成功 fixture（并可见新增交互反向用例）。

### 业务禁线扫描

命令：

```bash
rg -n "款式利润报表计算|利润快照列表生成|利润金额重新计算|款式利润.{0,16}(新建|创建|生成|重算|重新计算|计算|核算|提交|保存)|((新建|创建|生成|重算|重新计算|计算|核算|提交|保存).{0,16}款式利润)|利润报表.{0,16}(新建|创建|生成|重算|重新计算|计算|核算|提交|保存)|((新建|创建|生成|重算|重新计算|计算|核算|提交|保存).{0,16}利润报表)|毛利核算|净利核算|利润一键生成|createProfit|generateProfit|recalculateProfit|createSnapshot|generateSnapshot|recalculateSnapshot|profitCreate|profitGenerate|profitRecalculate" /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src
```

结果：无命中（空输出）。

## 边界确认

- 未修改 `07_后端/**`
- 未修改 `.github/**`
- 未修改 `02_源码/**`
- 未修改 `TASK-006*`
- 未纳入 `.pytest-postgresql-*.xml`
- 未新增任何利润快照创建/生成/重算入口
- 未恢复 substring 白名单豁免
- 未做全文件/全目录跳过语义扫描

## 结论

TASK-005J 已完成：只读说明文案已具备稳定成功 fixture，且在交互上下文中的同类文案会被门禁阻断，避免误杀与绕过在后续迭代中反复。TASK-006 仍未进入。
