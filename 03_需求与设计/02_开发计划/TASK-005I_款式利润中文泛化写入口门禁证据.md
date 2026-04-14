# TASK-005I 款式利润中文泛化写入口门禁证据

- 任务编号：TASK-005I
- 记录时间：2026-04-14 18:07 CST
- 执行人：Codex
- 执行基线 HEAD：`3d778cb55b63755bf69e263afe6e2d7b62d85b3d`

## 实施范围

本次仅增强前端只读门禁，不开放创建入口，不修改后端业务代码。

变更文件：
1. `06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
2. `06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`
3. `03_需求与设计/02_开发计划/TASK-005I_款式利润中文泛化写入口门禁证据.md`

## 中文语义门禁矩阵

### 领域词
- 款式利润
- 利润快照
- 利润报表
- 毛利
- 净利
- 利润核算
- 利润（补充通用词，用于命中“利润一键生成”等绕过写法）

### 写动作词
- 新建
- 创建
- 生成
- 重算
- 重新计算
- 计算
- 核算
- 提交
- 保存
- 一键生成

### 组合拦截规则
1. `领域词` 与 `写动作词` 在前后 0-16 字符内组合出现即阻断。
2. 阻断英文写入口命名：
   - `createProfit / generateProfit / recalculateProfit`
   - `createSnapshot / generateSnapshot / recalculateSnapshot`
   - `profitCreate / profitGenerate / profitRecalculate`
   - `generateProfitSnapshot`
   - `openProfitCalculateDialog`
3. 阻断写入口路由：
   - `/reports/style-profit/create`
   - `/reports/style-profit/new`
   - `/reports/style-profit/generate`
   - `/reports/style-profit/recalculate`
   - `/reports/style-profit/calculate`

## 白名单与防误杀

### 只读文案白名单
以下只读词不应被误杀：
- 款式利润报表
- 利润快照列表
- 利润快照详情
- 查看详情
- 查询
- 筛选
- 搜索
- 返回
- 审计信息
- 利润明细
- 来源追溯
- 利润率
- 利润金额

### 规则白名单
1. `src/api/request.ts` 和 `src/api/auth.ts` 中统一封装与鉴权场景允许出现 `fetch(`。
2. `src/api/request.ts` 必须保留 Authorization 组装。

白名单原因：
- 保留统一请求封装和鉴权实现，避免误将基础设施能力识别为业务写入口。
- 保证只读页面中的财务展示文案可正常通过门禁。

## 反向测试覆盖

`test-style-profit-contracts.mjs` 已覆盖并验证以下失败场景：
1. `<el-button>款式利润计算</el-button>`
2. `<el-button>利润报表重算</el-button>`
3. `<el-button>毛利核算</el-button>`
4. `<el-button>利润一键生成</el-button>`
5. `function openProfitCalculateDialog()`
6. 路由 `/reports/style-profit/calculate`
7. 标识符 `generateProfitSnapshot`
8. TASK-005H 既有反向场景（snapshot_create、POST、idempotency_key、create route、canRead 前置缺失、裸 fetch）均保留

## 验证结果

执行目录：`/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc`

1. `npm run check:style-profit-contracts`
   - 结果：通过（Scanned files: 24）
2. `npm run test:style-profit-contracts`
   - 结果：通过（scenarios=16）
3. `npm run verify`
   - 结果：通过（production/style-profit 契约、typecheck、build 全通过）
4. `npm audit --audit-level=high`
   - 结果：通过（found 0 vulnerabilities）

执行目录：`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service`

5. `.venv/bin/python -m pytest -q tests/test_style_profit_api.py tests/test_style_profit_api_permissions.py tests/test_style_profit_api_audit.py tests/test_style_profit_api_errors.py`
   - 结果：34 passed, 1 warning
6. `.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)`
   - 结果：通过

## 静态禁线扫描结果

命令：

```bash
rg -n "款式利润.{0,16}(新建|创建|生成|重算|重新计算|计算|核算|提交|保存)|((新建|创建|生成|重算|重新计算|计算|核算|提交|保存).{0,16}款式利润)|利润报表.{0,16}(新建|创建|生成|重算|重新计算|计算|核算|提交|保存)|((新建|创建|生成|重算|重新计算|计算|核算|提交|保存).{0,16}利润报表)|毛利核算|净利核算|利润一键生成|createProfit|generateProfit|recalculateProfit|createSnapshot|generateSnapshot|recalculateSnapshot|profitCreate|profitGenerate|profitRecalculate" /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src
```

结果：无命中（exit code 1，stdout 为空）。

## 边界确认

- 未修改 `07_后端/**`
- 未修改 `.github/**`
- 未修改 `02_源码/**`
- 未修改 `TASK-006*`
- 未纳入 `.pytest-postgresql-*.xml`
- 未开放利润快照创建/生成/重算入口

## 结论

TASK-005I 已完成：款式利润前端中文泛化写入口门禁已收口，能够识别并阻断中文语义与英文命名的写入口绕过，同时保证只读文案和统一请求白名单不被误杀。TASK-006 仍未进入。
