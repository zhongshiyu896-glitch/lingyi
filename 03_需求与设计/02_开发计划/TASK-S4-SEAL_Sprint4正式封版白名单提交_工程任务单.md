# TASK-S4-SEAL Sprint4 正式封版白名单提交 工程任务单

## 1. 基本信息
- 任务编号：`TASK-S4-SEAL`
- 任务名称：Sprint4 正式封版白名单提交
- 角色：`B Engineer`
- 优先级：`P0`
- 状态：`待执行（已放行）`
- 前置依赖：`TASK-S4-CLOSEOUT` 审计通过（审计意见书第372份）；Sprint4 包内 `TASK-030C~030G`、`TASK-040A~040C` 均已通过 C 审计

## 2. 任务目标
在 Sprint4 全包收口审计通过后，完成本地正式封版：

1. 复跑 Sprint4 核心验证。
2. 基于严格白名单暂存 Sprint4 相关代码、测试、迁移、文档与控制面文件。
3. 创建本地封版 commit。
4. 输出封版证据报告。
5. 不 push、不建 PR、不发布生产。

## 3. 允许范围
### 3.1 允许新增/修改封版证据
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/Sprint4_正式封版证据.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md`

### 3.2 允许纳入本地封版 commit 的 Sprint4 文件
只允许暂存以下类型文件：

质量管理链：
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/quality.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/quality_outbox.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/quality.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/quality.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/quality_outbox.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/quality_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/quality_outbox_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/quality_outbox_worker.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_quality_outbox_adapter.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/quality_export_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/quality_purchase_receipt_listener.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/versions/task_030c_add_quality_cancel_reason.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/versions/task_030d_create_quality_outbox.py`

销售库存与跨模块链：
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/sales_inventory.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/sales_inventory.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/sales_inventory_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_sales_inventory_adapter.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/cross_module_view.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/cross_module_view_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/cross_module_view.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/main.py`

前端：
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/quality.ts`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/sales_inventory.ts`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/cross_module.ts`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/quality/QualityInspectionDetail.vue`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/quality/QualityInspectionList.vue`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/sales_inventory/SalesInventoryStockLedger.vue`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/cross_module/`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/router/index.ts`

测试：
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_quality_create_baseline.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_quality_update_baseline.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_quality_defect_baseline.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_quality_confirm_baseline.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_quality_cancel_baseline.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_quality_outbox.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_quality_worker_permissions.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_quality_statistics_enhanced.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_quality_export_enhanced.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_quality_auto_trigger.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_quality_models.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_quality_api.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_sales_inventory_enhanced.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_sales_inventory_permission.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_sales_inventory_api.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_sales_inventory_permissions.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_cross_module_view.py`

