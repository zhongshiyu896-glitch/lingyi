# TASK-164A Lingyi当前tracked diff基线归口冻结报告

## 1. 执行范围与约束

- TASK_ID: `TASK-164A`
- 执行角色: `B Engineer`
- 本任务性质: `docs-only / read-only 归口冻结`
- 本任务未执行：
  - 任何 diff 清理、回滚、还原、格式化
  - 任何前端命令（npm/pnpm/yarn/vite/typecheck/build）
  - 任何后端测试/业务写缓存命令
  - 任何 CCC 启停/重载与 relay start/stop API 调用

## 2. 只读核对结果

### 2.1 tracked diff 总量

- 命令：`git -C '/Users/hh/Desktop/领意服装管理系统' diff --name-only | wc -l`
- 结果：`40`

### 2.2 tracked diff 清单统计

- 命令：`git -C '/Users/hh/Desktop/领意服装管理系统' diff --stat`
- 结果摘要：`40 files changed, 3512 insertions(+), 455 deletions(-)`

### 2.3 `vite.config.ts` 单独核对

- 命令：`git -C '/Users/hh/Desktop/领意服装管理系统' diff -- '06_前端/lingyi-pc/vite.config.ts'`
- diff 摘要：
  - 新增 `VITE_LINGYI_DEV_USER`、`VITE_LINGYI_DEV_ROLES` 环境变量读取
  - 新增 dev proxy `proxyReq` header 注入：
    - `X-LY-Dev-User`
    - `X-LY-Dev-Roles`
- 命令：`stat -f '%Sm %N' -t '%Y-%m-%d %H:%M:%S %z' '/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/vite.config.ts'`
- mtime：`2026-04-24 14:49:13 +0800`

### 2.4 untracked 面统计

- 命令：`git -C '/Users/hh/Desktop/领意服装管理系统' ls-files --others --exclude-standard | wc -l`
- 结果：`80681`
- 顶层目录聚合（只读统计）：
  - `04_测试与验收`: 77240
  - `01_需求与资料`: 3082
  - `05_交付物`: 176
  - `03_需求与设计`: 167
  - `03_环境与部署`: 4
  - `07_后端`: 3
  - `02_源码`: 3
  - `00_交接与日志`: 3
  - `.ci-reports`: 2
  - `06_前端`: 1

## 3. tracked diff 归口分类结论

### 3.1 分类计数

- `CONTROL_PLANE_OR_A_FLOW`: 4
- `HISTORICAL_TASK_OUTPUT`: 12
- `BUSINESS_CODE_TRACKED_DIFF_NEEDS_OWNER`: 22
- `DEV_CONFIG_TRACKED_DIFF_NEEDS_OWNER`: 1
- `UNKNOWN_OR_UNOWNED`: 1

合计：40（与 tracked diff 总数一致）

### 3.2 分类表（path / category / suspected_owner_or_source_task / evidence / next_action）

