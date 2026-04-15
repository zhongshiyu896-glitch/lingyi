# TASK-006D1 Worker/Outbox 状态机安全整改工程任务单

- 任务编号：TASK-006D1
- 模块：加工厂对账单
- 优先级：P0
- 版本：V1.0
- 更新时间：2026-04-15 19:47 CST
- 作者：技术架构师
- 前置依赖：TASK-006D 审计不通过，审计意见书第 165 份指出 2 个 P1 阻断问题
- 任务边界：只修复 payable outbox 与 worker 状态机安全问题；不得进入 TASK-006E，不得修改前端，不得新增 Payment Entry/GL Entry，不得提交 ERPNext Purchase Invoice。

## 一、任务目标

关闭 TASK-006D 审计发现的两个高危问题：

1. 已创建 payable outbox 后，对账单仍可取消，worker 后续可能先创建 ERPNext Purchase Invoice 草稿，再发现本地状态非法，形成孤儿 PI 草稿。
2. `claim_due()` 两阶段 claim 中，第二阶段 `UPDATE` 未重复校验 due/lease 条件，stale id 可抢占未过期 `processing` lease，导致重复处理风险。

本任务目标是把 payable outbox 状态机收紧为：

```text
创建 payable outbox 后，本地 statement 进入不可取消保护。
worker 在任何 ERPNext 调用前，必须重新读取并校验 statement 当前状态和 outbox 归属。
claim UPDATE 必须原子重复校验 due/lease 条件。
```

## 二、继续冻结的边界

以下内容仍禁止：

```text
TASK-006E 前端页面
打印页面
ERPNext Purchase Invoice submit/docstatus=1
Payment Entry
GL Entry
对账调整单
自动反冲/红冲
修改 .github
修改 02_源码
```

本任务允许继续保留 TASK-006D 已实现的 ERPNext Purchase Invoice 草稿创建，但必须保证：

```text
1. 已取消 statement 不会触发 ERPNext create/find。
2. pending/processing/succeeded payable outbox 存在时，statement 不可取消。
3. worker 调 ERPNext 前，statement 状态必须仍满足处理条件。
4. outbox claim 不得抢占未过期 lease。
```

## 三、允许修改文件

```text
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/factory_statement.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/factory_statement.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/factory_statement.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/factory_statement_service.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/factory_statement_payable_outbox_service.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/factory_statement_payable_worker.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_factory_statement_payable*.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_factory_statement_confirm_cancel.py
/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-006D1_WorkerOutbox状态机安全整改_交付证据.md
```

如确需迁移来补字段或索引，允许新增：

```text
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/versions/task_006d1_*.py
```

但不得改变 TASK-006D 已冻结的财务口径和 PI payload 金额口径。

## 四、禁止修改文件

```text
/Users/hh/Desktop/领意服装管理系统/06_前端/**
/Users/hh/Desktop/领意服装管理系统/.github/**
/Users/hh/Desktop/领意服装管理系统/02_源码/**
```

禁止新增或修改以下能力：

```text
ERPNext Purchase Invoice submit
Payment Entry 创建
GL Entry 创建
前端 payable 按钮/页面
打印页面
对账调整单
```

## 五、问题一整改：取消与 payable outbox 状态互斥

### 1. 取消前必须检查 payable outbox

`cancel` 服务在释放 inspection 前，必须检查当前 statement 是否存在 active payable outbox。

active payable outbox 状态定义：

```text
pending
processing
succeeded
```

建议处理：

```text
1. 存在 pending/processing/succeeded payable outbox 时，cancel 必须 fail closed。
2. 返回错误码：FACTORY_STATEMENT_PAYABLE_OUTBOX_ACTIVE。
3. 不得释放 inspection。
4. 不得修改 statement.status。
5. 必须写操作失败审计。
```

可选处理：如果当前已实现 `payable_draft_created` 状态，`succeeded` outbox 也可由 `FACTORY_STATEMENT_PAYABLE_ALREADY_CREATED` 表达；但 pending/processing 必须有明确错误，不得放行 cancel。

### 2. 创建 payable outbox 后的本地状态保护

