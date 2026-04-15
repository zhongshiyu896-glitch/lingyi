# TASK-005J12 运行时显式 Action Key 注入门禁整改工程任务单

- 模块：款式利润报表 / 前端只读门禁稳定化整改
- 任务编号：TASK-005J12
- 优先级：P1
- 版本：V1.0
- 更新时间：2026-04-14 21:15 CST
- 作者：技术架构师
- 前置审计：审计意见书第 130 份，`TASK-005J11` 有条件通过但存在高危运行时显式 action key 注入绕过
- 当前有效 HEAD：`f359fa710b0468f006c28ef7ff928c4222702761`
- 架构依据：`/03_需求与设计/01_架构设计/06_模块设计_款式利润报表.md` V4.9；`ADR-125`

## 1. 任务目标

修复运行时“显式字面量 action key 注入”绕过问题。`TASK-005J11` 已拦截动态 key 注入，例如 `item[ACTION_KEY] = goDetail`，但仍未覆盖显式 action key 的运行时注入，例如 `item['onClick'] = goDetail`、`Object.defineProperty(item, 'onClick', { value: openHelp })`、`Object.assign(item, { onClick: openHelp })`。

本任务要求：在 style-profit surface 内，运行时注入显式 action key 也必须 fail closed。不得因为 action key 是字符串字面量，或 label 是 `查看详情/查询/返回`，就允许运行时注入。允许显式 action key 出现在对象字面量中并按既有只读规则判断；但禁止对象创建后再通过赋值、defineProperty、Reflect.set、Object.assign 等方式注入 action key。

本任务只修复前端契约门禁、测试和证据，不开放利润快照创建入口，不进入 TASK-006。

## 2. 审计问题来源

审计意见书第 130 份指出以下样例仍可绕过：

```ts
const item = { label: '利润计算说明' }
Object.defineProperty(item, 'onClick', { value: openHelp })
```

以及：

```ts
Object.assign(item, { onClick: openHelp })
item['onClick'] = openHelp
```

根因：运行时注入规则只拦截动态 key，没有拦截显式字面量 action key 的运行时注入。

## 3. 允许修改文件

### 3.1 前端门禁文件

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`

### 3.2 前端约定文档

如需记录门禁边界，可追加：

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/README.md`

### 3.3 文档证据

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005J12_运行时显式ActionKey注入门禁整改_工程任务单.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005J12_运行时显式ActionKey注入门禁整改证据.md`（交付时新建）
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/当前 sprint 任务清单.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/03_技术决策记录.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/06_模块设计_款式利润报表.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/架构师会话日志.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录/审计官会话日志.md`

## 4. 禁止修改文件与行为

1. 禁止修改 `/Users/hh/Desktop/领意服装管理系统/07_后端/**`。
2. 禁止修改 `/Users/hh/Desktop/领意服装管理系统/.github/**`。
3. 禁止修改 `/Users/hh/Desktop/领意服装管理系统/02_源码/**`。
4. 禁止创建或修改任何 `TASK-006*` 文件。
5. 禁止提交 `.pytest-postgresql-*.xml`。
6. 禁止新增 `POST /api/reports/style-profit/snapshots` 的前端调用。
7. 禁止开放创建/生成/重算利润快照入口。
8. 禁止只拦截动态 key，忽略显式字面量 action key 的运行时注入。
9. 禁止把 `查看详情/查询/返回` 作为运行时 action key 注入的豁免理由。
10. 禁止新增第三方 parser 依赖；继续使用已有 `typescript` devDependency。
11. 禁止使用 `git add .` 或 `git add -A`。

## 5. 必做整改

### 5.1 显式 action key 集合

运行时注入检测必须至少覆盖以下显式 action key：

1. `onClick`
2. `handler`
3. `action`
4. `command`
5. `onSelect`
6. `onCommand`
7. `callback`
8. `execute`
9. `submit`
10. `onConfirm`
11. `onSubmit`
12. `click`
13. `open`

### 5.2 ElementAccessExpression 显式 key 写入检测

必须 fail closed：

```ts
item['onClick'] = openHelp
item["handler"] = showRule
item['submit'] ||= submitProfit
item["execute"] ??= executeProfit
item['onSelect'] &&= selectMenu
```

判断口径：

1. 左侧为 `ElementAccessExpression`。
2. key 为字符串字面量且属于显式 action key 集合。
3. 操作符为赋值或复合赋值。
4. 在 style-profit surface 内必须失败。
5. 不得因为目标对象名、label 文案、函数名看似只读而放行。

### 5.3 PropertyAccessExpression 显式 key 写入检测

必须 fail closed：