文档与控制面：
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/PKG-030-040-V1_Sprint4_A-B-C_全量自主循环任务包.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-030C_质检单确认取消状态机重启_工程任务单.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-030D_质量管理ERPNext库存写入联动Outbox_工程任务单.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-030E_质量统计分析增强_工程任务单.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-030F_质量导出PDFExcel增强_工程任务单.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-030G_来料检验自动触发_工程任务单.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-040A_销售库存只读聚合增强_工程任务单.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-040B_库存过滤权限增强_工程任务单.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-040C_跨模块视图_工程任务单.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/Sprint4_全包收口验证报告.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/Sprint4_正式封版证据.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/架构师会话日志.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录/审计官会话日志.md`
- `/Users/hh/Desktop/领意服装管理系统/00_交接与日志/HANDOVER_STATUS.md`
- `/Users/hh/Documents/Playground 2/LOOP_STATE.md`

## 4. 禁止范围
1. 禁止 `git add .`。
2. 禁止 `git add -A`。
3. 禁止暂存 `.ci-reports/`。
4. 禁止暂存 `01_需求与资料/**`。
5. 禁止暂存 `02_源码/**`。
6. 禁止暂存 `03_环境与部署/**`。
7. 禁止暂存 `04_测试与验收/**`。
8. 禁止暂存 `05_交付物/**`。
9. 禁止暂存 `.github/**`。
10. 禁止暂存未列入白名单的历史任务单、探针、缓存、构建产物、运行产物。
11. 禁止 push / remote / PR。
12. 禁止创建或推送 tag。
13. 禁止生产发布。
14. 禁止修改业务代码后再封版；如发现需要修复，立即 `BLOCKED` 回报。

## 5. 必须执行步骤
### 5.1 前置状态核验
```bash
cd /Users/hh/Desktop/领意服装管理系统
git status --short --branch
```

要求：记录当前脏工作树，区分 Sprint4 白名单文件与历史继承脏文件。

### 5.2 复跑后端核心测试
```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest \
  tests/test_quality_create_baseline.py \
  tests/test_quality_update_baseline.py \
  tests/test_quality_defect_baseline.py \
  tests/test_quality_confirm_baseline.py \
  tests/test_quality_cancel_baseline.py \
  tests/test_quality_outbox.py \
  tests/test_quality_worker_permissions.py \
  tests/test_quality_statistics_enhanced.py \
  tests/test_quality_export_enhanced.py \
  tests/test_quality_auto_trigger.py \
  tests/test_quality_models.py \
  tests/test_sales_inventory_enhanced.py \
  tests/test_sales_inventory_permission.py \
  tests/test_sales_inventory_api.py \
  tests/test_sales_inventory_permissions.py \
  tests/test_cross_module_view.py \
  -v --tb=short
```

### 5.3 复跑前端检查
```bash
cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc
npm run typecheck
npm run build
```

如 `npm run build` 因既有构建配置缺失失败，但 `typecheck` 通过，必须记录为残余风险，不得隐瞒。

### 5.4 边界扫描
```bash
cd /Users/hh/Desktop/领意服装管理系统

git diff --name-only -- .github 02_源码 04_生产

rg -n 'requests\.(post|put|patch|delete)|httpx\.(post|put|patch|delete)' \
  07_后端/lingyi_service/app/services \
  07_后端/lingyi_service/app/routers

rg -n '@router\.(post|put|patch|delete)' \
  07_后端/lingyi_service/app/routers/cross_module_view.py \
  07_后端/lingyi_service/app/routers/sales_inventory.py

rg -n 'outbox|worker|run-once|run_once' \
  07_后端/lingyi_service/app/services/quality_purchase_receipt_listener.py \
  07_后端/lingyi_service/app/services/sales_inventory_service.py \
  07_后端/lingyi_service/app/routers/sales_inventory.py \
  07_后端/lingyi_service/app/services/cross_module_view_service.py \
  07_后端/lingyi_service/app/routers/cross_module_view.py
```

### 5.5 生成封版证据
生成：

`/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/Sprint4_正式封版证据.md`

必须包含：
- 封版时间
- 前置审计编号：第372份
- 后端测试结果
- 前端 typecheck/build 结果
- 禁改目录扫描结果
- ERPNext 写调用扫描结果
- 写接口扫描结果
- outbox/worker 扫描结果
- 白名单 staged 清单
- 本地 commit hash
- 残余风险

### 5.6 白名单暂存
只允许使用显式路径暂存。

禁止：
```bash
git add .
git add -A
```

暂存后必须检查：
```bash
git diff --cached --name-only
git status --short --branch
```

如果 `git diff --cached --name-only` 出现白名单外文件，必须立即停止并回报 `BLOCKED`，不得 commit。

### 5.7 创建本地封版 commit
白名单核验通过后执行：

```bash
git commit -m "chore: seal Sprint 4 quality and sales inventory baseline"
```

提交后记录：
```bash
git rev-parse --short HEAD
git status --short --branch
```

## 6. 验收标准
1. 后端核心测试通过。
2. 前端 `npm run typecheck` 通过。
3. `npm run build` 通过，或失败原因被明确记录为既有残余风险。
4. 禁改目录 diff 为空。
5. 未发现未审计 ERPNext 同步写调用。
6. 未发现 Sprint4 关注模块新增写接口。
7. 未发现 Sprint4 关注模块新增 outbox/worker 越界。
8. 只暂存白名单文件。
9. 已创建本地封版 commit。
10. 未 push、未 PR、未 tag、未生产发布。
11. 已输出 `Sprint4_正式封版证据.md`。
12. 已追加工程师会话日志。

## 7. 失败处理
任一门禁失败时：

1. 停止。
2. 不要自行修复。
3. 不要 commit。
4. 回报 `STATUS: BLOCKED`。
5. 写明失败命令、失败摘要、涉及文件、建议下一步。

## 8. 完成回报格式
完成后仅按以下格式回交：

```md
STATUS: READY_FOR_AUDIT
TASK_ID: TASK-S4-SEAL
CONTEXT_VERSION: 未提供
ROLE: B

CHANGED_FILES:
- 绝对路径1
- 绝对路径2

EVIDENCE:
- 后端测试结果：
- 前端 typecheck/build 结果：
- 禁改目录扫描结果：
- ERPNext 写调用扫描结果：
- 写接口扫描结果：
- outbox/worker 扫描结果：
- staged 白名单清单：
- 本地封版 commit：
- 封版证据文件：

VERIFICATION:
- pytest：
- npm run typecheck：
- npm run build：
- git diff --cached --name-only：
- git rev-parse --short HEAD：
- git status --short --branch：

RISKS:
- 无 / 具体残余风险

NEXT_ROLE: C Auditor
```
