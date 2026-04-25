# TASK-016A 财务管理边界设计冻结 工程任务单

## 1. 基本信息

- 任务编号：TASK-016A
- 任务名称：财务管理边界设计冻结
- 角色：架构师
- 优先级：P0
- 状态：待执行
- 前置依赖：TASK-013C 审计通过

## 2. 任务目标

输出财务管理边界设计，冻结 Payment / GL / AR / AP 的权限、资源字段、ERPNext 集成、outbox 与审计边界。

## 3. 允许范围

1. 仅允许新增或修改：
   - `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-016A_财务管理边界设计.md`
   - `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-016A_财务管理边界设计冻结_工程任务单.md`
2. 允许引用 TASK-007~010 的公共基座。

## 4. 禁止范围

1. 禁止写业务代码。
2. 禁止创建 Payment Entry / GL Entry / Journal Entry。
3. 禁止实现 ERPNext 写入。
4. 禁止修改 `06_前端/**`、`07_后端/**`、`.github/**`、`02_源码/**`。
5. 禁止 push / remote / PR / 生产发布声明。

## 5. 必须输出

1. 财务范围矩阵。
2. 权限动作与资源字段。
3. ERPNext DocType 边界。
4. Outbox 写入规则。
5. 前端门禁要求。
6. 审计关注点。

## 6. 验证命令

```bash
cd /Users/hh/Desktop/领意服装管理系统
test -f '03_需求与设计/01_架构设计/TASK-016A_财务管理边界设计.md'
test -f '03_需求与设计/02_开发计划/TASK-016A_财务管理边界设计冻结_工程任务单.md'
git diff --name-only -- '06_前端' '07_后端' '.github' '02_源码'
git diff --cached --name-only
git diff --check -- '03_需求与设计/01_架构设计/TASK-016A_财务管理边界设计.md' '03_需求与设计/02_开发计划/TASK-016A_财务管理边界设计冻结_工程任务单.md'
```

## 7. 完成回报

```text
TASK-016A 执行完成。
结论：待审计
是否写业务代码：否
是否修改前端/后端/.github/02_源码：否
是否 push/remote/PR：否
```