| path | category | suspected_owner_or_source_task | evidence | next_action |
|---|---|---|---|---|
| `.gitignore` | UNKNOWN_OR_UNOWNED | 未明确归口 | 仓库根配置文件，当前无明确 TASK 归口证据 | 由 A 单开归口任务指定 owner；当前冻结为 baseline，不得在后续业务任务中误判为当轮改动 |
| `00_交接与日志/HANDOVER_STATUS.md` | CONTROL_PLANE_OR_A_FLOW | A 流转控制面 | 路径属于交接状态面 | 按控制面变更处理，不计入后续业务实现任务违规 |
| `03_需求与设计/01_架构设计/TASK-016A_财务管理边界设计.md` | HISTORICAL_TASK_OUTPUT | TASK-016A 历史产物 | 文件名含 TASK 且位于架构设计目录 | 归档为历史任务输出，不作为新任务改动证据 |
| `03_需求与设计/01_架构设计/TASK-017A_采购管理边界设计.md` | HISTORICAL_TASK_OUTPUT | TASK-017A 历史产物 | 同上 | 同上 |
| `03_需求与设计/01_架构设计/TASK-018A_仓库管理增强边界设计.md` | HISTORICAL_TASK_OUTPUT | TASK-018A 历史产物 | 同上 | 同上 |
| `03_需求与设计/01_架构设计/TASK-019A_报表与仪表盘总体设计.md` | HISTORICAL_TASK_OUTPUT | TASK-019A 历史产物 | 同上 | 同上 |
| `03_需求与设计/01_架构设计/TASK-020A_权限治理设计.md` | HISTORICAL_TASK_OUTPUT | TASK-020A 历史产物 | 同上 | 同上 |
| `03_需求与设计/01_架构设计/架构师会话日志.md` | CONTROL_PLANE_OR_A_FLOW | A 架构调度流 | 文件为 A 角色流水日志 | 仅按控制面/流转口径审计，不并入业务代码 diff |
| `03_需求与设计/02_开发计划/TASK-016A_财务管理边界设计冻结_工程任务单.md` | HISTORICAL_TASK_OUTPUT | TASK-016A 历史任务单 | 路径与命名符合历史任务单 | 冻结为 baseline，后续如需清理由 A 定向派发 |
| `03_需求与设计/02_开发计划/TASK-017A_采购管理边界设计冻结_工程任务单.md` | HISTORICAL_TASK_OUTPUT | TASK-017A 历史任务单 | 同上 | 同上 |
| `03_需求与设计/02_开发计划/TASK-018A_仓库增强边界设计冻结_工程任务单.md` | HISTORICAL_TASK_OUTPUT | TASK-018A 历史任务单 | 同上 | 同上 |
| `03_需求与设计/02_开发计划/TASK-019A_报表与仪表盘总体设计_工程任务单.md` | HISTORICAL_TASK_OUTPUT | TASK-019A 历史任务单 | 同上 | 同上 |
| `03_需求与设计/02_开发计划/TASK-020A_权限治理设计冻结_工程任务单.md` | HISTORICAL_TASK_OUTPUT | TASK-020A 历史任务单 | 同上 | 同上 |
| `03_需求与设计/02_开发计划/TASK-021D_生产工单内部Worker运行与Outbox闭环门禁_工程任务单.md` | HISTORICAL_TASK_OUTPUT | TASK-021D 历史任务单 | 同上 | 同上 |
| `03_需求与设计/02_开发计划/TASK-024D_移动端候选写入口与同步审计门禁_工程任务单.md` | HISTORICAL_TASK_OUTPUT | TASK-024D 历史任务单 | 同上 | 同上 |
| `03_需求与设计/02_开发计划/工程师会话日志.md` | CONTROL_PLANE_OR_A_FLOW | B 流转日志主文件 | 文件为 B 回交流水 | 后续审计按流水文件口径处理，不归入业务代码违规 |
| `03_需求与设计/05_审计记录/审计官会话日志.md` | CONTROL_PLANE_OR_A_FLOW | C 审计流转日志 | 文件为 C 审计流水 | 后续审计按审计日志口径，不归入业务代码违规 |
| `06_前端/lingyi-pc/scripts/frontend-contract-engine.mjs` | BUSINESS_CODE_TRACKED_DIFF_NEEDS_OWNER | 历史业务实现链（前端工具） | 位于前端 scripts，非控制面 | A 指定 owner（前端/工具链）后处理，不在本任务内变更 |
| `06_前端/lingyi-pc/scripts/test-frontend-contract-engine.mjs` | BUSINESS_CODE_TRACKED_DIFF_NEEDS_OWNER | 历史业务实现链（前端工具） | 同上 | 同上 |
| `06_前端/lingyi-pc/src/api/factory_statement.ts` | BUSINESS_CODE_TRACKED_DIFF_NEEDS_OWNER | 历史业务实现链（加工厂对账） | 位于业务 API 层 | A 后续按业务主线派单归口 |
| `06_前端/lingyi-pc/src/api/request.ts` | BUSINESS_CODE_TRACKED_DIFF_NEEDS_OWNER | 历史业务实现链（请求层） | 位于前端请求基座 | 同上 |
| `06_前端/lingyi-pc/src/api/sales_inventory.ts` | BUSINESS_CODE_TRACKED_DIFF_NEEDS_OWNER | 历史业务实现链（销售库存） | 位于业务 API 层 | 同上 |
| `06_前端/lingyi-pc/src/api/warehouse.ts` | BUSINESS_CODE_TRACKED_DIFF_NEEDS_OWNER | 历史业务实现链（仓库） | 位于业务 API 层 | 同上 |
| `06_前端/lingyi-pc/src/router/index.ts` | BUSINESS_CODE_TRACKED_DIFF_NEEDS_OWNER | 历史业务实现链（路由承载） | 位于前端路由层 | 同上 |
| `06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementDetail.vue` | BUSINESS_CODE_TRACKED_DIFF_NEEDS_OWNER | 历史业务实现链（加工厂对账） | 位于业务视图层 | 同上 |
| `06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementList.vue` | BUSINESS_CODE_TRACKED_DIFF_NEEDS_OWNER | 历史业务实现链（加工厂对账） | 位于业务视图层 | 同上 |
| `06_前端/lingyi-pc/src/views/production/ProductionPlanDetail.vue` | BUSINESS_CODE_TRACKED_DIFF_NEEDS_OWNER | 历史业务实现链（生产计划） | 位于业务视图层 | 同上 |
| `06_前端/lingyi-pc/src/views/production/ProductionPlanList.vue` | BUSINESS_CODE_TRACKED_DIFF_NEEDS_OWNER | 历史业务实现链（生产计划） | 位于业务视图层 | 同上 |
| `06_前端/lingyi-pc/src/views/sales_inventory/SalesInventorySalesOrderList.vue` | BUSINESS_CODE_TRACKED_DIFF_NEEDS_OWNER | 历史业务实现链（销售库存） | 位于业务视图层 | 同上 |
| `06_前端/lingyi-pc/src/views/sales_inventory/SalesInventoryStockLedger.vue` | BUSINESS_CODE_TRACKED_DIFF_NEEDS_OWNER | 历史业务实现链（销售库存） | 位于业务视图层 | 同上 |
| `06_前端/lingyi-pc/src/views/warehouse/WarehouseDashboard.vue` | BUSINESS_CODE_TRACKED_DIFF_NEEDS_OWNER | 历史业务实现链（仓库） | 位于业务视图层 | 同上 |
| `06_前端/lingyi-pc/vite.config.ts` | DEV_CONFIG_TRACKED_DIFF_NEEDS_OWNER | 前端开发配置归口待定 | diff 为 dev user/roles header 注入 | 单开配置归口任务，不并入 TASK-157A~163A |
| `07_后端/lingyi_service/app/core/error_codes.py` | BUSINESS_CODE_TRACKED_DIFF_NEEDS_OWNER | 历史业务实现链（后端） | 位于后端业务代码 | A 指定后端 owner 继续归口 |
| `07_后端/lingyi_service/app/routers/production.py` | BUSINESS_CODE_TRACKED_DIFF_NEEDS_OWNER | 历史业务实现链（后端） | 位于后端路由层 | 同上 |
| `07_后端/lingyi_service/app/routers/warehouse.py` | BUSINESS_CODE_TRACKED_DIFF_NEEDS_OWNER | 历史业务实现链（后端） | 位于后端路由层 | 同上 |
| `07_后端/lingyi_service/app/schemas/warehouse.py` | BUSINESS_CODE_TRACKED_DIFF_NEEDS_OWNER | 历史业务实现链（后端） | 位于后端 schema 层 | 同上 |
| `07_后端/lingyi_service/app/services/erpnext_warehouse_adapter.py` | BUSINESS_CODE_TRACKED_DIFF_NEEDS_OWNER | 历史业务实现链（后端） | 位于后端 service 层 | 同上 |
| `07_后端/lingyi_service/app/services/production_service.py` | BUSINESS_CODE_TRACKED_DIFF_NEEDS_OWNER | 历史业务实现链（后端） | 位于后端 service 层 | 同上 |
| `07_后端/lingyi_service/app/services/warehouse_service.py` | BUSINESS_CODE_TRACKED_DIFF_NEEDS_OWNER | 历史业务实现链（后端） | 位于后端 service 层 | 同上 |
| `07_后端/lingyi_service/tests/test_production_plan.py` | BUSINESS_CODE_TRACKED_DIFF_NEEDS_OWNER | 历史业务实现链（后端测试） | 位于后端测试层 | A 指定后端 owner 后处理 |

