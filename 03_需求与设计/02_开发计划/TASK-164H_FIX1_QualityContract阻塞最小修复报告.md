# TASK-164H FIX1 Quality Contract 阻塞最小修复报告

## 1. 任务范围

- TASK_ID: `TASK-164H`
- FIX_PASS: `FIX1`
- 允许代码文件：
  - `06_前端/lingyi-pc/src/api/quality.ts`
  - `06_前端/lingyi-pc/src/views/HomePage.vue`（本轮未改）
- 文档文件：
  - `03_需求与设计/02_开发计划/TASK-164H_FIX1_QualityContract阻塞最小修复报告.md`
  - `03_需求与设计/02_开发计划/工程师会话日志.md`

## 2. 最小实现说明

本轮仅在 `src/api/quality.ts` 做最小修复：

1. 清除裸 `fetch()`：
   - 导出逻辑改为 `requestFile(...)` 受控边界。
2. 清除 `URL.createObjectURL()`：
   - 以 `FileReader.readAsDataURL` + `<a download>` 触发下载，不再使用 Blob URL。
3. 补齐 `updateQualityInspection`：
   - 新增 `updateQualityInspection(...)`（PATCH）。
4. 保留 `updateDraftInspection` 兼容：
   - `updateDraftInspection(...)` 作为别名转调 `updateQualityInspection(...)`。

未新增 ERPNext 直连端点，未新增 diagnostic/internal/run-once/worker 入口。

## 3. 静态核对

### 3.1 quality.ts 合同锚点

- `rg -n "fetch\\(|axios|URL\\.createObjectURL|window\\.URL\\.createObjectURL|/api/resource|/api/method|frappe|/api/quality/diagnostic|quality/internal|run-once" src/api/quality.ts`
  - 结果：无命中（PASS）
- `rg -n "updateQualityInspection|updateDraftInspection" src/api/quality.ts`
  - 结果：均命中（PASS）

### 3.2 router/HomePage 回归锚点

- `rg -n "internal|run-once|worker|debug|diagnostic" src/router/index.ts`
  - 结果：无命中（PASS）
- `rg -n "/api/resource|/api/method|frappe|fetch\\(|internal|run-once|worker|debug|diagnostic" src/views/HomePage.vue`
  - 结果：无命中（PASS）
- 本轮未修改 `src/views/HomePage.vue`，保留 TASK-164H 最小会话文案修正。

## 4. 门禁验证结果

执行目录：`/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc`

1. `npm run check:quality-contracts` -> PASS
2. `npm run test:quality-contracts` -> PASS（scenarios=14）
3. `npm run typecheck` -> PASS
4. `npm run check:production-contracts` -> PASS
5. `npm run test:production-contracts` -> PASS（scenarios=12）
6. `npm run check:sales-inventory-contracts` -> PASS
7. `npm run test:sales-inventory-contracts` -> PASS（scenarios=13）
8. `npm run check:factory-statement-contracts` -> PASS
9. `npm run test:factory-statement-contracts` -> PASS（scenarios=26）
10. `npm run check:style-profit-contracts` -> PASS
11. `npm run test:style-profit-contracts` -> PASS（scenarios=475）

## 5. 收尾校验

- `git diff --check -- src/api/quality.ts src/router/index.ts src/views/HomePage.vue` -> PASS（无输出）
- 路径状态（限定）：
  - `src/api/quality.ts`: modified（本轮修复）
  - `src/router/index.ts`: modified（历史基线，未触碰）
  - `src/views/HomePage.vue`: untracked（历史基线，未触碰）
  - `工程师会话日志.md`: modified（本轮追加）
  - `TASK-164H_FIX1_...报告.md`: 本轮新增

## 6. 结论

- `related_scope`: `APP_SHELL_ROUTER_HOMEPAGE + QUALITY_CONTRACT_BLOCKER`
- `can_reclassify_to`: `HISTORICAL_TASK_OUTPUT_VERIFIED`
- `remaining_unowned_business_diffs_excluded`: `YES`

本结论仅针对 TASK-164H FIX1 范围，不外推到质量主链整体放行、剩余 business tracked diff、REL-004/REL-005、生产联调或 ERPNext 生产写入放行。
