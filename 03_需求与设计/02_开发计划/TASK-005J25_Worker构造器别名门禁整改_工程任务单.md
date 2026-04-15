# TASK-005J25 Worker 构造器别名门禁整改工程任务单

- 任务编号：TASK-005J25
- 模块：款式利润报表 / 前端只读契约门禁
- 优先级：P0
- 任务类型：审计阻断整改 / Worker 构造器别名收口
- 前置审计：审计意见书第 143 份
- 更新时间：2026-04-15 07:22 CST
- 作者：技术架构师

## 一、任务目标

修复 `check-style-profit-contracts.mjs` 对 `Worker/SharedWorker` 构造器别名的高危绕过。将 Worker 构造器识别接入已有 alias / namespace alias / conditional alias / dynamic member 解析体系，确保通过直接构造器、别名、命名空间别名、解构别名、条件别名、globalThis/window 中转等方式创建 Worker 时，都执行同一套 URL 安全校验。

## 二、背景问题

TASK-005J24 已收口 `URL.createObjectURL.call/apply/别名`、Blob URL 传播、Worker/SharedWorker 直接高危 URL，但审计官在第 143 份审计中复现 Worker 构造器别名仍可绕过：

```ts
const W = Worker
new W('data:text/javascript,postMessage(1)', { type: 'module' })

const SW = SharedWorker
new SW('data:text/javascript,postMessage(1)')

const G = globalThis
new G.Worker('data:text/javascript,postMessage(1)')
```

当前 Worker 构造器识别逻辑和 mutator/codegen/blob URL 的 alias 解析体系仍是两套，导致直接构造器能拦截，但别名构造器漏判。必须统一。

## 三、涉及文件

允许修改：

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005J25_Worker构造器别名门禁整改证据.md`

禁止修改：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/**`
- `/Users/hh/Desktop/领意服装管理系统/.github/**`
- `/Users/hh/Desktop/领意服装管理系统/02_源码/**`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/**/TASK-006*`
- `.pytest-postgresql-*.xml`、coverage、dist、node_modules 等运行生成物

## 四、实现要求

### 4.1 Worker 直接别名必须识别

必须识别并拦截以下形式：

```ts
const W = Worker
new W('data:text/javascript,postMessage(1)', { type: 'module' })

const SW = SharedWorker
new SW('data:text/javascript,postMessage(1)')
```

要求：

1. `const/let/var W = Worker` 必须映射为 Worker 构造器。
2. `const/let/var SW = SharedWorker` 必须映射为 SharedWorker 构造器。
3. `new W(...)` / `new SW(...)` 必须复用 Worker URL 校验逻辑。
4. 别名来源不明或被重写时，在 style-profit surface 内遇到疑似 Worker 构造必须 fail closed。

### 4.2 Worker 命名空间别名必须识别

必须识别并拦截以下形式：

```ts
const G = globalThis
new G.Worker('data:text/javascript,postMessage(1)')

const Win = window
new Win.SharedWorker('data:text/javascript,postMessage(1)')
```

要求：

1. `const G = globalThis` 必须映射为 globalThis 命名空间。
2. `const Win = window` 必须映射为 window 命名空间。
3. `new G.Worker(...)`、`new Win.SharedWorker(...)` 必须复用 Worker URL 校验逻辑。
4. 支持 `G['Worker']`、`Win['SharedWorker']` 和字符串拼接动态成员名。

### 4.3 Worker 解构别名必须识别

必须识别并拦截以下形式：

```ts
const { Worker: W } = globalThis
new W('data:text/javascript,postMessage(1)')

const { SharedWorker: SW } = window
new SW('data:text/javascript,postMessage(1)')
```

要求：

1. globalThis/window 解构出的 Worker/SharedWorker 必须映射为对应构造器。
2. 解构重命名、赋值式解构必须识别。
3. 字符串属性解构、计算属性解构按既有动态成员名规则处理。

### 4.4 Worker 条件别名必须识别或 fail closed

必须识别以下形式：

```ts
const W = condition ? Worker : Worker
new W('data:text/javascript,postMessage(1)')

const W = condition ? globalThis.Worker : window.Worker
new W('data:text/javascript,postMessage(1)')
```

要求：

1. 条件表达式两分支都解析为 Worker 构造器时，别名映射为 Worker。
2. 条件表达式两分支都解析为 SharedWorker 构造器时，别名映射为 SharedWorker。
3. 任一分支无法解析或分支不一致时，在 style-profit surface 内遇到 `new W(...)` 必须 fail closed。

### 4.5 Worker 容器中转必须识别或 fail closed

必须识别以下形式：

```ts
const constructors = [Worker]
new constructors[0]('data:text/javascript,postMessage(1)')

