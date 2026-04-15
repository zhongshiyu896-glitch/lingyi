# TASK-005J13 运行时 ActionKey 等价语法门禁整改工程任务单

- 任务编号：TASK-005J13
- 模块：款式利润报表 / 前端只读契约门禁
- 优先级：P0
- 任务类型：审计阻断整改
- 前置审计：审计意见书第 131 份
- 更新时间：2026-04-14 21:38 CST
- 作者：技术架构师

## 一、任务目标

修复 `check-style-profit-contracts.mjs` 对运行时显式 `ActionKey` 注入的等价语法绕过，确保 style-profit surface 内任何通过别名、括号访问、解构/赋值别名、变量 source 合并方式注入 `onClick/handler/command/submit` 等 action key 的写入口都 fail closed。

## 二、背景问题

审计官在 TASK-005J12 复审中确认标准写法已被拦截，但以下等价语法仍可通过门禁：

```ts
Object['defineProperty'](item, 'onClick', { value: openHelp })
Reflect['set'](item, 'onClick', openHelp)
Object['assign'](item, { onClick: openHelp })

const defineProperty = Object.defineProperty
defineProperty(item, 'onClick', { value: openHelp })

const action = { onClick: openHelp }
Object.assign(item, action)
```

这些写法本质上仍是在运行时给只读利润页面对象注入交互 action，会绕过“款式利润前端只读”边界，必须作为 P1 阻断修复。

## 三、涉及文件

允许修改：

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/package.json`（仅允许在已有脚本基础上补测试命令时修改）
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005J13_运行时ActionKey等价语法门禁整改证据.md`

禁止修改：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/**`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/**` 中非 style-profit 相关文件
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/**` 中非 style-profit 相关文件
- `/Users/hh/Desktop/领意服装管理系统/.github/**`
- `/Users/hh/Desktop/领意服装管理系统/02_源码/**`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/**/TASK-006*`
- `.pytest-postgresql-*.xml`、coverage、dist、node_modules 等运行生成物

## 四、实现要求

### 4.1 括号访问等价调用必须识别

必须识别并拦截以下调用形式：

```ts
Object['defineProperty'](item, 'onClick', { value: openHelp })
Object["defineProperty"](item, 'onClick', { value: openHelp })
Object['defineProperties'](item, { onClick: { value: openHelp } })
Reflect['set'](item, 'onClick', openHelp)
Object['assign'](item, { onClick: openHelp })
```

要求：

1. 解析 `PropertyAccessExpression` 与 `ElementAccessExpression` 两类 callee。
2. 当 callee 等价于 `Object.defineProperty/Object.defineProperties/Object.assign/Reflect.set` 时，按既有显式 action key 注入规则 fail closed。
3. action key 范围沿用现有门禁清单，不得缩小。

### 4.2 别名调用必须识别

必须识别并拦截以下别名形式：

```ts
const defineProperty = Object.defineProperty
defineProperty(item, 'onClick', { value: openHelp })

const assign = Object.assign
assign(item, { onClick: openHelp })

const set = Reflect.set
set(item, 'onClick', openHelp)
```

要求：

1. 在同一文件 AST 内建立安全的本地别名表。
2. 只需要覆盖 `const/let/var alias = Object.defineProperty/Object.defineProperties/Object.assign/Reflect.set`。
3. 别名只允许在当前文件内分析，不需要跨文件追踪。
4. 如果别名来源不明、被重新赋值或无法确认，遇到 style-profit surface 中疑似 action 注入时必须 fail closed。

### 4.3 Object.assign 变量 source 必须识别

必须识别并拦截以下变量 source 合并：

```ts
const action = { onClick: openHelp }
Object.assign(item, action)

