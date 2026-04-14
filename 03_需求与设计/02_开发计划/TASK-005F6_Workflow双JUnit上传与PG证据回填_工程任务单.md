# TASK-005F6 Workflow 双 JUnit 上传与 PostgreSQL 证据回填工程任务单

- 任务编号：TASK-005F6
- 模块：款式利润报表 / 外发加工管理 / PostgreSQL CI 门禁
- 版本：V1.0
- 更新时间：2026-04-14 15:55 CST
- 作者：技术架构师
- 优先级：P0
- 前置依赖：TASK-005F5 审计有条件通过，审计意见书第 108 份
- 执行角色：后端工程师
- 审计要求：完成后必须提交审计官复审；复审通过前不得进入 TASK-005G、前端创建入口或 TASK-006

## 1. 任务目标

修复 TASK-005F5 审计保留的两个中危问题：

1. GitHub workflow 仍上传旧 `.pytest-postgresql.xml`，无法上传双门禁脚本实际生成的两份 JUnit。
2. TASK-005F4/F5 PostgreSQL 非 skip 实跑证据仍为 pending。

本任务允许小范围修改 `.github/workflows/backend-postgresql.yml`，但只能修正 PostgreSQL JUnit artifact 上传路径，不得进入其他 GitHub 平台闭环或改前端 CI。

## 2. 本任务边界

### 2.1 允许修改

- `/Users/hh/Desktop/领意服装管理系统/.github/workflows/backend-postgresql.yml`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_ci_postgresql_gate.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/README.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005F4_PostgreSQL非Skip证据.md`

### 2.2 允许新建

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005F6_Workflow双JUnit上传证据.md`

### 2.3 禁止修改

- 禁止修改 `/Users/hh/Desktop/领意服装管理系统/06_前端/**`
- 禁止修改 `/Users/hh/Desktop/领意服装管理系统/02_源码/**`
- 禁止修改迁移文件
- 禁止修改业务代码
- 禁止新增或修改任何 `TASK-006*` 文件
- 禁止弱化 PostgreSQL 脚本门禁
- 禁止删除 settlement 或 style-profit 任一 JUnit 上传
- 禁止把 pending 证据伪装成非 skip 已通过

## 3. Workflow 修改要求

修改：

`/Users/hh/Desktop/领意服装管理系统/.github/workflows/backend-postgresql.yml`

### 3.1 Artifact 上传要求

现有上传路径：

```yaml
path: 07_后端/lingyi_service/.pytest-postgresql.xml
```

必须改为上传双 JUnit，推荐两种方式二选一。

方案 A：单 artifact，多 path：

```yaml
- name: Upload PostgreSQL JUnit reports
  if: always()
  uses: actions/upload-artifact@v4
  with:
    name: postgresql-gate-junit
    path: |
      07_后端/lingyi_service/.pytest-postgresql-subcontract-settlement.xml
      07_后端/lingyi_service/.pytest-postgresql-style-profit-subcontract.xml
```

方案 B：两个 artifact：

```yaml
- name: Upload settlement PostgreSQL JUnit report
  if: always()
  uses: actions/upload-artifact@v4
  with:
    name: postgresql-settlement-junit
    path: 07_后端/lingyi_service/.pytest-postgresql-subcontract-settlement.xml

- name: Upload style-profit PostgreSQL JUnit report
  if: always()
  uses: actions/upload-artifact@v4
  with:
    name: postgresql-style-profit-junit
    path: 07_后端/lingyi_service/.pytest-postgresql-style-profit-subcontract.xml
```

推荐方案 B，审计证据更清楚。

### 3.2 禁止事项

1. 不得继续只上传 `.pytest-postgresql.xml`。
2. 不得只上传 style-profit JUnit。
3. 不得只上传 settlement JUnit。
4. 不得修改 job 名称规避审计。
5. 不得删除 PostgreSQL service。
6. 不得改 workflow 触发路径来绕过执行。

## 4. 静态一致性测试要求

修改：

`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_ci_postgresql_gate.py`

必须新增 workflow 一致性测试：

1. 读取 `.github/workflows/backend-postgresql.yml`。
2. 断言包含 `.pytest-postgresql-subcontract-settlement.xml`。
3. 断言包含 `.pytest-postgresql-style-profit-subcontract.xml`。
4. 断言不再只出现旧 `.pytest-postgresql.xml` 作为唯一 artifact path。
5. 断言 artifact name 能区分 settlement 与 style-profit，或单 artifact path 同时包含两份文件。
6. 断言 workflow 仍调用 `bash scripts/run_postgresql_ci_gate.sh`。
7. 断言 workflow job 仍包含 PostgreSQL service。
8. 增加反向测试：如果 workflow 只上传旧 `.pytest-postgresql.xml`，测试必须失败。

