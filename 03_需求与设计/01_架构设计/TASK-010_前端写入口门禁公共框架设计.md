# TASK-010 前端写入口门禁公共框架设计

- 模块：前端写入口门禁公共框架
- 版本：V1.0（设计冻结）
- 更新时间：2026-04-16
- 前置：TASK-009D 审计通过（HEAD `a5e64146bfd7954d5daaa309dbf2e4769a5db237`）
- 适用范围：Sprint 2 所有前端模块（含 TASK-011、TASK-012）

## 一、目标与边界

### 1.1 目标
将 TASK-005（style-profit）与 TASK-006（factory-statement）已验证的前端门禁能力抽象为可复用公共框架，统一：
1. 模块门禁配置。
2. AST 主判定与 fail-closed 语义。
3. fixture 正反用例体系。
4. `npm run verify` 的门禁接入策略。

### 1.2 边界
1. 本文档只冻结规范，不写业务代码。
2. 不在 TASK-010A 修改 `06_前端/**`、`07_后端/**`、`.github/**`、`02_源码/**`。
3. 具体工程实现进入 TASK-010B。

---

## 二、现状梳理

### 2.1 style-profit 门禁现状
现有脚本：
- `scripts/check-style-profit-contracts.mjs`（约 6446 行）
- `scripts/test-style-profit-contracts.mjs`（约 5969 行）

已具备能力：
1. TypeScript AST 深度分析（数组污染、alias、函数副作用、迭代回调、构造器归一）。
2. 写入口与动态行为高危禁线（computed key、runtime mutator、eval/Function、timer 字符串、dynamic import、Worker/SharedWorker）。
3. `new Worker(...args)` / `Reflect.construct(...)` 等价路径统一判定。
4. 反向 fixture 覆盖密度高：`test-style-profit-contracts.mjs` 已沉淀 474 条失败场景 + 1 条成功场景（总计 475 场景）。

### 2.2 factory-statement 门禁现状
现有脚本：
- `scripts/check-factory-statement-contracts.mjs`（约 386 行）
- `scripts/test-factory-statement-contracts.mjs`（约 586 行）

已具备能力：
1. API/页面/路由/store/export 工具多目录扫描。
2. internal API、run-once、ERPNext `/api/resource`、裸 `fetch`、敏感词硬编码、CSV 公式注入等禁线。
3. 权限 denylist（含 `factory_statement:payable_draft_worker`）和前端 fail-closed 片段校验。
4. fixture 反向测试覆盖（25 条负向 + 1 条正向）。

### 2.3 当前 verify 接入现状
`package.json` 中 `verify` 当前串联：
1. `check:production-contracts`
2. `test:production-contracts`
3. `check:style-profit-contracts`
4. `test:style-profit-contracts`
5. `check:factory-statement-contracts`
6. `test:factory-statement-contracts`
7. `typecheck`
8. `build`

结论：已形成“模块门禁 + 项目 verify”路径，但脚本实现风格不一致，可复用性不足。

### 2.4 已暴露绕过类型汇总（Sprint 1 审计历史）
1. 语义绕过：中文写语义、只读文案误杀/漏杀。
2. 结构绕过：对象祖先链、computed key、命名空间/别名。
3. 运行时绕过：`Object.defineProperty`、`Object.assign`、`Reflect.set`。
4. 调用等价绕过：`call/apply/bind`、`call.call`、`Reflect.apply`。
5. 代码生成绕过：`eval`、`Function`、constructor 链、字符串 timer。
6. 模块加载绕过：dynamic import、Blob URL、Worker URL 传播。
7. 参数传播绕过：spread 数组、解构 alias、循环/回调参数污染。
8. 导出安全绕过：CSV 公式注入。

### 2.5 当前脚本不可复用点
1. style-profit 偏“深 AST 语义引擎”，factory-statement 偏“规则扫描 + 结构断言”，抽象层级不一致。
2. 规则配置、命中输出、fixture 命名未统一。
3. 新模块复制成本高，审计难以统一横向比较。

---

## 三、公共框架规范（冻结）

### 3.1 统一框架分层
1. `contract-config`：模块配置（声明式）。
2. `contract-engine`：扫描与判定引擎（AST 优先）。
3. `contract-reporter`：统一失败报告。
4. `contract-fixture-runner`：正反 fixture 执行器。
5. `module-wrapper`：兼容旧命令入口（style-profit、factory-statement）。

