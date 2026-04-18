# TASK-S-002 C2 审计清单

## 1. 边界合规

- [ ] 仅修改以下路径：
  - `07_后端/lingyi_service/tools/acceptance_smoke/`
  - `07_后端/lingyi_service/scripts/run_acceptance_smoke.sh`
  - `07_后端/lingyi_service/scripts/run_task002_acceptance_smoke.sh`（兼容入口）
  - `03_需求与设计/06_交付与验收/TASK-S-002/`
  - `03_需求与设计/02_开发计划/TASK-S-002_本地验收回归工具包_工程任务单.md`
- [ ] 未修改禁止目录：
  - `app/models/` `app/services/` `app/routers/` `app/schemas/`
  - `migrations/` `tests/` `06_前端/` `.github/` `02_源码/`
- [ ] 禁止范围未跟踪项已明确排除，不纳入 TASK-S-002 提交：
  - `02_源码/`
  - `06_前端/lingyi-pc/README.md`
- [ ] 未触达 TASK-005 / TASK-006 实现
- [ ] 旧路径重复清单已清理：`03_需求与设计/05_审计记录/TASK-S-002_C2审计清单.md` 不再作为本任务归档入口
- [ ] `tools/acceptance_smoke/__pycache__/` 未纳入提交

## 2. 工具能力

- [ ] `run_smoke.py` 可执行
- [ ] CLI 支持：`--module` `--base-url` `--token` `--report-dir`
- [ ] 支持 `--config`
- [ ] 仅通过 HTTP 调用，不 import 主业务 service/model/router/schema
- [ ] token/Authorization 在报告中脱敏
- [ ] 支持从前序响应提取变量并注入后续请求（如 `{{plan_id}}` / `{{order_id}}`）

## 3. Case 覆盖与格式

- [ ] 四个模块 case 文件存在：
  - `bom_cases.json`
  - `workshop_cases.json`
  - `production_cases.json`
  - `subcontract_cases.json`
- [ ] 覆盖 13 个关键接口（BOM 3 + Workshop 4 + Production 3 + Subcontract 3）
- [ ] 每个 case 包含：
  - `id/module/name/method/endpoint/expected_status/expected_code`
  - `payload` 或 `query`
- [ ] BOM/Subcontract 历史路径差异通过 `requirement_endpoint` 记录

## 4. 报告与退出码

- [ ] 能生成 `report.json` 与 `report.md`
- [ ] `report.json` 包含：
  - `task_id/generated_at/base_url/module/total_cases/passed/failed/skipped/elapsed_ms/cases`
- [ ] `cases[]` 包含：
  - `id/module/endpoint/method/expected_status/actual_status/expected_code/actual_code/pass/elapsed_ms/error`
- [ ] `report.md` 包含：
  - 模块通过率
  - 失败明细
  - 跳过原因
  - 耗时统计
  - 执行命令与报告生成时间
- [ ] 退出码规则：
  - 全通过 `0`
  - 存在失败/跳过/环境阻塞/配置错误 `1`

## 5. C2 结论

- [ ] 通过
- [ ] 有条件通过
- [ ] 不通过

结论说明：
