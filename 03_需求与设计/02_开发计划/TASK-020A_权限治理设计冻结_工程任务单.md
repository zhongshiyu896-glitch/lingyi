# TASK-020A 权限治理设计冻结 工程任务单

## 1. 基本信息

- 任务编号：TASK-020A
- 任务名称：权限治理设计冻结
- 执行角色：B Engineer
- 审计角色：C Auditor
- 优先级：P0
- 状态：待执行（已放行）
- 任务类型：docs-only / 设计冻结 / 不写代码
- 当前官方控制面：READY_FOR_BUILD / B Engineer / TASK-020A

## 2. 任务背景

1. 最新 A/B/C Role Lock 已明确：A 不得因 C 的等待建议机械停机，必须基于控制面与主线事实自主决策下一步。
2. `TASK-019A -> TASK-019B -> TASK-019C` 已完成 docs-only 设计主线收口。
3. `Sprint3_任务清单.md` 中 `TASK-019` 后的下一条正式设计任务为 `TASK-020A 权限治理设计冻结`。
4. 既有 `TASK-020A_权限治理设计.md` 与本工程任务单均在盘，但口径停留在 2026-04-17 旧状态，且任务单曾引用旧输出文件名 `TASK-020_权限治理设计.md`。
5. 本轮只允许 B 对 `TASK-020A` 设计文档做 docs-only 收敛，并追加工程师日志；不得进入任何权限治理实现。

## 3. 任务目标

将 `TASK-020A_权限治理设计.md` 收敛到当前 Sprint 3 设计冻结统一口径，使其达到可审计状态，并明确：

1. 本任务仅冻结权限治理设计，不做实现、不做联调、不做上线准备。
2. 权限治理必须基于 `TASK-007` 权限与审计统一基座。
3. 前端写入口与管理入口必须继承 `TASK-010` 门禁口径。
4. 未知动作、未知资源字段、权限源不可用必须 fail-closed。
5. `TASK-020A` 通过后仅允许进入 `TASK-020B` 系统管理设计冻结，不得直接进入任何权限治理实现任务。

## 4. 真相源

仅允许读取以下文件作为本轮依据：

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/Sprint3_任务清单.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/Sprint3_主执行计划.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-020A_权限治理设计.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-020_权限治理设计.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-007_权限与审计统一基座设计.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-010_前端写入口门禁公共框架设计.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-016A_财务管理边界设计.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-017A_采购管理边界设计.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-018A_仓库管理增强边界设计.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-019A_报表与仪表盘总体设计.md`

## 5. 允许修改文件

仅允许修改：

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-020A_权限治理设计.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md`

## 6. 禁止修改文件

禁止修改：