### 3.2 统一模块配置格式
每个模块必须声明如下最小字段：

```ts
interface FrontendContractModuleConfig {
  module: string
  surface: {
    moduleKey: string
    entryGlobs: string[]
    scanScopes: Array<'api' | 'views' | 'router' | 'stores' | 'components' | 'utils'>
  }
  allowedApis: string[]
  forbiddenApis: string[]
  forbiddenActions: string[]
  allowedReadOnlyActions: string[]
  allowedHttpMethods: Array<'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'>
  forbiddenKeywords: string[]
  forbiddenRuntimePatterns: string[]
  fixture: {
    positive: string[]
    negative: string[]
  }
}
```

约束：
1. 只读模块的 `allowedHttpMethods` 只能包含 `GET`。
2. 写模块必须显式声明允许动作；未声明即禁止。
3. 未配置项默认 fail closed。

### 3.3 统一扫描范围
默认扫描以下目录（模块可收窄，不可扩大到排除核心目录）：
1. `src/api/**`
2. `src/views/**`
3. `src/router/**`
4. `src/stores/**`
5. `src/components/**`
6. `src/utils/**`
7. `src/App.vue`

### 3.4 规则编号规范
统一编号格式：`FWG-<域>-<三位序号>`。
- `FWG-API-*`：API 与 HTTP 语义。
- `FWG-AST-*`：AST 行为语义。
- `FWG-RUN-*`：运行时代码执行与动态注入。
- `FWG-INT-*`：internal/worker/run-once 禁线。
- `FWG-EXP-*`：导出与数据安全。
- `FWG-PER-*`：权限动作与 UI 暴露。

### 3.5 AST 优先策略
1. AST 是主判定器；正则只可用于补充快速筛查。
2. AST 无法静态证明安全时，默认 fail closed。
3. 禁止继续堆叠“仅正则补丁”作为主策略。

### 3.6 统一 fail-closed 与白名单策略
1. 默认禁止，显式白名单放行。
2. 白名单必须最小化（按模块、按动作、按路径）。
3. “未知行为 / 无法解析行为 / 动态构造行为”一律拦截。

### 3.7 统一报告格式
每条命中至少输出：
1. 规则编号。
2. 文件路径。
3. 违规代码片段摘要（脱敏）。
4. 违规原因。
5. 修复建议。

输出示例：

```text
[FWG-INT-003] src/views/xxx.vue
原因：检测到 internal run-once 路径暴露
建议：移除 internal 路由调用，改为业务 API
```

---

## 四、统一规则清单（冻结）

### 4.1 只读模块规则
1. 禁止 `POST/PUT/PATCH/DELETE`。
2. 禁止 create/update/delete/confirm/cancel/generate/recalculate/sync/submit 等写语义动作。
3. 禁止恢复写入口的按钮、菜单、action 配置、运行时注入。

### 4.2 写入口模块规则
1. 只允许配置声明中放行的写动作。
2. 只允许统一 API client（`request()`）出网。
3. 未授权动作/路径默认阻断。

### 4.3 Internal API 禁入规则
1. 禁止前端调用 `/internal/*`。
2. 禁止暴露 `run-once`、`diagnostic`、worker 触发路径到普通页面。
3. internal worker 动作必须在权限 store 明确 denylist/清零。

### 4.4 ERPNext 直连禁入规则
1. 禁止前端直连 `/api/resource`。
2. 禁止前端出现提交 PI / Payment Entry / GL Entry 的调用与文案。

### 4.5 动态执行与注入禁入规则
1. 禁止 `eval`、`Function`、constructor 链执行。
2. 禁止字符串 `setTimeout/setInterval`。
3. 禁止动态 action key 与 runtime mutator 注入（`defineProperty/assign/Reflect.set`）。

### 4.6 Worker / Dynamic Import 禁入规则
1. 禁止 data/blob/http(s)/unknown Worker URL。
2. 禁止动态 import 高危 URL 与不可静态证明安全的导入。
3. 对别名、解构、bind/call/apply、Reflect 等价调用按同一模型处理。