创建 payable outbox 成功后，必须让后续 cancel 能识别“应付生成中”。可选择以下方案之一：

```text
方案 A：新增 statement.status = payable_draft_pending。
方案 B：不新增状态，但 cancel 查询 active payable outbox 并 fail closed。
```

推荐方案 B，改动小且符合当前审计要求。

无论采用哪种方案，都必须满足：

```text
pending payable outbox 存在时，cancel 不允许成功。
processing payable outbox 存在时，cancel 不允许成功。
succeeded payable outbox 存在时，cancel 不允许成功。
failed/dead payable outbox 是否允许 cancel 必须明确：
  - 推荐允许 cancel，但必须先确认没有 pending/processing/succeeded outbox。
  - 如不允许，也必须返回明确错误码，不得释放 inspection。
```

## 六、问题二整改：worker 调 ERPNext 前强校验 statement 状态

`factory_statement_payable_worker.py` 在任何 ERPNext 调用前，必须重新读取本地 statement，并校验：

```text
1. statement 存在。
2. outbox.statement_id 与 statement.id 一致。
3. statement.status 仍允许处理。
4. statement 不是 cancelled。
5. statement 没有被其他 payable outbox 成功占用。
6. statement.net_amount 与 outbox payload_hash/request_hash 仍一致，或 outbox 使用冻结 payload，不得实时重算覆盖。
```

允许 worker 处理的 statement 状态建议：

```text
confirmed
```

如实现了中间态，则允许：

```text
confirmed
payable_draft_pending
```

禁止处理：

```text
draft
cancelled
payable_draft_created
```

遇到非法状态时：

```text
1. 不得调用 ERPNext find/create。
2. outbox 标记 failed 或 dead，按设计选择，但必须不会继续重试污染外部系统。
3. 建议错误码：FACTORY_STATEMENT_INVALID_STATUS。
4. 写操作失败审计。
```

## 七、问题三整改：claim_due 原子校验 due/lease

`claim_due()` 不得只在 `list_due_ids()` 里判断 due/lease，第二阶段 `UPDATE` 也必须重复校验。

第二阶段 UPDATE 条件必须包含等价条件：

```text
id = :id
AND (
  (status IN ('pending', 'failed') AND (next_retry_at IS NULL OR next_retry_at <= now))
  OR
  (status = 'processing' AND locked_until < now)
)
```

不得允许：

```text
status='processing' AND locked_until > now
```

被第二个 worker 更新 attempts/locked_by/locked_until。

要求：

```text
1. stale id + 未过期 processing lease 不可 claim。
2. stale id + 已过期 processing lease 可 claim。
3. pending/failed 但 next_retry_at 在未来不可 claim。
4. pending/failed 且 due 可 claim。
5. claim 成功数量必须以 UPDATE rowcount 或返回行数为准。
```

如使用 PostgreSQL，推荐直接使用 `FOR UPDATE SKIP LOCKED` + 原子 update；如测试兼容 SQLite，必须用服务层逻辑模拟同等安全条件。

## 八、错误码要求

新增或确认以下错误码：

```text
FACTORY_STATEMENT_PAYABLE_OUTBOX_ACTIVE
FACTORY_STATEMENT_INVALID_STATUS
FACTORY_STATEMENT_PAYABLE_ALREADY_CREATED
FACTORY_STATEMENT_PAYABLE_WORKER_STALE_CLAIM
FACTORY_STATEMENT_DATABASE_WRITE_FAILED
FACTORY_STATEMENT_INTERNAL_ERROR
```

错误信封统一：

```json
{
  "code": "ERROR_CODE",
  "message": "用户可读错误",
  "detail": null
}
```

客户端不得收到 Python 异常原文、SQL 原文、ERPNext token/session 明文。

## 九、审计要求

必须写操作审计：

```text
1. cancel 因 active payable outbox 被拒绝。
2. worker 因 statement 已取消或非法状态而拒绝处理。
3. stale claim 被拒绝或跳过。
4. claim 成功。
5. worker 成功/失败。
```

必须写安全审计：

