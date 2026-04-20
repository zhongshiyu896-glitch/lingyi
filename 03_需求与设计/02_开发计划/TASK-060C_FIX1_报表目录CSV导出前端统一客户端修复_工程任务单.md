# TASK-060C_FIX1 报表目录 CSV 导出前端统一客户端修复 工程任务单

- 任务编号：TASK-060C_FIX1
- 任务名称：报表目录 CSV 导出前端统一客户端修复
- 角色：B Engineer
- 派发时间：2026-04-21 00:11 CST+8
- 派发人：A Technical Architect
- 模块：报表与仪表盘 / reports
- 前置依据：`TASK-060C` 审计意见书第410份 `NEEDS_FIX`
- 当前定位：仅修复第410份 P1 finding，不扩大 TASK-060C 后端能力边界。

## 0. 强制说明

本任务单是 A -> B 执行指令，不是 B -> C 审计输入。

未形成真实代码改动、验证命令输出和证据路径前，禁止回交 C。

本任务不允许 commit、push、PR、tag、生产发布。

## 1. 审计 finding 原文摘要

C Auditor 第410份指出：

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/report.ts` 中 `exportReportCatalogCsv` 直接创建 `<a>` 并设置 `link.href` 访问 `/api/reports/catalog/export`。
- 该方式未通过统一 `request` 或明确的项目下载 client。
- 风险：无法复用鉴权失败处理、错误响应解析和下载响应处理，`403/400` 可能被浏览器当作页面或文件打开。

## 2. 修复目标

修复 `exportReportCatalogCsv(query)`：

1. 不再直接把 `/api/reports/catalog/export` 塞给 `<a href>` 发起请求。
2. 必须使用统一客户端能力或明确下载 helper 发起请求。
3. 请求必须保留 `credentials: include`。
4. 非 2xx 响应必须解析错误信息并抛出可读错误。
5. 成功响应必须以 blob 下载 CSV。
6. 下载文件名必须安全：优先解析后端 `Content-Disposition`，若解析失败则使用固定 fallback：`report_catalog_export.csv`。
7. 不得把用户输入拼入文件名。

## 3. 允许修改文件

### 3.1 前端允许修改

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/report.ts`

### 3.2 条件允许修改

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/request.ts`
  - 仅当需要新增通用下载 helper 时允许修改。
  - helper 必须保持现有 `request<T>` 行为不变。
  - helper 建议名称可为 `downloadFile` / `requestBlob`，但必须清晰表达用途。

## 4. 禁止修改范围

1. 禁止修改后端文件。
2. 禁止修改 `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/router/index.ts`。
3. 禁止修改 `.github/**`。
4. 禁止修改 `02_源码/**`。
5. 禁止修改 `04_生产/**`。
6. 禁止新增或修改 migration。
7. 禁止新增或修改 `app/models/**`。
8. 禁止新增前端诊断、缓存刷新、重算、生成、同步、提交入口。
9. 禁止新增裸 `axios`。
10. 禁止新增 ERPNext `/api/resource` 直连。
11. 禁止 commit、push、PR、tag、生产发布。

## 5. 推荐实现口径

优先方案：在 `src/api/request.ts` 增加明确的下载 helper，然后 `report.ts` 使用该 helper。

helper 至少满足：

```ts
export interface DownloadFileResult {
  blob: Blob
  filename: string
  contentType: string
}
```

建议行为：

1. 使用 `fetch(url, { credentials: 'include', ... })`，这是统一客户端内部实现，不是业务 API 文件裸绕过。
2. 尝试解析 JSON 错误响应：
   - `401` 或 `AUTH_UNAUTHORIZED` -> `登录已失效，请重新登录`
   - `403` 或 `AUTH_FORBIDDEN` -> `无权执行该操作`
   - 其他错误 -> 使用后端 `message` 或 `请求失败`
3. 成功时读取 `response.blob()`。
4. 从 `Content-Disposition` 解析 filename，并做安全清洗。
5. 如果 filename 缺失或非法，使用 fallback。

`report.ts` 负责：

1. 构造 `/api/reports/catalog/export` 查询字符串。
2. 调用下载 helper。
3. 用 `URL.createObjectURL(blob)` 创建临时下载链接。
4. 设置安全文件名触发下载。
5. finally 中 revoke object URL 并移除 DOM 节点。

## 6. 验收要求

B 必须证明：

1. `report.ts` 不再直接设置 `link.href = '/api/reports/catalog/export...'` 发起请求。
2. 下载请求走统一 helper 或明确下载 client。
3. `credentials: include` 存在于下载请求链路。
4. `403/400` 等错误响应会被解析并抛错，而不是下载成文件。
5. 成功响应通过 blob 下载。
6. 文件名来源安全，不含用户查询参数。
7. 不修改后端、不修改 router。

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
rg -n "axios\.|/api/resource|diagnostic|cache_refresh|recalculate|generate|sync|submit" src/api/report.ts src/api/request.ts src/views/reports/ReportCatalog.vue || true
rg -n "link\.href\s*=\s*['\"]?/api/reports/catalog/export|window\.location|location\.href" src/api/report.ts src/api/request.ts src/views/reports/ReportCatalog.vue || true
git diff --name-only -- src/router/index.ts
```

说明：
- `src/api/request.ts` 内部出现 `fetch(` 可接受，因为它是统一客户端实现。
- `src/api/report.ts` 不应直接出现裸 `fetch(` 或 `axios.`。
- `src/api/report.ts` 中允许出现 `URL.createObjectURL` 和临时 `<a>`，但只能用于 blob 下载，不能用于直接访问后端 URL。

## 8. 回交格式

B 完成后回交给 C，必须包含：

```text
STATUS: READY_FOR_AUDIT
TASK_ID: TASK-060C_FIX1
ROLE: B Engineer

CHANGED_FILES:
- 真实改动文件列表

EVIDENCE:
- 第410份 P1 finding 修复说明
- 下载 helper 或统一客户端调用证据
- credentials include 证据
- 错误响应解析证据
- blob 下载与安全文件名证据
- 未修改后端/路由证据
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

1. 第410份 P1 finding 收敛。
2. 前端导出不再绕过统一客户端/下载 helper。
3. 下载错误响应可被前端捕获并提示。
4. 后端既有 060C 测试继续通过。
5. 前端 typecheck 通过。
6. 禁改目录 diff 为空。
7. B 回交包含真实验证命令与证据路径。
