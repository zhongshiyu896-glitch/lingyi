# TASK-YISUAN-1TO1-B036-SOURCE-CAPTURE-CAND005

## 统一契约结论
- source_status: found
- unified_contract_available: true
- missing_source_items: []
- candidate_id: YISUAN-1TO1-CAND-005

## 路由与关系
- `/materialPurchase/materialPurchaseProcess` -> `/subcontract/list?parity=material-purchase`
- `/subcontract/list` 与 `/subcontract/detail`：入口/回读关系明确
- `/sales-inventory/stock-ledger` 与 `/warehouse`：形成联合视觉合同（流水表 + 仓库摘要/库位）

## 详情级 UI 来源
1. subcontract list source
   - route/anchor: `z045_cand005_subcontract_sync_readback/*`
   - screenshot: `subcontract_list_1440x1200.png`
2. subcontract detail source
   - route/anchor: `z044_cand005_subcontract_list_detail_sync_lock_readback/*` + `z045_cand005_subcontract_sync_readback/*`
   - screenshot: `subcontract_detail_1440x1200.png`
3. materialPurchase parity source
   - route parity: `task_z007b_17_module_entry_to_list_route_parity_evidence.json`
   - route evidence: `z045_cand005_subcontract_sync_readback/route_evidence.json`
4. stock-ledger source
   - route/anchors: `mvp_b050_cand006_inventory_regression/{route_probe.json,dom_anchors.json}`
   - screenshot: `stock_ledger_1440x1200.png`
5. warehouse source
   - route/anchors: `yisuan_1to1_b012_regression_cand002/{route_probe.json,dom_anchors.json}`
   - screenshots: `warehouse_1440x1200.png`, `warehouse_yisuan_reference_1440x1200.png`

## UI 分组约束（可审计）
- 字段分组：筛选区、主信息区、状态区、表格区、读回区
- 按钮区：只读/guard 边界来源于 z044/z045 与 mvp_b050/b012 anchors
- 状态区：状态标签与只读提示来源于 anchors + 1440x1200 截图
- 表格密度：以 1440x1200 截图为密度基准
- 空状态与只读态：纳入合同，不在本任务执行实现改动

## 安全边界
- ERPNext production: forbidden
- real production account: forbidden
- online write: forbidden
- remote lifecycle release: forbidden
- A001-A006 business contract merged: false