```text
1. worker 非服务账号调用。
2. cancel 无动作权限。
3. cancel 无 supplier/company 资源权限。
4. 权限源不可用。
```

审计和日志不得包含：

```text
Authorization
Cookie
Token
Secret
Password
ERPNext session
SQL 原文
完整 traceback 明文
```

## 十、必须补测试

### A. 已取消 statement 不得创建 ERPNext PI

复现路径：

```text
1. confirmed statement 调用 /payable-draft 创建 pending outbox。
2. 尝试 cancel。
3. 如果 cancel 被拒绝：断言 statement 仍未取消，inspection 未释放。
4. 如果工程实现允许 failed/dead 后 cancel，则 pending/processing 必须拒绝。
5. worker run_once。
```

必须断言：

```text
□ pending payable outbox 存在时 cancel 返回 FACTORY_STATEMENT_PAYABLE_OUTBOX_ACTIVE 或等价明确错误。
□ ERPNext create_purchase_invoice_draft 未被调用。
□ ERPNext find_by_event_key 未在非法 statement 状态下被调用。
□ 不产生孤儿 PI 草稿。
```

### B. worker 调 ERPNext 前校验 statement 状态

构造：

```text
1. 创建 payable outbox。
2. 直接把 statement.status 改成 cancelled 或 draft。
3. 执行 worker run_once。
```

断言：

```text
□ ERPNext find/create 均未调用。
□ outbox 标记 failed/dead 或按设计停止重试。
□ error_code = FACTORY_STATEMENT_INVALID_STATUS。
□ 写操作失败审计。
```

### C. stale id + 未过期 processing lease 不可 claim

构造：

```text
1. outbox.status = processing。
2. outbox.locked_until = now + 5 minutes。
3. 模拟 list_due_ids 返回该 stale id，或直接调用 claim_due 的第二阶段。
```

断言：

```text
□ claim_due 不更新该行。
□ attempts 不增加。
□ locked_by 不改变。
□ locked_until 不改变。
□ worker 不处理该 outbox。
```

### D. 已过期 processing lease 可 claim

构造：

```text
1. outbox.status = processing。
2. outbox.locked_until = now - 1 minute。
```

断言：

```text
□ claim_due 可以重新 claim。
□ attempts 增加 1。
□ locked_by 更新为当前 worker。
□ locked_until 延长。
```

### E. pending/failed next_retry_at 语义

断言：

```text
□ pending next_retry_at 未来不可 claim。
□ failed next_retry_at 未来不可 claim。
□ pending next_retry_at 为空或过去可 claim。
□ failed next_retry_at 为空或过去可 claim。
```

### F. 防越界扫描

```text
□ 未实现 Purchase Invoice submit/docstatus=1。
□ 未创建 Payment Entry。
□ 未创建 GL Entry。
□ 未修改前端。
□ 未修改 .github。
□ 未修改 02_源码。
```

## 十一、交付前自测命令

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service

.venv/bin/python -m pytest -q tests/test_factory_statement*.py
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)

rg -n "submit\(|docstatus\s*=\s*1|Payment Entry|GL Entry|create_payment|submit_purchase_invoice" app tests

git diff --name-only -- /Users/hh/Desktop/领意服装管理系统/06_前端 /Users/hh/Desktop/领意服装管理系统/.github /Users/hh/Desktop/领意服装管理系统/02_源码
```

## 十二、交付说明必须包含

```text
1. 修改文件清单。
2. cancel 与 active payable outbox 的互斥规则说明。
3. worker 调 ERPNext 前的 statement 状态校验说明。
4. claim_due 原子 due/lease 条件说明。
5. 新增测试名称和覆盖点。
6. 自测命令和结果。
7. 明确声明未提交 Purchase Invoice。
8. 明确声明未创建 Payment Entry/GL Entry。
9. 明确声明未修改前端、.github、02_源码。
```

## 十三、下一步门禁

```text
TASK-006D1 审计通过后，才允许重新判断是否进入 TASK-006E。
TASK-006E 仍必须单独下发前端任务单，不得由 D1 自动进入。
```
