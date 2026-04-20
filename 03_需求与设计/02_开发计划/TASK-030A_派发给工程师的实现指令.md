# TASK-030A 派发给工程师的实现指令

## 1. 派发信息

- 任务编号：TASK-030A
- 任务名称：质量管理基线工程实现
- 派发角色：A Technical Architect
- 执行角色：B Engineer
- 派发时间：2026-04-19 14:20 CST+8
- 依据任务单：`/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-030A_质量管理基线工程实现_工程任务单.md`
- 审计依据：
  - `TASK-030A` 任务单复核通过（审计意见书第297份）
  - `TASK-012_质量管理基线设计.md` 设计冻结
  - `TASK-007` 权限与审计基座（审计意见书第175份）
- 当前门禁：`build_release_allowed=yes`，可进入实现；仍禁止 push / remote / PR / 生产发布

## 2. 派发目标

基于现有 `quality` 模块代码基础，完成质量管理 Phase 1 的“只读 / 统计 / 导出收口”实现，不得把本任务做成质量模块重建或写能力恢复。

本轮必须完成四件事：

1. 保留列表 / 详情 / 统计 / 导出四个读能力。
2. 冻结现有写口：创建 / 修改 / 确认 / 取消不得继续形成真实业务写入。
3. 去掉普通前端的写入口与写调用。
4. 将质量服务主链路中的 ERPNext `/api/resource` 直连收口到专用 fail-closed adapter。

## 3. 实现范围

### 3.1 允许实现的内容

1. 后端读侧收口：
   - 保留 `GET /api/quality/inspections`
   - 保留 `GET /api/quality/inspections/{id}`
   - 保留 `GET /api/quality/statistics`
   - 保留 `GET /api/quality/export`
2. 后端写口冻结：
   - 保留现有写路由定义也可以，但必须统一返回冻结错误信封（推荐错误码：`QUALITY_WRITE_FROZEN`）
   - 冻结后不得落库、不得写 ERPNext、不得记录成功审计
3. 前端去写化：
   - `quality.ts` 仅保留读侧导出
   - 列表页移除“创建检验单”按钮与创建对话框
   - 详情页移除“更新 / 确认 / 取消”按钮与相关对话框
4. ERPNext fail-closed 收口：
   - 将 `quality_service.py` 中的 `/api/resource` 读取迁移到专用 adapter 或现有 fail-closed adapter 体系
   - 保留 Item / Supplier / Warehouse 不可用时 fail closed
5. 测试收口：
   - 补齐或修正质量测试，使其覆盖只读正常、写口冻结、ERPNext fail-closed、统计排除 `cancelled`

### 3.2 允许修改的文件

1. 后端：
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/quality.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/quality.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/quality_service.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/quality.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_fail_closed_adapter.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_quality_adapter.py`（如需新建）
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/permission_service.py`（仅在必要时）
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/permissions.py`（仅在必要时）
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/versions/task_030a_*.py`（仅在必要时做增量修正）
2. 前端：
   - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/quality.ts`
   - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/quality/QualityInspectionList.vue`
   - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/quality/QualityInspectionDetail.vue`
3. 测试：
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_quality_api.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_quality_models.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_quality_*baseline.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_quality_*fail_closed.py`
4. 交付记录：
   - `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md`

## 4. 当前已确认现状

1. 现有读路由已存在：
   - `quality.py:349` 列表
   - `quality.py:428` 详情
   - `quality.py:612` 统计
   - `quality.py:664` 导出
2. 现有写路由仍存在且需冻结：
   - `quality.py:292` 创建
   - `quality.py:468` 修改
   - `quality.py:487` 确认
   - `quality.py:506` 取消
3. 现有前端写调用仍存在且需移除：
   - `quality.ts:227` 创建
   - `quality.ts:234` 修改
   - `quality.ts:241` 确认
   - `quality.ts:248` 取消
4. 现有普通前端写入口仍存在且需去写化：
   - `QualityInspectionList.vue:10` 创建按钮
   - `QualityInspectionList.vue:110` 创建对话框
   - `QualityInspectionDetail.vue:39` 到 `QualityInspectionDetail.vue:49` 写操作按钮
   - `QualityInspectionDetail.vue:109` 到 `QualityInspectionDetail.vue:160` 写操作对话框