```ts
item.onClick = openHelp
item.handler = showRule
item.submit ||= submitProfit
item.execute ??= executeProfit
```

判断口径：

1. 左侧为 `PropertyAccessExpression`。
2. 属性名属于显式 action key 集合。
3. 操作符为赋值或复合赋值。
4. 在 style-profit surface 内必须失败。

### 5.4 Object.defineProperty 显式 key 检测

必须 fail closed：

```ts
Object.defineProperty(item, 'onClick', { value: openHelp })
Object.defineProperty(item, "handler", { value: showRule })
Object.defineProperty(item, 'submit', { value: submitProfit })
```

判断口径：

1. callee 为 `Object.defineProperty`。
2. 第二个参数为字符串字面量且属于显式 action key 集合。
3. 在 style-profit surface 内必须失败。
4. 第二个参数为非字面量时继续沿用 TASK-005J11 动态 key fail closed。

### 5.5 Object.defineProperties 显式 key 检测

必须 fail closed：

```ts
Object.defineProperties(item, {
  onClick: { value: openHelp },
  'handler': { value: showRule },
  ["submit"]: { value: submitProfit },
})
```

判断口径：

1. callee 为 `Object.defineProperties`。
2. 第二个参数对象中出现显式 action key 时必须失败。
3. 第二个参数对象中出现 dynamic / unknown computed key 时继续 fail closed。

### 5.6 Reflect.set 显式 key 检测

必须 fail closed：

```ts
Reflect.set(item, 'onClick', openHelp)
Reflect.set(item, "handler", showRule)
Reflect.set(item, 'submit', submitProfit)
```

判断口径：

1. callee 为 `Reflect.set`。
2. 第二个参数为字符串字面量且属于显式 action key 集合。
3. 在 style-profit surface 内必须失败。
4. 第二个参数为非字面量时继续沿用 TASK-005J11 动态 key fail closed。

### 5.7 Object.assign 显式 action key source 检测

必须 fail closed：

```ts
Object.assign(item, { onClick: openHelp })
Object.assign(item, { 'handler': showRule })
Object.assign(item, { ["submit"]: submitProfit })
```

判断口径：

1. callee 为 `Object.assign`。
2. 任一 source object literal 出现显式 action key 时必须失败。
3. 任一 source object literal 出现 dynamic / unknown computed key 时继续 fail closed。
4. 不允许用 `查看详情/查询/返回` 豁免运行时 action key 注入。

### 5.8 对象字面量中显式 action key 的既有规则不变

以下写法不因本任务一律失败，继续按既有只读规则判断：

```ts
const item = {
  label: '查看详情',
  onClick: goDetail,
}
```

说明：本任务禁止的是“运行时注入 action key”，不是禁止所有对象字面量中的合法只读 action。

## 6. 必补反向测试

必须在 `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs` 中补充以下失败用例：

### 6.1 item['onClick'] 显式 key 赋值

```ts
const item = { label: '利润计算说明' }
item['onClick'] = openHelp
```

预期：门禁失败。

### 6.2 item.onClick 显式 key 赋值

```ts
const item = { label: '利润计算说明' }
item.onClick = openHelp
```

预期：门禁失败。

### 6.3 Object.defineProperty 显式 key

```ts
const item = { label: '利润计算说明' }
Object.defineProperty(item, 'onClick', { value: openHelp })
```

预期：门禁失败。

### 6.4 Object.assign 显式 key

```ts
const item = { label: '利润计算说明' }
Object.assign(item, { onClick: openHelp })
```

预期：门禁失败。

### 6.5 Reflect.set 显式 key

```ts
const item = { label: '利润计算说明' }
Reflect.set(item, 'onClick', openHelp)
```

预期：门禁失败。

### 6.6 Object.defineProperties 显式 key

```ts
const item = { label: '利润计算说明' }
Object.defineProperties(item, {
  onClick: { value: openHelp },
})
```

预期：门禁失败。

### 6.7 只读导航 label 也不得豁免运行时注入

```ts
const item = { label: '查看详情' }
item['onClick'] = goDetail
```

预期：门禁失败。

### 6.8 Vue script setup 显式 action key 注入

```vue
<script setup lang="ts">
const item = { label: '利润计算说明' }
Object.assign(item, { onClick: openHelp })
</script>
```

预期：门禁失败。

### 6.9 真实长距离显式 action key 注入

```ts
const item = {
  label: '利润计算说明',
  filler: '<真实1200字符>',
}
Object.defineProperty(item, 'onClick', { value: openHelp })
```

预期：门禁失败，并断言 `label` 与 `Object.defineProperty` 的真实距离超过 1200。

## 7. 必保留成功测试

