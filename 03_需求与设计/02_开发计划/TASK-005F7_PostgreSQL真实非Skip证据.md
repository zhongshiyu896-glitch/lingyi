# TASK-005F7 PostgreSQL 真实非 Skip 证据

- 任务编号：TASK-005F7
- 执行时间：2026-04-14 16:04 CST
- 执行人：Codex 工程执行
- 执行目录：`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service`
- PostgreSQL 来源：Docker 一次性测试库（`postgres:16-alpine`）
- 数据库名：`lingyi_test_pg_gate`
- 脱敏 DSN：`postgresql+psycopg://postgres:***@127.0.0.1:55432/lingyi_test_pg_gate`

## 1. 执行命令

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service

docker rm -f lingyi-pg-gate 2>/dev/null || true

docker run --rm --name lingyi-pg-gate \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=lingyi_test_pg_gate \
  -p 55432:5432 -d postgres:16-alpine

POSTGRES_TEST_ALLOW_DESTRUCTIVE=true \
POSTGRES_TEST_DSN='postgresql+psycopg://postgres:***@127.0.0.1:55432/lingyi_test_pg_gate' \
  bash scripts/run_postgresql_ci_gate.sh
```

## 2. JUnit 指标

1. `.pytest-postgresql-subcontract-settlement.xml`
   - tests=4
   - skipped=0
   - failures=3
   - errors=0

2. `.pytest-postgresql-style-profit-subcontract.xml`
   - 未生成（脚本在 settlement 门禁失败后已按 `set -e` 中断）

## 3. 关键失败信息

`run_postgresql_ci_gate.sh` 执行失败，settlement PostgreSQL 用例报错：

- 错误类型：`sqlalchemy.exc.ProgrammingError`
- 关键报错：`column "sales_order" of relation "ly_subcontract_order" does not exist`
- 失败用例：`tests/test_subcontract_settlement_postgresql.py` 中 3 个用例失败，1 个通过。

## 4. 安全门禁与敏感信息检查

1. 已设置 `POSTGRES_TEST_ALLOW_DESTRUCTIVE=true`。
2. 测试库名称满足 `lingyi_test_*` 规则。
3. 证据文档与命令未泄露明文 token/cookie/Authorization/私钥。
4. DSN 已脱敏显示。

## 5. 清理动作

```bash
docker rm -f lingyi-pg-gate
```

容器已清理，不保留运行实例。

## 6. 禁改扫描结果

执行命令：

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

结果说明：
- 输出存在多项既有改动/未跟踪项（本轮前已存在于工作区）。
- 本次 TASK-005F7 未新增业务代码修改，仅新增本证据文件。
- 未出现 `TASK-006*` 改动。

## 7. 结论

- 结论：**不通过（真实 non-skip 实跑失败）**
- 按任务单失败处理要求：
1. 仅记录失败证据并停止。
2. 本任务内不修代码。
3. 不进入 TASK-005G。
4. TASK-006 继续阻塞。
