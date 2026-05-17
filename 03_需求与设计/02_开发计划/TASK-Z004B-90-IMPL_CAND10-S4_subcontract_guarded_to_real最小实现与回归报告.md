# TASK-Z004B-90-IMPL CAND10-S4 subcontract 最小实现与回归报告

## 1. 任务与范围
- TASK_ID: `TASK-Z004B-90-IMPL`
- candidate: `TASK-Z004B-CAND-10-S4`
- module/route: `subcontract` / `/subcontract/list`
- 实现 allowlist 文件：
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/subcontract/SubcontractOrderList.vue`
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/subcontract/SubcontractOrderDetail.vue`

## 2. 产品改动
- 仅修改上述 2 个 Vue 文件。
- 本轮将以下入口保持 guarded（不触发真实写请求）：
  - 新建外发单（create）
  - 发料（issue）
  - 回料（receive）
  - 验货（inspect）
  - 结算预览（settlement_preview）
- 仅保留结算锁定/释放子链路的 UI 入口。

## 3. 回归执行结果
- npm: `precheck/typecheck/verify = PASS/PASS/PASS`
- browser evidence: `/tmp/task_z004b90_browser_result.json`
  - route coverage: `/subcontract/list` desktop/mobile 均已采集
  - screenshots_count: `2`
  - network methods: `{"GET": 42}`
  - browser write/forbidden/unexpected: `0/0/0`

## 4. API regression 与 zero residual
- 产物：
  - `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/task_z004b_90_cand10_s4_subcontract_guarded_to_real_api_regression.json`
  - `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/task_z004b_90_cand10_s4_subcontract_guarded_to_real_zero_residual.json`
- 结论：`BLOCKED`
  - 原因：`settlement-candidates` 返回空集合（`candidate_count=0`），无法在“不造数据”约束下形成合法 `lock -> release` 链路。
  - 按门禁未执行 lock/release 写请求。
  - 计数保持：
    - approved_write_request_count = `0`
    - unexpected/forbidden/ERPNext/worker/production/import-export = `0`
    - baseline/after_lock/after_release = `0/0/0`
    - residual_scan_result = `no_new_residual`

## 5. 状态保留
- `remote_lifecycle_parked=true`
- `readback_business_closed=false`
- `project_completion_claimed=false`（未声明项目完成）

## 6. 下一步建议
- 该任务按 precondition 阻断收口：需要先具备合法 settlement candidate（由既有业务数据自然产生或后续授权任务提供），再重跑 `TASK-Z004B-90-IMPL`。