### 4.7 导出与公式注入规则
1. 导出工具不得出网（禁止 `fetch/axios`）。
2. 金额字段不得 `Number/parseFloat` 重算。
3. CSV 单元格必须防护公式注入前缀（`= + - @ \t \r \n`）。

---

## 五、Fixture 规范（冻结）

### 5.1 命名规范
1. 正向：`positive_<rule_or_feature>_<case>.ts/vue`。
2. 反向：`negative_<rule_or_bypass>_<case>.ts/vue`。

### 5.2 覆盖要求
1. 每条规则至少 1 个 positive + 1 个 negative。
2. 每个审计发现绕过必须固化为 negative fixture。
3. negative fixture 必须断言“失败且命中目标规则编号/关键词”。

### 5.3 反向用例最小矩阵
1. direct 调用。
2. alias 调用。
3. destructure 场景。
4. call/apply/bind/Reflect 等价路径。
5. computed key。
6. runtime mutation。
7. 跨行与嵌套对象。

---

## 六、模块接入规范（TASK-011 / TASK-012）

### 6.1 TASK-011 销售/库存只读集成
1. 先落地模块 contract config 与 fixture。
2. 审计通过前，不允许进入页面开发。
3. 默认只读：仅允许 `GET` 与 read/export（若 export 已审计放行）。

### 6.2 TASK-012 质量管理基线
1. 先落地模块 contract config 与 fixture。
2. 写动作（create/update/confirm/cancel）必须显式声明并逐条负向验证。
3. internal worker、diagnostic、run-once 一律默认禁入。

### 6.3 通用接入流程
1. 新模块先建 config + fixture。
2. 再接入 `check:<module>-contracts` 与 `test:<module>-contracts`。
3. 最后并入 `npm run verify`。

---

## 七、迁移计划（style-profit / factory-statement）

### 7.1 迁移原则
1. 保留旧脚本命令入口，避免 CI 与本地命令中断。
2. 旧脚本内部改为调用公共框架引擎（wrapper 模式）。
3. 迁移期间行为必须等价，不得降低已关闭绕过防护。

### 7.2 分阶段路径
1. 阶段 1：抽取公共 config schema 与 reporter。
2. 阶段 2：style-profit 迁移为 wrapper（优先保留 AST 深判定能力）。
3. 阶段 3：factory-statement 迁移为 wrapper（接入统一规则编号与报告）。
4. 阶段 4：新模块（TASK-011/012）按公共 config 直接接入。

### 7.3 兼容约束
1. `npm run check/test:style-profit-contracts`、`npm run check/test:factory-statement-contracts` 命令名不变。
2. 已有 475（style-profit）与 26（factory-statement）场景不得回退。

---

## 八、TASK-010B 实现边界（冻结）

### 8.1 允许
1. 新建公共 contract engine（AST 主引擎 + 规则执行器 + reporter）。
2. 将 style-profit/factory-statement 旧脚本改为 wrapper。
3. 新增公共 fixture 基础设施和模块配置模板。

### 8.2 禁止
1. 禁止修改业务页面逻辑（非门禁脚本/配置/fixture）。
2. 禁止提前进入 TASK-011/TASK-012 业务功能开发。
3. 禁止通过扩大白名单、缩小扫描范围、跳过测试让门禁“假绿”。

---

## 九、审计前置检查清单

审计官在 TASK-010A 文档审计必须确认：
1. 规范明确 AST 优先、正则补充、默认 fail closed。
2. 配置结构覆盖 `module/surface/allowedApis/forbiddenApis/forbiddenActions/allowedReadOnlyActions`。
3. 规则清单覆盖 internal/ERPNext/dynamic execution/Worker/CSV 安全。
4. fixture 规范要求正反成对，并固化审计绕过。
5. style-profit 与 factory-statement 迁移路径明确且可执行。
6. TASK-011/TASK-012 被明确设为“先接门禁再开发页面”。
7. TASK-010B 边界清晰、无跨任务实现。

---

## 十、结论

TASK-010A 设计冻结结论：
1. 已冻结前端写入口门禁公共框架的配置、规则、扫描、报告、fixture 与迁移路径。
2. 已明确 TASK-011/TASK-012 的门禁前置依赖。
3. 可作为 TASK-010B 工程实现的唯一前置文档。
