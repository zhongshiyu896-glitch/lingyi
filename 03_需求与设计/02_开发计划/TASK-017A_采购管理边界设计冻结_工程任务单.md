# TASK-017A 采购管理边界设计冻结 工程任务单

## 1. 基本信息

- 任务编号：TASK-017A
- 任务名称：采购管理边界设计冻结
- 角色：架构师
- 优先级：P1
- 状态：待执行
- 前置依赖：TASK-013C 审计通过

## 2. 任务目标

输出采购管理边界设计，冻结 PO / PR / Supplier / Purchase Receipt 的权限、资源、ERPNext 边界、状态机与审计要求。

## 3. 允许范围

1. 仅允许新增或修改：
   - `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-017_采购管理边界设计.md`
   - `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-017A_采购管理边界设计冻结_工程任务单.md`
2. 允许引用 TASK-007~010 公共基座。

## 4. 禁止范围

1. 禁止写业务代码。
2. 禁止创建 Purchase Order / Purchase Receipt。
3. 禁止生产 ERPNext 写入。
4. 禁止修改 `06_前端/**`、`07_后端/**`、`.github/**`、`02_源码/**`。
5. 禁止 push / remote / PR / 生产发布。

## 5. 必须输出

1. 采购模块范围。
2. 权限动作。
3. 资源字段。
4. ERPNext DocType 边界。
5. 状态机建议。
6. Outbox 与审计要求。

## 6. 验证命令

```bash
cd /Users/hh/Desktop/领意服装管理系统
test -f '03_需求与设计/01_架构设计/TASK-017_采购管理边界设计.md'
test -f '03_需求与设计/02_开发计划/TASK-017A_采购管理边界设计冻结_工程任务单.md'
git diff --name-only -- '06_前端' '07_后端' '.github' '02_源码'
git diff --cached --name-only
git diff --check -- '03_需求与设计/01_架构设计/TASK-017_采购管理边界设计.md' '03_需求与设计/02_开发计划/TASK-017A_采购管理边界设计冻结_工程任务单.md'
```

## 7. 完成回报

```text
TASK-017A 执行完成。
结论：待审计
是否写业务代码：否
是否修改前端/后端/.github/02_源码：否
是否 push/remote/PR：否
```