const constructors = { W: Worker }
new constructors.W('data:text/javascript,postMessage(1)')
```

要求：

1. 简单数组/对象容器中的 Worker/SharedWorker 构造器必须追踪。
2. 动态索引、spread、不可还原容器在 style-profit surface 内 must fail closed。
3. 容器值为已知别名时，必须继续追踪到 Worker 构造器。

### 4.6 统一 Worker URL 校验

无论构造器来自以下哪种来源，都必须调用同一套 URL 校验：

- `Worker`
- `SharedWorker`
- `window.Worker`
- `globalThis.Worker`
- 直接别名
- 解构别名
- 命名空间别名
- 条件别名
- 容器中转
- 动态成员名

URL 校验规则沿用 TASK-005J24：

1. `data/blob/http/https/javascript` 协议 fail closed。
2. 变量、模板表达式、函数返回、条件表达式或无法静态证明本地安全路径 fail closed。
3. 只允许静态本地 worker 路径：`new Worker(new URL('./readonly-worker.ts', import.meta.url), { type: 'module' })`。
4. Worker options `{ type: 'module' }` 不得豁免高危 URL。

## 五、必须新增反向测试

至少新增以下反向测试，每条都必须明确断言门禁失败：

1. `const W = Worker; new W('data:text/javascript,postMessage(1)', { type: 'module' })`
2. `const SW = SharedWorker; new SW('data:text/javascript,postMessage(1)')`
3. `const G = globalThis; new G.Worker('data:text/javascript,postMessage(1)')`
4. `const Win = window; new Win.SharedWorker('data:text/javascript,postMessage(1)')`
5. `const G = globalThis; new G['Worker']('data:text/javascript,postMessage(1)')`
6. `const { Worker: W } = globalThis; new W('data:text/javascript,postMessage(1)')`
7. `const { SharedWorker: SW } = window; new SW('data:text/javascript,postMessage(1)')`
8. `let W; ({ Worker: W } = globalThis); new W('data:text/javascript,postMessage(1)')`
9. `const W = condition ? Worker : Worker; new W('data:text/javascript,postMessage(1)')`
10. `const W = condition ? globalThis.Worker : window.Worker; new W('data:text/javascript,postMessage(1)')`
11. `const W = condition ? Worker : unknownCtor; new W('data:text/javascript,postMessage(1)')` 必须 fail closed
12. `const constructors = [Worker]; new constructors[0]('data:text/javascript,postMessage(1)')`
13. `const constructors = { W: Worker }; new constructors.W('data:text/javascript,postMessage(1)')`
14. `const constructors = [Worker, ...extra]; new constructors[0]('data:text/javascript,postMessage(1)')` 必须 fail closed
15. `const constructors = { W: Worker, ...extra }; new constructors.W('data:text/javascript,postMessage(1)')` 必须 fail closed
16. `const W = Worker; new W(workerUrl)` 中 `workerUrl` 无法静态证明安全时 fail closed

## 六、必须保留成功用例

至少新增或保留以下成功 fixture：

1. `new Worker(new URL('./readonly-worker.ts', import.meta.url), { type: 'module' })`
2. `const W = Worker; new W(new URL('./readonly-worker.ts', import.meta.url), { type: 'module' })`
3. `const { Worker: W } = globalThis; new W(new URL('./readonly-worker.ts', import.meta.url), { type: 'module' })`
4. 普通非 Worker 构造器：`new Date()`
5. 普通字段名：`record['Worker_name']`

## 七、必须保留回归测试

不得删除、跳过、降级 TASK-005H 到 TASK-005J24 的既有测试。尤其必须保留：

- 第 131 份到第 142 份所有审计绕过样例。
- URL.createObjectURL call/apply/别名测试。
- Blob URL 传播到 import/Worker/script 测试。
- Worker/SharedWorker data/blob/http(s)/未知 URL 直接构造测试。
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

- 第 143 份审计列出的 Worker 构造器别名绕过全部被拦截。
- Worker/SharedWorker 直接别名全部接入 URL 校验。
- globalThis/window 命名空间别名全部接入 URL 校验。
- 解构别名、条件别名、容器中转全部接入 URL 校验或 fail closed。
- Worker URL 校验逻辑只有一套，不再出现直接构造器和别名构造器分叉。
- 静态本地 worker 成功用例不被误杀。
- TASK-005J13-J24 已关闭的绕过不回潮。
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
- `TASK-005J25_Worker构造器别名门禁整改证据.md`
- 验证命令摘要
- 禁改边界扫描摘要