## 4. `vite.config.ts` 归口结论（单独）

- `mtime`: `2026-04-24 14:49:13 +0800`
- `diff_summary`:
  - 增加 `VITE_LINGYI_DEV_USER / VITE_LINGYI_DEV_ROLES`
  - 增加 dev proxy 请求头注入 `X-LY-Dev-User / X-LY-Dev-Roles`
- `related_to_TASK_157A_163A`: **NO**
  - 依据：TASK-157A~163A 任务范围集中在 `/Users/hh/Desktop/ccc/**` 与日志/审计流；且多轮任务单显式禁止触碰 Lingyi 前端业务范围。
- `recommended_next_action`:
  - 由 A 新开 `DEV_CONFIG_TRACKED_DIFF_NEEDS_OWNER` 归口任务（可建议编号 `TASK-164B`）。
  - 在该任务完成前，将 `vite.config.ts` 明确冻结为 baseline dirty，后续 C 审计不应将其误判为当轮 B 越权改动（除非当轮 mtime 与 diff 内容出现新增变化且有直接证据）。

## 5. 冻结口径（供后续审计使用）

1. 当前 40 个 tracked diff 视为 `TASK-164A` 时点 baseline。
2. `CONTROL_PLANE_OR_A_FLOW` 与 `HISTORICAL_TASK_OUTPUT` 不应在后续业务实现任务中被重复判定为当轮业务代码越权。
3. `BUSINESS_CODE_TRACKED_DIFF_NEEDS_OWNER` 与 `DEV_CONFIG_TRACKED_DIFF_NEEDS_OWNER` 需 A 后续分配 owner 和任务单，不应在未归口前被自动外推为当前任务责任。
4. `UNKNOWN_OR_UNOWNED`（当前仅 `.gitignore`）需 A 额外裁决归口。
5. 本报告不构成任何业务功能放行、生产联调放行、GitHub 管理配置放行。

## 6. 本任务落地确认

- 本任务未清理、未回滚、未还原任何既有 diff。
- 本任务仅新增本报告，并按要求追加工程师会话日志。
