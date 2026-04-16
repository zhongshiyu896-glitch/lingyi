# TASK-010B1 前端门禁公共框架 Fail-Closed 配置整改 交付证据

- 任务编号：TASK-010B1
- 执行日期：2026-04-16
- 结论：待审计

## 1. 修复内容

1. 未知 `scanScopes` 已 fail closed。
- 在 `validateModuleContractConfig()` 增加 `surface.scanScopes` 白名单校验。
- 仅允许：`api/views/router/stores/components/utils`。
- 出现未知 scope（如 `apix`）直接失败，并在错误信息中回显未知 scope 名称。

2. `scannedFiles=0` 已 fail closed。
- 在 `runFrontendContractEngine()` 增加扫描结果门禁。
- 当配置声明了 `scanScopes` 且扫描结果为 0 时返回失败。
- 失败信息包含 `module`、`surface.moduleKey`、`scanScopes`。

3. `fixture.positive / fixture.negative` 已强制非空。
- 在 `validateModuleContractConfig()` 增加 `fixture` 结构校验。
- 缺失 `fixture`、`fixture.positive=[]`、`fixture.negative=[]` 均 fail closed。
- 错误信息可定位到模块名与字段。

4. 已补反向测试。
- 新增配置类反向用例：
  - `scanScopes: ['apix']` 失败。
  - scope 拼错时（存在违规代码）仍先配置失败，不会因扫描 0 文件假绿。
  - 合法 scope 但无匹配文件失败。
  - 缺失 `fixture` 失败。
  - `fixture.positive=[]` 失败。
  - `fixture.negative=[]` 失败。

## 2. 修改文件

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/frontend-contract-engine.mjs`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-frontend-contract-engine.mjs`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-010B1_前端门禁公共框架FailClosed配置整改_交付证据.md`

## 3. 验证命令与结果

执行目录：`/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc`

```bash
npm run test:frontend-contract-engine
npm run check:style-profit-contracts
npm run test:style-profit-contracts
npm run check:factory-statement-contracts
npm run test:factory-statement-contracts
npm run verify
npm audit --audit-level=high
```

结果：

- `npm run test:frontend-contract-engine`：通过，`scenarios=23`
- `npm run check:style-profit-contracts`：通过
- `npm run test:style-profit-contracts`：通过，`scenarios=475`
- `npm run check:factory-statement-contracts`：通过
- `npm run test:factory-statement-contracts`：通过，`scenarios=26`
- `npm run verify`：通过
- `npm audit --audit-level=high`：通过（`0 vulnerabilities`）

## 4. 禁改扫描结果

执行目录：`/Users/hh/Desktop/领意服装管理系统`

```bash
git diff --name-only -- "07_后端" ".github" "02_源码" "06_前端/lingyi-pc/src"
git diff --cached --name-only
```

结果：

- `07_后端/.github/02_源码/06_前端/src`：空输出（无改动）
- `git diff --cached --name-only`：空输出（未暂存）

## 5. 边界声明

- 未修改后端代码。
- 未修改 `.github`。
- 未修改 `02_源码`。
- 未修改前端业务 `src/**`。
- 未暂存、未提交、未 push。
