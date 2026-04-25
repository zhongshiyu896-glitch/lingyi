# TASK-017A 采购管理边界设计冻结 工程任务单

## 1. 基本信息

- 任务编号：TASK-017A
- 任务名称：采购管理边界设计冻结
- 角色：B Engineer
- 优先级：P1
- 状态：待执行
- 前置依赖：TASK-016C 审计通过
- 任务性质：docs-only

## 2. 任务目标

在既有 `TASK-017A` 采购设计文档基础上，补齐并冻结采购管理主链的统一边界口径，形成可送 C 正式审计的 docs-only 产物。

本轮通过后，只允许进入 `TASK-017B` 设计，不允许直接进入任何采购实现任务。

## 3. 输入真相源

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/Sprint3_任务清单.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-017A_采购管理边界设计.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-017_采购管理边界设计.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-016A_财务管理边界设计.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-016B_Payment Entry Adapter设计.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-016C_财务只读报表设计.md`

## 4. 输出文件

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-017A_采购管理边界设计.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md`

## 5. 允许修改范围

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-017A_采购管理边界设计.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md`

## 6. 严格禁止范围

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-017_采购管理边界设计.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-017A_采购管理边界设计冻结_工程任务单.md`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/**`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/**`
- `/Users/hh/Desktop/领意服装管理系统/.github/**`
- `/Users/hh/Desktop/领意服装管理系统/02_源码/**`
- `/Users/hh/Documents/Playground 2/LOOP_STATE.md`
- `/Users/hh/Desktop/领意服装管理系统/00_交接与日志/HANDOVER_STATUS.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/架构师会话日志.md`
- 任意审计官日志
- 任意远端、PR、push、发布动作

## 7. 执行要求

1. 以 `TASK-017A_采购管理边界设计.md` 作为唯一正式文档。
2. `TASK-017_采购管理边界设计.md` 仅作为旧稿参考，不得修改，不得作为本轮正式输出。
3. 保留现有已成立内容，只补会导致 C 审计打回的缺口，不要整篇重写。
4. 文档必须显式冻结采购主链边界，至少覆盖：
   - Purchase Request
   - Purchase Order
   - Purchase Receipt
   - Purchase Invoice 与采购侧关系
   - Supplier 主数据
   - Item / Warehouse / Account / Cost Center 的只读依赖关系
5. 文档必须新增或补齐统一的“三层能力冻结口径”，不能继续使用分散表述替代统一合同。
6. 三层能力口径至少覆盖：
   - Supplier
   - Purchase Request
   - Purchase Order draft/create
   - Purchase Order confirm/cancel
   - Purchase Receipt
   - Purchase Invoice（采购侧仅引用，不偷渡财务写入）
7. 文档必须明确写死以下结论：
   - 本轮通过只代表采购设计冻结成立
   - 不代表实现放行
   - 不代表联调、提测、上线、生产写入放行
   - `TASK-017A` 通过后仅允许进入 `TASK-017B` 设计
   - 不允许直接进入任何采购实现任务
8. 文档必须冻结以下内容：
   - 动作权限
   - 资源字段
   - ERPNext DocType 边界
   - Adapter / Outbox / fail-closed 约束
   - 状态机建议
   - 审计要求
   - 前端门禁
   - 生产发布前置条件
9. 文档必须明确写死以下原则：
   - 前端不得直连 ERPNext `/api/resource`
   - 采购写链不得绕过 `TASK-008` fail-closed adapter
   - 采购写链不得绕过 `TASK-009` outbox
   - 未经后续单独任务和单独审计，不得开放 Purchase Order / Purchase Receipt / Purchase Invoice 生产写入
10. 涉及财务或库存时，只允许写职责边界和接口边界，不允许偷渡实现放行。
11. 在 `工程师会话日志.md` 追加一条完成记录，明确：
   - 本轮为 `TASK-017A`
   - docs-only
   - 仅更新采购管理边界设计文档
   - 未修改前后端代码、测试代码、控制面文件、审计日志
12. 如果你判断必须修改任何禁止范围文件才能完成，请立即停止并按 `BLOCKED` 回交，不得越界改动。

## 8. 本轮必须回答并写清的问题

1. 采购模块在 Sprint 3 当前只冻结到什么边界，哪些对象仍然只是设计，不允许实现。
2. Purchase Request / Purchase Order / Purchase Receipt / Supplier / Purchase Invoice 在采购主链中的职责边界分别是什么。
3. 哪些能力属于只读能力。
4. 哪些能力最多只到候选写能力。
5. 哪些能力明确仍是生产写冻结。
6. 采购写链未来若要落地，必须经过哪些公共基座：
   - fail-closed adapter
   - outbox
   - 审计
   - 资源权限
7. 前端当前绝对不能做什么。
8. `TASK-017A` 通过后，下一个唯一允许进入的任务是什么。
9. 为什么本轮不能直接进入采购实现。

## 9. 建议文档结构

- 1. 设计目标与冻结范围
- 2. 采购模块总边界
- 3. Purchase Request 边界
- 4. Purchase Order 边界
- 5. Purchase Receipt 边界
- 6. Purchase Invoice 与采购侧关系边界
- 7. Supplier 主数据边界
- 8. ERPNext DocType 边界
- 9. 权限与资源字段冻结
- 10. 前端门禁与 fail-closed 约束
- 11. 三层能力冻结统一矩阵
- 12. 生产发布前置条件
- 13. 结论边界与下一步门禁

## 10. 验证命令

```bash
cd /Users/hh/Desktop/领意服装管理系统

test -f '03_需求与设计/01_架构设计/TASK-017A_采购管理边界设计.md'
test -f '03_需求与设计/02_开发计划/工程师会话日志.md'

git diff --name-only -- \
  '03_需求与设计/01_架构设计/TASK-017A_采购管理边界设计.md' \
  '03_需求与设计/02_开发计划/工程师会话日志.md'

git diff --name-only -- \
  '03_需求与设计/01_架构设计/TASK-017_采购管理边界设计.md' \
  '06_前端' \
  '07_后端' \
  '.github' \
  '02_源码' \
  '00_交接与日志' \
  '03_需求与设计/05_审计记录'

git diff --check -- \
  '03_需求与设计/01_架构设计/TASK-017A_采购管理边界设计.md' \
  '03_需求与设计/02_开发计划/工程师会话日志.md'

rg -n '三层能力|只读能力|候选写能力|生产写能力|TASK-017B|不允许直接进入实现|Purchase Request|Purchase Order|Purchase Receipt|Supplier|Purchase Invoice|Outbox|fail-closed|前端门禁|生产发布前置条件' \
  '03_需求与设计/01_架构设计/TASK-017A_采购管理边界设计.md'
```

## 11. 回交格式

```text
STATUS: READY_FOR_AUDIT
TASK_ID: TASK-017A
ROLE: B Engineer

CHANGED_FILES:
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-017A_采购管理边界设计.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md

EVIDENCE:
- 已补齐哪些章节
- 三层能力冻结统一矩阵落在哪些段落
- 已明确写死“仅允许进入 TASK-017B 设计，不允许直接进入实现”的段落
- 已明确哪些对象是只读、候选写、生产写冻结
- 已明确 Adapter / Outbox / fail-closed / 审计 / 前端门禁 / 发布前置条件的段落
- 已说明旧稿 `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-017_采购管理边界设计.md` 未修改

VERIFICATION:
- 逐条贴出验证命令结果摘要

BLOCKERS:
- 无 / 若有则精确说明

NEXT_ROLE:
- C Auditor
```

## 12. 完成定义

- `TASK-017A_采购管理边界设计.md` 已补齐并达到可审计状态
- 文档已形成统一三层能力冻结口径
- 文档已明确写死 `TASK-017A` 通过后仅允许进入 `TASK-017B` 设计
- 文档已明确禁止直接进入任何采购实现任务
- 工程师会话日志已追加完成记录
- 未修改任何前后端代码、测试代码、控制面文件、审计日志、旧稿 `TASK-017_采购管理边界设计.md`
