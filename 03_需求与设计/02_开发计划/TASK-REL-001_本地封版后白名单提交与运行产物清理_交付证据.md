# TASK-REL-001 本地封版后白名单提交与运行产物清理_交付证据

- 执行人：工程师（Codex）
- 执行时间：2026-04-15 23:05
- 当前 HEAD：`1da795333d20ed8ecfb2308da623358668272458`
- 是否提交：否
- 提交 SHA：无
- 结论：通过（本地基线治理完成，未提交）

## 1. 工作区盘点

- `git status --short`：
  - tracked diff：14 个文件（集中在 `03_需求与设计`、`06_前端`、`07_后端` 白名单范围）
  - untracked：73740 个文件（历史遗留为主）
- `git diff --name-only`：14 个文件
  - `03_需求与设计/01_架构设计/03_技术决策记录.md`
  - `03_需求与设计/01_架构设计/06_模块设计_款式利润报表.md`
  - `03_需求与设计/01_架构设计/架构师会话日志.md`
  - `03_需求与设计/02_开发计划/当前 sprint 任务清单.md`
  - `03_需求与设计/05_审计记录.md`
  - `03_需求与设计/05_审计记录/审计官会话日志.md`
  - `06_前端/lingyi-pc/package.json`
  - `06_前端/lingyi-pc/src/router/index.ts`
  - `06_前端/lingyi-pc/src/stores/permission.ts`
  - `07_后端/lingyi_service/app/core/error_codes.py`
  - `07_后端/lingyi_service/app/core/permissions.py`
  - `07_后端/lingyi_service/app/main.py`
  - `07_后端/lingyi_service/app/models/__init__.py`
  - `07_后端/lingyi_service/app/services/permission_service.py`
- `git ls-files --others --exclude-standard` 分组摘要：
  - `04_测试与验收`：69862
  - `01_需求与资料`：3082
  - `02_源码`：487
  - `05_交付物`：176
  - `03_需求与设计`：87
  - `07_后端`：29
  - `06_前端`：8
  - `00_交接与日志`：5
  - `03_环境与部署`：4
- 白名单候选（按任务单规则过滤）共 113：
  - `03_需求与设计` 非 TASK 文档：11
  - `TASK-005/006` 文档：76
  - `06_前端 factory_statement`：7
  - `07_后端 factory_statement`：19
- 非白名单历史遗留（如 `04_测试与验收/**`、`02_源码/**` 等）本任务未纳入。

## 2. 运行产物处理

- 处理前盘点命中：`dist/`、`.pytest_cache/`、`.pytest-postgresql-*.xml`、`node_modules/`
- 按任务单允许范围已清理：
  - `06_前端/lingyi-pc/dist/`（已清理）
  - `07_后端/lingyi_service/.pytest_cache/`（已清理）
  - `07_后端/lingyi_service/.pytest-postgresql-subcontract-settlement.xml`（已清理）
  - `07_后端/lingyi_service/.pytest-postgresql-style-profit-subcontract.xml`（已清理）
- `node_modules/`：按任务单默认保留，仅确保未暂存
- 最终运行产物盘点：仅剩 `06_前端/lingyi-pc/node_modules`

## 3. 暂存白名单

本次未执行暂存（未提交），`git diff --cached --name-only` 为空。

> 说明：本任务以“基线盘点 + 运行产物清理 + 验证复跑”为主；为避免将历史遗留 diff 混入，未执行白名单提交动作。

## 4. 禁止项扫描结果

- dist：未暂存
- node_modules：未暂存
- .pytest_cache：未暂存（且已清理）
- .pytest-postgresql-*.xml：未暂存（且已清理）
- secret/env/token/dsn：staged 为空，未发现
- 02_源码：未暂存
- .github：未暂存

## 5. 验证结果

- 后端 factory statement pytest：通过
  - 命令：`.venv/bin/python -m pytest -q tests/test_factory_statement*.py`
  - 结果：`77 passed, 244 warnings`
- 后端 py_compile：通过
  - 命令：`.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)`
- 前端 npm run verify：通过
  - 命令：`npm run verify`
  - 结果：包含 production/style-profit/factory-statement contracts、typecheck、build 全通过
- 前端 npm audit：通过
  - 命令：`npm audit --audit-level=high`
  - 结果：`found 0 vulnerabilities`
- factory-statement contracts：通过
  - 命令：`npm run test:factory-statement-contracts`
  - 结果：`scenarios=26`
- style-profit contracts：通过
  - 命令：`npm run test:style-profit-contracts`
  - 结果：`scenarios=475`

## 6. 本任务不包含

- 不包含生产发布
- 不包含 ERPNext 生产联调
- 不包含 GitHub required check
- 不包含 push/PR

## 7. 遗留风险

1. 工作区历史 untracked 数量较大（73740），后续若执行提交必须继续严格白名单逐文件暂存。
2. 前端 `npm run verify` 会再生成 `dist/`，需在提交前重复清理或确保不暂存。
3. 后端 pytest 仍有 `datetime.utcnow()` 相关 deprecation warnings（已知环境专项）。