- `/Users/hh/Desktop/领意服装管理系统/06_前端/**`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/**`
- `/Users/hh/Desktop/领意服装管理系统/.github/**`
- `/Users/hh/Desktop/领意服装管理系统/02_源码/**`
- `/Users/hh/Desktop/领意服装管理系统/00_交接与日志/**`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录/**`
- `/Users/hh/Documents/Playground 2/LOOP_STATE.md`
- `/Users/hh/Documents/Playground 2/TASK_BOARD.md`
- `/Users/hh/Documents/Playground 2/HANDOVER_STATUS.md`
- 任意测试代码
- 任意业务代码
- 任意远端、commit、push、tag、PR、发布动作

## 7. 必须补齐的设计结论

`TASK-020A_权限治理设计.md` 必须至少补齐并收敛以下内容：

1. 明确本任务只做权限治理设计冻结，不做实现、不做联调、不做上线。
2. 明确冻结对象：
   - 权限动作注册表
   - 角色权限矩阵
   - 用户资源权限配置
   - 权限变更审批
   - 安全审计查询
   - 操作审计查询
   - 权限诊断
   - TASK-007 基座回迁路径
3. 明确三层能力统一口径：
   - 只读能力
   - 候选写能力
   - 生产写能力
4. 明确动作权限最小集合，至少覆盖：
   - `permission:read`
   - `permission:export`
   - `permission:role_create`
   - `permission:role_update`
   - `permission:role_disable`
   - `permission:user_scope_update`
   - `permission:approval`
   - `permission:rollback`
   - `permission:audit_read`
   - `permission:diagnostic`
5. 明确资源字段最小集合，至少覆盖：
   - `company`
   - `item_code`
   - `supplier`
   - `customer`
   - `warehouse`
   - `work_order`
   - `sales_order`
   - `purchase_order`
   - `bom_id`
   - `account`
   - `cost_center`
   - `batch_no`
   - `serial_no`
6. 明确 fail-closed 规则：未知动作、未知资源字段、权限源不可用、审计源不可用、高危权限审批状态不明，均不得放行。
7. 明确前端门禁：
   - 普通用户不得看到权限治理菜单。
   - `permission:diagnostic` 不得暴露给普通前端菜单。
   - 无权限分支不得发请求。
   - 禁止前端直连权限源或 ERPNext。
   - 写入口必须继承 `TASK-010` 门禁口径。
8. 明确审计要求：
   - 安全审计与操作审计分轨。
   - token / cookie / authorization / password / secret / DSN 必须脱敏或不落库。
   - 导出必须防 CSV 公式注入并记录导出审计。
9. 明确 TASK-007 回迁边界：公共鉴权、资源校验、审计落库、错误信封不得重复实现；权限治理只承担编排层、审批层、版本层设计。
10. 明确结论边界：
    - `TASK-020A` 通过后仅允许进入 `TASK-020B` 系统管理设计冻结。
    - 不允许直接进入任何权限治理实现任务。
    - 不允许直接进入联调、提测、上线或生产发布。

## 8. 建议文档结构

建议将设计文档收敛为以下结构：

1. 设计目标与冻结范围
2. 权限治理总边界
3. 权限动作注册表
4. 角色权限矩阵
5. 用户资源权限配置
6. 权限变更审批流程
7. 安全审计日志查询设计
8. 操作审计日志查询设计
9. TASK-007 基座回迁路径
10. 前端门禁要求
11. fail-closed 与脱敏审计要求
12. 三层能力冻结统一矩阵
13. 生产发布前置条件
14. 结论边界与下一步门禁

## 9. 验证命令

```bash
cd /Users/hh/Desktop/领意服装管理系统

test -f '03_需求与设计/01_架构设计/TASK-020A_权限治理设计.md'
test -f '03_需求与设计/02_开发计划/TASK-020A_权限治理设计冻结_工程任务单.md'

git diff --name-only -- \
  '03_需求与设计/01_架构设计/TASK-020A_权限治理设计.md' \
  '03_需求与设计/02_开发计划/工程师会话日志.md'

git diff --name-only -- \
  '06_前端' \
  '07_后端' \
  '.github' \
  '02_源码' \
  '00_交接与日志' \
  '03_需求与设计/05_审计记录'

git diff --check -- \
  '03_需求与设计/01_架构设计/TASK-020A_权限治理设计.md' \
  '03_需求与设计/02_开发计划/工程师会话日志.md'

rg -n '只读能力|候选写能力|生产写能力|TASK-020B|不允许直接进入任何权限治理实现任务|fail-closed|TASK-007|TASK-010|permission:read|permission:export|permission:role_create|permission:role_update|permission:role_disable|permission:user_scope_update|permission:approval|permission:rollback|permission:audit_read|permission:diagnostic|company|warehouse|account|cost_center|脱敏|公式注入' \
  '03_需求与设计/01_架构设计/TASK-020A_权限治理设计.md'
```

## 10. 完成定义

- `TASK-020A_权限治理设计.md` 已收敛到当前统一设计冻结口径。
- 工程师会话日志已追加本轮完成记录。
- 本轮只修改设计文档与工程师会话日志。
- 未修改任何前端、后端、测试、控制面、审计记录。
- 已明确 `TASK-020A` 通过后仅允许进入 `TASK-020B` 设计。
- 已明确不得直接进入任何权限治理实现任务。
- `git diff --check` 通过。

## 11. 回交格式

```text
STATUS: READY_FOR_AUDIT
TASK_ID: TASK-020A
ROLE: B Engineer

CHANGED_FILES:
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-020A_权限治理设计.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md

EVIDENCE:
- 本轮补齐了哪些冻结口径
- 三层能力统一矩阵位于哪些段落
- TASK-007 / TASK-010 边界如何继承
- 为什么 TASK-020B 是唯一允许的下一张设计任务
- 为什么当前不得直接进入权限治理实现

VERIFICATION:
- 逐条列出验证命令结果

BLOCKERS:
- 若无则写“无”

NEXT_ROLE:
- C Auditor
```
