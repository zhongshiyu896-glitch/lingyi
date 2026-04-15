# TASK-REL-002 本地封版白名单基线提交_工程任务单

- 任务编号：TASK-REL-002
- 任务名称：本地封版白名单基线提交
- 模块范围：发布专项 / 本地仓库基线治理
- 前置任务：TASK-REL-001 本地封版后白名单提交与运行产物清理
- 前置状态：TASK-REL-001 已完成，运行产物已清理，暂存区为空，未提交
- 任务类型：本地白名单提交 / 提交前审计回显 / 非生产发布
- 执行日期：2026-04-15

## 一、任务目标

在 TASK-005 与 TASK-006 均已完成本地封版记录、且 TASK-REL-001 已完成运行产物清理的基础上，执行一次严格白名单逐文件暂存与本地 commit，形成可审计的本地封版基线。

本任务只固定本地仓库基线，不代表生产发布，不配置 remote，不 push，不创建 PR，不声明 GitHub hosted runner / required check 已闭环。

## 二、强制原则

1. 禁止使用 `git add .`。
2. 禁止使用 `git add -A`。
3. 禁止使用目录级粗粒度暂存，除非任务单白名单明确允许且执行前已确认目录仅含白名单文件。
4. 必须逐文件 `git add <path>` 暂存。
5. 必须在提交前输出 `git diff --cached --name-only` 给用户确认。
6. 用户确认 staged 清单前不得 commit。
7. 提交必须为本地 commit，不 push。
8. 提交信息不得包含“生产发布完成”。

## 三、允许提交白名单

### 1. TASK-005 / TASK-006 / TASK-REL 文档

允许提交以下范围内与 TASK-005、TASK-006、TASK-REL 直接相关的文档：

```text
03_需求与设计/01_架构设计/03_技术决策记录.md
03_需求与设计/01_架构设计/06_模块设计_款式利润报表.md
03_需求与设计/01_架构设计/07_模块设计_加工厂对账单.md
03_需求与设计/01_架构设计/架构师会话日志.md
03_需求与设计/02_开发计划/当前 sprint 任务清单.md
03_需求与设计/02_开发计划/TASK-005*.md
03_需求与设计/02_开发计划/TASK-006*.md
03_需求与设计/02_开发计划/TASK-REL-001*.md
03_需求与设计/02_开发计划/TASK-REL-002*.md
03_需求与设计/05_审计记录.md
03_需求与设计/05_审计记录/审计官会话日志.md
```

### 2. TASK-005 / TASK-006 前端代码与门禁

仅允许提交与款式利润只读前端、加工厂对账单前端、契约门禁直接相关的前端文件：

```text
06_前端/lingyi-pc/package.json
06_前端/lingyi-pc/package-lock.json
06_前端/lingyi-pc/.nvmrc
06_前端/lingyi-pc/.npmrc
06_前端/lingyi-pc/README.md
06_前端/lingyi-pc/index.html
06_前端/lingyi-pc/tsconfig.json
06_前端/lingyi-pc/tsconfig.node.json
06_前端/lingyi-pc/vite.config.ts
06_前端/lingyi-pc/src/main.ts
06_前端/lingyi-pc/src/App.vue
06_前端/lingyi-pc/src/env.d.ts
06_前端/lingyi-pc/src/router/index.ts
06_前端/lingyi-pc/src/stores/permission.ts
06_前端/lingyi-pc/src/api/request.ts
06_前端/lingyi-pc/src/api/auth.ts
06_前端/lingyi-pc/src/api/style_profit.ts
06_前端/lingyi-pc/src/api/factory_statement.ts
06_前端/lingyi-pc/src/views/style_profit/**
06_前端/lingyi-pc/src/views/factory_statement/**
06_前端/lingyi-pc/src/utils/factoryStatementExport.ts
06_前端/lingyi-pc/scripts/check-production-contracts.mjs
06_前端/lingyi-pc/scripts/test-production-contracts.mjs
06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs
06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs
06_前端/lingyi-pc/scripts/check-factory-statement-contracts.mjs
06_前端/lingyi-pc/scripts/test-factory-statement-contracts.mjs
```

### 3. TASK-005 / TASK-006 后端代码、迁移、测试、脚本

仅允许提交与款式利润、加工厂对账单、本地 PostgreSQL gate/acceptance 工具直接相关的后端文件：

