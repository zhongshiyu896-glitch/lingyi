# TASK-005J26 Worker 等价构造入口门禁整改工程任务单

- 任务编号：TASK-005J26
- 模块：款式利润报表 / 前端只读契约门禁
- 优先级：P0
- 任务类型：审计阻断整改 / Worker constructor sink 收口
- 前置审计：审计意见书第 144 份
- 更新时间：2026-04-15 07:44 CST
- 作者：技术架构师

## 一、任务目标

修复 `check-style-profit-contracts.mjs` 对 Worker/SharedWorker 等价构造入口的高危绕过。将 Worker 构造 sink 从单纯 `NewExpression` 检测升级为统一 constructor descriptor 解析，覆盖 `Worker.bind(...)`、Worker 构造器别名、`Reflect.construct(...)`、`Reflect.construct` 别名、参数数组中转等标准等价构造路径。

本任务只修前端只读契约门禁，不开放款式利润快照创建入口，不进入 TASK-006。

## 二、背景问题

TASK-005J25 已修复 Worker/SharedWorker 构造器别名主路径，但审计官第 144 份审计复现以下绕过：

```ts
new (Worker.bind(null))('data:text/javascript,postMessage(1)', { type: 'module' })

const BW = Worker.bind(null)
new BW('data:text/javascript,postMessage(1)', { type: 'module' })

Reflect.construct(Worker, ['data:text/javascript,postMessage(1)', { type: 'module' }])

const rc = Reflect.construct
rc(Worker, ['data:text/javascript,postMessage(1)'])
```

根因是 Worker URL 校验仍主要挂在 `new Worker(...)` / `new Alias(...)` 的 `NewExpression` 路径上，未把 `bind` 后的构造器和 `Reflect.construct` 统一归一为同一个 Worker constructor sink。

## 三、涉及文件

允许修改：

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005J26_Worker等价构造入口门禁整改证据.md`

禁止修改：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/**`
- `/Users/hh/Desktop/领意服装管理系统/.github/**`
- `/Users/hh/Desktop/领意服装管理系统/02_源码/**`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/**/TASK-006*`
- `.pytest-postgresql-*.xml`、coverage、dist、node_modules 等运行生成物

## 四、实现要求

### 4.1 建立统一 constructor descriptor

必须新增或改造现有解析逻辑，将以下调用统一归一为 constructor descriptor：

1. `new Worker(url, options)`
2. `new SharedWorker(url, options)`
3. `new Alias(url, options)`，其中 Alias 来源于 Worker/SharedWorker
4. `new (Worker.bind(null))(url, options)`
5. `new BoundWorker(url, options)`，其中 `BoundWorker = Worker.bind(null)`
6. `Reflect.construct(Worker, [url, options])`
7. `Reflect.construct(Alias, [url, options])`
8. `ReflectConstructAlias(Worker, [url, options])`

要求：

1. constructor descriptor 必须明确 `ctor_kind = worker | shared_worker | unknown`。
2. constructor descriptor 必须明确 `url_expression` 和 `options_expression`。
3. 无法解析构造器但处于 style-profit surface 且存在疑似 Worker/SharedWorker 构造链时，必须 fail closed。
4. 所有 descriptor 最终必须调用同一套 Worker URL 校验函数，不得复制出第二套判断。

### 4.2 Worker.bind 构造器必须识别

必须拦截以下形式：

```ts
new (Worker.bind(null))('data:text/javascript,postMessage(1)', { type: 'module' })
new (SharedWorker.bind(null))('data:text/javascript,postMessage(1)')

const BW = Worker.bind(null)
new BW('data:text/javascript,postMessage(1)', { type: 'module' })

const BSW = SharedWorker.bind(null)
new BSW('data:text/javascript,postMessage(1)')
```

要求：

1. `Worker.bind(...)` 返回值必须映射为 Worker 构造器。
2. `SharedWorker.bind(...)` 返回值必须映射为 SharedWorker 构造器。
3. `bind` 的 `thisArg` 不得豁免 URL 校验。
4. `Worker.bind(null, preboundUrl)` 这类预绑定 URL 必须识别并校验 `preboundUrl`。
5. 预绑定 URL 和 `new BW(...)` 运行时 URL 同时存在时，必须按实际构造参数顺序归一；无法静态判断时 fail closed。

### 4.3 Reflect.construct 必须识别

必须拦截以下形式：

```ts
Reflect.construct(Worker, ['data:text/javascript,postMessage(1)', { type: 'module' }])
Reflect.construct(SharedWorker, ['data:text/javascript,postMessage(1)'])

const rc = Reflect.construct
rc(Worker, ['data:text/javascript,postMessage(1)'])
```

要求：

1. `Reflect.construct` 直接调用必须识别。
2. `const rc = Reflect.construct` / 解构别名 / namespace alias / bracket callee / optional chain 等既有等价调用必须识别。
3. 第一个参数解析为 Worker/SharedWorker 构造器时，必须对第二个参数数组中的 URL 做同一套 Worker URL 校验。
4. 第二个参数不是静态数组、数组元素缺失、spread、变量或无法静态解析时，在 style-profit surface 内 fail closed。
5. 第三个 `newTarget` 参数不得绕过构造器来源校验。

### 4.4 Reflect.construct 参数数组中转必须识别或 fail closed

必须处理以下形式：

```ts
const args = ['data:text/javascript,postMessage(1)', { type: 'module' }]
Reflect.construct(Worker, args)