5. 现有 ERPNext 直连事实仍存在且需收口：
   - `quality_service.py:132` `/api/resource/{doctype}/{name}`

## 5. 严禁范围

1. 禁止把质量模块重做为并行新模块或新工程。
2. 禁止恢复普通前端可用的创建 / 修改 / 确认 / 取消真实写能力。
3. 禁止新增或恢复 ERPNext Stock Entry / Purchase Receipt / Delivery Note / GL / Payment / Purchase Invoice 写入。
4. 禁止引入 outbox、自动扣款结算、自动返工工单、自动报废入账。
5. 禁止保留质量主链路中的 ERPNext `/api/resource` 直连字面量。
6. 禁止新增本地持久化 Authorization / Cookie / Token / Secret 明文。
7. 禁止修改以下路径：
   - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/router/**`
   - `/Users/hh/Desktop/领意服装管理系统/.github/**`
   - `/Users/hh/Desktop/领意服装管理系统/02_源码/**`
   - `/Users/hh/Desktop/领意服装管理系统/04_生产/**`
8. 禁止 push / remote / PR / 生产发布。

## 6. 开始前必须完成的前置检查

1. 逐行阅读并确认以下文件边界：
   - `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-030A_质量管理基线工程实现_工程任务单.md`
   - `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-012_质量管理基线设计.md`
2. 核对审计日志中存在：
   - `TASK-030A` 第297份通过
3. 运行以下命令确认允许文件内不存在来源不明的未提交改动：
   - `git -C /Users/hh/Desktop/领意服装管理系统 status --short -- '07_后端/lingyi_service/app/models/quality.py' '07_后端/lingyi_service/app/schemas/quality.py' '07_后端/lingyi_service/app/services/quality_service.py' '07_后端/lingyi_service/app/routers/quality.py' '06_前端/lingyi-pc/src/api/quality.ts' '06_前端/lingyi-pc/src/views/quality/QualityInspectionList.vue' '06_前端/lingyi-pc/src/views/quality/QualityInspectionDetail.vue'`
4. 只要发现必须改动严禁范围文件才能完成任务，立即 `BLOCKED`。

## 7. 实现执行要求

1. 后端实现要求：
   - 读路由保持可用，资源过滤语义保持可用。
   - 写路由统一冻结，返回稳定错误信封，不得有数据库写入、ERPNext 写入或成功审计副作用。
   - `quality_service.py` 中 ERPNext 主数据读取必须经 fail-closed adapter 收口，不得再保留 `/api/resource` 字面量。
   - 统计必须继续排除 `cancelled`。
2. 前端实现要求：
   - `quality.ts` 只保留四个读侧导出函数。
   - `QualityInspectionList.vue` 只保留查询 / 导出 / 详情跳转。
   - `QualityInspectionDetail.vue` 只保留详情展示，不得保留更新 / 确认 / 取消入口。
3. 测试要求：
   - 覆盖读侧正常。
   - 覆盖写口冻结 / 不可写。
   - 覆盖 ERPNext fail-closed。
   - 覆盖 `cancelled` 不参与统计。

## 8. 完成后必须自验的检查点

### 8.1 功能与边界检查

1. 普通前端仍可查看质量列表、详情、统计、导出。
2. 普通前端不再可创建 / 修改 / 确认 / 取消。
3. 后端写口已冻结或移除，且无副作用。
4. 质量主链路不再出现 ERPNext `/api/resource` 直连。
5. 未引入敏感凭据本地持久化。

### 8.2 文件范围检查

1. 本轮 diff 只能命中第 3 节允许范围内文件。
2. 不得出现以下路径改动：
   - `06_前端/lingyi-pc/src/router/**`
   - `.github/**`
   - `02_源码/**`
   - `04_生产/**`

### 8.3 必跑命令

```bash
cd /Users/hh/Desktop/领意服装管理系统

# 1. 读路由保留
rg -n '@router.get\("/inspections"\)|@router.get\("/inspections/\{inspection_id\}"\)|@router.get\("/statistics"\)|@router.get\("/export"\)' \
  07_后端/lingyi_service/app/routers/quality.py

# 2. 写口冻结或移除
rg -n '@router\.(post|patch)\("/inspections|/confirm|/cancel' \
  07_后端/lingyi_service/app/routers/quality.py || true
rg -n 'QUALITY_WRITE_FROZEN|disabled_by_design|pending_design|not_enabled' \
  07_后端/lingyi_service/app/routers/quality.py \
  07_后端/lingyi_service/app/services/quality_service.py

# 3. 普通前端无写调用、无写文案
! rg -n 'createQualityInspection|updateQualityInspection|confirmQualityInspection|cancelQualityInspection' \
  06_前端/lingyi-pc/src/api/quality.ts \
  06_前端/lingyi-pc/src/views/quality/QualityInspectionList.vue \
  06_前端/lingyi-pc/src/views/quality/QualityInspectionDetail.vue
! rg -n '创建检验单|更新检验结果|确认检验单|取消检验单' \
  06_前端/lingyi-pc/src/views/quality/QualityInspectionList.vue \
  06_前端/lingyi-pc/src/views/quality/QualityInspectionDetail.vue

# 4. 无 ERPNext /api/resource 直连、无敏感凭据
! rg -n '/api/resource' \
  07_后端/lingyi_service/app/routers/quality.py \
  07_后端/lingyi_service/app/services/quality_service.py \
  06_前端/lingyi-pc/src/api/quality.ts \
  06_前端/lingyi-pc/src/views/quality
! rg -n 'localStorage.*token|localStorage.*AUTH|localStorage.*LY_AUTH_TOKEN' \
  06_前端/lingyi-pc/src/api/quality.ts \
  06_前端/lingyi-pc/src/views/quality

# 5. 质量测试集
pytest \
  07_后端/lingyi_service/tests/test_quality_api.py \
  07_后端/lingyi_service/tests/test_quality_models.py \
  -v --tb=short

# 6. 越界检查
git diff --name-only -- \
  06_前端/lingyi-pc/src/router \
  .github \
  02_源码 \
  04_生产
```

## 9. 交付回报模板

```text
STATUS: HANDOFF / NEEDS_FIX / BLOCKED
TASK_ID: TASK-030A
ROLE: B

CHANGED_FILES:
- 绝对路径 1
- 绝对路径 2

EVIDENCE:
- 哪些读能力被保留
- 哪些写口已冻结或移除
- 哪些前端写入口已移除
- ERPNext /api/resource 直连如何被收口

VERIFICATION:
- 命令 1：通过 / 失败（附简要结果）
- 命令 2：通过 / 失败（附简要结果）
- 命令 3：通过 / 失败（附简要结果）
- 命令 4：通过 / 失败（附简要结果）
- 命令 5：通过 / 失败（附简要结果）
- 命令 6：通过 / 失败（附简要结果）

BLOCKERS:
- 无 / 具体阻塞

NEXT_ROLE: C Auditor
```

同时追加以下结论项：

```text
TASK-030A 执行完成。
结论：待审计
质量管理 Phase 1 只读基线是否已收口：是
写接口状态：[已冻结 / 已移除]
普通前端写入口状态：[已移除]
是否存在 ERPNext 写操作：否
质量模块主链路是否仍有 /api/resource 直连：否
是否存在 views/router 越界修改：否
pytest 测试结果：[通过/失败]
```

## 10. 工程师会话日志追加格式

在 `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md` 末尾追加一行：

```text
- 2026-04-19 HH:MM | TASK-030A 质量管理 | 交付报告第X份 | 完成（质量管理 Phase 1 只读/统计/导出收口并已提交 C 复审）
```

## 11. 回交 C 的触发条件

满足以下全部条件后，才能回交 `C Auditor`：

1. 真实代码改动已形成，且只落在第 3 节允许范围内。
2. 读路由保留，写口冻结 / 移除已完成。
3. 普通前端写入口与写调用均已移除。
4. 质量主链路不再存在 `/api/resource` 直连。
5. 第 8.3 节命令已执行并记录结果。
6. 工程师会话日志已追加本轮交付记录。
7. 未设置 `build_release_allowed=yes`，未执行 push / remote / PR / 发布动作。
