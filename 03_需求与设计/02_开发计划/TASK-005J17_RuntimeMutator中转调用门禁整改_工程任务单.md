# TASK-005J17 Runtime Mutator 中转调用门禁整改工程任务单

- 任务编号：TASK-005J17
- 模块：款式利润报表 / 前端只读契约门禁
- 优先级：P0
- 任务类型：审计阻断整改
- 前置审计：审计意见书第 135 份
- 更新时间：2026-04-14 22:55 CST
- 作者：技术架构师

## 一、任务目标

修复 `check-style-profit-contracts.mjs` 对 runtime mutator sink 中转调用的剩余绕过，覆盖逗号表达式、条件表达式命名空间、数组容器中转、对象容器中转，确保 style-profit surface 内任何等价调用 `Object.defineProperty/Object.defineProperties/Object.assign/Reflect.set` 的路径都 fail closed。

## 二、背景问题

TASK-005J16 已关闭第 134 份审计中的 `Reflect.apply`、字符串/计算属性解构、`globalThis/window` 命名空间解构绕过，但审计官在第 135 份审计中复现以下绕过：

```ts
;(0, Object.defineProperty)(item, 'onClick', { value: openHelp })

const Obj = true ? Object : Object
Obj.defineProperty(item, 'onClick', { value: openHelp })

const mutators = [Object.defineProperty]
mutators[0](item, 'onClick', { value: openHelp })

const mutators = { dp: Object.defineProperty }
mutators.dp(item, 'onClick', { value: openHelp })
```

这些路径仍等价于源 mutator API，必须继续拦截。

## 三、涉及文件

允许修改：

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005J17_RuntimeMutator中转调用门禁整改证据.md`

禁止修改：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/**`
- `/Users/hh/Desktop/领意服装管理系统/.github/**`
- `/Users/hh/Desktop/领意服装管理系统/02_源码/**`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/**/TASK-006*`
- `.pytest-postgresql-*.xml`、coverage、dist、node_modules 等运行生成物

## 四、实现要求

### 4.1 逗号表达式 callee 必须识别

必须识别以下形式：

```ts
;(0, Object.defineProperty)(item, 'onClick', { value: openHelp })
;(0, Object.assign)(item, { onClick: openHelp })
;(0, Reflect.set)(item, 'onClick', openHelp)
```

要求：

1. 对 `CallExpression` 的 callee 做表达式归一化。
2. `CommaExpression` / `SequenceExpression` 必须取最后一个表达式继续解析。
3. 多层括号与逗号组合必须递归展开。
4. 展开后命中源 mutator API 时，按源 API 参数位置解析并 fail closed。

### 4.2 条件表达式命名空间必须识别

必须识别以下形式：

```ts
const Obj = true ? Object : Object
Obj.defineProperty(item, 'onClick', { value: openHelp })

const R = condition ? Reflect : Reflect
R.set(item, 'onClick', openHelp)
```

要求：

1. 当条件表达式两个分支都可解析为同一源命名空间时，别名必须映射回源命名空间。
2. 当任一分支无法解析或两个分支不一致时，在 style-profit surface 内遇到疑似 mutator/action 注入必须 fail closed。
3. 支持 `globalThis.Object/window.Object/globalThis.Reflect/window.Reflect` 作为分支来源。

### 4.3 数组容器中转必须识别

必须识别以下形式：

```ts
const mutators = [Object.defineProperty]
mutators[0](item, 'onClick', { value: openHelp })

const mutators = [Object.assign, Reflect.set]
mutators[1](item, 'onClick', openHelp)
```

要求：

1. 同文件内简单数组字面量必须建立索引到源 mutator API 的映射。
2. 数字字面量索引必须解析为对应源 API。
3. 索引越界、非数字字面量索引、数组含 spread 或无法静态还原时，在 style-profit surface 内必须 fail closed。
4. 数组元素为已知别名时，必须继续追踪到源 API。

### 4.4 对象容器中转必须识别

必须识别以下形式：

```ts
const mutators = { dp: Object.defineProperty }
mutators.dp(item, 'onClick', { value: openHelp })

