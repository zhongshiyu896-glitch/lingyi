# TASK-019A 报表与仪表盘总体设计 工程任务单

## 1. 基本信息

- 任务编号：TASK-019A
- 任务名称：报表与仪表盘总体设计
- 执行角色：B Engineer
- 任务性质：docs-only
- 优先级：P1
- 状态：待执行（已放行）
- 前置依赖：TASK-013C 审计通过；TASK-018C 已正式 PASS 并收口

## 2. 任务目标

基于既有设计文档，完成 `TASK-019A` 报表与仪表盘总体设计冻结，明确只读报表原则、指标来源、权限字段、导出安全、缓存边界、前端门禁、后端要求与下一步 `TASK-019B` 设计门禁。

本任务只允许形成设计冻结结论，不允许进入任何报表、看板、导出、诊断或缓存实现。

## 3. 允许范围

仅允许修改以下文件：

1. `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-019A_报表与仪表盘总体设计.md`
2. `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md`

允许只读参考以下真相源：

1. `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/Sprint3_任务清单.md`
2. `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-010_前端写入口门禁公共框架设计.md`
3. `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-016C_财务只读报表设计.md`
4. `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/report.ts`
5. `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/dashboard.ts`
6. `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/reports/ReportCatalog.vue`
7. `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/dashboard/DashboardOverview.vue`
8. `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/report.py`
9. `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/dashboard.py`
10. `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/report_catalog_service.py`
11. `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/dashboard_service.py`
12. `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/report_export_service.py`

## 4. 禁止范围

1. 禁止修改任何前端源码。
2. 禁止修改任何后端源码。
3. 禁止修改任何测试代码。
4. 禁止新增页面、路由、API、模型、migration、outbox、worker。
5. 禁止实现报表目录、看板、导出、诊断、缓存刷新。
6. 禁止新增任何写接口。
7. 禁止前端直连 ERPNext。
8. 禁止修改 `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-019_报表与仪表盘总体设计.md`；该文件只可作为旧版背景，不作为本轮正式输出。
9. 禁止修改 `LOOP_STATE.md`、`HANDOVER_STATUS.md`、架构师会话日志、审计官会话日志。
10. 禁止 push / remote / PR / commit / 生产发布。

## 5. 必须冻结的正文结论

`TASK-019A_报表与仪表盘总体设计.md` 至少必须写清：

1. 报表与仪表盘总体范围。
2. 所有报表默认只读，不得触发业务写入、生成、同步、重算、提交。
3. 指标来源与口径，至少覆盖生产、库存、财务、采购、质量、外发、BOM、权限审计、操作审计。
4. 权限动作与资源字段，至少覆盖 `report:read / report:export / report:dashboard / report:diagnostic` 与 `company / item_code / supplier / customer / warehouse / work_order / sales_order / purchase_order`。
5. 导出安全边界，包括公式注入防护、脱敏、行数限制、权限复用、操作审计。
6. 缓存边界，包括 TTL 分级、权限 scope 纳入 cache key、stale 标记、权限变更失效、财务类缓存限制。
7. 前端门禁：必须接入 `TASK-010`，禁止写入口、禁止裸 fetch/axios、禁止直连 ERPNext `/api/resource`。
8. 后端要求：统一响应、权限前置、资源过滤、错误信封、fail-closed，不得伪成功。
9. `diagnostic` 当前仅允许管理员/内部诊断边界，不得普通前端泛化。
10. 下一步门禁：`TASK-019A` 正式 PASS 后仅允许进入 `TASK-019B` 生产进度看板设计，不允许直接进入任何报表实现任务。

## 6. 验证命令

```bash
cd '/Users/hh/Desktop/领意服装管理系统'

test -f '03_需求与设计/01_架构设计/TASK-019A_报表与仪表盘总体设计.md'
test -f '03_需求与设计/02_开发计划/TASK-019A_报表与仪表盘总体设计_工程任务单.md'

rg -n "只读|report:read|report:export|report:dashboard|report:diagnostic|company|item_code|supplier|customer|warehouse|缓存|stale|公式注入|TASK-010|TASK-019B|不得直接进入.*实现" \
  '03_需求与设计/01_架构设计/TASK-019A_报表与仪表盘总体设计.md'

git diff --name-only -- \
  '06_前端' \
  '07_后端' \
  '.github' \
  '02_源码'

git diff --check -- \
  '03_需求与设计/01_架构设计/TASK-019A_报表与仪表盘总体设计.md' \
  '03_需求与设计/02_开发计划/TASK-019A_报表与仪表盘总体设计_工程任务单.md' \
  '03_需求与设计/02_开发计划/工程师会话日志.md'
```

## 7. 回交格式

```text
STATUS: READY_FOR_AUDIT
TASK_ID: TASK-019A
ROLE: B Engineer

CHANGED_FILES:
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-019A_报表与仪表盘总体设计.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md

EVIDENCE:
- 说明报表总体范围、指标来源、权限字段、导出安全、缓存边界、前端门禁、后端要求、TASK-019B 门禁已冻结。
- 说明未修改前端、后端、测试、控制面、审计日志。

VERIFICATION:
- 写明实际执行的验证命令和结果。

BLOCKERS:
- 若无则写“无”。

NEXT_ROLE:
- C Auditor
```
