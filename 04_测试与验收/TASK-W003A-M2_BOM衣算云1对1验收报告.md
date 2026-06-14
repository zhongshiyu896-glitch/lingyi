# TASK-W003A-M2 BOM 衣算云 1:1 验收报告

- 更新时间：2026-06-14 10:42 CST+8
- 范围：M2-S1 至 M2-S5，BOM 列表/详情读基线、建档/编辑真实写端点、详情生命周期按钮、清 local-dev 沙箱 UI 与死代码、Playwright 闭环截图。
- 结论：本地实现与自测 gate 通过；等待顾问代码/视觉审查。后端零改，未执行真实 ERPNext 生产写。

## 实现摘要

1. `BomList.vue` 替换为衣算云「物料开发 / 面料」布局：顶部面包屑、页签、工具栏、搜索、表格列、分页与加载/错误/禁用/空/无权限状态均按 35/37/40/41 口径落地。
2. 建档/编辑表单移除 `scenario_tag`、回滚、回读本地等沙箱面板；UI 仅展示面料建档字段，内部载体仍按后端安全 gate 生成。
3. 写闭环接真实前端 API：`createBom(POST /api/bom/)`、`updateBomDraft(PUT /api/bom/{id})`。
4. `BomDetail.vue` 接真实生命周期 API：`setDefaultBom`、`activateBom`、`deactivateBom`、`explodeBom`，按钮按 `button_permissions` fail-closed 显隐/禁用。
5. 删除 `bom.ts` 的 `LOCAL_*`/`*LocalBom*` 旧沙箱函数；删除 `production.ts` 的两个 `fetchLocalReadback*` 死代码。

## 自测结果

- `npm run verify`：PASS。
- `npm run test:bom-m2-contracts`：PASS，锁定无 `/api/local-dev/bom`、无旧 LocalBom/rollback/readback 符号、真实 BOM API 与 1:1 关键 token。
- `node 04_测试与验收/测试证据/W003A_M2_bom_yisuan_1to1/e2e_bom_m2_yisuan_flow.mjs`：PASS。
- `rg -n "/api/local-dev/bom" src/views`：空。

## 浏览器证据

- 基准截图：`01_list_yisuan_1to1_baseline.png`
- 写闭环：`02_create_dialog_yisuan_build.png`、`03_after_create_list_true_endpoint.png`、`04_detail_yisuan_lifecycle_toolbar.png`、`05_edit_dialog_yisuan_build.png`、`06_after_edit_detail_true_endpoint.png`、`07_after_default_activate_deactivate.png`、`08_explode_result_true_endpoint.png`
- 状态截图：`09_state_loading.png`、`10_state_error.png`、`11_state_disabled.png`、`12_state_empty.png`、`13_state_no_permission.png`
- 结构化摘要：`04_测试与验收/测试证据/W003A_M2_bom_yisuan_1to1/e2e_bom_m2_yisuan_flow_summary.json`

## 关键断言

- 真实端点命中：create=1、update=1、set_default=1、activate=1、deactivate=1、explode=1。
- `local_dev_bom_calls=0`。
- 1:1 样式 token：页面背景 `rgb(246, 248, 249)`、主色 `rgb(78, 136, 243)`、表头 `rgb(245, 247, 250)`、正文 `rgb(81, 90, 110)`。
- 关键结构：物料开发/面料顶部、工具栏、`请输入名称/供应商/编号`、表头 `图片/编号/部位/名称/颜色/成分/幅宽/克重/操作`、`30条/页` 均通过。

## 未释放项

- 顾问审查前不进入 M3。
- 真实 ERPNext 生产写、PR/merge/tag/release 仍为 HUMAN_ONLY。
