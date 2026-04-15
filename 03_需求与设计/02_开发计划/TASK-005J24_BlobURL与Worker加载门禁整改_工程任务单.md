# TASK-005J24 Blob URL 与 Worker 加载门禁整改工程任务单

- 任务编号：TASK-005J24
- 模块：款式利润报表 / 前端只读契约门禁
- 优先级：P0
- 任务类型：审计阻断整改 / runtime code loading 收口
- 前置审计：审计意见书第 142 份
- 更新时间：2026-04-15 06:58 CST
- 作者：技术架构师

## 一、任务目标

修复 `check-style-profit-contracts.mjs` 对 Blob URL 与 Worker 代码加载入口的剩余绕过。将 `URL.createObjectURL` 纳入统一 call descriptor / alias 解析，并对 `Worker/SharedWorker` 的 `data:`、`blob:`、`http(s):`、未知 URL、变量 URL、Blob URL 传播路径全部 fail closed。

## 二、背景问题

TASK-005J23 已禁用 `import('data:...')`、变量动态 import、主路径 Blob URL module loading，但审计官在第 142 份审计中复现以下绕过：

```ts
URL.createObjectURL.call(URL, new Blob(['export default Object.assign'], { type: 'text/javascript' }))
URL.createObjectURL.apply(URL, [new Blob(['export default Reflect.set'], { type: 'text/javascript' })])

const make = URL.createObjectURL
const blobUrl = make(new Blob(['export default Object.assign'], { type: 'text/javascript' }))
script.src = blobUrl

new Worker(blobUrl)
new Worker('data:text/javascript,postMessage(1)', { type: 'module' })
```

这些路径仍可生成或加载运行时代码，必须 fail closed。

## 三、涉及文件

允许修改：

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005J24_BlobURL与Worker加载门禁整改证据.md`

禁止修改：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/**`
- `/Users/hh/Desktop/领意服装管理系统/.github/**`
- `/Users/hh/Desktop/领意服装管理系统/02_源码/**`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/**/TASK-006*`
- `.pytest-postgresql-*.xml`、coverage、dist、node_modules 等运行生成物

## 四、实现要求

### 4.1 URL.createObjectURL call/apply 必须识别

必须识别并拦截以下形式：

```ts
URL.createObjectURL.call(URL, new Blob(['export default Object.assign'], { type: 'text/javascript' }))
URL.createObjectURL.apply(URL, [new Blob(['export default Reflect.set'], { type: 'text/javascript' })])
window.URL.createObjectURL.call(window.URL, new Blob(['console.log(1)'], { type: 'text/javascript' }))
globalThis.URL.createObjectURL.apply(globalThis.URL, [new Blob(['console.log(1)'], { type: 'application/javascript' })])
```

要求：

1. `.call()` 第二参数是 createObjectURL 的真实入参。
2. `.apply()` 第二参数数组第一个元素是 createObjectURL 的真实入参。
3. apply 参数不是数组字面量、含 spread、或无法静态还原时，在 style-profit surface 内 fail closed。
4. 支持 `URL.createObjectURL['call'](...)`、`URL.createObjectURL['apply'](...)`。
5. `window.URL`、`globalThis.URL` 与 `URL` 等价。

### 4.2 URL.createObjectURL 别名必须识别

必须识别并拦截以下形式：

```ts
const make = URL.createObjectURL
const blobUrl = make(new Blob(['export default Object.assign'], { type: 'text/javascript' }))

const { createObjectURL } = URL
const blobUrl = createObjectURL(new Blob(['export default Reflect.set'], { type: 'text/javascript' }))

