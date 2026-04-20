# Sprint4 正式封版证据

- 任务：TASK-S4-SEAL
- 封版时间：2026-04-20 13:33
- 前置审计：审计意见书第372份（TASK-S4-CLOSEOUT 通过）

## 1. 后端核心测试

命令：

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

结果：`70 passed, 18 warnings in 1.29s`

## 2. 前端检查

命令：

```bash
cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc
npm run typecheck
npm run build
```

结果：
- `typecheck`：通过
- `build`：通过（Vite build 完成，存在 chunk 体积提示但不阻塞封版）

## 3. 禁改目录扫描

命令：

```bash
cd /Users/hh/Desktop/领意服装管理系统
git diff --name-only -- .github 02_源码 04_生产
git status --short -- .github 02_源码 04_生产
```

结果：
- `git diff`：空
- `git status`：`?? 02_源码/`（继承未跟踪目录，非本轮新增）

## 4. ERPNext 写调用边界扫描

命令：

```bash
cd /Users/hh/Desktop/领意服装管理系统
rg -n 'requests\.(post|put|patch|delete)|httpx\.(post|put|patch|delete)' \
  07_后端/lingyi_service/app/services \
  07_后端/lingyi_service/app/routers
```

结果：空（未发现新增同步 ERPNext 写调用）

## 5. 写接口边界扫描

命令：

```bash
rg -n '@router\.(post|put|patch|delete)' \
  07_后端/lingyi_service/app/routers/cross_module_view.py \
  07_后端/lingyi_service/app/routers/sales_inventory.py
```

结果：空（未发现 Sprint4 关注模块新增写接口）

## 6. outbox/worker 边界扫描

命令：

```bash
rg -n 'outbox|worker|run-once|run_once' \
  07_后端/lingyi_service/app/services/quality_purchase_receipt_listener.py \
  07_后端/lingyi_service/app/services/sales_inventory_service.py \
  07_后端/lingyi_service/app/routers/sales_inventory.py \
  07_后端/lingyi_service/app/services/cross_module_view_service.py \
  07_后端/lingyi_service/app/routers/cross_module_view.py
```

结果：空（未发现 Sprint4 关注模块新增 outbox/worker 越界）

## 7. staged 白名单清单

> 待 `git diff --cached --name-only` 后回填。

## 8. 本地 commit hash

> 3ceb692

## 9. 残余风险

1. 工作树存在大量继承脏文件，本次按白名单显式暂存，未纳入的历史脏文件仍保留在工作树。
2. 后端测试存在 18 条已知 warning（datetime UTC 弃用告警），不影响本次封版门禁结论。

