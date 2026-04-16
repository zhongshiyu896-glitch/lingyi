# TASK-010A 前端写入口门禁公共框架设计冻结工程任务单

- 任务编号：TASK-010A
- 角色：工程师
- 优先级：P1
- 前置依赖：TASK-009D 审计通过（HEAD `a5e64146bfd7954d5daaa309dbf2e4769a5db237`）
- 任务类型：设计冻结（仅文档，不写代码）

## 一、任务目标

冻结 Sprint 2 前端写入口门禁公共框架设计，将 TASK-005 style-profit 与 TASK-006 factory-statement 契约门禁经验抽象为可复用规范，为 TASK-010B 工程实现和 TASK-011/TASK-012 前端接入提供统一前置约束。

## 二、任务边界

### 2.1 允许输出
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-010_前端写入口门禁公共框架设计.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-010A_前端写入口门禁公共框架设计冻结_工程任务单.md`

### 2.2 允许读取
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/Sprint2_架构规范.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/Sprint1_复盘报告.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/Sprint2_任务清单.md`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-factory-statement-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-factory-statement-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/package.json`

### 2.3 禁止修改
- `/Users/hh/Desktop/领意服装管理系统/06_前端/**`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/**`
- `/Users/hh/Desktop/领意服装管理系统/.github/**`
- `/Users/hh/Desktop/领意服装管理系统/02_源码/**`

## 三、必须冻结内容

### 3.1 现状梳理
必须输出并对比：
1. style-profit 门禁现状。
2. factory-statement 门禁现状。
3. 已出现绕过类型汇总。
4. 当前脚本不可复用点。
5. 当前 verify 接入现状。

### 3.2 公共框架规范
必须冻结：
1. 统一配置结构（`module`、`surface`、`allowedApis`、`forbiddenApis`、`forbiddenActions`、`allowedReadOnlyActions`）。
2. 统一扫描范围（`api/views/router/stores/components/utils`）。
3. 统一规则编号方案。
4. AST 优先策略与正则补充边界。
5. 默认 fail-closed 与显式白名单策略。
6. 统一报告输出格式。

### 3.3 统一规则清单
必须包含：
1. 只读模块规则。
2. 写入口模块规则。
3. internal API / run-once / worker 禁入规则。
4. ERPNext `/api/resource` 直连禁入规则。
5. 动态执行（`eval/Function/timer-string`）禁入规则。
6. Worker / dynamic import 高危加载禁入规则。
7. 导出安全与公式注入规则。

### 3.4 Fixture 规范
必须冻结：
1. positive/negative fixture 命名规范。
2. 每条规则至少一正一反。
3. 审计绕过样例必须固化为 negative fixture。
4. 反向用例最小覆盖矩阵（direct/alias/destructure/call-apply-bind/computed/runtime mutation）。

### 3.5 模块接入规范
必须明确：
1. TASK-011 销售/库存只读集成接入方式。
2. TASK-012 质量管理基线接入方式。
3. 新模块前端页面开发前必须先补 contract config + fixture。

### 3.6 迁移计划
必须冻结：
1. style-profit 迁移到公共框架路径。
2. factory-statement 迁移到公共框架路径。
3. 保留旧命令入口，旧脚本 wrapper 化。
4. 行为不回退与场景数不回退要求。

### 3.7 TASK-010B 实现边界
必须明确：
1. 允许创建公共 contract engine。
2. 允许旧脚本 wrapper 化。
3. 允许新增公共 fixture 测试。
4. 禁止修改业务页面逻辑。
5. 禁止提前进入 TASK-011/TASK-012。

## 四、审计前置要求

审计官必须确认：
1. 文档明确 AST 优先，不再以正则堆叠作为主策略。
2. 文档明确默认 fail closed、白名单显式放行。
3. 文档明确 internal/ERPNext/dynamic/Worker/CSV 风险统一门禁。
4. 文档明确 style-profit 与 factory-statement 的可执行迁移路径。
5. 文档明确 TASK-011/TASK-012 门禁前置条件。
6. 文档明确 TASK-010B 边界，不跨任务实现。

## 五、验收标准

- [ ] 已输出 `TASK-010_前端写入口门禁公共框架设计.md`
- [ ] 已输出 `TASK-010A_前端写入口门禁公共框架设计冻结_工程任务单.md`
- [ ] 文档明确 AST 优先、fail closed、fixture 必选
- [ ] 文档明确 style-profit/factory-statement 迁移路径
- [ ] 文档明确 TASK-011/TASK-012 前置接入要求
- [ ] 未修改前端业务代码
- [ ] 未修改后端业务代码
- [ ] 未修改 `.github`
- [ ] 未修改 `02_源码`
- [ ] 已追加架构师会话日志

## 六、验证命令

```bash
cd /Users/hh/Desktop/领意服装管理系统
test -f "03_需求与设计/01_架构设计/TASK-010_前端写入口门禁公共框架设计.md"
test -f "03_需求与设计/02_开发计划/TASK-010A_前端写入口门禁公共框架设计冻结_工程任务单.md"
git diff --name-only -- "06_前端" "07_后端" ".github" "02_源码"
git diff --cached --name-only
```

## 七、执行约束

1. 本任务只做文档冻结，不写业务代码。
2. 不提交，不 push，不配置 remote。
3. 不进入 TASK-010B 实现阶段。
4. 不进入 TASK-011/TASK-012。

## 八、交付回报格式

```text
TASK-010A 执行完成。
结论：待审计

已输出：
- /03_需求与设计/01_架构设计/TASK-010_前端写入口门禁公共框架设计.md
- /03_需求与设计/02_开发计划/TASK-010A_前端写入口门禁公共框架设计冻结_工程任务单.md

本次只输出文档，未修改前端/后端/.github/02_源码。
未提交、未 push。
```
