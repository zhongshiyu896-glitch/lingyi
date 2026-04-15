# TASK-006H 加工厂对账单本地封版审计任务单

- 任务编号：TASK-006H
- 模块：加工厂对账单
- 优先级：P0
- 版本：V1.0
- 更新时间：2026-04-15 22:29 CST
- 作者：技术架构师
- 前置依赖：TASK-006G 审计通过，建议进入 TASK-006 本地封版审计
- 任务类型：审计任务单
- 任务边界：只做 TASK-006 本地封版审计，不新增功能、不修改业务代码、不提交运行产物、不宣布生产发布。

## 一、任务目标

对 TASK-006 加工厂对账单模块进行本地封版审计，判断是否可以标记为“本地封版完成”。

审计官需基于：

```text
TASK-006A~F1 任务单
TASK-006A~G 交付证据
TASK-006G 本地封版复审证据
审计记录第 161~172 份及相关日志
前端/后端测试复跑结果
禁入扫描结果
工作区状态与运行产物说明
```

输出本地封版审计结论：

```text
通过：允许架构师记录 TASK-006 本地封版完成
有条件通过：列出必须补证据/修文档项，进入 TASK-006H1
不通过：列出阻断问题，禁止封版
```

## 二、禁止事项

本任务严禁：

```text
修改 06_前端/**
修改 07_后端/**
修改 .github/**
修改 02_源码/**
新增功能
修复业务代码
提交 dist/node_modules/.pytest_cache 等运行产物
宣布生产发布完成
宣布 GitHub hosted runner / required check 平台闭环完成
直接修改 ERPNext 或生产数据
```

如审计发现阻断问题，只输出审计意见，不直接修代码。

## 三、审计输入文件

必须读取：

```text
/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-006G_加工厂对账单本地封版复审证据.md
/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-006F_加工厂对账单封版前证据盘点.md
/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/07_模块设计_加工厂对账单.md
/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/03_技术决策记录.md
/Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录.md
/Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录/审计官会话日志.md
```

建议抽查：

```text
/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-006A_加工厂对账单开发前基线盘点证据.md
/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-006B_加工厂对账单后端模型迁移与草稿API_交付证据.md
/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-006B1_对账草稿重复防护与取消后重建约束整改_交付证据.md
/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-006D_ERPNext应付草稿Outbox集成_交付证据.md
/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-006E_加工厂对账单前端联调与契约门禁_交付证据.md
/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-006F1_CSV公式注入防护整改_交付证据.md
```

## 四、审计重点

### 1. 任务链路完整性

确认 TASK-006A~G 是否形成闭环：

```text
A：设计冻结
B：后端草稿基线
B1：重复防护与取消后重建约束
C：确认/取消/active-scope 语义
C1：create 未知异常兜底
D：ERPNext 应付草稿 outbox
D1：worker/outbox 状态机安全
E：前端联调与契约门禁
E1：前后端 company/payable 摘要契约
E2：同 statement active payable outbox 防重
F：打印导出与封版前证据盘点
F1：CSV 公式注入防护
G：本地封版复审证据
```

每个阶段必须有：

```text
任务单
交付证据或审计输入
审计意见书编号
审计结论
阻断项闭环说明
```

### 2. 后端能力审计

必须确认：

```text
草稿生成按 ly_subcontract_inspection 粒度
active-scope 防重
取消后 inspection 可重建
确认锁定金额
取消释放 inspection
create 未知异常统一错误信封
payable outbox 创建
ERPNext Purchase Invoice 草稿 docstatus=0
worker 服务账号最小权限
worker dry-run 不写外部系统
worker claim due/lease 安全
同 statement active payable outbox 防重
failed/dead 重建未实现且已列为风险
event_key 不含 idempotency_key
权限源 fail closed
操作审计/安全审计覆盖关键路径
```

### 3. 前端能力审计

必须确认：

```text
列表页
详情页
创建 company 必填
确认/取消/生成应付草稿按钮权限控制
active payable outbox 下取消/重复生成 fail closed
payable 状态展示
打印页
CSV 导出
CSV 公式注入防护
factory-statement contract 门禁
```

### 4. 禁止能力审计

必须确认未实现或未暴露：

```text
Purchase Invoice submit/docstatus=1
Payment Entry
GL Entry
前端 ERPNext /api/resource 直连
前端 internal worker 调用
裸 fetch
后端导出接口
failed/dead payable outbox 重建/reset
对账调整单
自动反冲/红冲
```

### 5. 证据质量审计

必须确认：

```text
TASK-006G 证据没有把本地验证夸大为生产发布
没有把本地验证夸大为 GitHub required check 平台闭环
dist/ 等运行产物未被纳入交付承诺
历史未跟踪文件和运行产物风险已披露
剩余风险完整且未伪装为已解决
```

## 五、必须复跑命令

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

### 工作区和运行产物

```bash
cd /Users/hh/Desktop/领意服装管理系统

git status --short
git diff --name-only -- 06_前端 07_后端 .github 02_源码
find . -maxdepth 4 \( -name dist -o -name node_modules -o -name .pytest_cache -o -name coverage \) -print
```

说明：

```text
1. `rg` 合法命中必须逐条解释。
2. `dist/` 如存在，必须标为运行产物，不得作为封版提交内容。
3. 工作区历史未跟踪文件不得影响本地封版结论，但必须记录风险。
```

## 六、审计输出要求

审计报告追加到：

```text
/Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录.md
```

审计日志追加到：

```text
/Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录/审计官会话日志.md
```

日志格式沿用现有规则。

审计意见必须包含：

```text
1. 审计意见书编号。
2. 审计结论：通过 / 有条件通过 / 不通过。
3. 是否允许架构师记录 TASK-006 本地封版完成。
4. 问题项统计：高/中/低。
5. 风险项清单。
6. 复跑命令结果。
7. 禁止能力扫描结论。
8. 工作区和运行产物说明。
9. 下一步建议。
```

## 七、通过标准

只有同时满足以下条件，才允许结论为“通过”：

```text
□ TASK-006A~G 任务链路完整。
□ 所有高危/中危阻断项均已闭环。
□ 后端 factory statement 测试通过。
□ 前端 factory statement contract/verify/audit 通过。
□ Purchase Invoice submit、Payment Entry、GL Entry、internal worker 前端调用、ERPNext 直连均未出现。
□ CSV 公式注入防护通过。
□ TASK-006G 证据风险披露完整。
□ 未发现新增业务代码 diff 或未解释的运行产物混入。
```

## 八、不通过或有条件通过处理

如果发现问题：

```text
高危：结论不通过，禁止本地封版，要求 TASK-006H1 修复。
中危：原则上有条件通过或不通过，视是否影响封版可信性。
低危：可有条件通过，但必须明确后续补证据或文档修正。
```

如需修复，只输出审计意见，不直接修改代码。

## 九、下一步门禁

```text
TASK-006H 审计通过后，架构师才允许输出 TASK-006 本地封版完成记录。
若 TASK-006H 有条件通过或不通过，必须先下发 TASK-006H1 或对应修复任务单。
```
