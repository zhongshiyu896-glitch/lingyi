# TASK-006G 加工厂对账单本地封版复审工程任务单

- 任务编号：TASK-006G
- 模块：加工厂对账单
- 优先级：P0
- 版本：V1.0
- 更新时间：2026-04-15 22:08 CST
- 作者：技术架构师
- 前置依赖：TASK-006F1 审计通过，允许进入 TASK-006G 前置任务单/审计放行流程
- 任务边界：只做 TASK-006 本地封版复审证据汇总和复核，不新增功能、不修改前端业务、不修改后端业务、不修改迁移、不提交运行产物。

## 一、任务目标

对 TASK-006 加工厂对账单模块进行本地封版复审，形成可交给审计官复审的证据文档。

本任务只做：

1. 汇总 TASK-006A~F1 全链路交付物。
2. 汇总审计意见书编号、结论和阻断项闭环情况。
3. 复跑必要的前端、后端、本地禁入扫描命令。
4. 核验打印/导出/CSV 安全、payable outbox 防重、worker 安全、权限门禁和错误信封。
5. 明确剩余风险和不得发布能力。
6. 输出“建议 TASK-006 进入本地封版审计”或“暂不建议封版”的结论。

不得自行宣布：

```text
TASK-006 已封版通过
生产发布通过
平台 CI/Required Check 通过
ERPNext 生产环境已验证
```

## 二、允许新增/修改文件

```text
/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-006G_加工厂对账单本地封版复审证据.md
/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-006G_加工厂对账单本地封版复审_交付证据.md
```

如需要同步修正上一份封版前证据盘点中的明显错字或命令结果，允许最小修改：

```text
/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-006F_加工厂对账单封版前证据盘点.md
```

## 三、禁止修改文件

```text
/Users/hh/Desktop/领意服装管理系统/06_前端/**
/Users/hh/Desktop/领意服装管理系统/07_后端/**
/Users/hh/Desktop/领意服装管理系统/.github/**
/Users/hh/Desktop/领意服装管理系统/02_源码/**
/Users/hh/Desktop/领意服装管理系统/dist/**
/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/dist/**
```

禁止提交或纳入证据基线：

```text
dist/
.pytest_cache/
node_modules/
.pytest-postgresql-*.xml
coverage/
临时探针文件
历史未跟踪业务代码
```

## 四、复审内容

### 1. 任务链路表

证据文档必须列出：

```text
TASK-006A 开发前基线盘点与设计冻结
TASK-006B 后端模型迁移与草稿 API
TASK-006B1 重复防护与取消后重建约束整改
TASK-006C 确认取消与 active-scope 语义收口
TASK-006C1 create 路由未知异常兜底修复
TASK-006D ERPNext 应付草稿 outbox 集成
TASK-006D1 worker/outbox 状态机安全整改
TASK-006E 前端联调与契约门禁
TASK-006E1 前后端契约与 payable 摘要整改
TASK-006E2 同 statement active payable outbox 防重
TASK-006F 打印导出与封版前证据盘点
TASK-006F1 CSV 公式注入防护整改
```

每行必须包含：

```text
任务编号
任务目标
对应任务单路径
对应证据路径
审计意见书编号
审计结论
是否闭环
```

### 2. 后端能力核验

必须核验并记录：

```text
草稿生成
同范围 active-scope 防重
取消后重建
确认
取消释放 inspection
create 未知异常统一错误信封
payable outbox 创建
ERPNext Purchase Invoice 草稿创建 docstatus=0
worker 服务账号权限
worker dry-run
worker claim due/lease 安全
同 statement active payable outbox 防重
event_key 不含 idempotency_key
权限源 fail closed
操作审计/安全审计
```

### 3. 前端能力核验

必须核验并记录：

```text
列表页
详情页
创建草稿 company 必填
确认按钮权限
取消按钮 active payable outbox fail closed
生成应付草稿只创建 outbox
payable 状态展示
打印页
CSV 导出
CSV 公式注入防护
factory-statement contract 门禁
```

### 4. 禁止能力核验

必须扫描并记录未出现：