const action = { handler: openHelp }
Object['assign'](item, action)
```

要求：

1. 在同一文件内追踪简单对象字面量变量：`const action = { onClick: ... }`。
2. 当 `Object.assign(target, action)` 的 source 变量包含 action key，必须 fail closed。
3. 对多个 source 参数逐一检查：`Object.assign(item, base, action, extra)`。
4. 对 spread、动态 source、无法解析的 source，在 style-profit surface 内必须沿用 fail closed 策略，不得静默放行。

### 4.4 不允许误放行只读说明文案

以下只读文案不得作为运行时 action 注入的豁免理由：

- `查看详情`
- `查询`
- `返回`
- `利润计算说明`
- `利润率计算规则`
- `款式利润报表`

只要同一对象或同一 action 构造链路中出现运行时 action key 注入，就必须 fail closed。

### 4.5 允许的成功场景

不得误杀以下场景：

1. 普通只读对象字面量，没有运行时 action 注入。
2. 非 action 字段写入，例如 `item.tooltip = '说明'`。
3. 纯读取表达式，例如 `const fn = item['onClick']`，除非同时形成写入或调用入口。
4. 既有合法只读导航 fixture，前提是不通过运行时注入新增 action key。

## 五、必须补充的反向测试

在 `test-style-profit-contracts.mjs` 中至少新增以下反向测试，每个都必须明确断言门禁失败：

1. `Object['defineProperty'](item, 'onClick', { value: openHelp })`
2. `Reflect['set'](item, 'onClick', openHelp)`
3. `Object['assign'](item, { onClick: openHelp })`
4. `const defineProperty = Object.defineProperty; defineProperty(item, 'onClick', ...)`
5. `const assign = Object.assign; assign(item, { onClick: openHelp })`
6. `const set = Reflect.set; set(item, 'onClick', openHelp)`
7. `const action = { onClick: openHelp }; Object.assign(item, action)`
8. `const action = { handler: openHelp }; Object['assign'](item, action)`
9. `Object.assign(item, base, action, extra)` 中 `action` 含 action key
10. 动态/无法解析 source 合并在 style-profit surface 内 fail closed

## 六、必须保留的回归测试

不得删除、跳过、降级以下既有测试：

- TASK-005H 全局只读边界测试
- TASK-005I/I1 中文语义写入口测试
- TASK-005J/J1/J2/J3/J4/J5/J6 多行、对象链、引号键、方法简写、计算属性键测试
- TASK-005J7/J8/J9/J10/J11/J12 computed key、AST、运行时动态/显式 action 注入测试

如果测试数量变化，证据文件必须说明新增/删除原因。删除反向测试必须视为不通过。

## 七、验证命令

工程师必须执行并在证据文件中贴摘要：

```bash
cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc
npm run check:style-profit-contracts
npm run test:style-profit-contracts
npm run verify
npm audit --audit-level=high

cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest -q tests/test_style_profit_api.py
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
```

## 八、验收标准

- `Object['defineProperty']`、`Reflect['set']`、`Object['assign']` 等价调用全部被拦截。
- `defineProperty/assign/set` 本地别名调用全部被拦截。
- `Object.assign(item, action)` 中 `action` 变量 source 含 action key 时被拦截。
- 多 source 合并逐一检查，任何 source 含 action key 均失败。
- 动态/无法解析 source 在 style-profit surface 内 fail closed。
- 非 action 字段运行时写入不被误杀。
- 纯读取动态 key 不被误杀。
- `npm run verify` 通过。
- 后端 style-profit API 定向回归通过。
- 未修改后端业务、workflow、`02_源码`、TASK-006 或运行生成物。
- 审计官复审通过后，才允许进入 TASK-005K 或 TASK-005 收尾封版评估。

## 九、禁止事项

- 禁止开放 `POST /api/reports/style-profit/snapshots` 前端入口。
- 禁止新增 `createStyleProfitSnapshot`、`snapshot_create`、`idempotency_key` 等创建入口调用。
- 禁止引入新的第三方 parser 依赖。
- 禁止把 TASK-006 解锁或写入 TASK-006 工程实现内容。
- 禁止通过扩大白名单、跳过测试、缩小扫描范围来让门禁变绿。

## 十、交付物

- 更新后的 `check-style-profit-contracts.mjs`
- 更新后的 `test-style-profit-contracts.mjs`
- `TASK-005J13_运行时ActionKey等价语法门禁整改证据.md`
- 验证命令摘要
- 禁改边界扫描摘要