## 附录A staged 白名单清单（提交前）
- 00_交接与日志/HANDOVER_STATUS.md
- 03_需求与设计/01_架构设计/架构师会话日志.md
- 03_需求与设计/02_开发计划/PKG-030-040-V1_Sprint4_A-B-C_全量自主循环任务包.md
- 03_需求与设计/02_开发计划/Sprint4_全包收口验证报告.md
- 03_需求与设计/02_开发计划/Sprint4_正式封版证据.md
- 03_需求与设计/02_开发计划/Sprint4_规划草案.md
- 03_需求与设计/02_开发计划/TASK-030A_派发给工程师的实现指令.md
- 03_需求与设计/02_开发计划/TASK-030A_质量管理基线工程实现_工程任务单.md
- 03_需求与设计/02_开发计划/TASK-030B_质检单创建修改与缺陷录入_工程任务单.md
- 03_需求与设计/02_开发计划/TASK-030C_派发给工程师的实现指令.md
- 03_需求与设计/02_开发计划/TASK-030C_质检单确认取消状态机重启_工程任务单.md
- 03_需求与设计/02_开发计划/TASK-030D_派发给工程师的实现指令.md
- 03_需求与设计/02_开发计划/TASK-030D_质量管理ERPNext库存写入联动Outbox_工程任务单.md
- 03_需求与设计/02_开发计划/TASK-030E_质量统计分析增强_工程任务单.md
- 03_需求与设计/02_开发计划/TASK-030F_质量导出PDFExcel增强_工程任务单.md
- 03_需求与设计/02_开发计划/TASK-030G_来料检验自动触发_工程任务单.md
- 03_需求与设计/02_开发计划/TASK-040A_销售库存只读聚合增强_工程任务单.md
- 03_需求与设计/02_开发计划/TASK-040B_库存过滤权限增强_工程任务单.md
- 03_需求与设计/02_开发计划/TASK-040C_跨模块视图_工程任务单.md
- 03_需求与设计/02_开发计划/TASK-S4-SEAL_Sprint4正式封版白名单提交_工程任务单.md
- 03_需求与设计/02_开发计划/工程师会话日志.md
- 03_需求与设计/05_审计记录/审计官会话日志.md
- 06_前端/lingyi-pc/src/api/cross_module.ts
- 06_前端/lingyi-pc/src/api/quality.ts
- 06_前端/lingyi-pc/src/api/sales_inventory.ts
- 06_前端/lingyi-pc/src/router/index.ts
- 06_前端/lingyi-pc/src/views/cross_module/CrossModuleView.vue
- 06_前端/lingyi-pc/src/views/quality/QualityInspectionDetail.vue
- 06_前端/lingyi-pc/src/views/quality/QualityInspectionList.vue
- 06_前端/lingyi-pc/src/views/sales_inventory/SalesInventoryStockLedger.vue
- 07_后端/lingyi_service/app/main.py
- 07_后端/lingyi_service/app/models/quality.py
- 07_后端/lingyi_service/app/models/quality_outbox.py
- 07_后端/lingyi_service/app/routers/cross_module_view.py
- 07_后端/lingyi_service/app/routers/quality.py
- 07_后端/lingyi_service/app/routers/sales_inventory.py
- 07_后端/lingyi_service/app/schemas/cross_module_view.py
- 07_后端/lingyi_service/app/schemas/quality.py
- 07_后端/lingyi_service/app/schemas/quality_outbox.py
- 07_后端/lingyi_service/app/schemas/sales_inventory.py
- 07_后端/lingyi_service/app/services/cross_module_view_service.py
- 07_后端/lingyi_service/app/services/erpnext_quality_adapter.py
- 07_后端/lingyi_service/app/services/erpnext_quality_outbox_adapter.py
- 07_后端/lingyi_service/app/services/erpnext_sales_inventory_adapter.py
- 07_后端/lingyi_service/app/services/quality_export_service.py
- 07_后端/lingyi_service/app/services/quality_outbox_service.py
- 07_后端/lingyi_service/app/services/quality_outbox_worker.py
- 07_后端/lingyi_service/app/services/quality_purchase_receipt_listener.py
- 07_后端/lingyi_service/app/services/quality_service.py
- 07_后端/lingyi_service/app/services/sales_inventory_service.py
- 07_后端/lingyi_service/migrations/versions/task_030c_add_quality_cancel_reason.py
- 07_后端/lingyi_service/migrations/versions/task_030d_create_quality_outbox.py
- 07_后端/lingyi_service/tests/test_cross_module_view.py
- 07_后端/lingyi_service/tests/test_quality_api.py
- 07_后端/lingyi_service/tests/test_quality_auto_trigger.py
- 07_后端/lingyi_service/tests/test_quality_cancel_baseline.py
- 07_后端/lingyi_service/tests/test_quality_confirm_baseline.py
- 07_后端/lingyi_service/tests/test_quality_create_baseline.py
- 07_后端/lingyi_service/tests/test_quality_defect_baseline.py
- 07_后端/lingyi_service/tests/test_quality_export_enhanced.py
- 07_后端/lingyi_service/tests/test_quality_outbox.py
- 07_后端/lingyi_service/tests/test_quality_statistics_enhanced.py
- 07_后端/lingyi_service/tests/test_quality_update_baseline.py
- 07_后端/lingyi_service/tests/test_quality_worker_permissions.py
- 07_后端/lingyi_service/tests/test_sales_inventory_api.py
- 07_后端/lingyi_service/tests/test_sales_inventory_enhanced.py
- 07_后端/lingyi_service/tests/test_sales_inventory_permission.py
- 07_后端/lingyi_service/tests/test_sales_inventory_permissions.py
