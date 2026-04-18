# TASK-BACKLOG Sprint2 审计缺口批量补审任务分发 交付证据

- 任务编号：TASK-BACKLOG
- 分发路径：路径 C（标注现状，生产发布前补审）
- 执行时间：2026-04-16
- 当前基线：`384970400f7a137e8384649bd73cab5ae2d33300`
- 结论：待分发

## 一、输出文件清单
1. `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-B1_Sprint2审计缺口补审_ERPNextFailClosed.md`
2. `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-B2_Sprint2审计缺口补审_Outbox状态机.md`
3. `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-B3_Sprint2审计缺口补审_前端门禁框架.md`
4. `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-B4_Sprint2审计缺口补审_权限审计基座.md`
5. `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-B5_Sprint2审计缺口补审_销售库存只读.md`
6. `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-B6_Sprint2审计缺口补审_质量管理基线.md`
7. `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-BACKLOG_Sprint2审计缺口批量补审任务分发_交付证据.md`

## 二、覆盖关系
- B1 对应：TASK-008
- B2 对应：TASK-009
- B3 对应：TASK-010
- B4 对应：TASK-007
- B5 对应：TASK-011
- B6 对应：TASK-012

## 三、模板一致性检查
每张补审任务卡均包含：
- 任务编号
- 任务名称
- 角色
- 优先级
- 前置依赖
- 补审范围
- 审计要点
- 通过标准（高危=0，中危<=1，P1/P2 必须整改复审）
- 执行说明
- 完成后回复格式
- 禁止事项（含禁改路径与 push/PR/remote 禁止）

## 四、边界声明
- 本次仅输出任务分发文档，不写业务代码。
- 未修改前端业务代码：`06_前端/**`。
- 未修改后端业务代码：`07_后端/**`。
- 未修改 `.github/**`。
- 未修改 `02_源码/**`。
- 未执行 push / remote / PR。

## 五、验证命令
```bash
cd /Users/hh/Desktop/领意服装管理系统
test -f "03_需求与设计/02_开发计划/TASK-B1_Sprint2审计缺口补审_ERPNextFailClosed.md"
test -f "03_需求与设计/02_开发计划/TASK-B2_Sprint2审计缺口补审_Outbox状态机.md"
test -f "03_需求与设计/02_开发计划/TASK-B3_Sprint2审计缺口补审_前端门禁框架.md"
test -f "03_需求与设计/02_开发计划/TASK-B4_Sprint2审计缺口补审_权限审计基座.md"
test -f "03_需求与设计/02_开发计划/TASK-B5_Sprint2审计缺口补审_销售库存只读.md"
test -f "03_需求与设计/02_开发计划/TASK-B6_Sprint2审计缺口补审_质量管理基线.md"
test -f "03_需求与设计/02_开发计划/TASK-BACKLOG_Sprint2审计缺口批量补审任务分发_交付证据.md"
git diff --name-only -- "06_前端" "07_后端" ".github" "02_源码"
git diff --cached --name-only
```
