# TASK-018A 仓库增强边界设计冻结 工程任务单

## 1. 基本信息

- 任务编号：TASK-018A
- 任务名称：仓库增强边界设计冻结
- 模块：仓库管理主链
- 派发角色：A Technical Architect
- 执行角色：B Engineer
- 审计角色：C Auditor
- 任务类型：docs-only / 设计冻结 / 禁止实现
- 优先级：P1
- 派发时间：2026-04-23

## 2. 任务目标

在 Sprint 3 主链内，完成 `TASK-018A` 仓库增强边界设计冻结，输出可审计的统一口径文档。

本轮只做设计冻结，不做任何实现，不做任何联调，不做任何生产写入验证。

本轮通过后，只允许进入 `TASK-018B` 设计，不允许直接进入任何仓库实现任务。

## 3. 本轮产物

1. 更新：
   - `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-018A_仓库管理增强边界设计.md`
2. 更新：
   - `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-018A_仓库增强边界设计冻结_工程任务单.md`
3. 追加：
   - `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md`

## 4. 真相源

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/Sprint3_任务清单.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-018A_仓库管理增强边界设计.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-018A_仓库增强边界设计冻结_工程任务单.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-017A_采购管理边界设计.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-017B_Purchase Order创建流程设计.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-017C_Purchase Receipt入库设计.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-007_权限与审计统一基座设计.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-008_ERPNext集成FailClosed规范.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-009_Outbox公共状态机规范.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-010_前端写入口门禁公共框架设计.md`

## 5. 允许修改范围

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-018A_仓库管理增强边界设计.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-018A_仓库增强边界设计冻结_工程任务单.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md`

## 6. 严格禁止范围

- `/Users/hh/Desktop/领意服装管理系统/06_前端/**`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/**`
- `/Users/hh/Desktop/领意服装管理系统/.github/**`
- `/Users/hh/Desktop/领意服装管理系统/02_源码/**`
- `/Users/hh/Desktop/领意服装管理系统/00_交接与日志/**`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录/**`
- `/Users/hh/Documents/Playground 2/LOOP_STATE.md`
- `/Users/hh/Documents/Playground 2/HANDOVER_STATUS.md`
- 任意测试代码
- 任意业务代码
- 任意 push / PR / tag / 发布动作

## 7. 本轮必须冻结的设计结论

1. 本任务只做“仓库增强边界设计冻结”，不做实现、不做联调、不做生产写入。
2. 明确冻结对象边界：
   - `Stock Entry`
   - 库存盘点
   - `Batch / Serial`
   - 库存预警
   - `Stock Ledger / Stock Reconciliation / Warehouse` 关系边界
3. 明确三层能力统一口径并给出统一矩阵：
   - 只读能力
   - 候选写能力
   - 生产写能力
4. 明确 `Adapter / Outbox / fail-closed / internal-only` 职责边界。
5. 明确动作权限与资源字段最小集合。
6. 明确 ERPNext DocType 边界，不得偷渡实现放行。
7. 明确前端门禁：
   - 不允许未审计写入口
   - 不允许前端直连 ERPNext
8. 明确结论门禁：
   - `TASK-018A` 通过后只允许进入 `TASK-018B` 设计
   - 不允许直接进入任何仓库实现任务
9. 若任务单或文档存在旧路径、旧文件名或旧口径，本轮必须修正到当前统一口径。

## 8. 建议文档结构

1. 设计目标与冻结范围
2. 仓库增强总边界
3. Stock Entry 边界
4. 库存盘点边界
5. Batch / Serial 边界
6. 库存预警边界
7. 权限动作矩阵
8. 资源字段矩阵
9. ERPNext DocType 与 Adapter / Outbox 边界
10. fail-closed 与审计要求
11. 三层能力冻结统一矩阵
12. 前端门禁
13. 结论边界与下一步门禁

## 9. 执行步骤

1. 阅读当前 `TASK-018A` 设计文档与工程任务单，定位旧路径、旧口径、未收敛点。
2. 对齐 `TASK-016A`、`TASK-017A/B/C` 的冻结风格，将 `TASK-018A` 文档收敛为统一口径。
3. 同步修正 `TASK-018A` 工程任务单，使路径、输出目标、验证命令、回交格式与当前口径一致。
4. 仅在文档与任务单修正完成后，追加 1 条工程师会话日志。
5. 不得改动任何代码、测试、控制面、审计官日志。

## 10. 必须执行的验证命令

```bash
cd /Users/hh/Desktop/领意服装管理系统

test -f '03_需求与设计/01_架构设计/TASK-018A_仓库管理增强边界设计.md'
test -f '03_需求与设计/02_开发计划/TASK-018A_仓库增强边界设计冻结_工程任务单.md'

git diff --name-only -- \
  '03_需求与设计/01_架构设计/TASK-018A_仓库管理增强边界设计.md' \
  '03_需求与设计/02_开发计划/TASK-018A_仓库增强边界设计冻结_工程任务单.md' \
  '03_需求与设计/02_开发计划/工程师会话日志.md'

git diff --name-only -- \
  '06_前端' \
  '07_后端' \
  '.github' \
  '02_源码' \
  '00_交接与日志' \
  '03_需求与设计/05_审计记录'

git diff --check -- \
  '03_需求与设计/01_架构设计/TASK-018A_仓库管理增强边界设计.md' \
  '03_需求与设计/02_开发计划/TASK-018A_仓库增强边界设计冻结_工程任务单.md' \
  '03_需求与设计/02_开发计划/工程师会话日志.md'

rg -n '只读能力|候选写能力|生产写能力|TASK-018B|不允许直接进入任何仓库实现任务|fail-closed|Outbox|Adapter|Stock Entry|盘点|Batch|Serial|预警' \
  '03_需求与设计/01_架构设计/TASK-018A_仓库管理增强边界设计.md' \
  '03_需求与设计/02_开发计划/TASK-018A_仓库增强边界设计冻结_工程任务单.md'
```

## 11. 完成定义

1. `TASK-018A_仓库管理增强边界设计.md` 已更新并达到可审计状态。
2. `TASK-018A_仓库增强边界设计冻结_工程任务单.md` 已与当前口径一致。
3. 工程师会话日志已追加本轮完成记录。
4. diff 仅命中 3 个允许文件。
5. 禁改目录无本轮新增改动。
6. 文档已明确：
   - 三层能力统一矩阵
   - `TASK-018A` 通过后仅允许进入 `TASK-018B` 设计
   - 不允许直接进入任何仓库实现任务

## 12. 回交格式

```text
STATUS: READY_FOR_AUDIT
TASK_ID: TASK-018A
ROLE: B Engineer

CHANGED_FILES:
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-018A_仓库管理增强边界设计.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-018A_仓库增强边界设计冻结_工程任务单.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md

EVIDENCE:
- 本轮具体补齐了哪些冻结口径
- 三层能力统一矩阵位于哪些段落
- 为什么 `TASK-018B` 是唯一允许的下一张设计任务
- 为什么当前不得直接进入仓库实现

VERIFICATION:
- 逐条列出验证命令结果

BLOCKERS:
- 若无则写“无”

NEXT_ROLE:
- C Auditor
```
