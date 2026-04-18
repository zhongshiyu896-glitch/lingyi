# TASK-015A ERPNext 生产联调设计冻结 工程任务单

## 1. 基本信息

- 任务编号：TASK-015A
- 任务名称：ERPNext 生产联调设计冻结
- 角色：架构师
- 优先级：P0
- 状态：待执行
- 前置依赖：TASK-014A 已恢复输出；B-1~B-6 已通过；TASK-014C 仍冻结

## 2. 任务目标

输出 ERPNext 生产联调设计方案，冻结只读联调、沙箱写入联调、生产写入禁止边界、账号权限清单、主数据清单与 evidence 模板。

## 3. 允许范围

1. 仅允许修改或新增以下文档：
   - `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-015_ERPNext生产联调设计.md`
   - `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-015A_ERPNext生产联调设计冻结_工程任务单.md`
2. 允许引用 TASK-007~010、TASK-014A、REL-004 的本地封版结论。
3. 允许声明“设计冻结待审计”。

## 4. 禁止范围

1. 禁止连接 ERPNext 生产环境。
2. 禁止写业务代码。
3. 禁止修改 `06_前端/**`、`07_后端/**`、`.github/**`、`02_源码/**`。
4. 禁止提交、push、remote、PR。
5. 禁止声明 Hosted Runner / required checks / 生产发布已闭环。
6. 禁止开放生产写入、Payment Entry、GL Entry、Purchase Invoice submit。

## 5. 必须输出

1. 设计文档必须包含环境矩阵、账号权限清单、主数据清单、只读联调范围、沙箱写入范围、fail-closed 要求、证据模板。
2. 必须明确 TASK-014C 仍冻结。
3. 必须明确 TASK-015B 只能只读联调。

## 6. 验证命令

```bash
cd /Users/hh/Desktop/领意服装管理系统
test -f '03_需求与设计/01_架构设计/TASK-015_ERPNext生产联调设计.md'
test -f '03_需求与设计/02_开发计划/TASK-015A_ERPNext生产联调设计冻结_工程任务单.md'
git diff --name-only -- '06_前端' '07_后端' '.github' '02_源码'
git diff --cached --name-only
git diff --check -- '03_需求与设计/01_架构设计/TASK-015_ERPNext生产联调设计.md' '03_需求与设计/02_开发计划/TASK-015A_ERPNext生产联调设计冻结_工程任务单.md'
```

## 7. 完成回报

```text
TASK-015A 执行完成。
结论：待审计
是否写业务代码：否
是否连接生产 ERPNext：否
是否修改前端/后端/.github/02_源码：否
是否 push/remote/PR：否
```