```text
Purchase Invoice submit/docstatus=1
Payment Entry
GL Entry
ERPNext /api/resource 前端直连
internal worker 前端调用
裸 fetch
后端导出接口
failed/dead payable outbox 重建/reset
对账调整单
自动反冲/红冲
```

### 5. 剩余风险

至少记录：

```text
datetime.utcnow() deprecation warnings 仍存在
failed/dead payable outbox 重建策略未实现，后续需单独任务
本地验证不等同生产 ERPNext 环境验证
本地验证不等同 GitHub hosted runner / required check 平台闭环
工作区仍有历史未跟踪文件与运行产物，提交必须白名单暂存
如果后续改 XLSX 或服务端导出，需要重新复核公式注入边界
```

## 五、必须执行命令

### 后端

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service

.venv/bin/python -m pytest -q tests/test_factory_statement*.py
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)

rg -n "submit\(|docstatus\s*=\s*1|Payment Entry|GL Entry|create_payment|submit_purchase_invoice|reset_payable|rebuild_payable|dead.*rebuild" app tests
```

### 前端

```bash
cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc

npm run check:factory-statement-contracts
npm run test:factory-statement-contracts
npm run verify
npm audit --audit-level=high

rg -n "fetch\(|axios|/api/resource|factory-statements/internal|run-once|submitPurchaseInvoice|Payment Entry|GL Entry|createPaymentEntry|createGlEntry" src scripts
rg -n "parseFloat\(|Number\(" src/views/factory_statement src/utils scripts
```

### 禁改与运行产物

```bash
cd /Users/hh/Desktop/领意服装管理系统

git diff --name-only -- 06_前端 07_后端 .github 02_源码
git status --short
```

说明：

```text
1. 如果 npm run verify 生成 dist/，必须在证据中标明 dist/ 是运行产物，不得纳入提交。
2. 如果 rg 命中合法 denylist、测试 fixture 或文档，必须逐条解释。
3. 如果发现新的业务代码 diff，不得继续宣称封版建议，必须先回报。
```

## 六、证据文档结构

`TASK-006G_加工厂对账单本地封版复审证据.md` 必须包含：

```text
# TASK-006G 加工厂对账单本地封版复审证据

## 1. 基本信息
- 复审时间
- 当前 HEAD
- 复审人
- 结论

## 2. 任务链路与审计闭环
表格：TASK-006A~F1

## 3. 后端能力核验
- 已完成能力
- 自测命令
- 结果

## 4. 前端能力核验
- 已完成能力
- 自测命令
- 结果

## 5. 禁止能力扫描
- 扫描命令
- 命中解释
- 结论

## 6. 打印/导出安全核验
- 打印数据来源
- CSV 金额不重算
- CSV 公式注入防护

## 7. 权限与审计核验
- 动作权限
- 资源权限
- internal worker denylist
- 安全审计/操作审计

## 8. 剩余风险
逐条列出

## 9. 封版建议
只能写：建议进入 TASK-006 本地封版审计 / 暂不建议封版
```

## 七、验收标准

```text
□ 输出 TASK-006G 本地封版复审证据文档。
□ TASK-006A~F1 任务链路和审计结论完整。
□ 后端 factory statement 测试复跑并记录结果。
□ 前端 factory statement contract/verify/audit 复跑并记录结果。
□ 禁止能力扫描完整并解释合法命中。
□ 明确 dist/ 等运行产物不得纳入提交。
□ 未修改 06_前端、07_后端、.github、02_源码。
□ 未新增业务功能。
□ 未自行宣布生产发布或平台闭环。
```

## 八、交付说明必须包含

```text
1. 证据文档路径。
2. 复审结论。
3. 后端测试结果。
4. 前端测试结果。
5. 禁改扫描结果。
6. 运行产物说明。
7. 剩余风险清单。
8. 明确声明未修改前端/后端业务代码、.github、02_源码。
```

## 九、下一步门禁

```text
TASK-006G 交付后必须交审计官复审。
审计通过后，才允许架构师输出 TASK-006 本地封版完成记录或继续下发 TASK-006G1 证据修正任务。
```
