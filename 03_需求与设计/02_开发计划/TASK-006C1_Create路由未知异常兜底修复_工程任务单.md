# TASK-006C1 Create 路由未知异常兜底修复工程任务单

- 任务编号：TASK-006C1
- 模块：加工厂对账单
- 优先级：P0
- 版本：V1.0
- 更新时间：2026-04-15 18:50 CST
- 作者：技术架构师
- 前置依赖：TASK-006C 审计不通过，审计意见指出 create 路由未知异常兜底二次抛 `NameError`
- 任务边界：只修复 `POST /api/factory-statements/` 未知异常兜底路径和防回归测试；不得进入 TASK-006D，不得实现 ERPNext Purchase Invoice、payable-draft、前端页面、打印页面。

## 一、任务目标

修复 `create_factory_statement()` 路由未知异常兜底分支中引用未定义变量 `statement_id` 的问题，确保服务层抛出未知异常时：

1. 不再二次抛出 `NameError`。
2. 返回统一错误信封 `FACTORY_STATEMENT_INTERNAL_ERROR`。
3. 失败审计仍能写入或按既有审计失败策略 fail closed。
4. 事务按现有规则 rollback。
5. 不影响 confirm/cancel 已通过的主路径。

## 二、审计复现问题

审计官复现方式：临时 patch `FactoryStatementService.create_draft()` 抛 `RuntimeError`。

当前异常结果：

```text
NameError: name 'statement_id' is not defined
```

问题位置：

```text
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/factory_statement.py:253
```

根因：

```text
create_factory_statement() 的 except Exception 分支引用了未定义变量 statement_id。
```

## 三、允许修改文件

```text
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/factory_statement.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_factory_statement*.py
/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-006C1_Create路由未知异常兜底修复_交付证据.md
```

如现有测试结构要求精确文件，优先追加到：

```text
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_factory_statement_api.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_factory_statement_audit.py
```

## 四、禁止修改文件

```text
/Users/hh/Desktop/领意服装管理系统/06_前端/**
/Users/hh/Desktop/领意服装管理系统/.github/**
/Users/hh/Desktop/领意服装管理系统/02_源码/**
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_*.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/factory_statement_payable*.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/versions/**
```

本任务禁止新增或实现：

```text
POST /api/factory-statements/{id}/payable-draft
ERPNext Purchase Invoice 创建
ERPNext /api/resource/Purchase Invoice 调用
前端页面
打印页面
对账调整单
付款/Payment Entry/GL Entry
```

## 五、实现要求

### 1. 修复 create 路由兜底变量

`create_factory_statement()` 必须保证 `except Exception` 分支不引用未定义变量。

建议方案：

```text
1. 在 try 前声明 statement_id = None，或直接在未知异常兜底审计中使用 resource_id=None。
2. 只有在 service 已成功返回 statement 后，才允许使用真实 statement.id。
3. create 阶段未知异常通常还没有可靠 statement_id，不得伪造 statement_id。
```

### 2. 统一错误信封

当 `FactoryStatementService.create_draft()` 或 create 路由内部发生未知异常时，响应必须保持统一错误信封：

```json
{
  "code": "FACTORY_STATEMENT_INTERNAL_ERROR",
  "message": "加工厂对账单处理失败",
  "data": null
}
```

HTTP 状态码按项目既有约定执行；如已有系统错误为 `500`，保持 `500`。

### 3. 失败审计

未知异常兜底必须尝试写操作失败审计，审计字段建议：

```text
module=factory_statement
action=create
resource_type=factory_statement
resource_id=null
result=failed
error_code=FACTORY_STATEMENT_INTERNAL_ERROR
operator=当前真实用户
request_id=规范化后的 request_id
```

要求：

```text
1. 审计记录不得依赖 statement_id 已存在。
2. 审计失败不得覆盖原始业务错误码为 NameError。
3. 日志不得输出 Authorization、Cookie、Token、Secret、Password、SQL 原文。
```

### 4. 事务处理

未知异常路径必须按现有事务规范 rollback。

要求：

```text
1. create_draft 抛 RuntimeError 后不得落 statement。
2. 不得锁定 inspection。
3. 不得产生 partial statement item。
4. 不得调用 ERPNext。
```

## 六、必须补测试

### 测试 1：create_draft 未知异常不二次抛 NameError

构造：

```text
mock/patch FactoryStatementService.create_draft 抛 RuntimeError("boom")
调用 POST /api/factory-statements/
```

断言：

```text
1. 响应不是 NameError。
2. 响应 code = FACTORY_STATEMENT_INTERNAL_ERROR。
3. HTTP 状态码符合系统错误约定。
4. response body 是统一错误信封。
5. 未创建 ly_factory_statement 记录。
6. 未创建 ly_factory_statement_item 记录。
```

### 测试 2：未知异常失败审计不依赖 statement_id

断言：

```text
1. 审计 service 被调用，或安全/操作审计表中存在失败记录。
2. resource_id 允许为空。
3. error_code = FACTORY_STATEMENT_INTERNAL_ERROR。
4. 日志/审计 payload 不包含 RuntimeError 明文敏感栈或 SQL 原文。
```

### 测试 3：已通过路径不回退

至少保留并复跑：

```text
1. confirm/cancel 主路径。
2. confirm/cancel 幂等 replay/conflict。
3. cancel 释放 inspection。
4. cancel 后可重建。
5. payable_draft_created 禁止 cancel。
6. Purchase Invoice / payable-draft 禁入扫描。
```

## 七、验收标准

```text
□ POST /api/factory-statements/ 在 create_draft 抛 RuntimeError 时返回 FACTORY_STATEMENT_INTERNAL_ERROR。
□ 该异常路径不再抛 NameError。
□ 该异常路径能写失败审计，且不依赖 statement_id。
□ 该异常路径事务 rollback，不落半条 statement/item/inspection 锁定。
□ TASK-006C 已通过的 confirm/cancel 测试继续通过。
□ 未新增 /api/factory-statements/{id}/payable-draft。
□ 未调用 ERPNext Purchase Invoice。
□ 未修改前端、.github、02_源码。
```

## 八、交付前自测命令

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service

.venv/bin/python -m pytest -q tests/test_factory_statement*.py
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)

rg -n "payable-draft|Purchase Invoice|/api/resource/Purchase Invoice|create_purchase_invoice|tabPurchase Invoice" app tests

git diff --name-only -- /Users/hh/Desktop/领意服装管理系统/06_前端 /Users/hh/Desktop/领意服装管理系统/.github /Users/hh/Desktop/领意服装管理系统/02_源码
```

说明：`rg` 扫描如命中历史允许文件，交付说明必须逐条解释；不得出现 TASK-006D 新实现。

## 九、交付说明必须包含

```text
1. 修改文件清单。
2. 修复点说明：statement_id 未定义如何消除。
3. 新增测试名称和覆盖点。
4. 自测命令和结果。
5. 明确声明未实现 payable-draft。
6. 明确声明未创建 ERPNext Purchase Invoice。
7. 明确声明未修改前端、.github、02_源码。
```

## 十、下一步门禁

```text
TASK-006C1 审计通过后，才允许进入 TASK-006D。
TASK-006D 才允许开始 ERPNext 应付草稿边界设计/实现。
```
