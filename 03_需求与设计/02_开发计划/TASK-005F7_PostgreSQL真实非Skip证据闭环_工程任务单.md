# TASK-005F7 PostgreSQL 真实非 Skip 证据闭环工程任务单

- 任务编号：TASK-005F7
- 模块：款式利润报表 / 外发加工管理 / PostgreSQL CI 门禁
- 版本：V1.0
- 更新时间：2026-04-14 16:05 CST
- 作者：技术架构师
- 优先级：P0
- 前置依赖：TASK-005F6 审计有条件通过，审计意见书第 109 份
- 执行角色：后端工程师 / 本地环境负责人
- 审计要求：完成后必须提交审计官复审；复审通过前不得进入 TASK-005G、前端创建入口或 TASK-006

## 1. 任务目标

闭环 TASK-005F6 审计保留的唯一中危问题：在真实 PostgreSQL 一次性测试库下运行后端 PostgreSQL hard gate，回填两份 JUnit 非 skip 证据。

必须产出：

1. settlement JUnit：`.pytest-postgresql-subcontract-settlement.xml`，指标为 `tests=4, skipped=0, failures=0, errors=0`。
2. style-profit JUnit：`.pytest-postgresql-style-profit-subcontract.xml`，指标为 `tests=4, skipped=0, failures=0, errors=0`。
3. 脱敏后的执行命令、环境、时间、数据库名、敏感信息扫描结果。

本任务不新增功能，不修改业务逻辑。

## 2. 本任务边界

### 2.1 允许操作

- 使用本地 Docker PostgreSQL 或本机 PostgreSQL 创建一次性测试库。
- 执行 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/scripts/run_postgresql_ci_gate.sh`。
- 更新或新建 PostgreSQL 非 skip 证据文档。
- 读取并记录两份 JUnit 的测试统计。

### 2.2 允许修改

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005F4_PostgreSQL非Skip证据.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005F6_Workflow双JUnit上传证据.md`

