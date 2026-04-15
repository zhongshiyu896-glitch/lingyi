# TASK-006E2 Payable Draft 同 Statement Active Outbox 防重整改工程任务单

- 任务编号：TASK-006E2
- 模块：加工厂对账单
- 优先级：P0
- 版本：V1.0
- 更新时间：2026-04-15 20:59 CST
- 作者：技术架构师
- 前置依赖：TASK-006E1 审计不通过，审计意见书第 168 份指出同 statement 可换幂等键重复创建 active payable outbox
- 任务边界：只修复 `/payable-draft` 创建路径的同 statement active outbox 防重；不得进入 TASK-006F，不得修改前端，除非只补契约测试；不得调用 internal worker，不得直连 ERPNext，不得提交 Purchase Invoice，不得创建 Payment Entry/GL Entry。

## 一、任务目标

关闭 TASK-006E1 审计发现的高危问题：

```text
同一 confirmed statement 已有 pending payable outbox 时，第二次请求换一个 idempotency_key 仍可创建新的 pending outbox。
```

本任务必须实现：

1. 同一 `statement_id` 同一时间只能存在一个 active payable outbox。
2. active 状态包括 `pending/processing/succeeded`。
3. 换不同 `idempotency_key` 不得绕过 active outbox 防重。
4. `event_key` 不得因为包含 `idempotency_key` 而允许同一 statement 多个 active outbox。
5. 并发请求不得创建两条 active outbox。
6. 前端按钮门禁只是体验层，后端必须独立防重。

## 二、继续冻结的边界

以下内容仍然禁止：

```text
TASK-006F
前端新功能
internal worker 调用入口
ERPNext /api/resource 前端直连
ERPNext Purchase Invoice submit/docstatus=1
Payment Entry
GL Entry
打印页面
对账调整单
自动反冲/红冲
```

本任务只处理后端 payable-draft active outbox 防重。

## 三、允许修改文件

```text
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/factory_statement.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/factory_statement_service.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/factory_statement_payable_outbox_service.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/factory_statement.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/factory_statement.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_factory_statement_payable*.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_factory_statement*.py
/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-006E2_PayableDraft同StatementActiveOutbox防重整改_交付证据.md
```

如需数据库层 partial unique index，允许新增迁移：

```text
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/versions/task_006e2_factory_statement_payable_active_scope.py
```

## 四、禁止修改文件

```text
/Users/hh/Desktop/领意服装管理系统/06_前端/**
/Users/hh/Desktop/领意服装管理系统/.github/**
/Users/hh/Desktop/领意服装管理系统/02_源码/**
```

如只补前端 contract 测试文件以验证“不依赖 UI 防重”，必须先在交付说明中标注；默认不改前端。

## 五、状态定义

active payable outbox：

```text
pending
processing
succeeded
```

inactive payable outbox：

```text
failed
dead
cancelled（如实现）
```

同一 `statement_id` 下存在 active payable outbox 时：

```text
1. 不得创建新的 payable outbox。
2. 不得生成新的 event_key。
3. 不得调用 ERPNext。
4. 不得改变原 active outbox。
```

## 六、处理策略

### 方案 A：稳定 replay 已有 active outbox（推荐）

当同 statement 已有 active outbox，而请求使用不同 `idempotency_key`：

```text
1. 返回已有 active outbox 摘要。
2. 不新增 outbox。
3. HTTP 200。
4. message 提示已有应付草稿任务。
5. 写操作审计：payable_draft_replay_active_outbox。
```

适用前提：返回不会误导客户端以为新请求创建了新 outbox。响应必须明确 `replayed=true` 或等价字段。

### 方案 B：返回业务冲突（可接受）

当同 statement 已有 active outbox，而请求使用不同 `idempotency_key`：

```text
1. 返回 409。
2. code = FACTORY_STATEMENT_PAYABLE_OUTBOX_ACTIVE。
3. data 包含 existing_outbox_id、existing_status。
4. 不新增 outbox。
5. 写操作失败审计。
```

本项目推荐：

```text
同 idempotency_key + 同 request_hash：replay。
同 statement 已有 active outbox + 不同 idempotency_key：409 FACTORY_STATEMENT_PAYABLE_OUTBOX_ACTIVE。
```

这样语义更清晰，不会把“不同请求”伪装成 replay。

## 七、event_key 口径修正

审计指出当前 `event_key` 包含 `idempotency_key`，导致不同 key 生成不同 event_key，不能阻止重复 outbox。

本任务必须修正：

```text
event_key 不得包含 idempotency_key。
event_key 不得包含 outbox_id/request_id/created_at/operator/attempts。
event_key 必须基于 statement + payable draft 核心业务 payload。
```

推荐：

```text
fspi:<sha256(company|statement_id|statement_no|supplier|net_amount|payable_account|cost_center|posting_date)>
```

如果 `remark` 不影响财务事实，可不纳入 event_key，但必须纳入 `request_hash`。

`request_hash` 继续包含：

```text
statement_id
statement_no
supplier
net_amount
payable_account
cost_center
posting_date
remark
```

## 八、数据库层防重

必须优先增加数据库层保护，防止并发双插。

推荐 PostgreSQL partial unique index：

```sql
CREATE UNIQUE INDEX uk_ly_factory_statement_payable_one_active
ON ly_schema.ly_factory_statement_payable_outbox (statement_id)
WHERE status IN ('pending', 'processing', 'succeeded');
```

如果测试库兼容问题导致 SQLite 无法实现 partial unique，至少必须：

```text
1. PostgreSQL 迁移包含 partial unique index。
2. 服务层在事务内使用行锁或唯一约束冲突 reload。
3. 测试覆盖并发或唯一冲突 reload 场景。
```