以下合法场景必须继续通过：

1. 对象字面量中合法只读 action：`{ label: '查看详情', onClick: goDetail }`。
2. 对象字面量中合法查询 action：`{ label: '查询', onClick: loadRows }`。
3. 对象字面量中合法返回 action：`{ label: '返回', onClick: goBack }`。
4. 非 action 字段运行时写入：`item.disabled = true`。
5. 非 action 字段 `Object.assign(item, { disabled: true })`。
6. 读取型动态 key：`const value = item[ACTION_KEY]`，且不构成写入或 action 入口。
7. Vue template 只读说明文案成功 fixture。

## 8. 验证命令

### 8.1 前端验证

```bash
cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc
npm run check:style-profit-contracts
npm run test:style-profit-contracts
npm run verify
npm audit --audit-level=high
```

### 8.2 后端只读回归

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest -q tests/test_style_profit_api.py tests/test_style_profit_api_permissions.py tests/test_style_profit_api_audit.py tests/test_style_profit_api_errors.py
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
```

### 8.3 显式 action key 注入覆盖扫描

```bash
rg -n "Object\.defineProperty|Object\.defineProperties|Reflect\.set|Object\.assign|PropertyAccessExpression|ElementAccessExpression|item\[['\"]onClick['\"]\]|item\.onClick|explicit action key|显式 action|运行时注入|fail closed" \
  /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs \
  /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs
```

### 8.4 业务禁线扫描

```bash
rg -n "款式利润报表计算|利润快照列表生成|利润金额重新计算|款式利润.{0,16}(新建|创建|生成|重算|重新计算|计算|核算|提交|保存)|((新建|创建|生成|重算|重新计算|计算|核算|提交|保存).{0,16}款式利润)|利润报表.{0,16}(新建|创建|生成|重算|重新计算|计算|核算|提交|保存)|((新建|创建|生成|重算|重新计算|计算|核算|提交|保存).{0,16}利润报表)|毛利核算|净利核算|利润一键生成|createProfit|generateProfit|recalculateProfit|createSnapshot|generateSnapshot|recalculateSnapshot|profitCreate|profitGenerate|profitRecalculate" \
  /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src
```

## 9. 交付证据要求

工程师必须新建：

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005J12_运行时显式ActionKey注入门禁整改证据.md`

证据文件必须包含：

1. 修改文件清单。
2. 显式 action key 集合。
3. ElementAccessExpression 字符串字面量 action key 写入检测说明。
4. PropertyAccessExpression action key 写入检测说明。
5. Object.defineProperty / Object.defineProperties / Reflect.set / Object.assign 显式 key 检测说明。
6. 对象字面量合法只读 action 不误杀的边界说明。
7. 新增反向测试清单。
8. 成功 fixture 清单。
9. 真实长距离 fixture 生成方式与距离断言结果。
10. 所有验证命令和结果。
11. 禁改范围扫描结果。
12. commit hash。
13. 是否新增依赖：必须写“否，继续使用现有 typescript devDependency”。

## 10. 提交要求

### 10.1 白名单 staged

只允许 staged：

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`
- 必要时允许的 `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/README.md`
- 必要时允许的 style_profit 只读页面小范围修正文件
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005J12_运行时显式ActionKey注入门禁整改证据.md`
- 本任务相关架构、计划、审计文档

### 10.2 推荐提交信息

```bash
git commit -m "fix: detect explicit runtime style profit actions"
```

## 11. 验收标准

1. `item['onClick'] = openHelp` 必须失败。
2. `item.onClick = openHelp` 必须失败。
3. `Object.defineProperty(item, 'onClick', { value: openHelp })` 必须失败。
4. `Object.assign(item, { onClick: openHelp })` 必须失败。
5. `Reflect.set(item, 'onClick', openHelp)` 必须失败。
6. `Object.defineProperties(item, { onClick: { value: openHelp } })` 必须失败。
7. `const item = { label: '查看详情' }; item['onClick'] = goDetail` 必须失败。
8. Vue script setup 中显式 action key 注入必须失败。
9. 真实长距离显式 action key 注入 fixture 必须失败，且距离断言超过 1200。
10. 对象字面量中的合法只读 action 不被误杀。
11. 非 action 字段运行时写入不被误杀。
12. 读取型动态 key 不构成写入时不被误杀。
13. `npm run test:style-profit-contracts` 通过。
14. `npm run verify` 通过。
15. `npm audit --audit-level=high` 为 0 high vulnerabilities。
16. 后端 style-profit API 定向回归通过。
17. 未新增第三方 parser 依赖。
18. 未开放创建快照入口。
19. 未进入 TASK-006。