### 2.3 允许新建

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005F7_PostgreSQL真实非Skip证据.md`

### 2.4 禁止修改

- 禁止修改 `/Users/hh/Desktop/领意服装管理系统/06_前端/**`
- 禁止修改 `/Users/hh/Desktop/领意服装管理系统/02_源码/**`
- 禁止修改 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/**`
- 禁止修改 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/**`
- 禁止修改 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/scripts/**`
- 禁止修改迁移文件
- 禁止修改 `.github/**`
- 禁止新增或修改任何 `TASK-006*` 文件
- 禁止把 skip、失败或未执行伪装成非 skip 通过
- 禁止使用生产库、准生产库或任何含真实业务数据的数据库

如果真实 PostgreSQL hard gate 失败，本任务只允许记录失败证据并停止，不允许在本任务内修代码。

## 3. PostgreSQL 测试库安全门禁

必须满足全部条件：

1. `POSTGRES_TEST_ALLOW_DESTRUCTIVE=true`。
2. 数据库名必须匹配以下任一格式：
   - `lingyi_test_*`
   - `*_test`
3. DSN 必须指向一次性测试库。
4. 证据文档不得出现真实密码、token、Cookie、Authorization、私钥或完整 DSN。
5. 如果 DSN 不符合安全门禁，必须停止执行并记录“未执行，原因：DSN 不安全”。

## 4. 推荐执行方式 A：Docker 一次性 PostgreSQL

在 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service` 执行：

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service

docker rm -f lingyi-pg-gate 2>/dev/null || true

docker run --rm \
  --name lingyi-pg-gate \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=lingyi_test_pg_gate \
  -p 55432:5432 \
  -d postgres:16

sleep 5

POSTGRES_TEST_ALLOW_DESTRUCTIVE=true \
POSTGRES_TEST_DSN='postgresql+psycopg://postgres:***@127.0.0.1:55432/lingyi_test_pg_gate' \
bash scripts/run_postgresql_ci_gate.sh
```

注意：实际执行时 `POSTGRES_TEST_DSN` 需要使用真实密码；写入证据文档时必须脱敏成 `***`。

执行后清理：

```bash
docker rm -f lingyi-pg-gate
```

## 5. 推荐执行方式 B：本机一次性 PostgreSQL

如果本机已有 PostgreSQL，可以创建一次性库：

```bash
createdb lingyi_test_pg_gate

cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service

POSTGRES_TEST_ALLOW_DESTRUCTIVE=true \
POSTGRES_TEST_DSN='postgresql+psycopg://USER:***@127.0.0.1:5432/lingyi_test_pg_gate' \
bash scripts/run_postgresql_ci_gate.sh
```

执行完成后可删除一次性库：

```bash
dropdb lingyi_test_pg_gate
```

## 6. 必须核验的 JUnit 指标

运行成功后必须核验：

| JUnit 文件 | 必须指标 |
| --- | --- |
| `.pytest-postgresql-subcontract-settlement.xml` | `tests=4, skipped=0, failures=0, errors=0` |
| `.pytest-postgresql-style-profit-subcontract.xml` | `tests=4, skipped=0, failures=0, errors=0` |

可以使用现有 JUnit 断言工具或手工读取 XML，但证据中必须明确两份文件的四项指标。

## 7. 证据文档要求

新建或更新：

`/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005F7_PostgreSQL真实非Skip证据.md`

必须包含：

1. 执行时间。
2. 执行人。
3. 执行目录。
4. PostgreSQL 来源：Docker / 本机 / 其他一次性测试库。
5. 数据库名：必须是 `lingyi_test_*` 或 `*_test`。
6. 脱敏 DSN。
7. 执行命令。
8. settlement JUnit 指标。
9. style-profit JUnit 指标。
10. 敏感信息扫描结果。
11. 清理动作。
12. 结论：通过 / 不通过。

如果执行失败，证据文档必须记录：

1. 失败命令。
2. 失败阶段。
3. 脱敏错误摘要。
4. 两份 JUnit 是否生成。
5. 是否存在 skip、failure 或 error。
6. 明确结论为“不通过”，不得进入 TASK-005G。

## 8. 敏感信息扫描

证据文件写完后必须扫描：

```bash
rg -n "postgresql\+psycopg://[^*\n]*:[^*\n]*@|password|passwd|secret|token|Authorization|Cookie|BEGIN PRIVATE KEY|github_pat|ghp_" \
  /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005F7_PostgreSQL真实非Skip证据.md
```

要求：不得出现真实密码、token、Cookie、Authorization、私钥或未脱敏 DSN。

## 9. 回归验证要求

即使本任务只做证据，也必须复跑现有基线：

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service

.venv/bin/python -m pytest -q tests/test_ci_postgresql_gate.py
.venv/bin/python -m pytest -q
.venv/bin/python -m unittest discover
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
```

## 10. 禁改扫描

交付前必须执行：

```bash
git status --short -- \
  06_前端 \
  02_源码 \
  .github \
  07_后端/lingyi_service/app \
  07_后端/lingyi_service/tests \
  07_后端/lingyi_service/scripts \
  07_后端/lingyi_service/migrations \
  03_需求与设计/02_开发计划/TASK-006*
```

要求：上述路径不得有本任务新增修改。

## 11. 验收标准

□ 使用真实 PostgreSQL 一次性测试库执行 `scripts/run_postgresql_ci_gate.sh`。  
□ 数据库名符合 `lingyi_test_*` 或 `*_test`。  
□ `POSTGRES_TEST_ALLOW_DESTRUCTIVE=true` 已显式设置。  
□ settlement JUnit 为 `tests=4, skipped=0, failures=0, errors=0`。  
□ style-profit JUnit 为 `tests=4, skipped=0, failures=0, errors=0`。  
□ 证据文档记录脱敏 DSN、命令、时间、JUnit 指标和清理动作。  
□ 敏感信息扫描通过。  
□ 定向 pytest、全量 pytest、unittest、py_compile 通过。  
□ 禁改扫描通过。  
□ 未修改业务代码、测试代码、脚本、迁移、前端、`.github`、`02_源码` 或 TASK-006。  
□ 审计官复审通过前不得进入 TASK-005G、前端创建入口或 TASK-006。  

## 12. 交付说明要求

工程师交付时必须说明：

1. PostgreSQL 测试库来源：Docker / 本机 / 其他一次性库。
2. 数据库名。
3. 脱敏 DSN。
4. 执行命令。
5. 两份 JUnit 指标。
6. 敏感信息扫描结果。
7. 清理动作。
8. 回归测试结果。
9. 禁改扫描结果。
10. 如失败，明确失败原因，不得申请进入 TASK-005G。
