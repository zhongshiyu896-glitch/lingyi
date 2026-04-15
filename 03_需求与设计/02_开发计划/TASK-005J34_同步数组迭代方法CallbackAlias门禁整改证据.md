# TASK-005J34 同步数组迭代方法 Callback Alias 门禁整改证据

## 1. 任务范围
- 任务编号：`TASK-005J34`
- 目标：补齐同步数组迭代方法 callback alias 门禁，尤其 `reduce/reduceRight/flatMap/findIndex/findLast/findLastIndex`。
- 仅修改前端门禁脚本、前端门禁测试脚本、本证据文档。
- 未开放快照创建入口；未进入 `TASK-006`。

## 2. 修改文件
1. `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
2. `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`
3. `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005J34_同步数组迭代方法CallbackAlias门禁整改证据.md`

## 3. 实现说明

### 3.1 迭代门禁从 name set 升级为 method descriptor map
- 将 `runtimeArrayIterationMethodNameSet` 升级为 `runtimeArrayIterationMethodDescriptorMap`。
- descriptor 包含：
  - `callback_argument_index`
  - `current_item_parameter_index`
- 覆盖方法与参数位：
  - index=0：`forEach/map/some/every/filter/find/findIndex/findLast/findLastIndex/flatMap`
  - index=1：`reduce/reduceRight`

### 3.2 callback 参数按 descriptor 绑定
- `applyRuntimeIterationCallbackSummaryAtCall()` 改为按 descriptor 取 callback 与 current item 参数位。
- `reduce/reduceRight` 使用 callback 第 2 个参数绑定 current item。
- 对 `reduce/reduceRight` 额外回填 callback 第 1 参数（优先初始值，其次首元素）以降低误判 unresolved。

### 3.3 fail-closed 规则
- descriptor 无效、callback 缺失、iterable 不可静态还原时，继续按 conservative/fail-closed 路径处理。
- 未知 collection + 可污染 callback（写入/逃逸/unknown）时，将 tracked arrays 标记 unknown。

## 4. 新增/补齐测试

### 4.1 新增反向测试（均应失败）
已新增并通过以下 J34 场景：
1. `findIndex` callback 解构写入污染
2. `findLast` callback 解构写入污染
3. `findLastIndex` callback 解构写入污染
4. `flatMap` callback 解构写入污染
5. `reduce` callback 第 2 参数解构写入污染
6. `reduceRight` callback 第 2 参数解构写入污染
7. `reduce` callback 第 2 参数对象解构写入污染
8. `collection.reduce`（来源不可静态还原）+ callback 解构写入 fail closed
9. `flatMap` callback `splice` 污染
10. `findIndex` callback `escape(alias)` fail closed
11. `reduce` 污染后 `new unknownCtor(...args)`
12. `reduce` 污染后 `Reflect.construct(Worker, args)`

### 4.2 合法成功 fixture（继续通过）
- 在 base fixture 保留并通过以下只读同步迭代：
  - `findIndex/findLast/findLastIndex/flatMap` 只读 callback
  - `reduce/reduceRight` 只读 callback（不写入/不逃逸）
- 保留 `nums.reduce((acc,[n]) => acc + n, 0)` 非 Worker 正常场景。

## 5. 验证命令与结果

### 5.1 前端
在 `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc` 执行：

```bash
npm run check:style-profit-contracts
npm run test:style-profit-contracts
npm run verify
npm audit --audit-level=high
```

结果：
- `check:style-profit-contracts`：通过（`Style-profit contract check passed. Scanned files: 24`）
- `test:style-profit-contracts`：通过（`All style-profit contract fixture tests passed. scenarios=443`）
- `verify`：通过（包含 production/style-profit contracts + typecheck + build）
- `npm audit --audit-level=high`：`found 0 vulnerabilities`

### 5.2 后端定向回归（只跑不改）
在 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service` 执行：

```bash
.venv/bin/python -m pytest -q tests/test_style_profit_api.py tests/test_style_profit_api_permissions.py tests/test_style_profit_api_audit.py tests/test_style_profit_api_errors.py
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
```

结果：
- `pytest`：`34 passed, 1 warning in 0.92s`
- `py_compile`：通过（无输出）

## 6. 扫描记录

### 6.1 J34 覆盖扫描
执行：

```bash
rg -n "reduceRight|flatMap|findIndex|findLast|findLastIndex|\[\[args\]\]\.reduce\(|\[\[args\]\]\.reduceRight\(|collection\.reduce\(" scripts/test-style-profit-contracts.mjs
```

结果：命中新增长反向测试与合法 fixture。

### 6.2 业务禁线扫描（src）
执行：

```bash
rg -n "款式利润报表计算|利润快照列表生成|利润金额重新计算|款式利润.{0,16}(新建|创建|生成|重算|重新计算|计算|核算|提交|保存)|((新建|创建|生成|重算|重新计算|计算|核算|提交|保存).{0,16}款式利润)|利润报表.{0,16}(新建|创建|生成|重算|重新计算|计算|核算|提交|保存)|((新建|创建|生成|重算|重新计算|计算|核算|提交|保存).{0,16}利润报表)|毛利核算|净利核算|利润一键生成|createProfit|generateProfit|recalculateProfit|createSnapshot|generateSnapshot|recalculateSnapshot|profitCreate|profitGenerate|profitRecalculate" src
```

结果：无命中（`rg` exit code 1）。

## 7. 禁改边界确认
- 未修改 `/07_后端/**`、`/.github/**`、`/02_源码/**`、`TASK-006*`。
- 未新增第三方 parser 依赖。
- 未新增 `POST /api/reports/style-profit/snapshots` 前端调用。

## 8. 提交信息
- 当前基线 HEAD（提交前）：`28abbcc`
- 计划提交信息：`fix: map style profit sync iteration callback aliases`
- commit hash（代码修复提交）：`0daa8a9`
