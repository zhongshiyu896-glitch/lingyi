# TASK-060C_FIX2 报表目录 CSV 导出错误提示闭环 工程任务单

- 任务编号：TASK-060C_FIX2
- 任务名称：报表目录 CSV 导出错误提示闭环
- 角色：B Engineer
- 派发时间：2026-04-21 00:32 CST+8
- 派发人：A Technical Architect
- 模块：报表与仪表盘 / reports
- 前置依据：`TASK-060C_FIX1` 审计意见书第412份 `NEEDS_FIX`
- 当前定位：仅修复第412份 P1 finding，不扩大前后端能力边界。

## 0. 强制说明

本任务单是 A -> B 执行指令，不是 B -> C 审计输入。

未形成真实代码改动、验证命令输出和证据路径前，禁止回交 C。

本任务不允许 commit、push、PR、tag、生产发布。

## 1. 审计 finding 原文摘要

C Auditor 第412份指出：

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/reports/ReportCatalog.vue` 的 `exportCatalogCsv` 仍直接调用异步 `reportApi.exportReportCatalogCsv(...)`。
- 当前调用没有 `await`、`.catch` 或 `try/catch`。
- `requestFile(...)` 已能解析并抛出 `401/403/400/503` 等错误，但页面不会捕获这些错误并提示用户，形成未处理 Promise。

## 2. 修复目标

只修复 `ReportCatalog.vue` 导出按钮调用链：

1. 将 `exportCatalogCsv` 改为可消费 Promise 的实现，例如：`async (): Promise<void>`。
2. 使用 `await reportApi.exportReportCatalogCsv(...)` 或等价 `.catch(...)`。
3. 在 `catch` 中调用 `ElMessage.error((error as Error).message || '导出失败')`。
4. 保持无权限前置判断：无 `report:export` 时仍 `ElMessage.warning(...)` 并 `return`。
5. 不改变 `reportApi.exportReportCatalogCsv(...)` 的签名和下载逻辑。
6. 不新增诊断、刷新、重算、生成、同步、提交等入口。

## 3. 允许修改文件

仅允许修改：

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/reports/ReportCatalog.vue`

## 4. 禁止修改范围

1. 禁止修改 `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/request.ts`。
2. 禁止修改 `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/report.ts`。
3. 禁止修改 `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/router/index.ts`。
4. 禁止修改任何后端文件。
5. 禁止修改 `.github/**`。
6. 禁止修改 `02_源码/**`。
7. 禁止修改 `04_生产/**`。
8. 禁止新增或修改 migration。
9. 禁止新增或修改 `app/models/**`。
10. 禁止新增 `diagnostic / cache_refresh / recalculate / generate / sync / submit`。
11. 禁止新增 `fetch` / `axios` / `/api/resource` 直连。
12. 禁止 commit、push、PR、tag、生产发布。

## 5. 推荐实现

建议将当前：

```ts
const exportCatalogCsv = (): void => {
  if (!canExport.value) {
    ElMessage.warning('当前账号无 report:export 权限')
    return
  }
  reportApi.exportReportCatalogCsv({ ... })
}
```

改为：

```ts
const exportCatalogCsv = async (): Promise<void> => {
  if (!canExport.value) {
    ElMessage.warning('当前账号无 report:export 权限')
    return
  }
  try {
    await reportApi.exportReportCatalogCsv({ ... })
  } catch (error: unknown) {
    ElMessage.error((error as Error).message || '导出失败')
  }
}
```

如项目 lint/typecheck 对 async click handler 有特殊要求，也可以用：

```ts
void reportApi.exportReportCatalogCsv({ ... }).catch((error: unknown) => {
  ElMessage.error((error as Error).message || '导出失败')
})
```

但必须能证明没有未处理 Promise。

## 6. 验收要求

B 必须证明：

1. `ReportCatalog.vue` 中 `reportApi.exportReportCatalogCsv(...)` 的 Promise 已被 `await`、`.catch` 或 `try/catch` 消费。
2. 导出错误可通过 `ElMessage.error(...)` 展示。
3. 无 `report:export` 权限时仍走 `ElMessage.warning(...)`。
4. 未修改 `request.ts`、`report.ts`、`router/index.ts` 和任何后端文件。
5. 未新增 `fetch` / `axios` / `/api/resource` 直连。
6. 第410份已通过项不得回退。

## 7. 必跑验证命令

在 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service` 执行：

```bash
.venv/bin/python -m pytest tests/test_report_catalog_export.py tests/test_report_catalog_readonly.py tests/test_permissions_registry.py -v --tb=short
.venv/bin/python -m py_compile app/routers/report.py app/services/report_catalog_service.py app/services/report_export_service.py app/schemas/report.py
rg -n "@router\.(post|put|patch|delete)" app/routers/report.py || true
rg -n "requests\.|httpx\.|/api/resource|Stock Entry|Stock Reconciliation|GL Entry|Payment Entry|Purchase Invoice" app/routers/report.py app/services/report_catalog_service.py app/services/report_export_service.py app/schemas/report.py || true
rg -n "outbox|worker|run-once|internal|diagnostic|cache_refresh|recalculate|generate|sync|submit" app/routers/report.py app/services/report_catalog_service.py app/services/report_export_service.py app/schemas/report.py || true
git diff --name-only -- .github 02_源码 04_生产
```

在 `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc` 执行：

```bash
npm run typecheck
rg -n "reportApi\.exportReportCatalogCsv|ElMessage\.error|ElMessage\.warning" src/views/reports/ReportCatalog.vue
rg -n "fetch\(|axios\.|/api/resource|diagnostic|cache_refresh|recalculate|generate|sync|submit" src/views/reports/ReportCatalog.vue || true
git diff --name-only -- src/api/request.ts src/api/report.ts src/router/index.ts
```

说明：
- `sync` 若只作为 `async` 子串命中，需要在回交中说明不是业务同步语义。
- `git diff --name-only -- src/api/request.ts src/api/report.ts src/router/index.ts` 必须为空；如不为空，视为越界。

## 8. 回交格式

B 完成后回交给 C，必须包含：

```text
STATUS: READY_FOR_AUDIT
TASK_ID: TASK-060C_FIX2
ROLE: B Engineer

CHANGED_FILES:
- 真实改动文件列表

EVIDENCE:
- 第412份 P1 finding 修复说明
- exportCatalogCsv Promise 消费证据
- ElMessage.error 错误提示证据
- 未修改 request.ts / report.ts / router/index.ts / 后端文件证据
- 禁改目录 diff 结果

VERIFICATION:
- pytest 结果
- py_compile 结果
- npm run typecheck 结果
- 负向扫描结果

BLOCKERS:
- 无 / 具体阻塞

NEXT_ROLE:
- C Auditor
```

## 9. 完成定义

满足以下条件才算完成：

1. 第412份 P1 finding 收敛。
2. 下载错误响应可被页面捕获并提示。
3. 第410份修复不回退。
4. 前端 typecheck 通过。
5. 后端既有 060C 测试继续通过。
6. 禁改目录 diff 为空。
7. 未修改本任务禁止文件。
8. B 回交包含真实验证命令与证据路径。
