# TASK-010D1 Legacy Fixture 白名单绕过整改交付证据

## 任务结论

TASK-010D 审计发现公共前端写入口门禁仍保留 `LEGACY_FIXTURE_OPTIONAL_MODULES`，导致 `style_profit` / `factory_statement` 可不声明 `fixture.positive` / `fixture.negative` 仍通过配置校验。本轮已完成整改，结论：待审计。

## 修复内容

1. 移除公共 engine 中的 legacy fixture 例外白名单。
2. `validateModuleContractConfig()` 对所有模块统一强制要求：
   - `fixture` 必须存在。
   - `fixture.positive` 必须为非空数组。
   - `fixture.negative` 必须为非空数组。
3. `style_profit` 模块配置显式补齐 `fixture.positive` / `fixture.negative`。
4. `factory_statement` 模块配置显式补齐 `fixture.positive` / `fixture.negative`。
5. 新增反向测试：
   - `legacy style_profit missing fixture should fail closed`
   - `legacy factory_statement missing fixture should fail closed`

## 修改文件

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/frontend-contract-engine.mjs`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-factory-statement-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-frontend-contract-engine.mjs`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-010D1_LegacyFixture白名单绕过整改_交付证据.md`

## 验证结果

- `npm run test:frontend-contract-engine`：通过，`scenarios=25`
- `npm run check:style-profit-contracts`：通过，`Scanned files: 28`
- `npm run test:style-profit-contracts`：通过，`scenarios=475`
- `npm run check:factory-statement-contracts`：通过，`Scanned files: 8`
- `npm run test:factory-statement-contracts`：通过，`scenarios=26`
- `npm run verify`：通过，含 production/style-profit/factory-statement/frontend-contract-engine/typecheck/build
- `npm audit --audit-level=high`：通过，`found 0 vulnerabilities`

## 复核点

- `LEGACY_FIXTURE_OPTIONAL_MODULES` 已移除。
- `style_profit` 缺失 fixture 会 fail closed。
- `factory_statement` 缺失 fixture 会 fail closed。
- 现有 `style_profit` 与 `factory_statement` wrapper 配置均已显式声明 fixture。

## 边界声明

- 未修改 `06_前端/lingyi-pc/src/**`。
- 未修改 `07_后端/**`。
- 未修改 `.github/**`。
- 未修改 `02_源码/**`。
- 未新增运行时代码入口。
- 未暂存，未提交，未 push，未配置 remote，未创建 PR。
- `npm run verify` 生成的 `dist/` 为构建产物，不纳入本任务提交范围。
