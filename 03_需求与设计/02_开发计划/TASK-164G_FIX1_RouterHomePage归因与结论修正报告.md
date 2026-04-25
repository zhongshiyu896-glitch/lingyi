# TASK-164G FIX1 Router/HomePage 归因与结论修正报告

## 1. 任务范围

- TASK_ID: `TASK-164G`
- FIX_PASS: `FIX1`
- 本轮仅执行只读归因补证与结论修正，不做任何代码修改。
- 本轮仅允许输出：
  - `03_需求与设计/02_开发计划/TASK-164G_FIX1_RouterHomePage归因与结论修正报告.md`
  - `03_需求与设计/02_开发计划/工程师会话日志.md`

## 2. 只读证据

### 2.1 router diff（只读）

命令：

`git -C '/Users/hh/Desktop/领意服装管理系统' diff -- '06_前端/lingyi-pc/src/router/index.ts'`

摘要：

- `/` redirect 从 `/bom/list` 改为 `/home`
- 新增 `/home` 路由，`name: HomePage`，`component: () => import('@/views/HomePage.vue')`
- 新增 `/app/:pathMatch(.*)*` redirect `/home`
- 新增 `/:pathMatch(.*)*` redirect `/home`

### 2.2 HomePage 状态与 mtime（只读）

命令：

1. `git -C '/Users/hh/Desktop/领意服装管理系统' status --short -- '06_前端/lingyi-pc/src/router/index.ts' '06_前端/lingyi-pc/src/views/HomePage.vue'`
2. `stat -f '%Sm %N' -t '%Y-%m-%d %H:%M:%S %z' '/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/router/index.ts' '/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/HomePage.vue'`

结果：

- `M 06_前端/lingyi-pc/src/router/index.ts`
- `?? 06_前端/lingyi-pc/src/views/HomePage.vue`
- 两者 mtime 均为 `2026-04-24 15:15:32 +0800`

### 2.3 历史 owner 证据检索（只读）

检索范围：

- `工程师会话日志.md`
- `架构师会话日志.md`
- `TASK-164A_Lingyi当前tracked_diff基线归口冻结报告.md`
- `TASK-164G` 原任务单与原归口报告
- 相关历史任务文档（`TASK-004*`、`TASK-015*`、`TASK-021*`、`TASK-100*`）

检索命令要点：

- `rg -n "HomePage|/home|pathMatch|catch-all|redirect"`
- `rg -n "src/router/index.ts|HomePage.vue|BUSINESS_CODE_TRACKED_DIFF_NEEDS_OWNER"`

结果结论：

- 在 `TASK-004/015/021/100` 相关任务文档中，未检索到 `/home`、`HomePage`、catch-all redirect 的明确 owner 证据。
- `TASK-164A` 基线报告将 `src/router/index.ts` 标记为 `BUSINESS_CODE_TRACKED_DIFF_NEEDS_OWNER`（待后续 owner 归口）。
- 当前可见关于 `HomePage` 的记录来自 C/A 对 `TASK-164G` 的 FIX finding 与复核说明，不构成历史 owner 归口证据。

## 3. 归因与结论修正

### 3.1 归因结果

- `ATTRIBUTION_RESULT: ROUTER_HOMEPAGE_NOT_TASK_164G`

说明：

- 现有只读证据无法证明 `src/router/index.ts` 中 `/home`/catch-all 变更与 `HomePage.vue` 属于 `TASK-164G`（生产计划 Work Order 候选写入口链）范围内历史产物。
- `HomePage.vue` 当前为 untracked，且未在 `TASK-164G` 允许范围文件中。

### 3.2 TASK-164G 结论修正

- `TASK_164G_OVERALL_RECLASSIFICATION: PARTIAL_ONLY`
- `PRODUCTION_SCOPE_RECLASSIFICATION: HISTORICAL_TASK_OUTPUT_VERIFIED`
- `ROUTER_HOMEPAGE_RECLASSIFICATION: PENDING_OWNER`

修正口径：

1. 不再声称 `TASK-164G` 七文件整体 `HISTORICAL_TASK_OUTPUT_VERIFIED`。
2. 仅对生产计划/Work Order 语义文件（列表/详情 + 后端 production 三文件 + `test_production_plan.py`）维持范围内验证通过结论。
3. `router/index.ts` 与 `HomePage.vue` 保留为待归口 baseline diff，需 A 后续单开 owner 归口任务。

## 4. no-code-change 证明

命令：

1. `git -C '/Users/hh/Desktop/领意服装管理系统' diff --name-only -- '03_需求与设计/02_开发计划/TASK-164G_FIX1_RouterHomePage归因与结论修正报告.md' '03_需求与设计/02_开发计划/工程师会话日志.md'`
2. `git -C '/Users/hh/Desktop/领意服装管理系统' status --short -- '06_前端/lingyi-pc/src/router/index.ts' '06_前端/lingyi-pc/src/views/HomePage.vue'`

结果：

- 本轮写入仅限 FIX1 报告与工程师会话日志。
- `router/index.ts` 仍为 `M`，`HomePage.vue` 仍为 `??`，状态未被本轮改变。

## 5. 风险边界

- 本报告仅修正 `TASK-164G` 对 router/HomePage 的范围归因，不代表该两项已完成 owner 归口。
- 不代表剩余 business tracked diff、REL-004/REL-005、生产联调、ERPNext 生产写入或业务功能放行。