const U = URL
const blobUrl = U.createObjectURL(new Blob(['console.log(1)'], { type: 'text/javascript' }))
```

要求：

1. 直接别名、解构别名、赋值式解构别名、命名空间别名必须识别。
2. 别名 `.call/.apply` 必须识别。
3. `globalThis.URL/window.URL` 解构或命名空间别名必须识别。
4. 无法确认别名安全时，在 style-profit surface 内 fail closed。

### 4.3 Blob URL 传播必须 fail closed

必须识别以下传播路径：

```ts
const blobUrl = URL.createObjectURL(new Blob(['export default Object.assign'], { type: 'text/javascript' }))
import(blobUrl)
new Worker(blobUrl)
script.src = blobUrl
```

要求：

1. `URL.createObjectURL(new Blob(...))` 结果进入变量后，该变量必须标记为 code-loading URL。
2. 标记变量进入 `import()`、`new Worker()`、`new SharedWorker()`、`script.src` 时必须 fail closed。
3. 即使尚未进入 sink，只要 Blob 类型为脚本 MIME，在 style-profit surface 内也建议 fail closed；若保留普通下载 Blob 成功用例，必须证明不进入代码加载 sink。
4. Blob MIME 为 `text/javascript/application/javascript/text/ecmascript/module` 等脚本类型必须 fail closed。
5. Blob MIME 无法静态确认安全时，fail closed。

### 4.4 Worker / SharedWorker 高危 URL 必须 fail closed

必须识别并拦截以下形式：

```ts
new Worker('data:text/javascript,postMessage(1)', { type: 'module' })
new Worker('blob:https://example.local/worker')
new Worker('https://cdn.example.com/worker.js')
new SharedWorker('data:text/javascript,postMessage(1)')
new Worker(workerUrl)
```

要求：

1. `new Worker()` / `new SharedWorker()` 第一个参数为 `data/blob/http/https/javascript` 协议时 fail closed。
2. 第一个参数为变量、模板表达式、函数返回、条件表达式或无法静态证明本地安全路径时 fail closed。
3. 只允许静态本地 worker 路径，例如 `new Worker(new URL('./readonly-worker.ts', import.meta.url), { type: 'module' })`，且该 worker 文件必须在项目内并接受既有扫描。
4. Worker options `{ type: 'module' }` 不得豁免 data/blob URL。

### 4.5 Script src 高危 URL 必须 fail closed

必须识别并拦截以下形式：

```ts
script.src = URL.createObjectURL(new Blob(['console.log(1)'], { type: 'text/javascript' }))
script.src = blobUrl
script.setAttribute('src', blobUrl)
script.src = 'data:text/javascript,console.log(1)'
script.src = 'https://cdn.example.com/a.js'
```

要求：

1. `script.src` 直接赋值高危协议或 Blob URL 标记变量时 fail closed。
2. `script.setAttribute('src', ...)` 高危协议或 Blob URL 标记变量时 fail closed。
3. 无法静态证明安全的 script src，在 style-profit surface 内 fail closed。

## 五、必须新增反向测试

至少新增以下反向测试，每条都必须明确断言门禁失败：

1. `URL.createObjectURL.call(URL, new Blob(['export default Object.assign'], { type: 'text/javascript' }))`
2. `URL.createObjectURL.apply(URL, [new Blob(['export default Reflect.set'], { type: 'text/javascript' })])`
3. `window.URL.createObjectURL.call(window.URL, new Blob(['console.log(1)'], { type: 'text/javascript' }))`
4. `globalThis.URL.createObjectURL.apply(globalThis.URL, [new Blob(['console.log(1)'], { type: 'application/javascript' })])`
5. `const make = URL.createObjectURL; const blobUrl = make(new Blob(['export default Object.assign'], { type: 'text/javascript' }))`
6. `const { createObjectURL } = URL; createObjectURL(new Blob(['export default Reflect.set'], { type: 'text/javascript' }))`
7. `const U = URL; U.createObjectURL(new Blob(['console.log(1)'], { type: 'text/javascript' }))`
8. `const blobUrl = URL.createObjectURL(new Blob(['export default Object.assign'], { type: 'text/javascript' })); import(blobUrl)`
9. `const blobUrl = URL.createObjectURL(new Blob(['postMessage(1)'], { type: 'text/javascript' })); new Worker(blobUrl)`
10. `const blobUrl = URL.createObjectURL(new Blob(['console.log(1)'], { type: 'text/javascript' })); script.src = blobUrl`
11. `new Worker('data:text/javascript,postMessage(1)', { type: 'module' })`
12. `new Worker('blob:https://example.local/worker')`
13. `new Worker('https://cdn.example.com/worker.js')`
14. `new SharedWorker('data:text/javascript,postMessage(1)')`
15. `new Worker(workerUrl)` 中 `workerUrl` 无法静态证明安全时 fail closed
16. `script.src = 'data:text/javascript,console.log(1)'`
17. `script.src = 'https://cdn.example.com/a.js'`
18. `script.setAttribute('src', blobUrl)` 中 `blobUrl` 为 Blob URL 标记变量

## 六、必须保留成功用例

至少新增或保留以下成功 fixture：

1. 静态本地 worker：`new Worker(new URL('./readonly-worker.ts', import.meta.url), { type: 'module' })`
2. 普通静态本地资源：`const asset = '/assets/logo.png'`
3. 普通 Blob 用于下载文本且不进入 import/Worker/script；如无法证明安全，则在 style-profit surface 内禁止 Blob 更稳。
4. 静态本地懒加载 import：`import('@/views/style_profit/StyleProfitList.vue')`

## 七、必须保留回归测试

不得删除、跳过、降级 TASK-005H 到 TASK-005J23 的既有测试。尤其必须保留：

- 第 131 份到第 141 份所有审计绕过样例。
- data/blob/http/javascript 动态 import 测试。
- 变量动态 import、vite-ignore import 测试。
- Blob URL module loading 测试。
- Worker/script 直接 Blob URL 代码加载测试。
- timer、constructor、eval/Function、runtime mutator 源引用禁用全部既有测试。

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

- 第 142 份审计列出的 Blob URL 与 Worker 绕过全部被拦截。
- `URL.createObjectURL.call/apply` 全部 fail closed。
- `URL.createObjectURL` 别名、解构别名、命名空间别名全部 fail closed。
- Blob URL 变量进入 import/Worker/script 时 fail closed。
- Worker/SharedWorker 的 data/blob/http(s)/未知 URL 全部 fail closed。
- script.src / setAttribute('src') 高危 URL 全部 fail closed。
- 静态本地 worker 成功用例不被误杀。
- TASK-005J13-J23 已关闭的绕过不回潮。
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
- `TASK-005J24_BlobURL与Worker加载门禁整改证据.md`
- 验证命令摘要
- 禁改边界扫描摘要
