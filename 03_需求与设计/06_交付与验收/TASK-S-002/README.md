# TASK-S-002 交付与验收

本目录存放第二组 B2 的本地验收/冒烟回归工具交付物与执行证据。

## 固定输出报告

- `sample_reports/report.json`
- `sample_reports/report.md`
- `failure_sample/report.json`
- `failure_sample/report.md`

## 手册与记录

- `本地验收回归执行手册.md`
- `R1_执行记录.md`

## 工具入口

- `07_后端/lingyi_service/scripts/run_acceptance_smoke.sh`
- `07_后端/lingyi_service/scripts/run_task002_acceptance_smoke.sh`（兼容入口）
- `07_后端/lingyi_service/tools/acceptance_smoke/run_smoke.py`
- `03_需求与设计/06_交付与验收/TASK-S-002/TASK-S-002_C2审计清单.md`

## 覆盖范围

1. BOM：`POST /api/bom/`、`GET /api/bom/`、`GET /api/bom/{bom_id}`
2. Workshop：`tickets/register`、`tickets/reversal`、`tickets`、`daily-wages`
3. Production：`plans`(POST/GET)、`plans/{plan_id}/material-check`
4. Subcontract：`POST /api/subcontract/`、`GET /api/subcontract/`、`POST /api/subcontract/{order_id}/issue-material`
5. 共 13 个关键接口 case（含历史口径 `requirement_endpoint` 元数据）

## 边界说明

1. 仅包含 tools/scripts/docs/evidence。
2. 不修改主线业务代码，不进入 TASK-005/TASK-006。
3. 工具只走 HTTP，不导入主业务 service/model/router/schema。
4. 报告按真实执行结果输出，可复核、可审计。
