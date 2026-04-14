# TASK-005J24 Blob URL 与 Worker 加载门禁整改证据

## 1. 执行信息
- 任务：TASK-005J24
- 执行目录：`/Users/hh/Desktop/领意服装管理系统`
- 前置基线：`6dc7a7a`
- 本次提交：495632140be97c43d766a0d3023b8e4ae2f8b7f3

## 2. 修改文件
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005J24_BlobURL与Worker加载门禁整改证据.md`

## 3. 实现摘要
1. 将 `URL.createObjectURL` 纳入统一 runtime call descriptor 解析链路：
   - 支持 direct / `.call` / `.apply` / `Reflect.apply`。
   - 支持 `URL`、`window.URL`、`globalThis.URL`、别名、解构别名、赋值式解构别名。
2. 增强 Blob URL 传播追踪：
   - 识别 `const blobUrl = createObjectURL(...)` 及运行时赋值来源。
   - Blob URL 标记变量进入 `import(...)`、`new Worker(...)`、`new SharedWorker(...)`、`script.src`、`script.setAttribute('src', ...)` 时 fail closed。
3. 扩展 Worker/SharedWorker 加载判定：
   - `data:` / `blob:` / `javascript:` / `http:` / `https:` 协议 fail closed。
   - 变量、函数返回、无法静态证明安全来源 fail closed。
   - 保留静态本地 worker 成功路径：`new Worker(new URL('./readonly-worker.ts', import.meta.url), { type: 'module' })`。
4. 扩展 script URL 写入判定：
   - `script.src = ...` 与 `script.setAttribute('src', ...)` 统一检查。
   - 高危协议与 Blob URL 标记变量 fail closed。
5. 回归策略：
   - 未删除/降级 TASK-005H ~ TASK-005J23 既有门禁测试。

## 4. 新增/增强反向测试覆盖（J24）
已新增并通过以下场景：
- `URL.createObjectURL.call/apply`（含 `window.URL`、`globalThis.URL`）
- `createObjectURL` 直接别名、解构别名、命名空间别名
- Blob URL 变量进入 `import/Worker/script.src/script.setAttribute('src', ...)`
- `new Worker('data:...')`、`new Worker('blob:...')`、`new Worker('https:...')`
- `new SharedWorker('data:...')`
- `new Worker(workerUrl)` 无法静态证明安全时 fail closed

## 5. 成功用例回归
- 合法最小 fixture 通过。
- 静态本地 worker 用例通过：
  - `new Worker(new URL('./readonly-worker.ts', import.meta.url), { type: 'module' })`
- 既有只读文案、只读动作、静态本地 dynamic import 成功用例均未回退。

## 6. 验证命令与结果
### 前端
1. `npm run check:style-profit-contracts`
   - 结果：通过（`Style-profit contract check passed.`，`Scanned files: 24`）
2. `npm run test:style-profit-contracts`
   - 结果：通过（`All style-profit contract fixture tests passed. scenarios=291`）
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
- 结果：无输出（本次未触碰禁改目录/任务）。

## 8. 结论
- TASK-005J24 要求的 Blob URL 与 Worker 加载绕过已收口：`URL.createObjectURL` 等价调用、Blob URL 传播、Worker/SharedWorker 高危 URL、`script.src/setAttribute('src')` 均已纳入 fail closed。
- 前端/后端验证通过。
- 未开放利润快照创建入口，未进入 TASK-006。