```text
07_后端/lingyi_service/app/core/error_codes.py
07_后端/lingyi_service/app/core/permissions.py
07_后端/lingyi_service/app/main.py
07_后端/lingyi_service/app/models/__init__.py
07_后端/lingyi_service/app/models/style_profit.py
07_后端/lingyi_service/app/models/factory_statement.py
07_后端/lingyi_service/app/schemas/style_profit.py
07_后端/lingyi_service/app/schemas/factory_statement.py
07_后端/lingyi_service/app/routers/style_profit.py
07_后端/lingyi_service/app/routers/factory_statement.py
07_后端/lingyi_service/app/services/permission_service.py
07_后端/lingyi_service/app/services/style_profit*.py
07_后端/lingyi_service/app/services/erpnext_style_profit_adapter.py
07_后端/lingyi_service/app/services/factory_statement*.py
07_后端/lingyi_service/app/services/erpnext_purchase_invoice_adapter.py
07_后端/lingyi_service/migrations/versions/task_005*.py
07_后端/lingyi_service/migrations/versions/task_006*.py
07_后端/lingyi_service/tests/test_style_profit*.py
07_后端/lingyi_service/tests/test_factory_statement*.py
07_后端/lingyi_service/tests/test_ci_postgresql_gate.py
07_后端/lingyi_service/scripts/assert_pytest_junit_no_skip.py
07_后端/lingyi_service/scripts/run_postgresql_ci_gate.sh
07_后端/lingyi_service/scripts/run_acceptance_smoke.sh
07_后端/lingyi_service/scripts/run_task002_acceptance_smoke.sh
07_后端/lingyi_service/README.md
07_后端/lingyi_service/requirements-dev.txt
```

## 四、禁止提交清单

以下内容一律禁止暂存和提交：

```text
02_源码/**
.github/**
00_交接与日志/**
01_需求与资料/**
04_测试与验收/**
05_交付物/**
03_环境与部署/**
06_前端/lingyi-pc/node_modules/**
06_前端/lingyi-pc/dist/**
06_前端/lingyi-pc/coverage/**
07_后端/lingyi_service/.pytest_cache/**
07_后端/lingyi_service/.pytest-postgresql-*.xml
*.db
*.sqlite
*.log
.env
.env.*
```

除非另有新任务单明确放行，不得提交非 TASK-005 / TASK-006 / TASK-REL 相关历史遗留文件。

## 五、提交前必须执行

### 1. 仓库与工作区盘点

```bash
cd /Users/hh/Desktop/领意服装管理系统
git rev-parse HEAD
git status --short
git diff --name-only
git diff --cached --name-only
```

### 2. 运行产物复查

```bash
test ! -d '06_前端/lingyi-pc/dist' && echo 'dist absent' || echo 'dist exists'
test ! -d '07_后端/lingyi_service/.pytest_cache' && echo 'pytest_cache absent' || echo 'pytest_cache exists'
ls '07_后端/lingyi_service'/.pytest-postgresql-*.xml 2>/dev/null || echo 'postgresql junit xml absent'
```

若 `dist/` 因 verify 重新生成，必须在提交前再次清理或确认未暂存。

### 3. 前端验证

```bash
cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc
npm run verify
npm audit --audit-level=high
```

### 4. 后端验证

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest -q tests/test_style_profit_api.py tests/test_style_profit_api_permissions.py tests/test_style_profit_api_audit.py tests/test_style_profit_api_errors.py tests/test_factory_statement*.py
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
```

### 5. 禁止能力扫描

```bash
cd /Users/hh/Desktop/领意服装管理系统
rg -n "submit Purchase Invoice|/api/resource/Purchase Invoice|Payment Entry|GL Entry|createPaymentEntry|createGlEntry" 07_后端/lingyi_service/app 07_后端/lingyi_service/tests 06_前端/lingyi-pc/src || true
rg -n "factory-statements/internal|payable-draft-sync/run-once|/api/resource" 06_前端/lingyi-pc/src || true
```

允许命中负向测试、契约反向测试或状态枚举；若命中生产实现路径，必须停止并提审。

## 六、暂存流程

1. 按白名单逐文件执行 `git add <path>`。
2. 禁止 `git add .`。
3. 禁止 `git add -A`。
4. 暂存后必须执行：

```bash
git diff --cached --name-only
git diff --cached --check
```

5. 将 staged 清单回显给用户确认。
6. 用户确认后才允许 commit。

## 七、提交信息建议

```text
chore: baseline local sealed modules
```

或：

```text
chore: baseline local closeout for style profit and factory statement
```

## 八、交付证据要求

必须输出：

```text
/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-REL-002_本地封版白名单基线提交_交付证据.md
```

证据至少包含：

1. 提交前 HEAD。
2. 提交后 HEAD。
3. commit SHA 与 message。
4. staged 清单全文。
5. 禁止提交清单复核结果。
6. 前后端验证结果。
7. 是否使用 `git add .` / `git add -A`：必须为否。
8. 是否 push：必须为否。
9. 是否生产发布：必须为否。
10. 运行产物处理结果。

## 九、验收标准

1. 只提交白名单文件。
2. 未提交运行产物、缓存、数据库、环境变量、`node_modules`。
3. 未提交 `02_源码/**`、`.github/**`、`04_测试与验收/**`、`05_交付物/**`。
4. 前后端验证通过。
5. 禁止能力扫描无未解释生产路径命中。
6. 提交后证据文件记录完整。
7. 本地 commit 完成但不 push。