唯一冲突处理：

```text
1. 捕获 IntegrityError。
2. rollback 当前 insert。
3. reload 已存在 active outbox。
4. 返回 FACTORY_STATEMENT_PAYABLE_OUTBOX_ACTIVE 或按策略 replay。
5. 不得落为 DATABASE_WRITE_FAILED。
```

## 九、服务层防重顺序

`create_payable_draft_outbox()` 推荐顺序：

```text
1. 动作权限和资源权限校验。
2. 读取并锁定 statement。
3. 校验 statement.status == confirmed。
4. 按 company + statement_id + idempotency_key 查询同 key 历史。
5. 同 key 同 hash replay。
6. 同 key 异 hash 返回 FACTORY_STATEMENT_IDEMPOTENCY_CONFLICT。
7. 查询 statement active payable outbox。
8. 如存在 active outbox，返回 FACTORY_STATEMENT_PAYABLE_OUTBOX_ACTIVE 或稳定 replay，不新增。
9. 构造不含 idempotency_key 的 event_key。
10. insert payable outbox。
11. commit 成功后返回。
```

注意：

```text
同 key replay 必须优先于 active outbox conflict。
```

否则同一请求重试会被误判为 active conflict。

## 十、错误码

必须支持：

```text
FACTORY_STATEMENT_PAYABLE_OUTBOX_ACTIVE
FACTORY_STATEMENT_IDEMPOTENCY_CONFLICT
FACTORY_STATEMENT_INVALID_STATUS
FACTORY_STATEMENT_DATABASE_WRITE_FAILED
FACTORY_STATEMENT_INTERNAL_ERROR
```

`FACTORY_STATEMENT_PAYABLE_OUTBOX_ACTIVE` 响应建议：

```json
{
  "code": "FACTORY_STATEMENT_PAYABLE_OUTBOX_ACTIVE",
  "message": "当前对账单已有应付草稿任务，不能重复生成",
  "data": {
    "existing_outbox_id": 1,
    "existing_status": "pending"
  }
}
```

## 十一、必须补测试

### A. 不同 idempotency_key 不得创建第二条 active outbox

复现：

```text
1. 创建并确认 statement。
2. POST /payable-draft，idempotency_key=manual-pay-1。
3. POST /payable-draft，idempotency_key=manual-pay-2，payload 其他字段相同。
```

断言：

```text
□ 第二次不会创建新 outbox。
□ 数据库同 statement_id 下 active outbox 数量仍为 1。
□ 第二次返回 FACTORY_STATEMENT_PAYABLE_OUTBOX_ACTIVE 或稳定 replay。
□ 不调用 ERPNext。
```

### B. 同 idempotency_key 同 hash 仍 replay

断言：

```text
□ 同 key 同 hash 返回首次 outbox_id。
□ 不误报 FACTORY_STATEMENT_PAYABLE_OUTBOX_ACTIVE。
□ active outbox 数量仍为 1。
```

### C. 同 idempotency_key 异 hash 仍 conflict

断言：

```text
□ 同 key 异 payable_account/cost_center/posting_date/remark 返回 FACTORY_STATEMENT_IDEMPOTENCY_CONFLICT。
□ 不创建第二条 outbox。
```

### D. failed/dead 后策略测试

按实现策略断言：

```text
□ 如果 failed/dead 不算 active，则可重新创建新 outbox。
□ 如果 failed/dead 仍禁止，则返回明确错误码。
□ 策略必须写入交付说明。
```

### E. event_key 不包含 idempotency_key

断言：

```text
□ manual-pay-1 与 manual-pay-2 在相同业务 payload 下生成相同 event_key。
□ event_key 不包含 outbox_id/request_id/created_at/operator。
```

### F. 并发/唯一冲突测试

至少覆盖一种：

```text
□ 模拟 IntegrityError 后 reload existing active outbox，不返回 DATABASE_WRITE_FAILED。
□ 或真实并发两个请求仅落一条 active outbox。
```

### G. 防越界扫描

```text
□ 未调用 internal worker。
□ 未提交 Purchase Invoice。
□ 未创建 Payment Entry/GL Entry。
□ 未修改前端。
□ 未修改 .github/02_源码。
```

## 十二、交付前自测命令

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service

.venv/bin/python -m pytest -q tests/test_factory_statement*.py
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)

rg -n "submit\(|docstatus\s*=\s*1|Payment Entry|GL Entry|create_payment|submit_purchase_invoice" app tests

git diff --name-only -- /Users/hh/Desktop/领意服装管理系统/06_前端 /Users/hh/Desktop/领意服装管理系统/.github /Users/hh/Desktop/领意服装管理系统/02_源码
```

如本任务补了前端 contract 测试，则还必须执行：

```bash
cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc
npm run check:factory-statement-contracts
npm run test:factory-statement-contracts
npm run verify
```

## 十三、交付说明必须包含

```text
1. 修改文件清单。
2. active payable outbox 防重策略：replay 还是 409 conflict。
3. active 状态集合说明。
4. failed/dead 是否允许重新创建说明。
5. event_key 新口径，明确不含 idempotency_key。
6. 数据库唯一约束或并发防重策略说明。
7. 新增测试名称和覆盖点。
8. 自测命令和结果。
9. 明确声明未调用 internal worker。
10. 明确声明未提交 Purchase Invoice、未创建 Payment Entry/GL Entry。
11. 明确声明未修改前端、.github、02_源码。
```

## 十四、下一步门禁

```text
TASK-006E2 审计通过后，才允许重新判断是否进入 TASK-006F。
TASK-006F 不得自动开始，必须由架构师单独下发任务单。
```
