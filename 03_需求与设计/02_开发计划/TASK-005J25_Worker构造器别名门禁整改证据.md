# TASK-005J25 Worker 构造器别名门禁整改证据

## 1. 执行信息
- 任务：TASK-005J25
- 执行目录：`/Users/hh/Desktop/领意服装管理系统`
- 前置基线：`5ad0533`
- 本次提交：c8bfd19721701aaa535ad991d22bcd2667186f40

## 2. 修改文件
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005J25_Worker构造器别名门禁整改证据.md`

## 3. 实现摘要
1. Worker 构造器识别接入 alias 解析体系：
   - 新增 Worker 构造器分类与解析：`Worker` / `SharedWorker`。
   - 支持直接别名、解构别名、赋值式解构别名、命名空间别名、条件别名。
2. Worker 构造器识别接入容器中转解析：
   - 支持简单数组/对象容器中转追踪。
   - 容器动态索引、spread、不可静态还原场景 fail closed。
3. Worker 检测切换到统一构造器 descriptor：
   - `new ...` 不再只识别直接 `Worker/SharedWorker`。
   - 对 unresolved 构造器别名输出 fail closed 结果。
4. Worker URL 安全校验仍保持单一路径：
   - `data/blob/http/https/javascript` 协议 fail closed。
   - 变量/函数返回/无法静态证明安全来源 fail closed。
   - 保留静态本地 worker 成功路径：`new Worker(new URL('./readonly-worker.ts', import.meta.url), { type: 'module' })`。

## 4. 新增/增强反向测试覆盖（J25）
已新增并通过：
- `const W = Worker; new W('data:...')`
- `const SW = SharedWorker; new SW('data:...')`
- `const G = globalThis; new G.Worker('data:...')`
- `const Win = window; new Win.SharedWorker('data:...')`
- `new G['Worker']('data:...')` 与 `new G['Work' + 'er']('data:...')`
- `const { Worker: W } = globalThis; new W('data:...')`
- `const { SharedWorker: SW } = window; new SW('data:...')`
- `let W; ({ Worker: W } = globalThis); new W('data:...')`
- 条件别名（同源/混合源/不一致分支）
- 数组/对象容器中转及 spread 变体
- 别名构造器 + `workerUrl` 无法静态证明安全来源 fail closed

## 5. 成功用例回归
- 合法最小 fixture 通过。
- 静态本地 worker 直接构造通过。
- `const W = Worker; new W(new URL('./readonly-worker.ts', import.meta.url), { type: 'module' })` 通过。
- `const { Worker: DW } = globalThis; new DW(new URL('./readonly-worker.ts', import.meta.url), { type: 'module' })` 通过。
- `record['Worker_name']` 等只读字段访问未误杀。

## 6. 验证命令与结果
### 前端
1. `npm run check:style-profit-contracts`
   - 结果：通过（`Style-profit contract check passed.`）
2. `npm run test:style-profit-contracts`
   - 结果：通过（`All style-profit contract fixture tests passed. scenarios=308`）
3. `npm run verify`
   - 结果：通过（production/style-profit 合约、typecheck、build 全通过）
4. `npm audit --audit-level=high`
   - 结果：通过（`found 0 vulnerabilities`）

### 后端只读回归
1. `.venv/bin/python -m pytest -q tests/test_style_profit_api.py`
   - 结果：通过（`8 passed, 1 warning`）
2. `.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)`
   - 结果：通过

## 7. 禁改范围扫描
执行：`git diff --name-only -- 07_后端 .github 02_源码 '03_需求与设计/**/TASK-006*'`
- 结果：无输出（未触碰禁改目录/任务）。

## 8. 结论
- TASK-005J25 要求的 Worker 构造器别名绕过已收口：直接别名、解构别名、命名空间别名、条件别名、容器中转均已接入统一 Worker URL 校验或 fail closed。
- 已验证 TASK-005J13 ~ TASK-005J24 既有门禁未回退。
- 未开放创建快照入口，未进入 TASK-006。