const args = [workerUrl]
Reflect.construct(Worker, args)
```

要求：

1. 简单常量数组可解析时，必须校验第一个元素。
2. 参数数组包含 spread、条件表达式、函数返回、变量 URL 或动态改写时 fail closed。
3. 参数数组别名多层中转时，如果已有 alias 体系能解析则解析；无法解析则 fail closed。

### 4.5 Worker 构造器来源必须复用 J25 alias 体系

以下构造器来源必须继续支持：

- Worker / SharedWorker 直接引用
- 直接别名
- 解构别名
- 命名空间别名
- 条件别名
- 容器中转
- dynamic member 解析
- bind 返回构造器
- Reflect.construct 第一个参数

要求：

1. 不允许只在 `NewExpression` 上补 if 分支。
2. 不允许 `new Worker(...)` 和 `Reflect.construct(Worker, ...)` 走两套 URL 校验。
3. 不允许通过放宽成功白名单让测试通过。

## 五、必须新增反向测试

至少新增以下反向测试，每条必须断言门禁失败：

1. `new (Worker.bind(null))('data:text/javascript,postMessage(1)', { type: 'module' })`
2. `new (SharedWorker.bind(null))('data:text/javascript,postMessage(1)')`
3. `const BW = Worker.bind(null); new BW('data:text/javascript,postMessage(1)', { type: 'module' })`
4. `const BSW = SharedWorker.bind(null); new BSW('data:text/javascript,postMessage(1)')`
5. `const BW = Worker.bind(null, 'data:text/javascript,postMessage(1)'); new BW({ type: 'module' })`
6. `Reflect.construct(Worker, ['data:text/javascript,postMessage(1)', { type: 'module' }])`
7. `Reflect.construct(SharedWorker, ['data:text/javascript,postMessage(1)'])`
8. `const rc = Reflect.construct; rc(Worker, ['data:text/javascript,postMessage(1)'])`
9. `const { construct } = Reflect; construct(Worker, ['data:text/javascript,postMessage(1)'])`
10. `Reflect['construct'](Worker, ['data:text/javascript,postMessage(1)'])`
11. `Reflect.construct(Worker, [workerUrl])`，其中 `workerUrl` 无法静态证明安全
12. `const args = ['data:text/javascript,postMessage(1)']; Reflect.construct(Worker, args)`
13. `const args = [workerUrl]; Reflect.construct(Worker, args)` 必须 fail closed
14. `Reflect.construct(Worker, [...args])` 必须 fail closed
15. `Reflect.construct(unknownCtor, ['data:text/javascript,postMessage(1)'])` 在 style-profit surface 内如疑似 Worker 构造链必须 fail closed
16. `Reflect.construct(Worker, ['data:text/javascript,postMessage(1)'], SafeCtor)` 不得被第三参数豁免

## 六、必须保留成功用例

至少保留或新增以下成功 fixture：

1. `new Worker(new URL('./readonly-worker.ts', import.meta.url), { type: 'module' })`
2. `const BW = Worker.bind(null); new BW(new URL('./readonly-worker.ts', import.meta.url), { type: 'module' })`
3. `Reflect.construct(Worker, [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }])`
4. `new Date()`
5. `Reflect.construct(Date, [])`
6. 非 style-profit surface 的普通安全样例不被误杀，但不得因此缩小 style-profit 扫描范围。

## 七、必须保留回归测试

不得删除、跳过、降级 TASK-005H 到 TASK-005J25 的既有测试。尤其必须保留：

- 第 131 份到第 144 份所有审计绕过样例。
- Worker/SharedWorker 构造器 alias、namespace alias、conditional alias、container alias 测试。
- URL.createObjectURL call/apply/别名测试。
- Blob URL 传播到 import/Worker/script 测试。
- dynamic import、Blob URL module loading、timer、constructor、eval/Function 全部既有测试。

## 八、验证命令

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

## 九、验收标准

- 第 144 份审计列出的 `Worker.bind` 和 `Reflect.construct` 绕过全部被拦截。
- Worker 构造 sink 已统一到 constructor descriptor 层。
- `new Worker(...)`、`new Alias(...)`、`new (Worker.bind(...))(...)`、`Reflect.construct(Worker, args)` 全部复用同一套 URL 校验。
- Reflect.construct 参数数组无法静态证明安全时 fail closed。
- 静态本地 worker 成功用例不被误杀。
- TASK-005J13-J25 已关闭的绕过不回潮。
- `npm run verify` 通过。
- 后端 style-profit API 定向回归通过。
- 未修改后端、workflow、`02_源码`、TASK-006 或运行生成物。

## 十、禁止事项

- 禁止开放 `POST /api/reports/style-profit/snapshots` 前端入口。
- 禁止新增 `createStyleProfitSnapshot`、`snapshot_create`、`idempotency_key` 等创建入口调用。
- 禁止引入新的第三方 parser 依赖。
- 禁止通过扩大白名单、跳过测试、缩小扫描范围来让门禁变绿。
- 禁止把 TASK-006 解锁或写入 TASK-006 工程实现内容。

## 十一、交付物

- 更新后的 `check-style-profit-contracts.mjs`
- 更新后的 `test-style-profit-contracts.mjs`
- `TASK-005J26_Worker等价构造入口门禁整改证据.md`
- 验证命令摘要
- 禁改边界扫描摘要