## 5. PostgreSQL 非 skip 证据要求

### 5.1 如果当前有真实 PostgreSQL DSN

执行：

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
POSTGRES_TEST_ALLOW_DESTRUCTIVE=true POSTGRES_TEST_DSN='postgresql+psycopg://***@HOST:PORT/lingyi_test_xxx' bash scripts/run_postgresql_ci_gate.sh
```

必须回填：

1. settlement JUnit：`tests=4, skipped=0, failures=0, errors=0`
2. style-profit JUnit：`tests=4, skipped=0, failures=0, errors=0`
3. 脱敏 DSN。
4. 命令。
5. 时间。
6. JUnit 文件名。
7. 敏感信息扫描结果。

### 5.2 如果当前没有真实 PostgreSQL DSN

1. 证据文件必须保持 pending。
2. 明确本地无 DSN，只能证明脚本和静态一致性测试通过。
3. 明确双 JUnit artifact 上传路径已修复。
4. 不得写“非 skip 通过”。
5. 保留后续回填字段。

## 6. README 更新要求

更新 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/README.md`：

1. 说明 workflow 会上传两份 JUnit artifact。
2. 写明文件名：
   - `.pytest-postgresql-subcontract-settlement.xml`
   - `.pytest-postgresql-style-profit-subcontract.xml`
3. 如果采用两个 artifact，写明 artifact 名称。
4. 明确旧 `.pytest-postgresql.xml` 已废弃，不再作为证据文件。
5. 明确 TASK-005 财务封版仍需真实非 skip 证据。

## 7. 测试要求

必须通过：

1. `tests/test_ci_postgresql_gate.py`
2. 双 PG 文件本地无 DSN 安全 skip
3. `-m postgresql` 本地无 DSN 安全 skip
4. 全量 pytest
5. unittest discover
6. py_compile

如果有 PostgreSQL DSN，必须额外通过 `bash scripts/run_postgresql_ci_gate.sh` 并生成两份 JUnit。

## 8. 建议验证命令

在 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service` 执行：

```bash
.venv/bin/python -m pytest -q tests/test_ci_postgresql_gate.py
.venv/bin/python -m pytest -q tests/test_style_profit_subcontract_postgresql.py tests/test_subcontract_settlement_postgresql.py
.venv/bin/python -m pytest -q -m postgresql tests/test_style_profit_subcontract_postgresql.py tests/test_subcontract_settlement_postgresql.py
.venv/bin/python -m pytest -q
.venv/bin/python -m unittest discover
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
```

## 9. 禁改扫描

交付前必须执行：

```bash
git status --short -- 06_前端 02_源码 07_后端/lingyi_service/migrations 03_需求与设计/02_开发计划/TASK-006*
```

说明：本任务允许修改 `.github/workflows/backend-postgresql.yml`，所以禁改扫描不包含 `.github`。

## 10. 验收标准

□ workflow 上传 `.pytest-postgresql-subcontract-settlement.xml`。  
□ workflow 上传 `.pytest-postgresql-style-profit-subcontract.xml`。  
□ workflow 不再只上传旧 `.pytest-postgresql.xml`。  
□ workflow 仍调用 `bash scripts/run_postgresql_ci_gate.sh`。  
□ workflow 仍包含 PostgreSQL service。  
□ `tests/test_ci_postgresql_gate.py` 能发现 workflow artifact path 回退。  
□ README 说明双 JUnit artifact。  
□ 证据文件不伪装非 skip 通过。  
□ 如有 DSN，两组 JUnit 均为 `tests=4, skipped=0, failures=0, errors=0`。  
□ 定向 pytest、全量 pytest、unittest、py_compile 通过。  
□ 禁改扫描通过。  
□ 审计官复审通过前不得进入 TASK-005G、前端创建入口或 TASK-006。  

## 11. 交付说明要求

工程师交付时必须说明：

1. workflow artifact 修改方案（A 或 B）。
2. 两份 JUnit 文件名和 artifact 名称。
3. `test_ci_postgresql_gate.py` 新增测试清单。
4. 本地无 DSN skip 结果，或真实 DSN 非 skip 结果。
5. README 更新摘要。
6. 敏感信息扫描结果。
7. 禁改扫描结果。
8. 未修改业务代码、未进入前端、未进入迁移、未进入 TASK-006。