const mutators = { assign: Object.assign, set: Reflect.set }
mutators['assign'](item, { onClick: openHelp })
```

要求：

1. 同文件内简单对象字面量必须建立属性到源 mutator API 的映射。
2. 点访问和字符串字面量括号访问必须解析为对应源 API。
3. 计算属性、spread、动态属性或无法静态还原时，在 style-profit surface 内必须 fail closed。
4. 对象属性值为已知别名时，必须继续追踪到源 API。

### 4.5 不回潮要求

不得缩小 TASK-005J13/J14/J15/J16 已关闭范围，包括：

- bracket callee
- 直接函数别名
- 变量 source/descriptor
- 声明式与赋值式解构别名
- 命名空间别名
- bind/call/apply
- Reflect.apply
- 字符串/计算属性解构
- globalThis/window 直接与解构命名空间

## 五、必须新增反向测试

至少新增以下反向测试，每条都必须明确断言门禁失败：

1. `;(0, Object.defineProperty)(item, 'onClick', { value: openHelp })`
2. `;(0, Object.assign)(item, { onClick: openHelp })`
3. `;(0, Reflect.set)(item, 'onClick', openHelp)`
4. `const Obj = true ? Object : Object; Obj.defineProperty(item, 'onClick', ...)`
5. `const R = condition ? Reflect : Reflect; R.set(item, 'onClick', openHelp)`
6. `const Obj = condition ? globalThis.Object : window.Object; Obj.assign(item, { onClick: openHelp })`
7. `const mutators = [Object.defineProperty]; mutators[0](item, 'onClick', ...)`
8. `const mutators = [Object.assign, Reflect.set]; mutators[1](item, 'onClick', openHelp)`
9. `const mutators = [Object.defineProperty]; mutators[index](item, 'onClick', ...)` 必须 fail closed
10. `const mutators = [Object.defineProperty, ...extra]; mutators[0](...)` 必须 fail closed
11. `const mutators = { dp: Object.defineProperty }; mutators.dp(item, 'onClick', ...)`
12. `const mutators = { assign: Object.assign }; mutators['assign'](item, { onClick: openHelp })`
13. `const mutators = { set: Reflect.set }; mutators[key](item, 'onClick', openHelp)` 必须 fail closed
14. `const mutators = { dp: Object.defineProperty, ...extra }; mutators.dp(...)` 必须 fail closed

## 六、必须保留回归测试

不得删除、跳过、降级 TASK-005H 到 TASK-005J16 的既有测试。尤其必须保留：

- 第 131 份审计 6 个绕过样例。
- 第 132 份审计 5 个绕过样例。
- 第 133 份审计 7 个绕过样例。
- 第 134 份审计 6 个绕过样例。
- bracket callee、直接函数别名、解构别名、命名空间别名、bind/call/apply、Reflect.apply、globalThis/window 测试。
- Object.assign 变量 source / descriptor 检测测试。

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

- 第 135 份审计列出的 4 类绕过全部被拦截。
- 逗号表达式 callee 全部被拦截。
- 条件表达式命名空间全部被拦截或 fail closed。
- 数组容器中转全部被拦截或 fail closed。
- 对象容器中转全部被拦截或 fail closed。
- TASK-005J13/J14/J15/J16 已关闭的绕过不回潮。
- 非 action 字段写入不被误杀。
- 纯读取动态 key 不被误杀。
- `npm run verify` 通过。
- 后端 style-profit API 定向回归通过。
- 未修改后端、workflow、`02_源码`、TASK-006 或运行生成物。

## 九、禁止事项

- 禁止开放 `POST /api/reports/style-profit/snapshots` 前端入口。
- 禁止新增 `createStyleProfitSnapshot`、`snapshot_create`、`idempotency_key` 等创建入口调用。
- 禁止引入新的第三方 parser 依赖。
- 禁止通过扩大白名单、跳过测试、缩小扫描范围来让门禁变绿。
- 禁止把 TASK-006 解锁或写入 TASK-006 工程实现内容。

## 十、交付物

- 更新后的 `check-style-profit-contracts.mjs`
- 更新后的 `test-style-profit-contracts.mjs`
- `TASK-005J17_RuntimeMutator中转调用门禁整改证据.md`
- 验证命令摘要
- 禁改边界扫描摘要
