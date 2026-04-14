# TASK-005J1 多行交互上下文门禁整改证据

- 任务编号：TASK-005J1
- 记录时间：2026-04-14 18:20 CST
- 执行人：Codex
- 执行基线 HEAD：`ba3ef7351f3d252400e0f39cc70c1b6afd396d29`

## 问题与目标

审计指出：只读说明文案交互上下文识别仅看“文案所在行”，多行按钮/菜单/action/路由块存在绕过风险。

本次目标：将门禁升级为多行上下文识别，确保“利润计算说明”等只读文案一旦位于交互入口（即使跨行）也会被阻断。

## 代码整改

修改文件：
1. `06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
2. `06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`
3. `03_需求与设计/02_开发计划/TASK-005J1_多行交互上下文门禁整改证据.md`

### check-style-profit-contracts.mjs

1. 删除“仅按单行识别交互上下文”的逻辑。
2. 新增多行交互识别能力：
   - 前后窗口检测（默认半径 300 字符）
   - 未闭合交互标签块检测：
     - `<el-button>...</el-button>`
     - `<button>...</button>`
     - `<el-menu-item>...</el-menu-item>`
     - `<menu-item>...</menu-item>`
   - 交互窗口关键特征：`@click`、`onClick`、`router.push`、`path:`、`name:`
   - 标识符上下文检测：函数名/变量名中包含只读说明文案时视为交互上下文
3. 只读说明短语仍可在纯说明文本中通过，但在交互上下文中统一失败。
4. 未恢复 substring 白名单豁免，未做全文件/全目录跳过。

### test-style-profit-contracts.mjs

新增并通过（应失败）反向测试：
1. 多行 `<el-button>`：`利润计算说明`
2. 多行 `<button>`：`利润率计算规则`
3. 多行 `<el-menu-item @click>`：`利润快照来源说明`
4. 多行 action 配置：`label: '利润计算说明'` + `onClick`
5. 多行路由配置：`path: '/reports/style-profit/calculate'`

保留并未降级：
- TASK-005H / TASK-005I / TASK-005I1 / TASK-005J 原有反向测试与成功 fixture
- `style_profit:snapshot_create` / `snapshot_create` / `idempotency_key` 等禁线

## 验证结果

执行目录：`/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc`

1. `npm run check:style-profit-contracts`
   - 结果：通过（Scanned files: 24）
2. `npm run test:style-profit-contracts`
   - 结果：通过（scenarios=27）
3. `npm run verify`
   - 结果：通过（production/style-profit 契约、typecheck、build 全通过）
4. `npm audit --audit-level=high`
   - 结果：通过（found 0 vulnerabilities）

执行目录：`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service`

5. `.venv/bin/python -m pytest -q tests/test_style_profit_api.py tests/test_style_profit_api_permissions.py tests/test_style_profit_api_audit.py tests/test_style_profit_api_errors.py`
   - 结果：34 passed, 1 warning
6. `.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)`
   - 结果：通过

## 审计复现用例扫描

命令：

```bash
rg -n "<el-button>|<button>|<el-menu-item|onClick|利润计算说明|利润率计算规则|利润快照来源说明" /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs
```

结果：多行交互上下文反向测试均存在（含按钮、菜单、onClick/action 配置和相关文案）。

## 业务禁线扫描

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
- 未开放创建/生成/重算利润快照入口

## 结论

TASK-005J1 已完成：多行交互上下文绕过已关闭，说明文案仅在非交互场景可通过，交互入口（含跨行）会被稳定阻断。TASK-006 仍未进入。
